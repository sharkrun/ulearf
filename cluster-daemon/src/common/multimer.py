#! /usr/bin/env python
# -*- coding:utf-8 -*-

from frame.logger import Log, PrintStack
import multiprocessing
import signal


class Multimer(object):
    def __init__(self, interval, timeout_handler):
        super(Multimer, self).__init__()
        self.interval = interval
        self.handler = timeout_handler

    def run(self):
        try:
            print 'self.interval:', self.interval
            p = multiprocessing.Process(target=self.handler.timeout, args=(self.interval,))
            p.start()
            # p.join()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            PrintStack()
            Log(1, 'Multimer except:{}'.format(e.message))