# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
from common.util import DateNowStr
from frame.logger import PrintStack, Log
import time

"""
被动的等待某个事件发生，然后做相应的处理
"""

class Event(object):
    SUCCESS = 0
    FAIL = 1
    PROCESSING = 2
    WAITING = 4
    ROLLBACK = 3
    
    def __init__(self,event_info):
        #self.event_id = task_id
        self.__state = event_info.pop("__state",self.WAITING)
        self.__log = event_info.pop("__log","")
        self.__time_out = event_info.pop("__time_out", time.time() + 1800)
        self.create_time = time.time() * 1000
        
        self.__dict__.update(event_info)
        
    def snapshot(self):
        """
        # 用于抓取任务当前的状态，便于入库存储
        """
        snap = {}
        snap["task_id"] = self.task_id
        snap["__state"] = self.__state
        snap["__log"] = self.__log
        snap["__time_out"] =self.__time_out
        snap["create_time"] =self.create_time
        return snap
    
    def is_finished(self):
        return self.__state == self.SUCCESS or \
            self.__state == self.FAIL
    
    def is_timeout(self):
        return self.__time_out < time.time()
    
    def is_waiting(self):
        return self.__state == self.WAITING
    
    def is_process(self):
        return self.__state == self.PROCESSING 
        
    
    def log(self,msg,code = 1):
        self.__log += "[%s][%s][%s];"%(DateNowStr(),code,msg)
        
    def get_log(self):
        return self.__log
        
    def set_timeout(self,expired_time):
        '''
        @param expired_time:second from 1970-1-1
        '''
        if expired_time > time.time():
            self.__time_out = expired_time
            
    def set_process(self):
        self.__state = Event.PROCESSING
    
    def set_success(self):
        self.__state = Event.SUCCESS
        self.destroy()
        
    
    def set_fail(self,reason,code=1):
        self.__state = Event.FAIL
        self.log(reason,code)
        self.destroy()
    
    def is_success(self):
        return Event.SUCCESS == self.__state
    
    def is_fail(self):
        return Event.FAIL == self.__state
    
    
    def on_update(self,*args):
        """由子类实现"""
        pass
        
            
    def update(self,*args):
        try:
            self.on_update(*args)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
    
    
    def finish(self,*args):
        try:
            self.on_finish(*args)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
           
    
    def on_finish(self,task_rlt):
        '''
        # 收尾工作，比如将事件置为结束，避免系统重新启动时继续监听任务。
        '''
        if task_rlt.success:
            Log(4,"Task Success.")
        else:
            Log(3,"Task Fail.")
            
    def action(self):
        """事件监听的行为"""
        return {}
    
    def destroy(self):
        try:
            self.on_destroy()
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
    
    def on_destroy(self):
        pass
    
    
        
        
    
    
    