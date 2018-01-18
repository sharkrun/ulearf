# -*- coding: utf-8 -*-
'''
Created on 2017年6月5日

@author: Cloudsoar
'''

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import FAIL
from core.kubeclient import KubeClient
from core.launcherclient import LauncherClient
from frame.logger import Log


class KubeClientMgr(object):
    """
    保存集群客户端
    """
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.__store = {}
        self.expiry_time = 0

    def get_cluster_client(self, cluster_name):
        """
        获取单个集群的 apiserver client
        :param cluster_name:
        :return:
        """
        rlt = LauncherClient.instance().get_cluster_auth_info(cluster_name)
        if not rlt.success:
            return rlt
        # Log(4, "get_cluster_client auth_info:{}".format(rlt.content))
        client = KubeClient(rlt.content)
        con = client.connect()
        if con.success:
            return Result(client)
        else:
            Log(3, 'KubeClientMgr get_cluste_client [%s]fail, as[%s]' % (cluster_name, con.message))
            return Result('', 500, con.message)

    def get_api(self, cluster_name):
        rlt = LauncherClient.instance().get_cluster_auth_info(cluster_name)
        if not rlt.success:
            return rlt
        # Log(4, "get_cluster_client auth_info:{}".format(rlt.content))
        client = KubeClient(rlt.content)
        con = client.connect()
        if con.success:
            return Result(client.api)
        else:
            Log(3, 'KubeClientMgr get_cluste_client [%s]fail, as[%s]' % (cluster_name, con.message))
            return Result('', 500, con.message)

    def delete_cluster_node(self, cluster_name, node_name):
        """
        :param :
        :return:
        """
        rlt = self.get_cluster_client(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClientMgr.delete_cluster_node[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster_client  fail')
        client = rlt.content
        return client.delete_node(node_name)

    def all_pods(self, cluster_name):
        """
        :param cluster_name:
        :return:
        """
        try:
            pods_list = []
            rlt = self.get_cluster_client(cluster_name)
            if not rlt.success:
                Log(1, 'KubeClientMgr.all_pods[%s] fail,as[the cluster info invalid]' % (cluster_name))
                return Result('', FAIL, 'get cluster_client  fail')

            client = rlt.content
            rlt = client.get_all_pods()
            if not rlt.success:
                return rlt

            for pod in rlt.content:
                # conditions = pod.get('status', {}).get('conditions', [])
                # for k in conditions:
                    # if k.get('type', '') == 'Ready':
                    #     if k.get('status') == 'True':
                    #         pods_list.append(pod)
                    #     break
                    # pass
                if pod.get('status', {}).get('phase') == 'Running':
                    pods_list.append(pod)
            return Result(pods_list)
        except Exception as e:
            return Result('', 500, e.message)

    def node_ready_pods_num(self, cluster_name, ws_list):
        """
        获取某个主机上状态为ready的pods个数
        :param cluster_name:
        :return:
        """
        try:
            pod_num = 0
            rlt = self.get_cluster_client(cluster_name)
            if not rlt.success:
                Log(1, 'KubeClientMgr.all_pods[%s] fail,as[the cluster info invalid]' % (cluster_name))
                return Result('', FAIL, 'get cluster_client  fail')

            client = rlt.content
            rlt = client.get_node_pods()
            if not rlt.success:
                return rlt

            for pod in rlt.content:
                if pod.get('metadata', {}).get('namespace') in ws_list:
                    conditions = pod.get('status', {}).get('conditions', [])
                    for k in conditions:
                        if k.get('type', '') == 'Ready':
                            if k.get('status') == 'True':
                                pod_num += 1
                            break
            return Result(pod_num)
        except Exception as e:
            return Result('', 500, e.message)

    def get_host_pod_num(self, cluster_name, ns_list, host_ip):
        """
        """
        rlt = self.get_cluster_client(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster_client  fail')
        client = rlt.content
        return client.get_host_pod_num(ns_list, host_ip)

        # rlt = self.get_api(cluster_name)
        # if not rlt.success:
        #     Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
        #     return Result('', FAIL, 'get cluster_client  fail')
        # pods_num = 0
        # for ns in ns_list:
        #     pods = pykube.Pod.objects(rlt.content).filter(namespace=ns)
        #     ready_pods = filter(operator.attrgetter("ready"), pods)
        #     print 'ns:{}, ready_pods:{}, all_pods:{}'.format(ns, len(ready_pods), len(pods))
        #     pods_num += len(ready_pods)
        # return Result(pods_num)

    def get_host_pod_list(self, cluster_name, namespace, host_ip):
        """
        """
        rlt = self.get_cluster_client(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster_client  fail')

        arr = []
        client = rlt.content
        rlt = client.get_host_pod_list(namespace, host_ip)
        if rlt.success:
            arr.extend(rlt.content)
        else:
            Log(1,
                'KubeClientMgr.get_host_pod_list get_pod_list[%s][%s]fail,as[%s]' % (namespace, host_ip, rlt.message))

        return Result(arr)