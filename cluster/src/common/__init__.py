# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

from common.guard import LockGuard
import threading

class SingleModel(object):
    '''
    # 使用单例模式的时候要注意，如果导入的路径不同，会产生不同的实例，比如：
    # 有文件 test.py 类 MySingle 继承自SingleModel
    # 文件 t1.py 导入 使用 from src.test import MySingle
    # 文件t2.py 导入使用 frome test import MySingle  
    # 这要 t1 中的MySingle.instance() 和 t2 的 MySingle.instance() 将得到不同的实例  
    '''
    
    __lock = threading.Lock()
    
    def __init__(self):
        '''
        Constructor
        '''
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()

        return cls._instance
