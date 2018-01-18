# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
"""

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class WorkSpacedb(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'workspace')
        
    def read_workspace(self, workspace_name):
        """
        获取具体的workspace的信息
        :param project_id:
        :return:
        """
        rlt = self.read(workspace_name, json=True)
        if not rlt.success:
            if rlt.result != ETCD_KEY_NOT_FOUND_ERR:
                Log(1, 'WorkSpaceMgr.read_workspace fail,as[%s]'%(rlt.message))
            return Result('', rlt.result, rlt.message)
        return rlt
    
    def read_by_wg_ws(self, project_id, workspace_id):
        """
        通过group和workspace获取
        :param project_id:
        :param workspace_id:
        :return:
        """
        return self.read('%s/%s'%(project_id, workspace_id), json=True)
    
    def read_workspace_list(self, project_id):
        return self.read_list(project_id, key_id='workspace_id')

    def read_all_workspace(self):
        """
        读取所有的workspace信息
        :return: [{},{}]
        """
        return self.all_value_list()

    def clu_used(self, clu_name):
        """
        获取某个集群占用的workspace
        :param clu_name:
        :return:
        """
        rlt = self.all_value_list()
        if not rlt.success:
            return rlt
        arr = []
        Log(4, "clu_used:{}">format(rlt.content))
        for i in rlt.content:
            if i.get('cluster_name') == clu_name:
                arr.append(i)
        return Result(arr)

    def workspace_is_exist(self, w_name):
        """
        判断workspace是否存在
        :param w_name: workspace_name
        :return: False:不存在
        """
        return self.is_key_exist(w_name)

    def save_workspace(self, ws_name, data):
        """
        保存workspace
        :param ws_name:
        :param data:
        :return:
        """
        rlt = self.set(ws_name, data)
        if not rlt.success:
            Log(1, 'WorkSpaceMgr.create_workspace save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(ws_name)

    def update_namespace(self, namespace_id, data):
        if not self.is_key_exist(namespace_id):
            Log(1, 'NamespaceMgr.update_namespace [%s]fail,as the key not exist' % (namespace_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The namespace not exist.')

        if isinstance(data, dict):
            rlt = self.update_json_value(namespace_id, data)
            if not rlt.success:
                Log(1, 'NamespaceMgr.update_namespace save info fail,as[%s]' % (rlt.message))
                return rlt

        return Result(namespace_id)

    def update_workspace(self, ws_name, data):
        """
        更新workspace信息
        :param project_id:
        :param workspace_id:
        :param data:
        :return:
        """
        if not self.is_key_exist(ws_name):
            Log(1, 'WorkSpaceMgr.update_workspace [%s]fail,as the key not exist' % ws_name)
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The workspace not exist.')

        rlt = self.update_json_value(ws_name, data)
        if not rlt.success:
            Log(1, 'WorkSpaceMgr.update_workspace save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(ws_name)
    
    def delete_workspace(self, workspace_name):
        rlt = self.delete(workspace_name)
        if not rlt.success:
            Log(1, 'WorkSpaceMgr.delete_workspace info fail,as[%s]'%(rlt.message))
            return rlt
        
        return Result('ok')

    def is_name_exist(self, project_id, tpl_name, workspace_id=None):
        rlt = self.read_list(project_id, key_id='workspace_id')
        if not rlt.success:
            Log(1, 'is_name_exist.read workspace list [%s] fail,as[%s]'%(project_id, rlt.message))
            return False
        
        for cfg in rlt.content:
            if workspace_id and cfg.get('workspace_id') == workspace_id:
                continue
            
            if cfg.get('name') == tpl_name:
                return True
        
        return False

    def read_all_gws(self):
        """
        返回所有group和workspace对应关系
        :return: {"g1": ["ws1", "ws2"]}
        """
        rlt = self.all_value_list()
        if not rlt.success:
            return rlt
        w_d = {}
        for i in rlt.content:
            w_d.setdefault(i['group'], []).append(i['name'])
        return Result(w_d)

    def read_group_workspace(self, cluster_name):
        """
        统计一个集群下 workspacegroup和workspace对应关系
        [{'group': '', 'workspace': [{}, {}, {}]'}
        :return:
        """
        rlt = self.all_value_list()
        if not rlt.success:
            return rlt
        arr = []

        for i in rlt.content:
            if i.get('cluster_name') == cluster_name:
                arr.append(i)

        w_d = {}
        for i in arr:
            w_d.setdefault(i['group'], []).append(i['name'])
        gws = [{'group': k, 'workspace': v} for k, v in w_d.items()]

        return Result(gws)

    def get_ws_by_group(self, group):
        """
        通过group获取workspace
        :param group:
        :return:
        """
        rlt = self.all_value_list()
        if not rlt.success:
            return rlt
        arr = []
        for i in rlt.content:
            if i.get('group') == group:
                arr.append(i)
        return Result(arr)

    def get_ns_by_cluster(self, cluster_name):
        """
        获取集群上的worksapce列表
        :param cluster_name:
        :return: ['ws1', 'ws2']
        """
        rlt = self.read_list()
        if not rlt.success:
            Log(1, 'NamespaceMgr.get_ns_by_cluster read_all fail,as[%s]'%(rlt.message))
            return rlt
        Log(4, "get_ns_by_cluster:{}".format(rlt.content))
        arr = []
        for namespace in rlt.content:
            if namespace.get('cluster_name') == cluster_name:
                arr.append(namespace)
        return Result(arr)