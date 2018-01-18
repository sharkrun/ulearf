# -*- coding: utf-8 -*-

"""
主机资源配置
"""
from frame import  etcdclient
from core.const import ETCD_ROOT_PATH


class NodeResourceMgr(object):
    """
    """
    def __init__(self):
        self.root = ETCD_ROOT_PATH + ''
