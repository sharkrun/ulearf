# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
'''
Created on 2017年8月11日

@author: Jack
'''
import threading

from twisted.web import http

from common.guard import LockGuard
from common.util import Result
from core.const import STORAGE_CLASS_STATUS_NOT_READY, \
    STORAGE_CLASS_DEFAULT_NAMESPACE
from core.errcode import INVALID_PARAM_ERR, STORAGE_CLASS_NOT_READY_ERR, \
    INIT_VESPACE_CLIENT_FAILERR
from core.kubeclientmgr import KubeClientMgr
from core.vespacemgr import VespaceMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.mount import MountDB
from etcddb.storage.pv import PVDB
from etcddb.storage.storageclass import StorageClassDB
from etcddb.storage.volume import VolumeDB
from frame.auditlogger import LogDel
from frame.etcdv3 import ID
from frame.logger import Log
from workflow.data.addnodework import AddStorageNodeWork
from workflow.data.addpvwork import AddPVWork
from workflow.data.addstorageclasswork import AddStorageClassWork
from workflow.data.deletenodework import DeleteStorageNodeWork
from workflow.data.deletestoragework import DeleteStorageWork
from workflow.data.initstoragework import InitStorageWork
from workflow.workflowmgr import WorkFlowMgr


class StorageMgr(object):
    '''
    classdocs
    '''
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        '''
        Constructor
        '''
        pass

    def init_storage_cluster(self, cluster_name, masters):
        task_info = {}
        task_info['cluster_name'] = cluster_name
        
        if isinstance(masters, basestring):
            task_info['ip0'] = masters
        else:
            num = len(masters)
            if num < 1:
                Log(1, 'init_storage_cluster[%s][%s]fail,as[Parameter invalid]'%(cluster_name, str(masters)))
                return Result('', INVALID_PARAM_ERR, 'ip invalid')
            
            for i in range(0, num):
                task_info['ip%s'%(i)] = masters[i].get('HostIP')
        
        workbench = InitStorageWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'init_storage_cluster[%s] fail,as[%s]'%(cluster_name, rlt.message))
            return rlt

        workbench.ready()
        rlt = WorkFlowMgr.instance().create_init_storage_cluster_task(task_info, workbench)
        if not rlt.success:
            return rlt

        return Result('ok')

    def delete_storage_cluster(self, cluster_name):
        task_info = {}
        task_info['cluster_name'] = cluster_name
        workbench = DeleteStorageWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'delete_storage_cluster[%s] fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        workbench.ready()
        rlt = WorkFlowMgr.instance().create_delete_storage_cluster_task(task_info, workbench)
        if rlt.success:
            return Result('ok')
        
        return rlt

    def add_storage_node(self, cluster_name, node_ip):
        task_info = {}
        task_info['cluster_name'] = cluster_name
        task_info['ip'] = node_ip
        workbench = AddStorageNodeWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'add_storage_node[%s][%s] fail,as[%s]'%(cluster_name, node_ip, rlt.message))
            return rlt
        
        workbench.ready()
        rlt = WorkFlowMgr.instance().create_add_storage_host_task(task_info, workbench)
        if rlt.success:
            return Result('ok')
        
        return rlt
    
    def delete_storage_node(self, cluster_name, node_name, operator):
        task_info = {}
        task_info['cluster_name'] = cluster_name
        task_info['ip'] = node_name.replace('-', '.')
        task_info['operator'] = operator
        workbench = DeleteStorageNodeWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'delete_storage_node[%s][%s] fail,as[%s]'%(cluster_name, node_name, rlt.message))
            return rlt
        
        workbench.ready()
        rlt = WorkFlowMgr.instance().create_delete_storage_host_task(task_info, workbench)
        if rlt.success:
            return Result('ok')
        
        return rlt
    
    def delete_pv(self, cluster_name, pv_name, operator):
        rlt = PVDB.instance().read_volume_info(cluster_name, pv_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_pv read_volume_info[%s][%s]fail,as[%s]'%(cluster_name, pv_name, rlt.message))
            return rlt
        
        pv_info = rlt.content 
        kube_client = KubeClientMgr.instance().get_cluster_client(cluster_name)
        if kube_client is None:
            Log(1, 'StorageMgr.delete_pv get_cluster_client[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid', http.BAD_REQUEST)
        
        rlt = self.delete_volume(cluster_name, pv_info.get('volume_id'))
        if not rlt.success:
            Log(1, 'StorageMgr.delete_pv _delete_volume[%s]fail,as[%s]'%(pv_name, rlt.message))
            return rlt
        
        rlt = kube_client.delete_persistent_volume_claim(pv_info['workspace'], pv_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_pv delete_persistent_volume_claim[%s]fail,as[%s]'%(pv_name, rlt.message))
        
        rlt = kube_client.delete_persistent_volume(pv_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_pv delete_persisten_tvolume[%s]fail,as[%s]'%(pv_name, rlt.message))
        
        rlt = PVDB.instance().delete_volume(cluster_name, pv_name)
        if rlt.success:
            LogDel(3,  operator, u'从集群[%s]删除容器卷[%s]'%(cluster_name, pv_name))
        else:
            Log(1, 'StorageMgr.delete_pv delete_volume[%s][%s] in etcd[%s]fail,as[%s]'%(cluster_name, pv_name, rlt.message))
        return rlt
    
    def delete_volume(self, cluster_name, volume_id):
        rlt = StoregeClusterDB.instance().get_cluster_info(cluster_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume get_cluster_info[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        cluster_id = rlt.content.get('cluster_id')
        rlt = VolumeDB.instance().read_volume_info(cluster_name, volume_id)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume read_volume_info[%s][%s]fail,as[%s]'%(cluster_name, volume_id, rlt.message))
            return rlt
        
        volume = rlt.content
        
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        if not client:
            Log(1, 'StorageMgr.delete_volume get_cluster_client[%s]fail'%(cluster_name))
            return Result('', INIT_VESPACE_CLIENT_FAILERR, 'get_cluster_client fail')
        
        app_node_list = []
        mount_id_list = []
        rlt = MountDB.instance().read_mount_list(cluster_name, volume.get('name'))
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume read_mount_list[%s][%s]fail,as[%s]'%(cluster_name, volume_id, rlt.message))
        else:
            for node in rlt.content:
                mount_id_list.append(node.get(ID))
                app_node_list.append({'ip':node.get('ip'), 'port':node.get('port')})

        if app_node_list:
            rlt = client.unmount_volume(volume, app_node_list)
            if not rlt.success:
                Log(1, 'StorageMgr.delete_volume unmount_volume[%s][%s]fail,as[%s]'%(cluster_name, volume.get('name'), rlt.message))
                return rlt
            MountDB.instance().delete_mount_records(cluster_name, mount_id_list)
        
        rlt = client.delete_volume(cluster_id, volume.get('name'))
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume delete_volume[%s][%s]fail,as[%s]'%(cluster_name, volume.get('name'), rlt.message))
            return rlt
        
        rlt = VolumeDB.instance().delete_volume(cluster_name, volume_id)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume delete_volume[%s][%s] from etcd fail,as[%s]'%(cluster_name, volume_id, rlt.message))
        return rlt
    
    
    def delete_workspace_pv(self, cluster_name, workspace, operator):
        rlt = PVDB.instance().read_volume_list(cluster_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_workspace_pv read_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        success = []
        fail = []
        for pv in rlt.content:
            if pv.get('workspace') == workspace:
                ret = self.delete_pv(cluster_name, pv.get('pv_name'), operator)
                if ret.success:
                    success.append(pv.get('pv_name'))
                else:
                    fail.append(pv.get('pv_name'))
            
        Log(3, 'StorageMgr.delete_workspace_pv from [%s]success:%s,fail:%s'%(workspace, str(success), str(fail)))
            
        return Result({'success':len(success), 'fail':len(fail)})
            
        
        
    def create_persistent_volume(self, task_info):
        workbench = AddPVWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'create_persistent_volume[%s]fail,as[%s]'%(str(task_info), rlt.message))
            return rlt
        
        workbench.ready()
        rlt = WorkFlowMgr.instance().create_persistent_volume_task(task_info, workbench)
        if rlt.success:
            return Result('ok')
        
        return rlt  
        
    def create_storage_class(self, task_info):
        workbench = AddStorageClassWork(task_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'create_storage_class[%s]fail,as[%s]'%(str(task_info), rlt.message))
            return rlt
        
        workbench.ready()
        rlt = WorkFlowMgr.instance().create_storage_class_task(task_info, workbench)
        if rlt.success:
            return Result('ok')
        
        return rlt  
        
    def delete_storage_class(self, cluster_name, storage_class, operator):
        rlt = StorageClassDB.instance().read_storage_class_info(cluster_name, storage_class)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_storage_class read_storage_class_info[%s][%s]fail,as[%s]'%(cluster_name, storage_class, rlt.message))
            return rlt
        
        info = rlt.content
        if info.get('status') == STORAGE_CLASS_STATUS_NOT_READY:
            Log(1, 'StorageMgr.delete_storage_class [%s][%s]fail,as[The storage class not ready]'%(cluster_name, storage_class))
            return Result('', STORAGE_CLASS_NOT_READY_ERR, 'The storage class not ready')
        
        kube_client = KubeClientMgr.instance().get_cluster_client(cluster_name)
        if kube_client is None:
            Log(1, 'StorageMgr.delete_storage_class get_cluster_client[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid', http.BAD_REQUEST)
        
        rlt = kube_client.remove_storage_class_deploy(STORAGE_CLASS_DEFAULT_NAMESPACE, storage_class)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_storage_class remove_storage_class_deploy[%s]fail,as[%s]'%(storage_class, rlt.message))
            return rlt
        
        rlt = self.delete_volume(cluster_name, info.get('volume_id'))
        if not rlt.success:
            Log(1, 'StorageMgr.delete_storage_class delete_volume[%s]fail,as[%s]'%(storage_class, rlt.message))
        
        rlt = kube_client.delete_storage_class(storage_class)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_storage_class delete_storage_class[%s]fail,as[%s]'%(storage_class, rlt.message))
        
        rlt = StorageClassDB.instance().delete_storage_class(cluster_name, storage_class)
        if rlt.success:
            LogDel(3,  operator, u'从集群[%s]删除共享卷[%s]成功'%(cluster_name, storage_class))
        else:
            Log(1, 'StorageMgr.delete_storage_class delete_storage_class[%s][%s] from etcd[%s]fail,as[%s]'%(cluster_name, storage_class, rlt.message))
        return rlt
    
    
    def delete_group_storage_class(self, group, operator):
        rlt = StorageClassDB.instance().get_sc_by_group(group)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_group_storage_class get_sc_by_group[%s]fail,as[%s]'%(group, rlt.message))
            return rlt
        
        success = []
        fail = []
        for sc in rlt.content:
            ret = self.delete_storage_class(sc.get('cluster_name'), sc.get('storage_class_name'), operator)
            if ret.success:
                success.append(sc.get('storage_class_name'))
            else:
                fail.append(sc.get('storage_class_name'))

            
        Log(3, 'StorageMgr.delete_group_storage_class [%s]success:%s,fail:%s'%(group, str(success), str(fail)))
            
        return Result({'success':len(success), 'fail':len(fail)})
    
    
    
    
    