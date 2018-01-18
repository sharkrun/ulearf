# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
创建StorageClass，包括provisioner
"""


from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR, INIT_VESPACE_CLIENT_FAILERR, \
    TASK_CANCEL_ERR, INVALID_PARAM_ERR, VESPACE_RESULT_INVALID_ERROR
from core.kubeclientmgr import KubeClientMgr
from core.vespaceclient import DEFAULT_STORAGE_DOMAIN, \
    STORAGE_SHARE_TYPE_NFS, \
    DEFAULT_STORAGE_POOL_NAME, STORAGE_SHARE_TYPE_ISCSI
from core.vespacemgr import VespaceMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.mount import MountDB
from etcddb.storage.node import StorageNodeDB
from etcddb.storage.storageclass import StorageClassDB
from etcddb.storage.volume import VolumeDB
from frame.auditlogger import LogAdd
from frame.configmgr import GetSysConfig
from frame.etcdv3 import ID
from frame.exception import InternalException
from frame.logger import Log, PrintStack
from workflow.data.taskdata import TaskData


class AddStorageClassWork(TaskData):
    
    def __init__(self, work_info):
        """
        work_info = {
            "cluster_name":"",
            "ip":"",
            "group":"",
            "volume_name":"",
            "capacity":"",
            "read_write_mode":"",
            "recovery_model":"",
            "volume_type":"",
            "creator":"",
            "replica":"",
            "namespace":""
        }
        """
        self.cluster_name = ''
        self.ip = ''
        self.group = ''
        self.volume_name = ''
        self.storage_class_name = ''
        self.capacity = ''
        self.read_write_mode = ''
        self.recovery_model = ''
        self.volume_type = ''
        self.creator = ''
        self.replica = 2
        self.namespace = ''
        
        self.volume_status = 0
        self.cluster_id = ''
        self.data_volume_server = ''
        self.data_volume_path = ''
        self.volume_id = ''
        self.storage_access_path = ''
        self.veclient = None
        self.kubeclient = None
        self.deploy_success = False
        self.create_storage_class_success = False
        super(AddStorageClassWork, self).__init__(work_info)

        
    def snapshot(self):
        snap = super(AddStorageClassWork, self).snapshot()
        snap["cluster_name"] = self.cluster_name
        snap["cluster_id"] = self.cluster_id
        snap["namespace"] = self.namespace
        snap["ip"] = self.ip
        snap["volume_name"] = self.volume_name
        snap["storage_class_name"] = self.storage_class_name
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
        snap["deploy_success"] = self.deploy_success
        snap["create_storage_class_success"] = self.create_storage_class_success
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
                Log(1, 'AddStorageClassWork.check_valid get_cluster_client[%s]fail'%(self.cluster_name))
                return Result('', INVALID_PARAM_ERR, 'cluster_name is invalid')
            else:
                self.kubeclient = kube_client
                
            if self.recovery_model not in ['Retain', 'Recycle', 'Delete']:
                self.recovery_model = 'Delete'
                
        except InternalException,e:
            Log(1,"AddStorageClassWork.check_valid except[%s]"%(e.value))
            return Result("AddStorageClassWork",e.errid,e.value)
        except Exception,e:
            PrintStack()
            return Result("AddStorageClassWork",INTERNAL_EXCEPT_ERR,"AddStorageClassWork.check_valid except[%s]"%(str(e)))
            
        return Result(0)
    
    def ready(self):
        self.save_to_db()
        
    def is_volume_exist(self):
        if StorageClassDB.instance().is_storage_class_exist(self.cluster_name, self.storage_class_name):
            return True
        else:
            Log(1, 'The storage class[%s][%s] lost'%(self.cluster_name, self.storage_class_name))
            raise InternalException("storage_class_name deleted.", TASK_CANCEL_ERR)
    
    def get_cluster_id(self):
        if self.cluster_id:
            return self.cluster_id
        
        rlt = StoregeClusterDB.instance().get_cluster_info(self.cluster_name)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.get_cluster_id get_cluster_info[%s][%s]fail,as[%s]'%(self.cluster_name, self.ip, rlt.message))
            raise InternalException("get_cluster_info[%s] fail,as[%s]."%(self.cluster_name, rlt.message), rlt.result)
        
        self.cluster_id = rlt.content.get('cluster_id')
        return self.cluster_id

    
    def create_data_volume(self):
        data = {}
        data['ip'] = self.ip
        data['name'] = self.volume_name
        data['capacity'] = '{}G'.format(self.capacity)
        data['share_type'] = self.volume_type
        data['replica'] = self.replica
        data['cluster_id'] = self.get_cluster_id()
        if self.volume_type == STORAGE_SHARE_TYPE_ISCSI:
            data['target_port'] = VolumeDB.instance().get_iscsi_target_port(self.cluster_name)
            
        rlt = self.veclient.create_volume(data)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.create_data_volume create_volume[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        rlt = self.veclient.get_volume_info(data['cluster_id'], DEFAULT_STORAGE_DOMAIN, DEFAULT_STORAGE_POOL_NAME, data['name'])
        if not rlt.success:
            Log(1, 'AddStorageClassWork.create_data_volume get_volume_info[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        volume_info = rlt.content
        rlt = self.parse_volume_accesspath(volume_info.get('accesspath'))
        if not rlt.success:
            Log(1, 'AddStorageClassWork.create_data_volume parse_volume_accesspath[%s]fail,as[%s]'%(str(volume_info.get('accesspath')), rlt.message))
            return rlt
        
        
        rlt = MountDB.instance().create_mount_record(self.cluster_name, data)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.create_data_volume create_mount_record[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        self.volume_status = volume_info.get('status', 0)
        data['creator'] = self.creator
        data['cluster_name'] = self.cluster_name
        data['bind'] = self.volume_name
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
            Log(1, 'AddStorageClassWork.create_data_volume create_volume in etcd[%s]fail,as[%s]'%(str(data), rlt.message))
        return rlt
    
    def delete_data_volume(self):
        if not self.volume_id:
            return Result('done')
        
        rlt = VolumeDB.instance().read_volume_info(self.cluster_name, self.volume_id)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.read_volume_info [%s][%s]from etcd fail,as[%s]'%(self.cluster_name, self.volume_id, rlt.message))
            return rlt
        
        volume = rlt.content
        
        app_node_list = []
        mount_id_list = []
        rlt = MountDB.instance().read_mount_list(self.cluster_name, self.pv_name)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.delete_data_volume read_mount_list[%s][%s]fail,as[%s]'%(self.cluster_name, self.pv_name, rlt.message))
        else:
            for node in rlt.content:
                mount_id_list.append(node.get(ID))
                app_node_list.append({'ip':node.get('ip'), 'port':node.get('port')})

        if app_node_list:
            rlt = self.veclient.unmount_volume(volume, app_node_list)
            if not rlt.success:
                Log(1, 'AddStorageClassWork.delete_data_volume unmount_volume[%s][%s]fail,as[%s]'%(self.cluster_name, volume.get('name'), rlt.message))
                return rlt
            MountDB.instance().delete_mount_records(self.cluster_name, mount_id_list)
        
        rlt = self.veclient.delete_volume(volume['cluster_id'], volume.get('name'))
        if not rlt.success:
            Log(1, 'AddStorageClassWork.delete_data_volume delete_volume[%s][%s]fail,as[%s]'%(self.cluster_name, volume.get('name'), rlt.message))
            return rlt
            
        rlt = VolumeDB.instance().delete_volume(self.cluster_name, self.volume_id)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.delete_data_volume delete_volume[%s][%s]from etcd fail,as[%s]'%(self.cluster_name, self.volume_id, rlt.message))
        return rlt
    
    
    def parse_volume_accesspath(self, access_path_list):
        if not isinstance(access_path_list, list) or len(access_path_list) < 1:
            return Result('', VESPACE_RESULT_INVALID_ERROR, '[%s][%s][%s]accesspath invalid'%(self.cluster_name, self.ip, self.volume_name))

        if self.volume_type == STORAGE_SHARE_TYPE_NFS:
            arr = access_path_list[0].split(':')
        else:
            arr = access_path_list[0].split(' ')
            
        if len(arr) != 2:
            return Result('', VESPACE_RESULT_INVALID_ERROR, '[%s][%s][%s]accesspath invalid'%(self.cluster_name, self.ip, self.volume_name))
        
        self.data_volume_server = arr[0]
        self.data_volume_path = arr[1]
        self.storage_access_path = access_path_list[0]
        return Result('ok')
        
    
    def deploy_provisioner(self):
        cfg = self._deploy()
        rlt = self.kubeclient.create_deployment(self.namespace, cfg)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.deploy_provisioner fail,as[%s]'%(rlt.message))
        
        self.deploy_success = True
        return rlt
    
    
    def uninstall_provisioner(self):
        if not self.deploy_success:
            return Result('done')
        
        rlt = self.kubeclient.remove_storage_class_deploy(self.namespace, self.storage_class_name)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.uninstall_provisioner [%s]fail,as[%s]'%(self.storage_class_name, rlt.message))
        return rlt
        
    def create_storage_class(self):
        cfg = self._storage_class()
        rlt = self.kubeclient.create_storage_class(cfg)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.create_storage_class fail,as[%s]'%(rlt.message))
        
        self.create_storage_class_success = True
        return rlt
    
    
    def delete_storage_class(self):
        if not self.create_storage_class_success:
            return Result('done')
        
        rlt = self.kubeclient.delete_storage_class(self.storage_class_name)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.delete_storage_class [%s]fail,as[%s]'%(self.storage_class_name, rlt.message))
        return rlt
    
    
    def _storage_class(self):
        return {
            "kind": "StorageClass",
            "apiVersion": "storage.k8s.io/v1beta1",
            "metadata":{
                "name": self.storage_class_name
            },              
            "provisioner": "vespace/{}".format(self.storage_class_name)
        }
        
    def _deploy(self):
        image = GetSysConfig("external_storage_image")
        return {
            "kind": "Deployment",
            "apiVersion": "apps/v1beta1",
            "metadata":{
                "name": self.storage_class_name,
                "namespace": self.namespace
            },
            "spec":{
                "replicas": 1,
                "strategy":{
                    "type": "Recreate"
                },
                "template":{
                    "metadata":{
                        "labels":{
                            "app": self.storage_class_name
                        }
                    },
                    "spec":{
                        "serviceAccount": "nfs-client-provisioner",
                        "containers":[{
                                "name": self.storage_class_name,
                                "image": image,
                                "volumeMounts":[{
                                    "name": "nfs-client-root",
                                    "mountPath": "/persistentvolumes"
                                }],

                                "env":[{
                                    "name": "PROVISIONER_NAME",
                                    "value": "vespace/{}".format(self.storage_class_name)
                                },{
                                    "name": "NFS_SERVER",
                                    "value": self.data_volume_server
                                },{
                                    "name": "NFS_PATH",
                                    "value": self.data_volume_path
                                }]
                            }
                        ],
                        "volumes":[{
                            "name": "nfs-client-root",
                            "nfs":{
                                "server": self.data_volume_server,
                                "path": self.data_volume_path
                            }
                        }]
                    }                    
                }
            }
        }
    
    def save_storage_class_info(self):
        if not self.volume_id:
            Log(1, 'AddStorageClassWork.save_storage_class_info fail,as[the volume_id invalid]')
            return Result('', INVALID_PARAM_ERR, 'the volume_id invalid')
        
        info = {'volume_id': self.volume_id, 
                'access_path':self.storage_access_path, 
                'data_volume_server':self.data_volume_server, 
                'data_volume_path':self.data_volume_path, 
                'status':self.volume_status}
        rlt = StorageClassDB.instance().update_storage_class(self.cluster_name, self.storage_class_name, info)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.save_storage_class_info update_storage_class[%s][%s]fail,as[%s]'%(self.cluster_name, self.storage_class_name, rlt.message))
        return rlt
    
    def delete_storage_class_info(self):
        rlt = StorageClassDB.instance().delete_storage_class(self.cluster_name, self.storage_class_name)
        if not rlt.success:
            Log(1, 'AddStorageClassWork.delete_pv delete_storage_class[%s][%s]fail,as[%s]'%(self.cluster_name, self.storage_class_name, rlt.message))
        return rlt
    
    def delete_pv(self):
        return self.delete_storage_class_info()
       
    
    def on_fail(self, tskResult):
        """
        # 销毁失败
        """
        Log(1,"AddStorageClassWork.on_fail")
        LogAdd(1, 'system', u'在存储集群[%s][%s]创建共享卷[%s][%s]失败'%(self.cluster_name, self.ip, self.storage_class_name, self.capacity))
        

    
    def on_success(self):
        """
        # 销毁成功
        """
        Log(4,"AddStorageClassWork.on_success")
        LogAdd(3, 'system', u'在存储集群[%s][%s]创建共享卷[%s][%s]成功'%(self.cluster_name, self.ip, self.storage_class_name, self.capacity))


