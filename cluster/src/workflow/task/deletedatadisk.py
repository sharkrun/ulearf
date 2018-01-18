# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_APPLICATION_TASK_SUFFIX, ADD_APPLICATION_TASK, \
    ADD_APPLICATION_INDEX


class DeleteDataDiskTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeleteDataDiskTask, self).__init__(task_info, ADD_APPLICATION_TASK_SUFFIX)
        self.task_type = ADD_APPLICATION_TASK
        self.index = ADD_APPLICATION_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeleteDataDiskTask.launch_task")
        try:
            rlt = self.workbench.delete_data_disk()
            if rlt.success:
                self.log("delete_data_disk success.")
            else:
                self.log("delete_data_disk fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("DeleteDataDiskTask delete_data_disk fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeleteDataDiskTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeleteDataDiskTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeleteDataDiskTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeleteDataDiskTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeleteDataDiskTask.rollback")
        self.log("rollback.")
        return Result(self._id)

        