# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
from common.util import Result
from frame.logger import Log
from core.errcode import FAIL
from frame.event import Event
import time

"""

"""




class EventSchedu(Event):
    def __init__(self,schedu_info):
        self.last_report_time = time.time()   # 最后更新时间
        self.queue = []
        super(EventSchedu, self).__init__(schedu_info)        
        self.__event_list = {}
        
    def __del__(self):
        Log(3,"EventSchedu.__del__,event [%s]"%(self.task_id))
        
    def start(self):
        self.last_report_time = time.time()    
        
    def load_events(self):
        """加载需要监听的事件"""
        
    def load_event(self,event_id):
        """根据ID加载监听的事件"""
        
    def append_event(self,event):
        """添加一个监听事件"""
        if not event:
            return
        self.__event_list[event._id] = event
        self.queue.append(event._id)
        event.schedule = self
        Log(4,"EventSchedu.append_event [%s]"%(event._id))

    def get_next(self):
        """
        # 取得下一个监听事件
        # 如果前一个事件失败了，则任务失败
        """
        for _id in self.queue:
            if _id not in self.__event_list:
                Log(1,"The event[%s] not exist"%(_id))
                continue
            event = self.__event_list[_id]
            if event.is_success():
                continue
            elif event.is_fail():
                return None
            else:
                Log(4,"EventSchedu.get_next action[%s]"%(event._id))
                return event.action()
                
            
    def get_event(self,event_id):
        Log(4,"EventSchedu.get_event,there are [%d]event"%(len(self.__event_list)))
        if event_id in self.__event_list:
            return self.__event_list[event_id]
        else:
            event = self.load_event(event_id)
            if event:
                self.append_event(event)
                return event
            else:
                Log(1,"get_event fail,as[event is not exist.]")
                return None
    
    def on_update(self,event_id,status_info):
        """更新事件的状态"""
        self.last_report_time = time.time()  # 更新任务上报时间
        event = self.get_event(event_id)
        if event:
            event.update(status_info)
        else:
            Log(1,"The event[%s] not exist."%(event_id))
            
        
    def set_event_result(self,event_id,return_info):
        """设置事件处理结果"""
        event = self.get_event(event_id)
        
        if event:
            event.finish(return_info)
        else:
            Log(1,"The event[%s] not exist."%(event_id))
            
    def on_finish(self):
        """外部检查事件日程结束的时候调用"""
        
        
    def snapshot(self):
        """
        # 用于抓取任务当前的状态，便于入库存储
        """
        snap = super(EventSchedu, self).snapshot()
        snap["queue"] = self.queue        
        return snap
    
    def get_state(self):
        if self.is_success():
            return Result(100)
        if self.is_fail():
            return Result(0,FAIL,self.get_log())
        
        progress = 0
        for event in self.__event_list.values():
            if event.is_fail():
                return Result(0,FAIL,event.get_log())
            else:
                progress += event.get_progress()
                
        return Result(progress)
            
            
    def is_finished(self):
        if super(EventSchedu, self).is_finished():
            return True
        
        waiting = False
        for e in self.__event_list.values():
            if e.is_fail():
                self.set_fail(e.get_log(), FAIL)
                return True
            elif e.is_waiting() or e.is_process():
                waiting = True  # 这里不能立即返回，因为如果有失败的事件，则任务也是结束的。
            
        if not waiting:
            # 任务都不是等待状态，且没有失败的任务，则将任务状态置为成功
            self.set_success()
            return True
        else:
            return False
        
    def time_out(self):
        for event in self.__event_list.values():
            if event.is_process() or event.is_waiting():
                event.time_out()
                

                 
    


    