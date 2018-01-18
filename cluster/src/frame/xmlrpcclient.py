# -*- test-case-name: twisted.web.test.test_xmlrpc -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
from common.util import Result
from frame.logger import SysLog
from core.errcode import CALL_REMOTE_METHOD_ERR, REMOTE_SERVICE_ABNORMAL_ERR
from twisted.internet import defer
from twisted.web.xmlrpc import Proxy
import time

"""
implement XMLRPC interface
"""

    
class XMLRPCClient(object):
    RUNNING = "running"
    DISCONNECT = "disconnected"
    __proxy = None
    
    def __init__(self,url,**kwargs):
        self.url = url.encode('gb2312')
        _allowNone = kwargs.get('allowNone', False)
        _timeOut = kwargs.get('connectTimeout', 30.0)
        try:
            proxy = Proxy(self.url,allowNone=_allowNone,connectTimeout=_timeOut)
        except Exception,e:
            SysLog(1,"XMLRPCClient.init fail as [%s]"%(str(e)))
        else:
            self.__proxy = proxy
    
    def getErrorCallback(self,callback):
        def errorCallback(failure):
            SysLog(2,"There is a exception on [%s],as[%s]"%(self.url,repr(failure.getTraceback())))
            SysLog(2,"ErrorMessage is [%s]"%(repr(failure.getErrorMessage())))
            rlt = Result(self.url,CALL_REMOTE_METHOD_ERR,repr(failure.getErrorMessage()))
            return callback(rlt)
        return errorCallback
    
    def asynCallRemote(self,methodName,callback,*args,**kargs):
        SysLog(2,"asynCallRemote method[%s]"%methodName)
        errorCallback = self.getErrorCallback(callback)
        if self.__proxy is None:
            errorCallback("asynCallRemote The proxy is None.")
            return Result(self.url,REMOTE_SERVICE_ABNORMAL_ERR,"asynCallRemote fail as [The proxy is None.] ")
        try:
            methodName = methodName.encode('gb2312')
            d = self.__proxy.callRemote(methodName,*args,**kargs).addCallback(callback).addErrback(errorCallback)            
        except Exception,e:
            SysLog(1,"XMLRPCClient.asynCallRemote call [%s] with [%s] fail,as [%s]"%(methodName,str(args),str(e)))
            return Result(methodName,CALL_REMOTE_METHOD_ERR,str(e))
        else:
            return d
        
    def deferResult(self,d):
        if not isinstance(d, defer.Deferred):
            return d
        
        count = 0;
        while count < 30:
            count += 1
            if isinstance(getattr(d,"result",None),Result):
                return d.result
            else:
                time.sleep(1)
        return Result("",1,"DeferResult get result fail.")
    