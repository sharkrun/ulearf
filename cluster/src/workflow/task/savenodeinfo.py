# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建一个存储集群
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, SAVE_NODE_INFO_TASK_SUFFIX, \
    SAVE_NODE_INFO_TASK, SAVE_NODE_INFO_INDEX


class SaveNodeInfoTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(SaveNodeInfoTask, self).__init__(task_info, SAVE_NODE_INFO_TASK_SUFFIX)
        self.task_type = SAVE_NODE_INFO_TASK
        self.index = SAVE_NODE_INFO_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"SaveNodeInfoTask.launch_task")
        try:
            rlt = self.workbench.save_node_info()
            if rlt.success:
                self.log("save_node_info success.")
            else:
                self.log("save_node_info fail. as[%s]"%(rlt.message))
                return rlt

        except InternalException,ex:
            self.log("SaveNodeInfoTask save_node_info fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "SaveNodeInfoTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"SaveNodeInfoTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "SaveNodeInfoTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(SaveNodeInfoTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"SaveNodeInfoTask.rollback")
        self.log("rollback")
        return Result(self._id)

        