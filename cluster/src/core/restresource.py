# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

from twisted.internet import threads
from twisted.web import resource, server
from core.resthandler import dispatch
from frame.logger import PrintStack
from frame.logger import Log


class RestResource(resource.Resource):
    def __init__(self, allow_none=True, useDateTime=False, encoding="UTF-8"):
        resource.Resource.__init__(self)
        self.isLeaf = True

    def render_GET(self, request):
        return self.process('GET', request)

    def render_PUT(self, request):
        return self.process('PUT', request)

    def render_DELETE(self, request):
        return self.process('DELETE', request)

    def render_POST(self, request):
        return self.process('POST', request)

    def process(self, http_method, request):
        try:
            responseFailed = []
            request.notifyFinish().addErrback(responseFailed.append)
    
            d = threads.deferToThread(dispatch, http_method, request)
            d.addErrback(self.error_callback)
            d.addCallback(self.callback, request, responseFailed)
            return server.NOT_DONE_YET
        except:
            PrintStack()

    def callback(self, content, request, responseFailed=None):
        try:
            request.setHeader("content-length", str(len(content)))
            request.setHeader("Access-Control-Allow-Origin", "*")
            request.write(content)
            if not request.finished:
                request.finish()
        except RuntimeError:
            Log(3, "callback :Request.finish called on a request after its connection was lost; ")
        except Exception as e:
            Log(1, "callback error:{}".format(str(e)))
            PrintStack()

    def error_callback(self, failure):
        try:
            return str(failure)
        except:
            PrintStack()

