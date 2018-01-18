# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

from common.util import DateNowStr, Result
from frame.logger import PrintStack, Log
from core.errcode import UNCAUGHT_EXCEPTION_ERR
from frame.exception import InternalException
from twisted.internet import defer
import time


"""
任务模型，通过这个任务模型驱动任务执行
主要有执行，回退，重试三种逻辑
"""

LOG_MAX_LENTH = 3000

class Task(object):
    SUCCESS = 0
    FAIL    = 1
    PROCESSING = 2
    ROLLBACK = 3
    WAITING = 4
    INITIAL = 100
    
    __delay = 10
    
    
    def __init__(self, task_info):
        self.error_code = task_info.pop("error_code",0)
        self.__state = task_info.pop("__state",Task.INITIAL)
        self.__rollbask_state = task_info.pop("__rollbask_state",Task.INITIAL)
        self.__log = task_info.pop("__log","")
        self.__time_out = task_info.pop("__time_out",time.time() + 1800) 
        self.index = 0
        self.create_time = time.time() * 1000
        self.start_time = 0
        
        self.__dict__.update(task_info)
        
    def snapshot(self):
        """
        # 用于抓取任务当前的状态，便于入库存储
        """
        snap = {}
        #snap["_id"] = self._id
        snap["error_code"] = self.error_code
        snap["__state"] = self.__state
        snap["__rollbask_state"] = self.__rollbask_state
        snap["__log"] = self.__log
        snap["__delay"] = self.__delay
        snap["__time_out"] =self.__time_out
        snap["create_time"] =self.create_time
        snap["start_time"] = self.start_time
        snap["index"] = self.index
        return snap
    
    def update_log(self):
        taskObj = {"__log":self.__log}
        return self.update(taskObj)
    
    def update(self,taskObj=None):
        return Result(0)
   
    def test(self):
        return Result(self._id)
    
    def run(self):
        try:
            self.set_process()
            self.pre_work()
            return self.process()
        except Exception,e:
            PrintStack()
            
            msg = "Task do pre work fail,as[%s]"%(str(e))
            Log(1,msg)
            self.log(msg)
            self.set_fail(msg, UNCAUGHT_EXCEPTION_ERR)
            raise InternalException(msg)
        
    def pre_work(self):
        '''
                     一些准备工作，比如保存任务信息等。
        '''
    
    
    
    
    
    def process(self):
        try:
            self.job = defer.maybeDeferred(self.__launch)
            self.job.addCallback(self.__process_launch_result)
        except Exception,e:
            PrintStack()
            self.set_fail("The thread execute fail,as[%s]"%(str(e)))
            return Result(self._id,UNCAUGHT_EXCEPTION_ERR,str(e))
        else:
            return Result(self._id)
            
        

    def __launch(self):
        try:
            rlt = self.launch_task()
        except InternalException,e:
            PrintStack()
            msg = "Launch task fail,as[%s]"%(str(e))
            Log(1,msg)
            self.log(msg)
            rlt = Result(self._id,e.errid,e.value)
        except Exception,e:
            PrintStack()
            msg = "Launch task fail,as[%s]"%(str(e))
            Log(1,msg)
            self.set_fail(msg)
            rlt = Result(self._id,UNCAUGHT_EXCEPTION_ERR,msg)
        finally:
            if not isinstance(rlt,Result):
                return Result(rlt)
            return rlt
            
    def launch_task(self):
        return Result("success")
            
    def __process_launch_result(self,launch_rlt):
        try:
            return self.process_launch_result(launch_rlt)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
            if not self.is_finished():
                self.set_fail(msg)
                
            return Result("",UNCAUGHT_EXCEPTION_ERR,msg)


    
    
    def process_launch_result(self,launch_rlt):
        '''
        # 处理启动任务的结果
        '''
        if launch_rlt.success:
            self.set_success()
        else:
            self.set_fail(launch_rlt.message, launch_rlt.result)
            
            
            
            
            

    def rollback_task(self):
        try:
            self.job = defer.maybeDeferred(self.__rollbask)
            self.job.addCallback(self.__process_rollback_result)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
            if not self.is_finished():
                self.set_rollbask_fail(msg)
                
    def __rollbask(self):
        try:
            rlt = self.rollback()
        except InternalException,e:
            PrintStack()
            msg = "Launch task fail,as[%s]"%(str(e))
            Log(1,msg)
            self.log(msg)
            
            rlt = Result(self._id,e.errid,e.value)
        except Exception,e:
            PrintStack()
            msg = "Launch task fail,as[%s]"%(str(e))
            Log(1,msg)
            self.set_rollbask_fail(msg)
            rlt = Result(self._id,UNCAUGHT_EXCEPTION_ERR,msg)
        finally:
            return rlt
    
    def rollback(self):
        '''
                      回滚操作，如果任务需要回退，则需要重写此函数。
        '''
    
    def __process_rollback_result(self,rollback_result):
        try:
            self.process_rollback_result(rollback_result)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
            if not self.is_finished():
                self.set_rollbask_fail(msg)
        
        
        
    def process_rollback_result(self,rollback_result):
        if rollback_result.success:
            self.set_rollbask_success()
        else:
            self.set_rollbask_fail(rollback_result.message, rollback_result.result)
    
    
    
    
    
    
    
    def retry(self):
        '''
                    如果任务启动出现主动抛出的异常，且任务状态为未终止，则调用此函数，再次启动任务
                    中间休眠10秒
        '''
        pass
        
    def set_delay(self,delay):
        self.__delay = delay
        
    def delay(self):
        time.sleep(self.__delay)
    
    def __retry(self):
        try:
            self.delay()
            self.retry()
        except Exception,e:
            PrintStack()
            msg = "Retry task fail,as[%s]"%(str(e))
            Log(1,msg)            
            self.set_fail(msg)
    
    
    
    
    
    
    def __end(self,task_rlt):
        try:
            self.end_work(task_rlt)
        except Exception,e:
            PrintStack()
            msg = "do the end work fail,as[%s]"%(str(e))
            Log(1,msg) 
           
    
    def end_work(self,task_rlt):
        '''
                     收尾工作，比如将保存的任务置为结束，避免系统重新启动时将任务重启。
        '''
        if task_rlt.success:
            Log(4,"Task Success.")
        else:
            Log(3,"Task Fail.")
            
            
    
    
    def is_finished(self):
        return self.__state == Task.SUCCESS or \
             self.__state == Task.FAIL or \
             self.__rollbask_state == Task.SUCCESS or \
             self.__rollbask_state == Task.FAIL
    
    def is_timeout(self):
        return self.__time_out < time.time()
    
    def is_initialed(self):
        return self.__state != self.INITIAL
        
    
    def log(self,msg,code = 1):
        if len(self.__log) > LOG_MAX_LENTH :
            index = self.__log.find("];",LOG_MAX_LENTH / 2)
            self.__log = self.__log[:index + 2]
        self.__log += "[%s][%d][%s];"%(DateNowStr(),code,msg)
        
    def log_and_save(self,msg,code = 1):
        self.log(msg, code)
        taskObj = {"__log":self.__log}
        return self.update(taskObj)

        
    def get_log(self):
        return self.__log
        
    def set_timeout(self,expired_time):
        '''
        @param expired_time:second from 1970-1-1
        '''
        if expired_time > time.time():
            self.__time_out = expired_time
    
    def set_success(self):
        self.__state = Task.SUCCESS
        self.__end(Result(Task.SUCCESS))
        
    def set_process(self):
        self.__state = Task.PROCESSING
        self.start_time = time.time() * 1000
    
    def set_fail(self,reason,code=UNCAUGHT_EXCEPTION_ERR):
        self.error_code = code
        self.__state = Task.FAIL
        self.__end(Result("",code,reason))
        self.log_and_save(reason,code)
    
    def is_success(self):
        return Task.SUCCESS == self.__state
    
    def is_fail(self):
        return Task.FAIL == self.__state
    
    
    def set_rollbask_success(self):
        self.__rollbask_state = Task.SUCCESS
    
    def set_rollbask_fail(self,reason,code=1):
        self.__rollbask_state = Task.FAIL
        self.log(reason,code)
    
    def is_rollbask_success(self):
        return Task.SUCCESS == self.__rollbask_state
    
    def is_rollbask_fail(self):
        return Task.FAIL == self.__rollbask_state
    
    def is_rollbask_finished(self):
        return self.__rollbask_state in (Task.SUCCESS,Task.FAIL)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    