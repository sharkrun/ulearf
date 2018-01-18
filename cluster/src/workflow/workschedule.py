# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
支线调度计划
1、根据订单信息分解成多个任务
2、存储任务的上下文
3、驱动任务逐步执行
"""

from etcddb.workflow.task import TaskDB
from frame.logger import Log
from frame.taskschedu import TaskSchedu


class WorkSchedule(TaskSchedu):
    
    def __init__(self,task_info):
        self._id = None
        self.is_initialized = False
        super(WorkSchedule, self).__init__(task_info)
        
    def save_to_db(self):
        """
        # 将任务信息存入数据库，同时将订单置为处理状态，
        # 只能执行一次，后续操作要用更新接口
        """
        taskObj = self.snapshot()
        
        if self._id:
            rlt = TaskDB.instance().update_to_db(self._id, taskObj)
        else:
            rlt = TaskDB.instance().create_task(taskObj)
            if rlt.success:
                self._id = rlt.content
            else:
                Log(1,"TaskDBImpl.save_to_db fail,as[%s]"%(rlt.message))
        return rlt
    
    def begin_process(self):
        # 将订单置为处理中状态
        pass
            
    def update(self,taskObj=None):
        if taskObj is None:
            taskObj = self.snapshot()
        rlt = TaskDB.instance().update_to_db(self._id, taskObj)
        if not rlt.success:
            Log(1,"TaskDBImpl.update[%s] fail,as[%s]"%(self._id,rlt.message))
    
  

