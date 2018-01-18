#!/usr/sbin/python
# -*- coding: utf-8 -*-

from twisted.internet import reactor
from frame.logger import PrintStack
from frame.logger import Log
from twisted.web import resource
from api.elasticmgr import ElasticMgr
from common.timer import Timer
from api.node_monitor import Monitor
from api.syndata import SynData
from api.ufleet_host import UfleetMonitor


class RootResource(resource.Resource):
    isLeaf = True

    def __init__(self):
        resource.Resource.__init__(self)

        # 60s
        self.elastic_timer = Timer(60, ElasticMgr(), 'elastic check')
        self.elastic_timer.start()

        # 60s
        self.monitor_timer = Timer(60, Monitor(), 'node_monitor')
        self.monitor_timer.start()

        # 60s
        self.syndata_timer = Timer(60, SynData(), 'syndata')
        self.syndata_timer.start()

        # 20s
        self.ufleetmonitor_time = Timer(20, UfleetMonitor(), 'ufleetmonitor')
        self.ufleetmonitor_time.start()

        # --------------------------------------------------------------------
        # self.apiwatch_timer = Timer(10000, APiserverWatch())
        # p1 = multiprocessing.Process(target=ElasticGevent().start, args=(20,))
        #
        # p2 = multiprocessing.Process(target=MonitorGevent().start, args=(20,))
        #
        # p3 = multiprocessing.Process(target=SynDataGevent().start, args=(20,))
        #
        # p1.start()
        # p2.start()
        # p3.start()
        #
        # p1.join(5)
        # p2.join(5)
        # p3.join(5)


def main():
    RootResource()
    reactor.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        PrintStack()
        Log(1, "main error:{}".format(str(e)))
