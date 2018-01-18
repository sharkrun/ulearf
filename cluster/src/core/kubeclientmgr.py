# -*- coding: utf-8 -*-
'''
Created on 2017年6月5日

@author: Cloudsoar
'''

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import FAIL, LICENSE_OUT_OF_DATE
from core.kubeclient import KubeClient
from core.launcherclient import LauncherClient
from etcddb.kubernetes.clustermgr import Clusterdb
from frame.logger import Log
from core.errcode import CLUSTER_HAS_EXISTED, NODE_USED_BY_UFLEET
from etcddb.kubernetes.nodemgr import CluNodedb
from etcddb.kubernetes.mastermgr import Masterdb
from frame.configmgr import GetSysConfig
from common.datatype import clu_struct, auth_info_struct
from common.util import NowMilli
from etcddb.kubernetes.workspacemgr import WorkSpacedb
import datetime
import time
from common.datatype import node_struct
from common.datatype import masternode_struct
from core.errcode import CLU_IS_PENDING
from cadvisor import Cadvisor


def utc2local(utc_st):
    """UTC时间转本地时间（+8:00）"""
    now_stamp = time.time()
    local_time = datetime.datetime.fromtimestamp(now_stamp)
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st


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
        self.__authinfo = {}
        self.__pods = {}
        self.expiry_time = 0
        self.load_pod_time = 0
        self.loaddata()

    def reload(self, flush=0):
        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def loaddata(self):
        self.expiry_time = NowMilli() + 30000
        self.load_all_client()

    def load_all_client(self):
        """
        加载所有集群客户端
        :return:
        """
        # 获取有主机的集群名
        rlt = CluNodedb.instance().get_clu_node()
        # rlt = Clusterdb.instance().get_all_cluster_name()
        if not rlt.success:
            Log(1, "kubeclientmgr load_all_client error:{}".format(rlt.message))
            return
        for i in rlt.content.keys():
            self.load_cluster(i)

        Log(4, "load_all_client:{}".format(self.__store.keys()))

    def load_cluster(self, cluster_name):
        """
        加载单个集群client
        :param cluster_name:
        :return:
        """
        rlt = LauncherClient.instance().get_cluster_auth_info(cluster_name)
        if not rlt.success:
            if rlt.result == CLU_IS_PENDING:
                return Result('', CLU_IS_PENDING, 'clu master is pending')
            Log(1, 'KubeClientMgr.load_cluster read_cluster_auth_info[%s]fail,as[%s]' % (cluster_name, rlt.message))
            return rlt
        Log(4, "load_cluster, cluster_name:{}".format(cluster_name))
        return self.add_cluster_client(cluster_name, rlt.content)

    def load_clu_pods(self, clu_name, host_name, pods_list):
        """
        :param clu_name:
        :param pods_list:
        :return:
        """
        # if self.load_pod_time <= NowMilli():
        self.load_pod_time = NowMilli() + 30000
        self.__pods.setdefault(clu_name, {}).update({host_name: pods_list})

    def get_pods_load(self, clu_name, host_name):
        Log(3, "pods:{}".format(self.__pods))
        if self.load_pod_time <= NowMilli():
            rlt = self.get_host_all_pods(clu_name, host_name)
            if not rlt.success:
                return rlt
            self.load_clu_pods(clu_name, host_name, rlt.content)
            return Result(rlt.content)
        else:
            pods = self.__pods.get(clu_name, {}).get(host_name)
            Log(3, "get_pods_load:{}".format(pods))
            if not pods:
                rlt = self.get_host_all_pods(clu_name, host_name)
                if not rlt.success:
                    return rlt
                self.load_clu_pods(clu_name, host_name, rlt.content)
                return Result(rlt.content)
            return Result(pods)

    def get_current_client(self, cluster_name):
        """
        实时从launcher获取 apiserver client
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

    def get_cluster_client(self, cluster_name):
        """
        获取单个集群的 apiserver client
        :param cluster_name:
        :return:
        """
        self.reload()
        if cluster_name in self.__store:
            return self.__store[cluster_name]
        rlt = self.load_cluster(cluster_name)
        if rlt.success:
            return rlt.content
        Log(3, "get_cluster_client fail:{}".format(rlt.message))
        return None

    def read_cluster_auth_info(self, cluster_name):
        """
        获取集群的认证信息
        :param cluster_name:
        :return:
        """
        self.reload()
        rlt = self.__authinfo.get(cluster_name)
        if not rlt:
            return Result('', 404, 'not found auth info')
        return Result(rlt)

    def add_cluster_client(self, cluster_name, auth_info):
        """
        把集群客户端存到内存self__store中
        :param cluster_name:
        :param auth_info:
        :return:
        """
        client = KubeClient(auth_info)
        rlt = client.connect()
        if rlt.success:
            # 添加到缓存中
            self.__authinfo[cluster_name] = auth_info
            self.__store[cluster_name] = client
            return Result(client)
        else:
            Log(3, 'KubeClientMgr.add_cluster[%s]fail, as[%s]' % (cluster_name, rlt.message))
            return rlt

    def syn_nodeinfo(self, node_one, j, clu_gws):
        """
        :param node_one: {}
        :param j: {}
        :return:{'node_one': dic, 'change_num': int}
        """
        # 主机内存
        node_one['name'] = j.get('metadata', {}).get('name', '')

        # 主机cpu
        node_one['cpu'] = j.get('status', {}).get('capacity', {}).get('cpu', '')

        # 主机添加时间
        t1 = j.get('metadata', {}).get('creationTimestamp', '')
        t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
        t3 = utc2local(t2)
        node_one['datetime'] = datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")

        # 主机内存
        node_one['memory'] = str(
            round(float(j.get('status', {}).get('capacity', {}).get('memory', '')[:-2]) / (1024 * 1024),
                  3)) + 'GB'

        # 主机状态
        docker_version = j.get('status', {}).get('nodeInfo', {}).get(
            'containerRuntimeVersion', '')
        node_one['docker_version'] = docker_version
        node_one['unschedulable'] = j.get('spec', {}).get('unschedulable', '')

        status = ''
        conditions = j.get('status', {}).get('conditions', [])
        for k in conditions:
            if k.get('type', {}) == 'Ready':
                status1 = k.get('status', '')
                if status1 == 'True':
                    status = 'running'
                else:
                    status = 'error'
                break
        node_one['status'] = status

        # 主机标签
        labels = j.get('metadata', {}).get('labels', {})
        l_key = labels.keys()
        if 'kubernetes.io/hostname' in l_key:
            del labels['kubernetes.io/hostname']
        if 'beta.kubernetes.io/os' in l_key:
            del labels['beta.kubernetes.io/os']
        if 'beta.kubernetes.io/arch' in l_key:
            del labels['beta.kubernetes.io/arch']
        node_one['label'] = labels

        # pod个数
        ns_list = []
        for i in clu_gws:
            ns_list += i['workspace']
        pods_num = 0

        for k in ns_list:
            p = KubeClientMgr.instance().get_host_pod_list(node_one['cluster_name'], k, node_one['name'])
            # p = get_one_pod(api, k, node_one['name'])
            pods_num += len(p.content)
        node_one['pod_num'] = pods_num

        # 磁盘信息
        cadvisor_cli = Cadvisor(node_one['ip'], '/api/v1.3/machine')
        rlt = cadvisor_cli.get()
        if rlt.success:
            filesystems = rlt.content.get('filesystems', [])
            disk_num = 0
            for f in filesystems:
                disk_num += f.get('capacity', 0)
            node_one['disk'] = str(round(disk_num / (1024 ** 3), 3)) + 'GB'
        else:
            Log(1, "add cluster syn_nodeinfo get data from cadvisor error:{}, node:{}".format(rlt.message, node_one['ip']))
        return node_one

    def create_new_cluster(self, cluster_info, passport):
        """
        创建集群
        :param creater:
        :param cluster_info:
        :return:
        """
        master_ip = cluster_info.get('addr', '').split(':')[0]
        host_name = master_ip.replace('.', '-')

        # 检查license
        if not passport.get('licensed', ''):
            return Result('', LICENSE_OUT_OF_DATE, 'licensed is out of date', 400)

        # check集群是否存在
        cluster_name = cluster_info.get('cluster_name', '')
        if Clusterdb.instance().clu_is_exist(cluster_name):
            return Result(0, CLUSTER_HAS_EXISTED, 'clu is existed', 400)

        masternode_list = []
        nodemonitor_list = []
        clunode_list = []
        if cluster_info.get('create_way', '') == 'add':
            # check 集群ip是否添加过
            if CluNodedb.instance().is_node_exist(cluster_name, host_name):
                return Result(0, msg='', result=CLUSTER_HAS_EXISTED, code=400)

            # 检查是否是ufleet主机
            ufleet_hosts = GetSysConfig('ufleet_hosts').split(',')
            if master_ip in ufleet_hosts:
                return Result('', msg='the host is used by ufleet.', result=NODE_USED_BY_UFLEET, code=400)

            client = KubeClient({'auth_data': cluster_info.get('cacerts', ''),
                                 'server': 'https://' + cluster_info.get('addr', ''),
                                 'cert_data': cluster_info.get('apiservercerts'),
                                 'client_key': cluster_info.get('apiserverkey'),
                                 'cluser_name': cluster_name})
            rlt = client.connect()
            if not rlt.success:
                Log(3, 'KubeClientMgr.add_cluster[%s]fail, as[%s]' % (cluster_name, rlt.message))
                return rlt
            self.__store[cluster_name] = client

            rlt = client.get_all_nodes()
            if not rlt.success:
                return rlt

            for j in rlt.content:
                address = j.get('status', {}).get('addresses', [])
                for add in address:
                    if 'InternalIP' == add.get('type', ''):
                        ip = add.get('address')
                        if ip == cluster_info.get('addr', '').split(':')[0]:
                            host_type = 'master'
                        else:
                            host_type = 'node'
                        ip_name = ip.replace('.', '-')

                        node_data = node_struct(cluster_name, add.get('address'), host_type,
                                                cluster_info.get('creater'))
                        node_data = self.syn_nodeinfo(node_data, j, [])

                        # clusternode
                        clunode_list.append({'cluster_name': cluster_name, 'data': node_data})

                        # masternodedir
                        masternode_data = masternode_struct(cluster_info.get('creater'), cluster_name, host_type,
                                                            add.get('address', ''),
                                                            '', '', '', '', '', '')
                        masternode_list.append({'master_ip': ip_name, 'data': masternode_data})

                        # nodemonitor
                        nodemonitor_list.append(ip_name)

            # 调用launcher保存集群认证信息接口
            auth_data = auth_info_struct(cluster_info)
            rlt = LauncherClient.instance().load_cluster(auth_data)
            if not rlt.success:
                return Result('', 500, 'load_cluster error:' + rlt.message, 500)

        # 保存数据到etcd
        new_clu = clu_struct(cluster_info)
        rlt = Clusterdb.instance().create_cluster_full(cluster_name, new_clu)
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 400)

        for i in clunode_list:
            rlt = CluNodedb.instance().save_node(i['cluster_name'], i['data'])
            if not rlt.success:
                return rlt

        for i in masternode_list:
            rlt = Masterdb.instance().save_master(i['master_ip'], i['data'])
            if not rlt.success:
                return rlt

        return Result('')

    def get_cluster_nodes(self, cluster_name):
        """
        # 通过api获取添加成功的主机
        :param :
        :return:
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.get_cluster_nodes[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        return client.get_all_nodes()

    def delete_cluster_node(self, cluster_name, node_name):
        """
        :param :
        :return:
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.delete_cluster_node[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        return client.delete_node(node_name)

    def create_cluster_namespace(self, cluster_name, namespace, config):
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.create_namespace[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster_client fail')

        # rlt = client.delete_namespace(namespace)
        # if not rlt.success:
        #     Log(4, 'create_namespace delete_namespace[%s]fail,as[%s]' % (namespace, rlt.message))

        return client.create_full_namespace(namespace, config)

    def delete_cluster_namespace(self, cluster_name, namespace):
        """
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.delete_cluster_node[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        return client.delete_namespace(namespace)

    def update_cluster_namespace(self, cluster_name, namespace, config):
        """
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.delete_cluster_node[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        return client.update_namespace(namespace, config)

    def get_host_pod_list(self, cluster_name, namespace, host_name):
        """
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        arr = []
        rlt = client.get_host_pod_list(namespace, host_name)
        if rlt.success:
            arr.extend(rlt.content)
        else:
            Log(1,
                'KubeClientMgr.get_host_pod_list get_pod_list[%s][%s]fail,as[%s]' % (namespace, host_name, rlt.message))

        return Result(arr)

    def get_pause_id(self, host_ip, container_id):
        """
        获取pod的pause容器id
        通过cadvisor获取pause容器id
        :param hostip:
        :param container_id:
        :return:
        """
        cadvisor_cli = Cadvisor(host_ip)
        rlt = cadvisor_cli.get(container_id)
        if not rlt.success:
            return rlt
        pause_id = rlt.content.values()[0].get('labels', {}).get('io.kubernetes.sandbox.id', '')
        return Result({'pause_id': pause_id})

    def get_host_all_pods(self, cluster_name, host_name):
        """
        # 获取主机上的pods
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')
        rlt = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClientMgr.get_host_pod_list get_ns_by_cluster[%s] fail,as[%s]' % (cluster_name, rlt.message))
            return rlt
        namespace_list = rlt.content
        ns_name_list = []
        for ns in namespace_list:
            ns_name_list.append(ns.get('name'))
        rlt = client.get_host_pods(ns_name_list, host_name)
        if not rlt.success:
            return Result('', 400, rlt.message, 400)
        host_pods = rlt.content

        return Result(host_pods)

    def get_all_pods(self, cluster_name):
        """
        # 获取主机上的pod
        """
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.get_all_pods[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        rlt = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClientMgr.get_host_pod_list get_ns_by_cluster[%s] fail,as[%s]' % (cluster_name, rlt.message))
            return rlt

        arr = []
        namespace_list = rlt.content
        for ns in namespace_list:
            namespace = ns.get('name')
            if not namespace:
                Log(1, 'KubeClientMgr.get_host_pod_list get_pod_list skip,as[name space invalid]')
                continue

            rlt = client.get_pod_list(ns['name'])
            if rlt.success:
                arr.extend(rlt.content)
            else:
                Log(1, 'KubeClientMgr.get_host_pod_list get_pod_list[%s]fail,as[%s]' % (ns['name'], rlt.message))

        return Result(arr)

    def get_k8s_pod_set(self, cluster_name, namespace):
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.get_host_pod_list[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster client fail')

        rlt = client.get_pod_set(namespace)
        if not rlt.success:
            Log(1, 'KubeClientMgr.get_host_pod_list get_pod_set[%s]fail,as[%s]' % (namespace, rlt.message))

        return rlt

    def get_namespace_configmaps(self, namespace):
        """
        获取某个namespace下所有的configmap设置
        :param cluster_name:
        :param namespace:
        :return:
        """
        rlt = WorkSpacedb.instance().read_workspace(namespace)
        if not rlt.success:
            return rlt
        clu_name = rlt.content.get('cluster_name')
        client = self.get_cluster_client(clu_name)
        if client is None:
            return Result('', FAIL, 'get cluster client fail')

        return client.get_configmaps(namespace)

    def delete_configmap(self, namespace, configmap):
        rlt = WorkSpacedb.instance().read_workspace(namespace)
        if not rlt.success:
            return rlt
        clu_name = rlt.content.get('cluster_name')
        client = self.get_cluster_client(clu_name)
        if client is None:
            return Result('', FAIL, 'get cluster client fail')
        return client.delete_configmap(namespace, configmap)

    def create_configmap(self, namespace, data):
        rlt = WorkSpacedb.instance().read_workspace(namespace)
        if not rlt.success:
            return rlt
        clu_name = rlt.content.get('cluster_name')
        client = self.get_cluster_client(clu_name)
        if client is None:
            return Result('', FAIL, 'get cluster client fail')
        return client.create_configmaps(namespace, data)

    def create_clusterrole(self, cluster_name, name, data):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.create_clusterroles(data)

    def list_clusterrole(self, cluster_name):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.clusterroles()

    def delete_clusterrole(self, cluster_name, name):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.del_clusterroles(name)

    def create_clusterrolebinding(self, cluster_name, name, data):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.create_clusterrolebinding(data)

    def list_clusterrolebinding(self, cluster_name):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.clusterrolebinding()

    def delete_clusterrolebinding(self, cluster_name, name):
        client = self.get_cluster_client(cluster_name)
        if not client:
            return Result('', FAIL, 'get cluster client fail')
        return client.del_clusterrolebinding(name)

    def test_cluster_connect(self, cluster_name, url):
        client = self.get_cluster_client(cluster_name)
        if client is None:
            Log(1, 'KubeClientMgr.test_cluster_connect[%s] fail,as[the cluster info invalid]' % (cluster_name))
            return Result('', FAIL, 'get cluster info fail')

        return client.test(url)
