# -*- coding: utf-8 -*-
'''
Created on 2017年6月5日

@author: Cloudsoar
'''
import base64
import datetime
import json
import random

import pykube
from twisted.web import http

from common.util import Result, utc2local
from core.deployclient import DeployClient
from core.errcode import CALL_KUBE_INSTERFACE_FAIL_ERROR, \
    CALL_KUBE_INSTERFACE_EXCEPT_ERROR
from core.node import Node
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from frame.logger import Log
from frame.logger import PrintStack
import copy
from common.decorators import requestexcept


class KubeClient(object):
    def __init__(self, auth_info):
        self.auth_data = auth_info.get('auth_data')
        self.server = auth_info.get('server')
        self.cert_data = auth_info.get('cert_data')
        self.client_key = auth_info.get('client_key')
        self.cluster_name = auth_info.get('cluster_name')
        self.timeout = 10

    @property
    def api(self):
        return self.client

    def connect(self):
        """
        # 测试连接
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
        config['clusters'][0]['cluster']['certificate-authority-data'] = base64.b64encode(self.auth_data)
        config['clusters'][0]['cluster']['server'] = self.server
        config['users'][0]['user']['client-certificate-data'] = base64.b64encode(self.cert_data)
        config['users'][0]['user']['client-key-data'] = base64.b64encode(self.client_key)

        api = pykube.HTTPClient(pykube.KubeConfig(doc=config))
        try:
            response = api.request(method='GET', url='', timeout=2)
        except pykube.PyKubeError as e:
            Log(1, 'server:{},ssl error:{}'.format(self.server, e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR,
                          'KubeClient connect to server:{} fail,ssl error:{}'.format(self.server, e))
        except Exception, e:
            Log(1, 'server:{},ssl error:{}'.format(self.server, e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR,
                          'KubeClient connect to server:{} except,ssl error:{}'.format(self.server, e))

        if response.status_code == 200:
            self.client = api
            return Result('ok')
        else:
            Log(1, msg='server:{} ssl error. text:{}'.format(self.server, response.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, response.text)

    def create_ns_obj(self, workspace_name):
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": workspace_name
            }
        }

    def create_rsquto_obj(self, workspace_name, data):
        return {
            "kind": "ResourceQuota",
            "apiVersion": "v1",
            "metadata": {
                "name": workspace_name + "-resource",
                "namespace": workspace_name,
                "clusterName": self.cluster_name
            },
            "spec": {
                "hard":
                    {
                        "requests.cpu": str(data.get('resource_cpu')),
                        "requests.memory": str(data.get('resource_mem')) + 'Gi'
                    }
            }
        }

    def create_limit_obj(self, workspace_name, data):
        """
        LimitRnge针对容器的资源限制
        :param workspace_name:
        :param data:
        :return:
        """
        return {
            "kind": "LimitRange",
            "apiVersion": "v1",
            "metadata": {
                "name": workspace_name + '-limit',
                "namespace": workspace_name,
                "clusterName": self.cluster_name
            },
            "spec": {
                "limits": [
                    {
                        "type": "Pod",
                        "max": {"cpu": data.get('pod_cpu_max'), "memory": str(data.get('pod_mem_max')) + 'Mi'},
                        "min": {"cpu": data.get('pod_cpu_min'), "memory": str(data.get('pod_mem_min')) + 'Mi'},
                        # "default": {"cpu": resource_cpu, "memory": str(resource_mem) + 'Gi'},
                        # "defaultRequest": {"cpu": str(min_cpu), "memory": str(min_mem) + 'Mi'},
                        # "maxLimitRequestRatio":{"cpu": 5, "memory": 4},
                    },
                    {
                        "type": "Container",
                        "default": {"cpu": data.get('c_cpu_default'), "memory": str(data.get('c_mem_default')) + 'Mi'},
                        # Default Limit
                        "defaultRequest": {"cpu": data.get('c_cpu_default_min'),
                                           "memory": str(data.get('c_mem_default_min')) + 'Mi'},
                        "min": {"cpu": data.get('c_cpu_min'), "memory": str(data.get('c_mem_min')) + 'Mi'},
                        "max": {"cpu": data.get('c_cpu_max'), "memory": str(data.get('c_mem_max')) + 'Mi'}
                    }
                ]
            }
        }

    def test(self, url):
        r = self.client.request(method='GET', url=url, timeout=self.timeout)
        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        return Result('')

    def create_full_namespace(self, namespace, config):

        # 先执行一次删除
        rlt = self.delete_namespace(namespace)
        if not rlt.success:
            return rlt

        rlt = self.create_namespace(namespace)
        if not rlt.success:
            Log(1, 'create_full_namespace.create_namespace fail,as[%s]' % (rlt.message))
            return rlt

        rlt = self.set_namespace_resouce(namespace, config)
        if not rlt.success:
            Log(1, 'create_full_namespace.set_namespace_resouce fail,as[%s]' % (rlt.message))
            self.delete_namespace(namespace)
            return rlt

        rlt = self.set_namespace_limit(namespace, config)
        if not rlt.success:
            Log(1, 'create_full_namespace.set_namespace_resouce fail,as[%s]' % (rlt.message))
            self.delete_namespace(namespace)
            return rlt

        return Result('ok')

    def create_namespace(self, namespace):
        url = 'namespaces'

        data = self.create_ns_obj(namespace)
        try:
            r = self.client.request(method='POST', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'create_namespace except{}'.format(e))
            return Result('', msg='create_namespace except{}'.format(e), result=400)

        if r.status_code == 201:
            return Result(r.json())
        else:
            Log(1, 'create_namespace[%s]fail,as[%s], status_code:[%s]' % (namespace, r.text, r.status_code))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def set_namespace_resouce(self, namespace, config):
        url = 'namespaces/%s/resourcequotas' % (namespace)

        data = self.create_rsquto_obj(namespace, config)
        Log(4, "set_namespace_resouse data :{}".format(data))
        try:
            r = self.client.request(method='POST', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'set_namespace_resouce except{}'.format(e))
            return Result('', msg='set_namespace_resouce except{}'.format(e), result=400)

        if r.status_code == 201:
            return Result(r.json())
        else:
            Log(1, 'set_namespace_resouce[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def set_namespace_limit(self, namespace, config):
        url = 'namespaces/%s/limitranges' % (namespace)

        data = self.create_limit_obj(namespace, config)
        try:
            r = self.client.request(method='POST', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'set_namespace_limit except{}'.format(e))
            return Result('', msg='set_namespace_limit except{}'.format(e), result=400)

        if r.status_code == 201:
            return Result(r.json())
        else:
            Log(1, 'set_namespace_limit[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_namespaces(self):
        url = 'namespaces'
        r = self.client.request(method='GET', url=url, timeout=self.timeout)
        if r.status_code != 200:
            return []

        name_list = []
        namespaces = r.json()
        items = namespaces.get('items', [])
        if items:
            for i in items:
                name = i.get('metadata', {}).get('name', '')
                if name != 'ufleet' and name != 'kube-system':
                    name_list.append(name)

        return name_list

    def get_namespace_resource(self, namespace):
        url = 'namespaces/%s/resourcequotas/%s-resource' % (namespace, namespace)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_namespace_resource except{}'.format(e))
            return Result('', msg='get_namespace_resource except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'get_namespace_resource[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def update_namespace(self, namespace, config):
        # ns_list = self.get_namespaces()
        # if namespace not in ns_list:
        #     Log(1, 'update_namespace update namespace[%s] fail,as [The namespace not exist.]' % (namespace))
        #     return Result('', FAIL, 'The namespace not exist.')

        rlt = self.get_namespace_resource(namespace)
        if not rlt.success:
            Log(1, 'update_namespace get_namespace_resource[%s] fail,as[%s]' % (namespace, rlt.message))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, 'read namespace resource fail.')

        old_cfg = rlt.content

        rlt = self.update_namespace_resource(namespace, config)
        if not rlt.success:
            Log(1, 'update_namespace update namespace resource[%s] fail,as [%s]' % (namespace, rlt.message))
            return rlt

        rlt = self.update_namespace_limit(namespace, config)
        if not rlt.success:
            Log(1, 'update_namespace update namespace limit[%s] fail,as [%s]' % (namespace, rlt.message))
            self.update_namespace_resource(namespace, old_cfg)
            return rlt

        return Result('ok')

    def update_namespace_resource(self, namespace, config):
        url = 'namespaces/%s/resourcequotas/%s-resource' % (namespace, namespace)

        data = self.create_rsquto_obj(namespace, config)

        try:
            r = self.client.request(method='PUT', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'update_namespace_resource except{}'.format(e))
            return Result('', msg='update_namespace_resource except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'update_namespace_resource[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def update_namespace_limit(self, namespace, config):
        url = 'namespaces/%s/limitranges/%s-limit' % (namespace, namespace)

        data = self.create_limit_obj(namespace, config)
        try:
            r = self.client.request(method='PUT', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'update_namespace_limit except{}'.format(e))
            return Result('', msg='update_namespace_limit except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'update_namespace_limit[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def delete_namespace(self, namespace):
        url = 'namespaces/' + namespace
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'delete_namespace except{}'.format(e))
            return Result('', msg='delete_namespace except{}'.format(e), result=400)

        if r.status_code == 200 or r.status_code == 404:
            Log(3, "delete_namespace:{}, status_code:{}".format(namespace, r.status_code))
            return Result('')
        else:
            Log(1, 'delete_namespace[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_pod_list(self, namespace):
        rlt = self.get_pods(namespace)
        if not rlt.success:
            return rlt

        pod_list = rlt.content

        rlt = WorkSpacedb.instance().read_workspace(namespace)
        if rlt.success:
            group = rlt.content.get('group')
        else:
            Log(1, 'get_host_pod_list get_namespace_info[%s][%s] fail,as[%s]' % (
                self.cluster_name, namespace, rlt.message))
            group = '-'

        arr = []
        for pod in pod_list:
            info = self.parse_pod_info(pod)
            info['namespace'] = namespace
            info['group_name'] = group
            arr.append(info)

        return Result(arr)

    def get_pods(self, namespace):
        url = 'namespaces/{}/pods'.format(namespace)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_pods except{}'.format(e))
            return Result('', msg='get_pods except{}'.format(e), result=400)

        # Log(4, 'kubeclient get_pods return [{}]'.format(r.text))

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_pod(self, namespace, name):
        """
        # 删除 deployment
        """
        url = 'namespaces/{}/pods/{}'.format(namespace, name)
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'delete pod except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'delete pod except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient delete pod return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def host_all_pods(self, host_name):
        """
        all pods of host_name
        :param host_name:
        :return:
        """
        url = 'proxy/nodes/{}/pods'.format(host_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(3, 'get_pod_list except{}'.format(e))
            return Result('', msg='get_pod_list except{}'.format(e), result=400)
        if r.status_code == 200:
            return Result(r.json())
        return Result('', 400, r.text, r.status_code)

    def get_host_pods(self, ns_list, hostname):
        """
        # 获取一个主机上的所有pod
        :param ns_list:
        :param hostname:
        :return:
        """
        rlt = self.host_all_pods(hostname)
        if not rlt.success:
            return rlt

        r_pods = []
        for pod in rlt.content.get('items', []):
            if pod.get('metadata', {}).get('namespace') in ns_list:
                info = self.parse_pod_info(pod)
                if info['status'] == 'error':
                    continue
                info['namespace'] = pod.get('metadata', {}).get('namespace')
                rlt = WorkSpacedb.instance().read_workspace(info['namespace'])
                if rlt.success:
                    group = rlt.content.get('group')
                else:
                    Log(1, "read_workspace error:{}".format(rlt.message))
                    group = '-'
                info['group_name'] = group
                # if info['status'] == 'running':
                r_pods.append(info)
        return Result(r_pods)

    def get_host_pod_list(self, namespace, hostname):
        url = 'namespaces/%s/pods' % (namespace)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_pod_list except{}'.format(e))
            return Result('', msg='get_pod_list except{}'.format(e), result=400)

        rlt = WorkSpacedb.instance().read_workspace(namespace)
        if rlt.success:
            group = rlt.content.get('group')
        else:
            Log(1, 'get_host_pod_list get_namespace_info[%s][%s] fail,as[%s]' % (
                self.cluster_name, namespace, rlt.message))
            group = '-'

        arr = []
        if r.status_code == 200:
            data = r.json()
            Log(3, "88888:{}".format(data))
            pod_list = data.get('items', [])
            for pod in pod_list:
                if pod.get('spec', {}).get('nodeName') == hostname:
                    info = self.parse_pod_info(pod)
                    info['namespace'] = namespace
                    info['group_name'] = group
                    if info['status'] == 'running':
                        arr.append(info)

            return Result(arr)
        else:
            Log(1, 'get_pod_list[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def parse_pod_info(self, pod):
        p = {'name': pod.get('metadata', {}).get('name', ''),
             'status': '',
             'apply': pod.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.app', ''),
             # 'service': pod.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.service', ''),
             'date': '',
             'container': pod.get('status', {}).get('containerStatuses', []),
             'pod_uid': pod.get('metadata', {}).get('uid', '')
             }
        # Log(4, "syndata get_one_pod:{}".format(pod.get('status', {})))
        t1 = pod.get('status', {}).get('startTime', '')
        if t1:
            t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
            t3 = utc2local(t2)
            p['date'] = datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")

        conditions = pod.get('status', {}).get('conditions', [])
        for k in conditions:
            if k.get('type', '') == 'Ready':
                p['status'] = k.get('status', '')
                break
        if p['status'] == 'True':
            p['status'] = 'Running'
        else:
            p['status'] = 'error'

        return p

    def get_pod_info(self, cluster_name, namespace, group):
        url = 'namespaces/' + namespace + '/pods'
        r = self.client.request(method='GET', url=url, timeout=self.timeout)
        if r.status_code != 200:
            return []

        content_list = []
        data = r.json()
        items = data.get('items', [])
        if items:
            for i in items:
                pod = {'cluster_name': cluster_name,  # pod所在集群
                       'api': self.client,  # 连接集群的apiserver
                       'group': group,  # 所属group
                       'namespace': namespace,  # pod所在的namespace
                       'service': i.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.service', ''),
                       # pod所属服务名
                       'service_threshold': '',  # 服务阈值
                       'node_name': i.get('spec').get('nodeName', ''),  # pod所属主机名
                       'pod_name': i.get('metadata', {}).get('name', ''),  # pod名称
                       'container_list': i.get('status', {}).get('containerStatuses', []),  # 容器列表
                       'host_ip': i.get('status', {}).get('hostIP', '')  # 主机ip
                       }
                if pod['group'] and pod['namespace'] and pod['service']:
                    check_threshold = DeployClient.instance().get_threshold(pod['service'], pod['group'],
                                                                            pod['namespace'])
                    if check_threshold and check_threshold.get('deployed', '') is True and check_threshold.get(
                            'supported', '') is True:
                        pod['service_threshold'] = check_threshold
                if pod['service_threshold']:
                    content_list.append(pod)

        content_1 = []
        re_content = []
        service_name_list = []
        for j in content_list:
            # Log(3, "service_name:{}".format(j.get('service', '')))
            service_name = j.get('service', '')
            if service_name:
                service_name_list.append(service_name)
        service_name_list = set(service_name_list)
        for k in service_name_list:
            temp_dic = {'service_name': k, 'pod_list': []}
            for m in content_list:
                if k == m.get('service', ''):
                    temp_dic['pod_list'].append(m)
            re_content.append(temp_dic)
        for m in re_content:
            content_1.append(random.sample(m['pod_list'], 1)[0])
        # Log(3, "re_content:{}".format(content_1))
        return content_1

    def get_one_pod(self, namespace, host_name):
        """
        获取一个主机上指定的namespace下的pod信息
        :param api:
        :return:[]
        """
        group_name = ''
        Log(4, 'syndata get_one_pod...:{}'.format(namespace))
        group_temp = WorkSpacedb.instance().read_workspace(namespace)
        if group_temp.success:
            group_name = group_temp.content['group']
        url = 'namespaces/' + namespace + '/pods'
        pods = self.client.request(method='GET', url=url, timeout=0.3)
        pod_list = []
        if pods.success:
            items = pods.content.get('items', [])
            if items:
                for j in items:
                    if j.get('spec', {}).get('nodeName') == host_name:
                        p = {'name': j.get('metadata', {}).get('name', ''),
                             'status': '',
                             'apply': j.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.app', ''),
                             'service': j.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.service',
                                                                                         ''),
                             'date': '',
                             'namespace': namespace,
                             'container': j.get('status', {}).get('containerStatuses', []),
                             'group_name': group_name
                             }
                        # Log(4, "syndata get_one_pod:{}".format(j.get('status', {})))

                        conditions = j.get('status', {}).get('conditions', [])
                        for k in conditions:
                            if k.get('type', '') == 'Ready':
                                p['status'] = k.get('status', '')
                                break

                        if p['status'] == 'True':
                            p['status'] = 'running'
                        else:
                            p['status'] = 'error'
                        t1 = j.get('status', {}).get('startTime', '')
                        if t1:
                            t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
                            t3 = utc2local(t2)
                            p['date'] = datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")
                        # else:
                        #     Log(3, "get_one pod\' status is pending or error:{}".format(j.get('status', '')))
                        if p['status'] == 'running':
                            pod_list.append(p)
        return Result(pod_list)

    def get_pod_set(self, namespace):
        """
        # 获取pod的限制
        # pod的限制是根据namespace设置大小确定的，默认和namespace的值相等
        """
        url = 'namespaces/' + namespace + '/limitranges'
        r = self.client.request(method='GET', url=url, timeout=self.timeout)
        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        pod_limit = r.json()
        data = pod_limit.get('items', [])
        if data:
            data = data[0]
            r = {'cpu': '', 'mem': ''}
            for i in data.get('spec', {}).get('limits', []):
                if 'max' in i.keys():
                    cpu_1 = i.get('max', {}).get('cpu', '')
                    if 'm' in cpu_1:
                        cpu_2 = round(int(cpu_1[:-1]) / 1000, 3)
                    else:
                        cpu_2 = int(cpu_1)
                    r['cpu'] = cpu_2

                    mem_1 = i.get('max', {}).get('memory', '')
                    if 'Gi' in mem_1:
                        mem_2 = int(mem_1[:-2])
                    elif 'Mi' in mem_1:
                        mem_2 = round(int(mem_1[:-2]) / 1024, 3)
                    elif 'm' in mem_1:
                        mem_2 = round(int(mem_1[:-1]) / (1024 ** 3 * 1000), 3)
                    else:
                        mem_2 = int(mem_1)
                    r['mem'] = mem_2
            return Result(r)
        return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, 'data invalid')

    def get_all_pods(self, cluster_name):
        """
        获取一个集群上所有pod
        :param cluster_name:
        :return:
        """
        rlt = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClient.get_pod_total get_ns_by_cluster [%s] fail, as[%s]' % (cluster_name, rlt.message))
            return rlt
        pods_list = []
        for ns in rlt.content:
            ret = self.get_pod_list(ns)
            if ret.success:
                pods_list.append(ret.content)
        return Result(pods_list)

    def get_pod_num(self, cluster_name):
        rlt = WorkSpacedb.instance().get_ns_by_cluster(cluster_name)
        if not rlt.success:
            Log(1, 'KubeClient.get_pod_total get_ns_by_cluster [%s] fail, as[%s]' % (cluster_name, rlt.message))
            return rlt

        total = 0
        for namespace in rlt.content:
            ret = self.get_pod_list(namespace)
            if ret.success:
                total += len(ret.content)
            else:
                Log(1, 'get_pod_total get_pod_list[%s] fail,as[%s]' % (namespace, ret.message))

        return total

    def get_all_nodes(self):
        """
        #  通过api获取添加成功的主机
        """
        url = '/nodes'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_apinodes except{}'.format(e))
            return Result('', msg='get_apinodes except{}'.format(e), result=400)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_node(self, node_name):
        url = 'nodes/' + node_name
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception as e:
            Log(3, "delete_node by apiserver failed:{}".format(e.message))
            return Result('')
        if r.status_code == 200:
            return Result('')
        else:
            Log(1, 'delete_node[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_node_info(self, node_name):
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_node_info except{}'.format(e))
            return Result('', msg='get_node_info except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_node_labels(self, node_name):
        """
        获取单个主机上的标签
        :param node_name:
        :return:
        """
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_node_info except{}'.format(e))
            return Result('', msg='get_node_info except{}'.format(e), result=400)

        if r.status_code == 200:

            data = {'labels': '', 'unschedulable': ''}
            node_info = r.json()
            labels = node_info.get('metadata', {}).get('labels', {})

            for label_key in labels.keys():
                if 'kubernetes' in label_key:
                    del labels[label_key]

            data['unschedulable'] = node_info.get('spec', {}).get('unschedulable', '')
            data['labels'] = labels
            return Result(data)
        else:
            Log(1, 'get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_all_labels(self):
        """
        获取一个集群上所有标签
        :return:
        """
        all_nodes = self.get_all_nodes()
        if not all_nodes.success:
            return Result('', all_nodes.result, all_nodes.message, 500)
        items = all_nodes.content
        data_list = []
        # items = node_info.json().get('items', {})
        if items:
            for i in items:
                if i.get('spec', {}).get('unschedulable', ''):
                    continue
                node_one = {'name': i.get('metadata', {}).get('name', ''),
                            'label': ''
                            }
                labels = i.get('metadata', {}).get('labels', {})
                for label_key in labels.keys():
                    if 'kubernetes' in label_key:
                        del labels[label_key]
                node_one['label'] = labels
                if node_one['label']:
                    data_list.append(node_one)
        return Result(data_list)

    def set_labels(self, node_name, labels):
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'set_labels except{}'.format(e))
            return Result('', msg='set_labels except{}'.format(e), result=400)

        if r.status_code != 200:
            Log(1, 'KubeClient.set_labels get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        olddata = copy.deepcopy(data.get('metadata', {}).get('labels', {}))
        olddata.update(labels)

        data['metadata']['labels'] = olddata

        return self.update_node_info(node_name, data)

    def is_unschedulable(self, node_name):
        """
        # 查看主机是否为维护模式
        """
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_node_info except{}'.format(e))
            return Result('', msg='get_node_info except{}'.format(e), result=400)

        if r.status_code == 200:
            node_info = r.json()
            if node_info.get('spec', {}).get('unschedulable', ''):
                return Result(True)

            return Result(False)
        else:
            Log(1, 'get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def change_schedulable(self, node_name, status):
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'set_labels except{}'.format(e))
            return Result('', msg='set_labels except{}'.format(e), result=400)

        if r.status_code != 200:
            Log(1, 'KubeClient.set_labels get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        check = data.get('spec', {}).get('unschedulable', '')

        if bool(check) == bool(status):
            Log(3, 'change_schedulable skip as the status is same')
            return Result('ok')

        if status:
            data.get('spec', {})['unschedulable'] = True
        else:
            data.get('spec', {})['unschedulable'] = '1'
            del data.get('spec', {})['unschedulable']

        return self.update_node_info(node_name, data)

    def update_node_info(self, node_name, node_info):
        url = 'nodes/%s' % (node_name)
        try:
            r = self.client.request(method='PUT', url=url, data=json.dumps(node_info), timeout=self.timeout)
        except Exception, e:
            Log(1, 'update_node_info except{}'.format(e))
            return Result('', msg='update_node_info except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'update_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

    def get_service_list(self):
        url = 'services'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get_service_list except{}'.format(e))
            return Result('', msg='get_service_list except{}'.format(e), result=400)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def load_cluster_info(self, master_ip, cluster_name):
        rlt = self.get_all_nodes()
        if not rlt.success:
            Log(1, 'KubeClient.load_cluster_info get_all_nodes [%s][%s] fail, as[%s]' % (
                master_ip, cluster_name, rlt.message))
            return rlt

        inf_dic = {'node_num': 0, 'node_list': []}
        for node in rlt.content:
            n = Node()
            n.apply(node)
            if n.ip:
                inf_dic['node_list'].append(n.ip)
                inf_dic['node_num'] += 1

                n.node_type = 'master' if n.ip == master_ip else 'node'
                n.cluster_name = self.cluster_name
                n.pod_num = self.get_pod_num(cluster_name)
                n.save()

        return Result(inf_dic)

    def get_configmaps(self, namespace):
        url = 'namespaces/' + namespace + '/configmaps'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get configmaps except{}'.format(e))
            return Result('', msg='get configmaps except{}'.format(e), result=400)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def create_configmaps(self, namespace, data):
        """
        设置configmap
        :param namespace:
        :param data:
        :return:
        """
        url = 'namespaces/' + namespace + '/configmaps'
        try:
            r = self.client.request(method='POST', data=json.dumps(data), url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get configmaps except{}'.format(e))
            return Result('', msg='post configmaps except{}'.format(e), result=400)

        if r.status_code != 201:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text, r.status_code)

        data = r.json()
        return Result(data.get('items', []))

    def delete_configmap(self, namespace, name):
        """
        删除configmap
        :param namespace:
        :param configmap:
        :return:
        """
        url = 'namespaces/' + namespace + '/configmaps/' + name
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'delete configmaps except{}'.format(e))
            return Result('', msg='delete configmaps except{}'.format(e), result=400)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text, r.status_code)
        data = r.json()
        return Result(data)

    def get_persistent_volumes(self):
        """
        # 查询persistent volumes列表
        """
        url = 'persistentvolumes'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get persistent volumes except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volumes except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def get_persistent_volume_info(self, name):
        """
        # 查询persistent volumes列表
        """
        url = 'persistentvolumes/' + name
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get persistent volumes except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volume except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        return Result(r.json())

    def create_persistent_volume(self, data):
        """
        # 创建persistent volumes
        """
        url = 'persistentvolumes'
        try:
            r = self.client.request(method='POST', data=json.dumps(data), url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'create persistent volume except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'create persistent volume except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_persistent_volume(self, name):
        """
        # 删除 persistent volume
        """
        url = 'persistentvolumes/' + name
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'delete persistentvolume except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'delete persistentvolume except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def get_persistent_volume_claims(self):
        """
        # 查询persistent volumes列表
        """
        url = 'persistentvolumeclaims'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get persistent volume claims except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volume claims except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def get_persistent_volume_claim_info(self, namespace, name):
        """
        # 查询persistent volumes列表
        """
        url = 'namespaces/%s/persistentvolumeclaims/%s' % (namespace, name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'get persistent volume claims except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volume claims except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        return Result(r.json())

    def create_persistent_volume_claim(self, namespace, data):
        """
        # 创建persistent volumes
        """
        url = 'namespaces/%s/persistentvolumeclaims' % (namespace)
        try:
            r = self.client.request(method='POST', data=json.dumps(data), url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'create persistent volume claim except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volume claims except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_persistent_volume_claim(self, namespace, name):
        """
        # 删除 persistent volume
        """
        url = 'namespaces/%s/persistentvolumeclaims/%s' % (namespace, name)
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception, e:
            Log(1, 'delete persistent volume claim except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get persistent volume claims except{}'.format(e),
                          http.EXPECTATION_FAILED)

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def all_events(self):
        """
        获取所有namespace下的events
        :return:
        """
        try:
            r = self.client.request(method='GET', url='events', timeout=self.timeout)
            return Result(r.json().get('item', []))
        except Exception, e:
            return Result('', 500, e.message, 500)
        except ValueError:
            # return Result(r.text)
            return Result('')

    def ns_events(self, ws):
        """
        获取指定workspace下的events
        :param ws:
        :return:
        """
        try:
            r = self.client.request(method='GET', url='namespaces/' + ws + '/events', timeout=self.timeout)
            return Result(r.json().get('items', []))
        except Exception, e:
            return Result('', 500, e.message, 500)
        except ValueError:
            # return Result(r.text)
            return Result('')

    def test_apiserver(self, url, version='v1', base='/api'):
        """
        测试apiserver接口
        :return:
        """
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout, version=version, base=base)
            Log(3, "r.url{}".format(self.client.url))
            try:
                return Result(r.json())
            except Exception as e:
                return Result(r.text)
        except ValueError:
            # return Result(r.text)
            PrintStack()
            return Result('', 500, '', 500)
        except Exception, e:
            PrintStack()
            return Result('', 500, e.message, 500)

    def get_storage_classes(self):
        """
        # 查询storage class列表
        """
        url = 'storageclasses'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout, base='/apis/storage.k8s.io',
                                    version='v1beta1')
        except Exception, e:
            Log(1, 'get storage classes except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get storage classes except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient get_storage_classes return [{}]'.format(r.text))

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def get_storage_class_info(self, name):
        """
        # 查询指定storage class详细信息
        """
        url = 'storageclasses/{}'.format(name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout, base='/apis/storage.k8s.io',
                                    version='v1beta1')
        except Exception, e:
            Log(1, 'get storage class info except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get storage class info except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient get_storage_class_info return [{}]'.format(r.text))

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        return Result(r.json())

    def create_storage_class(self, data):
        """
        # 创建storage class
        """
        url = 'storageclasses'
        try:
            r = self.client.request(method='POST', data=json.dumps(data), url=url, timeout=self.timeout,
                                    base='/apis/storage.k8s.io', version='v1beta1')
        except Exception, e:
            Log(1, 'create storage class except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get storage class except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient create_storage_class return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_storage_class(self, name):
        """
        # 删除 storage class
        """
        url = 'storageclasses/{}'.format(name)
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout, base='/apis/storage.k8s.io',
                                    version='v1beta1')
        except Exception, e:
            Log(1, 'delete storage class except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get storage class except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient delete_storage_class return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def get_deployments(self, namespace):
        """
        # 查询deployment列表
        """
        url = 'namespaces/{}/deployments'.format(namespace)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout, base='/apis/apps', version='v1beta1')
        except Exception, e:
            Log(1, 'get deployment list except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get deployment list except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient get_deployments return [{}]'.format(r.text))

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def get_deployment_info(self, namespace, name):
        """
        # 查询deployment详细信息
        """
        url = 'namespaces/{}/deployments/{}'.format(namespace, name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout, base='/apis/apps', version='v1beta1')
        except Exception, e:
            Log(1, 'get deployment info except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get deployment info except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient get_deployment_info return [{}]'.format(r.text))

        if r.status_code != 200:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        return Result(r.json())

    def create_deployment(self, namespace, data):
        """
        # 创建deployment
        """
        url = 'namespaces/{}/deployments'.format(namespace)
        try:
            r = self.client.request(method='POST', data=json.dumps(data), url=url, timeout=self.timeout,
                                    base='/apis/apps', version='v1beta1')
        except Exception, e:
            Log(1, 'create deployment except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'get deployment except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient create_deployment return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def delete_deployment(self, namespace, name):
        """
        # 删除 deployment
        """
        url = 'namespaces/{}/deployments/{}'.format(namespace, name)
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout, base='/apis/apps',
                                    version='v1beta1')
        except Exception, e:
            Log(1, 'delete deployment except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'delete deployment except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient delete_deployment return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def delete_replicaset(self, namespace, name):
        """
        # 删除 replicaset
        """
        url = 'namespaces/{}/replicasets/{}'.format(namespace, name)
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout, base='/apis/extensions',
                                    version='v1beta1')
        except Exception, e:
            Log(1, 'delete replicaset except{}'.format(e))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'delete replicaset except{}'.format(e),
                          http.EXPECTATION_FAILED)

        Log(4, 'kubeclient delete_replicaset return [{}]'.format(r.text))

        if r.status_code >= 300:
            return Result('', CALL_KUBE_INSTERFACE_FAIL_ERROR, r.text)

        data = r.json()
        return Result(data)

    def parse_pod_resource(self, namespace, deployment_name):
        rlt = self.get_pods(namespace)
        if not rlt.success:
            Log(1, 'kubeclient remove_storage_class_deploy get_pods[%s] fail,as[%s]' % (namespace, rlt.message))
            return None

        pod_metadata = None
        for pod in rlt.content:
            metadata = pod.get('metadata', {})
            if metadata and metadata.get('labels', {}).get('app', '') == deployment_name:
                pod_metadata = metadata

        if not pod_metadata:
            return None

        data = {}
        data['pod_name'] = pod_metadata.get('name')
        ownerReferences = pod_metadata.get('ownerReferences', [])
        if ownerReferences and isinstance(ownerReferences, list):
            for ref in ownerReferences:
                if ref.get('kind') == 'ReplicaSet':
                    data['replicaset_name'] = ref.get('name')

        return data

    def remove_storage_class_deploy(self, namespace, deployment_name):
        """
        # 移除deployment全部的资源
        """
        res = self.parse_pod_resource(namespace, deployment_name)

        rlt = self.delete_deployment(namespace, deployment_name)
        if not rlt.success:
            Log(1, 'kubeclient remove_storage_class_deploy delete_deployment[%s][%s] fail,as[%s]' % (
                namespace, deployment_name, rlt.message))
            return rlt

        if not res:
            return Result('done')

        if 'replicaset_name' in res:
            rlt = self.delete_replicaset(namespace, res['replicaset_name'])
            if not rlt.success:
                Log(1, 'kubeclient remove_storage_class_deploy delete_pod[%s][%s] fail,as[%s]' % (
                    namespace, res['replicaset_name'], rlt.message))
        else:
            Log(1, 'kubeclient remove_storage_class_deploy[%s][%s] replicaset not exist' % (namespace, deployment_name))

        if 'pod_name' in res:
            rlt = self.delete_pod(namespace, res['pod_name'])
            if not rlt.success:
                Log(1, 'kubeclient remove_storage_class_deploy delete_pod[%s][%s] fail,as[%s]' % (
                    namespace, res['pod_name'], rlt.message))
        else:
            Log(1, 'kubeclient remove_storage_class_deploy[%s][%s] pod not exist' % (namespace, deployment_name))

        return Result('done')

    def eviction(self, ns, pod_name):
        """
        create eviction for node drain
        :param ns:
        :param pod_name:
        :return:
        """
        url = "namespaces/{}/pods/{}/eviction".format(ns, pod_name)
        data = {
            "apiVersion": "policy/v1beta1",
            "kind": "Eviction",
            "metadata": {
                "name": pod_name,
                "namespace": ns
            }
        }
        try:
            r = self.client.request(method='POST', url=url, data=json.dumps(data), timeout=self.timeout)
        except Exception, e:
            Log(1, 'post eviction except{}'.format(e.message))
            return Result('', CALL_KUBE_INSTERFACE_EXCEPT_ERROR, 'post eviction except{}'.format(e.message),
                          http.EXPECTATION_FAILED)
        Log(4, "eviction.....status:{}, text:{}, url:{}".format(r.status_code, r.text, url))
        if r.status_code == 201:
            return Result(r.json())
        else:
            return Result(r.text, r.status_code, '', r.status_code)

    def clu_status(self):
        """
        cluster status
        :return:
        """
        try:
            r = self.client.request(method='GET', url='componentstatuses', timeout=self.timeout)
            return Result(r.json().get('items', []))
        except Exception as e:
            return Result('', 500, e.message, 500)
        except ValueError:
            # return Result(r.text)
            return Result('')

    @requestexcept
    def create_clusterroles(self, data):
        # '/ apis / rbac.authorization.k8s.io / v1 / clusterroles / view'
        r = self.client.request(method='POST', url='clusterroles', timeout=self.timeout, data=json.dumps(data),
                                version='rbac.authorization.k8s.io/v1', base='/apis')
        if r.status_code == 201:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def clusterroles(self, name=None):
        url = 'clusterroles/%s' % name if name else 'clusterroles'
        r = self.client.request(method='GET', url=url, timeout=self.timeout, version='rbac.authorization.k8s.io/v1',
                                base='/apis')
        if r.status_code == 200:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def del_clusterroles(self, name):
        r = self.client.request(method='DELETE', url='clusterroles/%s' % name, timeout=self.timeout,
                                version='rbac.authorization.k8s.io/v1', base='/apis')
        if r.status_code == 200:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def create_clusterrolebinding(self, data):
        # '/ apis / rbac.authorization.k8s.io / v1 / clusterroles / view'
        r = self.client.request(method='POST', url='clusterrolebindings', timeout=self.timeout, data=json.dumps(data),
                                version='rbac.authorization.k8s.io/v1', base='/apis')
        if r.status_code == 201:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def clusterrolebinding(self, name=None):
        url = 'clusterrolebindings/%s' % name if name else 'clusterrolebindings'
        r = self.client.request(method='GET', url=url, timeout=self.timeout, version='rbac.authorization.k8s.io/v1',
                                base='/apis')
        if r.status_code == 200:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)

    @requestexcept
    def del_clusterrolebinding(self, name):
        r = self.client.request(method='DELETE', url='clusterrolebindings/%s' % name, timeout=self.timeout,
                                version='rbac.authorization.k8s.io/v1', base='/apis')
        if r.status_code == 200:
            return Result(r.json())
        else:
            return Result('', r.status_code, r.text, r.status_code)