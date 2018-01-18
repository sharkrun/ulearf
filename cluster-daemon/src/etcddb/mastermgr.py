# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年7月4日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, ETCD_RECORD_NOT_EXIST_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class Masterdb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'masternodedir')

    def read_master(self, master_id):
        return self.read(master_id, json=True)

    def is_master_exist(self, master_name):
        return self.is_key_exist(master_name)
