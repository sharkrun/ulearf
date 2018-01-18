# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.
"""
实现任务相关的数据库操作
"""

import threading

from common.guard import LockGuard
from common.util import NowMilli, Result
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_CREATE_KEY_FAIL_ERR, NO_SUCH_RECORD_ERR
from frame.etcdv3 import ETCDMgr, ID
from frame.logger import Log


SUCCESS = 0
FAIL    = 1
PROCESSING = 2
ROLLBACK = 3
WAITING = 4
INITIAL = 100
    

class TaskDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()

        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'task', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'TSK'
        
    def read_task_info(self, task_id):
        return self.read(task_id)
         
        
    def update_to_db(self, task_id, taskObj):
        rlt = self.update_json_value(task_id, taskObj)
        if not rlt.success:
            Log(1, 'TaskDB.update_to_db save info fail,as[%s]'%(rlt.message))
        return rlt
    
    def create_task(self, taskObj):
        rlt = self.get_identity_id()
        if not rlt.success:
            Log(1, 'TaskDB.create_task.get_identity_id fail,as[%s]'%(rlt.message))
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')
        
        task_id = rlt.content
        taskObj['create_time'] = NowMilli()
        rlt = self.set(task_id, taskObj)
        if not rlt.success:
            Log(1, 'TaskDB.create_task save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(task_id)
    
    def read_task_page(self):
        return self.read_list(key_id=ID)
    
    def read_interrupt_task_list(self, task_type_list=None):
        rlt = self.read_list(key_id=ID)
        if not rlt.success:
            Log(1, 'TaskDB.read_interrupt_task_list fail,as[%s]')
            return rlt
        
        if isinstance(task_type_list, basestring):
            task_type_list = [task_type_list]
            
        arr = []
        for task in rlt.content:
            if task.get('__state') in [SUCCESS, FAIL]:
                continue
            
            if task.get('task_type') in task_type_list:
                arr.append(task)
        
        return Result(arr)

    
    def get_task_id_by_key(self, task_type, task_key, task_id):
        rlt = self.read_list(key_id=ID)
        if not rlt.success:
            Log(1, 'TaskDB.read_interrupt_task_list fail,as[%s]')
            return rlt
            
        for task in rlt.content:
            if task[ID] == task_id:
                continue
            
            if task.get('__state') == 0 or task.get('__state') == 1:
                continue
            
            if task.get('task_type') == task_type and task.get('task_key') == task_key:
                Log(3, 'get_task_id_by_key return [%s]'%(str(task)))
                return Result(task[ID])

        return Result('', NO_SUCH_RECORD_ERR, 'No repeat task exist.')
