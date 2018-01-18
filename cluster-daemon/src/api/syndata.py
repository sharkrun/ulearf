# -*- coding: utf-8 -*-
"""
"""
from __future__ import division
from core.const import ETCD_ROOT_PATH
from frame.logger import Log, PrintStack
import datetime
import time
from common.commcluster import syn_nodeinfo
from common.util import Result
from core.deployclient import DeployClient
from etcddb.nodemgr import CluNodedb
from etcddb.clustermgr import Clusterdb
from etcddb.workspacemgr import WorkSpacedb
from core.kubeclientmgr import KubeClientMgr
from core.errcode import CLU_IS_PENDING, ETCD_KEY_NOT_FOUND_ERR
import Queue
from common.inter import Factory
from core.launcherclient import LauncherClient
import json


# def utc2local(utc_st):
#     """UTC时间转本地时间（+8:00）"""
#     now_stamp = time.time()
#     local_time = datetime.datetime.fromtimestamp(now_stamp)
#     utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
#     offset = local_time - utc_time
#     local_st = utc_st + offset
#     return local_st


class SynDataFac(object):
    def __init__(self, cluster_name, node, client, ws_list):
        self.root = ETCD_ROOT_PATH + '/clustermanages/'
        self.cluster_name = cluster_name
        self.node = node
        self.client = client
        self.status = 0
        self.ws_list = ws_list

    def node_ready_pods_num(self, pods_list):
        pod_num = 0
        daemonset_pod = 0
        for pod in pods_list:
            # DaemonSet
            if pod.get('metadata', {}).get('namespace') in self.ws_list:
                conditions = pod.get('status', {}).get('conditions', [])
                for k in conditions:
                    if k.get('type', '') == 'Ready':
                        if k.get('status') == 'True':
                            pod_num += 1
                            for m in pod.get('metadata', {}).get('ownerReferences', []):
                                if m.get('kind') == 'DaemonSet':
                                    daemonset_pod += 1
                                    break
                        break
        return pod_num, daemonset_pod

    def check_host_status(self):
        # 检查主机状态 master: kube-scheduler, kube-controller-manager, kube-dns, calico-node
        # node:
        if self.node['type'] == 'master':
            rlt = self.client.ns_pods('kube_system')
            if not rlt.success:
                return
            s_list = []
            for i in rlt.content:
                if 'calico-node' in i.get('metadata', {}).get('labels', {}).values():
                    s_list.append({'pod_type': 'calico-node', 'status': i.get('status', {}).get('phase', '')})
                if 'kube-controller-manager' in i.get('metadata', {}).get('labels', {}).values():
                    s_list.append(
                        {'pod_type': 'kube-controller-manager', 'status': i.get('status', {}).get('phase', '')})
                if 'kube-dns' in i.get('metadata', {}).get('labels', {}).values():
                    s_list.append({'pod_type': 'kube-dns', 'status': i.get('status', {}).get('phase', '')})
                if 'kube-scheduler' in i.get('metadata', {}).get('labels', {}).values():
                    s_list.append({'pod_type': 'kube-scheduler', 'status': i.get('status', {}).get('phase', '')})
        else:
            rlt = self.client.ns_pods()

    def component_statuses(self):
        """
        #~ kubectl get componentstatus
        检查master的状态  scheduler controller-manager etcd-0
        :param client:
        :param clu_name:
        :return:
        """
        rlt = self.client.clu_status()
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

    def run(self):
        """
        :return:
        """
        t1 = time.time()
        Log(4, 'syndata #run.. cluster_name:{},node:{}, time:{}'.format(self.cluster_name, self.node,
                                                                        datetime.datetime.now()))

        # 获取主机上pod个数
        rlt = self.client.get_node_pods(self.node.get('name', ''))
        if rlt.success:
            new_pod_num, daemonset_pod_num = self.node_ready_pods_num(rlt.content)
        else:
            new_pod_num, daemonset_pod_num = self.node.get('pod_num'), 0

        # 获取主机信息
        rlt = self.client.get_node_info(self.node.get('name', ''))
        if not rlt.success:
            self.status = 1
            return
        new_node_info = rlt.content

        m_s_info = dict()
        # 检查主机作为master的状态
        if self.node['type'] == 'master':
            m_s_info = self.component_statuses()
            Log(4, "node:{} m_status..............:{}".format(self.node['ip'], m_s_info))

        # 比较node信息是否发生变化
        update_node = syn_nodeinfo(self.node, new_node_info, m_s_info)
        Log(4,
            "node:{},old pod num:{}, new pod num:{}, daemonset_pod_num:{}".format(self.node['ip'], self.node['pod_num'],
                                                                                  new_pod_num, daemonset_pod_num))

        if new_pod_num != self.node.get('pod_num', 0):
            update_node['pod_num'] = new_pod_num

        # drain status
        old_evction = self.node.get('is_eviction')
        if old_evction:
            if new_pod_num - daemonset_pod_num > 0 and self.node.get('eviction_status') != 'ongoing':
                update_node['eviction_status'] = 'ongoing'
            if new_pod_num - daemonset_pod_num == 0 and self.node.get('eviction_status') != 'finished':
                update_node['eviction_status'] = 'finished'

        # 更新etcd中数据
        if update_node:
            ip_name = self.node['ip'].replace('.', '-')
            Log(3, "node:{},update_node:{}".format(self.node['ip'], update_node))
            rlt = CluNodedb.instance().update_node(self.cluster_name, ip_name, update_node)
            if not rlt.success:
                Log(1, "update_node error:{}".format(rlt.message))

        Log(3, "syndata runing finished. node:{},cost:{}".format(self.node.get('ip'), time.time() - t1))
        self.status = 1
        return

    def is_finished(self):
        return self.status > 0


class SynData(object):
    """
    同步apiserver数据到etcd中
    """

    def __init__(self):
        super(SynData, self).__init__()
        self.task_queue = Queue.Queue()
        self.root = ETCD_ROOT_PATH + '/clustermanages/'
        self.__init_thread_pool(5, 'SynData')

    def __init_thread_pool(self, thread_num, schedule_name):
        while thread_num:
            name = "%s_%s" % (schedule_name, thread_num)
            thread_num -= 1
            Factory(self.task_queue, name)  # 执行队列中的任务

    def syn_apply_num(self, clu_name, clu_gws, apply_num):
        deploy = DeployClient.instance().get_apply_num(clu_name, clu_gws)
        if apply_num != deploy.content:
            return Clusterdb.instance().update_apply_num(clu_name, deploy.content)
        return Result('')

    def change_node_status(self, nodes_dir, message):
        """
        修改主机的状态从running为error
        :param nodes_dir:
        :return:
        """
        for k, v in nodes_dir.items():
            if v['status'] == 'running':
                Log(2,
                    "syndata clu[{}] status is error. change node[{}] status to error:{}".format(v['cluster_name'],
                                                                                                 v['ip'], message))
                CluNodedb.instance().update_node(v['cluster_name'], k, message)

    def parse_json(self, info):
        try:
            a = json.loads(info)
        except ValueError:
            return None, False
        else:
            return a, True

    def syn_vip(self, clu_name):
        """
        获取cluster的vip
        :param clu_name:
        :return:
        """
        rlt = LauncherClient.instance().get_cluster_info(clu_name)
        if not rlt.success:
            Log(1, "syn_vip get_cluster_info error:{}".format(rlt.message))
            return
        json_data, s = self.parse_json(rlt.content.get('info'))
        if not s:
            Log(1, "syn_vip cluster_info can not parse to json:{}".format(rlt.content.get('info')))
            return
        vip = json_data.get('vip')

        rlt = Clusterdb.instance().get_vip(clu_name)
        if rlt.success:
            vip0, s = self.parse_json(rlt.content)
            if not s:
                Log(1, "syn_vip the info can not parse to json:{}".format(rlt.content))
                return
        else:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                vip0 = ''
            else:
                Log(1, "syn_vip can get vip error:{}".format(rlt.message))
                return

        if vip != vip0:
            Clusterdb.instance().save_vip(clu_name, {'vip': vip})
        return

    # 向队列中投放任务
    def timeout(self):
        try:
            Log(3, "syndata  #timeout start at:{}".format(datetime.datetime.now()))
            if not CluNodedb.instance().ismaster():
                Log(3, "syndata this node is not master")
                return

            # 当队列中有任务不添加
            if self.task_queue.qsize():
                Log(3, "syndata timeout task_queue.qsize:{},".format(self.task_queue.qsize()))
                return

            clu_apply_num = {}
            rlt1 = Clusterdb.instance().read_clu_map()
            if not rlt1.success:
                Log(1, "syndata timeout rlt1.message:{}".format(rlt1.message))
                return
            for c, v in rlt1.content.items():
                sp_key = c.split('/')
                if sp_key[-1] == 'apply_num':
                    clu_apply_num[sp_key[-2]] = v

            clu_node = {}
            rlt = CluNodedb.instance().read_clunode_map(pass_nll_value=False)
            if not rlt.success:
                return Result('', rlt.result, rlt.message, 500)

            if rlt.success:
                for k, v in rlt.content.items():
                    sp_key = k.split('/')
                    if len(sp_key) == 6:
                        clu_node.setdefault(sp_key[4], {})[sp_key[5]] = v
                    if len(sp_key) == 5:
                        clu_node.setdefault(sp_key[4], {})
            # apply_num个数的参数
            clu_ws = WorkSpacedb.instance().read_gws()
            if not clu_ws.success:
                Log(3, "syndata timeout ws :{}".format(clu_ws.message))
                return

            for clu_name, nodes in clu_node.items():
                # 只同步有主机的集群
                if not nodes:
                    continue

                # 更新k8s集群的vip
                # self.syn_vip(clu_name)

                # 同步更新集群应用个数
                syn_clu = self.syn_apply_num(clu_name, clu_ws.content.get(clu_name, []), clu_apply_num.get(clu_name, 0))
                if not syn_clu.success:
                    Log(1, "syndata clu_info apply_num error:{}".format(syn_clu.message))

                # 当apiserver连接不上时，表明集群异常(可能是刚添加，也可能是添加成功后出现异常)，需要修改主机的状态
                rlt = KubeClientMgr.instance().get_cluster_client(clu_name)
                if not rlt.success:
                    Log(3, "rlt.message:{}".format(rlt.message))
                    # 如果集群状态是pending则不执行检查任务
                    if rlt.result == CLU_IS_PENDING:
                        return
                    check_num = 3
                    while check_num:
                        Log(3, "check_num:{}, clu_name:{}, node:{}".format(check_num, clu_name, len(nodes)))
                        rlt = KubeClientMgr.instance().get_cluster_client(clu_name)
                        if rlt.success:
                            break
                        check_num -= 1
                        time.sleep(0.5)
                    if check_num == 0:
                        self.change_node_status(nodes, {'status': 'error', 'message': rlt.message, 'pod_num': 0})
                        continue

                client = rlt.content

                gws = clu_ws.content.get(clu_name, [])
                ws_list = []
                for i in gws:
                    ws_list.extend(i.get('workspace', []))

                for n in nodes.values():
                    if not n['name']:
                        rlt = LauncherClient.instance().get_host_name(clu_name, n['type'] + 's', n['ip'])
                        if not rlt.success:
                            continue
                        host_name = rlt.content
                        ip_name = n['ip'].replace('.', '-')
                        rlt = CluNodedb.instance().update_node(clu_name, ip_name, {'name': host_name})
                        if not rlt.success:
                            Log(1, "update_node error:{}".format(rlt.message))
                        n['name'] = host_name
                    task = SynDataFac(clu_name, n, client, ws_list)
                    self.create_task(task)
            Log(3, "syndata create task all done at:{}".format(datetime.datetime.now()))
            return True
        except Exception as e:
            Log(1, "sysdata error:{}".format(e.message))
            PrintStack()
            return None
        except KeyboardInterrupt:
            Log(3, "syndata timeout be killed")
            return None

    def create_task(self, task):
        Log(4, "syndata create task:{}".format(task.node))
        self.task_queue.put(task)