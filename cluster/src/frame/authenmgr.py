# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.


from common.guard import LockGuard
from common.util import Result
from frame.logger import Log, PrintStack
from frame.authen import authen, RING_HELP_ASSIST
import threading

"""
Manager user security info and verify it  
"""


class AuthenMgr(authen):
    moduleId = "AuthenMgr"
    
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
        offset = 60
        Log(3,"AuthenMgr.__init__ with offset[%d]"%(offset))
        super(AuthenMgr,self).__init__(offset)

    def get_green_passport(self,method):
        if method == "whatTime" or method == "login" or method == "getCCPVMInfo":
            passport = {}
            passport["method"] = method
            passport["ring"] = RING_HELP_ASSIST
            return passport
        return False
    
    
    def verify_token(self,method,token,*args):
        try:
            passport = self.check_token(method,token,*args)
        except Exception,e:
            PrintStack()
            Log(1,"AuthenMgr.verify_token fail as [%s]"%(str(e)))
        else:
            return Result(passport)
        
    

        
        
  
 
        