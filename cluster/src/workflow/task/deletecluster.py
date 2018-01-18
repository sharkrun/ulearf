# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
删除一个存储集群
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, CREATE_STORAGE_CLUSTER_TASK_SUFFIX, \
    CREATE_STORAGE_CLUSTER_TASK, CREATE_STORAGE_CLUSTER_INDEX


class DeleteClusterTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeleteClusterTask, self).__init__(task_info, CREATE_STORAGE_CLUSTER_TASK_SUFFIX)
        self.task_type = CREATE_STORAGE_CLUSTER_TASK
        self.index = CREATE_STORAGE_CLUSTER_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeleteClusterTask.launch_task")
        try:
            rlt = self.workbench.delete_cluster()
            if rlt.success:
                self.log("delete_cluster success.")
            else:
                self.log("delete_cluster fail. as[%s]"%(rlt.message))
                return rlt

        except InternalException,ex:
            self.log("DeleteClusterTask delete_cluster fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeleteClusterTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeleteClusterTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeleteClusterTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeleteClusterTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeleteClusterTask.rollback")
        self.log("rollback")
        return Result(self._id)

        