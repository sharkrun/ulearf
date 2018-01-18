# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年7月4日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.errcode import ETCD_CREATE_KEY_FAIL_ERR, ETCD_KEY_NOT_FOUND_ERR, \
    INVALID_PARAM_ERR, ETCD_RECORD_NOT_EXIST_ERR, FAIL
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


SERVICE_PREFIX = 'SVC'


class Monitordb(ETCDMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        ETCDMgr.__init__(self, 'nodemonitor')
        self.prefix = SERVICE_PREFIX
        
    def _is_match(self, data, query):
        for key,value in query.iteritems():
            if isinstance(value, list):
                if data.get(key) not in value:
                    return False
            elif data.get(key) != value:
                return False
        return True
        
    def query(self, condition):
        rlt = self.read_list(key_id='id')
        if not rlt.success:
            Log(1, 'MonitorMgr.query read_all fail,as[%s]'%(rlt.message))
            return rlt
        
        arr = []
        for record in rlt.content:
            if self._is_match(record, condition):
                arr.append(record)
        
        return Result(arr)
        
    def read_record(self, node_id):
        return self.read(node_id, json=True)

    def create_record(self, data):
        server_name = data.get('name',None)
        if not server_name:
            return Result(0, INVALID_PARAM_ERR, 'Service name invalid')
        
        workspace = data.get('workspace',None)
        if not workspace:
            return Result(0, INVALID_PARAM_ERR, 'workspace invalid')
        
        if self.is_record_exist(workspace, server_name):
            return Result(0, INVALID_PARAM_ERR, 'Service [%s][%s] repeat'%(workspace, server_name))
        
        key = data.get('id',None)
        if key:
            if self.is_key_exist(key):
                return Result(0, FAIL, 'The record id[%s] is repeat'%(key))
        else:
            rlt = self.get_identity_id()
            if not rlt.success:
                Log(1, 'MonitorMgr.create_record.get_identity_id fail,as[%s]'%(rlt.message))
                return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')
        
            key = rlt.content
            data['id'] = key
            
        data['create_time'] = NowMilli()
        rlt = self.set(key, data)
        if not rlt.success:
            Log(1, 'MonitorMgr.create_record fail,as[%s]'%(rlt.message))
            return rlt
        
        return Result(key)

    def update_record(self, node_id, data):
        if not self.is_key_exist(node_id):
            Log(1, 'MonitorMgr.update_record [%s]fail,as the key not exist'%(node_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The record not exist.')
        
        if isinstance(data, dict):
            rlt = self.update_json_value(node_id, data)
            if not rlt.success:
                Log(1, 'MonitorMgr.update_record save info fail,as[%s]'%(rlt.message))
                return rlt
    
        return Result(node_id)

    def delete_record(self, node_id):
        rlt = self.delete(node_id)
        if not rlt.success:
            Log(1, 'MonitorMgr.delete_record info fail,as[%s]'%(rlt.message))
        return rlt
    
    def delete_record_by_name(self, workspace, app_name, record_name):
        rlt = self.read_list(key_id='id')
        if not rlt.success:
            Log(1, 'MonitorMgr.delete_record_by_name read_all fail,as[%s]'%(rlt.message))
            return rlt
        
        if app_name:
            for record in rlt.content:
                if record.get('name') == app_name and record.get('workspace') == workspace:
                    return self.delete_record(record['id'])
        else:
            for record in rlt.content:
                if record.get('record_name') == record_name and record.get('workspace') == workspace:
                    return self.delete_record(record['id'])
            
        return Result('', ETCD_RECORD_NOT_EXIST_ERR, 'The record not exist')
    
    def is_record_exist(self, workspace, record_name):
        rlt = self.read_list(key_id='id')
        if not rlt.success:
            Log(1, 'MonitorMgr.is_record_exist read_all fail,as[%s]'%(rlt.message))
            return True
        
        for record in rlt.content:
            if record.get('name') == record_name and record.get('workspace') == workspace:
                return True
            
        return False

    def save_monitornode(self, host_name, info):
        """
        保存monitor主机信息
        :param key:
        :return:
        """
        return self.set(host_name, info)

    def nodemonitor_deldir(self, host_name):
        """
        删除主机记录目录
        :param host_name:
        :return:
        """
        rlt = self.delete_dir(host_name)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, "nodemonitor_deldir error:{}".format(rlt.message))
            return rlt
        return Result('')

    def read_moniternode_map(self, key):
        """
        读取map
        :param key:
        :return:{}
        """
        return self.read_map(key)
        
    def read_all(self):
        """
        :return:
        """
        return self.read_map()
            
            
        