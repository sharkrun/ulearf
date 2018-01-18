# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月15日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, PARAME_IS_INVALID_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class VolumeDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'volume', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'VOL'
        
    def read_volume_info(self, cluster_name, volume_id):
        rlt = self.read('%s/%s'%(cluster_name, volume_id), json=True)
        if not rlt.success:
            Log(1, 'VolumeDB.read_volume_info fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_volume_list(self, cluster_name):
        return self.read_list(cluster_name, key_id='volume_id')

    def create_volume(self, host_ip, data):
        if 'name' not in data or not data['name']:
            Log(1, 'VolumeDB.create_volume fail,as[name is invalid]')
            return Result('', PARAME_IS_INVALID_ERR, 'name is must')
        
        host_id = host_ip.replace('.', '-')
        
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s'%(host_id, data['name']), data)
        if not rlt.success:
            Log(1, 'VolumeDB.create_volume save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(data['name'])
            
    def update_volume(self, cluster_name, volume_id, data):
        if not self.is_key_exist('%s/%s'%(cluster_name, volume_id)):
            Log(1, 'VolumeDB.update_volume [%s/%s]fail,as the key not exist'%(cluster_name, volume_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The volume not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, volume_id), data)
        if not rlt.success:
            Log(1, 'VolumeDB.update_volume save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(volume_id)
    
    def delete_volume(self, cluster_name, volume_id):
        rlt = self.delete('%s/%s'%(cluster_name, volume_id))
        if not rlt.success:
            Log(1, 'VolumeDB.delete_volume delete[%s][%s]fail,as[%s]'%(cluster_name, volume_id, rlt.message))
        return rlt
    
    
    def is_volume_exist(self, cluster_name, volume_name):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'VolumeDB.is_volume_exist read_list fail,as[%s]'%(rlt.message))
            return False
        
        for volume in rlt.content:
            if volume.get('name') == volume_name:
                return True
            
        return False
    
    
    def count_volume(self, cluster_name):
        rlt = self.read_key_list(cluster_name)
        if not rlt.success:
            Log(1, 'VolumeDB.count_volume read_key_list fail,as[%s]'%(rlt.message))
            return 0
        
        return len(rlt.content)
        
        
    def bind_to_pv(self, cluster_name, volume_id, pv_name):
        if not self.is_key_exist('%s/%s'%(cluster_name, volume_id)):
            Log(1, 'VolumeDB.update_volume [%s/%s]fail,as the key not exist'%(cluster_name, volume_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The volume not exist.')
        
        data = {'bind': pv_name}
        rlt = self.update_json_value('%s/%s'%(cluster_name, volume_id), data)
        if not rlt.success:
            Log(1, 'VolumeDB.bind_to_pv save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(volume_id)
        
    def get_iscsi_target_port(self, cluster_name):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'VolumeDB.get_iscsi_target_port read_list[%s] fail,as[%s]'%(cluster_name, rlt.message))
            return 3260
        
        arr = []
        for volume in rlt.content:
            if volume.get('share_type') == "iSCSI":
                arr.append(volume.get('target_port',0))
                
        for num in range(3260,32767):
            if num not in arr:
                return num
            
            
                
            
        
        
    