# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.


import json

from twisted.internet import threads
from twisted.web import resource, server
from common.util import LawResult
from frame.logger import SysLog


class RegistryNotify(resource.Resource):
    def __init__(self,service,handler,allow_none = True,useDateTime=False, encoding = "UTF-8"):
        resource.Resource.__init__(self)
        self.service = service     
        self.instance = handler
        self.isLeaf = True
        self.encoding = encoding

    def render_GET(self,request):
        return self.process(request)
    
    def render_PUT(self,request):
        return self.process(request)
    
    def render_DELETE(self,request):
        return self.process(request)
    
    def render_POST(self, request):
        return self.process(request)
    
    def render_OPTIONS(self, request):
        return self.process(request)
    
    def process(self,request):
        function = getattr(self.instance, "dispatch", None)
        if function is None:
            f = {'msg':'handler dispatch fail'}
            self._cbRender(f, request)
        else:
            # Use this list to track whether the response has failed or not.
            # This will be used later on to decide if the result of the
            # Deferred should be written out and Request.finish called.
            responseFailed = []
            request.notifyFinish().addErrback(responseFailed.append)
            
            d = threads.deferToThread(function, request)
            d.addErrback(self._ebRender)
            d.addCallback(self._cbRender, request, responseFailed)
        return server.NOT_DONE_YET 
        
    
    def _ebRender(self, failure):
        SysLog(1,'_ebRender in with %s'%(str(failure)))
        return {'msg':'ErrCallback'}  

    
    def _cbRender(self, result, request, responseFailed=None):
        ret = {"success":True,"message":""}
        if responseFailed:
            return

        if isinstance(result,LawResult):
            ret = result.to_ext_result()
        else:
            ret = result

        try:
            content = json.dumps(ret)
            request.setHeader("content-length", str(len(content)))
            request.write(content)
        except Exception, e:
            SysLog(1,"RegistryNotify._cbRender fail [%s]"%str(e))
        request.finish()
