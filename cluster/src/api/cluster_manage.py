# -*- coding: utf-8 -*-
# Copyright (c) 2017  the ufleet
import json
import re

from twisted.internet import threads
from twisted.web import http

from common.decorators import list_route
from common.util import Result
from core.cluster_managemgr import ClusterManageMgr
from core.errcode import INVALID_JSON_DATA_ERR, \
    PARAME_IS_INVALID_ERR, INVALID_PARAM_ERR, FAIL, DISK_IS_IN_USE_ERR, ETCD_KEY_NOT_FOUND_ERR, \
    INTERNAL_EXCEPT_ERR
from core.kubeclientmgr import KubeClientMgr
from core.networkmgr import NetworkMgr
from core.storagemgr import StorageMgr
from etcddb.configmapmgr import ConfigMapdb
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from etcddb.monitormgr import Monitordb
from etcddb.storage.disk import DiskDB
from frame.authen import ring8, ring0, ring5, ring3
from frame.configmgr import GetSysConfig
from frame.logger import Log, PrintStack


# from twisted.internet import reactor
class Cluster(object):
    """
    实现集群管理功能  集群添加，集群列表查看，集群详情
    """

    def __init__(self):
        self.clumgr = ClusterManageMgr()
        self.kubemgr = KubeClientMgr.instance()
        print 'cluster start....'

    def _is_name_valid(self, cluster_name):
        m = re.match(r"^\w[-\w]*\w$", cluster_name)
        if m:
            return True
        return False

    # 异步接口的回调函数
    def callback(self, r, *k):
        Log(4, "callback.......,content:{}, request:{}".format(r, k))

    def error_callback(self, failure):
        try:
            Log(1, "error_callback:{}".format(str(failure)))
        except Exception:
            PrintStack()

    @ring0
    @ring3
    @list_route(methods=['POST'])
    def create(self, post_data, **kwargs):
        """
        创建集群
        :param kwargs:
        :return:
        """
        try:
            data_info = json.loads(post_data.replace("'", "\'"))
            cluster_name = data_info.get('cluster_name', '')
            if not self._is_name_valid(cluster_name):
                return Result('', PARAME_IS_INVALID_ERR, 'cluster_name is invalid', http.BAD_REQUEST)
            Log(3, "create passport:{}".format(kwargs.get('passport', {})))
            data_info['creater'] = kwargs.get('passport', {}).get('username', '')
            rlt = self.kubemgr.create_new_cluster(data_info, kwargs.get('passport', {}))
            if not rlt.success:
                return Result('', rlt.result, rlt.message, 400)

            if 'addr' in data_info and data_info['addr']:
                master_ip = data_info['addr'].split(':')[0]
                rlt = StorageMgr.instance().init_storage_cluster(cluster_name, master_ip)
                if not rlt.success:
                    Log(1, 'Cluster.create init_storage_cluster[%s][%s] fail,as[%s]' % (
                        cluster_name, master_ip, rlt.message))

            self.clumgr.reload(flush=1)
            return Result('')
        except Exception, e:
            Log(1, "cluster create error:{}".format(e))
            PrintStack()
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def delete_cluster(self, **kwargs):
        """
        # 删除集群集群,如果有资源则不让删除
        # 删除k8s存储集群，如果只剩最后一个集群，则删除失败
        :param post_data:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', None)
        username = kwargs.get('passport', {}).get('username', 'unknown')
        if cluster_name is None:
            return Result(0, msg='request error', code=400)

        rlt = self.clumgr.delete_cluster(cluster_name=cluster_name, username=username)
        if rlt.success:
            StorageMgr.instance().delete_storage_cluster(cluster_name)
        else:
            Log(1, 'delete_cluster[%s][%s] fail,as[%s]' % (username, cluster_name, rlt.message))
        return rlt

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def list(self, **kwargs):
        """
        # 获取集群的列表
        :return:
        """
        try:
            offset = kwargs.get('offset', 0)
            limit = kwargs.get('limit', None)
            passport = kwargs.get('passport', {})
            userid = passport.get('ring')
            username = passport.get('username')
            return self.clumgr.get_cluster_list(limit=limit, offset=int(offset), userid=userid, username=username)
        except Exception, e:
            PrintStack()
            Log(1, "cluster list,error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def add_master(self, post_data, **kwargs):
        """
        # 添加master主机：管理主机(master)
        :return:
        """
        try:
            re_data = json.loads(post_data.replace("'", "\'"))
            passport = kwargs.get('passport', {})
        except Exception as e:
            Log(1, "add_cluster.parse data to json fail.input[%s]" % (post_data))
            return Result('', INVALID_JSON_DATA_ERR, str(e))

        if not self._is_name_valid(re_data.get("Name", "")):
            return Result('', PARAME_IS_INVALID_ERR, 'cluster_name is invalid', http.BAD_REQUEST)

        rlt = self.clumgr.add_master(re_data, passport)
        if not rlt.success:
            Log(1, 'Cluster.add_master add_master[%s][%s] fail,as[%s]' % (
                re_data.get("ClusterName", ""), re_data.get("HostIP", ""), rlt.message))
            return rlt

        self.clumgr.reload(flush=1)

        rlt = StorageMgr.instance().init_storage_cluster(re_data.get("Name", ""), re_data.get('Masters', []))
        if not rlt.success:
            Log(1,
                'Cluster.add_master init_storage_cluster[%s][%s] fail,as[%s]' % (
                    re_data.get("Name", ""), re_data.get("Masters", []), rlt.message))
        return Result('')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def add_node(self, post_data, **kwargs):
        """
        # 添加node
        # 判断创建主机是否创建成功的的方法：1.看http://192.168.14.166:31886/clusters/kubernetes-1/masters返回的数据的value中是否有
        kubeletstatus和apiserverstatus这两个key，并且状态都是true
        :return:
        """
        try:
            node_info = json.loads(post_data.replace("'", "\'"))
            passport = kwargs.get('passport', {})
            # creater = kwargs.get('passport', {}).get('username')
            cluster_name = node_info.get("ClusterName", "")
            host_ip = node_info.get("HostIP", "")
            rlt = self.clumgr.add_node(node_info, passport)
            if not rlt.success:
                Log(1, "cluster add node error:{}".format(rlt.message))
                return rlt

            rlt = StorageMgr.instance().add_storage_node(cluster_name, host_ip)
            if not rlt.success:
                Log(1, 'Cluster.add_node add_storage_node[%s][%s] fail,as[%s]' % (cluster_name, host_ip, rlt.message))

            return Result('ok')
        except Exception as e:
            PrintStack()
            Log(1, "add_node:{}".format(e))
            return Result('', INVALID_JSON_DATA_ERR, str(e))

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def remove_node(self, **kwargs):
        """
        # 删除工作主机node
        # 清除主机上的数据
        # 从存储集群删除存储节点
        """
        cluster_name = kwargs.get('cluster_name', None)
        node_name = kwargs.get('node_name', None)
        passport = kwargs.get('passport', {})
        username = kwargs.get('passport', {}).get('username', 'unknown')
        host_real_name = kwargs.get('name', '')
        force_remove = kwargs.get('force', False)
        if not force_remove and DiskDB.instance().count_disk_num(node_name) > 0:
            return Result('', DISK_IS_IN_USE_ERR, 'Please delete umount disk first.')

        if cluster_name and node_name:
            rlt = self.clumgr.remove_node(cluster_name, node_name, host_real_name, passport)
            if not rlt.success:
                Log(1, 'remove_node[%s][%s][%s] fail,as[%s]' % (username, node_name, cluster_name, rlt.message))
            else:
                StorageMgr.instance().delete_storage_node(cluster_name, node_name, username)

            return rlt

        else:
            return Result('', msg='the parame  is error', result=PARAME_IS_INVALID_ERR, code=400)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def remove_master(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', None)
        passport = kwargs.get('passport', {})
        master_name = kwargs.get('master_name', None)
        host_ip = master_name.replace('-', '.')
        host_real_name = kwargs.get('name', '')
        rlt = self.clumgr.remove_master(cluster_name, host_ip, host_real_name, passport)
        if rlt.success:
            StorageMgr.instance().delete_storage_cluster(cluster_name)
        else:
            Log(1, 'remove_master[%s][%s][%s] fail,as[%s]' % (
            passport.get('username'), master_name, cluster_name, rlt.message))

        return rlt

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_one_cluster(self, **kwargs):
        """
        获取第一个成功的集群信息
        :param :
        :return:
        """
        try:
            return self.clumgr.one_cluster()
        except Exception, e:
            return Result('', FAIL, str(e))

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_cluster(self, **kwargs):
        """
        # 获取单个集群的信息
        :param kwargs:
        :return:
        """
        try:
            cluster_name = kwargs.get('cluster_name', '')
            flush = kwargs.get('flush', '0')
            return self.clumgr.get_cluster(cluster_name, flush)
        except Exception, e:
            PrintStack()
            Log(1, "get_cluster,error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def list_node(self, **kwargs):
        """
        获取主机列表
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        return self.clumgr.get_node(cluster_name=cluster_name)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_error_node_reason(self, **kwargs):
        """
        查看主机添加失败的原因
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_type = kwargs.get('host_type', '')
        ip = kwargs.get('ip', '')
        rlt = self.clumgr.error_reason(cluster_name, ip, host_type)
        if not rlt.success:
            return Result('', 400, rlt.message, 400)
        else:
            return Result(rlt.content)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_host_progress(self, **kwargs):
        """
        查看主机添加的进度
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_type = kwargs.get('host_type', '')
        ip = kwargs.get('ip', '')
        rlt = self.clumgr.host_progress(cluster_name, ip, host_type)
        if not rlt.success:
            return Result('', 400, rlt.message, 400)
        else:
            return Result(rlt.content)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def list_pod(self, **kwargs):
        """
        获取pod列表
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_name = kwargs.get('host_name', '')
        return self.clumgr.get_pod(
            cluster_name=cluster_name, host_name=host_name)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def list_workspace(self, **kwargs):
        """
        获取一个集群上面的所有工作区
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        return self.clumgr.workspace_list(cluster_name=cluster_name)

    @ring5
    @ring3
    @ring0
    @ring8
    @list_route(methods=['GET'])
    def authenticat(self, **kwargs):
        """
        获取集群的认证信息
        :param kwargs:
        :return:
        """
        workspace = kwargs.get('workspace', '')
        rlt = self.clumgr.get_cluster_auth(workspace)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('', 400, 'the workspace [{}] is not existed'.format(workspace), 404)
            else:
                return rlt
        return Result(rlt.content)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_auth(self, **kwargs):
        """
        get auth by cluster_name
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name')
        if not cluster_name:
            return Result('', 400, 'param error', 400)
        rlt = self.clumgr.get_auth(cluster_name)
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 400)
        return Result(rlt.content)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def cluster_overview(self, **kwargs):
        """
        集群的概览
        已经实现
        :param:
        :return:
        """
        return self.clumgr.cluster_overview()

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def node_overview(self, **kwargs):
        """
        主机的概览
        已经实现
        :param :
        :return:
        """
        return self.clumgr.node_overview()

    # @ring5
    # @ring3
    # @ring0
    # @list_route(methods=['GET'])
    # def pod_overview(self, **kwargs):
    #     """
    #     pod的概览
    #     :param :
    #     :return:
    #     """
    #     return self.clumgr.pod_overview()

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_cluster_by_space(self, **kwargs):
        """
        通过workspace获取集群名称
        :param kwargs:
        :return:
        """
        workspace_name = kwargs.get('workspace_name', None)
        if workspace_name:
            return self.clumgr.get_cluster_by_space(
                workspace_name=workspace_name)
        else:
            return Result('', msg='param error', result=400, code=400)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def container_monitor(self, **kwargs):
        """
        容器监控
        :param kwargs:
        :return:
        """
        try:
            container_id = kwargs.get('containerID', None)
            host_ip = kwargs.get('ip', None)
            if container_id and host_ip:
                return self.clumgr.data_anly(container_id, host_ip)
            else:
                return Result('', msg='invalid param', result=400, code=400)
        except Exception as e:
            PrintStack()
            return Result('', msg=e, result=500, code=500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_current_host(self, **kwargs):
        """
        获取当前主机的ip
        :return:
        """
        current_host = GetSysConfig('current_host')
        return Result('http://' + current_host)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def set_label(self, post_data, **kwargs):
        """
        给主机设置标签：添加或者删除标签
        已实现
        :param kwargs:
        :return:
        """
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception as e:
            Log(1,
                "set_label.parse data to json fail.input[%s]" % (post_data))
            return Result('', INVALID_JSON_DATA_ERR, str(e))
        cluster_name = data.get('cluster_name', '')
        host_name = data.get('host_name', '')
        labels = data.get('labels', {})
        username = kwargs.get('passport', {}).get('username', 'unknown')
        return self.clumgr.set_label(
            cluster_name=cluster_name,
            host_name=host_name,
            labels=labels,
            username=username)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_labels(self, **kwargs):
        """
        获取一个集群上所有lables
        :param kwargs: workspace_name,group_name
        :return: {"labels":[]}
        """
        workspace_name = kwargs.get('workspace_name', '')
        if not workspace_name:
            return Result('', 400, 'param error', 400)
        rlt = self.clumgr.get_labels(workspace_name)
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 500)
        return Result(rlt.content)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_labels_host(self, **kwargs):
        """
        通过集群的主机获取标签
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_name = kwargs.get('host_name', '')
        return self.clumgr.get_lables_host(cluster_name, host_name)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def set_defend(self, **kwargs):
        """
        设置主机是否为维护模式
        当status为1,设置主机为维护模式，否则为非维护模式
        已实现
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_name = kwargs.get('host_name', '')
        host_type = kwargs.get('host_type', '')
        host_ip = kwargs.get('host_ip', '')
        status = kwargs.get('status', '')
        username = kwargs.get('passport', {}).get('username', 'unknown')
        if status != '0' and status != '1':
            return Result('invalid param {},type:{}'.format(status, type(status)), result=INVALID_PARAM_ERR, code=400)
        return self.clumgr.set_defend(
            cluster_name=cluster_name,
            host_name=host_name,
            host_type=host_type,
            host_ip=host_ip,
            username=username)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['POST'])
    def ssh_command(self, post_data, **kwargs):
        """
        连接到主机上执行指定命令
        :param post_data:
        :param :
        :return:
        """
        post_data = json.loads(post_data.replace("'", "\'"))
        host_ip = post_data.get('ip', '')
        command = post_data.get('command', '')
        if not host_ip:
            return Result('', 400, 'param error', 400)
        return self.clumgr.ssh_command(host_ip, command)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def get_all_node(self, **kwargs):
        """
        :param:
        :return:
        """
        return self.clumgr.get_all_node()

    @ring0
    @ring5
    @ring3
    @list_route(methods=['POST'])
    def add_cluster_member(self, post_data, **kwargs):
        """
        给cluster添加用户成员
        :param post_data:
        :param kwargs:
        :return:
        """
        post_data = json.loads(post_data.replace("'", "\'"))
        passport = kwargs.get('passport', {})
        # username = kwargs.get('passport', {}).get('username', 'unknown')
        rlt = self.clumgr.add_cluster_member(post_data, passport)
        if not rlt.success:
            return Result('', rlt.result, '', 400)
        return Result('')

    @ring0
    @ring5
    @ring3
    @list_route(methods=['POST'])
    def del_cluster_member(self, post_data, **kwargs):
        """
        删除集群用户成员
        :param post_data:
        :param kwargs:
        :return:
        """
        post_data = json.loads(post_data.replace("'", "\'"))
        passport = kwargs.get('passport', {})
        cluster_name = post_data.get('cluster_name')
        member = post_data.get('member')
        return self.clumgr.del_cluster_member(cluster_name, member, passport)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def get_cluster_member(self, **kwargs):
        """
        获取集群用户成员
        :param :
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        return self.clumgr.get_cluster_member(cluster_name)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def get_ports(self, **kwargs):
        """
        获取集群端口占用情况
        :param kwargs:
        :return:
        """
        return self.clumgr.get_ports(kwargs)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def node_monitor(self, **kwargs):
        """
        主机监控
        :param kwargs:
        :return:
        """
        return self.clumgr.node_monitor(kwargs)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_subnet(self, **kwargs):
        """
        获取集群的子网列表  条件: is_show = 1  status=1
        :param kwargs:
        :return:[]
        """
        try:
            rlt = NetworkMgr.instance().get_ippool_clu(kwargs.get('cluster_name'), 1, int(kwargs.get('offset', 0)),
                                                       kwargs.get('limit', None))
            if not rlt.success:
                Log(3, 'get_ippool error:{}'.format(rlt.message))
                return Result('', rlt.result, '')
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def set_net_ws(self, post_data, **kwargs):
        """
        设置子网，指派工作区
        :param kwargs:
        :return:[]
        """
        try:
            data_info = json.loads(post_data.replace("'", "\'"))
            Log(3, "set_net_ws:{}".format(kwargs.get('passport')))
            data_info['creater'] = kwargs.get('passport', {}).get('username', '')
            if not all([isinstance(data_info.get('workspace'), basestring),
                        isinstance(data_info.get('cluster_name'), basestring),
                        isinstance(data_info.get('fa_ip'), basestring),
                        isinstance(data_info.get('key'), basestring),
                        isinstance(data_info.get('subnet'), basestring)]):
                return Result('', 400, 'param error', 400)
            rlt = NetworkMgr.instance().set_workspace(data_info)
            if not rlt.success:
                Log(3, 'set_net_ws error:{}'.format(rlt.message))
                return Result('', rlt.result, rlt.message, 400)
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, e.message, 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def subnet_ws_list(self, **kwargs):
        """
        获取集群的子网工作区: status=0
        :param kwargs:
        :return:[]
        """
        try:
            rlt = NetworkMgr.instance().get_ippool_clu(kwargs.get('cluster_name'), 0, kwargs.get('offset'),
                                                       kwargs.get('limit'))
            if not rlt.success:
                Log(3, 'subnet_workspace error:{}'.format(rlt.message))
                return Result('', rlt.result, '')
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def del_net_ws(self, post_data, **kwargs):
        """
        删除子网设置和指派的工作区
        :param kwargs:
        :return:[]
        """
        try:
            data_info = json.loads(post_data.replace("'", "\'"))
            data_info['creater'] = kwargs.get('passport', {}).get('username', '')

            rlt = NetworkMgr.instance().del_subnet_ws(data_info)
            if not rlt.success:
                Log(3, 'set_net_ws error:{}'.format(rlt.message))
                return Result('', rlt.result, rlt.message, 400)
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, e.message, 500)

    @ring5
    @ring3
    @ring0
    @ring8
    @list_route(methods=['GET'])
    def get_clu_member(self, **kwargs):
        """
        获取用户是否在集群列表的成员中
        :param kwargs:
        :return:
        """
        try:
            passport = kwargs.get('passport', {})
            return self.clumgr.get_all_member(passport)
        except Exception as e:
            PrintStack()
            Log(1, "get clu member error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def events(self, **kwargs):
        """
        获取一个group下所有事件
        :param kwargs:
        :return:
        """
        try:
            offset = kwargs.get('offset', '1')
            limit = kwargs.get('limit', '10')
            group = kwargs.get('group', '')
            workspace = kwargs.get('workspace', '')
            start_time = kwargs.get('start_time', '')
            end_time = kwargs.get('end_time', '')
            if offset:
                offset = int(offset)
            if limit:
                limit = int(limit)
            return self.clumgr.get_ws_events(group, workspace, start_time, end_time, offset, limit)

        except Exception as e:
            PrintStack()
            Log(1, "get events error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def pod_pause_id(self, **kwargs):
        """
        获取pod的pause容器id, 用于容器监控时获取容器的网络数据
        :param host_ip:
        :param container_id:
        :return:
        """
        try:
            host_ip = kwargs.get('host_ip')
            container_id = kwargs.get('container_id')
            if container_id:
                container_id = container_id.split('//')[1] if '//' in container_id else container_id
                return KubeClientMgr.instance().get_pause_id(host_ip, container_id)
            else:
                return Result('', 400, 'param error', 400)
        except Exception as e:
            PrintStack()
            Log(1, "pod_pause id error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring0
    @ring5
    @ring3
    @ring8
    def test_apiserver(self, **kwargs):
        """
        获取apiserver返回的数据
        :param kwargs:
        :return:
        """
        try:
            return self.clumgr.test_apiserver(kwargs)
        except Exception:
            PrintStack()
            return Result('', 500, '', 500)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def test_etcd(self, **kwargs):
        return self.clumgr.test_etcd()

    @ring0
    @ring3
    @ring5
    def deletegroup(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception, e:
            Log(1, "Cluster.deletegroup load data to json fail,input[%s]" % (post_data))
            return Result('', INVALID_JSON_DATA_ERR, str(e), http.BAD_REQUEST)
        
        operator = args.get('passport',{}).get('username', 'system')
        
        Log(3, '[{}] delete group [{}] in'.format(operator, post_data))
        
        group = data.get('group')
        if not group:
            Log(1, 'deletegroup fail,as[group name is invalid]')
            return Result('', PARAME_IS_INVALID_ERR, 'group invalid')
        
        StorageMgr.instance().delete_group_storage_class(group, operator)

        ws = WorkSpacedb.instance().get_ws_by_group(group)
        if not ws.success:
            Log(1, 'deletegroup get_ws_by_group fail,as[%s]' % (ws.message))
            return Result('ok')

        g_d = {}
        for ns in ws.content:
            g_d.setdefault(ns['cluster_name'], []).append(ns['name'])

        for cluster_name, workspace_list in g_d.items():
            client = KubeClientMgr.instance().get_cluster_client(cluster_name)
            if client:
                for workspace in workspace_list:
                    # 删除pvc
                    StorageMgr.instance().delete_workspace_pv(cluster_name, workspace, operator)
                    
                    # 通过apiserver删除workspace
                    client.delete_namespace(workspace)

                    # 删除etcd中workspace信息
                    WorkSpacedb.instance().delete_workspace(workspace)

                    # 删除etcd中cluster下的member
                    # http://192.168.14.9:8881/v1/usergroup/b/user

                    # 删除workspace上的confmap
                    rlt = ConfigMapdb.instance().del_by_ws(workspace)
                    if not rlt.success:
                        Log(1, "workspace delete del_by_ws error:{}".format(rlt.message))

                    # 删除子网工作区的指派
                    rlt = NetworkMgr.instance().get_subnet_by_ws(workspace)
                    if not rlt.success:
                        Log(1, "networkmgr get_subnet_by_ws error:{}".format(rlt.message))
                        continue

                    data = rlt.content
                    if data:
                        NetworkMgr.instance().del_subnet_ws({"cluster_name": cluster_name,
                                                             'fa_ip': data.get('fa_ip'),
                                                             'key': data.get('key')})
        
        Log(3, '[{}] delete group [{}] resource finished'.format(operator, group))
        return Result('ok')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_hosts_by_ns(self, **kwargs):
        try:
            workspace = kwargs.get('workspace')
            if not workspace or '/' in workspace:
                return Result('', 400, 'param error', 400)
            return self.clumgr.get_hosts_by_ns(workspace)

        except Exception as e:
            PrintStack()
            Log(1, "get get_hosts_by_ns error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def set_host_eviction(self, **kwargs):
        """
        # 异步执行迁移主机的应用
        # kubectl drain <NODENAME>
        # 节点应用的迁移
        :param post_data:
        :param kwargs:
        :return:
        """
        # def process(self, http_method, request):
        cluster_name = kwargs.get('cluster_name', '')
        host_name = kwargs.get('host_name', '')
        host_ip = kwargs.get('host_ip', '')
        # reactor.callInThread(self.clumgr.set_eviction, cluster_name, host_ip, host_name)

        # 异步执行迁移主机的应用
        d = threads.deferToThread(self.clumgr.set_eviction, cluster_name, host_ip, host_name)
        d.addErrback(self.error_callback)
        d.addCallback(self.callback, cluster_name, host_ip)

        return self.clumgr.change_evction_status(cluster_name, host_ip)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def host_online(self, **kwargs):
        """
        # 主机上线
        :param post_data:
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name', '')
        host_ip = kwargs.get('host_ip', '')
        host_name = kwargs.get('host_name', '')
        return self.clumgr.host_online(cluster_name, host_ip, host_name)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def clu_monitor(self, **kwargs):
        """
        # 集群资源监控
        :param kwargs:
        :return:
        """
        return Monitordb.instance().read_all()

    def _test(self, name, age):
        import time
        # b = 10 / 0
        time.sleep(5)
        return 9

    @ring5
    @ring3
    @ring8
    @list_route(methods=['GET'])
    def test_defer(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        name = kwargs.get('name')
        age = kwargs.get('age')
        d = threads.deferToThread(self._test, name, age)
        d.addErrback(self.error_callback)
        d.addCallback(self.callback, name, age)
        return Result(80)


