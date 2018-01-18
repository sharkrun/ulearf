#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr


class UfleetHostdb(ETCDMgr):
    # ufleet/cluster/ufleethost/<hostip>/cpu {1: {'alltime': 22, 'idletime': 33, 'time': ''}, 2:33 }
    # ufleet/cluster/ufleethost/<hostip>/mem
    # ufleet/cluster/ufleethost/<hostip>/disk
    # uflleet/cluster/ufleethost/<hostip>/net

    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'ufleethost')

    def read_host(self, ip, t):
        """
        获取一个集群的详细信息
        :param cluster_id:
        :return: {'':'', '':''}
        """

        rlt = self.read(ip + '/' + t, json=True)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result({})
        return rlt

    def hostallinfo(self):
        """
        :param ip:
        :return:
        """
        return self.read_map()

