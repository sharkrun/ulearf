# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.


"""
将任务计划分发给工厂执行
并检查任务进度，驱动任务正向执行，反向回退，
并负责任务恢复等操作
"""

import Queue
import threading
import time

from common.guard import LockGuard
from common.util import Result
from core.errcode import TASK_ALREADY_EXIST_ERR, TASK_NOT_EXIST_ERR, \
    TASK_CANCELED_ERR
from frame.logger import Log, PrintStack


class TaskScheduMgr(object):
    
    def __init__(self, thread_num, schedule_name="Task"):
        self.task_queue = Queue.Queue()
        self.schedule_name = schedule_name
        # 保护
        self.__lock = threading.Lock()
        self.__slow_task_lock = threading.Lock()
        self.threads = []
        self.slow_task_threads = {}
        self.task_store = {}
        self.finish_task = {}
        self.delay = 120
        self.__init_thread_pool(thread_num,schedule_name)
        
    def __init_thread_pool(self, thread_num, schedule_name):
        while thread_num:
            name = "%s_%s"%(schedule_name,thread_num)
            thread_num -= 1
            self.threads.append(Factory(self.task_queue,name))
        
    def timeout(self):
        if len(self.task_store) == 0:
            return
        
        with LockGuard(self.__lock):
            arr = []
            for task_id,expire_time in self.finish_task.iteritems():
                if expire_time <= time.time():
                    arr.append(task_id)
                    if task_id in self.task_store:
                        del self.task_store[task_id]
            
            for _id in arr:
                self.finish_task.pop(_id,None)
        
        for task_id,tsk in self.task_store.iteritems():
            if task_id in self.finish_task:
                continue
            if tsk.is_finished():
                self.finish_task[task_id] = time.time() + self.delay  # 推迟2分钟销毁任务，等待轮询
                
    def drop_task(self, user_id, task_id):
        with LockGuard(self.__lock):
            if task_id not in self.task_store:
                return True
        
            if self.task_store[task_id].is_finished() and user_id == self.task_store[task_id].user_id:
                del self.task_store[task_id]
                return True
        
        return False
        
                
    def get_task_status(self, task_id):
        if task_id in self.task_store:
            return self.task_store[task_id].get_task_status()
        else:
            return self.get_status_from_db(task_id)
        
    def wait_all_complete(self):
        for item in self.threads:  
            if item.isAlive():
                item.join()

    def get_status_from_db(self,task_id):
        """
        # 从数据库查询任务状态信息
        # 子类实现
        """
        
    def load_task(self,task_info):
        """
        # 根据任务信息加载任务
        # 子类实现
        """
    
    def create_task(self,task):
        with LockGuard(self.__lock):
            if task._id in self.task_store:
                return Result(0, TASK_ALREADY_EXIST_ERR,
                              "The task[%s]is exist already."%(task._id))
            self.task_store[task._id] = task
            self.task_queue.put(task)
        return Result(1)
    
    def cancel_task(self, task_id):
        if task_id not in self.task_store:
            Log(1, 'TaskScheduMgr.cancel_task[%s]fail,as the task not exist.'%(task_id))
            return Result('', TASK_NOT_EXIST_ERR, 'The task not exist.')
        
        self.task_store[task_id].set_fail('cancel', TASK_CANCELED_ERR)
        return Result('canceled')
            
    
    def create_slow_task(self,task):
        with LockGuard(self.__slow_task_lock):
            if task._id in self.task_store:
                return Result(0, TASK_ALREADY_EXIST_ERR,
                              "The task[%s]is exist already."%(task._id))
            self.task_store[task._id] = task
            
            key = task.get_queue_key(0)
            if key not in self.slow_task_threads:
                processor = Processor(key)
                processor.create_task(task)
                self.slow_task_threads[key] = processor
            else:
                self.slow_task_threads[key].create_task(task)

        return Result(1)


class Processor(object):
    """
    # 这个类用于处理同一种标记，必须排队的任务
    """
    def __init__(self,identity_key):
        self._id = identity_key
        self.queue = Queue.Queue()
        self.actor = Factory(self.queue,identity_key)
        Log(1,"Construct new Processor[%s]"%(identity_key))
        
    def create_task(self,task):
        self.queue.put(task)
        

    
class Factory(threading.Thread):
    def __init__(self, task_queue,factory_name="Factory"):
        super(Factory, self).__init__(name=factory_name)
        self.task_queue = task_queue
        self.setDaemon(True)
        self.start()
    
    def run(self):
        while True:
            try:  
                #任务异步出队，Queue内部实现了同步机制
                task = self.task_queue.get()
                task.run()
                while True:
                    if task.is_success() or task.is_rollbask_success():
                        #通知系统任务完成  
                        self.task_queue.task_done()
                        break
                    elif task.is_fail():
                        task.rollback()
                    time.sleep(3)
            except Exception,e:
                PrintStack()
                Log(1,"Factory.run throw exception[%s]"%(str(e)))
    

