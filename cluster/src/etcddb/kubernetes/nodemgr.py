# -*- coding: utf-8 -*-
# ufleet 2017-08-15
"""
"""

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class CluNodedb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'clusternodes')

    def read_node(self, cluster_name, node_id):
        rlt = self.read('%s/%s' % (cluster_name, node_id), json=True)
        if not rlt.success:
            Log(1, 'NodeMgr.read_node fail,as[%s]' % (rlt.message))

        return rlt

    def read_node_list(self, cluster_name):
        """
        获取某个集群下的所有主机
        :param cluster_name:
        :return: 集群存在：[{},{},{}] 不存在：[]
        """

        rlt = self.all_value_list(cluster_name)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result([])
        return rlt
    
    def read_master_list(self, cluster_name):
        """
        # 获取某个集群下的所有主机
        """
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            return rlt
        
        arr = []
        for node in rlt.content:
            if node.get('type') == "master":
                ip = node.get('ip')
                if ip:
                    arr.append({'HostIP':ip})
        
        return Result(arr)

    def save_node(self, cluster_name, data):
        """
        保存主机信息
        :param cluster_name:
        :param data:
        :return:
        """
        node_name = data['ip'].replace('.', '-')
        rlt = self.set(cluster_name + '/' + node_name, data)
        if not rlt.success:
            Log(1, 'NodeMgr.create_node save info fail,as[%s]' % (rlt.message))
            return rlt

        return Result('')

    def update_node(self, cluster_name, node_id, data):
        if not self.is_key_exist('%s/%s' % (cluster_name, node_id)):
            Log(1, 'NodeMgr.update_node [%s/%s]fail,as the key not exist' % (cluster_name, node_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The node not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s' % (cluster_name, node_id), data)
        if not rlt.success:
            Log(1, 'NodeMgr.update_node save info fail,as[%s]' % (rlt.message))
            return rlt

        return Result(node_id)

    def delete_node(self, cluster_name, node_id):
        """
        删除某个集群下的一个主机
        :param cluster_name:
        :param node_id:
        :return:
        """
        rlt = self.delete('%s/%s' % (cluster_name, node_id))
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, 'NodeMgr.delete_node info fail,as[%s]' % (rlt.message))
            return rlt

        return Result('ok')

    def is_node_added(self, node_id):
        """
        检查某个主机是否被添加过(包括该系统下所有集群的所有主机)
        :param cluster_name:
        :param node_id:
        :return:
        """
        rlt = self.read_clunode_map()
        if not rlt.success:
            # 表示该目录还没被创建
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result(False)
            return rlt
        for k, v in rlt.content.items():
            sp_key = k.split('/')
            if sp_key[-3] == 'clusternodes' and sp_key[-1] == node_id:
                return Result(True)
        return Result(False)

    def read_clunode_map(self):
        """
        返回所有主机
        :return:{'key': {}, 'key2': {}}
        """
        return self.read_map()

    def get_clu_node(self):
        """
        {"<cluster_name>": [{}, {}], "<cluster_name>": []}
        :return:
        """
        clu_node = {}
        rlt = self.read_map()
        if not rlt.success:
            return rlt
        
        for k, v in rlt.content.items():
            sp_key = k.split('/')
            if sp_key[-3] == 'clusternodes':
                clu_node.setdefault(sp_key[-2], []).append(v)
        return Result(clu_node)

    def delete_node_dir(self, cluster_name):
        """
        删除clusternodes/<cluster_name> 目录
        :return:
        """
        return self.delete_dir(cluster_name)

    def read_clunode_list(self):
        """
        读取map
        :param key:
        :return:{}
        """
        return self.read_list()
    
    def is_node_exist(self, cluster_name, node_ip):
        node_id = node_ip.replace('.', '-')
        return self.is_key_exist('%s/%s'%(cluster_name, node_id))
        