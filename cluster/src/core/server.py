# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

"""
Implement the web server 
"""

import os

from twisted.application import service
from twisted.internet.protocol import Factory
from twisted.web import resource
from twisted.web.static import File
from txsockjs.factory import SockJSResource

from core.restresource import RestResource
from core.terminal import SSHProtocol
from frame.configmgr import ConfigMgr
from frame.logger import PrintStack, Log
from frame.web import mimesuffix


# from txsockjs.factory import SockJSResource
class RootResource(resource.Resource):
    isLeaf = False
    numberRequests = 0

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.www_root = ConfigMgr.instance().get_www_root_path()

    def render_GET(self, request):
        path = os.path.normcase(request.path)[1:]

        response = None
        try:
            suffix = "html"
            if len(path) == 0:
                path = "index.html"

            fullpath = os.path.join(self.www_root, path)
            suffix = os.path.splitext(os.path.basename(path))[-1][1:]
            if suffix == '':
                suffix = 'html'
                fullpath = os.path.join(fullpath, "index.html")

            if os.path.isfile(fullpath):
                with open(fullpath, "rb") as fp:
                    response = fp.read()

            if suffix in mimesuffix:
                request.setHeader("content-type", mimesuffix[suffix])
        except:
            PrintStack()

        response = response if response else "<body><h1>Error!</h1>Get file [%s] fail</body>" % (path)
        request.setHeader("content-length", str(len(response)))
        return response

    def render_POST(self, request):
        response = '''<body><h1>Error!</h1>
        Method POST is not allowed for root resource
        </body>'''
        request.setHeader("content-type", ["text/html"])
        request.setHeader("content-length", str(len(response)))
        request.write(response)
        request.finish()

    def getChild(self, path, request):
        if path not in ["server"]:
            return self
        else:
            print "error"


class WebService(service.Service):
    def __init__(self, workroot, conf_file=""):
        self.workroot = workroot

        Log(3, "WebService Starting completed")

    def get_resource(self):
        www_root = os.path.split(self.workroot)[0]
        wwwroot = os.path.join(www_root, 'wwwroot')
        swagger = os.path.join(www_root, 'swagger')
        r = RootResource(self)
        r.putChild("v1", RestResource())
        r.putChild("chat", SockJSResource(Factory.forProtocol(SSHProtocol)))
        r.putChild("console", File(wwwroot))
        r.putChild("swagger", File(swagger))
        return r
