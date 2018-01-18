# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月11日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, ETCD_CREATE_KEY_FAIL_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class DiskDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'disk', ETCD_STORAGE_ROOT_PATH)
        
    def read_disk_info(self, host_ip, disk_id):
        host_id = host_ip.replace('.', '-')
        
        rlt = self.read('%s/%s'%(host_id, disk_id), json=True)
        if not rlt.success:
            Log(1, 'DiskDB.read_disk_info fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_disk_list(self, host_ip):
        host_id = host_ip.replace('.', '-')
        return self.read_list(host_id, key_id='disk_id')
    
    def count_disk_num(self, host_ip):
        host_id = host_ip.replace('.', '-')
        rlt = self.count(host_id)
        if not rlt.success:
            Log(1, 'DiskDB.count_disk_num[%s] fail,as[%s]'%(host_id, rlt.message))
            return 0
        
        return rlt.content

    def create_disk(self, host_ip, data):
        rlt = self.get_identity_id()
        if not rlt.success:
            Log(1, 'DiskDB.create_disk.get_identity_id fail,as[%s]'%(rlt.message))
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')
        
        disk_id = rlt.content
        host_id = host_ip.replace('.', '-')
        
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s'%(host_id, disk_id), data)
        if not rlt.success:
            Log(1, 'DiskDB.create_disk save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(disk_id)
            
    def update_disk(self, cluster_name, disk_id, data):
        if not self.is_key_exist('%s/%s'%(cluster_name, disk_id)):
            Log(1, 'DiskDB.update_disk [%s/%s]fail,as the key not exist'%(cluster_name, disk_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The disk not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, disk_id), data)
        if not rlt.success:
            Log(1, 'DiskDB.update_disk save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(disk_id)
    
    def delete_disk(self, host_ip, disk_id):
        host_id = host_ip.replace('.', '-')
        rlt = self.delete('%s/%s'%(host_id, disk_id))
        if not rlt.success:
            Log(1, 'DiskDB.delete_disk info fail,as[%s]'%(rlt.message))
            return rlt
        
        return Result('ok')
    
    
    def is_disk_exist(self, host_ip, disk_id):
        host_id = host_ip.replace('.', '-')
        return self.is_key_exist('%s/%s'%(host_id, disk_id))
    
    def statistic(self, host_ip):
        host_id = host_ip.replace('.', '-')
        rlt =  self.read_list(host_id, key_id='disk_id')
        if not rlt.success:
            Log(1, 'DiskDB.statistic[%s] fail,as[%s]'%(host_ip, rlt.message))
            return 0, 0
        
        total = 0
        free = 0
        
        
        return total, free
        
        
        

        
    