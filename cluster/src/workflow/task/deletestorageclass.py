# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
删除StorageCluster相关的资源
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_STORAGE_TASK_SUFFIX, ADD_STORAGE_TASK, \
    ADD_STORAGE_INDEX


class DeleteStorageClassTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeleteStorageClassTask, self).__init__(task_info, ADD_STORAGE_TASK_SUFFIX)
        self.task_type = ADD_STORAGE_TASK
        self.index = ADD_STORAGE_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeleteStorageClassTask.launch_task")
        try:
            rlt = self.workbench.delete_storage_classes()
            if rlt.success:
                self.log("delete_storage_classes success.")
            else:
                self.log("delete_storage_classes fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("delete_storage_classes fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeleteStorageClassTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeleteStorageClassTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeleteStorageClassTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeleteStorageClassTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeleteStorageClassTask.rollback")
        self.log("rollback.")
        return Result(self._id)

        