# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
用于管理配置文件（纯文本文件，不会被编译）中保存的配置信息
"""

import os
import sys
import threading

from common.guard import LockGuard
from frame.configbase import ConfigBase
from frame.logger import Log


class ConfigMgr(ConfigBase):
    '''
    classdocs
    '''
    __lock = threading.Lock()
    __config_path = None
    Env = {}

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    @classmethod
    def getValue(cls, key):
        return cls.instance().get_config(key)

    def __init__(self):
        '''
        Constructor
        '''
        ConfigBase.__init__(self)
        self.wwwroot = ''

    def init(self):
        config_path = self.get_config_path()
        if not os.path.isfile(config_path):
            Log(1, "The configure file [%s] is not exist." % (config_path))
            return
        self.__config_path = config_path
        self.loadConfig(config_path)

    def save_to_file(self):
        self.save_config(self.__config_path)

    def get_base_path(self):
        if hasattr(sys, "_MEIPASS"):
            return os.environ.get('CLUSTER_WORK_ROOT', '/opt/cluster')
        else:
            return os.path.abspath(".")

    def get_config_path(self):
        if hasattr(sys, "_MEIPASS"):
            base_path = os.environ.get('CLUSTER_WORK_ROOT', '/opt/cluster')
            return os.path.join(base_path, 'conf', 'config.conf')
        else:
            base_path = os.path.abspath(".")
            return os.path.join(base_path, 'frame', 'conf', 'config.conf.1')

    def get_int(self, key, default=0):
        v = self.get_config(key)
        if v is None:
            return default

        try:
            v = int(v)
        except Exception as e:
            Log(2, "get_int fail,key[%s],value[%s],err[%s]." % (key, v, str(e)))
            return default
        else:
            return v

    @classmethod
    def get_path(self, *folders, **args):
        """
        # folder_name eg. test/res
        """
        base_path = self.get_base_path()

        path = os.path.join(base_path, *folders) if folders else base_path
        path = os.path.normpath(path)
        if args.get('auto_create', False) and not os.path.isdir(path):
            os.makedirs(path)
        return path

    def set_value(self, key, value):
        self.update_key(key, value)
        self.save_to_file()
        return True

    def get_www_root_path(self):
        if not self.wwwroot:
            www_root = self.get_base_path()
            www_root = os.path.split(www_root)[0]
            folder = GetSysConfig("www_root_folder") or 'wwwroot'
            self.wwwroot = os.path.join(www_root, folder)
        return self.wwwroot


ConfigMgr.instance().init()


def SetConfig(key, value):
    return ConfigMgr.instance().set_value(key, value)


def GetSysConfig(key):
    return ConfigMgr.instance().get_config(key)


def GetSysConfigInt(key, default=0):
    return ConfigMgr.instance().get_int(key, default)


def GetWorkPath(*path, **args):
    return ConfigMgr.instance().get_path(*path, **args)
