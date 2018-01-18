# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年7月27日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


SERVICE_PREFIX = 'SVC'

class StoregeClusterDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'cluster', ETCD_STORAGE_ROOT_PATH)
        self.prefix = SERVICE_PREFIX
        
        
    def read_cluster_list(self):
        return self.read_list(key_id='name')
        
        
    def get_cluster_info(self, cluster_name):
        return self.read(cluster_name)
            

    def create_cluster(self, name, cluster_info):
        cluster_info['create_time'] = NowMilli()
        
        rlt = self.set(name, cluster_info)
        if not rlt.success:
            Log(1, 'StoregeClusterMgr.create_cluster fail,as[%s]'%(rlt.message))
            return rlt
        
        return Result(name)

    
    def update_cluster(self, cluster_name, data):
        if not self.is_key_exist(cluster_name):
            Log(1, 'StoregeClusterMgr.update_cluster [%s]fail,as the key not exist'%(cluster_name))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The cluster not exist.')
        
        if isinstance(data, dict):
            rlt = self.update_json_value(cluster_name, data)
            if not rlt.success:
                Log(1, 'StoregeClusterMgr.update_cluster save info fail,as[%s]'%(rlt.message))
                return rlt
    
        return Result(cluster_name)
    
    
    def delete_cluster(self, cluster_name):
        rlt = self.delete(cluster_name)
        if not rlt.success:
            Log(1, 'StoregeClusterMgr.delete_cluster info fail,as[%s]'%(rlt.message))
        return rlt

    
    def is_cluster_exist(self, cluster_name):
        if self.is_key_exist(cluster_name):
            return True
        
        return False
    
    
    def get_cluster_num(self, cluster_name):
        rlt = self.read_key_list(cluster_name)
        if not rlt.success:
            Log(1, 'StoregeClusterMgr.get_cluster_num[%s] fail,as[%s]'%(cluster_name, rlt.message))
            return 0
        
        return len(rlt.content)


                
        
    
     
            
            
        