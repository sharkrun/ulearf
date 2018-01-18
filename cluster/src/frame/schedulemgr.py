# -*- coding: utf-8 -*-
# Copyright (c) 2016-2016 The Cloudsoar.
# See LICENSE for details.
"""
To implement scheduled task manager
"""

import threading
import time

from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from common.guard import LockGuard
from common.util import DateNowStr


class ScheduledMgr(object):
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        '''
        Limits application to single instance
        '''
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.__sched = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)
        self.__sched.start()
        
        
    def add_date_job(self,func,exec_date,*args,**kwargs):
        """
        @param func: method to do the job
        @param exec_date: the time when to do the job,eg
            The job will be executed on November 6th, 2009
            exec_date = date(2009, 11, 6)
            The job will be executed on November 6th, 2009 at 16:30:05
            exec_date = datetime(2009, 11, 6, 16, 30, 5)
            exec_date = '2009-11-06 16:30:05'
            exec_date = '2009-11-06 16:30:05.720400'
        """
        # Store the job in a variable in case we want to cancel it
        job = self.__sched.add_job(func, 'date', args, exec_date=exec_date)
        return job
        
        
    def add_interval_job(self,func,interval_time={},*args,**kwargs):
        """
        @param func: method to do the job
        @param interval_time: a dictionary,eg
        {
            'weeks':1,    #number of weeks to wait
            'days':1,     #number of days to wait
            'hours':1,    #number of hours to wait
            'minutes':1,  #number of minutes to wait
            'seconds':1,  #number of seconds to wait
            'start_date':'2010-10-10 09:30'    #when to first execute the job and start the
                                               #counter (default is after the given interval)     
        }
        """

        # Schedule job_function to be called every two hours
        self.__sched.add_job(func, 'interval', args=args,kwargs=kwargs,**interval_time)
        
        
    def add_cron_job(self,func,cron_time,*args,**kwargs):
        """
        :param func: method to do the job,callable to run
        @param cron_time: a dictionary,eg
        {
            'year':1        # year to run on
            'month':1       # month to run on
            'week':1,       # week of the year to run on
            'day_of_week':1 # weekday to run on (0 = Monday)
            'day':1,        # day of month to run on
            'hour':1,       # hour to run on
            'minute':1,     # minute to run on
            'second':1,     # second to run on
            'start_date':'2010-10-10 09:30' ,
            'name':''
        }
        eg
            # Schedules job_function to be run on the third Friday
            # of June, July, August, November and December at 00:00, 01:00, 02:00 and 03:00
            self.__sched.add_cron_job(func, month='6-8,11-12', day='3rd fri', hour='0-3')
            
            # Schedule a backup to run once from Monday to Friday at 5:30 (am)
            self.__sched.add_cron_job(func, day_of_week='mon-fri', hour=5, minute=30)
        """
        self.__sched.add_job(func, 'cron', args=args,kwargs=kwargs,**cron_time)
        
    def remove_job(self, job_id):
        try:
            self.__sched.remove_job(job_id)
        except Exception:
            return False
        else:
            return True
                
    def update_job(self, job_id, job_args):
        self.modify_job(job_id, **job_args)
        
    def shutdown(self):
        self.__sched.shutdown()
        


def Test(msg):
    print "%s:%s"%(DateNowStr(),msg)
            
        
        
if __name__ == '__main__':
    schedu = ScheduledMgr.instance()
    
    cron_time = {'id':'hello','second':10}
    cron_time1 = {'id':'hello1','second':30}
    
    time.sleep(60 * 1)
    
    schedu.remove_job("hello")
    
#    schedu.add_cron_job(Test,cron_time,"hello 10")
#    schedu.add_cron_job(Test,cron_time1,"hello 30")
    
    time.sleep(60 * 2)
    schedu.shutdown()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
