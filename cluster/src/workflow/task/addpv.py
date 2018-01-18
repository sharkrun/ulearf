# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_PV_TASK_SUFFIX, ADD_PV_TASK, ADD_PV_INDEX


class AddPVTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(AddPVTask, self).__init__(task_info, ADD_PV_TASK_SUFFIX)
        self.task_type = ADD_PV_TASK
        self.index = ADD_PV_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"AddPVTask.launch_task")
        try:
            rlt = self.workbench.create_persistent_volume()
            if rlt.success:
                self.log("create_persistent_volume success.")
            else:
                self.log("create_persistent_volume fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("AddPVTask create_persistent_volume fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "AddPVTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"AddPVTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "AddPVTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(AddPVTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"AddPVTask.rollback")
        rlt = self.workbench.delete_pv()
        if rlt.success:
            self.log("delete_pv success.")
        else:
            self.log("delete_pv fail. as[%s]"%(rlt.message))
        return rlt

        