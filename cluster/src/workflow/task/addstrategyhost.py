# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, ADD_STRATEGY_TASK_SUFFIX, ADD_STRATEGY_TASK, \
    ADD_STRATEGY_INDEX


class AddStrategyHostTask(SubTask):
    
    def __init__(self, task_info, workbench, ip):
        super(AddStrategyHostTask, self).__init__(task_info, ADD_STRATEGY_TASK_SUFFIX)
        self.task_type = ADD_STRATEGY_TASK
        self.index = ADD_STRATEGY_INDEX
        self.weight = 0.8
        self.workbench = workbench
        self.ip = ip
        self.port = 0
    
    def launch_task(self):
        Log(4,"AddStrategyHostTask.launch_task")
        try:
            rlt = self.workbench.add_strategy_host(self.ip)
            if rlt.success:
                self.log("add_strategy_host success.")
                self.port = rlt.content
            else:
                self.log("add_strategy_host fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("AddStrategyHostTask add_strategy_host fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "AddStrategyHostTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"AddStrategyHostTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "AddStrategyHostTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(AddStrategyHostTask, self).snapshot()
        snap['ip'] = self.ip
        snap['port'] = self.port
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"AddStrategyHostTask.rollback")
        if not self.port:
            self.log("rollback success.")
            return Result()
            
        rlt = self.workbench.delete_strategy_host(self.ip, self.port)
        if rlt.success:
            self.log("delete_strategy_host success.")
        else:
            self.log("delete_strategy_host fail. as[%s]"%(rlt.message))
                
        return rlt

        