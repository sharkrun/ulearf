# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年10月18日

@author: Cloudsoar
'''

import threading

from common.guard import LockGuard
from common.util import NowMilli
from core.vespaceclient import VeSpaceClient, DEFAULT_USER_NAME, \
    DEFAULT_PASSWORD
from core.vespacehaclient import VeSpaceHAClient
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.strategy import StrategyNodeDB
from frame.logger import Log


class VespaceMgr(object):
    '''
    # 管理 Vespace集群客户端
    '''


    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.__store = {}
        self.expiry_time = 0
        self.loaddata()

    def reload(self, flush=0):
        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def loaddata(self):
        self.expiry_time = NowMilli() + 30000
        self.load_all_client()

    def load_all_client(self):
        """
        # 加载所有集群客户端
        """
        # 获取有主机的集群名
        rlt = StoregeClusterDB.instance().read_cluster_list()
        if not rlt.success:
            Log(1, "VespaceMgr load_all_client read_cluster_list fail as[%s]"%(rlt.message))
            return
        
        tmp = {}
        for cluster in rlt.content:
            client = self.load_cluster(cluster)
            if client:
                tmp[cluster['name']] = client
            
        self.__store = tmp


    def load_cluster(self, cluster):
        """
        # 加载单个集群client
        """
        ip_list = StrategyNodeDB.instance().read_node_ip_list(cluster.get('name', '-'))
        if not ip_list:
            Log(1, "VespaceMgr load_cluster fail as[node not exist]")
            return None
        
        if len(ip_list) == 1:
            return VeSpaceClient(ip_list[0], cluster.get('username', DEFAULT_USER_NAME), cluster.get('password', DEFAULT_PASSWORD))
        else:
            return VeSpaceHAClient(ip_list, cluster.get('username', DEFAULT_USER_NAME), cluster.get('password', DEFAULT_PASSWORD))
            

    def get_cluster_client(self, cluster_name):
        """
        # 获取单个集群的 apiserver client
        """
        self.reload()
        if cluster_name in self.__store:
            return self.__store[cluster_name]
        
        rlt = StoregeClusterDB.instance().get_cluster_info(cluster_name)
        if not rlt.success:
            Log(1, "VespaceMgr.get_cluster_client get_cluster_info fail as[%s]"%(rlt.message))
            return None
        
        client = self.load_cluster(rlt.content)
        if client:
            self.__store[cluster_name] = client
            return client
        
        return None


