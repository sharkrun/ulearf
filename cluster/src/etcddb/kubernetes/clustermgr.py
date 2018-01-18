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


CLUSTER_AUTH_SUFFIX = 'auth_info'
CLUSTER_CLU_INFO = 'cluster_info'


class Clusterdb(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'clustermanages')

    def read_cluster(self, cluster_id):
        """
        获取一个集群的详细信息
        :param cluster_id:
        :return: {'':'', '':''}
        """

        rlt = self.read(cluster_id + '/cluster_info', json=True)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result({})
        return rlt

    def read_clu_map(self):
        """
        读取clustermanages/下所有内容
        :return: {'/cluster/clustermanages/<cluster_name>/cluster_inf/': {}}
        """
        return self.read_map()

    def clu_is_exist(self, cluster_name):
        """
        判断集群是否存在，看cluster_info是否存在
        :param cluster_id:
        :return:
        """
        return self.is_key_exist(cluster_name + '/cluster_info')

    def authinfo_is_exist(self, cluster_name):
        """
        判断集群auth_info是否存在，看cluster_info是否存在
        :param cluster_id:
        :return:
        """
        return self.is_key_exist(cluster_name + '/auth_info')

    def read_all_auth(self):
        """
        读取集群的所有auth_info
        :return:
        """
        rlt = self.read_map()
        if not rlt.success:
            return rlt
        r_data = {}
        for k, v in rlt.content.items():
            sp_key = k.split('/')
            if sp_key[-1] == 'auth_info':
                r_data[sp_key[-2]] = v
        return Result(r_data)

    def read_cluster_auth(self, cluster_id):
        return self.read('%s/%s' % (cluster_id, CLUSTER_AUTH_SUFFIX), json=True)
    
    def read_cluster_list(self, project_id):
        return self.read_list(skip_suffix=CLUSTER_AUTH_SUFFIX, key_id='cluster_id')

    def create_cluser(self, cluster_name, cluster_info):
        # cluster_info["create_time"] = DateNowStr()

        rlt = self.set(cluster_name, cluster_info)
        if not rlt.success:
            Log(1, 'ClusterMgr.create_cluster save info fail,as[%s]'%(rlt.message))
        return rlt

    # def save_auth_info(self, cluster_name, auth_info):
    #     """
    #     auth_info
    #     :param cluster_name:
    #     :param auth_info:
    #     :return:
    #     """
    #     rlt = self.set(cluster_name + '/auth_info', auth_info)
    #     if not rlt.success:
    #         Log(1, 'ClusterMgr.create_cluster save data fail,as[%s]' % (rlt.message))
    #         return rlt
    #     return Result(cluster_name)

    def del_auth_info(self, cluster_name):
        """
        删除auth_info
        :param cluster_name:
        :return:
        """
        rlt = self.delete(cluster_name + '/auth_info')
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, "del_auth_info:{} error:{}".format(cluster_name, rlt.message))
            return rlt
        return Result('')

    def read_clu_member(self, cluster_name):
        """
        :param cluster_name:
        :return:
        """
        rlt = self.read(cluster_name + '/member', json=True)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result([])
        return rlt

    def del_clu_member(self, cluster_name):
        """
        删除member
        :param cluster_name:
        :return:
        """
        rlt = self.delete(cluster_name + '/member')
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, "del_auth_info:{} error:{}".format(cluster_name, rlt.message))
            return rlt
        return Result('')

    def create_cluster_full(self, cluster_name, cluster_info):
        # cluster_info["create_time"] = DateNowStr()
        # if auth_info:
        #     rlt = self.set(cluster_name + '/auth_info', auth_info)
        #     if not rlt.success:
        #         Log(1, 'ClusterMgr.create_cluster save auth_info fail,as[%s]' % (rlt.message))
        #         return rlt

        rlt = self.set(cluster_name + '/cluster_info', cluster_info)
        if not rlt.success:
            Log(1, 'ClusterMgr.create_cluster save cluster_info fail,as[%s]'%(rlt.message))
            return rlt

        rlt = self.set(cluster_name + '/member', [])
        if not rlt.success:
            Log(1, 'ClusterMgr.create_cluster save member fail,as[%s]' % (rlt.message))
            return rlt

        rlt = self.set(cluster_name + '/apply_num', 0)
        if not rlt.success:
            Log(1, 'ClusterMgr.create_cluster save apply_num fail,as[%s]'%(rlt.message))
            return rlt

        return Result(cluster_name)

    def update_apply_num(self, cluster_id, data):
        if not self.is_key_exist(cluster_id + '/cluster_info'):
            Log(1, 'ClusterMgr.update_cluster [{}] fail,as the key not exist:{}'.format(cluster_id,
                                                                                        cluster_id + '/cluster_info'))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The cluster not exist.')

        if isinstance(data, int):
            rlt = self.update_int_value(cluster_id + '/apply_num', data)
            if not rlt.success:
                Log(1, 'ClusterMgr.update_cluster save info fail,as[%s]' % (rlt.message))
                return rlt

        return Result(cluster_id)

    def update_cluster(self, cluster_id, data):
        if not self.is_key_exist(cluster_id + '/cluster_info'):
            Log(1, 'ClusterMgr.update_cluster [{}] fail,as the key not exist:{}'.format(cluster_id, cluster_id + '/cluster_info'))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The cluster not exist.')

        # content = data.pop('content',None)
        # if content:
        #     rlt = self.set('%s-%s'%(cluster_id, CLUSTER_AUTH_SUFFIX), content)
        #     if not rlt.success:
        #         Log(1, 'ClusterMgr.update_cluster save data fail,as[%s]'%(rlt.message))
        #         return rlt
        Log(3, "update_clusger data:{}".format(data))
        if data:
            rlt = self.update_json_value(cluster_id + '/cluster_info', data)
            if not rlt.success:
                Log(1, 'ClusterMgr.update_cluster save info fail,as[%s]'%(rlt.message))
                return rlt
    
        return Result(cluster_id)

    def delete_cluster_dir(self, cluster_name):
        """
        删除集群，删除cluster_manage/<cluster_name>目录
        :param cluster_name:
        :return:
        """
        rlt = self.delete_dir(cluster_name)
        if not rlt.success:
            Log(1, 'ClusterMgr.delete_cluster [{}] fail,as[{}]'.format(cluster_name, rlt.message))
            return rlt

        return Result('ok')

    def read_clu_content(self, cluster_id):
        """
        返回集群列表
        :param cluster_id:
        :return:
        """
        return self.read_list(cluster_id, suffis=CLUSTER_CLU_INFO)

    def read_member(self, cluster_id):
        """
        返回集群member信息
        :param cluster_id:
        :return:
        """
        return self.read(cluster_id + '/member', json=True)

    def is_name_exist(self, cluster_name, cluster_id=None):
        rlt = self.read_list(skip_suffix=CLUSTER_AUTH_SUFFIX, key_id='cluster_id')
        if not rlt.success:
            Log(1, 'is_name_exist.read cluster list [%s] fail,as[%s]'%(rlt.message))
            return False
        
        for cfg in rlt.content:
            if cluster_id and cfg.get('cluster_id') == cluster_id:
                continue
            
            if cfg.get('name') == cluster_name:
                return True
        
        return False
    
    # def get_all_cluster_name(self):
    #     """
    #     获取所有集群名称
    #     :return:
    #     """
    #     rlt = self.read_key_list('')
    #     if not rlt.success:
    #         Log(1, 'ClusterMgr.get_all_cluster_name read_key_list fail,as[%s]'%(rlt.message))
    #         return rlt
    #     return Result(rlt.content)

    def add_member(self, cluster_name, list_member):
        """
        添加成员
        :return:
        """
        return self.add_list_value(cluster_name, list_member)

    def del_member(self, cluster_name, list_member):
        """
        删除成员
        :param list_member:
        :return:
        """
        return self.del_list_value(cluster_name, list_member)