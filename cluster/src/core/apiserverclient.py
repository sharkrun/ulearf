# -*- coding: utf-8 -*-
import pykube
import threading
from common.guard import LockGuard
from frame.logger import Log
import base64
from common.util import Result
import requests


class MyRequest(object):
    def __init__(self, server):
        self.server = server

    def request(self, method, url, data=None, headers=None, timeout=1):
        if method == 'GET':
            url = self.server + '/api/v1' + url
            r = requests.get(url=url, timeout=timeout)
            return r
        if method == 'PATCH':
            url = self.server + '/api/v1' + url
            r = requests.patch(url=url, data=data, headers=headers, timeout=timeout)
            return r
        if method == 'PUT':
            url = self.server + '/api/v1' + url
            r = requests.put(url=url, data=data, headers=headers, timeout=timeout)
            return r
        if method == 'DELETE':
            url = self.server + '/api/v1' + url
            r = requests.delete(url=url, data=data, headers=headers, timeout=timeout)
            return r


class ClusterConnect(object):
    """
    连接集群
    """
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def ca_auth(self, auth_data, server, cert_data, client_key, auth_way='ca_auth'):
        """
        ca认证
        :param cluster_name:
        :param auth_data:
        :param server:
        :param user_name:
        :param cert_data:
        :param client_key:
        :param context_name:
        :return:
        """
        config = {
            "clusters": [
                {
                    "name": "self",
                    "cluster": {
                        "certificate-authority-data": "",
                        "server": ""
                    }
                }
            ],
            "users": [
                {
                    "name": "self",
                    "user": {
                        "client-certificate-data": "",
                        "client-key-data": "",
                    }
                }
            ],
            "contexts": [
                {
                    "name": "self",
                    "context": {
                        "cluster": "self",
                        "user": "self"
                    }
                }
            ],
            "current-context": "self"
        }
        if auth_way == 'http':
            api = MyRequest(server)
            Log(3, "http11:{}".format(api))
            return Result(api)
        else:
            config['clusters'][0]['cluster']['certificate-authority-data'] = base64.b64encode(auth_data)
            config['clusters'][0]['cluster']['server'] = server
            config['users'][0]['user']['client-certificate-data'] = base64.b64encode(cert_data)
            config['users'][0]['user']['client-key-data'] = base64.b64encode(client_key)
        # try:
        api = pykube.HTTPClient(pykube.KubeConfig(doc=config))
        return Result(api)

