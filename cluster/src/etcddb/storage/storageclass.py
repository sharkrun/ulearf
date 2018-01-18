# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年12月6日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class StorageClassDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'storageclass', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'SC'
        
    def read_storage_class_info(self, cluster_name, storage_class):
        rlt = self.read('%s/%s'%(cluster_name, storage_class), json=True)
        if not rlt.success:
            Log(1, 'StorageClassDB.read_storage_class_info fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_storage_class_list(self, cluster_name, group):
        rlt = self.read_list(cluster_name, key_id='storage_class')
        if not rlt.success:
            Log(1, 'StorageClassDB.read_storage_class_list read_list fail,as[%s]'%(rlt.message))
            return rlt
        
        if not group:
            return rlt
        
        arr = []
        for sc in rlt.content:
            if sc.get('group') == group:
                arr.append(sc)
                    
        return Result(arr)
    
    def get_sc_by_group(self, group):
        rlt = self.read_key_list()
        if not rlt.success:
            Log(1, 'StorageClassDB.get_sc_by_group read_key_list fail,as[%s]'%(rlt.message))
            return rlt
        
        arr = []
        for cluster in rlt.content:
            ret = self.read_list(cluster, key_id='storage_class')
            if not ret.success:
                Log(1, 'StorageClassDB.get_pv_by_group read_list[%s] fail,as[%s]'%(cluster, ret.message))
                continue
            
            for pv in ret.content:
                if pv.get('group') == group:
                    arr.append(pv)
                    
        return Result(arr)
    
    
    def get_sc_by_mount_ip(self, cluster_name, mount_ip):
        rlt = self.read_list(cluster_name, key_id='storage_class')
        if not rlt.success:
            Log(1, 'StorageClassDB.get_sc_by_mount_ip read_list fail,as[%s]'%(rlt.message))
            return rlt
        
        arr = []
        for sc in rlt.content:
            if sc.get('ip') == mount_ip:
                arr.append(sc)
                    
        return Result(arr)
    
    def get_sc_by_workspace(self, cluster, workspace):
        rlt = self.read_list(cluster, key_id='storage_class')
        if not rlt.success:
            Log(1, 'StorageClassDB.get_sc_by_workspace read_list[%s] fail,as[%s]'%(cluster, rlt.message))
            return rlt
        
        arr = []
        for pv in rlt.content:
            if pv.get('workspace') == workspace:
                arr.append(pv)
                    
        return Result(arr)

    def create_storage_class(self, cluster_name, data):
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s'%(cluster_name, data['storage_class_name']), data)
        if not rlt.success:
            Log(1, 'StorageClassDB.create_storage_class save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(data['storage_class_name'])
            
    def update_storage_class(self, cluster_name, storage_class_name, data):
        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, storage_class_name), data)
        if not rlt.success:
            Log(1, 'StorageClassDB.update_storage_class save info fail,as[%s]'%(rlt.message))
        return rlt
    
    def delete_storage_class(self, cluster_name, storage_class_name):
        rlt = self.delete('%s/%s'%(cluster_name, storage_class_name))
        if not rlt.success:
            Log(1, 'StorageClassDB.delete_storage_class delete[%s][%s]fail,as[%s]'%(cluster_name, storage_class_name, rlt.message))
        return rlt
    
    
    def is_storage_class_exist(self, cluster_name, storage_class_name):
        return self.is_key_exist('%s/%s'%(cluster_name, storage_class_name))
    
    
    def count_volume(self, cluster_name):
        rlt = self.read_key_list(cluster_name)
        if not rlt.success:
            Log(1, 'StorageClassDB.count_volume read_key_list fail,as[%s]'%(rlt.message))
            return 0
        
        return len(rlt.content)
        
        
        
        
        

        
    