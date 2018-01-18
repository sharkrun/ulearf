# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
初始化存储集群
"""

import time

from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR, INIT_VESPACE_CLIENT_FAILERR, \
    TASK_CANCEL_ERR, STORAGE_NODE_EXIST_ALREADY_ERR
from core.vespaceclient import DEFAULT_STORAGE_DOMAIN, \
    HOST_TYPE_APPLICATION, HOST_TYPE_STOREGE, \
    VESPACE_DATA_EXIST_ALREADY_EXIST_ERR, STOREGE_HOST_PORT, \
    APPLICATION_HOST_PORT
from core.vespacemgr import VespaceMgr
from etcddb.kubernetes.nodemgr import CluNodedb
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.node import StorageNodeDB
from frame.auditlogger import LogAdd
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class AddStorageNodeWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "repository":"",
            "tag":""
        }
        """
        self.cluster_name = ''
        self.cluster_id = ''
        self.ip = ''
        self.store_api_port = STOREGE_HOST_PORT
        self.app_api_port = APPLICATION_HOST_PORT
        self.client = None
        super(AddStorageNodeWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(AddStorageNodeWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
        snap["ip"] = self.ip
        snap["store_api_port"] = self.store_api_port
        snap["app_api_port"] = self.app_api_port
        snap["cluster_id"] = self.cluster_id
        return snap
        
        
    def check_valid(self):
        """
        # 检查数据
        """
        try:
            if self.client is None:
                self.client = VespaceMgr.instance().get_cluster_client(self.cluster_name)
            
            if not (self.client and self.client.test()):
                return Result('', INIT_VESPACE_CLIENT_FAILERR, 'init vespace client fail.')
            
            if StorageNodeDB.instance().is_node_exist(self.cluster_name, self.ip):
                return Result('', STORAGE_NODE_EXIST_ALREADY_ERR, 'The node is added.' )
                
        except InternalException,e:
            Log(1,"AddStorageNodeWork.check_valid except[%s]"%(e.value))
            return Result("AddStorageNodeWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("AddStorageNodeWork",INTERNAL_EXCEPT_ERR,"AddStorageNodeWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def ready(self):
        self.save_to_db()
        
    def wait_for_ready(self):
        for _ in range(36):
            rlt = self.schedule_status()
            if not rlt.success:
                Log(4, 'skip current action, as the schedule is failed')
                return rlt
            time.sleep(5)
        return Result('ready')
        
    def is_service_ready(self):
        if CluNodedb.instance().is_node_exist(self.cluster_name, self.ip):
            return self.client.test_storage_service(self.ip) \
                and self.client.test_application_service(self.ip)
        else:
            Log(1, 'The host[%s][%s] lost'%(self.cluster_name, self.ip))
            raise InternalException("host deleted.", TASK_CANCEL_ERR)
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'AddStorageNodeWork.add_node get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id

    def add_application_host(self):
        cluster_id = self.get_cluster_id()
        rlt = self.client.add_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, HOST_TYPE_APPLICATION)
        if rlt.success:
            self.app_api_port = rlt.content.get('port')
        elif VESPACE_DATA_EXIST_ALREADY_EXIST_ERR == rlt.result:
            Log(1, 'AddStorageNodeWork.add_application_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            self.app_api_port = APPLICATION_HOST_PORT
            return Result('ok')
        else:            
            Log(1, 'AddStorageNodeWork.add_application_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt
    
    def delete_application_host(self):
        if not self.app_api_port:
            Log(2, 'The application host[%s][%s] not added'%(self.cluster_name, self.ip))
            return Result('ok')
        
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, self.app_api_port, HOST_TYPE_APPLICATION)
        if not rlt.success:
            Log(1, 'AddStorageNodeWork.delete_application_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt

    def add_storage_host(self):
        cluster_id = self.get_cluster_id()
        rlt = self.client.add_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, HOST_TYPE_STOREGE)
        if rlt.success:
            self.store_api_port = rlt.content.get('port')
        elif VESPACE_DATA_EXIST_ALREADY_EXIST_ERR == rlt.result:
            Log(1, 'AddStorageNodeWork.add_storage_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            self.store_api_port = STOREGE_HOST_PORT
            return Result('ok')
        else:
            Log(1, 'AddStorageNodeWork.add_storage_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt
    
    def delete_storage_host(self):
        if not self.store_api_port:
            Log(2, 'The storage host[%s][%s] not added'%(self.cluster_name, self.ip))
            return Result('ok')
        
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, self.store_api_port, HOST_TYPE_STOREGE)
        if not rlt.success:
            Log(1, 'AddStorageNodeWork.delete_storage_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt
    
    def save_node_info(self):
        if StorageNodeDB.instance().is_node_exist(self.cluster_name, self.ip):
            Log(2, 'save_node_info The node[%s][%s] exist already'%(self.cluster_name, self.ip))
        
        host_info = {'cluster': self.cluster_name, 
                     'cluster_id': self.cluster_id, 
                     'domain_name': DEFAULT_STORAGE_DOMAIN, 
                     'ip': self.ip, 
                     'store_api_port':self.store_api_port,
                     'app_api_port':self.app_api_port
                     }
        rlt = StorageNodeDB.instance().create_node(self.cluster_name, self.ip, host_info)
        if not rlt.success:
            Log(1, 'AddStorageNodeWork.save_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        
        return rlt
       
    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"AddStorageNodeWork.on_fail")
        LogAdd(3, 'system', u'给存储集群[%s]添加存储节点[%s]失败'%(self.cluster_name, self.ip))
    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"AddStorageNodeWork.on_success")
        LogAdd(3, 'system', u'给存储集群[%s]添加存储节点[%s]成功'%(self.cluster_name, self.ip))

