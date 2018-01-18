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

    def read_clu_map(self):
        """
        读取clustermanages/下所有内容
        :return: {'/cluster/clustermanages/<cluster_name>/cluster_inf/': {}}
        """
        return self.read_map()

    def get_vip(self, cluster_id):
        return self.read(cluster_id + '/vip')

    def save_vip(self, cluster_id, vip):
        rlt = self.set(cluster_id + '/vip', vip)
        if not rlt.success:
            Log(1, "save_vip error:{}".format(rlt.message))
        return Result(0)

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
