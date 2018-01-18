# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

"""
Implement the web server 
"""

from common.util import Result
from frame.logger import SysLog
from twisted.internet import threads
from twisted.internet.defer import Deferred
from twisted.web import server, xmlrpc
from twisted.web.xmlrpc import Handler
import xmlrpclib

Fault = xmlrpclib.Fault


class XMLRPCResource(xmlrpc.XMLRPC):
    def __init__(self, service, handler, allow_none=True, useDateTime=False, encoding="UTF-8"):
        xmlrpc.XMLRPC.__init__(self, allow_none, useDateTime)
        self.service = service
        self.handler = handler.dispatch
        self.isLeaf = True
        self.encoding = encoding

    def render_POST(self, request):
        request.content.seek(0, 0)
        request.setHeader("content-type", "text/xml")
        try:
            if self.useDateTime:
                args, functionPath = xmlrpclib.loads(request.content.read(),
                                                     use_datetime=True)
            else:
                # Maintain backwards compatibility with Python < 2.5
                args, functionPath = xmlrpclib.loads(request.content.read())

        except Exception, e:
            f = Fault(self.FAILURE, "Can't deserialize input: %s" % (e,))
            self._cbRender(f, request)

        else:
            responseFailed = []
            request.notifyFinish().addErrback(responseFailed.append)

            d = threads.deferToThread(self.handler, functionPath, *args)
            d.addErrback(self._ebRender)
            d.addCallback(self._cbRender, request, responseFailed)
        return server.NOT_DONE_YET

    def _cbRender(self, result, request, responseFailed=None):
        if responseFailed:
            return

        if isinstance(result, Result) and isinstance(result.content, Deferred):
            result.content.addCallback(self._cbRender, request, responseFailed)
            return

        if isinstance(result, Handler):
            result = result.result
        if not isinstance(result, Fault):
            result = (result,)
        try:
            try:
                content = xmlrpclib.dumps(
                    result, methodresponse=True,
                    allow_none=self.allowNone)
            except Exception, e:
                f = Fault(self.FAILURE, "Can't serialize output: %s" % (e,))
                content = xmlrpclib.dumps(f, methodresponse=True,
                                          allow_none=self.allowNone)

            request.setHeader("content-length", str(len(content)))
            request.write(content)
        except:
            SysLog(1, "XMRPC._cbRender error.")
        request.finish()

    def render_GET(self, request):
        text = '''
<body>
    <h1>Error!</h1>
    Method GET is not alowed for XMLRPC requests
    Be careful
</body>
        '''
        request.setHeader("content-type", ["text/html"])
        # request.setHeader("content-length", str(len(text)))
        request.write(text)
        request.finish()
