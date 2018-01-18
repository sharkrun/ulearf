#! /usr/bin/env python
# -*- coding:utf-8 -*-

from common.decorators import list_route
from frame.authen import ring0, ring5, ring3

from core.ufleethostmgr import UfleetHostMgr


class UfleetHost(object):
    def __init__(self):
        self.ufleetmgr = UfleetHostMgr()

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def hosts(self, **kwargs):
        """
        ufleet主机列表
        :param kwargs:
        :return:
        """

        return self.ufleetmgr.hosts()

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def detail(self, **kwargs):
        ip = kwargs.get('ip')
        return self.ufleetmgr.detail(ip)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def error_msg(self, **kwargs):
        """
        ufleet主机异常的原因
        :param kwargs:
        :return:
        """
        ip = kwargs.get('ip')
        return self.ufleetmgr.detail(ip)