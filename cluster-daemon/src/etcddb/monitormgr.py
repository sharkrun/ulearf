# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年7月4日

@author: Jack
'''

import threading

from common.guard import LockGuard
from frame.etcdv3 import ETCDMgr


SERVICE_PREFIX = 'SVC'


class Monitordb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'nodemonitor')
        self.prefix = SERVICE_PREFIX

    def save_monitornode(self, host_name, num, data):
        """
        保存监控主机
        :param host_name:
        :return:
        """
        return self.set(host_name + '/' + str(num), data)






