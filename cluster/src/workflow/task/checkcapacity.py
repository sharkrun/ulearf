# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建一个存储集群
"""


import time

from common.util import Result
from core.errcode import INTERFACE_NOT_EXIST_ERR
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, CHECK_CAPACITY_TASK_SUFFIX, \
    CHECK_CAPACITY_TASK, CHECK_CAPACITY_INDEX


class CheckCapacityTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(CheckCapacityTask, self).__init__(task_info, CHECK_CAPACITY_TASK_SUFFIX)
        self.task_type = CHECK_CAPACITY_TASK
        self.index = CHECK_CAPACITY_INDEX
        self.weight = 0.2
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"CheckCapacityTask.launch_task")
        try:
            time.sleep(3)
            if self.workbench.is_volume_exist():
                return Result('ok')
            else:
                Log(3, 'The persistent volume not exist')
                return Result('', INTERFACE_NOT_EXIST_ERR, 'The persistent volume not exist.')
        except InternalException,ex:
            self.log("CheckCapacityTask test_strategy_service fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "CheckCapacityTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"CheckCapacityTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "CheckCapacityTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(CheckCapacityTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"CheckCapacityTask.rollback")
        self.workbench.delete_pv()
        self.log("rollback")
        return Result(self._id)

        