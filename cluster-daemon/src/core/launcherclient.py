# -*- coding: utf-8 -*-
"""

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
            Log(3, '[%s] success, return [%s]' % (act, self.res.respond_body))
        else:
            Log(1, '[%s] fail, return [%s],massage[%s]' % (act, self.res.text, self.res.text))

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

    # def host_status_note(self, status):
    #     """
    #     # 主机状态注释
    #     :param kwargs:
    #     :return:
    #     """
    #     status_list = list(set(status.values()))
    #     reason = {'error_reason': []}
    #     if status.get('connectstatus', '') == -1:
    #         reason['error_reason'].append(u'连接主机失败')
    #     if status.get('existstatus', '') == -1:
    #         reason['error_reason'].append(u'主机名重复')
    #     if status.get('kubeletstatus', '') == -1:
    #         reason['error_reason'].append(u'目录挂载出错')
    #     if status_list == [1]:
    #         reason['error_reason'].append(u'连接中断')
    #     if status.get('initenvtstatus', '') == -1:
    #         reason['error_reason'].append('initenvtstatus -1')
    #     if status.get('transfilestatus', '') == -1:
    #         reason['error_reason'].append('transfilestatus -1')
    #     if status.get('certstatus', '') == -1:
    #         reason['error_reason'].append('certstatus -1')
    #     if status.get('configstatus', '') == -1:
    #         reason['error_reason'].append('configstatus -1')
    #     if status.get('imagestatus', '') == -1:
    #         reason['error_reason'].append(u'镜像拉取失败')
    #     if status.get('cnistatus', '') == -1:
    #         reason['error_reason'].append('cnistatus -1')
    #     if status.get('preflightstatus', '') == -1:
    #         reason['error_reason'].append(u'环境检查失败')
    #     if status.get('tokenstatus', '') == -1:
    #         reason['error_reason'].append(u'生成配文件失败')
    #     if status.get('apiserverstatus', '') == -1:
    #         reason['error_reason'].append(u'api认证失败')
    #     if status.get('masterapistatus', '') == -1:
    #         reason['error_reason'].append('masterapistatus -1')
    #     return reason

    def get_cluster_list(self, timeout=1):
        """
        # 取得集群列表
        """
        try:
            r = requests.get(self.laucher_url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_cluster_list except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_cluster_info(self, cluster_name, timeout=1):
        """
        rest.Get("/clusters", launcherapi.GetClusters),
        """
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_cluster_info except:{}'.format(e), result=500)
        else:
            if r.status_code == 200:
                return Result(r.json())
            else:
                return Result('', r.status_code, r.text)

    def delete_cluster(self, cluster_name, timeout=1):
        """
        # 删除集群
        """
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.delete(url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='delete_cluster except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)

    def get_master_list(self, cluster_name, timeout=1):
        """
        # 获取管理节点列表
        """
        url = self.laucher_url + '/%s/masters' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_list except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_master_info(self, cluster_name, master_name, timeout=1):
        """
        # 获取管理节点信息
        """
        url = self.laucher_url + '/%s/masters/%s' % (cluster_name, master_name)
        try:
            r = requests.get(url=url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def get_cluster_auth_info(self, cluster_name):
        url = self.laucher_url + '/%s' % (cluster_name)
        try:
            r = requests.get(url=url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_master_list except:{}'.format(e), result=500)

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
        if data.get('status') == 'running':
            return Result(data['hostname'])
        return Result('')

    def get_node_info(self, cluster_name, node_name, timeout=1):
        """
        # 获取节点信息
        """
        url = self.laucher_url + '/%s/nodes/%s' % (cluster_name, node_name)
        try:
            r = requests.get(url=url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_node_info except:{}'.format(e), result=500)
        else:
            return Response(r)

    def delete_node(self, cluster_name, node_name, timeout=1):
        """
        # 删除节点
        """
        url = self.laucher_url + '/%s/nodes/%s' % (cluster_name, node_name)
        try:
            r = requests.delete(url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return Result('', msg='delete_node except:{}'.format(e), result=500, code=500)
        else:
            return Response(r)
