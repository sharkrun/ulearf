# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
初始化存储集群
"""


from twisted.web import http

from common.util import Result
from core.const import STORAGE_CLASS_STATUS_NOT_READY, \
    STORAGE_CLASS_DEFAULT_NAMESPACE
from core.errcode import INTERNAL_EXCEPT_ERR, INIT_VESPACE_CLIENT_FAILERR, \
    TASK_CANCEL_ERR, STORAGE_NODE_NOT_EXIST_ERR, ETCD_KEY_NOT_FOUND_ERR, \
    INVALID_PARAM_ERR
from core.kubeclientmgr import KubeClientMgr
from core.vespaceclient import DEFAULT_STORAGE_DOMAIN, \
    HOST_TYPE_APPLICATION, HOST_TYPE_STOREGE, STOREGE_HOST_PORT, \
    APPLICATION_HOST_PORT
from core.vespacemgr import VespaceMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.disk import DiskDB
from etcddb.storage.mount import MountDB
from etcddb.storage.node import StorageNodeDB
from etcddb.storage.pv import PVDB
from etcddb.storage.storageclass import StorageClassDB
from etcddb.storage.volume import VolumeDB
from frame.auditlogger import LogDel
from frame.etcdv3 import ID
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class DeleteStorageNodeWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "repository":"",
            "tag":""
        }
        """
        self.cluster_name = ''
        self.cluster_id = ''
        self.operator = ''
        self.ip = ''
        self.store_api_port = STOREGE_HOST_PORT
        self.app_api_port = APPLICATION_HOST_PORT
        self.client = None
        super(DeleteStorageNodeWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(DeleteStorageNodeWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
        snap["operator"] = self.operator
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
            
            rlt = StorageNodeDB.instance().read_node_info(self.cluster_name, self.ip)
            if not rlt.success:
                Log(1, 'DeleteStorageNodeWork.check_valid read_node_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
                return Result('', STORAGE_NODE_NOT_EXIST_ERR, 'The node is not exist.' )
            
            self.store_api_port = rlt.content.get('store_api_port', STOREGE_HOST_PORT)
            self.app_api_port = rlt.content.get('app_api_port', APPLICATION_HOST_PORT)
                
        except InternalException,e:
            Log(1,"DeleteStorageNodeWork.check_valid except[%s]"%(e.value))
            return Result("DeleteStorageNodeWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("DeleteStorageNodeWork",INTERNAL_EXCEPT_ERR,"DeleteStorageNodeWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def ready(self):
        self.save_to_db()
        
    def is_service_ready(self):
        if StorageNodeDB.instance().is_node_exist(self.cluster_name, self.ip):
            return True
        else:
            Log(1, 'The host[%s][%s] lost'%(self.cluster_name, self.ip))
            raise InternalException("host deleted.", TASK_CANCEL_ERR)
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.get_cluster_id get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id
    
    def delete_application_host(self):
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, self.app_api_port, HOST_TYPE_APPLICATION)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_application_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt
    
    def delete_storage_host(self):
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_host(cluster_id, DEFAULT_STORAGE_DOMAIN, self.ip, self.store_api_port, HOST_TYPE_STOREGE)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_storage_host [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        return rlt
    
    def delete_node_info(self):
        rlt = StorageNodeDB.instance().delete_node(self.cluster_name, self.ip)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_node_info [%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
        
        return rlt
    
    def delete_storage_classes(self):
        rlt = StorageClassDB.instance().get_sc_by_mount_ip(self.cluster_name, self.ip)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork get_sc_by_mount_ip[%s][%s] fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            return Result('fail')
        
        for sc in rlt.content:
            if 'storage_class_name' in sc and sc['storage_class_name']:
                self.delete_storage_class(self.cluster_name, sc, self.operator)
                
        return Result(len(rlt.content))


    def delete_storage_class_from_db(self, storage_class):
        rlt = StorageClassDB.instance().delete_storage_class(self.cluster_name, storage_class)
        if rlt.success:
            LogDel(3,  self.operator, u'从集群[%s]删除共享卷[%s]成功'%(self.cluster_name, storage_class))
        else:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class delete_storage_class[%s][%s] from etcd[%s]fail,as[%s]'%(self.cluster_name, storage_class, rlt.message))
        return rlt
    
    
    def delete_pvs(self):
        rlt = MountDB.instance().get_volume_by_mount_ip(self.cluster_name, self.ip)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pvs get_volume_by_mount_ip[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            return Result('done')
        
        if not len(rlt.content):
            Log(1, 'DeleteStorageNodeWork.delete_pvs [%s][%s]success,as[not mount volumes]'%(self.cluster_name, self.ip))
            return Result('done')
        
        for volume_name in rlt.content:
            self.delete_pv(self.cluster_name, volume_name, self.operator)
                
        return Result(len(rlt.content))
    
    def delete_storage_class(self, cluster_name, info, operator):
        storage_class = info.get('storage_class_name')
        if info.get('status') == STORAGE_CLASS_STATUS_NOT_READY:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class [%s][%s]fail,as[The storage class not ready]'%(cluster_name, storage_class))
            return self.delete_storage_class_from_db(storage_class)
        
        kube_client = KubeClientMgr.instance().get_cluster_client(cluster_name)
        if kube_client is None:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class get_cluster_client[%s]fail'%(cluster_name))
            return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid', http.BAD_REQUEST)
        
        rlt = kube_client.remove_storage_class_deploy(STORAGE_CLASS_DEFAULT_NAMESPACE, storage_class)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class remove_storage_class_deploy[%s]fail,as[%s]'%(storage_class, rlt.message))
            return rlt

        mount_node_list = []
        rlt = MountDB.instance().read_mount_list(cluster_name, info.get('volume_name'))
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class read_mount_list[%s]fail,as[%s]'%(cluster_name, info.get('volume_name'), rlt.message))
        else:
            mount_node_list = rlt.content
        
        rlt = self.delete_volume(cluster_name, info.get('volume_id'), mount_node_list)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class delete_volume[%s]fail,as[%s]'%(storage_class, rlt.message))
        
        rlt = kube_client.delete_storage_class(storage_class)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_storage_class delete_storage_class[%s]fail,as[%s]'%(storage_class, rlt.message))
        
        return self.delete_storage_class_from_db(storage_class)
    
    def delete_volume(self, cluster_name, volume_id, mount_node_list):
        rlt = VolumeDB.instance().read_volume_info(cluster_name, volume_id)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_volume read_volume_info[%s][%s]fail,as[%s]'%(cluster_name, volume_id, rlt.message))
            return rlt
        
        volume = rlt.content
        
        app_node_list = []
        mount_id_list = []
        for node in rlt.mount_node_list:
            mount_id_list.append(node.get(ID))
            app_node_list.append({'ip':node.get('ip'), 'port':node.get('port')})
            
        if app_node_list:
            rlt = self.client.unmount_volume(volume, app_node_list)
            if not rlt.success:
                Log(1, 'DeleteStorageNodeWork.delete_volume unmount_volume[%s][%s]fail,as[%s]'%(cluster_name, volume.get('name'), rlt.message))
                return rlt
            
            MountDB.instance().delete_mount_records(cluster_name, mount_id_list)
        
        cluster_id = self.get_cluster_id()
        rlt = self.client.delete_volume(cluster_id, volume.get('name'))
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_volume delete_volume[%s][%s]fail,as[%s]'%(cluster_name, volume.get('name'), rlt.message))
            return rlt
        
        rlt = VolumeDB.instance().delete_volume(cluster_name, volume_id)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_volume delete_volume[%s][%s] from etcd fail,as[%s]'%(cluster_name, volume_id, rlt.message))
        return rlt
    
    def umount_volume(self, cluster_name, volume_id, mount_node_list):
        node_list = []
        mount_id = ''
        for node in mount_node_list:
            if node.get('ip') == self.ip:
                node_list.append({'ip':node.get('ip'),'port':node.get('port')})
                mount_id = node.get(ID)
                
        if not node_list:
            Log(1, 'umount_volume[%s][%s]fail,as the volume not mount to this host[%s]'%(cluster_name, volume_id, self.ip))
            return Result('skip')
        
        rlt = VolumeDB.instance().read_volume_info(cluster_name, volume_id)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_volume read_volume_info[%s][%s]fail,as[%s]'%(cluster_name, volume_id, rlt.message))
            return rlt
        
        volume = rlt.content
        rlt = self.client.unmount_volume(volume, node_list)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_volume unmount_volume[%s][%s]fail,as[%s]'%(cluster_name, volume.get('name'), rlt.message))
            return rlt
        
        rlt = MountDB.instance().delete_mount_record(cluster_name, mount_id)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.umount_volume delete_mount_record[%s][%s] from etcd fail,as[%s]'%(cluster_name, mount_id, rlt.message))
        return rlt
                
    def delete_pv(self, cluster_name, volume_name, operator):
        mount_node_list = []
        rlt = MountDB.instance().read_mount_list(cluster_name, volume_name)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pv read_mount_list[%s]fail,as[%s]'%(cluster_name, volume_name, rlt.message))
        else:
            mount_node_list = rlt.content
        
        if len(mount_node_list) > 1:
            return self.umount_volume(cluster_name, volume_name, mount_node_list)
        
        return self._delete_pv(cluster_name, volume_name, mount_node_list, operator)
    
    def _delete_pv(self, cluster_name, volume_name, mount_node_list, operator):
        kube_client = KubeClientMgr.instance().get_cluster_client(cluster_name)
        if kube_client is None:
            Log(1, 'DeleteStorageNodeWork.delete_pv get_cluster_client[%s]fail'%(cluster_name))
            return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid', http.BAD_REQUEST)
        
        rlt = PVDB.instance().read_pv_info_by_volume_id(cluster_name, volume_name)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pv read_pv_info_by_volume_id[%s][%s]fail,as[%s]'%(cluster_name, volume_name, rlt.message))
            return self.delete_volume(cluster_name, volume_name, mount_node_list)
        
        pv_info = rlt.content
        rlt = self.delete_volume(cluster_name, volume_name, mount_node_list)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pv _delete_volume[%s]fail,as[%s]'%(volume_name, rlt.message))
            return rlt
        
        pv_name = pv_info.get('pv_name')
        rlt = kube_client.delete_persistent_volume_claim(pv_info['workspace'], pv_name)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pv delete_persistent_volume_claim[%s]fail,as[%s]'%(pv_name, rlt.message))
        
        rlt = kube_client.delete_persistent_volume(pv_name)
        if not rlt.success:
            Log(1, 'DeleteStorageNodeWork.delete_pv delete_persisten_tvolume[%s]fail,as[%s]'%(pv_name, rlt.message))
        
        rlt = PVDB.instance().delete_volume(cluster_name, pv_name)
        if rlt.success:
            LogDel(3,  operator, u'从集群[%s]删除容器卷[%s]'%(cluster_name, pv_name))
        else:
            Log(1, 'DeleteStorageNodeWork.delete_pv delete_volume[%s][%s] in etcd[%s]fail,as[%s]'%(cluster_name, pv_name, rlt.message))
        return rlt
    
    
    def delete_data_disk(self):
        rlt = DiskDB.instance().read_disk_list(self.ip)
        if not rlt.success:
            if rlt.result ==  ETCD_KEY_NOT_FOUND_ERR:
                return Result(0)
            
            Log(1, 'DeleteStorageNodeWork.delete_data_disk read_disk_list fail,as[%s]'%(rlt.message))
            return rlt
        
        device_list = rlt.content
        if len(device_list) == 0:
            return Result('nothing to do')
        
        delete_disk_list = [dev['Path'] for dev in device_list]
        rlt = self.client.delete_data_disk(device_list[0]['cluster_id'],
                                      device_list[0]['domain_name'],
                                      device_list[0]['ip'],
                                      device_list[0]['store_api_port'],
                                      delete_disk_list)
        if rlt.success:
            LogDel(3, 'system', u'从存储集群[%s][%s]移除全部数据盘成功'%(self.cluster_name, self.ip))
        else:
            LogDel(3, 'system', u'从存储集群[%s][%s]移除全部数据盘失败，因为【%s】'%(self.cluster_name, self.ip, rlt.message))
        
        for disk in device_list:
            rlt = DiskDB.instance().delete_disk(self.ip, disk['disk_id'])
            if not rlt.success:
                Log(1, 'DeleteStorageNodeWork.delete_data_disk delete_disk in etcd fail,as[%s]'%(rlt.message))
                
        return Result(len(delete_disk_list))
       
    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"DeleteStorageNodeWork.on_fail")
        LogDel(1, 'system', u'从存储集群[%s]删除存储节点[%s]失败'%(self.cluster_name, self.ip))

    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"DeleteStorageNodeWork.on_success")
        LogDel(3, 'system', u'从存储集群[%s]删除存储节点[%s]成功'%(self.cluster_name, self.ip))


