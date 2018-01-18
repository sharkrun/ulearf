# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建一个存储集群
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, DELETE_STORAGE_NODE_TASK_SUFFIX, \
    DELETE_STORAGE_NODE_TASK, DELETE_STORAGE_NODE_INDEX


class DeleteClusterInfoTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeleteClusterInfoTask, self).__init__(task_info, DELETE_STORAGE_NODE_TASK_SUFFIX)
        self.task_type = DELETE_STORAGE_NODE_TASK
        self.index = DELETE_STORAGE_NODE_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeleteClusterInfoTask.launch_task")
        try:
            rlt = self.workbench.delete_cluster_info()
            if rlt.success:
                self.log("delete_cluster_info success.")
            else:
                self.log("delete_cluster_info fail. as[%s]"%(rlt.message))
                return rlt

        except InternalException,ex:
            self.log("DeleteClusterInfoTask delete_cluster_info fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeleteClusterInfoTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeleteClusterInfoTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeleteClusterInfoTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeleteClusterInfoTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeleteClusterInfoTask.rollback")
        self.log("rollback")
        return Result(self._id)

        