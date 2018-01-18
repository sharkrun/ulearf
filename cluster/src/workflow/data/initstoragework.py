# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
初始化存储集群
"""

import time

from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR, TASK_CANCEL_ERR
from core.vespaceclient import VeSpaceClient, DEFAULT_STORAGE_DOMAIN, \
    HOST_TYPE_STRATEGY, \
    VESPACE_DATA_EXIST_ALREADY_EXIST_ERR, APPLICATION_HOST_PORT, \
    STRATEGY_HOST_PORT, DEFAULT_USER_NAME, DEFAULT_PASSWORD
from core.vespacehaclient import VeSpaceHAClient
from etcddb.kubernetes.clustermgr import Clusterdb
from etcddb.settingmgr import SettingMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.strategy import StrategyNodeDB
from frame.auditlogger import LogAdd
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class InitStorageWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "cluster_name":"",
            "ip0":""
        }
        """
        self.cluster_name = None
        self.ip0 = ''
        self.ip1 = ''
        self.ip2 = ''
        self.cluster_id = ''
        self.license_str = ''
        self.username = DEFAULT_USER_NAME
        self.password = DEFAULT_PASSWORD
        self.client = None
        super(InitStorageWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(InitStorageWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
        snap["username"] = self.username
        snap["password"] = self.password
        snap["cluster_id"] = self.cluster_id
        snap["license_str"] = self.license_str
        snap["ip0"] = self.ip0
        snap["ip1"] = self.ip1
        snap["ip2"] = self.ip2
        return snap
    
    
    def wait_for_ready(self):
        for _ in range(36):
            rlt = self.schedule_status()
            if not rlt.success:
                Log(4, 'skip current action, as the schedule is failed')
                return rlt
            time.sleep(5)
        return Result('ready')
        
        
    def check_valid(self):
        """
        # 检查数据
        """
        try:
            if self.client is None:
                self.client = self.get_vespace_client()
            
            rlt = SettingMgr.instance().get_vespace_license()
            if rlt.success:
                self.license_str = rlt.content
            else:
                Log(1, 'InitStorageWork.check_valid get_vespace_license fail,as[%s]'%(rlt.message))
                return rlt
                
        except InternalException,e:
            Log(1,"InitStorageWork.check_valid except[%s]"%(e.value))
            return Result("InitStorageWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("InitStorageWork",INTERNAL_EXCEPT_ERR,"InitStorageWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def get_vespace_client(self):
        if (self.ip1 and self.ip2):
            return VeSpaceHAClient([self.ip0, self.ip1, self.ip2], self.username, self.password)
        return VeSpaceClient(self.ip0, self.username, self.password)
    
    def ready(self):
        self.save_to_db()
        
    def is_service_ready(self):
        if Clusterdb.instance().clu_is_exist(self.cluster_name):
            return self.client and self.client.test() \
                and self.client.test_strategy_service(self.ip0) \
                and (self.client.test_strategy_service(self.ip1) if self.ip1 else True) \
                and (self.client.test_strategy_service(self.ip2) if self.ip2 else True)
         
        else:
            Log(1, 'The cluster[%s]lost'%(self.cluster_name))
            raise InternalException("cluster deleted.", TASK_CANCEL_ERR)
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'InitStorageWork.get_cluster_id get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip0, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id
    
    def create_cluster(self):
        rlt = self.client.create_cluster(self.cluster_name, self.ip0)
        if rlt.success:
            Log(1, 'InitStorageWork.create_cluster return [%s]'%(str(rlt.content)))
            self.cluster_id = rlt.content.get('uuid')
        else:
            Log(1, 'InitStorageWork.create_cluster [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip0, rlt.message))
        return rlt
    
    def delete_cluster(self):
        if not self.cluster_id:
            Log(4, 'delete_cluster skip, as the cluster id not exist.')
            return Result('done')
        
        rlt = self.client.delete_cluster(self.cluster_id)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.delete_cluster[%s]fail,as[%s]'%(self.cluster_name, rlt.message))
        return rlt
    
    def add_license(self):
        cluster_id = self.get_cluster_id()
        
        rlt = self.client.add_license(cluster_id, self.license_str)
        if not rlt.success:
            Log(1, 'InitStorageWork.add_license [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip0, rlt.message))
            return rlt
        
        cluster_info = rlt.content
        
        arr = [self.ip0]
        if self.ip1:
            arr.append(self.ip1)
            
        if self.ip2:
            arr.append(self.ip2)
        
        cluster_info['ip'] = ','.join(arr)
        cluster_info['cluster_id'] = self.cluster_id
        rlt = StoregeClusterDB.instance().create_cluster(self.cluster_name, cluster_info)
        if not rlt.success:
            Log(1, 'InitStorageWork.create_cluster[%s][%s]to etcd fail,as[%s]'%(self.cluster_name, self.ip0, rlt.message))
        return rlt
    
    
    def add_strategy_host(self, ip):
        rlt = self.client.add_host(self.cluster_id, DEFAULT_STORAGE_DOMAIN, ip, HOST_TYPE_STRATEGY)
        if rlt.success:
            port = rlt.content.get('port')
        elif VESPACE_DATA_EXIST_ALREADY_EXIST_ERR == rlt.result:
            Log(1, 'InitStorageWork.add_strategy_host [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
            port = APPLICATION_HOST_PORT
        else:            
            Log(1, 'InitStorageWork.add_strategy_host [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
            return rlt
    
        return Result(port)
    
    def delete_strategy_host(self, ip, port=STRATEGY_HOST_PORT):
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, DEFAULT_STORAGE_DOMAIN, ip, port, HOST_TYPE_STRATEGY)
        if not rlt.success:
            Log(1, 'InitStorageWork.delete_strategy_host [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
        
        rlt = StrategyNodeDB.instance().delete_node(self.cluster_name, ip)
        if not rlt.success:
            Log(1, 'InitStorageWork.delete_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
        
        return rlt
    
    def save_node_info(self):
        self._save_node_info(self.ip0)
        
        if self.ip1:
            self._save_node_info(self.ip1)
            
        if self.ip2:
            self._save_node_info(self.ip2)
        
        return Result('ok')
    
    def delete_node_info(self):
        self._delete_node_info(self.ip0)
        
        if self.ip1:
            self._delete_node_info(self.ip1)
            
        if self.ip2:
            self._delete_node_info(self.ip2)
        
        return Result('ok')
        
    
    def _delete_node_info(self, ip):
        rlt = StrategyNodeDB.instance().delete_node(self.cluster_name, ip)
        if not rlt.success:
            Log(1, 'InitStorageWork.delete_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
        
        return rlt
        
    
    def _save_node_info(self, ip):
        if StrategyNodeDB.instance().is_node_exist(self.cluster_name, ip):
            Log(2, 'save_node_info The node[%s][%s] exist already'%(self.cluster_name, ip))
        
        host_info = {'cluster': self.cluster_name,
                     'cluster_id': self.cluster_id,
                     'domain_name': DEFAULT_STORAGE_DOMAIN,
                     'ip': ip
                    }
        rlt = StrategyNodeDB.instance().create_node(self.cluster_name, ip, host_info)
        if not rlt.success:
            Log(1, 'InitStorageWork._save_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
        
        return rlt

    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"InitStorageWork.on_fail")
        LogAdd(1, 'system', u'创建存储集群[%s][%s]失败'%(self.cluster_name, self.ip0))

    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"InitStorageWork.on_success")
        LogAdd(3, 'system', u'创建存储集群[%s][%s]成功,ID=[%s]'%(self.cluster_name, self.ip0, self.cluster_id))


