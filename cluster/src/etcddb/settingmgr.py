# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
"""

import threading

from common.guard import LockGuard
from frame.etcdv3 import ETCDMgr
from frame.logger import Log

SETTING_PREFIX = ''


class SettingMgr(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'setting')
        self.prefix = SETTING_PREFIX

    def get_version(self):
        rlt = self.read('version')
        if rlt.success:
            return rlt.content

        return None
    
    def get_vespace_license(self):
        rlt = self.read('vespace')
        if not rlt.success:
            Log(1, 'SettingMgr.get_vespace_license fail,as[%s]' % (rlt.message))

        return rlt
    
    def set_vespace_license(self, license_str):
        rlt = self.set('vespace', license_str)
        if not rlt.success:
            Log(1, 'SettingMgr.set_vespace_license[%s] fail,as[%s]' % (license_str, rlt.message))

        return rlt

