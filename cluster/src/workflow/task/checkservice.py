# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建一个存储集群
"""

import time

from common.util import Result
from core.errcode import VESPACE_SERVICE_ABNORMAL_ERR
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, CHECK_SERVICE_TASK_SUFFIX, CHECK_SERVICE_INDEX, CHECK_SERVICE_TASK


class CheckServiceTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(CheckServiceTask, self).__init__(task_info, CHECK_SERVICE_TASK_SUFFIX)
        self.task_type = CHECK_SERVICE_TASK
        self.index = CHECK_SERVICE_INDEX
        self.weight = 0.2
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"CheckServiceTask.launch_task")
        try:
            ready = False
            for _ in range(120):
                rlt = self.workbench.schedule_status()
                if not rlt.success:
                    Log(4, 'skip current action, as the schedule is failed')
                    return rlt
                
                if self.workbench.is_service_ready():
                    Log(3, 'The vespace service is ready')
                    if ready:
                        return Result('ok')
                    else:
                        ready = True
                        
                
                self.add_progress(1)
                time.sleep(30)

            return Result('', VESPACE_SERVICE_ABNORMAL_ERR, 'The vespace service abnormal.')
        except InternalException,ex:
            self.log("CheckServiceTask test_strategy_service fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "CheckServiceTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"CheckServiceTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "CheckServiceTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(CheckServiceTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"CheckServiceTask.rollback")
        self.log("rollback")
        return Result(self._id)

        