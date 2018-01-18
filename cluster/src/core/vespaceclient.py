# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.



from twisted.web import http

from common.util import Result, NowMilli, getMD5
from core.errcode import VESPACE_RESPONSE_DATA_INVALID_ERR, \
    CALL_VESPACE_INSTERFACE_FAIL_ERROR, INVALID_PARAM_ERR
from frame.curlclient import CURLClient, Response, HTTP_EXCEPTION
from frame.exception import InternalException
from frame.logger import Log, PrintStack


MANAGER_HOST_PORT = 8081
STRATEGY_HOST_PORT = 9876
STOREGE_HOST_PORT = 9887
APPLICATION_HOST_PORT = 9888
DEFAULT_STORAGE_POOL_NAME = 'default'
DEFAULT_STORAGE_DOMAIN = 'default'
STORAGE_SHARE_TYPE_NFS = 'NFS'
STORAGE_SHARE_TYPE_ISCSI = 'iSCSI'
DEFAULT_SHARE_TYPE = STORAGE_SHARE_TYPE_NFS
DEFAULT_REPLICA_NUMBER = 2

HOST_TYPE_STRATEGY = 2
HOST_TYPE_STOREGE = 1
HOST_TYPE_APPLICATION = 3

MIN_EXPIRE_TIME = 1000 * 60 * 3
TOKEN_EXPIRE_TIME = 1000 * 60 * 15
VESPACE_DATA_EXIST_ALREADY_EXIST_ERR = 5002

DEFAULT_USER_NAME = 'admin'
DEFAULT_PASSWORD = 'admin'

def VeResult(rltDict):
    if not isinstance(rltDict, dict):
        return Result(rltDict)
    
    result = int(rltDict.get("ecode", 0))
    msg = rltDict.get("message", "done")
    content = rltDict.get("data", None)
    
    return Result(content, result, msg)


class VeSpaceClient(CURLClient):
    '''
    # VeSpace服务的客户端，实现对接功能
    '''   

    def __init__(self, domain, username, password):
        CURLClient.__init__(self, '%s:%s'%(domain, MANAGER_HOST_PORT))
        self.token = None
        self.token_expire_time = 0
        self.username = username
        self.password = password
        self.clusters = {}

    def members(self, ip=None):
        """
        # 登陆
        /v1/system/member/list
        """
        domain = self.domain if ip is None else "%s:%s"%(ip, MANAGER_HOST_PORT)
        url = "http://" + domain + '/v1/system/member/list'
        response = self.do_get(url, '', domain=domain)
        #response.log('VeSpaceClient.members')
        if response.success:
            data = response.json_data()
            if data is None or not isinstance(data, dict):
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.members data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.members fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def login(self, ip=None):
        """
        # 登陆
        /v1/authentication/login
        """
        domain = self.domain if ip is None else "%s:%s"%(ip, MANAGER_HOST_PORT)
        url = "http://" + domain + '/v1/authentication/login'
        data = {"username":self.username, "password":getMD5(self.password)}
        response = self.do_post(url, data, '', domain=domain)
        #response.log('VeSpaceClient.login')
        if response.success:
            data = response.json_data()
            if data is None or not isinstance(data, dict):
                raise InternalException('VeSpaceClient.login data parse to json fail.', VESPACE_RESPONSE_DATA_INVALID_ERR)
            
            if data.get('ecode') != 0:
                raise InternalException('VeSpaceClient.login fail as[%s].'%(data.get('message')), VESPACE_RESPONSE_DATA_INVALID_ERR)
            
            self.token = data.get('data', {}).get('token')
            self._cache_cluster_info(data.get('data', {}).get('clusters'))
            self.token_expire_time = NowMilli() + TOKEN_EXPIRE_TIME
        else:
            raise InternalException('VeSpaceClient.login fail,as[%s].'%(response['body']), CALL_VESPACE_INSTERFACE_FAIL_ERROR)
        
    def _cache_cluster_info(self, clusters):
        if clusters and isinstance(clusters, list):
            self.clusters = {}
            for cluster in clusters:
                self.clusters[cluster.get('name')] = cluster.get('uuid')
    
    def refreshtoken(self, ip=None):
        """
        # 刷新token
        /v1/authentication/refreshtoken
        """
        domain = self.domain if ip is None else "%s:%s"%(ip, MANAGER_HOST_PORT)
        url = "http://" + domain + '/v1/authentication/refreshtoken'
        response = self.do_post(url, domain=domain)
        #response.log('VeSpaceClient.refreshtoken')
        if response.success:
            data = response.json_data()
            if data is None or not isinstance(data, dict):
                raise InternalException('VeSpaceClient.refreshtoken data parse to json fail.', VESPACE_RESPONSE_DATA_INVALID_ERR)
            
            if data.get('ecode') != 0:
                raise InternalException('VeSpaceClient.refreshtoken fail as[%s].'%(data.get('message')), VESPACE_RESPONSE_DATA_INVALID_ERR)
            
            self.token = data.get('data',{}).get('token')
            self.token_expire_time = NowMilli() + TOKEN_EXPIRE_TIME
        else:
            raise InternalException('VeSpaceClient.refreshtoken fail,as[%s].'%(response['body']), CALL_VESPACE_INSTERFACE_FAIL_ERROR)

    def logout(self, ip=None):
        """
        # 登出
        /v1/authentication/logout
        """
        domain = self.domain if ip is None else "%s:%s"%(ip, MANAGER_HOST_PORT)
        url = "http://" + domain + '/v1/authentication/logout'
        response = self.do_post(url, domain=domain)
        #response.log('VeSpaceClient.logout')
        if response.success:
            data = response.json_data()
            if data is None or not isinstance(data, dict):
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.logout data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.logout fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def get_token(self, domain=None):
        if self.token is None or self.token_expire_time < NowMilli():
            self.login(domain)
        
        elif self.token_expire_time - NowMilli() < MIN_EXPIRE_TIME:
            self.refreshtoken(domain)
            
        return self.token
            
        
    def test(self):        
        try:
            rlt = self.members()
            if rlt.success and rlt.content.get('leader'):
                return True
        except Exception,e:
            PrintStack()
            Log(1, 'VeSpaceClient.test except,as[%s]'%(str(e)))

        return False
    
    
    def test_storage_service(self, host_ip):
        return self.test_service(host_ip, STOREGE_HOST_PORT)
    
    def test_application_service(self, host_ip):
        return self.test_service(host_ip, APPLICATION_HOST_PORT)
    
    def test_strategy_service(self, host_ip):
        url = 'http://%s:%s/cosrv/master/inspect'%(host_ip, STRATEGY_HOST_PORT)
        data = {"Ip": "%s:%s"%(host_ip, STRATEGY_HOST_PORT)}
        response = self.do_post(url, data, '')
        if not response.success:
            return False
        
        data = response.json_data()
        if data is None:
            return False
        
        return data.get("Result") == 0
        
    
    def test_service(self, host_ip, port):
        url = 'http://%s:%s'%(host_ip, port)
        response = self.do_get(url ,'')
        Log(4, 'VeSpaceClient.test_service[{}][{}] status_code={}'.format(host_ip, port, response.status_code))
        if response.status_code >= 200 and response.status_code < 500 :
            return True
        else:
            return False

    def add_license(self, cluster_id, license_str):
        """
        # 增加集群
        /v1/cluster/add
        """
        url = "http://" + self.domain + '/v1/license/add'
        #license_str = '68Qe0d9aNaRdV1Q5w3M-D4A5w6MfD-A4weMfD3A-wbM2D7A4x-N9T0Ebw8NfD0c13bN2T8Yf44M3j6A038M6T7A8wdM-T0g3xbM5D-A4w3Q8zbA-waM1EcYew-M4DaE5w1M1D5AfwfM4DfIc4eM6D9A7x5NaD7E8wdM-D2A0xdM0T-A4wbMcD9A-xbM4T7E8x-M6T1Ecx0M4T8E5xe21f56d8a0d84-8bcf-48f5-8034-1afd8e19424ee39f45'
        data = {"license":license_str, "clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.add_license')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.create_cluster data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.create_cluster fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    
    def create_cluster(self, name, ip):
        """
        # 增加集群
        /v1/cluster/add
        """
        url = "http://" + self.domain + '/v1/cluster/add'
        data = {"name":name, "ip":ip}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.create_cluster')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.create_cluster data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            if data.get('ecode') == 1000 and name in self.clusters and self.clusters[name]:
                return Result({'name':name, 'uuid':self.clusters[name]})
            elif data.get('ecode') == 0:
                self.clusters[name] = (data.get('data') or {}).get('uuid')
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.create_cluster fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def delete_cluster(self, cluster_id):
        """
        # 删除集群
        /v1/cluster/delete
        """
        url = "http://" + self.domain + '/v1/cluster/delete'
        data = {"clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.delete_cluster')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.delete_cluster data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.delete_cluster fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def get_cluster_info(self, username, cluster_id):
        """
        # 取得集群信息
        http://192.168.4.111:8081/v1/user/cluster/list?pagenum=0&pagesize=10&filtername=&username=admin&clusteruuid=cba83974-d1fd-4f9a-98ac-98bbaf4682b5
        """
        url = 'http://%s/v1/user/cluster/list?pagenum=0&pagesize=10&filtername=&username=%s&clusteruuid=%s'%(
                self.domain, username, cluster_id)
        response = self.do_get(url)
        #response.log('VeSpaceClient.get_cluster_info')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.get_cluster_info data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.get_cluster_info fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def create_domain(self, cluster_id, domain_name):
        """
        # 取得集群信息
        /v1/domain/add
        """
        
        
    def delete_domain(self, cluster_id, domain_name):
        """
        # 取得集群信息
        /v1/domain/delete
        """
        
    def get_domain_list(self, cluster_id, page_index, page_size):
        """
        # 取得集群信息
        /v1/domain/list
        """
    
    def get_domain_info(self, cluster_id, domain_name, page_index, page_size):
        """
        # 取得集群信息
        /v1/domain/get
        """
    
    def get_domain_name_list(self, cluster_id):
        """
        # 取得集群信息
        /v1/domain/names
        """
        
    def create_namespace(self, cluster_id, namespace_name):
        """
        # 增加命名空间
        /v1/namespace/add
        '{"namespace":"namespace01","clusterid":5}'
        """
        
        
    def delete_namespace(self, cluster_id, namespace_name):
        """
        # 删除命名空间
        /v1/namespace/delete
        '{"namespace":"namespace01","clusterid":5}'
        """
        
    def get_namespace_list(self, cluster_id, page_index, page_size):
        """
        # 命名空间列表
        /v1/namespace/list
        'http://192.168.14.250:8080/v1/namespace/list?pagenum=0&pagesize=6&filtername=&username=admin&clusterid=5'
        """
    
    def get_namespace_info(self, cluster_id, namespace_name, page_index, page_size):
        """
        # 命名空间详情
        /v1/namespace/get
        'http://192.168.14.250:8080/v1/namespace/get?namespace=default&namespace=0&poolpagesize=5&strategypagenum=0&strategypagesize=5&strategyfiltername=&username=admin&clusterid=5'
        """
    
    def _get_server_port(self, hosttype):
        if hosttype == HOST_TYPE_STRATEGY:
            return STRATEGY_HOST_PORT
        elif hosttype == HOST_TYPE_STOREGE:
            return STOREGE_HOST_PORT
        elif hosttype == HOST_TYPE_APPLICATION:
            return APPLICATION_HOST_PORT
        
        Log(1, 'VeSpaceClient._get_server_port fail, invalid host type [%s]'%(hosttype))
        return 0
    
    def add_host(self, cluster_id, domain, ip, host_type):
        """
        # 取得集群信息
        /v1/host/add
        '{"ip":"192.168.14.21","port":9887,"domainname":"14_21","hosttype":1,"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}'
        """
        port = self._get_server_port(host_type)
        url = "http://" + self.domain + '/v1/host/add'
        data = {"ip":ip, "port":port, "domainname":domain, "hosttype":host_type, "clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.create_host')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.create_host data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.create_host fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
        
    def delete_host(self, cluster_id, domain_name, ip, port, host_type, force=True):
        """
        # 取得集群信息
        /v1/host/delete
        @param param: '{"ip":"192.168.14.21","port":9887,"domainname":"14_21","hosttype":1,"byforce":true,"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}'
        """
        url = "http://" + self.domain + '/v1/host/delete'
        data = {"ip":ip, "port":port, "domainname":domain_name, "hosttype":host_type, "clusteruuid":cluster_id, "byforce":force}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.delete_host')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.delete_host data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.delete_host fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def get_ctl_host_list(self, cluster_id, page_index, page_size):
        """
        # 应用主机列表
        /v1/domain/list
        """ 
    
    def get_ctl_host_info(self, cluster_id, ip, port, page_index, page_size):
        """
        # 应用主机详情
        /v1/host/controller/get
        """
        
    def get_storage_host_list(self, cluster_id, filtername, page_index, page_size):
        """
        # 存储主机列表
        /v1/host/storage/list
        'http://192.168.14.28:8080/v1/host/storage/list?pagenum=0&pagesize=6&filtername=&domainnames=14_15&clusterid=1'
        """ 
    
    def get_storage_host_info(self, cluster_id, domain, ip, port, page_index=0, page_size=10):
        """
        # 取得存储主机详细信息
        /v1/host/storage/get
        'http://192.168.14.28:8080/v1/host/storage/get?ip=192.168.14.15&port=9887&domainname=14_15&componentspagenum=0&componentspagesize=5&clusteruuid=1'
        """
        url = 'http://%s/v1/host/storage/get?ip=%s&port=%s&domainname=%s&componentspagenum=%s&componentspagesize=%s&duration=60&count=10&clusteruuid=%s'%(
                self.domain, ip, port, domain, page_index, page_size, cluster_id)
        response = self.do_get(url)
        #response.log('VeSpaceClient.get_storage_host_info')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.get_storage_host_info data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.get_storage_host_info fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def get_strategy_host_list(self, cluster_id, filtername, page_index, page_size):
        """
        # 策略主机详情
        /v1/host/strategy/list
        'http://192.168.14.28:8080/v1/host/strategy/list?clusterid=1'
        """ 
    
    def get_strategy_host_info(self, cluster_id, ip, port, page_index, page_size):
        """
        # 应用主机详情
        /v1/host/storage/get
        'http://192.168.14.28:8080/v1/host/strategy/get?ip=192.168.14.15&port=9876&clusterid=1'
        """
        
    def add_data_disk(self, cluster_id, domain_name, ip, port, device_list):
        """
        # 增加数据盘
        /v1/host/storage/adddatadevice
        {"ip":"192.168.3.65","port":9887,"domain":"default","devices":["/dev/sdb"],"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}
        """
        url = "http://" + self.domain + '/v1/host/storage/adddatadevice'
        data = {"ip":ip, "port":port, "domain":domain_name, "devices":device_list, "clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.add_data_disk')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.add_data_disk data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.add_data_disk fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
        
    def delete_data_disk(self, cluster_id, domain_name, ip, port, device_list):
        """
        # 删除数据盘
        /v1/host/storage/deletedatadevice
        '{"ip":"192.168.14.15","port":9887,"domain":"14_15","devices":["/dev/sdc"],"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}'
        """
        url = "http://" + self.domain + '/v1/host/storage/deletedatadevice'
        data = {"ip":ip, "port":port, "domain":domain_name, "devices":device_list, "clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.delete_data_volume')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.delete_data_volume data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.delete_data_volume fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def add_cache_disk(self, cluster_id, domain_name, host_info):
        """
        # 增加缓存盘
        /v1/host/storage/addcachedevice
        '{"ip":"192.168.14.15","port":9887,"domain":"14_15","devices":["/dev/sdb"],"clusterid":6}'
        """
        
        
    def delete_cache_disk(self, cluster_id, domain_name, host_id, force):
        """
        # 删除缓存盘
        /v1/host/storage/deletecachedevice
        '{"ip":"192.168.14.15","port":9887,"domain":"14_15","devices":["/dev/sdb"],"clusterid":6}'
        """
        
    def create_pool(self, cluster_id, pool_name):
        """
        # 取得命名空间信息
        /v1/pool/add
        '{"name":"pn1","namespace":"ns1","strategy":"strg1","clusterid":6}'
        """
        
        
    def delete_pool(self, cluster_id, pool_name):
        """
        # 取得命名空间信息
        /v1/pool/delete
        '{"name":"pn1","namespace":"ns1","clusterid":6}'
        """
        
    def get_pool_list(self, cluster_id, page_index, page_size):
        """
        # 取得命名空间信息
        /v1/pool/list
        'http://192.168.14.250:8080/v1/pool/list?pagenum=0&pagesize=10&filtername=&clusterid=6'
        """
    
    def get_pool_info(self, cluster_id, pool_name, page_index, page_size):
        """
        # 池详情
        /v1/pool/get
        'http://192.168.14.250:8080/v1/pool/get?name=200&namespace=default&volumepagenum=0&volumepagesize=10&clusterid=6'
        """
    
    def get_pool_name_list(self, cluster_id):
        """
        # 池名称列表
        /v1/pool/names
        'http://192.168.14.250:8080/v1/pool/names?namespace=default&clusterid=1'
        """
        
    def create_strategy(self, cluster_id, strategy_name):
        """
        # 添加策略
        /v1/strategy/add
        '{"name":"strg1","namespace":"default","attr":{"replica":"1","filter_cpu_core":"1","filter_memory":"1073741824","filter_cpu_usage":"1","weigher_cpu_core":"2","weigher_load":"1","weigher_memory":"1","weigher_cpu_usage":"1"},"clusterid":6}
        """
        
        
    def delete_strategy(self, cluster_id, strategy_name):
        """
        # 删除侧路
        /v1/strategy/delete
        '{"name":"strg1","namespace":"default","clusterid":6}'
        """
        
    def get_strategy_list(self, cluster_id, page_index, page_size):
        """
        # 策略列表
        /v1/strategy/list
        """
    
    def get_strategy_info(self, cluster_id, strategy_name, page_index, page_size):
        """
        # 策略详情
        /v1/strategy/get
        'http://192.168.14.250:8080/v1/strategy/get?name=001&namespace=default&poolpagenum=0&poolpagesize=5&clusterid=6'
        """
    
    def get_strategy_name_list(self, cluster_id):
        """
        # 获取策略名称
        /v1/strategy/names
        'http://192.168.14.250:8080/v1/strategy/names?namespace=default&clusterid=1'
        """
    
    def _get_nfs_volume_attribute(self, replica):
        """
        {
            "DevType" : "share",
            "DataType" : "stripe",
            "Safety" : "first",
            "Encrypto" : "off",
            "DriveType" : "HDD",
            "ThinProvision" : "on",
            "ReadIOPSLimit" : "0",
            "WriteIOPSLimit" : "0",
            "ReadBytesLimit" : "0",
            "WriteBytesLimit" : "0",
            "ShareType" : "nfs",
            "NFSArgs" : "rw@sync@no_root_squash",
            "NFSAcl" : "*",
            "StripeShift" : "12",
            "StripeNum" : "4"
        } 
        """
        return {
            "DevType":"share",
            "DataType":"stripe",
            "Safety":"first",
            "Encrypto":"off",
            "DriveType":"HDD",
            "ThinProvision":"off",
            "ReadIOPSLimit" : "0",
            "WriteIOPSLimit" : "0",
            "ReadBytesLimit" : "0",
            "WriteBytesLimit" : "0",
            "ShareType":"nfs",
            "NFSArgs" : "rw@sync@no_root_squash",
            "NFSAcl" : "*",
            "replica": str(replica),
            "StripeShift":"12",
            "StripeNum":"8",
   
        }
    
    def _get_iscsi_volume_attribute(self, replica, target_port):
        """
        {
            "DevType": "target",
            "DataType" : "stripe",
            "Safety" : "first",
            "Encrypto" : "off",
            "DriveType" : "HDD",
            "ThinProvision" : "on",
            "ReadIOPSLimit" : "0",
            "WriteIOPSLimit" : "0",
            "ReadBytesLimit" : "0",
            "WriteBytesLimit" : "0",
            "TargetACL" : "ALL",
            "TargetDPort" : "0",
            "replica" : "1",
            "StripeShift" : "12",
            "StripeNum" : "8"
        }
        """
        return {
            "DevType":"target",
            "DataType":"stripe",
            "Safety":"first",
            "Encrypto":"off",
            "DriveType":"HDD",
            "ThinProvision":"off",
            "ReadIOPSLimit" : "0",
            "WriteIOPSLimit" : "0",
            "ReadBytesLimit" : "0",
            "WriteBytesLimit" : "0",
            "TargetACL" : "ALL",
            "TargetDPort" : "0",
            "replica": str(replica),
            "StripeShift":"12",            
            "StripeNum":"8"
        }
        
        
    def create_volume(self, volume_info):
        """
        # 创建卷
        /v1/volume/add
        {"name":"asd","capacity":"1G","namespace":"default","poolname":"default",
        "attribute":{"DevType":"share","DataType":"stripe","Safety":"first","Encrypto":"off","DriveType":"HDD","ThinProvision":"off",
        "ShareType":"nfs","replica":"3","StripeShift":"12","StripeNum":"8"},
        "address":"192.168.14.43:9888","clusterid":1}
        """
        try:
            data = {
                "name": volume_info['name'],
                "capacity": volume_info['capacity'],
                "snap_capacity": volume_info['capacity'],
                "namespace": volume_info.get('namespace', DEFAULT_STORAGE_DOMAIN),
                "poolname": volume_info.get('pool', DEFAULT_STORAGE_POOL_NAME),
                "address": volume_info['ip'],
                "clusteruuid": volume_info['cluster_id']
            }
        except:
            return Result('',INVALID_PARAM_ERR, 'parameter is invalid', http.BAD_REQUEST)
        
        url = "http://" + self.domain + '/v1/volume/add'
        share_type = volume_info.get('share_type', DEFAULT_SHARE_TYPE)
        replica = volume_info.get('replica', DEFAULT_REPLICA_NUMBER)
        if share_type == DEFAULT_SHARE_TYPE:
            data['attribute'] = self._get_nfs_volume_attribute(replica)
        else:
            data['attribute'] = self._get_iscsi_volume_attribute(replica, volume_info.get('target_port', 3260))
            
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.create_volume')
        
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.create_volume data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.create_volume fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def delete_volume(self, cluster_id, volume_name):
        """
        # 删除卷
        /v1/volume/delete
        '{"name":"test-del","poolname":"default","namespace":"default","clusteruuid":6}'
        """
        url = "http://" + self.domain + '/v1/volume/delete'
        data = {"name":volume_name, "poolname":DEFAULT_STORAGE_POOL_NAME, "namespace":DEFAULT_STORAGE_DOMAIN, "clusteruuid":cluster_id}
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.delete_volume')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.delete_volume data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.delete_volume fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def get_volume_list(self, cluster_id, filtername, page_index=0, page_size=10):
        """
        # 取得卷列表
        /v1/volume/list
        http://192.168.3.66:8081/v1/volume/list?filtername=&pagenum=0&pagesize=10&filterstatus=-1&filtermounted=0&clusteruuid=d0cfaa10-92c8-4c10-b256-d9a1488517e9
        """
        url = 'http://%s/v1/volume/list?filtername=%s&pagenum=%s&pagesize=%s&filterstatus=-1&filtermounted=0&clusteruuid=%s'%(
                self.domain, filtername, page_index, page_size, cluster_id)
        response = self.do_get(url)
        #response.log('VeSpaceClient.get_volume_list')
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.get_volume_list data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.get_volume_list fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def get_volume_disk_list(self, cluster_id, page_index, page_size):
        """
        # 取得卷列表
        /v1/volume/disk/get
        'http://192.168.14.28:8080/v1/volume//disk/get?ip=192.168.14.15&clusterid=1'
        """
    
    def get_volume_info(self, cluster_id, namespace, poolname, volume_name):
        """
        # 取得卷信息
        /v1/volume/get
        http://192.168.17.203:8081/v1/volume/get?name=vol1&namespace=default&poolname=default&clusteruuid=01332be6-a458-46ba-88ed-d9033f102239
        """
        url = 'http://%s/v1/volume/get?name=%s&namespace=%s&poolname=%s&clusteruuid=%s'%(
                self.domain, volume_name, namespace, poolname, cluster_id)
        response = self.do_get(url)
        #response.log('VeSpaceClient.get_volume_info')
        
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.get_volume_info data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.get_volume_info fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
    
    def expansion_volume(self, cluster_id):
        """
        # 卷扩容
        /v1/volume/expansion
        '{"capacity":"2G","name":"vol1","poolname":"default","namespace":"default","clusterid":6}'
        """
        
        
    def mount_volume(self, volume_info, app_node_list):
        """
        # 挂载卷
        /v1/volume/map
        {"name":"iscsi002","poolname":"default","namespace":"default","addresses":[{"ip":"192.168.3.65","port":9888}],"targetdport":0,
        "attr":{"NFSArgs":"rw@sync@no_root_squash","NFSAcl":"*"},"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}
        """
        try:
            data = {
                "name": volume_info['name'],
                "namespace": volume_info.get('namespace', DEFAULT_STORAGE_DOMAIN),
                "poolname": volume_info.get('pool', DEFAULT_STORAGE_POOL_NAME),
                "addresses": app_node_list,
                "clusteruuid": volume_info['cluster_id'],
                "attr":{"NFSArgs":"rw@sync@no_root_squash","NFSAcl":"*"}
            }
            
            if volume_info.get('share_type', DEFAULT_SHARE_TYPE) == STORAGE_SHARE_TYPE_ISCSI:
                data["targetdport"] = volume_info.get('targetdport', 0)
            
        except:
            return Result('', INVALID_PARAM_ERR, 'parameter is invalid', http.BAD_REQUEST)
        
        url = "http://" + self.domain + '/v1/volume/map'
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.mount_volume')
        
        if response.success:
            Log(3, 'VeSpaceClient.mount_volume success.')
            
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.mount_volume data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.mount_volume fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)

        
    def unmount_volume(self, volume_info, app_node_list):
        """
        # 卸载卷
        /v1/volume/unmap
        {"name":"iscsi002","poolname":"default","namespace":"default","addresses":[{"ip":"192.168.3.65","port":9888}],"clusteruuid":"d0cfaa10-92c8-4c10-b256-d9a1488517e9"}
        """
        try:
            data = {"name": volume_info['name'],
                    "namespace": volume_info.get('namespace', DEFAULT_STORAGE_DOMAIN),
                    "poolname": volume_info.get('pool', DEFAULT_STORAGE_POOL_NAME),
                    "addresses": app_node_list,
                    "clusteruuid": volume_info['cluster_id']
                }
        except:
            return Result('', INVALID_PARAM_ERR, 'parameter is invalid', http.BAD_REQUEST)
        
        url = "http://" + self.domain + '/v1/volume/unmap'
        response = self.do_post(url, data)
        #response.log('VeSpaceClient.unmount_volume')
        
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.unmount_volume data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.unmount_volume fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)        
        
    def clone_volume(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 克隆卷
        /v1/volume/clone
        '{"name":"vol1","snapshotname":"snp1","clonename":"clone1","poolname":"default","namespace":"default","clusterid":6}'
        """
        
    def modify_volume(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 卷类型转换
        /v1/volume/modify
        '{"name":"vol11","poolname":"default","namespace":"default","devtype":"target","acl":"ALL","clusterid":6}'
        """
        
    def modify_volume_iops(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 修改iops
        /v1/volume/iops
        '{ "clusterid": 2,"name": "test-iops","namespace": "default", "poolname": "default", "readbyteslimit": "3", "readiopslimit": "3", "wreteiopslimit": "3", "writebyteslimit": "3" }'
        """
        
    def convert_volume_sharetype(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 共享类型转换
        /v1/volume/sharetypeconvert
        '{"name":"volsh","poolname":"default","namespace":"default","sharetype":"nfs","clusterid":2}'
        """
        
    def migrate_volume(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 迁移卷
        /v1/volume/migrate
        '{"name":"vol11","poolname":"default","namespace":"default","devtype":"target","acl":"ALL","clusterid":6}'
        """
        
    def create_snapshot(self, cluster_id, snapshot_name):
        """
        # 创建快照
        /v1/volume/snapshot/create
        '{"name":"vol1","description":"快照1","snapshotname":"snp1","poolname":"default","namespace":"default","clusterid":6}'
        """
        
        
    def delete_snapshot(self, cluster_id, snapshot_name):
        """
        # 删除快照
        /v1/volume/snapshot/delete
        '{"snapshotname":"snap1","namespace":"default","poolname":"default","name":"volmg","clusterid":1}'
        """
        
    def rollback_snapshot(self, cluster_id, snapshot_name):
        """
        # 回滚快照
        /v1/volume/snapshot/rollback
         '{"name":"vol1","snapshotname":"snp1","poolname":"default","namespace":"default","clusterid":6}'
        """

    def get_snapshot_list(self, cluster_id, page_index, page_size):
        """
        # 取得快照列表
        /v1/volume/snapshot/list
        'http://192.168.14.28:8080/v1/volume/snapshot/list?name=volsh&namespace=default&poolname=default&clusterid=2'
        """
    def get_snapshot_tree(self, cluster_id, page_index, page_size):
        """
        # 快照树
        /v1/volume/snapshot/tree
        'http://192.168.14.28:8080/v1/volume/snapshot/tree?name=volsh&namespace=default&poolname=default&clusterid=2'
        """
    
    
    
    def get_snapshot_name_list(self, cluster_id):
        """
        # 取得快照名字列表
        /v1/snapshot/names
        """
        
    def create_user(self, cluster_id, user_name):
        """
        # 创建用户
        /v1/user/add
        '{"email":"admin@example.com","username":"test","password":"e10adc3949ba59abbe56e057f20f883e"}'
        """
        
        
    def delete_user(self, cluster_id, user_name):
        """
        # 删除用户
        /v1/user/delete
        '{"username":"test1"}'
        """
        
    def get_user_list(self, filter_key="", page_index=0, page_size=10):
        """
        # 取得用户列表
        /v1/user/list
        'http://192.168.14.250:8080/v1/user/list?pagenum=0&pagesize=7&filtername='
        """
        url = 'http://%s/v1/user/list?pagenum=%s&pagesize=%s&filtername=%s'%(
                self.domain, page_index, page_size, filter_key)
        response = self.do_get(url)
        #response.log('VeSpaceClient.get_user_list')
        
        if response.success:
            data = response.json_data()
            if data is None:
                return Result('', VESPACE_RESPONSE_DATA_INVALID_ERR, 'VeSpaceClient.get_user_list data parse to json fail.', http.INTERNAL_SERVER_ERROR)
            
            return VeResult(data)
        else:
            return Result('', CALL_VESPACE_INSTERFACE_FAIL_ERROR, 'VeSpaceClient.get_user_list fail,as[%s].'%(response['body']), http.INTERNAL_SERVER_ERROR)
        
    def get_user_enable_list(self, cluster_id, page_index, page_size):
        """
        # 取得用户授权列表
        /v1/user/authorization/list
        'http://192.168.14.250:8080/v1/user/authorization/list?username=lin&clusterid=1'
        """
        
    def modify_user_email(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 修改用户邮箱
        /v1/user/modifyemail
        '{"email": "admin@example.com",  "username": "john"  }'
        """    
    
    def modify_user_password(self, cluster_id, snapshot_name, page_index, page_size):
        """
        # 修改用户密码
        /v1/user/modifypassword
        '{"username":"john","oldpassword":"21232f297a57a5a743894a0e4a801fc3","newpassword":"e10adc3949ba59abbe56e057f20f883e","clusterid":1}'
        """    
        
    def enable_cluster(self, cluster_id, user_name):
        """
        # 给用户授权集群
        '{"username":"lin","clusterid":3}'
        /v1/user/cluster/add
        """
        
        
    def disable_cluster(self, cluster_id, user_name):
        """
        # 取消用户的集群授权
        /v1/user/cluster/delete
        '{"username":"lin","clusterid":4}'
        """
        
    def get_user_cluster_list(self, namespace_id, page_index, page_size):
        """
        # 普通用户集群列表
        /v1/user/namespace/list
        'http://192.168.14.250:8080/v1/user/cluster/list?pagenum=0&pagesize=10&filtername=&username=admin'
        """
        
    def get_user_cluster_info(self, cluster_id, user_name, page_index, page_size):
        """
        # 用户的授权集群详情
        /v1/user/cluster/get
        'http://192.168.14.250:8080/v1/user/cluster/get?username=admin&clusterid=1'
        """
        
    def enable_namespace(self, namespace_id, user_name):
        """
        # 给用户授权命名空间
        /v1/user/namespace/add
        '{"clusterid":4,"username":"lin","namespaces":["default"]}'
        """
        
        
    def disable_namespace(self, namespace_id, user_name):
        """
        # 取消用户的命名空间授权
        /v1/user/namespace/delete
        '{"clusterid":1,"username":"lin","namespaces":["default"]}'
        """
    
    def get_user_ns_list(self, namespace_id, page_index, page_size):
        """
        # 普通用户命名空间列表
        /v1/user/namespace/list
        'http://192.168.14.250:8080/v1/user/namespace/list?pagenum=0&pagesize=6&filtername=&username=test1'
        """
        
    def get_user_namespace_info(self, cluster_id, user_name, page_index, page_size):
        """
        # 普通用户命名空间详情
        /v1/user/namespace/get
        'http://192.168.14.250:8080/v1/user/namespace/get?namespace=default&poolpagenum=0&poolpagesize=5&strategypagenum=0&strategypagesize=5&strategyfiltername=&username=test1'
        """   
        
        
    def get_user_logs(self, cluster_id, page_index, page_size):
        """
        # 取得用户操作日志
        /v1/user/operatelogs
        'http://192.168.14.250:8080/v1/user/operatelogs?pagenum=0&pagesize=10&username=admin&clusterid=5'
        """

    def callRemote(self, url, method, token=None, post_data=None, **args):
        try:
            if token is None:
                token = self.get_token()
            Headers = self.getBasicHeaders(token, **args)
            response = self.send_http_request(url, Headers, method, post_data)
            Log(4, u"callRemote[%s][%s]return[%s]"% (method, url, response.respond_body))
        except InternalException,e:
            Log(4, u"callRemote InternalException[%s][%s]return[%s]"% (method, url, str(e)))
            return Response('', '', e.errid, e.value)
        except Exception, e:
            Log(4, u"callRemote Exception[%s][%s]return[%s]"% (method, url, str(e)))
            return Response('', '', HTTP_EXCEPTION, str(e))
        else:
            return response
        
        