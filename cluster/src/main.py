#!/usr/sbin/python
# -*- coding: utf-8 -*-
'''
# Copyright (c) 20016-2016 The Cloudsoar.
## See LICENSE for details
'''

import os

from twisted.internet import reactor
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from twisted.web import server

from core.server import WebService
from frame.configmgr import GetSysConfigInt
from frame.logger import PrintStack
from frame.logger import Log
# from twisted.python import threadable
# threadable.init(1)


def main():
    workroot = os.path.dirname(os.path.abspath(__file__))
    
    logdir = os.path.join(workroot, "trace", 'twisted')
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    log_file = DailyLogFile("server.log", logdir)
    log.startLogging(log_file)

    port = GetSysConfigInt("server_port", 8885)

    reactor.suggestThreadPoolSize(20)

    webserver = WebService(workroot)
    reactor.listenTCP(port, server.Site(webserver.get_resource(), timeout=10))
    reactor.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        PrintStack()
        Log(1, "main error:{}".format(str(e)))
