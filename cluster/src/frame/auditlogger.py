# -*- coding: utf-8 -*-

import datetime
import threading
import time

from frame.etcdv3 import ETCDClient
from frame.logger import PrintStack, Log


class AuditLogger(object):
    """
    将审计日志记录到etcd中
    """
    __lock = threading.Lock()
    operlogger = None
    syslogger = None
    weblogger = None
    stack_file = None
    dblogger = None

    @classmethod
    def instance(cls):
        AuditLogger.__lock.acquire()
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        AuditLogger.__lock.release()
        return cls._instance

    def __init__(self):
        """
        Constructor
        """
        self.etcd = ETCDClient.instance()

    def write(self, level, operate='', _object='', operator=''):
        """
        :param level: 日志级别 1: ERROR  3: INFO
        :param operate:  操作内容
        :param object:   操作对象
        :param operator: 操作者
        :return:
        """
        log = {
            'ID': '',
            'Level': level,
            'Operate': operate,
            'Operator': operator,
            'Object': _object,
            'Module': 'cluster',
            'Time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'UnixTime': int(round(time.time() * (10 ** 9)))
        }
        log['ID'] = log['Module'] + '_' + str(log['UnixTime'])
        self.etcd.set('/ufleet/auditlog/' + log['ID'], log)


def LogAdd(level, operator, obj):
    WebLog(level, u"创建", obj, operator)


def LogDel(level, operator, obj):
    WebLog(level, u"删除", obj, operator)


def LogMod(level, operator, obj):
    WebLog(level, u"修改", obj, operator)


def WebLog(level, operate='', _object='', operator=''):
    try:
        l = AuditLogger.instance()
        if level == 1:
            level = 'ERROR'
        elif level == 3:
            level = 'INFO'
        else:
            level = 'DEBUG'
        l.write(level, operate, _object, operator)
    except Exception as e:
        PrintStack()
        Log(1, 'WebLog error:{}'.format(e.message))
