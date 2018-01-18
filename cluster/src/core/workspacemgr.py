# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
"""

from core.const import ETCD_ROOT_PATH
from common.util import Result
from core.errcode import WORKSPACE_SET_ERROR, WORKSPACE_IS_EXISTED, CLUSTER_NOT_EXISTED, \
    WORKSPACE_CHANGE_ERROR, WORKSPACE_GLT_ERROR, ETCD_KEY_NOT_FOUND_ERR, CLU_NOT_AUTH
from etcddb.kubernetes.clustermgr import Clusterdb
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from core.kubeclientmgr import KubeClientMgr
from etcddb.kubernetes.nodemgr import CluNodedb
from common.datatype import workspace_struce
from core.networkmgr import NetworkMgr
# from common.util import NowMilli
from frame.logger import Log
from frame.auditlogger import WebLog
# from frame.logger import PrintStack
from etcddb.configmapmgr import ConfigMapdb


class WorkspaceMgr(object):
    def __init__(self):
        self.root = ETCD_ROOT_PATH + '/workspace/'
        # self.__store = {}
        # self.expiry_time = 0
        # self.loaddata()

    # def reload(self, flush=0):
    #     if flush == 1:
    #         self.loaddata()
    #     else:
    #         if self.expiry_time <= NowMilli():
    #             self.loaddata()
    #
    # def loaddata(self):
    #     self.expiry_time = NowMilli() + 30000
    #     try:
    #         self.load_workspace()
    #     except Exception as e:
    #         PrintStack()
    #         Log(1, "loaddata error:{}".format(e.message))
    #
    # def load_workspace(self):
    #     """
    #     将所有workspace信息读到内存中
    #     :return:
    #     """
    #     rlt = WorkSpacedb.instance().read_all_workspace()
    #     if not rlt.success:
    #         return rlt
    #     self.__store = rlt.content

    def check_param(self, w):
        """
        检查参数
        {
            "cluster_name": 集群名称
            "workspacegroup_name": group名称
            "workspace_name": workspace名称
            "resource_cpu": 工作区cpu配额 默认: 1
            "resource_mem": 工作区内存配额 默认: 2000Mi
            "pod_cpu_min": pod cpu下限 默认: 0.1
            "pod_cpu_max": pod cpu上限 默认: 4
            "pod_mem_min": pod mem下限 默认: 2Mi
            "pod_mem_max": pod mem上限 默认:2000Mi
            "c_cpu_default": 容器cpu默认值 默认:0.1
            "c_mem_default": 容器mem默认值 默认:500Mi
            # ------ v1.8 增加 ----
            "c_cpu_default_min": 容器cpu默认最小值,
            "c_mem_default_min": 容器mem默认最小值,
            "c_cpu_min": 容器全局配额 cpu下限 默认:0.1
            "c_cpu_max": 容器全局配额 cpu上限 默认:2
            "c_mem_min": 容器全局配额 mem下限 默认:1Mi
            "c_mem_max" 容器 全局配额 mem上限  默认:1000Mi
        }

        :param w:
        :return:
        """
        if WorkSpacedb.instance().workspace_is_exist(w.get('workspace_name')):
            return Result('', WORKSPACE_IS_EXISTED, '', 400)

        if not Clusterdb.instance().clu_is_exist(w.get('cluster_name')):
            return Result('', CLUSTER_NOT_EXISTED, '', code=400)

        if w.get('workspace_name', '') == 'default' or w.get('workspace_name', '') == 'kube-system' or w.get(
                'workspace_name', '') == 'kube-public':
            return Result('', msg='', result=WORKSPACE_IS_EXISTED, code=400)
        return Result('')

    def workspce_remain(self, cluster_name):
        """
        :param cluster_name:
        :return:
        """
        rlt = CluNodedb.instance().read_node_list(cluster_name)
        if not rlt.success:
            return rlt
        # cluster_info = self.clu_info.get_node(cluster_name)
        cpu_1 = 0
        mem_1 = 0
        cpu_2 = 0
        mem_2 = 0
        Log(4, "workspace_remain:{}".format(rlt.content))
        for i in rlt.content:
            if i.get('status', '') == 'running':
                c = i.get('cpu', '')
                m = i.get('memory', '')
                if c:
                    cpu_1 += int(i.get('cpu', 0))
                if m:
                    mem_1 += float(i.get('memory', 0)[:-2])

        # 获取已经添加的workspace所占用资源
        rlt = WorkSpacedb.instance().clu_used(cluster_name)
        # used_workspace = get_workspace_list(self.etcd, cluster_name)
        if rlt.success:
            for i in rlt.content:
                cpu_2 += i.get('cpu', 0)
                mem_2 += float(i.get('mem', 0))
        else:
            if rlt.result != ETCD_KEY_NOT_FOUND_ERR:
                return Result('', msg=rlt.message, result=500, code=500)
        return Result(
            {'cpu_remain': round(cpu_1 * 0.8 - cpu_2, 2), 'mem_remain': round(mem_1 * 0.8 - mem_2, 3)})

    def __check_permission(self, username, clu_name):
        """
        检查是否有操作该资源的权限
        :param clu_name:
        :return:
        """
        rlt = Clusterdb.instance().read_clu_member(clu_name)
        if not rlt.success:
            Log(1, "workspacemgr check_permission error:{}".format(rlt.message))
            return rlt
        rlt1 = Clusterdb.instance().read_cluster(clu_name)
        if not rlt1.success:
            return rlt1
        if username not in rlt.content and username != rlt1.content.get('creater'):
            return Result(False)
        return Result(True)

    def check_resource(self, cluster_name, w, old_cpu=0, old_mem=0):
        """
        :param cluster_name:
        :param w:
        :param old_cpu:
        :param old_mem:
        :return:
        """
        # 获取剩余资源
        rlt = self.workspce_remain(cluster_name)
        if not rlt.success:
            return rlt

        if w.get('resource_cpu') - old_cpu > rlt.content['cpu_remain'] or w.get('resource_mem') - old_mem > rlt.content['mem_remain']:
            return Result('', msg='the cpu or the mem is bigger than than all cluster\'s sum',
                          result=WORKSPACE_SET_ERROR, code=400)

        # if w.get('resource_cpu') > cpu_1 - cpu_2 or w.get('resource_mem') > mem_1 - mem_2:
        #     return Result('', msg='the cpu or the mem is bigger than than all cluster\'s sum',
        #                   result=WORKSPACE_SET_ERROR, code=400)
        if w.get('resource_mem') * 1000 < 100 or w.get('resource_cpu') < 0.1:
            return Result('', msg='the cpu must bigger than 0.1 and the mem must bigger than 0.1',
                          result=WORKSPACE_GLT_ERROR, code=400)
        return Result('')

    def workspace_create(self, passport, w):
        """
        创建workspace
        :param creater:
        :param w:
        :return:
        """
        clu_name = w.get('cluster_name')
        ws_name = w.get('workspace_name')
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_permission(passport.get('username'), clu_name)
            if not rlt.success:
                return rlt
            if not rlt.content:
                return Result('', CLU_NOT_AUTH, 'not allowed', 400)

        # 检查参数
        check_param = self.check_param(w)
        if not check_param.success:
            return Result('', check_param.result, check_param.message, check_param.code)

        # 校验资源值
        check_res = self.check_resource(clu_name, w)
        if not check_res.success:
            return Result('', check_res.result, check_res.message, 400)

        # 通过apiserver创建namespace
        k = KubeClientMgr.instance().create_cluster_namespace(clu_name, ws_name, w)
        if not k.success:
            return Result('', k.result, k.message, 400)

        # 保存workspace数据
        data = workspace_struce(w, passport.get('username'))

        WebLog(3, u'创建', u"cluster[{}]的workspace[{}]".format(clu_name, ws_name), passport.get('username'))
        return WorkSpacedb.instance().save_workspace(w.get('workspace_name'), data)

    def workspace_update(self, passport, w):
        """
        更新workspace
        :param creater:
        :param w:
        :return:
        """
        clu_name = w.get('cluster_name')
        ws_name = w.get('workspace_name')

        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_permission(passport.get('username'), clu_name)
            if not rlt.success:
                return rlt
            if not rlt.content:
                return Result('', CLU_NOT_AUTH, 'not allowed', 400)

        old_workspace = WorkSpacedb.instance().read_workspace(w.get('workspace_name'))
        # old_workspace = self.etcd.read(self.root + w.get('workspace_name'), json=True)
        if old_workspace.success:
            if w.get('resource_cpu') < old_workspace.content.get('cpu', 0) or w.get(
                    'resource_mem') < old_workspace.content.get('mem', 0):
                return Result('', msg='change value can not litter than old value', result=WORKSPACE_CHANGE_ERROR,
                              code=400)
        else:
            return Result('', old_workspace.result, old_workspace.message, 400)

        # 校验资源值
        check_res = self.check_resource(clu_name, w, old_workspace.content.get('cpu', 0), old_workspace.content.get('mem', 0))
        if not check_res.success:
            return check_res

        # 通过apiserver更新namespace信息
        u_status = KubeClientMgr.instance().update_cluster_namespace(clu_name, ws_name, w)
        if not u_status.success:
            return Result('', u_status.result, u_status.message, 400)

        # 更新etcd数据
        data = workspace_struce(w, passport.get('username'))
        WorkSpacedb.instance().update_workspace(w.get('workspace_name'), data)

        WebLog(3, u'更新', u"cluster[{}]的workspace[{}]".format(clu_name, ws_name), passport.get('username'))
        return Result('')

    def workspace_delete(self, workspace_name, workspacegroup_name, cluster_name, passport):
        """
        删除workspace
        已经实现
        :param workspace_name:
        :param workspacegroup_name:
        :return:
        """
        # 检查权限
        if passport.get('ring') != 'ring0':
            rlt = self.__check_permission(passport.get('username'), cluster_name)
            if not rlt.success:
                return rlt
            if not rlt.content:
                return Result('', CLU_NOT_AUTH, 'not allowed', 400)
        # 删除应用
        # /**** deploy 模块自动检测，不需要主动去调用删除应用接口 ***/
        # gws = WorkSpacedb.instance().read_group_workspace(cluster_name)
        # Log(3, "gws:{}".format(gws.content))
        # deploy = DeployClient.instance().get_apply_num(cluster_name, gws.content)
        # if not deploy.success:
        #     Log(1, "get apply num error:{}".format(gws.message))
        # if deploy.content > 0:
        #     rlt = DeployClient.instance().delete_apply(cluster_name, workspacegroup_name, workspace_name)
        #     if not rlt.success:
        #         Log(1, "delete apply error:{}".format(rlt.message))

        # 通过apiserver删除namespace
        rlt = KubeClientMgr.instance().delete_cluster_namespace(cluster_name, workspace_name)
        if not rlt.success:
            Log(1, "kubeclient delete workspace:{} error:{}".format(workspace_name, rlt.message))
            return rlt
        # 删除workspace指定的子网
        rlt = NetworkMgr.instance().get_subnet_by_ws(workspace_name)
        if rlt.success:
            data = rlt.content
            if data:
                NetworkMgr.instance().del_subnet_ws(
                    {"cluster_name": cluster_name, 'fa_ip': data.get('fa_ip'), 'key': data.get('key')})
        else:
            Log(1, "networkmgr get_subnet_by_ws error:{}".format(rlt.message))

        # 删除etcd中configmap数据
        rlt = ConfigMapdb.instance().del_by_ws(workspace_name)
        if not rlt.success:
            if rlt.result != ETCD_KEY_NOT_FOUND_ERR:
                Log(1, "workspace delete configmap error:{}".format(rlt.message))

        # 更新etcd中数据
        rlt = WorkSpacedb.instance().delete_workspace(workspace_name)
        if not rlt.success:
            Log(1, "workspacedb delete workspace:{} error:{}".format(workspace_name, rlt.message))

        WebLog(3, u'删除', u"cluster[{}]的workspace[{}]".format(cluster_name, workspace_name), passport.get('username'))
        return Result('')

    def workspace_num(self, group=None):
        """
        :return:
        """
        num = 0
        ws = WorkSpacedb.instance().read_all_workspace()
        if ws.success:
            if group:
                for i in ws.content:
                    if i['group'] == group:
                        num += 1
            else:
                num = len(ws.content)
        return Result(num)

    def group_ws_name_list(self, group):
        """
        一个group下所有的workspace列表
        :return:
        """
        rlt = WorkSpacedb.instance().read_all_workspace()
        if not rlt.success:
            return rlt
        r_data = []
        for i in rlt.content:
            if i['group'] == group:
                r_data.append(i['name'])
        return Result(r_data)

    def group_ws_list(self, group):
        """
        一个group下所有的workspace列表
        :return:
        """
        rlt = WorkSpacedb.instance().read_all_workspace()
        if not rlt.success:
            return rlt
        r_data = []
        for i in rlt.content:
            if i['group'] == group:
                r_data.append(i)
        return Result(r_data)

    def cluster_list(self, group):
        """
        通过用户组查看集群列表
        :param group:
        :return:
        """
        rlt = WorkSpacedb.instance().read_all_workspace()
        if not rlt.success:
            return rlt
        r_data = []
        for i in rlt.content:
            if i['group'] == group:
                r_data.append(i['cluster_name'])
        return Result(list(set(r_data)))

    def subnet_workspace(self, cluster_name):
        """
        获取可被指派的工作区
        :param cluster_name:
        :return:
        """
        # 集群上的所有workspace列表
        rlt = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not rlt.success:
            return rlt
        w_list = []
        for i in rlt.content:
            w_list.append(i['name'])

        # 已经被指定过的workspace
        rlt = NetworkMgr.instance().get_ippool_clu(cluster_name, 0)
        if not rlt.success:
            Log(1, "workspace subnet_worksapce error:{}".format(rlt.message))
            return rlt
        for i in rlt.content:
            if i['workspace'] in w_list:
                w_list.remove(i['workspace'])
        return Result(w_list)

    def get_by_clu(self, cluster_name, group):
        """
        通过cluster_name和group获取集群列表
        :param cluster_name:
        :param group:
        :return:
        """
        # 集群上的所有workspace列表
        rlt = WorkSpacedb.instance().read_all_workspace()
        if not rlt.success:
            return rlt
        return Result([i for i in rlt.content if i['group'] == group and i['cluster_name'] == cluster_name])