# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
实现VM相关的数据库操作
"""

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_CREATE_KEY_FAIL_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class WorkDB(ETCDMgr):
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()

        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'work', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'WRK'
        
    def create_work_record(self, work_info):
        rlt = self.get_identity_id()
        if not rlt.success:
            Log(1, 'WorkDB.create_work_record.get_identity_id fail,as[%s]'%(rlt.message))
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')
        
        work_id = rlt.content
        work_info['create_time'] = NowMilli()
        rlt = self.set(work_id, work_info)
        if not rlt.success:
            Log(1, 'WorkDB.create_work_record save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(work_id)
    
    def update_all_work_info(self, work_id, work_info):
        """
        # work 结构信息非常多，这个方法实现替换功能，不做部分字段的修改
        """
        rlt = self.set(work_id, work_info)
        if not rlt.success:
            Log(1, 'WorkDB.update_all_work_info save info fail,as[%s]'%(rlt.message))
        return rlt
        
    def update_work_part_info(self, work_id, work_info):
        rlt = self.update_json_value(work_id, work_info)
        if not rlt.success:
            Log(1, 'WorkDB.update_work_part_info save info fail,as[%s]'%(rlt.message))
        return rlt

    
    def read_work_info(self, work_id):
        return self.read(work_id)

        
        
        
        
    