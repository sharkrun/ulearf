# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.
"""
这是一个基类，用于多个任务共享数据
提供入库存储，与恢复功能
"""


from common.util import Result
from core.errcode import UNCAUGHT_EXCEPTION_ERR, SUCCESS
from etcddb.workflow.work import WorkDB
from frame.etcdv3 import ID
from frame.logger import Log


class TaskData(object):
    
    def __init__(self, work_info):
        self._id = ""
        self.__signal = SUCCESS
        self.__message = ""
        self.__dict__.update(work_info)
        
    def snapshot(self):
        return {'__signal': self.__signal, '__message':self.__message, ID:self._id}
        
    def save_to_db(self):
        rlt = WorkDB.instance().create_work_record(self.snapshot())
        if rlt.success:
            self._id = rlt.content
        else:
            Log(1,"TaskData.save_to_db fail,as[%s]"%(rlt.message))
            
    def update_to_db(self,task_data=None):
        if not self._id:
            Log(1,"TaskData.update_to_db fail,as[The id is invalid]")
            return
            
        if task_data is None:
            task_data = self.snapshot()
            
        rlt = WorkDB.instance().update_work_part_info(self._id,task_data)
        if not rlt.success:
            Log(1,"TaskData.update_work_part_info fail,as[%s]"%(rlt.message))
            
    def on_fail(self,taskResult):
        """
        # 任务失败时执行的操作
        """
    
    def on_success(self):
        """
        # 任务成功时执行的操作
        """

    def set_fail(self, reason, code=UNCAUGHT_EXCEPTION_ERR):
        """
        # 任务成功时执行的操作
        """
        self.__signal = code
        self.__message = reason
        self.update_to_db({'__signal': self.__signal, '__message': self.__message})
        
    def schedule_status(self):
        return Result('', self.__signal, self.__message)
        
    
        