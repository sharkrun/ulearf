# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

from frame.logger import Log
import time
import inspect
"""
"""


class LockGuard(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.acquire()
        # Log(4, "lock.acquire on [%s] [%s] inspect:[%s]"%(id(self), id(self.lock), inspect.stack()[1]))

    def __exit__(self, _type, value, traceback):
        self.lock.release()
        # Log(4, "lock.release on [%s] [%s] inspect:[%s]"%(id(self), id(self.lock), inspect.stack()[1]))


class FileGuard(object):
    def __init__(self, filename, mode):
        Log(3, "FileGuard inspect:{}".format(inspect.stack(()[1])))
        self.mode = mode
        self.filename = filename
        self.f = None

    def __enter__(self):
        try:
            self.f = open(self.filename, self.mode)
            return self.f
        except IOError as e:
            Log(2, "FileGuard.open file fail as [%s]" % (str(e)))
            return None

    def __exit__(self, _type, value, traceback):
        if self.f:
            self.f.close()


class FileReadGuard(object):
    def __init__(self, filename):
        self.filename = filename
        self.f = None

    def __enter__(self):
        try:
            self.f = open(self.filename, 'r')
            content = self.f.read()
            return content
        except IOError as e:
            Log(2, "FileGuard.open file fail as [%s]" % (str(e)))
            return None

    def __exit__(self, _type, value, traceback):
        if self.f:
            Log(4, 'type:%s, value:%s, traceback:%s' % (str(_type), str(value), str(traceback)))
            self.f.close()


class Calculagraph(object):
    def __init__(self, action, count=1):
        self.action = action
        self.multiplier = count
        self.begin = time.time()

    def __enter__(self):
        Log(4, "[%s]begin at[%f]" % (self.action, self.begin))

    def __exit__(self, _type, value, traceback):
        end = time.time()
        cost = end - self.begin
        Log(4, '[%s]finished at[%f],cost[%f]for[%d]' % (self.action, end, cost, self.multiplier))
