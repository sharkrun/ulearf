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


class MountVolumeTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(MountVolumeTask, self).__init__(task_info, ADD_DATA_VOLUME_TASK_SUFFIX)
        self.task_type = ADD_DATA_VOLUME_TASK
        self.index = ADD_DATA_VOLUME_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"MountVolumeTask.launch_task")
        try:
            rlt = self.workbench.mount_host()
            if rlt.success:
                self.log("mount_host success.")
            else:
                self.log("mount_host fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("MountVolumeTask mount_host fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "MountVolumeTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"MountVolumeTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "MountVolumeTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(MountVolumeTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"MountVolumeTask.rollback")
        rlt = self.workbench.unmount_host()
        if rlt.success:
            self.log("unmount_host success.")
        else:
            self.log("unmount_host fail. as[%s]"%(rlt.message))
        return rlt

        