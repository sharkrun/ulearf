# -*- coding: utf-8 -*-
from common.util import Result
from frame.authen import ring8, ring0, ring5, ring3
from frame.configmgr import GetSysConfig
from common.decorators import list_route


class Websocket(object):
    def __init__(self):
        pass

    @ring0
    @ring3
    @ring5
    @ring8
    @list_route(methods=['GET'])
    def websocket(self, **kwargs):
        host = GetSysConfig('current_host')
        url = 'http://' + host + '/chat'
        return Result(url)
