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
        self.timeout = 10
        self.deploy_url = 'http://%s:%s/v1/deploy' % (host, port)
        self.headers = {"content-type": "application/json", "token": "1234567890987654321"}

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
        try:
            r = requests.post(url, json.dumps(query_param), timeout=timeout, headers=self.headers)

        except requests.exceptions.RequestException as e:
            return Result('', msg='get_apply_num except:{}'.format(e), result=500)

        else:
            if r.status_code == 200:
                data = r.json()
                return Result(data.get(cluster_name, 0))
            else:
                Log(3, "get_apply_num error status_code:{}, url:{}, data:{}".format(r.status_code, url, query_param))
                return Result(0, FAIL, r.text)

    def get_threshold(self, service, group, namespace):
        """
        # 获取service的阈值
        :return:
        """
        url = self.deploy_url + '/deployment/%s/group/%s/workspace/%s/hpa' % (service, group, namespace)
        try:
            r = requests.get(url, timeout=self.timeout, headers=self.headers)
        except requests.exceptions.RequestException as e:
            Log(1, 'get_threshold except:{}'.format(e))
            return None
        else:
            if r.status_code == 200:
                return r.json()
            else:
                Log(4, "deployclient get threshold error. code:{}, url:{}, return_data:{}".format(r.status_code, url, r.text))
                return None

    def service_up(self, service, group, workspace, replicas):
        """
        # 扩容缩容
        # 当replicas为正则扩容，反之为缩容
        replicas:副本数目
        """

        url = self.deploy_url + '/deployment/%s/group/%s/workspace/%s/increment/%s' % (
            service, group, workspace, replicas)
        try:
            r = requests.put(url, timeout=self.timeout, headers=self.headers)
        except requests.exceptions.RequestException as e:
            Log(1, 'service_up except:{}'.format(e))
            return None
        else:
            if r.status_code == 200:
                return True
            else:
                Log(1, "service up error. url:{}, response:{}".format(url, r.text))
                return None

    def all_deploy(self):
        """
        设置了弹性伸缩的deployment
        :return:
        """
        url = self.deploy_url + '/deployment/allgroup/hpas'
        try:
            r = requests.get(url, timeout=self.timeout, headers=self.headers)
        except requests.exceptions.RequestException as e:
            Log(1, 'get request from deployment error:{}'.format(e.message))
            return None
        except Exception as e:
            Log(1, "get all_deploy Exception:{}".format(e.message))
            return None
        else:
            if r.status_code == 200:
                return r.json()
            else:
                Log(1, "get all_deploy error. url:{}, response:{}".format(url, r.text))
                return None
