# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建一个存储集群
"""


from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, WAIT_TASK_SUFFIX, WAIT_TASK, WAIT_INDEX


class WaitTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(WaitTask, self).__init__(task_info, WAIT_TASK_SUFFIX)
        self.task_type = WAIT_TASK
        self.index = WAIT_INDEX
        self.weight = 0.2
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"WaitTask.launch_task")
        try:
            rlt = self.workbench.wait_for_ready()
            if rlt.success:
                self.log("wait_for_ready success.")
            else:
                self.log("wait_for_ready fail. as[%s]"%(rlt.message))
                return rlt

        except InternalException,ex:
            self.log("WaitTask wait_for_ready fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "WaitTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"WaitTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "WaitTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(WaitTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"WaitTask.rollback")
        self.log("rollback")
        return Result(self._id)

        