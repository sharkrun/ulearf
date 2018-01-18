# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
初始化存储集群
"""

from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR, INIT_VESPACE_CLIENT_FAILERR, \
    TASK_CANCEL_ERR, LAST_CLUSTER_CANNOT_DELETE_ERR
from core.vespaceclient import STRATEGY_HOST_PORT, \
    HOST_TYPE_STRATEGY
from core.vespacemgr import VespaceMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.strategy import StrategyNodeDB
from frame.auditlogger import LogDel
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class DeleteStorageWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "repository":"",
            "tag":""
        }
        """
        self.cluster_name = None
        self.cluster_id = ''
        self.client = None
        super(DeleteStorageWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(DeleteStorageWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
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
            
            if StoregeClusterDB.instance().get_cluster_num(self.cluster_name) <= 1:
                return Result('', LAST_CLUSTER_CANNOT_DELETE_ERR, 'The last cluster can not be delete')
                
        except InternalException,e:
            Log(1,"DeleteStorageWork.check_valid except[%s]"%(e.value))
            return Result("DeleteStorageWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("DeleteStorageWork",INTERNAL_EXCEPT_ERR,"DeleteStorageWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def ready(self):
        self.save_to_db()
        
    def is_service_ready(self):
        if StoregeClusterDB.instance().is_cluster_exist(self.cluster_name):
            return True
        else:
            Log(1, 'The cluster[%s]lost'%(self.cluster_name))
            raise InternalException("cluster deleted.", TASK_CANCEL_ERR)
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.get_cluster_id get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id
    
    def delete_strategy_host(self):
        rlt = StrategyNodeDB.instance().read_node_list(self.cluster_name)
        if not rlt.success:
            Log(1, 'delete_strategy_host read_node_list[%s] fail,as[%s]'%(self.cluster_name, rlt.message))
            return rlt
        
        for host in rlt.content:
            self._delete_strategy_host(host.get('ip'))
            
        return Result('ok')
    
    def _delete_strategy_host(self, ip, port=STRATEGY_HOST_PORT):
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, STRATEGY_HOST_PORT, ip, port, HOST_TYPE_STRATEGY)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.delete_strategy_host [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
            
        rlt = StrategyNodeDB.instance().delete_node(self.cluster_name, ip)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.delete_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, ip, rlt.message))
        
        return rlt
    
    def delete_cluster(self):
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_cluster(cluster_id)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.delete_cluster[%s]fail,as[%s]'%(self.cluster_name, rlt.message))
        return rlt
    
    def delete_cluster_info(self):
        StrategyNodeDB.instance().delete_cluster(self.cluster_name)
        
        rlt = StoregeClusterDB.instance().delete_cluster(self.cluster_name)
        if not rlt.success:
            Log(1, 'DeleteStorageWork.delete_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        
        return rlt

    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"DeleteStorageWork.on_fail")
        LogDel(1, 'system', u'删除存储集群[%s]失败'%(self.cluster_name))

    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"DeleteStorageWork.on_success")
        LogDel(3, 'system', u'删除存储集群[%s]成功'%(self.cluster_name))


