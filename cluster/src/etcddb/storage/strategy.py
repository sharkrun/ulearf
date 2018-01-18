# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年9月4日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class StrategyNodeDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'strategy', ETCD_STORAGE_ROOT_PATH)
        
    def read_node_info(self, cluster_name, host_ip):
        node_id = host_ip.replace('.', '-')
        
        rlt = self.read('%s/%s'%(cluster_name, node_id), json=True)
        if not rlt.success:
            Log(1, 'StrategyNodeDB.read_node fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_node_list(self, cluster_name):
        return self.read_list(cluster_name, key_id='node_id')
    
    def read_node_ip_list(self, cluster_name):
        rlt = self.read_list(cluster_name, key_id='node_id')
        if not rlt.success:
            return []
        
        arr = []
        for node in rlt.content:
            arr.append(node.get('ip', ''))
            
        return arr

    def create_node(self, cluster_name, host_ip, data):
        node_id = host_ip.replace('.', '-')
        
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s'%(cluster_name, node_id), data)
        if not rlt.success:
            Log(1, 'StrategyNodeDB.create_node save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(node_id)
            
    def update_node(self, cluster_name, node_id, data):
        if not self.is_key_exist('%s/%s'%(cluster_name, node_id)):
            Log(1, 'StrategyNodeDB.update_node [%s/%s]fail,as the key not exist'%(cluster_name, node_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The node not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, node_id), data)
        if not rlt.success:
            Log(1, 'StrategyNodeDB.update_node save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(node_id)
    
    def delete_node(self, cluster_name, node_id):
        rlt = self.delete('%s/%s'%(cluster_name, node_id))
        if not rlt.success:
            Log(1, 'StrategyNodeDB.delete_node info fail,as[%s]'%(rlt.message))
        return rlt
    
    def is_node_exist(self, cluster_name, host_ip):
        node_id = host_ip.replace('.', '-')
        return self.is_key_exist('%s/%s'%(cluster_name, node_id))
    
    def delete_cluster(self, cluster_name):
        rlt = self.delete_dir(cluster_name)
        if not rlt.success:
            Log(1, 'StrategyNodeDB.delete_cluster[%s] fail,as[%s]'%(cluster_name, rlt.message))
        return rlt
        
        
