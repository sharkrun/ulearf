# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年12月26日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.const import ETCD_STORAGE_ROOT_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, ETCD_CREATE_KEY_FAIL_ERR
from core.vespaceclient import APPLICATION_HOST_PORT
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class MountDB(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'mount', ETCD_STORAGE_ROOT_PATH)
        self.prefix = 'MNT'
        
    def read_mount_info(self, cluster_name, mount_id):
        rlt = self.read('%s/%s'%(cluster_name, mount_id), json=True)
        if not rlt.success:
            Log(1, 'MountDB.read_mount_info fail,as[%s]'%(rlt.message))
        
        return rlt
    
    def read_mount_list(self, cluster_name, volume_name):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'MountDB.read_mount_list read_list fail,as[%s]'%(rlt.message))
            return False
        
        arr = []
        for host in rlt.content:
            if host.get('name') == volume_name:
                arr.append(host)
            
        return Result(arr)
    
    def get_volume_by_mount_ip(self, cluster_name, ip):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'MountDB.read_mount_list_by_id read_list fail,as[%s]'%(rlt.message))
            return False
        
        arr = []
        for host in rlt.content:
            if host.get('ip') == ip:
                arr.append(host.get('name'))
            
        return Result(arr)
    
    def save_mount_info(self, cluster_name, volume_info, host_list):
        for host_info in host_list:
            data = {}
            data.update(volume_info)
            data.update(host_info)
            self.create_mount_record(cluster_name, data)
            
        return Result('done')

    def create_mount_record(self, cluster_name, mount_info):
        rlt = self.get_identity_id()
        if not rlt.success:
            Log(1, 'MountDB.create_mount_record.get_identity_id fail,as[%s]'%(rlt.message))
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')
        
        _id = rlt.content
        
        data = {'create_time':NowMilli()}
        data['ip'] = mount_info.get('ip')
        data['port'] = mount_info.get('port', APPLICATION_HOST_PORT)
        data['name'] = mount_info.get('name')
        data['cluster_id'] = mount_info.get('cluster_id')
        data['share_type'] = mount_info.get('share_type')
        data['target_port'] = mount_info.get('target_port')
 
        rlt = self.set('%s/%s'%(cluster_name, _id), data)
        if not rlt.success:
            Log(1, 'MountDB.create_mount_record save info fail,as[%s]'%(rlt.message))
            return rlt

        return Result(_id)
            
    def update_mount_info(self, cluster_name, mount_id, data):
        if not self.is_key_exist('%s/%s'%(cluster_name, mount_id)):
            Log(1, 'MountDB.update_mount_info [%s/%s]fail,as the key not exist'%(cluster_name, mount_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The volume not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s'%(cluster_name, mount_id), data)
        if not rlt.success:
            Log(1, 'MountDB.update_mount_info save info fail,as[%s]'%(rlt.message))
            return rlt
    
        return Result(mount_id)
    
    def delete_mount_record(self, cluster_name, mount_id):
        rlt = self.delete('%s/%s'%(cluster_name, mount_id))
        if not rlt.success:
            Log(1, 'MountDB.delete_mount_record delete[%s][%s]fail,as[%s]'%(cluster_name, mount_id, rlt.message))
        return rlt
    
    
    def delete_mount_records(self, cluster_name, mount_id_list):
        for mount_id in mount_id_list:
            self.delete_mount_record(cluster_name, mount_id)
        
        return Result('done')


    def is_mount_exist(self, cluster_name, volume_name):
        rlt = self.read_list(cluster_name)
        if not rlt.success:
            Log(1, 'MountDB.is_volume_exist read_list fail,as[%s]'%(rlt.message))
            return False
        
        for volume in rlt.content:
            if volume.get('name') == volume_name:
                return True
            
        return False

    def count_mount_number(self, cluster_name, volume_name):
        rlt = self.read_key_list(cluster_name)
        if not rlt.success:
            Log(1, 'MountDB.count_volume read_key_list fail,as[%s]'%(rlt.message))
            return 0
        
        num = 0
        for volume in rlt.content:
            if volume.get('name') == volume_name:
                num += 1
        return num
        
