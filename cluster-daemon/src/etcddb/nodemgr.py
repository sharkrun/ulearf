# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
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

    def update_node(self, cluster_name, node_id, data):
        if not self.is_key_exist('%s/%s' % (cluster_name, node_id)):
            Log(1, 'NodeMgr.update_node [%s/%s]fail,as the key not exist' % (cluster_name, node_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The node not exist.')

        data['update_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s' % (cluster_name, node_id), data)
        if not rlt.success:
            Log(1, 'NodeMgr.update_node save info fail,as[%s]' % (rlt.message))
            return rlt

        return Result(node_id)

    def read_clunode_map(self, pass_nll_value=True):
        """
        返回所有主机
        :return:{'key': {}, 'key2': {}}
        """
        return self.read_map(pass_nll_value=pass_nll_value)

    def read_clunode_list(self):
        """
        读取map
        :param key:
        :return:{}
        """
        return self.read_list()