# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
初始化存储集群
"""


from random import Random

from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR, INIT_VESPACE_CLIENT_FAILERR, \
    TASK_CANCEL_ERR, INVALID_PARAM_ERR, VESPACE_RESULT_INVALID_ERROR
from core.kubeclientmgr import KubeClientMgr
from core.vespaceclient import DEFAULT_STORAGE_DOMAIN, \
    STORAGE_SHARE_TYPE_NFS, \
    DEFAULT_STORAGE_POOL_NAME, STORAGE_SHARE_TYPE_ISCSI, APPLICATION_HOST_PORT
from core.vespacemgr import VespaceMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.mount import MountDB
from etcddb.storage.node import StorageNodeDB
from etcddb.storage.pv import PVDB
from etcddb.storage.volume import VolumeDB
from frame.auditlogger import LogAdd
from frame.etcdv3 import ID
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class AddPVWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "cluster_name":"",
            "ip":"",
            "group":"",
            "pv_name":"",
            "capacity":"",
            "read_write_mode":"",
            "recovery_model":"",
            "volume_type":"",
            "creator":"",
            "replica":"",
            "workspace":""
        }
        """
        self.cluster_name = ''
        self.ip = ''
        self.group = ''
        self.pv_name = ''
        self.capacity = ''
        self.read_write_mode = ''
        self.recovery_model = ''
        self.volume_type = ''
        self.creator = ''
        self.replica = 2
        self.workspace = ''
        
        self.volume_status = 0
        self.cluster_id = ''
        self.data_volume_server = ''
        self.data_volume_path = ''
        self.volume_id = ''
        self.storage_access_path = ''
        self.app_node_list = []
        self.veclient = None
        self.kubeclient = None
        self.targetdport = 0
        super(AddPVWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(AddPVWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
        snap["cluster_id"] = self.cluster_id
        snap["workspace"] = self.workspace
        snap["ip"] = self.ip
        snap["pv_name"] = self.pv_name
        snap["group"] = self.group
        snap["capacity"] = self.capacity
        snap["read_write_mode"] = self.read_write_mode
        snap["recovery_model"] = self.recovery_model
        snap["volume_type"] = self.volume_type
        snap["volume_id"] = self.volume_id
        snap["storage_access_path"] = self.storage_access_path
        snap["data_volume_server"] = self.data_volume_server
        snap["data_volume_path"] = self.data_volume_path
        snap["creator"] = self.creator
        snap["volume_status"] = self.volume_status
        snap["app_node_list"] = self.app_node_list
        snap["targetdport"] = self.targetdport
        return snap
        
        
    def check_valid(self):
        """
        # 检查数据
        """
        try:
            if not StorageNodeDB.instance().is_app_node_exist(self.cluster_name, self.ip):
                return Result('', INVALID_PARAM_ERR, 'mount host is invalid')
                                                          
            if self.veclient is None:
                self.veclient = VespaceMgr.instance().get_cluster_client(self.cluster_name)
            
            if not self.veclient.test():
                return Result('', INIT_VESPACE_CLIENT_FAILERR, 'init vespace client fail.')
            
            kube_client = KubeClientMgr.instance().get_cluster_client(self.cluster_name)
            if kube_client is None:
                Log(1, 'AddPVWork.check_valid get_cluster_client[%s]fail'%(self.cluster_name))
                return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid')
            else:
                self.kubeclient = kube_client
                
            if self.recovery_model not in ['Retain', 'Recycle', 'Delete']:
                self.recovery_model = 'Delete'
                
        except InternalException,e:
            Log(1,"AddPVWork.check_valid except[%s]"%(e.value))
            return Result("AddPVWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("AddPVWork",INTERNAL_EXCEPT_ERR,"AddPVWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def ready(self):
        self.save_to_db()
        
    def is_volume_exist(self):
        if PVDB.instance().is_volume_exist(self.cluster_name, self.pv_name):
            return True
        else:
            Log(1, 'The volume[%s][%s] lost'%(self.cluster_name, self.pv_name))
            raise InternalException("pv deleted.", TASK_CANCEL_ERR)
        
    def update_pv_info(self):
        if not self.volume_id:
            Log(1, 'AddPVWork.update_pv_info fail,as[the volume_id invalid]')
            return Result('', INVALID_PARAM_ERR, 'the volume_id invalid')
        
        info = {'volume_id': self.volume_id, 
                'access_path':self.storage_access_path, 
                'status':self.volume_status}
        rlt = PVDB.instance().update_volume(self.cluster_name, self.pv_name, info)
        if not rlt.success:
            Log(1, 'AddPVWork.update_pv_info update_volume[%s][%s]fail,as[%s]'%(self.cluster_name, self.pv_name, rlt.message))
        return rlt
        
    def delete_pv(self):
        rlt = PVDB.instance().delete_volume(self.cluster_name, self.pv_name)
        if not rlt.success:
            Log(1, 'AddPVWork.delete_pv delete_volume[%s][%s]fail,as[%s]'%(self.cluster_name, self.pv_name, rlt.message))
        return rlt
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'AddPVWork.get_cluster_id get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id

    
    def create_data_volume(self):
        data = {}
        data['ip'] = self.ip
        data['name'] = self.pv_name
        data['capacity'] = self.capacity
        data['share_type'] = self.volume_type
        data['replica'] = self.replica
        data['cluster_id'] = self.get_cluster_id()
        if self.volume_type == STORAGE_SHARE_TYPE_ISCSI:
            self.targetdport = VolumeDB.instance().get_iscsi_target_port(self.cluster_name)
            data['target_port'] = self.targetdport
            
        rlt = self.veclient.create_volume(data)
        if not rlt.success:
            Log(1, 'AddPVWork.create_data_volume create_volume[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        rlt = self.veclient.get_volume_info(data['cluster_id'], DEFAULT_STORAGE_DOMAIN, DEFAULT_STORAGE_POOL_NAME, data['name'])
        if not rlt.success:
            Log(1, 'AddPVWork.create_data_volume get_volume_info[%s][%s]fail,as[%s]'%(data['cluster_id'], data['name'], rlt.message))
            return rlt
        
        volume_info = rlt.content
        rlt = self.parse_volume_accesspath(volume_info.get('accesspath'))
        if not rlt.success:
            Log(1, 'AddPVWork.create_data_volume parse_volume_accesspath[%s]fail,as[%s]'%(str(volume_info.get('accesspath')), rlt.message))
            return rlt
        
        rlt = MountDB.instance().create_mount_record(self.cluster_name, data)
        if not rlt.success:
            Log(1, 'AddPVWork.create_data_volume create_mount_record[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        self.volume_status = volume_info.get('status', 0)
        data['creator'] = self.creator
        data['cluster_name'] = self.cluster_name
        data['bind'] = self.pv_name
        data['status'] = self.volume_status
        data['flag'] = volume_info.get('flag', 0)
        data['capacity_num'] = volume_info.get('capacity',0)
        data['mounted'] = volume_info.get('mounted',[])
        data['accesspath'] = volume_info.get('accesspath',[])
        data['controllerhosts'] = volume_info.get('controllerhosts',{}).get('default',[])
        rlt = VolumeDB.instance().create_volume(self.cluster_name, data)
        if rlt.success:
            self.volume_id = rlt.content
        else:
            Log(1, 'AddPVWork.create_data_volume create_volume in etcd[%s]fail,as[%s]'%(str(data), rlt.message))
        return rlt
    
    def delete_data_volume(self):
        if not self.volume_id:
            return Result('done')
        
        rlt = VolumeDB.instance().read_volume_info(self.cluster_name, self.volume_id)
        if not rlt.success:
            Log(1, 'AddPVWork.read_volume_info [%s][%s]from etcd fail,as[%s]'%(self.cluster_name, self.volume_id, rlt.message))
            return rlt
        
        volume = rlt.content
        
        app_node_list = []
        mount_id_list = []
        rlt = MountDB.instance().read_mount_list(self.cluster_name, self.pv_name)
        if not rlt.success:
            Log(1, 'StorageMgr.delete_data_volume read_mount_list[%s][%s]fail,as[%s]'%(self.cluster_name, self.pv_name, rlt.message))
        else:
            for node in rlt.content:
                mount_id_list.append(node.get(ID))
                app_node_list.append({'ip':node.get('ip'), 'port':node.get('port')})

        if app_node_list:
            rlt = self.veclient.unmount_volume(volume, app_node_list)
            if not rlt.success:
                Log(1, 'StorageMgr.delete_volume unmount_volume[%s][%s]fail,as[%s]'%(self.cluster_name, volume.get('name'), rlt.message))
                return rlt
            MountDB.instance().delete_mount_records(self.cluster_name, mount_id_list)
        
        rlt = self.veclient.delete_volume(volume['cluster_id'], volume.get('name'))
        if not rlt.success:
            Log(1, 'StorageMgr.delete_volume delete_volume[%s][%s]fail,as[%s]'%(self.cluster_name, volume.get('name'), rlt.message))
            return rlt
        
        rlt = VolumeDB.instance().delete_volume(self.cluster_name, self.volume_id)
        if not rlt.success:
            Log(1, 'AddPVWork.delete_data_volume delete_volume[%s][%s]from etcd fail,as[%s]'%(self.cluster_name, self.volume_id, rlt.message))
        return rlt
    
    
    def parse_volume_accesspath(self, access_path_list):
        if not isinstance(access_path_list, list) or len(access_path_list) < 1:
            return Result('', VESPACE_RESULT_INVALID_ERROR, '[%s][%s][%s]accesspath invalid'%(self.cluster_name, self.ip, self.pv_name))

        if self.volume_type == STORAGE_SHARE_TYPE_NFS:
            arr = access_path_list[0].split(':')
        else:
            arr = access_path_list[0].split(' ')
            
        if len(arr) != 2:
            return Result('', VESPACE_RESULT_INVALID_ERROR, '[%s][%s][%s]accesspath invalid'%(self.cluster_name, self.ip, self.pv_name))
        
        self.data_volume_server = arr[0]
        self.data_volume_path = arr[1]
        self.storage_access_path = access_path_list[0]
        return Result('ok')
        
    
    def create_persistent_volume(self):
        if self.volume_type == STORAGE_SHARE_TYPE_NFS:
            pv_cfg = self.nfs_volume()
        else:
            pv_cfg = self.iscsi_volume()
            
        rlt = self.kubeclient.create_persistent_volume(pv_cfg)
        if not rlt.success:
            Log(1, 'AddPVWork.add_pv create_persistent_volume[%s]fail,as[%s]'%(str(pv_cfg), rlt.message))
        return rlt
    
    
    def delete_persistent_volume(self):
        rlt = self.kubeclient.delete_persistent_volume(self.pv_name)
        if not rlt.success:
            Log(1, 'AddPVWork.add_pv delete_persistent_volume[%s]fail,as[%s]'%(self.pv_name, rlt.message))
        return rlt
        
    def create_persistent_volume_claim(self):
        pvc_cfg = self.persistent_volume_claim()
        rlt = self.kubeclient.create_persistent_volume_claim(self.workspace, pvc_cfg)
        if not rlt.success:
            Log(1, 'AddPVWork.add_pv create_persistent_volume[%s]fail,as[%s]'%(str(pvc_cfg), rlt.message))
        return rlt
    
    
    def delete_persistent_volume_claim(self):
        rlt = self.kubeclient.delete_persistent_volume_claim(self.workspace, self.pv_name)
        if not rlt.success:
            Log(1, 'AddPVWork.add_pv delete_persistent_volume_claim[%s][%s]fail,as[%s]'%(self.workspace, self.pv_name, rlt.message))
        return rlt
    
    def parse_access_mode(self, mode):
        if mode == 'RWO':
            return "ReadWriteOnce"
        elif mode == 'ROX':
            return "ReadOnlyMany"
        elif mode == 'RWX':
            return "ReadWriteMany"
        else:
            return "ReadOnlyMany"
    
    def nfs_volume(self):
        accessmode = self.parse_access_mode(self.read_write_mode or 'RWX')
        return {
            "kind" : "PersistentVolume",
            "apiVersion" : "v1",
            "metadata" : {
                "name" : self.pv_name,
                "namespace": self.workspace,
                "clusterName" : self.cluster_name
            },
            "spec" : {
                "capacity" : {
                    "storage": self.capacity + 'i'
                },
                "nfs" : {
                    "server" : self.data_volume_server,
                    "path" : self.data_volume_path,
                    "readOnly" : False
                },
                "accessModes" : [accessmode],
                "persistentVolumeReclaimPolicy" : self.recovery_model,
                "storageClassName" : "slow"
            }
        }
        
    def iscsi_volume(self):
        accessmode = self.parse_access_mode(self.read_write_mode or 'ROX')
        portals = []
        for node in self.app_node_list:
            portals.append('%s:%s'%(node.get('ip'), self.targetdport))
            
        return {
            "kind" : "PersistentVolume",
            "apiVersion" : "v1",
            "metadata" : {
                "name" : self.pv_name,
                "namespace": self.workspace,
                "clusterName" : self.cluster_name
            },
            "spec" : {
                "capacity" : {
                    "storage": self.capacity+'i'
                },
                "iscsi": {
                    "targetPortal": self.data_volume_server,
                    "portals": portals,
                    "iqn": self.data_volume_path,
                    "lun": 1,
                    "fsType": "ext4",
                    "readOnly": False,
                    "chapAuthDiscovery": False,
                    "chapAuthSession": False
                },
                "accessModes" : [accessmode],
                "persistentVolumeReclaimPolicy" : self.recovery_model,
                "storageClassName" : "slow"
            }
        }

      

    
    def persistent_volume_claim(self):
        accessmode = self.parse_access_mode(self.read_write_mode)
        return {
            "kind": "PersistentVolumeClaim",
            "apiVersion": "v1",
            "metadata": {
                "name": self.pv_name,
                "namespace": self.workspace,
                "clusterName": self.cluster_name
            },
            "spec": {
                "accessModes": [
                    accessmode
                ],
                "resources": {
                    "requests": {"storage": self.capacity + 'i'}
                },
                "volumeName": self.pv_name,
                "storageClassName": "slow"
            }
        }
        
    def _get_ramdom_host(self, host_list, num):
        if num >= len(host_list):
            return host_list
        
        arr = []
        length = len(host_list) - 1
        random = Random()
        while len(arr) < num:
            index = random.randint(0, length)
            if index not in arr:
                arr.append(index)
        
        return [host_list[i] for i in arr]

    def mount_host(self):
        if self.volume_type == STORAGE_SHARE_TYPE_NFS:
            return Result('done')
        
        rlt = StorageNodeDB.instance().read_app_node_list(self.cluster_name)
        if not rlt.success:
            Log(1, 'AddPVWork.mount_host read_app_node_list[%s]fail,as[%s]'%(self.cluster_name, rlt.message))
            return Result('done')
        
        app_node_list = []
        for node in rlt.content:
            if node.get('ip') == self.ip:
                continue
            
            app_node_list.append({'ip':node.get('ip'), 'port':node.get('app_api_port', APPLICATION_HOST_PORT)})
            
        if not app_node_list:
            return Result('done')
        
        app_node_list = self._get_ramdom_host(app_node_list, 2)
        
        data = {}
        data['name'] = self.pv_name
        data['cluster_id'] = self.get_cluster_id()
        data['share_type'] = self.volume_type
        data['targetdport'] = self.targetdport
        rlt = self.veclient.mount_volume(data, app_node_list)
        if not rlt.success:
            Log(1, 'AddPVWork.mount_host mount_volume[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        self.app_node_list = app_node_list
        
        rlt = MountDB.instance().save_mount_info(self.cluster_name, data, app_node_list)
        if not rlt.success:
            Log(1, 'AddPVWork.mount_host save_mount_info[%s]fail,as[%s]'%(str(data), rlt.message))
        return rlt
    
    def unmount_host(self):
        if self.volume_type == STORAGE_SHARE_TYPE_NFS:
            return Result('nfs type volume')
        
        rlt = MountDB.instance().read_mount_list(self.cluster_name, self.pv_name)
        if not rlt.success:
            Log(1, 'AddPVWork.unmount_host read_mount_list[%s][%s]fail,as[%s]'%(self.cluster_name, self.pv_name, rlt.message))
            return Result('done')
        
        app_node_list = []
        mount_id_list = []
        for host in rlt.content:
            mount_id_list.append(host.get(ID))
            node = {}
            node['ip'] = host.get('ip')
            node['port'] = host.get('port')
            app_node_list.append(node)
            
        if not app_node_list:
            return Result('not mount')
        
        data = {}
        data['name'] = self.pv_name
        data['cluster_id'] = self.get_cluster_id()
        
        rlt = self.veclient.unmount_volume(data, app_node_list)
        if not rlt.success:
            Log(1, 'AddPVWork.mount_host mount_volume[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        rlt = MountDB.instance().delete_mount_records(self.cluster_name, mount_id_list)
        if not rlt.success:
            Log(1, 'AddPVWork.mount_host save_mount_info[%s]fail,as[%s]'%(str(data), rlt.message))
        return rlt
        
        
    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"AddPVWork.on_fail")
        LogAdd(1, 'system', u'在存储集群[%s][%s]创建数据卷[%s][%s]失败,因为[%s]'%(self.cluster_name, self.ip, self.pv_name, self.capacity, tskResult.message))
        

    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"AddPVWork.on_success")
        LogAdd(3, 'system', u'在存储集群[%s][%s]创建数据卷[%s][%s]成功'%(self.cluster_name, self.ip, self.pv_name, self.capacity))


