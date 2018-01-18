# -*- coding: utf-8 -*-
"""
"""
from __future__ import division

import copy
import datetime
import socket
import time

import paramiko

from common.datatype import node_struct, masternode_struct
from common.util import NowMilli
from common.util import Result
from core.errcode import CLUSTER_EXISTED_WORKSPACE, CLUSTER_NOT_EXISTED, NODE_HAS_ADDED, \
    CLUSTER_EXESTED_NODE, CURRENT_HOST_NOT_ADD, NODE_IS_EXISTED, NODE_USED_BY_UFLEET, CLUSTER_SSL_ERROR, \
    CLU_DELETE_NOT_ALLOWED, CLU_NOT_AUTH, INTERNAL_EXCEPT_ERR, LICENSE_OUT_OF_DATE
from core.kubeclient import KubeClient
from core.kubeclientmgr import KubeClientMgr
from core.remoteclient import RemoteParam
from etcddb.kubernetes.clustermgr import Clusterdb
from etcddb.kubernetes.mastermgr import Masterdb
from etcddb.kubernetes.nodemgr import CluNodedb
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from etcddb.monitormgr import Monitordb
from etcddb.networkmgr import Networkdb
from frame.auditlogger import WebLog
from frame.configmgr import GetSysConfig
from frame.logger import Log, PrintStack
from launcherclient import LauncherClient
# from operator import itemgetter
# import multiprocessing
from common.commoncluster import syn_nodeinfo
from core.errcode import CLU_IS_PENDING
from cadvisor import Cadvisor


def remote_scp(host_ip, remote_path, local_path, username, password):
    t = paramiko.Transport((host_ip, 22))
    t.connect(username=username, password=password)  # 登录远程服务器
    sftp = paramiko.SFTPClient.from_transport(t)  # sftp传输协议
    src = remote_path
    des = local_path
    sftp.get(src, des)
    t.close()


def utc2local(utc_st):
    """UTC时间转本地时间（+8:00）"""
    now_stamp = time.time()
    local_time = datetime.datetime.fromtimestamp(now_stamp)
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st


class ClusterManageMgr(object):
    def __init__(self):
        self.cludb = Clusterdb.instance()
        self.__store = {"all_nodes": [], "clu_node": {}, "clu_dic": {}}
        self.expiry_time = 0
        self.loaddata()
        self.kubemgr = KubeClientMgr.instance()

    def reload(self, flush=0):
        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def loaddata(self):
        self.expiry_time = NowMilli() + 20000
        try:
            self.load_cluster()
            self.load_node()
        except Exception as e:
            PrintStack()
            Log(1, "loaddata error:{}".format(e.message))

    def load_cluster(self):
        """
        # 加载集群信息
        :return:__store = {'clu_dic': {<cluster_name>: {"type": "", "member": [], "apply_num": 4}, 'clu_node': []}
        """
        rlt = self.cludb.read_clu_map()
        if not rlt.success:
            Log(1, "load_cluster fail,as[%s]" % (rlt.message))
            return

        clu_dic = {}
        clu_member = {}
        # clu_vip = {}
        clu_apply_num = {}
        for k, v in rlt.content.items():
            sp_key = k.split('/')
            if sp_key[-1] == 'cluster_info':
                clu_dic[sp_key[-2]] = v
            elif sp_key[-1] == 'member':
                clu_member[sp_key[-2]] = v or []
            elif sp_key[-1] == 'apply_num':
                clu_apply_num[sp_key[-2]] = v
                # if sp_key[-1] == 'vip':
                #     clu_vip[sp_key[-2]] = v

        Log(4, "load_cluster  clu_apply_num:{}".format(clu_apply_num))
        for k, v in clu_dic.items():
            v['apply_num'] = clu_apply_num.get(k, '')
            v['member'] = clu_member.get(k, [])
            # v['vip'] = clu_vip.get(k, {}).get('vip', '')

        self.__store['clu_dic'] = clu_dic

    def load_node(self):
        """
        # 加载node信息
        clu_node: {'cluster_name' : [{'node_name': 'ubunt', }, {}], ...}
        all_node: [{},{}]
        :return:
        """
        clu_node = {}
        all_nodes = []
        rlt = CluNodedb.instance().read_clunode_map()
        if not rlt.success:
            Log(1, "load_node read_clunode_map fail,as[%s]" % (rlt.message))
            return

        for k, v in rlt.content.items():
            sp_key = k.split('/')
            if sp_key[-3] == 'clusternodes':
                clu_node.setdefault(sp_key[-2], []).append(v)
                all_nodes.append(v)
        self.__store['all_nodes'] = all_nodes
        self.__store['clu_node'] = clu_node

    def __check_node_permission(self, username, clu_name):
        """
        # 主机资源的操作权限
        :return:
        """
        self.reload()
        member = self.__store['clu_dic'].get(clu_name, {}).get('member', [])
        creater = self.__store['clu_dic'].get(clu_name, {}).get('creater')
        if username not in member and username != creater:
            return Result('', CLU_NOT_AUTH, 'not allowed', 400)
        return Result(True)

    def __check_clu_mem_permission(self, username, clu_name):
        """
        :param username:
        :param clu_name:
        :return:
        """
        self.reload()
        creater = self.__store['clu_dic'].get(clu_name, {}).get('creater')
        if username != creater:
            return Result('', CLU_NOT_AUTH, 'not allowed', 400)
        return Result(True)

    def cluster_info_lo(self, cluster_name):
        """
        # 获取缓存中的信息
        :param cluster_name:
        :return: { 'auth_way': '',
                   'creater': '',
                   'create_time': datetime,
                   'cluster_name': "",
                   'node_num': 0,
                   'master_ip': [],
                   'node_list': [],
                   'member': [],
                   'cluster_type': 'accept',
                   'master_status': 'running',
                   'apply_num': 0,
                 }
        """
        self.reload()
        return self.__store['clu_dic'].get(cluster_name, {})

    def check_node_info(self, hosts):
        """
        检查添加主机时的参数
        :return:
        """
        ip_list = []
        for i in hosts:
            hostip = i.get('HostIP', '')
            hostname = i.get('HostName', '')
            cluster_name = i.get('ClusterName', '')
            ip_list.append(hostip)
            current_host = GetSysConfig('current_host').split(':')[0]
            if hostip == current_host:
                return Result('', CURRENT_HOST_NOT_ADD, 'current host can not add', code=400)

            # 检查集群是否存在（是否存在key值）
            if not self.cludb.clu_is_exist(cluster_name):
                return Result('', msg='', result=CLUSTER_NOT_EXISTED, code=400)

            # 检查该主机是否被添加过
            rlt = CluNodedb.instance().is_node_added(hostname)
            if not rlt.success:
                return rlt

            if rlt.content is True:
                return Result('', msg='', result=NODE_HAS_ADDED, code=400)

            # 检查是否是ufleet主机
            ufleet_hosts = GetSysConfig('ufleet_hosts').split(',')
            if hostip in ufleet_hosts:
                return Result('', msg='the host is used by ufleet.', result=NODE_USED_BY_UFLEET, code=400)
        if [True, False][len(ip_list) == len(list(set(ip_list)))]:
            return Result('', 400, 'master ip repeated', 400)
        return Result(0)

    def add_master(self, query_param, passport):
        """
        调用创建master主机的接口
        :return:
        """
        try:
            masters = query_param.get('Masters', [])
            cluster_name = query_param.get('Name', '')
            # 检查权限
            if not cluster_name:
                return Result('', 400, 'param error', 400)
            if passport.get('ring') != 'ring0':
                rlt = self.__check_node_permission(passport.get('username'), cluster_name)
                if not rlt.success or not rlt.content:
                    return rlt

            # 检查license
            if not passport.get('licensed', ''):
                return Result('', LICENSE_OUT_OF_DATE, 'licensed is out of date')

            # 检查参数
            check = self.check_node_info(masters)
            if not check.success:
                return Result('', check.result, check.message, 400)

            # 检查主机个数
            node_num = CluNodedb.instance().read_node_list(cluster_name)
            if not node_num.success:
                return Result('', 0, node_num.message, 403)
            master_list = [i['ip'] for i in node_num.content if i['type'] == 'master']

            # 保存数据到etcd
            for master_info in masters:
                # 保存主机信息到clusternode
                node_data = node_struct(cluster_name, master_info['HostIP'], 'master', passport.get('username'))
                rlt = CluNodedb.instance().save_node(cluster_name, node_data)
                if not rlt.success:
                    return rlt

                # 保存主机信息到masternodedir
                masternode_data = masternode_struct(passport.get('username'), master_info.get('ClusterName', ''),
                                                    'Master',
                                                    master_info.get('HostIP', ''), master_info.get('HostSSHPort', ''),
                                                    master_info.get('HostName', ''),
                                                    master_info.get('UserName', ''), master_info.get('UserPwd', ''),
                                                    master_info.get('Prikey', ''), master_info.get('PrikeyPwd'))

                rlt = Masterdb.instance().save_master(master_info.get('HostName', ''), masternode_data)
                if not rlt.success:
                    return rlt

                WebLog(3, u'添加', u"主机[{}]".format(master_info.get('HostIP', '')), passport.get('username'))

            # 通过launcher创建master
            # 当添加k8s高可用集群的master
            if len(master_list) > 1:
                rlt = LauncherClient.instance().add_ha_master(cluster_name, masters[0])
                if not rlt.success:
                    return rlt
            else:
                rlt = Clusterdb.instance().update_cluster(cluster_name,
                                                          {"vip": query_param.get('info', {}).get("Vip", masters[0].get(
                                                              'HostIP', ''))})
                if not rlt.success:
                    Log(1, "cluster add master update cluster errorr:{}".format(rlt.message))
                    return
                rlt = LauncherClient.instance().create_cluster(query_param)
                if not rlt.success:
                    self.reload(1)
                    return rlt

            self.reload(flush=1)
            return Result('')
        except Exception, e:
            # SysLog(1, "cluster add_master:{}".format(e))
            PrintStack()
            Log(1, "add master error:{}".format(e.message))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    def add_node(self, query_param, passport):
        """
        调用创建node的接口
        :param ip:
        :param username:
        :param password:
        :param veri_type:
        :return:
        """
        cluster_name = query_param.get('ClusterName')

        # 检查license
        if not passport.get('licensed', ''):
            return Result('', LICENSE_OUT_OF_DATE, 'licensed is out of date', 400)

        # 检查权限
        if not cluster_name:
            return Result('', 400, 'param error', 400)
        if passport.get('ring') != 'ring0':
            if passport.get('ring') != 'ring0':
                rlt = self.__check_node_permission(passport.get('username'), cluster_name)
                if not rlt.success or not rlt.content:
                    return rlt

        check = self.check_node_info([query_param])
        if not check.success:
            return Result('', check.result, check.message, 400)

        clu_info = self.cludb.read_cluster(cluster_name)
        if not clu_info.success:
            return Result('', clu_info.result, clu_info.message, 400)

        if clu_info.content.get('auth_way') == 'http':
            query_param['CaCerts'] = ""
        else:
            query_param['CaCerts'] = "ca_auth"

        # 保存主机信息到clusternode目录下
        node_data = node_struct(cluster_name, query_param['HostIP'], 'node', passport.get('username'))
        CluNodedb.instance().save_node(cluster_name, node_data)

        # 保存主机信息到masternodedir目录下
        masternode_data = masternode_struct(passport.get('username'), cluster_name, 'Node',
                                            query_param.get('HostIP', ''), query_param.get('HostSSHPort', ''),
                                            query_param.get('HostName', ''),
                                            query_param.get('UserName', ''), query_param.get('UserPwd', ''),
                                            query_param.get('Prikey', ''), query_param.get('PrikeyPwd'))

        Masterdb.instance().save_master(query_param.get('HostName', ''), masternode_data)

        WebLog(3, u'添加', u"节点[{}]".format(query_param.get('HostIP', '')), passport.get('username'))

        # 通过launcher创建node
        rlt = LauncherClient.instance().create_node(cluster_name, query_param)

        # 当调用launcher失败，删除etcd中数据
        if not rlt.success:
            self.reload(1)
            return rlt

        self.reload(flush=1)
        return Result('')

    def one_cluster(self):
        """
        :return:
        """
        rlt = self.cludb.read_clu_map()
        if not rlt.success:
            return Result('', result=405, code=405)

        for k, v in rlt.content.items():
            k1 = k.split('/')
            if k1[-1] == 'cluster_info':
                clu_name = v.get("cluster_name")
                auth_info = self.kubemgr.read_cluster_auth_info(clu_name)
                if not auth_info.success:
                    continue

                rlt = self.kubemgr.read_cluster_auth_info(clu_name)
                if not rlt.success:
                    continue
                kubeclient = KubeClient(rlt.content)
                s_connect = kubeclient.connect()
                if s_connect.success:
                    auth_info.content['workspace'] = 'default'
                    # auth_info.content['datetime'] = cluster_info.content.get('datetime', '')
                    auth_info.content['creater'] = v.get('creater', '')
                    auth_info.content['auth_way'] = v.get('auth_way', '')
                    return Result(auth_info.content)
        return Result('', result=405, code=405)

        # name_list = self.cludb.get_all_cluster_name()
        # if name_list.success:
        #     for name in name_list.content:
        #         cluster_info = self.cludb.read_cluster(name)
        #         if not cluster_info.success:
        #             continue
        #         auth_info = self.kubemgr.read_cluster_auth_info(name)
        #         if not auth_info.success:
        #             continue
        #
        #         kubeclient = KubeClient(auth_info.content)
        #         rlt = kubeclient.connect()
        #         if rlt.success:
        #             auth_info.content['workspace'] = 'default'
        #             # auth_info.content['datetime'] = cluster_info.content.get('datetime', '')
        #             auth_info.content['creater'] = cluster_info.content.get('creater', '')
        #             auth_info.content['auth_way'] = cluster_info.content.get('auth_way', '')
        #             return Result(auth_info.content)
        #     return Result('', result=405, code=405)
        # else:
        #     return Result('', result=405, code=405)

    def get_cluster(self, cluster_name, flush=0):
        """
        获取一个集群的信息
        :param cluster_name:
        :return:
        """
        self.reload(flush=flush)
        cluster_info = self.__store['clu_dic'].get(cluster_name, {})
        clu_node = self.__store['clu_node'].get(cluster_name, [])
        cluster_info['node_num'] = len(clu_node)
        master_ip = []
        master_status = []
        for i in clu_node:
            if i['status'] == 'pending':
                host_status = LauncherClient.instance().get_node_status(cluster_name, i['type'], i['ip'])
                if host_status.success:
                    i['status'] = host_status.content
                else:
                    i['status'] = 'error'
            if i['type'] == 'master':
                master_ip.append(i['ip'])
                master_status.append(i['status'])

        if cluster_info.get('type') == 'ha':
            count = {}
            for item in master_status:
                count[item] = count.get(item, 0) + 1
            if count.get('running', 0) >= 2:
                cluster_info['master_status'] = 'running'
            elif count.get('error') >= 2:
                cluster_info['master_status'] = 'error'
            else:
                cluster_info['master_status'] = 'pending'
        else:
            if master_status:
                cluster_info['master_status'] = master_status[0]
        return Result(cluster_info)

    def get_cluster_list(self, offset=0, limit=None, userid='ring0', username='admin'):
        """
        集群列表
        :param offset:
        :param limit:
        :param userid:
        :param username:
        :return: []
        """
        self.reload()
        if limit:
            limit = int(limit)
        data_dic = {'cluster_list': []}
        all_cluster = self.__store['clu_dic'].values()

        clu_list = []
        if userid == 'ring0' or 'ring3':
            clu_list = all_cluster[offset:limit]
        else:
            for c in all_cluster:
                if username in c.get('member', []):
                    clu_list.append(c)

        # 根据主机状态确定集群状态
        for i in clu_list:
            master_ip = []
            node_list = []
            clu_nodes = self.__store['clu_node'].get(i['cluster_name'], [])
            i['node_num'] = len(clu_nodes)
            master_status = []
            if clu_nodes:
                for j in clu_nodes:
                    if j['type'] == 'master':
                        master_ip.append(j['ip'])
                        master_status.append(j['status'])
                        # i['cluster_status'] = j['status']
                    node_list.append(j['ip'])
                if i.get('type') == 'ha':
                    count = {}
                    for item in master_status:
                        count[item] = count.get(item, 0) + 1
                    if count.get('running', 0) >= 2:
                        i['cluster_status'] = 'running'
                    elif count.get('error') >= 2:
                        i['cluster_status'] = 'error'
                    else:
                        i['cluster_status'] = 'pending'
                else:
                    i['cluster_status'] = master_status[0]
            else:
                i['cluster_status'] = ''
            i['master_ip'] = master_ip
            i['node_list'] = node_list
        data_dic['cluster_list'] = clu_list[offset:limit]
        return Result(data_dic)

    def get_cluster_auth(self, workspace):
        """
        获取集群认证信息
        :param name:
        :return:
        """
        try:
            ws = WorkSpacedb.instance().read_workspace(workspace)
            if not ws.success:
                return ws

            cluster_name = ws.content.get('cluster_name')

            # rlt = self.kubemgr.read_cluster_auth_info(cluster_name)
            # if not rlt.success:
            #     return rlt
            # auth_info = rlt.content
            rlt = LauncherClient.instance().get_cluster_auth_info(cluster_name)
            if not rlt.success:
                if rlt.result == CLU_IS_PENDING:
                    return Result('', CLU_IS_PENDING, 'clu master is pending')
                Log(1, 'KubeClientMgr.load_cluster read_cluster_auth_info[%s]fail,as[%s]' % (cluster_name, rlt.message))
                return rlt
            auth_info = rlt.content

            auth_info['workspace'] = workspace
            auth_info['cluster_name'] = cluster_name
            data_dic = {"k8sconf": auth_info,
                        "namespace": workspace
                        }
            return Result(data_dic)

        except Exception, e:
            Log(1, "get_auth_info error:{}".format(e.message))
            PrintStack()
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    def get_auth(self, cluster_name):
        return LauncherClient.instance().get_cluster_auth_info(cluster_name)

    def __check_conditions(self, con):
        """
        :param con:
        :return:
        """
        for j in con:
            if j.get('type') == 'Ready':
                if j.get('status') == 'True':
                    return True
        return False

    def component_statuses(self, client):
        """
        #~ kubectl get componentstatus
        检查master的状态  scheduler controller-manager etcd-0
        :param client:
        :param clu_name:
        :return:
        """
        rlt = client.clu_status()
        s_info = []
        if rlt.success:
            for i in rlt.content:
                name = i.get('metadata', {}).get('name')
                if 'etcd' in name:
                    continue
                for j in i.get('conditions'):
                    if j.get('type') == 'Healthy':
                        s_info.append({'name': name, 'status': j.get('status'), 'message': j.get('message')})
            s = list(set([i['status'] for i in s_info]))
            message = [i['message'] for i in s_info]

            if s == ['True']:
                return {'status': 'running', 'message': ''}
            else:
                return {'status': 'error', 'message': ';'.join(message)}
        else:
            Log(3, "get cluster components tatuses error:{}".format(rlt.message))
            return None

        # status = 0
        # rlt = client.get_pods('kube-system')
        # if not rlt.success:
        #     return rlt
        # for i in rlt.content:
        #     con = i.get('status', {}).get('conditions', [])
        #     host_ip = i.get('status', {}).get('hostIP', '')
        #     name = i.get('metadata', {}).get('name', '')
        #     if host_ip != ip:
        #         continue
        #     if name.startswith('calico-node'):
        #         status += 1 if self.__check_conditions(con) else False
        #     elif name.startswith('kube-apiserver'):
        #         status += 1 if self.__check_conditions(con) else False
        #     elif name.startswith('kube-controller-manager'):
        #         status += 1 if self.__check_conditions(con) else False
        #     elif name.startswith('kube-dns'):
        #         status += 1 if self.__check_conditions(con) else False
        #     elif name.startswith('kube-proxy'):
        #         status += 1 if self.__check_conditions(con) else False
        #     elif name.startswith('kube-scheduler'):
        #         status += 1 if self.__check_conditions(con) else False

    def get_node(self, cluster_name):
        """
        # 主机列表
        :param cluster_name:
        :param flush:
        :return:
        """
        self.reload()
        nodes = self.__store['clu_node'].get(cluster_name, [])
        for i in nodes:
            if i['status'] == 'pending' or not i.get('memory', ''):
                statusRlt = LauncherClient.instance().get_node_status(cluster_name, i['type'], i['ip'])
                if not statusRlt.success:
                    Log(1, 'get_node[%s][%s][%s]fail,as[%s]' % (cluster_name, i['type'], i['ip'], statusRlt.message))
                    i['status'] = 'error'
                    continue

                if statusRlt.content != 'running':
                    i['status'] = statusRlt.content
                    continue

                # 获取主机名
                rlt = LauncherClient.instance().get_host_name(cluster_name, i['type'] + 's', i['ip'])
                if not rlt.success:
                    Log(1, 'get_node get_host_name[%s][%s][%s] fail,as[%s]' % (
                        cluster_name, i['type'], i['ip'], rlt.message))
                    continue

                host_name = rlt.content

                # 实时获取主机信息
                # 获取apiserver client
                rlt = KubeClientMgr.instance().get_current_client(cluster_name)
                if not rlt.success:
                    Log(1, 'get_node get_current_client [%s]fail,as[%s]' % (cluster_name, rlt.message))
                    continue

                client = rlt.content

                # 获取最新主机信息
                rlt = client.get_node_info(host_name)
                if not rlt.success:
                    Log(1, 'get_node get_node_info [%s]fail,as[%s]' % (host_name, rlt.message))
                    continue

                new_node_info = rlt.content

                update_node = syn_nodeinfo(i, new_node_info)

                # 检查主机作为master的状态
                if i['type'] == 'master':
                    m_s = self.component_statuses(client)
                    if m_s:
                        if m_s['status'] != i.get('m_status'):
                            update_node['status'] = m_s['status']
                            update_node['message'] = m_s['message']
                if not update_node:
                    continue

                rlt_ = CluNodedb.instance().update_node(i['cluster_name'], i['ip'].replace('.', '-'), update_node)
                if not rlt_.success:
                    Log(1, "get_node update_node [%s][%s]fail,as[%s]" % (i['cluster_name'], i['ip'], rlt_.message))

                i.update(update_node)

        return Result(nodes)

    def error_reason(self, cluster_name, ip, host_type):
        """
        主机异常的原因
        :param cluster_name:
        :param host_name:
        :return:
        """
        launchercli = LauncherClient.instance()
        rlt = launchercli.get_host_error_reason(cluster_name, host_type, ip)
        if not rlt:
            ip_name = ip.replace('.', '-')
            r = CluNodedb.instance().read_node(cluster_name, ip_name)
            if not r.success:
                return r
            return Result({'error_reason': [r.content.get('message', '')]})
        return rlt

    def host_progress(self, cluster_name, ip, host_type):
        """
        主机进度
        :param cluster_name:
        :param host_name:
        :return:
        """
        rlt = LauncherClient.instance().get_host_info(cluster_name, host_type, ip)
        if not rlt.success:
            return rlt
        data = rlt.json_data()

        pro = data.get('progress', '0')
        if pro:
            try:
                per = round(eval(pro), 3) * 100
            except ZeroDivisionError:
                per = 0
        else:
            per = 0
        return Result(per)

    def get_pod(self, cluster_name, host_name):
        """
        获取主机上的pod
        :param cluster_name:
        :return:
        """
        # return self.kubemgr.get_host_all_pods(cluster_name, host_name)
        # return self.kubemgr.get_pods_load(cluster_name, host_name)
        return self.kubemgr.get_host_all_pods(cluster_name, host_name)

    def workspace_list(self, cluster_name):
        """
        """
        return WorkSpacedb.instance().get_ns_by_cluster(cluster_name)

    def delete_cluster(self, cluster_name, username):
        """
        删除集群
        已经实现
        :param cluster_name:
        :return:
        """
        # 检查是否有权限删除 admin和创建者可以删除
        if username != 'admin':
            rlt = Clusterdb.instance().read_cluster(cluster_name)
            if not rlt.success:
                return rlt
            if rlt.content.get('creater') != username:
                return Result('', CLU_DELETE_NOT_ALLOWED, 'not allowed', 405)

        ws = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not ws.success:
            return ws

        if len(ws.content) > 0:
            return Result('', CLUSTER_EXISTED_WORKSPACE, '', 400)

        # 检查主机个数
        node_num = CluNodedb.instance().read_node_list(cluster_name)
        if not node_num.success:
            return node_num

        if len(node_num.content) > 0:
            return Result('', msg='the cluster existed node', result=CLUSTER_EXESTED_NODE, code=400)

        # 删除clustermanages中信息
        self.cludb.delete_cluster_dir(cluster_name)
        WebLog(3, u'删除', u"集群[{}]".format(cluster_name), username)

        # 删除network中数据
        Networkdb.instance().del_ippool_dir(cluster_name)

        # 删除clusternodes中集群信息
        CluNodedb.instance().delete_node_dir(cluster_name)
        # 更新缓存中的信息
        self.reload(flush=1)
        return Result('success')

    def remove_node(self, cluster_name, node_name, host_real_name, passport):
        """
        移除node,node_name:192-168-4-5
        已经实现
        :param node_name:
        :return:
        """
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_node_permission(passport.get('username'), cluster_name)
            if not rlt.success or not rlt.content:
                return rlt

        info_d = self.cluster_info_lo(cluster_name)
        if not info_d:
            return Result('', msg='the cluster is not existed', result=CLUSTER_NOT_EXISTED, code=400)

        node_ip = node_name.replace('-', '.')

        # 通过apiserver删除主机
        if host_real_name:
            rlt = self.kubemgr.delete_cluster_node(cluster_name, host_real_name)
            if not rlt.success:
                Log(1, "delete node:{} error by apiserver:{}".format(host_real_name, rlt.message))
        else:
            rlt = LauncherClient.instance().get_host_name(cluster_name, 'nodes', node_ip)
            if rlt.success:
                rlt = self.kubemgr.delete_cluster_node(cluster_name, rlt.content)
                if not rlt.success:
                    Log(1, "delete node:{} error by apiserver:{}".format(rlt.content, rlt.message))

        # 通过launcher 删除node
        rlt = LauncherClient.instance().delete_node(cluster_name, node_ip)
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 500)

        # 删除etcd中的数据
        Masterdb.instance().delete_master(node_name)

        # 删除nodemonitor中的数据
        rlt = Monitordb.instance().nodemonitor_deldir(node_name)
        if not rlt.success:
            return Result('', 0, )

        # 删除clusternodedir下的主机信息
        rlt = CluNodedb.instance().delete_node(cluster_name, node_name)
        if not rlt.success:
            return Result('', 0, rlt.message, 500)

        WebLog(3, u'删除', u"节点[{}]".format(node_name.replace('-', '.')), passport.get('username'))
        # 更新缓存中的信息
        self.reload(flush=1)
        return Result('')

    def remove_master(self, cluster_name, host_ip, host_real_name, passport):
        """
        移除高科用集群的某个master
        检出workspace和node
        :param node_name:
        :return:
        """
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_node_permission(passport.get('username'), cluster_name)
            if not rlt.success or not rlt.content:
                return rlt

        info_d = self.cluster_info_lo(cluster_name)
        if not info_d:
            return Result('', msg='the cluster is not existed', result=CLUSTER_NOT_EXISTED, code=400)

        # 检查主机个数
        node_num = CluNodedb.instance().read_node_list(cluster_name)
        if not node_num.success:
            return Result('', 0, node_num.message, 403)
        master_list = []
        node_list = []
        for i in node_num.content:
            if i['type'] == 'node':
                node_list.append(i['ip'].replace('.', '-'))
            if i['type'] == 'master':
                master_list.append(i['ip'].replace('.', '-'))

        # 为保证高可用集群正常运行，必须有两台master是正常才行
        if len(master_list) >= 3:
            # 删除etcd中数据
            host_name = host_ip.replace('.', '-')
            rlt = Masterdb.instance().delete_master(host_name)
            if not rlt.success:
                return rlt
            rlt = Monitordb.instance().nodemonitor_deldir(host_name)
            if not rlt.success:
                return rlt
            rlt = CluNodedb.instance().delete_node(cluster_name, host_name)
            if not rlt.success:
                return rlt
            WebLog(3, u"删除", u"master[{}]".format(host_name), passport.get('username'))
            # 通过apiserver删除主机
            if host_real_name:
                rlt = self.kubemgr.delete_cluster_node(cluster_name, host_real_name)
                if not rlt.success:
                    Log(1, "delete node:{} error by apiserver:{}".format(host_real_name, rlt.message))
            else:
                rlt = LauncherClient.instance().get_host_name(cluster_name, 'masters', host_ip)
                if rlt.success:
                    rlt = self.kubemgr.delete_cluster_node(cluster_name, rlt.content)
                    if not rlt.success:
                        Log(1, "delete node:{} error by apiserver:{}".format(rlt.content, rlt.message))
            rlt = LauncherClient.instance().delete_ha_master(cluster_name, host_ip)
            if not rlt.success:
                self.reload(flush=1)
                return rlt
            # 更新缓存中的信息
            self.reload(flush=1)
            return Result(0)

        if node_list:
            return Result('', msg='delete node first', result=NODE_IS_EXISTED, code=400)

        # 检查是否有workspace
        rlt = WorkSpacedb.instance().clu_used(cluster_name)
        if not rlt.success:
            return rlt
        if rlt.content:
            return Result('', msg='there are existed workspace in the cluster. delete workspace first',
                          result=CLUSTER_EXISTED_WORKSPACE, code=400)

        # 通过launcher 删除cluster
        rlt = LauncherClient.instance().delete_cluster(cluster_name)
        if not rlt.success:
            return rlt

        # 删除etcd中的数据
        for i in master_list:
            rlt = Masterdb.instance().delete_master(i)
            if not rlt.success:
                return rlt

            rlt = Monitordb.instance().nodemonitor_deldir(i)
            if not rlt.success:
                return rlt

            rlt = CluNodedb.instance().delete_node(cluster_name, i)
            if not rlt.success:
                return rlt
            WebLog(3, u"删除", u"master[{}]".format(i.replace('-', '.')), passport.get('username'))

        # 先删除所有的subnets, 再创建目录
        rlt = Networkdb.instance().del_ippool_dir(cluster_name)
        if not rlt.success:
            return rlt

        # 将集群中的应用个数更新为0
        Clusterdb.instance().update_apply_num(cluster_name, 0)

        # 将集群vip更新为空
        Clusterdb.instance().update_cluster(cluster_name, {"vip": ""})
        # 更新缓存中的信息
        self.reload(flush=1)

        return Result('')

    def cluster_overview(self):
        """
        集群的概览
        :return:
        """
        rlt = self.get_cluster_list()
        if not rlt.success:
            return rlt
        data = {'running_num': 0, 'pending_num': 0, 'failed_num': 0}

        for i in rlt.content.get('cluster_list', []):
            if i.get('cluster_status') == 'running':
                data['running_num'] += 1
            if i.get('cluster_status') == 'pending':
                data['pending_num'] += 1
            if i.get('cluster_status') == 'error':
                data['failed_num'] += 1
        return Result(data)

    def node_overview(self):
        """
        主机的概览
        :return:
        """
        rlt = CluNodedb.instance().read_clunode_map()
        if not rlt.success:
            return rlt

        data = {'running_num': 0, 'pending_num': 0, 'failed_num': 0, 'eviction_num': 0}
        for i in rlt.content.values():
            if i.get('is_eviction'):
                data['eviction_num'] += 1
            else:
                if i.get('status') == 'running':
                    data['running_num'] += 1
                if i.get('status') == 'pending':
                    data['pending_num'] += 1
                if i.get('status') == 'error':
                    data['failed_num'] += 1

        return Result(data)

    def get_cluster_by_space(self, workspace_name):
        """
        :param workspace_name:
        :param group_name:
        :return:
        """
        ws = WorkSpacedb.instance().read_workspace(workspace_name)
        if not ws.success:
            return ws
        return Result(ws.content.get('cluster_name'))

    def cpu_anly(self, cpu_list):
        """
        对cpu进行数据分析
        :return:
        """
        cpu_data = []
        Log(3, "cpu_anly:{}".format(cpu_list))
        for i in range(len(cpu_list) - 1):
            Log(3, "timestamp:{}".format(cpu_list[i + 1]['timestamp'][0:-9]))
            t1 = datetime.datetime.strptime(cpu_list[i + 1]['timestamp'][0:-9], "%Y-%m-%dT%H:%M:%S.%f")
            t2 = datetime.datetime.strptime(cpu_list[i]['timestamp'][0:-9], "%Y-%m-%dT%H:%M:%S.%f")
            t_micro = (t1 - t2).seconds * 10 ** 6 + (t1 - t2).microseconds
            if t_micro > 0:
                cpu_use = cpu_list[i + 1]['cpu']['usage']['total'] - cpu_list[i]['cpu']['usage']['total']
                t = {
                    'time': cpu_list[i + 1]['timestamp'],
                    'cpu_use': round(abs(cpu_use) / (10 ** 3 * t_micro), 3)
                }
                cpu_data.append(t)
        return cpu_data

    def net_anly(self, net_list):
        """
        对网络进行分析
        :param net_list:
        :return:
        """
        net_r = []
        for i in net_list:
            Log(3, "net_anly:{}".format(i))
            for j in i.get('net', []):
                if j.get('name', '').startswith('eth'):
                    r = {
                        'time': time.mktime(time.strptime(i.get('timestamp', '').split('.')[0], '%Y-%m-%dT%H:%M:%S')),
                        'tx_bytes0': j.get('tx_bytes'),
                        'rx_bytes0': j.get('rx_bytes')
                    }
                    net_r.append(r)
                    break
        d_s = sorted(net_r, key=lambda s: s['time'])
        for i in range(len(d_s)):
            if i > 0:
                t_ = d_s[i]['time'] - d_s[i - 1]['time']
                d_s[i]['rx_bytes'] = round(abs(d_s[i]['rx_bytes0'] - d_s[i - 1]['rx_bytes0']) / (t_ * 1024), 3)
                d_s[i]['tx_bytes'] = round(abs(d_s[i]['tx_bytes0'] - d_s[i - 1]['tx_bytes0']) / (t_ * 1024), 3)
        for i in d_s:
            x = time.localtime(i['time'])
            i['time'] = time.strftime("%Y-%m-%dT%H:%M:%S", x)
        if d_s:
            d_s.remove(d_s[0])
        return d_s

    def disk_anly(self, disk_list):
        """
        对磁盘进行数据分析
        :param disk_list:
        :return:
        """
        disk_r = []
        for i in disk_list:
            read_bytes = 0
            write_bytes = 0
            for j in i.get('disk', {}).get('io_service_bytes', []):
                read_bytes += j.get('stats', {}).get('Read')
                write_bytes += j.get('stats', {}).get('Write')
            r = {
                'time': i.get('timestamp', '').split('.')[0],
                'read': round(read_bytes / (1024 * 1024), 3),
                'write': 0
            }
            disk_r.append(r)
        return disk_r

    def mem_anly(self, mem_list):
        """
        对mem进行数据分析
        :param mem_list:
        :return:
        """
        mem_r = []
        for m in mem_list:
            r = {
                'time': m.get('timestamp', '').split('.')[0],
                'usage': round(m.get('mem', {}).get('usage', 0) / (1024 * 1024), 3)
            }
            mem_r.append(r)
        return mem_r

    # def from_cadvisor(self, container_id, host_ip):
    #     """
    #     容器监控
    #     :param container_id:
    #     :param host_ip:
    #     :return:
    #     """
    #     try:
    #         url = 'http://' + host_ip + ':4194/api/v1.2/docker/' + container_id.split('//')[1]
    #         data = requests.get(url, timeout=5)
    #     except requests.exceptions.RequestException as e:
    #         Log(1, "check_cadvisor:{}".format(e.message))
    #         return ''
    #     except Exception as e:
    #         Log(1, "check_cadvisor Exception:{}".format(e.message))
    #         return ''
    #     else:
    #         if data.status_code == 200:
    #             try:
    #                 return data.json()
    #             except Exception as e:
    #                 Log(3, "from cadvisor data.json() error:{}".format(e.message))
    #                 return ''
    #         else:
    #             Log(1, "check_cadvisor error:{}, url:{}".format(data.text, url))
    #             return ''

    def data_anly(self, container_id, host_ip):
        """
        :param container_id:
        :param host_ip:
        :return:
        """
        # cpu disk mem
        # cdm_data = self.from_cadvisor(container_id, host_ip)
        cadvisor_cli = Cadvisor(host_ip)
        rlt = cadvisor_cli.get(container_id)
        if not rlt.success:
            return rlt
        cdm_data = rlt.content
        data_info = {
            'cpu': [],
            'disk': [],
            'mem': [],
            'net': []
        }
        if cdm_data and isinstance(cdm_data, dict):
            data = cdm_data.values()[0]
            pause_id = data.get('labels', {}).get('io.kubernetes.sandbox.id', '')
            j = data.get('stats', [])
            for k in j:
                cpu_info = {
                    'timestamp': k.get('timestamp', ''),
                    'cpu': k.get('cpu', ''),
                }
                disk_info = {
                    'timestamp': k.get('timestamp', ''),
                    'disk': k.get('diskio', '')
                }
                mem_info = {
                    'timestamp': k.get('timestamp', ''),
                    'mem': k.get('memory', '')
                }
                data_info['cpu'].append(cpu_info)
                data_info['disk'].append(disk_info)
                data_info['mem'].append(mem_info)
        else:
            Log(1, "get cdm_data data from cadvisor error:{}".format(cdm_data))
            return Result('', 400, 'the data from cadvisor error:{}'.format(cdm_data), 400)
        # 获取pause容器的网络(由于pod是共享pause容器网络)
        # net_data = self.from_cadvisor(pause_id, host_ip)

        cadvisor_cli = Cadvisor(host_ip)
        rlt = cadvisor_cli.get(pause_id)
        if not rlt.success:
            return rlt
        net_data = rlt.content
        if net_data and isinstance(net_data, dict):
            data = net_data.values()[0]
            j = data.get('stats', [])
            for k in j:
                net_info = {
                    'timestamp': k.get('timestamp', ''),
                    'net': k.get('network', {}).get('interfaces', [])
                }
                data_info['net'].append(net_info)
        else:
            Log(1, "get net data from cadvisor error:{}".format(net_data))
        # 返回数据结构
        r_data = {
            'cpu': self.cpu_anly(data_info['cpu']),
            'mem': self.mem_anly(data_info['mem']),
            'disk': self.disk_anly(data_info['disk']),
            'net': self.net_anly(data_info['net'])
        }

        return Result(r_data)

    def set_label(self, cluster_name, host_name, labels, username):
        """
        给主机设置标签
        :param cluster_name:
        :param host_ip:
        :return:
        """
        f_labels = copy.deepcopy(labels)
        client = self.kubemgr.get_cluster_client(cluster_name)
        if client is None:
            return Result('', CLUSTER_SSL_ERROR, 'get kube client failed', 400)
        set_labels = client.set_labels(host_name, labels)
        if not set_labels.success:
            Log(1, "set label error:{}".format(set_labels.message))
            return Result('', set_labels.result, set_labels.message, 500)
        WebLog(3, "更新", "主机标签[{}]".format(f_labels), username)
        return Result('')

    def set_defend(self, cluster_name, host_name, host_type, host_ip, username):
        """
        设置主机维护模式
        :param cluster_name:
        :param host_name:
        :param username:
        :return:
        """
        kubecli = self.kubemgr.get_cluster_client(cluster_name)
        if kubecli is None:
            return Result('', CLUSTER_SSL_ERROR, 'get kube client failed', 400)

        if not host_name:
            rlt = LauncherClient.instance().get_host_info(cluster_name, host_type, host_ip)
            if not rlt.success:
                return rlt
            data_info = rlt.json_data()
            host_name = data_info.get('hostname', '')

        is_sche = kubecli.is_unschedulable(host_name)
        if not is_sche.success:
            return Result('', is_sche.result, is_sche.message, 500)

        status = False if is_sche.content else True
        Log(3, "set defend:{}".format(status))
        st = kubecli.change_schedulable(host_name, status)
        if not st.success:
            return Result('', st.result, st.message, 500)
        WebLog(3, u'修改', u"%s维护模式" % host_name, username)

        # 更新etcd中数据
        status = 1 if status else ''
        CluNodedb.instance().update_node(cluster_name, host_ip.replace('.', '-'), {"unschedulable": status})

        self.reload(flush=1)
        return Result('')

    def get_lables_host(self, cluster_name, host_name):
        """
        获取单个主机上的标签
        :param cluster_name:
        :param host_name:
        :return:
        """
        # rlt = CluNodedb.instance().read_node(cluster_name, host_name)

        client = self.kubemgr.get_cluster_client(cluster_name)
        if client is None:
            return Result('', CLUSTER_SSL_ERROR, 'get kubeclient failed', 400)
        rlt = client.get_node_labels(host_name)
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 500)
        return Result(rlt.content)

    def get_labels(self, workspace_name):
        """
        获取workspace所在集群的标签
        :param group_name:组名
        :param workspace_name:workspace名称
        :return:
        """
        ws = WorkSpacedb.instance().read_workspace(workspace_name)
        if not ws.success:
            return ws

        kubeclient = self.kubemgr.get_cluster_client(ws.content.get('cluster_name'))
        if kubeclient is None:
            return Result('', CLUSTER_SSL_ERROR, '', 400)
        rlt = kubeclient.get_all_labels()
        if not rlt.success:
            return rlt
        return Result(rlt.content)

    def passphrase(self):
        return "123456"

    def ssh_command(self, host_ip, command):
        """
        :param cluster_name:
        :param host_name:
        :param host_type:
        :param host_ip:
        :param command:
        :return:
        """

        # remot = RemoteParam(host_ip)
        # return remot.process_command(command)

        # p = multiprocessing.Pool()
        # remot = RemoteParam(host_ip)
        # result = p.apply_async(remot.command, args=(command,))
        # p.close()
        # p.join()
        # Log(3, "result.get():{}".format(result.get(2)))
        # return result.get()
        rlt = Masterdb.instance().read_master(host_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        con = rlt.content
        if not con:
            return Result('', 400, 'not found the host', 400)
        username = con.get('username', None)
        passwd = con.get('userpwd', None)
        prikey = con.get('prikey', None)
        prikeypwd = con.get('prikeypwd', None)
        port = int(con.get('port', 22))

        remot = RemoteParam(host_ip, port, username, passwd, prikey, prikeypwd)
        rlt = remot.create_sshclient()
        if not rlt.success:
            return rlt

        rlt = remot.exec_command(command)
        if not rlt.success:
            remot.close()
            return rlt
        remot.close()

        return rlt

    def get_all_node(self):
        """
        获取所有主机
        只获取通过ufleet添加的主机(知道主机的用户名和密码)
        :return:
        """
        # nodes_info = Masterdb.instance().read_masternode_map(key=None)
        # if not nodes_info.success:
        #     return Result('', nodes_info.result, nodes_info.message, 500)
        # data_info = {}
        #
        # nodes_info = nodes_info.content
        # for k, v in nodes_info.items():
        #     key = k.split('/')[-1]
        #     if v:
        #         if v.get('username', ''):
        #             data_info[key] = v
        # return Result(data_info)
        d = {}
        nodes = self.__store.get('all_nodes', [])
        for i in nodes:
            if i.get('status') == 'running':
                d[i['ip'].replace('.', '-')] = i
        return Result(d)

    def add_cluster_member(self, d, passport):
        """
        :param post_data:
        :param username:
        :return:
        """
        cluster_name = d.get('cluster_name')
        if not cluster_name:
            return Result('', 400, 'param error', 400)
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_clu_mem_permission(passport.get('username'), cluster_name)
            if not rlt.success or not rlt.content:
                return rlt

        rlt = self.cludb.add_member(d.get('cluster_name'), d.get('member', []))
        if not rlt.success:
            return rlt

        WebLog(3, u'修改', u"集群%s成员[%s]" % (d.get('cluster_name'), d.get('member')), passport.get('username'))
        self.reload(flush=1)
        return Result('')

    def del_cluster_member(self, cluster_name, member, passport):
        """
        :param username:
        :param post_data:
        :return:
        """
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_clu_mem_permission(passport.get('username'), cluster_name)
            if not rlt.success or not rlt.content:
                return rlt

        rlt = self.cludb.del_member(cluster_name, member)
        if not rlt.success:
            return rlt
        WebLog(3, u'删除', u"集群%s成员[%s]" % (cluster_name, member), passport.get('username'))
        self.reload(flush=1)
        return Result('')

    def get_cluster_member(self, cluster_name):
        """
        :return:
        """
        v = self.cluster_info_lo(cluster_name)
        if v:
            return Result(v.get('member', ''))
        else:
            return Result('')

    def is_open(self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((ip, int(port)))
            s.shutdown(2)
            print '{} is open'.format(port)
            return True
        except:
            print '%d is down' % port
            return False

    def get_ports(self, d):
        """
        cluster_name
        :param d:
        :return:
        """
        self.reload()
        g = d.get('group', '')
        w = d.get('workspace', '')
        if not g or not w:
            return Result('', msg='request param error', code=400, result=400)

        ws = WorkSpacedb.instance().read_workspace(w)
        if not ws.success:
            return ws

        kubeclient = self.kubemgr.get_cluster_client(ws.content.get('cluster_name'))
        if kubeclient is None:
            return Result('', CLUSTER_SSL_ERROR, '', 400)

        # 获取service
        rlt = kubeclient.get_service_list()
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 500)

        data = rlt.content
        return_data = {'NodePort': []}
        for i in data:
            if i.get('spec', {}).get('type') == 'NodePort':
                return_data['NodePort'] += i.get('spec', {}).get('ports')
        return Result(return_data)

    def node_monitor(self, d):
        """
        主机监控
        :param d:
        :return:
        """
        host = d.get('host_ip').replace('.', '-')
        if not host:
            return Result([])
        monitor_info = Monitordb.instance().read_moniternode_map(host)
        if not monitor_info.success:
            return Result('', monitor_info.result, monitor_info.message, 500)

        d_s = sorted(monitor_info.content.values(), key=lambda s: s['datetime'])

        # 返回两个小时内的数据
        d_s = d_s[-121:]
        for index, v in enumerate(d_s):
            if not index:
                continue
            # 单位： byte/s 每秒字节数，如果换算成KB,除以1000
            rx_tx_1 = v['network']['rx'] + v['network']['tx']
            rx_tx_2 = d_s[index - 1]['network']['rx'] + d_s[index - 1]['network']['tx']
            t_ = (v['datetime'] - d_s[index - 1]['datetime'])
            if t_:
                v['network']['aver_bytes'] = round((rx_tx_1 - rx_tx_2) / t_, 2)
                s = v['anlycpu']['num_all'] - d_s[index - 1]['anlycpu']['num_all']
                t = v['anlycpu']['idle_all'] - d_s[index - 1]['anlycpu']['idle_all']
                v['cpu'] = round(100 * (s - t) / s, 2)

        if d_s:
            d_s.remove(d_s[0])
        return Result(d_s)

    def get_all_member(self, passport):
        self.reload()
        member = {}
        for k, v in self.__store['clu_dic'].items():
            if passport.get('username') in v.get('member', []):
                member[k] = 1
            else:
                member[k] = 0
        return Result(member)

    def get_ws_events(self, group, ws_name, start_time, end_time, offset, limit):
        data_list = []
        ws_list = []
        if not ws_name:
            rlt = WorkSpacedb.instance().get_ws_by_group(group)
            if not rlt.success:
                return rlt
            for i in rlt.content:
                ws_list.append(i.get('name', ''))
        else:
            ws_list.append(ws_name)

        Log(3, "ws_list:{}".format(ws_list))
        for ws in ws_list:
            rlt = WorkSpacedb.instance().read_workspace(ws)
            if rlt.success and rlt.content:
                client = self.kubemgr.get_cluster_client(rlt.content.get('cluster_name', ''))
                if client:
                    events = client.ns_events(ws)
                    if events.success:
                        for i in events.content:
                            t1 = i.get('metadata', {}).get('creationTimestamp', '')
                            if t1:
                                t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
                                t3 = utc2local(t2)
                                # add_date = datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")
                                i['create_time'] = t3
                        data_list.extend(events.content)
        data_list = sorted(data_list, key=lambda s: s['create_time'])

        start_time1 = ''
        end_time1 = ''
        if start_time and end_time:
            try:
                start_time1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_time1 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return Result('', 400, 'the start_time or end_time not format "%Y-%m-%d %H:%M:%S"', 400)
        r_data = []
        for i, x in enumerate(data_list):
            if start_time1 and end_time1:
                if start_time1 <= x['create_time'] <= end_time1:
                    x['create_time'] = datetime.datetime.strftime(x['create_time'], "%Y-%m-%d %H:%M:%S")
                    r_data.append(x)
            else:
                x['create_time'] = datetime.datetime.strftime(x['create_time'], "%Y-%m-%d %H:%M:%S")
                r_data.append(x)
        p1, p2 = divmod(len(r_data), limit)
        if p2:
            page_num = p1 + 1
        else:
            page_num = p1

        d = {'page_num': page_num, 'events': r_data[(offset - 1) * limit:limit * offset]}
        Log(3, "get_events:{}, page_num:{}".format(len(r_data), len(r_data) / limit))
        return Result(d)

    def get_hosts_by_ns(self, workspace):
        rlt = WorkSpacedb.instance().read_workspace(workspace)
        if not rlt.success:
            return rlt
        clu_name = rlt.content.get('cluster_name')
        return self.get_node(clu_name)

    def change_evction_status(self, clu_name, host_ip):
        # 设置主机的应用迁移状态
        rlt = CluNodedb.instance().update_node(clu_name, host_ip.replace('.', '-'),
                                               {"is_eviction": 1, "eviction_status": "ongoing"})
        if not rlt.success:
            Log(1, "update node:{}, eviction status error:{}".format(host_ip, rlt.message))
        self.reload(1)
        return Result(0)

    def set_eviction(self, clu_name, host_ip, host_name):
        """
        :param clu_name:
        :param host_ip:
        :return:
        """
        rlt = WorkSpacedb.instance().get_ns_by_cluster(clu_name)
        if not rlt.success:
            return rlt

        ws_list = [i.get('name') for i in rlt.content]

        client = KubeClientMgr.instance().get_cluster_client(clu_name)
        if not client:
            return Result('', 400, 'get kubeclient error.', )

        # 先检查主机是否是维护模式
        is_sche = client.is_unschedulable(host_name)
        if not is_sche.success:
            return Result('', is_sche.result, is_sche.message, 500)

        if not is_sche.content:
            # 先将主机设置成维护模式
            st = client.change_schedulable(host_name, True)
            if not st.success:
                return st

        rlt = client.host_all_pods(host_name)
        if not rlt.success:
            return rlt
        for pod in rlt.content.get('items', []):
            ns = pod.get('metadata', {}).get('namespace')
            pod_name = pod.get('metadata', {}).get('name')
            if pod.get('status', {}).get('hostIP') == host_ip and ns in ws_list:
                client.eviction(ns, pod_name)
            if ns == 'kube-system' and pod_name.startswith('calico-policy'):
                client.eviction(ns, pod_name)
        self.reload(1)
        return Result(0)

    def host_online(self, clu_name, host_ip, host_name):
        """
        :param clu_name:
        :param host_ip:
        :return:
        """
        rlt = CluNodedb.instance().update_node(clu_name, host_ip.replace('.', '-'),
                                               {"is_eviction": 0, "eviction_status": "", "unschedulable": ""})
        if not rlt.success:
            Log(1, 'set host online error:{}'.format(rlt.message))

        client = KubeClientMgr.instance().get_cluster_client(clu_name)
        if not client:
            return Result('', 400, 'get kubeclient error.', )
        # 先检查主机是否是维护模式
        is_sche = client.is_unschedulable(host_name)
        if not is_sche.success:
            return Result('', is_sche.result, is_sche.message, 500)

        if is_sche.content:
            # 先将主机设置成非维护模式
            st = client.change_schedulable(host_name, False)
            if not st.success:
                return st

        self.reload(1)
        return Result(0)

    def test_apiserver(self, kwargs):
        """
        测试apiserver
        :param cluster_name:
        :param host_name:
        :param url:
        :return:
        """
        try:
            cluster_name = kwargs.get('cluster_name')
            url = kwargs.get('url')
            version = kwargs.get('version', 'v1')
            base = kwargs.get('base', '/api')
            client = self.kubemgr.get_cluster_client(cluster_name)
            if not client:
                return Result('', 400, 'connect the apiserver error', 400)
            return client.test_apiserver(url, version, base)
        except Exception as e:
            PrintStack()
            return Result('', 500, e.message)

    def test_etcd(self):
        data = {
            'read_list0': WorkSpacedb.instance().read_all_workspace().content,
            'read_list': Networkdb.instance().read_list('clu4').content,
            'read_key_list': self.cludb.read_key_list().content,
            'read_map': self.cludb.read_map().content,

        }
        return Result(data)
