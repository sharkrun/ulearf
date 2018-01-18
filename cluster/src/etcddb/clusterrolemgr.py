#! /usr/bin/env python
# -*- coding:utf-8 -*-

from frame.etcdv3 import ETCDMgr
import threading
from common.guard import LockGuard
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from common.util import Result


class ClusterRoledb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, '_instance'):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        super(ClusterRoledb, self).__init__('clusterrole')

    def save(self, name, data):
        return self.set(name, data)

