# -*- coding: utf-8 -*-
"""
Created on 2017年7月26日

"""

import json
import threading
import requests
from common.guard import LockGuard
from common.util import Result
from core.errcode import FAIL, SUCCESS, CLU_IS_PENDING, CLU_IS_ERROR
from frame.configmgr import GetSysConfig
from frame.logger import Log

HTTP_OK_200 = 200


class Response(object):
    def __init__(self, res):
        """
        """
        super(Response, self).__init__()
        self.res = res

    @property
    def success(self):
        return self.res.status_code == HTTP_OK_200

    @property
    def message(self):
        return self.res.text

    @property
    def fail(self):
        return self.res.status_code < 200 or self.res.status_code > 299

    def __getitem__(self, key):
        if "body" == key:
            return self.res.text
        elif "status_code" == key:
            return self.res.status_code
        else:
            return None

    def __str__(self):
        return "Response<'status_code':%d,'headers':'%s','body':%s>" % \
               (self.res.status_code, self.res.headers, self.res.text)

    def log(self, act):
        if self.res.status_code == HTTP_OK_200:
            Log(3, '[%s] success, return [%s]' % (act, self.res.text))
        else:
            Log(1, '[%s] fail, return [%s]' % (act, self.res.text))

    def json_data(self):
        return self.res.json()

    def to_json(self):
        return {
            'error_code': SUCCESS if self.res.status_code == HTTP_OK_200 else FAIL,
            'error_msg': self.res.text,
            'content': self.res.json()
        }


class LauncherClient(object):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        host = GetSysConfig('cluster_auth_info_host')
        port = GetSysConfig('cluster_auth_info_port')
        self.laucher_url = 'http://%s:%s/clusters' % (host, port)
        self.timeout = 5

    def get_cluster_list(self):
        """
        # 取得集群列表
        """
        try:
            r = requests.get(self.laucher_url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_cluster_list except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_cluster_info(self, cluster_name):
        """
        rest.Get("/clusters", launcherapi.GetClusters),
        """
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_cluster_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def delete_cluster(self, cluster_name):
        """
        # 删除集群
        """
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.delete(url, timeout=15)
        except requests.exceptions.RequestException as e:
            return Result('', msg='delete_cluster except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def delete_ha_master(self, cluster_name, host_ip):
        """
        删除高可用集群的master
        :param host_ip:
        :return:
        """
        url = self.laucher_url + '/%s/masters/%s' % (cluster_name, host_ip)
        try:
            r = requests.delete(url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='delete_cluster except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def add_ha_master(self, cluster_name, data):
        """
        高可用k8s集群添加master
        :param cluster_name:
        :param data:
        :return:
        """
        url = self.laucher_url + '/%s/masters/new' % cluster_name
        try:
            r = requests.post(url, data=json.dumps(data), headers={"content-type": "application/json"}, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='add_ha_master except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def get_master_list(self, cluster_name):
        """
        # 获取管理节点列表
        """
        url = self.laucher_url + '/%s/masters' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_list except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_master_info(self, cluster_name, master_name):
        """
        # 获取管理节点信息
        """
        url = self.laucher_url + '/%s/masters/%s' % (cluster_name, master_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_host_error_reason(self, cluster_name, host_type, host_ip):
        """
        # 获取添加节点失败的原因
        """
        url = self.laucher_url + '/{}/{}/{}'.format(cluster_name, host_type, host_ip)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get host error reason except:{}'.format(e), result=500)

        res = Response(r)
        if not res.success:
            res.log('LauncherClient.get_host_error_reason error')
            return res
        data = res.json_data()
        if not data.get('errormsg'):
            # return Result({"error_reason": ["lost connection host"]})
            return None
        return Result({'error_reason': [data.get('errormsg')]})

    def get_master_status(self, cluster_name, host_ip):
        url = self.laucher_url + '/%s/masters' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_info except:{}'.format(e), result=500)

        res = Response(r)
        if not res.success:
            res.log('LauncherClient.get_master_status')
            return res

        nodes = res.json_data().values()
        for v in nodes:
            if v.get('hostip') == host_ip:
                status_list = []
                for m in v.get('masterstatus', {}).values():
                    status_list.append(m)

                if -1 in status_list:
                    return Result('error')
                else:
                    return Result('pending')

        Log(1, 'get_master_status[%s][%s] fail, as [the node not exist]' % (cluster_name, host_ip))
        return Result('', FAIL, 'the node not exist')

    def get_cluster_auth_info(self, cluster_name):
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_list except:{}, url:{}'.format(e, url), result=500)

        res = Response(r)
        if not res.success:
            res.log('LauncherClient.get_cluster_auth_info:{}'.format(cluster_name))
            return Result('', FAIL, res.message)
        data = res.json_data()
        if data.get('status') == 'running':

            info = data.get('info', "{}")
            info = json.loads(info)
            auth_info = {
                'auth_way': 'ca_auth',
                'auth_data': info.get('cacert', ''),
                'server': 'https://' + info.get('vip', '') + ":6443",
                'cert_data': info.get('apiclientcert', ''),
                'client_key': info.get('apiclientkey', ''),
                'cluster_name': cluster_name,
            }

            return Result(auth_info)
        elif data.get('status') == 'pending':
            return Result('', CLU_IS_PENDING, 'clu master is pending')
        else:
            return Result('', CLU_IS_ERROR, 'clu master is error')

    def get_node_list(self, cluster_name, timeout=1):
        """
        # 获取节点列表
        """
        url = self.laucher_url + '/%s/nodes' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_list except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_node_status(self, cluster_name, hosttype, host_ip):
        url = self.laucher_url + '/{}/{}s/{}'.format(cluster_name, hosttype, host_ip)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_status except:{}, url:{}'.format(e, url), result=500)

        res = Response(r)
        if not res.success:
            res.log('LauncherClient.get_node_status')
            return res
        data = res.json_data()
        return Result(data.get('status', ''))

    def get_host_name(self, cluster_name, host_type, node_ip):

        url = self.laucher_url + '/%s/%s/%s' % (cluster_name, host_type, node_ip)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_list except:{}'.format(e), result=500)

        res = Response(r)
        if not res.success:
            res.log('LauncherClient.get_host_name')
            return Result('', FAIL, res.message)

        data = res.json_data()
        host_name = data.get('hostname', '')
        if host_name:
            return Result(host_name)
        else:
            return Result('', 400, 'the hostname is:{}'.format(host_name))

    def get_host_info(self, cluster_name, host_type, host_ip):
        """
        # 获取节点信息
        """
        url = self.laucher_url + '/%s/%s/%s' % (cluster_name, host_type, host_ip)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_node_info(self, cluster_name, node_ip):
        """
        # 获取节点信息
        """
        url = self.laucher_url + '/%s/nodes/%s' % (cluster_name, node_ip)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def create_cluster(self, node_info):
        """
        # 创建集群
        """
        url = self.laucher_url + '/new'
        try:
            r = requests.post(url, json.dumps(node_info), headers={"content-type": "application/json"},
                              timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='create_cluster except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def load_cluster(self, clu_info):
        """
        纳管集群
        :param clu_info:
        :param timeout:
        :return:
        """
        url = self.laucher_url + '/load'
        try:
            r = requests.post(url, json.dumps(clu_info), headers={"content-type": "application/json"},
                              timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='create_node except:{}'.format(e), result=500, code=500)
        else:
            Log(3, "laod cluster url:{}, data:{}".format(url, json.dumps(clu_info)))
            return Response(r)

    def create_node(self, cluster_name, node_info):
        """       
        # 创建节点
        """
        url = self.laucher_url + '/%s/nodes/new' % (cluster_name)
        try:
            r = requests.post(url, json.dumps(node_info), headers={"content-type": "application/json"},
                              timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='create_node except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def delete_node(self, cluster_name, node_name):
        """        
        # 删除节点
        """
        url = self.laucher_url + '/%s/nodes/%s' % (cluster_name, node_name)
        try:
            r = requests.delete(url, timeout=15)
        except requests.exceptions.RequestException as e:
            return Result('', msg='delete_node except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)
