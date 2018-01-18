# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建StorageClass
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, CREATE_STORAGE_CLASS_TASK_SUFFIX, \
    CREATE_STORAGE_CLASS_TASK, CREATE_STORAGE_CLASS_INDEX


class CreateStorageClassTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(CreateStorageClassTask, self).__init__(task_info, CREATE_STORAGE_CLASS_TASK_SUFFIX)
        self.task_type = CREATE_STORAGE_CLASS_TASK
        self.index = CREATE_STORAGE_CLASS_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"CreateStorageClassTask.launch_task")
        try:
            rlt = self.workbench.create_storage_class()
            if rlt.success:
                self.log("create_storage_class success.")
            else:
                self.log("create_storage_class fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("CreateStorageClassTask create_storage_class fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "CreateStorageClassTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"CreateStorageClassTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "CreateStorageClassTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(CreateStorageClassTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"CreateStorageClassTask.rollback")
        rlt = self.workbench.delete_storage_class()
        if rlt.success:
            self.log("delete_storage_class success.")
        else:
            self.log("delete_storage_class fail. as[%s]"%(rlt.message))
        return rlt

        