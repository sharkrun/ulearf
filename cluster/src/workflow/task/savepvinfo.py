# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, UPDATE_PV_TASK_SUFFIX, UPDATE_PV_TASK, \
    UPDATE_PV_INDEX


class SavePVInfoTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(SavePVInfoTask, self).__init__(task_info, UPDATE_PV_TASK_SUFFIX)
        self.task_type = UPDATE_PV_TASK
        self.index = UPDATE_PV_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"SavePVInfoTask.launch_task")
        try:
            rlt = self.workbench.update_pv_info()
            if rlt.success:
                self.log("update_pv_info success.")
            else:
                self.log("update_pv_info fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("SavePVInfoTask update_pv_info fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "SavePVInfoTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"SavePVInfoTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "SavePVInfoTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(SavePVInfoTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"SavePVInfoTask.rollback")
        self.log('rollback')
        return Result('ok')

        