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


class DeleteNodeInfoTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeleteNodeInfoTask, self).__init__(task_info, DELETE_STORAGE_NODE_TASK_SUFFIX)
        self.task_type = DELETE_STORAGE_NODE_TASK
        self.index = DELETE_STORAGE_NODE_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeleteNodeInfoTask.launch_task")
        try:
            rlt = self.workbench.delete_node_info()
            if rlt.success:
                self.log("delete_node_info success.")
            else:
                self.log("delete_node_info fail. as[%s]"%(rlt.message))
                return rlt

        except InternalException,ex:
            self.log("DeleteNodeInfoTask delete_node_info fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeleteNodeInfoTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeleteNodeInfoTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeleteNodeInfoTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeleteNodeInfoTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeleteNodeInfoTask.rollback")
        self.log("rollback")
        return Result(self._id)

        