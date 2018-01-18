# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
'''
Created on 2017年8月11日

@author: Jack
'''
import json
import re

from twisted.web import http

from common.util import Result, Parse2Float
from core.const import STORAGE_CLASS_DEFAULT_NAMESPACE, \
    STORAGE_CLASS_STATUS_NOT_READY
from core.errcode import FAIL, INVALID_JSON_DATA_ERR, INVALID_PARAM_ERR, \
    ETCD_KEY_NOT_FOUND_ERR, NO_SUCH_RECORD_ERR, \
    CAPACITY_LESS_THAN_REQUEST_ERR
from core.storagemgr import StorageMgr
from core.vespaceclient import VeSpaceClient, HOST_TYPE_STOREGE, HOST_TYPE_APPLICATION, \
    STORAGE_SHARE_TYPE_NFS, STORAGE_SHARE_TYPE_ISCSI, \
    DEFAULT_USER_NAME, DEFAULT_PASSWORD, DEFAULT_STORAGE_DOMAIN, \
    DEFAULT_STORAGE_POOL_NAME
from core.vespacemgr import VespaceMgr
from etcddb.kubernetes.nodemgr import CluNodedb
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from etcddb.settingmgr import SettingMgr
from etcddb.storage.cluster import StoregeClusterDB
from etcddb.storage.disk import DiskDB
from etcddb.storage.mount import MountDB
from etcddb.storage.node import StorageNodeDB
from etcddb.storage.pv import PVDB
from etcddb.storage.storageclass import StorageClassDB
from etcddb.storage.volume import VolumeDB
from etcddb.workflow.task import TaskDB
from frame.auditlogger import LogAdd, LogDel, LogMod
from frame.authen import ring0, ring3, ring5
from frame.logger import Log
from workflow.work import ADD_STORAGE_NODE_WORK, INIT_STORAGE_CLUSTER_WORK


class Storage(object):
    '''
    classdocs
    '''



    def __init__(self):
        '''
        Constructor
        '''
        pass

    
    @ring0
    @ring3
    def set_license(self, license_str, **args):
        username = args.get('passport',{}).get('username', 'unkown')
        
        rlt = SettingMgr.instance().set_vespace_license(license_str)
        if rlt.success:
            LogMod(3, username, u'用户 [%s] 更新存储模块license 成功.'%(username))
        else:
            LogMod(3, username, u'用户 [%s] 更新存储模块license 失败,as[%s].'%(username, rlt.message))
        return rlt
    
    @ring0
    @ring3
    def get_license(self, **args):
        return SettingMgr.instance().get_vespace_license()

    
    @ring0
    @ring3 
    def add_cluster(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'name' not in data or not data['name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        name = data['name']
        ip = data['ip']
        client = VeSpaceClient(ip, data.get('username',DEFAULT_USER_NAME), data.get('password',DEFAULT_PASSWORD))
        rlt = client.create_cluster(name, ip)
        if not rlt.success:
            Log(1, 'Storage.add_cluster [%s][%s]fail,as[%s]'%(name, ip, rlt.message))
            return rlt
        
        cluster_id = rlt.content.get('id')
        
        rlt = SettingMgr.instance().get_vespace_license()
        if not rlt.success:
            Log(1, 'Storage.add_cluster get_vespace_license fail,as[%s]'%(rlt.message))
            return rlt
        
        license_str = rlt.content
        rlt = client.add_license(cluster_id, license_str)
        if not rlt.success:
            Log(1, 'Storage.add_cluster add_licence[%s][%s]fail,as[%s]'%(name, ip, rlt.message))
            return rlt
        
        cluster_info = rlt.content
        cluster_info['ip'] = ip
        cluster_info['cluster_id'] = cluster_id
        rlt = StoregeClusterDB.instance().create_cluster(name, cluster_info)
        if not rlt.success:
            Log(1, 'Storage.add_cluster[%s][%s]to etcd fail,as[%s]'%(name, ip, rlt.message))
        return rlt

    
    @ring0
    @ring3
    @ring5
    def nodes(self, cluster_name, **args):
        rlt = StorageNodeDB.instance().read_app_node_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.nodes read_app_node_list fail,as[%s]'%(rlt.message))
        return rlt
        
    
    @ring0
    @ring3
    def add_node(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        cluster_name = data['cluster_name']
        ip = data['ip']
        
        rlt = StoregeClusterDB.instance().get_cluster_info(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.add_node get_cluster_info[%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
            return Result('', FAIL, 'The cluster not exist')
        
        cluster_id = rlt.content.get('cluster_id')
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        rlt = client.add_host(cluster_id, DEFAULT_STORAGE_DOMAIN, ip, HOST_TYPE_STOREGE)
        if not rlt.success:
            Log(1, 'Storage.add_node [%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
            return rlt
        
        host_info = {'cluster': cluster_name, 'cluster_id': cluster_id, 'domain_name': DEFAULT_STORAGE_DOMAIN, 'ip': ip, 'store_api_port':rlt.content.get('port')}
        rlt = client.add_host(cluster_id, DEFAULT_STORAGE_DOMAIN, ip, HOST_TYPE_APPLICATION)
        if rlt.success:
            host_info['app_api_port'] = rlt.content.get('port')
        else:
            Log(1, 'Storage.add_node [%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
        
        rlt = StorageNodeDB.instance().create_node(cluster_name, ip, host_info)
        if not rlt.success:
            Log(1, 'Storage.add_node [%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
        
        return rlt
    
    @ring0
    @ring3
    def delete_node(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        cluster_name = data['cluster_name']
        ip = data['ip']
        
        
        rlt = StorageNodeDB.instance().read_node_info(cluster_name, ip)
        if not rlt.success:
            Log(1, 'Storage.delete_node read_node_info[%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
            return rlt
            
        cluster_id = rlt.content.get('cluster_id')
        store_api_port = rlt.content.get('store_api_port')
        app_api_port = rlt.content.get('app_api_port')
        domain = rlt.content.get('domain_name', DEFAULT_STORAGE_DOMAIN)
        
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        data = {}
        if store_api_port:
            rlt = client.delete_host(cluster_id, domain, ip, store_api_port, HOST_TYPE_STOREGE)
            if rlt.success:
                data['storage'] = True
            else:
                data['storage'] = False
                Log(1, 'Storage.delete_node delete_host[%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
        
        if app_api_port:
            rlt = client.delete_host(cluster_id, domain, ip, app_api_port, HOST_TYPE_APPLICATION)
            if rlt.success:
                data['application'] = True
            else:
                data['application'] = False
                Log(1, 'Storage.delete_node delete_host[%s][%s]fail,as[%s]'%(cluster_name, ip, rlt.message))
                
        return Result(data)
    
    @ring0
    @ring3
    @ring5
    def clusters(self):
        rlt = StoregeClusterDB.instance().read_cluster_list()
        if not rlt.success:
            Log(1, 'Storage.cluster_list read_cluster_list fail,as[%s]'%(rlt.message))
            return rlt

        arr = []
        for cluster in rlt.content:
            info = self.calc_cluster_info(cluster['name'])
            if info['host_number'] > 0:
                cluster.update(info)
                arr.append(cluster)
            
        return Result(arr)
    
    def calc_cluster_info(self, cluster_name):
        statistic = {}
        host_number = 0
        total = 0
        free = 0
        volume_num = 0
        volumes = []
        
        rlt = StorageNodeDB.instance().read_node_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.clusters read_node_list[%s] fail,as[%s]'%(cluster_name, rlt.message))
        else:            
            for node in rlt.content:
                if node.get('store_api_port'):
                    host_number += 1
                    ret = self._statistics_host_storage(cluster_name, node)
                    if not ret.success:
                        Log(1, 'Storage.clusters _statistics_host_storage[%s]fail,as[%s]'%(str(node), ret.message))
                        continue
                    
                    total += ret.content['total']
                    free += ret.content['free']
                    
            ret = VolumeDB.instance().read_volume_list(cluster_name)
            if ret.success:
                volumes = ret.content
                volume_num = len(ret.content)
        
        statistic['total'] = total
        statistic['free'] = free
        statistic['host_number'] = host_number
        statistic['volumes'] = volumes
        statistic['volume_num'] = volume_num
        return statistic
                    
    
    def _statistics_host_storage(self, cluster_name, node_info):
        rlt = self._get_disk_info(cluster_name, node_info)
        if not rlt.success:
            Log(1, 'Storage._statistics_host_storage _get_disk_info fail,as[%s]'%(rlt.message))
            return rlt
        
        total = 0
        allocated = 0
        for disk in rlt.content:
            if not disk.get('added', False):
                continue
            
            total += disk['Total']
            allocated += disk['Allocated']
        
        return Result({'total':total, 'free': total - allocated})

    @ring0
    @ring3
    @ring5
    def disks(self, cluster_name, host_ip, **args):
        rlt = StoregeClusterDB.instance().get_cluster_info(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.disks get_cluster_info fail,as[%s]'%(rlt.message))
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                self._init_storage_cluster(cluster_name)
            return rlt
        
        rlt = StorageNodeDB.instance().read_node_info(cluster_name, host_ip)
        if not rlt.success:
            Log(1, 'Storage.disks read_node_info fail,as[%s]'%(rlt.message))
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                self._add_storage_node(cluster_name, host_ip)
            return rlt
        
        return self._get_disk_info(cluster_name, rlt.content)
    
    def _init_storage_cluster(self, cluster_name):
        rlt = TaskDB.instance().get_task_id_by_key(INIT_STORAGE_CLUSTER_WORK, cluster_name, '-')
        if rlt.result == ETCD_KEY_NOT_FOUND_ERR or rlt.result == NO_SUCH_RECORD_ERR:
            Log(3, '_init_storage_cluster Auto init_storage_cluster[%s]'%(cluster_name))
            rlt = CluNodedb.instance().read_master_list(cluster_name)
            if not rlt.success:
                Log(3, '_init_storage_cluster read_master_ip_list[%s] fail,as[%s]'%(cluster_name, rlt.message))
                return rlt
            
            StorageMgr.instance().init_storage_cluster(cluster_name, rlt.content)
        else:
            Log(3, '_init_storage_cluster[%s]skip,as[the task exist already]'%(cluster_name))
    
    def _add_storage_node(self, cluster_name, host_ip):
        key = '%s-%s'%(cluster_name, host_ip)
        rlt = TaskDB.instance().get_task_id_by_key(ADD_STORAGE_NODE_WORK, key, '-')
        if rlt.result == ETCD_KEY_NOT_FOUND_ERR or rlt.result == NO_SUCH_RECORD_ERR:
            Log(3, '_add_storage_node Auto add_storage_node[%s][%s]'%(cluster_name, host_ip))
            StorageMgr.instance().add_storage_node(cluster_name, host_ip)
        else:
            Log(3, '_add_storage_node[%s][%s]skip,as[the task exist already]'%(cluster_name, host_ip))
        
    
    def _get_disk_info(self, cluster_name, node_info):
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        rlt = client.get_storage_host_info(node_info['cluster_id'], node_info['domain_name'], node_info['ip'], node_info['store_api_port'])
        if not rlt.success:
            Log(1, 'Storage.get_storage_host_info [%s][%s]fail,as[%s]'%(node_info['cluster'], node_info['ip'], rlt.message))
            return rlt
        
        disk_list = (rlt.content.get('Disk') or {}).get('Dbi', [])
        engine = rlt.content.get('Engine')
        if isinstance(engine, dict):
            DataDevices = engine.get('DataDev') or []
            CacheDevices = engine.get('CacheDev') or []
        else:
            DataDevices = []
            CacheDevices = []
            
        data = {}
        for device in DataDevices:
            device['engine'] = 'data'
            data[device['Device']] = device
            
        for device in CacheDevices:
            device['engine'] = 'cache'
            data[device['Device']] = device
        
        for disk in disk_list:
            disk_path = disk['Path']
            if disk_path in data:
                disk.update(data[disk_path])
                disk['added'] = True
            else:
                disk['added'] = False
        
        return Result(disk_list)


    @ring0
    @ring3
    def add_data_disk(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'host_ip is invalid', http.BAD_REQUEST)
        
        if 'disks' not in data or not data['disks']:
            return Result('',INVALID_PARAM_ERR, 'disk list is invalid', http.BAD_REQUEST)
        
        
        cluster_name = data['cluster_name']
        host_ip = data['ip']
        disk_list = data['disks']
        rlt = StorageNodeDB.instance().read_node_info(cluster_name, host_ip)
        if not rlt.success:
            Log(1, 'Storage.add_data_disk read_node_info fail,as[%s]'%(rlt.message))
            return rlt
        
        node_info = rlt.content
        rlt = self._get_disk_info(cluster_name, node_info)
        if not rlt.success:
            Log(1, 'Storage.add_data_disk _get_disk_info fail,as[%s]'%(rlt.message))
            return rlt

        device_list = rlt.content
        add_disk_list = []
        arr = []
        for dev in device_list:
            if dev['Path'] in disk_list and dev['added']==False:
                add_disk_list.append(dev['Path'])
                arr.append(dev)
        
        if len(add_disk_list) == 0:
            return Result('', FAIL, 'Disk path invalid')
        
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        rlt = client.add_data_disk(node_info['cluster_id'], node_info['domain_name'], node_info['ip'], node_info['store_api_port'], add_disk_list)
        if not rlt.success:
            Log(1, 'Storage.add_data_disk [%s][%s][%s]fail,as[%s]'%(cluster_name, host_ip, str(disk_list), rlt.message))
            return rlt
        
        creator  = args.get('passport',{}).get('username', '')
        LogAdd(3, creator, u'给存储集群[%s]添加数据盘[%s]%s'%(cluster_name, host_ip, str(disk_list)))
        
        for disk in arr:
            disk.update(node_info)
            disk['creator'] = creator
            rlt = DiskDB.instance().create_disk(host_ip, disk)
            if not rlt.success:
                Log(1, 'Storage.add_data_disk create_disk in etcd fail,as[%s]'%(rlt.message))

        return Result(len(arr))
    
    @ring0
    @ring3
    def delete_data_disk(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'host_ip is invalid', http.BAD_REQUEST)
        
        if 'disks' not in data or not data['disks']:
            return Result('',INVALID_PARAM_ERR, 'disk list is invalid', http.BAD_REQUEST)
        
        
        cluster_name = data['cluster_name']
        host_ip = data['ip']
        disk_list = data['disks']
        
        rlt = DiskDB.instance().read_disk_list(host_ip)
        if not rlt.success:
            Log(1, 'Storage.delete_data_disk read_disk_list fail,as[%s]'%(rlt.message))
            return rlt
        
        device_list = rlt.content
        delete_disk_list = []
        arr = []
        for dev in device_list:
            if dev['Path'] in disk_list:
                delete_disk_list.append(dev['Path'])
                arr.append(dev)
                
        if len(delete_disk_list) == 0:
            return Result('', FAIL, 'Disk path invalid')
        
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        rlt = client.delete_data_disk(arr[0]['cluster_id'], arr[0]['domain_name'], arr[0]['ip'], arr[0]['store_api_port'], delete_disk_list)
        if not rlt.success:
            Log(1, 'Storage.delete_data_disk [%s][%s][%s]fail,as[%s]'%(cluster_name, host_ip, str(disk_list), rlt.message))
            return rlt
        
        creator  = args.get('passport',{}).get('username', '')
        LogDel(3, creator, u'从存储集群[%s]移除数据盘[%s]%s'%(cluster_name, host_ip, str(disk_list)))
        
        for disk in arr:
            rlt = DiskDB.instance().delete_disk(host_ip, disk['disk_id'])
            if not rlt.success:
                Log(1, 'Storage.delete_data_disk delete_disk in etcd fail,as[%s]'%(rlt.message))
                
        return Result(len(delete_disk_list))
    
    @ring0
    @ring3
    @ring5
    def volumes(self, cluster_name):
        rlt = VolumeDB.instance().read_volume_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.volumes read_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
        return rlt
    
    
    @ring0
    @ring3
    @ring5
    def workspace_volumes(self, workspace):
        rlt = WorkSpacedb.instance().read_workspace(workspace)
        if not rlt.success:
            Log(1, 'Storage.workspace_volumes read_workspace[%s]fail,as[%s]'%(workspace, rlt.message))
            return rlt
        
        cluster_name = rlt.content.get('cluster_name')
        rlt = VolumeDB.instance().read_volume_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.volumes read_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
        return rlt
    
    
    @ring0
    @ring3
    @ring5
    def free_volumes(self, cluster_name):
        rlt = VolumeDB.instance().read_volume_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.volumes read_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        arr = []
        for volume in rlt.content:
            if not volume.get('bind'):
                arr.append(volume)
            
        return Result(arr)
        
    def _sync_volume_info(self, cluster_name, filtername=''):
        rlt = VolumeDB.instance().read_volume_list(cluster_name)
        if not rlt.success:
            Log(1, 'Storage.volumes read_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        
        volumes = rlt.content
        if len(volumes) == 0:
            Log(3, 'volumes[%s]no volume exist in etcd.')
            return Result([])
        
        cluster_id = volumes[0].get('cluster_id')
        
        client = VespaceMgr.instance().get_cluster_client(cluster_name)
        rlt = client.get_volume_list(cluster_id, filtername)
        if not rlt.success:
            Log(1, 'Storage.volumes get_volume_list[%s]fail,as[%s]'%(cluster_name, rlt.message))
            return rlt
        
        tmp = {}
        for volume in rlt.content.get('List', []):
            tmp[volume['name']] = volume
            
        if not tmp:
            Log(3, 'volumes[%s]no volume exist in server.')
            return Result([])
        
        arr = []
        for volume in volumes:
            volume_name = volume['name']
            if volume_name not in tmp:
                Log(1, 'The volume[%s][%s] not exist in server'%(cluster_name, volume_name))
                VolumeDB.instance().delete_volume(cluster_name, volume['volume_id'])
                continue
            
            volume['status'] = tmp[volume_name].get('status','-')
            volume['flag'] = tmp[volume_name].get('flag','-')
            volume['capacity_num'] = tmp[volume_name].get('capacity',0)
            volume['mounted'] = tmp[volume_name].get('mounted',[])
            volume['accesspath'] = tmp[volume_name].get('accesspath',[])
            volume['controllerhosts'] = tmp[volume_name].get('controllerhosts',{}).get('default',[])
            arr.append(volume)
                
        return Result(arr)
    
    
    @ring0
    @ring3
    def add_volume(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'name' not in data or not data['name']:
            return Result('',INVALID_PARAM_ERR, 'volume name is invalid', http.BAD_REQUEST)
        
        if VolumeDB.instance().is_volume_exist(data['cluster_name'], data['name']):
            return Result('',INVALID_PARAM_ERR, 'volume name is repeat', http.BAD_REQUEST)
        
        if 'capacity' not in data or not data['capacity']:
            return Result('',INVALID_PARAM_ERR, 'capacity is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not StorageNodeDB.instance().is_app_node_exist(data['cluster_name'], data['ip']):
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        rlt = StoregeClusterDB.instance().get_cluster_info(data['cluster_name'])
        if not rlt.success:
            Log(1, 'Storage.add_volume get_cluster_info[%s]fail,as[%s]'%(data['cluster_name'], rlt.message))
            return rlt
        
        if data.get('share_type') == STORAGE_SHARE_TYPE_ISCSI:
            data['target_port'] = VolumeDB.instance().get_iscsi_target_port(data['cluster_name'])
        
        data['cluster_id'] = rlt.content.get('cluster_id')
        client = VespaceMgr.instance().get_cluster_client(data['cluster_name'])
        rlt = client.create_volume(data)
        if not rlt.success:
            Log(1, 'Storage.add_volume create_volume[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        rlt = client.get_volume_info(data['cluster_id'], DEFAULT_STORAGE_DOMAIN, DEFAULT_STORAGE_POOL_NAME, data['name'])
        if not rlt.success:
            Log(1, 'Storage.add_volume get_volume_info[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        rlt = MountDB.instance().create_mount_record(data['cluster_name'], data)
        if not rlt.success:
            Log(1, 'Storage.add_volume create_mount_record[%s]fail,as[%s]'%(str(data), rlt.message))
            return rlt
        
        volume_info = rlt.content
        data['creator'] = args.get('passport',{}).get('username', '')
        data['bind'] = ''
        data['status'] = volume_info.get('status','-')
        data['flag'] = volume_info.get('flag','-')
        data['capacity_num'] = volume_info.get('capacity',0)
        data['mounted'] = volume_info.get('mounted',[])
        data['accesspath'] = volume_info.get('accesspath',[])
        data['controllerhosts'] = volume_info.get('controllerhosts',{}).get('default',{})
        rlt = VolumeDB.instance().create_volume(data['cluster_name'], data)
        if not rlt.success:
            Log(1, 'Storage.add_volume create_volume in etcd[%s]fail,as[%s]'%(str(data), rlt.message))
        return rlt
            
    @ring0
    @ring3
    def delete_volume(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Storage.delete_volume load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'volume_id' not in data or not data['volume_id']:
            return Result('',INVALID_PARAM_ERR, 'volume id is invalid', http.BAD_REQUEST)
        
        return StorageMgr.instance().delete_volume(data['cluster_name'], data['volume_id'])
        

    @ring0
    @ring3
    @ring5    
    def pvs(self, cluster):
        rlt = PVDB.instance().read_volume_list(cluster)
        if not rlt.success:
            Log(1, 'Storage.get_pv_list read_volume_list[%s]fail,as[%s]'%(cluster, rlt.message))
        return rlt
    
    @ring0
    @ring3
    @ring5    
    def get_pv_by_group(self, group):
        rlt = PVDB.instance().get_pv_by_group(group)
        if not rlt.success:
            Log(1, 'Storage.get_pv_by_group get_pv_by_group[%s]fail,as[%s]'%(group, rlt.message))
        return rlt
    
    
    @ring0
    @ring3
    @ring5
    def workspace_pvs(self, workspace):
        rlt = WorkSpacedb.instance().read_workspace(workspace)
        if not rlt.success:
            Log(1, 'Storage.workspace_volumes read_workspace[%s]fail,as[%s]'%(workspace, rlt.message))
            return rlt
        
        cluster = rlt.content.get('cluster_name')
        rlt = PVDB.instance().get_pv_by_workspace(cluster, workspace)
        if not rlt.success:
            Log(1, 'Storage.workspace_pvs get_pv_by_workspace[%s][%s]fail,as[%s]'%(cluster, workspace, rlt.message))
        return rlt
    
    
    @ring0
    @ring3
    @ring5    
    def get_pv_by_workspace(self, cluster, workspace):
        rlt = PVDB.instance().get_pv_by_workspace(cluster, workspace)
        if not rlt.success:
            Log(1, 'Storage.get_pv_by_workspace get_pv_by_workspace[%s][%s]fail,as[%s]'%(cluster, workspace, rlt.message))
        return rlt
    
    @ring0
    @ring3
    @ring5  
    def add_pv(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'workspace' not in data or not data['workspace']:
            return Result('',INVALID_PARAM_ERR, 'workspace is invalid', http.BAD_REQUEST)
        
        if 'group' not in data or not data['group']:
            return Result('',INVALID_PARAM_ERR, 'group is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        if 'pv_name' not in data or not data['pv_name']:
            return Result('',INVALID_PARAM_ERR, 'pv name is invalid', http.BAD_REQUEST)
        
        if 'capacity' not in data or not data['capacity']:
            return Result('',INVALID_PARAM_ERR, 'capacity is invalid', http.BAD_REQUEST)
        
        #if 'read_write_mode' not in data or not data['read_write_mode']:
        #    return Result('',INVALID_PARAM_ERR, 'read_write_mode is invalid', http.BAD_REQUEST)
        
        #if 'recovery_model' not in data or not data['recovery_model']:
        #    return Result('',INVALID_PARAM_ERR, 'recovery_model is invalid', http.BAD_REQUEST)
        
        if 'volume_type' not in data or data['volume_type'] not in [STORAGE_SHARE_TYPE_NFS, STORAGE_SHARE_TYPE_ISCSI]:
            return Result('',INVALID_PARAM_ERR, 'volume type is invalid', http.BAD_REQUEST)
        
        if PVDB.instance().is_volume_exist(data['cluster_name'], data['pv_name']):
            return Result('',INVALID_PARAM_ERR, 'persistent volume name is repeat', http.BAD_REQUEST)
        
        capacity = float(data['capacity'].strip("GgMm "))
        _calc =  self.calc_cluster_info(data['cluster_name'])
        if (_calc['free'] >> 20)  < capacity * 1024:
            return Result('', CAPACITY_LESS_THAN_REQUEST_ERR, 'Insufficient disk space')
        
        data['creator'] = args.get('passport',{}).get('username', '')
        rlt = StorageMgr.instance().create_persistent_volume(data)
        if not rlt.success:
            Log(1, 'Storage.add_pv create_persistent_volume[%s][%s]fail,as[%s]'%(data['cluster_name'], data['pv_name'], rlt.message))
            return rlt
        
        data['status'] = 0
        rlt = PVDB.instance().create_volume(data['cluster_name'], data)
        if rlt.success:
            LogAdd(3,  data['creator'], u'在集群[%s]创建容器卷[%s]挂载地址[%s]'%(data['cluster_name'], data['pv_name'], data['ip']))
        else:        
            Log(1, 'Storage.add_pv create_volume in etcd[%s]fail,as[%s]'%(str(data), rlt.message))
        
        return rlt
    
    @ring0
    @ring3
    @ring5
    def delete_pv(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Configure.add load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'pv_name' not in data or not data['pv_name']:
            return Result('',INVALID_PARAM_ERR, 'pv name is invalid', http.BAD_REQUEST)
        
        username = args.get('passport',{}).get('username', '')
        
        return StorageMgr.instance().delete_pv(data['cluster_name'], data['pv_name'], username)
        

    @ring0
    @ring3
    @ring5    
    def storageclasses(self, cluster, group=''):
        rlt = StorageClassDB.instance().read_storage_class_list(cluster, group)
        if not rlt.success:
            Log(1, 'Storage read_storage_class_list[%s][%s]fail,as[%s]'%(cluster, group, rlt.message))
        return rlt
    
    @ring0
    @ring3
    @ring5    
    def get_sc_by_group(self, group):
        rlt = StorageClassDB.instance().get_sc_by_group(group)
        if not rlt.success:
            Log(1, 'Storage.get_sc_by_group [%s]fail,as[%s]'%(group, rlt.message))
        return rlt


    @ring0
    @ring3
    @ring5
    def add_storage_class(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Storage.add_storage_class load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('',INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'group' not in data or not data['group']:
            return Result('',INVALID_PARAM_ERR, 'group is invalid', http.BAD_REQUEST)
        
        if 'ip' not in data or not data['ip']:
            return Result('',INVALID_PARAM_ERR, 'ip is invalid', http.BAD_REQUEST)
        
        if 'name' not in data or not data['name']:
            return Result('',INVALID_PARAM_ERR, 'storage class name is must', http.BAD_REQUEST)

        m = re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$", data['name'])
        if not m:
            return Result('',INVALID_PARAM_ERR, 'storage class name is invalid', http.BAD_REQUEST)
        
        data['volume_name'] = data['name'].replace('.','-')
        data['storage_class_name'] = data['name']
        data['namespace'] = STORAGE_CLASS_DEFAULT_NAMESPACE
        
        if 'capacity' not in data or not data['capacity']:
            return Result('',INVALID_PARAM_ERR, 'capacity is invalid', http.BAD_REQUEST)
        
        capacity = Parse2Float(data['capacity'])
        if capacity < 1:
            return Result('',INVALID_PARAM_ERR, 'capacity must be equal or greater than 1', http.BAD_REQUEST)
        
#         if 'volume_type' not in data or data['volume_type'] not in [STORAGE_SHARE_TYPE_NFS, STORAGE_SHARE_TYPE_ISCSI]:
#             return Result('',INVALID_PARAM_ERR, 'volume type is invalid', http.BAD_REQUEST)
        
        data['volume_type'] = STORAGE_SHARE_TYPE_NFS
        
        if StorageClassDB.instance().is_storage_class_exist(data['cluster_name'], data['storage_class_name']):
            return Result('',INVALID_PARAM_ERR, 'storage class name is repeat', http.BAD_REQUEST)
        
        if VolumeDB.instance().is_volume_exist(data['cluster_name'], data['volume_name']):
            return Result('',INVALID_PARAM_ERR, 'volume name is repeat', http.BAD_REQUEST)

        _calc =  self.calc_cluster_info(data['cluster_name'])
        if (_calc['free'] >> 20)  < capacity * 1024 * 2:
            return Result('', CAPACITY_LESS_THAN_REQUEST_ERR, 'Insufficient disk space')
        
        data['creator'] = args.get('passport',{}).get('username', '')
        rlt = StorageMgr.instance().create_storage_class(data)
        if not rlt.success:
            Log(1, 'Storage create_storage_class[%s][%s]fail,as[%s]'%(data['cluster_name'], data['storage_class_name'], rlt.message))
            return rlt
        
        data['status'] = STORAGE_CLASS_STATUS_NOT_READY
        rlt = StorageClassDB.instance().create_storage_class(data['cluster_name'], data)
        if rlt.success:
            LogAdd(3,  data['creator'], u'在集群[%s]创建动态卷[%s]挂载地址[%s]成功'%(data['cluster_name'], data['storage_class_name'], data['ip']))
        else:
            Log(1, 'Storage create_storage_class in etcd[%s]fail,as[%s]'%(str(data), rlt.message))
        
        return rlt
    
    @ring0
    @ring3
    @ring5
    def delete_storage_class(self, post_data, **args):
        try:
            data = json.loads(post_data.replace("'", "\'"))
        except Exception,e:
            Log(1,"Storage.delete_storage_class load data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e), http.BAD_REQUEST)
        
        if 'cluster_name' not in data or not data['cluster_name']:
            return Result('', INVALID_PARAM_ERR, 'cluster name is invalid', http.BAD_REQUEST)
        
        if 'name' not in data or not data['name']:
            return Result('', INVALID_PARAM_ERR, 'storage class name is invalid', http.BAD_REQUEST)
        
        username = args.get('passport',{}).get('username', '')
        
        return StorageMgr.instance().delete_storage_class(data['cluster_name'], data['name'], username)
        
    
    
    
    
    
    
    
    