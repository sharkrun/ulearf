# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

"""
1、根据订单信息分解成多个任务
2、存储任务的上下文
3、驱动任务逐步执行
"""

import time

from common.util import Result
from frame.logger import Log, PrintStack
from core.errcode import UNCAUGHT_EXCEPTION_ERR, TASK_TIMEOUT_ERR
from frame.task import Task


class TaskSchedu(Task):
    
    def __init__(self, task_info):
        self.action = ''
        super(TaskSchedu, self).__init__(task_info)
        self.to_do_task = []
        self.finished_task = []
        self.current_task = None
        self.task_result = {}
        
        self.set_timeout(time.time() + 3600)
        
        
    def __del__(self):
        Log(4,"TaskSchedu __del__, task id is [%s],obj[%s]"%(self._id, id(self)))
        self.to_do_task = []
        self.finished_task = []
        
    def create_task(self, taskObj):
        if taskObj.is_success():
            self.finished_task.append(taskObj)
        else:
            self.to_do_task.append(taskObj)
        
    def pre_work(self):
        pass
        
    def launch_task(self):
        if len(self.to_do_task):
            self.current_task = self.to_do_task.pop(0)
            try:
                return self.current_task.run()
            except Exception,e:
                PrintStack()
                Log(1,"launch task[%s] fail,as[%s]"%(self._id,str(e)))
            
                return Result(self._id,UNCAUGHT_EXCEPTION_ERR,str(e))
        else:
            self.set_success()
            return Result(self._id) 
            
    def process_launch_result(self,launch_result):
        # 先保存当前任务
        if not self.current_task:
            return launch_result
        
        self.finished_task.append(self.current_task)
        
        if self.current_task.is_success():
            self.current_task = None
            if len(self.to_do_task):
                return self.process()
            else:
                self.set_success()
        
        elif self.is_timeout():
            # 如果任务已经超时，则放弃当前任务，开始回退
            self.current_task = None
            self.set_fail("Timeout", TASK_TIMEOUT_ERR)
            
        else:
            self.set_fail("[%s]fail"%(self.current_task.task_type), self.current_task.error_code)
            self.current_task = None

            
            
            
    def rollback(self):
        if len(self.finished_task):
            self.current_task = self.finished_task.pop()
            try:
                self.current_task.rollback()
                self.current_task.update()
            except Exception,e:
                PrintStack()
                Log(1,"rollback task[%s] fail,as[%s]"%(self._id,str(e)))
                self.current_task = None
        else:
            self.set_rollbask_success()

    def process_rollback_result(self,rollback_result):
        if self.current_task.is_success():
            self.current_task = None
            if len(self.finished_task):
                return self.rollbask()
            else:
                self.set_rollbask_success()
        
        elif self.is_timeout():
            # 如果任务已经超时，则放弃当前任务，开始回退
            self.current_task = None
            self.set_rollbask_fail("Timeout", 1)
            
        else:
            self.current_task = None
            self.set_rollbask_fail(rollback_result.message, rollback_result.result)
    
    def snapshot(self):
        snap = super(TaskSchedu, self).snapshot()
        snap["task_type"] = self.task_type
        snap["action"] = self.action
        snap["task_result"] = self.task_result
        return snap
        
    def get_task_status(self):
        if self.is_finished():
            return self.get_task_result()
        else:
            return self.analyse_task_status()
            
    def analyse_task_status(self):
        rlt = {}
        rlt["task_id"] = self._id
        rlt["status"] = "processing" if self.start_time > 0 else 'waiting'
        rlt["action"] = self.action
        rlt["progress"] = self.calc_progress()

        return rlt
    
    def calc_progress(self):
        total = 0.0
        
        for task in self.finished_task:
            total += task.get_progress()
        
        if self.current_task:
            total += self.current_task.get_progress()
            
        return round(total,2)


    def get_task_result(self):
        rlt = {}
        rlt["task_id"] = self._id
        rlt["status"] = "success" if self.is_success() else "fail"
        rlt["action"] = self.action
        rlt["error_code"] = self.error_code
        rlt["progress"] = 100
        return rlt

