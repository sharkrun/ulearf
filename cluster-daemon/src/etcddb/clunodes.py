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
            Log(1, "etcd read_map error:{}".format(rlt.message))
            return Result('', rlt.result, rlt.message)
        if rlt.success:
            for k, v in rlt.content.items():
                sp_key = k.split('/')
                if sp_key[-3] == 'clusternodes':
                    clu_node.setdefault(sp_key[-2], []).append(v)
        return Result(clu_node)
