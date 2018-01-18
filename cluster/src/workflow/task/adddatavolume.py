# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
在Vespace创建volume
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_DATA_VOLUME_TASK_SUFFIX, ADD_DATA_VOLUME_TASK, \
    ADD_DATA_VOLUME_INDEX


class AddDataVolumeTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(AddDataVolumeTask, self).__init__(task_info, ADD_DATA_VOLUME_TASK_SUFFIX)
        self.task_type = ADD_DATA_VOLUME_TASK
        self.index = ADD_DATA_VOLUME_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"AddDataVolumeTask.launch_task")
        try:
            rlt = self.workbench.create_data_volume()
            if rlt.success:
                self.log("create_data_volume success.")
            else:
                self.log("create_data_volume fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("AddDataVolumeTask create_data_volume fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "AddDataVolumeTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"AddDataVolumeTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "AddDataVolumeTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(AddDataVolumeTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"AddDataVolumeTask.rollback")
        rlt = self.workbench.delete_data_volume()
        if rlt.success:
            self.log("delete_data_volume success.")
        else:
            self.log("delete_data_volume fail. as[%s]"%(rlt.message))
        return rlt

        