# -*- coding: utf-8 -*-
# ufleet 2017-08-16
"""
configmap 模块 配置config
"""

from frame.etcdv3 import ETCDMgr
import threading
from common.guard import LockGuard
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from common.util import Result


class ConfigMapdb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'configmap')

    def read_all_configmap(self):
        """
        读取所有configmap
        :return:
        """
        rlt = self.read_map()
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result([])
            return rlt
        return rlt

    def read_configmap(self, workspace, conf_name):
        """

        :return:
        """
        return self.read('/'.join([workspace, conf_name]))

    def is_existed(self, workspace, config_name):
        """
        查看是否存在
        :param config_name:
        :param version:
        :return:
        """
        return self.is_key_exist('/'.join([workspace, config_name]))

    def save_configmap(self, workspace, conf_name,  data):
        """
        保存配置
        :return:
        """
        return self.set('/'.join([workspace, conf_name]), data)

    def del_configmap(self, workspace, conf_name):
        """
        删除configmap
        :param conf_name:
        :return:
        """
        rlt = self.delete('/'.join([workspace, conf_name]))
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            return rlt
        return Result('')

    def get_by_ws(self, workspace):
        """
        获取一个workspace下的所有configmap
        :param workspace:
        :return:
        """
        rlt = self.read_map()
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result([])
            return rlt
        return Result([i for i in rlt.content.values() if (i.get('workspace') == workspace)])

    def del_by_ws(self, workspace):
        """
        删除一个workspace的所有configmap
        :param workspace:
        :return:
        """
        return self.delete_dir(workspace)