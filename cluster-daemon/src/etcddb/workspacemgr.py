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
            Log(1, 'WorkSpaceMgr.read_workspace fail,as[%s]' % (rlt.message))
            return Result('', rlt.result, rlt.message)
        return rlt

    def read_gws(self):
        """
        返回所有workspace和group与集群的对应关系
        :return: {'<cluster_name>': ['group': '<group_name>', 'workspace': ['<ws1>', '<ws2>']
        """
        rlt = self.all_value_list()
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result([])
            return rlt
        a_data = {}
        arr = {}
        for i in rlt.content:
            arr.setdefault(i.get('cluster_name'), []).append(i)
        for k, v in arr.items():
            rlt1 = {}
            for i in v:
                rlt1.setdefault(i.get('group'), []).append(i.get('name'))

            a_data[k] = [{'group': k1, 'workspace': v1} for k1, v1 in rlt1.items()]
        return Result(a_data)

