# -*- coding: utf-8 -*-

"""

"""
import json
import threading
import requests
from common.guard import LockGuard
from common.util import Result
from core.errcode import FAIL
from frame.configmgr import GetSysConfig
from frame.logger import Log
from common.decorators import requestexcept


class DeployClient(object):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        host = GetSysConfig('apply_info_host')
        port = GetSysConfig('apply_info_port')
        self.timeout = 5
        self.deploy_url = 'http://%s:%s/v1/deploy' % (host, port)

    def get_apply_num(self, cluster_name, gws, timeout=2):
        """
        # 获取一个集群上的应用个数
        """
        query_param = {
            "clusterwgs": [{
                "cluster": cluster_name,
                "gws": gws
            }]
        }
        url = self.deploy_url + '/app/apps/cluster'
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        try:
            r = requests.post(url, json.dumps(query_param), timeout=timeout, headers=headers)
        except requests.exceptions.RequestException as e:
            return Result('', msg='get_apply_num except:{}'.format(e), result=500)
        else:
            if r.status_code == 200:
                data = r.json()
                return Result(data.get(cluster_name, 0))
            else:
                print json.dumps(query_param)
                return Result(0, FAIL, r.text)

    def get_threshold(self, service, group, namespace):
        """
        # 获取service的阈值
        :return:
        """
        url = self.deploy_url + '/deployment/%s/group/%s/workspace/%s/hpa' % (service, group, namespace)
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        try:
            r = requests.get(url, timeout=self.timeout, headers=headers)
        except requests.exceptions.RequestException as e:
            Log(1, 'get_threshold except:{}'.format(e))
            return None
        else:
            if r.status_code == 200:
                return r.json()
            else:
                return None

    @requestexcept
    def get_clusterrole(self, cluster_name, name=None):
        if name:
            url = "%s/clusterrole/%s/cluster/%s" % (self.deploy_url, name, cluster_name)
        else:
            url = "%s/clusterrole/cluster/%s" % (self.deploy_url, cluster_name)
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        r = requests.get(url, timeout=self.timeout, headers=headers)
        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, "request {} error:{}".format(url, r.text))
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def del_clusterrole(self, name, cluster_name):
        url = "%s/clusterrole/%s/cluster/%s" % (self.deploy_url, name, cluster_name)
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        r = requests.delete(url, timeout=self.timeout, headers=headers)
        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, "request {} error:{}".format(url, r.text))
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def get_clusterrolebinding(self, cluster_name, name=None):
        if name:
            url = "%s/clusterrolebinding/%s/cluster/%s" % (self.deploy_url, name, cluster_name)
        else:
            url = "%s/clusterrolebinding/cluster/%s" % (self.deploy_url, cluster_name)
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        r = requests.get(url, timeout=self.timeout, headers=headers)
        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, "request {} error:{}".format(url, r.text))
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def del_clusterrolebinding(self, name, cluster_name):
        url = "%s/clusterrolebinding/%s/cluster/%s" % (self.deploy_url, name, cluster_name)
        headers = {"content-type": "application/json", "token": "1234567890987654321"}
        r = requests.delete(url, timeout=self.timeout, headers=headers)
        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, "request {} error:{}".format(url, r.text))
            return Result('', r.status_code, r.text, r.status_code)