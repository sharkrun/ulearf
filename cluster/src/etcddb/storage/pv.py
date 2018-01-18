# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月21日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_RECORD_NOT_EXIST_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class PVDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'pv', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'PV'
        
    def read_volume_info(self, cluster_name, pv_name):
        rlt = self.read('%s/%s'%(cluster_name, pv_name), json=True)
        if not rlt.success:
            Log(1, 'PVDB.read_volume_info fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_pv_info_by_volume_id(self, cluster_name, volume_id):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'PVDB.read_pv_info_by_volume_id fail,as[%s]'%(rlt.message))
            return rlt
        
        for pv in rlt.content:
            if pv.get('volume_id') == volume_id:
                return Result(pv)
            
        return Result('', ETCD_RECORD_NOT_EXIST_ERR, 'data not exist')
    
    
    def read_volume_list(self, cluster_name):
        rlt = self.read_list(cluster_name, key_id='pv_name')
        if not rlt.success:
            Log(1, 'PVDB.read_volume_list read_list fail,as[%s]'%(rlt.message))
        return rlt
    
    
    def get_pv_by_group(self, group):
        rlt = self.read_key_list()
        if not rlt.success:
            Log(1, 'PVDB.get_pv_by_group read_key_list fail,as[%s]'%(rlt.message))
            return rlt
        
        arr = []
        for cluster in rlt.content:
            ret = self.read_list(cluster, key_id='pv_name')
            if not ret.success:
                Log(1, 'PVDB.get_pv_by_group read_list[%s] fail,as[%s]'%(cluster, ret.message))
                continue
            
            for pv in ret.content:
                if pv.get('group') == group:
                    arr.append(pv)
                    
        return Result(arr)
    
    def get_pv_by_workspace(self, cluster, workspace):
        rlt = self.read_list(cluster, key_id='pv_name')
        if not rlt.success:
            Log(1, 'PVDB.get_pv_by_workspace read_list[%s] fail,as[%s]'%(cluster, rlt.message))
            return rlt
        
        arr = []
        for pv in rlt.content:
            if pv.get('workspace') == workspace:
                arr.append(pv)
                    
        return Result(arr)
    
    def get_pv_by_mount_ip(self, cluster, mount_ip):
        rlt = self.read_list(cluster, key_id='pv_name')
        if not rlt.success:
            Log(1, 'PVDB.get_pv_by_mount_ip read_list[%s] fail,as[%s]'%(cluster, rlt.message))
            return rlt
        
        arr = []
        for pv in rlt.content:
            if pv.get('ip') == mount_ip:
                arr.append(pv)
                    
        return Result(arr)

    def create_volume(self, cluster_name, data):
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s'%(cluster_name, data['pv_name']), data)
        if not rlt.success:
            Log(1, 'PVDB.create_volume save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(data['pv_name'])
            
    def update_volume(self, cluster_name, pv_name, data):
        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, pv_name), data)
        if not rlt.success:
            Log(1, 'PVDB.update_volume save info fail,as[%s]'%(rlt.message))
        return rlt
    
    def delete_volume(self, cluster_name, pv_name):
        rlt = self.delete('%s/%s'%(cluster_name, pv_name))
        if not rlt.success:
            Log(1, 'PVDB.delete_volume delete[%s][%s]fail,as[%s]'%(cluster_name, pv_name, rlt.message))
        return rlt
    
    
    def is_volume_exist(self, cluster_name, pv_name):
        return self.is_key_exist('%s/%s'%(cluster_name, pv_name))
    
    
    def count_volume(self, cluster_name):
        rlt = self.read_key_list(cluster_name)
        if not rlt.success:
            Log(1, 'PVDB.count_volume read_key_list fail,as[%s]'%(rlt.message))
            return 0
        
        return len(rlt.content)
        
        
        
        
        

        
    