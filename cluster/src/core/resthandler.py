# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
分发控制台提交的请求
"""

import json
import os

from twisted.web import http

from api.cluster_manage import Cluster
from api.ippool import Ippool
from api.storage import Storage
from api.websocket import Websocket
from api.configmap import Configmap
from api.workspace import Workspace
from api.clusterrole import ClusterRole
from api.clusterrolebinding import ClusterRoleBinding
from common.util import Result, LawResult
from core.errcode import ERR_METHOD_CONFLICT, ERR_SERVICE_INACTIVE, \
    PERMISSION_DENIED_ERR, INTERNAL_OPERATE_ERR, INTERNAL_EXCEPT_ERR, ERR_ACCESS_AUTHENFAIL, UNCAUGHT_EXCEPTION_ERR, \
    INTERFACE_NOT_EXIST_ERR
from core.userclient import UserClient
from frame.authen import ring8, ring0, ring5
from frame.exception import OPException
from frame.logger import PrintStack, SysLog, Log
from upgrade.upgrademgr import init_app_data
from workflow.workflowmgr import WorkFlowMgr
# from api.hostmgr import HostMgr
from api.ufleetmonitor import UfleetHost


class RestHandler(object):
    moduleId = "API"

    def __init__(self):
        self.__method_list = []
        self.__service_active = False
        self.init()

    def activate_server(self):
        self.__service_active = True

    def init_method(self, mod_instance, mod_name):
        for method in dir(mod_instance):
            if method[0] == "_":
                continue
            func = getattr(mod_instance, method)
            if type(func) == type(self.init_method) and hasattr(func, "ring"):
                rings = getattr(func, "ring")
            else:
                continue

            for ring in rings:
                methodSign = "%s.%s.%s" % (mod_name, ring, method)
                if methodSign in self.__method_list:
                    raise OPException("merge method fail: " + str(methodSign) + " conflict!", ERR_METHOD_CONFLICT)
                else:
                    self.__method_list.append(methodSign)

    def check_passport(self, mod_name, method, passport):
        # Log(3, "passport:{}".format(passport))
        ring = passport["ring"]
        methodSign = "%s.%s.%s" % (mod_name, ring, method)
        if methodSign in self.__method_list:
            return True
        return False

    def init(self):
        init_app_data()
        self.init_method(self, self.moduleId)

        self.workspace = Workspace()
        self.init_method(self.workspace, "workspace")

        self.cluster = Cluster()
        self.init_method(self.cluster, "cluster")

        self.term_socket = Websocket()
        self.init_method(self.term_socket, "term_socket")

        self.ippool = Ippool()
        self.init_method(self.ippool, "ippool")

        self.storage = Storage()
        self.init_method(self.storage, "storage")

        self.configmap = Configmap()
        self.init_method(self.configmap, "configmap")

        # self.hostmgr = HostMgr()
        # self.init_method(self.hostmgr, 'hostmgr')

        self.ufleetmgr = UfleetHost()
        self.init_method(self.ufleetmgr, 'ufleetmgr')

        self.clusterrole = ClusterRole()
        self.init_method(self.clusterrole, 'clusterrole')

        self.clusterrolebinding = ClusterRoleBinding()
        self.init_method(self.clusterrolebinding, 'clusterrolebinding')

        self.activate_server()
        self.work = WorkFlowMgr.instance()
        self.work.load_schedu_list()

    def dispatch(self, methodMod, method, http_method, passport, *args, **params):
        ret = None
        try:
            # check service available
            if not self.__service_active:
                raise OPException("Service inactive yet", ERR_SERVICE_INACTIVE)
            if not self.check_passport(methodMod, method, passport):
                ret = Result("", PERMISSION_DENIED_ERR, "Unauthorized or route not existed", 400)
                return

            if methodMod == self.moduleId:
                func = getattr(self, method, None)
            else:
                mod = getattr(self, methodMod, None)
                func = getattr(mod, method, None)

            if func is None:
                ret = Result("", INTERFACE_NOT_EXIST_ERR, "The method not exist.")
                return
            
            params['passport'] = passport
            if hasattr(func, 'bind_to_methods') and http_method in func.bind_to_methods:
                ret = func(*args, **params)
            elif func.func_code.co_flags & 0x8:
                ret = func(*args, **params)
            else:
                ret = func(*args)

        except OPException, e:
            PrintStack()
            # operation error logging and error handle
            ret = Result(e.errid, INTERNAL_OPERATE_ERR, str(e))
            Log(1, "Call method[" + str(method) + "] error! " + str(e) + " Param:" + str(params))
        except Exception, e:
            PrintStack()
            Log(1, "error:" + str(e))
            ret = Result(0, INTERNAL_EXCEPT_ERR, "internal errors")
            SysLog(1, "Dispatch.dispatch fail as [%s]" % str(e))
        finally:
            if isinstance(ret, LawResult):
                Log(4, u"%s return status_code <%s>" % (method, ret.code))
                return ret
            else:
                Log(4, u"%s return value is <%s>" % (method, str(ret)))
                return Result(ret)

    @ring0
    @ring5
    @ring8
    def version(self):
        return Result(os.environ.get('MODULE_VERSION', '-'))


resthandler = RestHandler()
usermgr = UserClient()


def dispatch(http_method, request):
    try:
        token_str = request.requestHeaders.getRawHeaders('token')
        Log(3, '[%s][%s][%s]in' % (http_method, request.path, token_str))

        passport = usermgr.parse_token(token_str)
        if passport is None:
            result = Result('', ERR_ACCESS_AUTHENFAIL, 'authorize fail', http.UNAUTHORIZED)
            return

        arr = [key for key in request.postpath if key != '']
        methodMod = resthandler.moduleId
        method = 'version'
        args = []

        if len(arr) == 1:
            method = arr[0]
        elif len(arr) > 1:
            methodMod = arr[0]
            method = arr[1]
            args = arr[2:]

        if 'POST' == http_method:
            data = request.content.read()
            if len(data) > (2 ** 23):
                data = 'post data too big.'
                request.content = None

            # Log(3, 'post data[%s]'%(str(data)))
            args.append(data)

        params = {}
        for key in request.args:
            if len(request.args[key]) == 1:
                params[key] = request.args[key][0]
            else:
                params[key] = request.args[key]
        # args为body中的请求参数(如果是post请求)或者是uri中第三层对象名称， params为url中携带的参数{}
        result = resthandler.dispatch(methodMod, method, http_method, passport, *args, **params)
        return
    except:
        PrintStack()
        result = Result('', UNCAUGHT_EXCEPTION_ERR, 'service except', http.BAD_REQUEST)
    finally:
        if not result.success:
            request.setResponseCode(result.code if result.code != 200 else http.INTERNAL_SERVER_ERROR)
        request.setHeader('content-type', 'application/json')
        return json.dumps(result.to_json())
