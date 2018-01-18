# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

import time

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_LICENSE_TASK_SUFFIX, ADD_LICENSE_TASK, ADD_LICENSE_INDEX


class AddLicenseTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(AddLicenseTask, self).__init__(task_info, ADD_LICENSE_TASK_SUFFIX)
        self.task_type = ADD_LICENSE_TASK
        self.index = ADD_LICENSE_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"AddLicenseTask.launch_task")
        try:
            time.sleep(3)
            rlt = self.workbench.add_license()
            if rlt.success:
                self.log("add_license success.")
            else:
                self.log("add_license fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("AddLicenseTask add_license fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "AddLicenseTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"AddLicenseTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "AddLicenseTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(AddLicenseTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"AddLicenseTask.rollback")
        self.log("rollback")
        return Result(self._id)

        