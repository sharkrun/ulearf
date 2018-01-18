# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.
"""
实现子任务相关的数据库操作
子任务是指那些组成一个任务计划的原子操作。
"""

import threading

from common.guard import LockGuard
from common.util import Result
from core.const import ETCD_STORAGE_ROOT_PATH
from frame.etcdv3 import ETCDMgr, ID
from frame.logger import Log


class SubTaskDB(ETCDMgr):
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()

        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'subtask', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'STSK'
        
    def update_to_db(self, parent_task_id, task_id, taskObj):
        rlt = self.update_json_value('%s/%s'%(parent_task_id, task_id), taskObj)
        if not rlt.success:
            Log(1, 'SubTaskDB.update_to_db save info fail,as[%s]'%(rlt.message))
        return rlt

    
    def read_task_list(self, parent_task_id):
        return self.read_list(parent_task_id, key_id=ID)
    
    def read_task_by_ids(self, parent_task_id, task_id_list):
        rlt = self.read_list(parent_task_id, key_id=ID)
        if not rlt.success:
            Log(1, 'TaskDB.read_interrupt_task_list fail,as[%s]')
            return rlt
            
        arr = []
        for task in rlt.content:
            if task['task_id'] in task_id_list:
                arr.append(task)
        
        return Result(arr)
    
    def read_sub_task_info(self, parent_task_id, task_id):
        return self.read("%s/%s"%(parent_task_id, task_id))
    
    def create_task(self, parent_task_id, task_id, taskObj):
        taskObj["progress"] = 0
        return self.set("%s/%s"%(parent_task_id, task_id), taskObj)
     
    