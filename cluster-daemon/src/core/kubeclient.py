# ! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
import base64
import datetime
import random

import pykube

from common.util import Result, utc2local
from core.deployclient import DeployClient
from core.errcode import FAIL
from frame.logger import Log
from etcddb.workspacemgr import WorkSpacedb


class KubeClient(object):
    def __init__(self, auth_info):
        self.auth_data = auth_info.get('auth_data')
        self.server = auth_info.get('server')
        self.cert_data = auth_info.get('cert_data')
        self.client_key = auth_info.get('client_key')
        self.cluster_name = auth_info.get('cluster_name')
        self.timeout = 10
        self.connect_time = 0

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
            response = api.request(method='GET', url='', timeout=5)
        except pykube.PyKubeError as e:
            Log(3, 'server:{},ssl error:{}'.format(self.server, e.message))
            return Result('', FAIL, 'KubeClient connect to server:{} fail,ssl error:{}'.format(self.server, e))
        except Exception as e:
            Log(3, 'server:{},ssl error:{}'.format(self.server, e.message))
            return Result('', FAIL, 'KubeClient connect to server:{} except,ssl error:{}'.format(self.server, e))

        if response.status_code == 200:
            self.client = api
            return Result('ok')
        else:
            Log(3, msg='server:{} ssl error. text:{}'.format(self.server, response.text))
            return Result('', FAIL, response.text)

    def parse_pod_info(self, pod):
        p = {'name': pod.get('metadata', {}).get('name', ''),
             'status': '',
             'apply': pod.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.app', ''),
             'service': pod.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.service', ''),
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
            p['status'] = 'running'
        else:
            p['status'] = 'error'

        return p

    def get_pod_info(self, cluster_name, namespace, group):
        url = '/namespaces/' + namespace + '/pods'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            Log(3, "get_pod_info from apiserver:{}".format(e.message))
            return []
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
                       'app': i.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.app', ''),  # app name
                       'deploy': i.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.deploy', ''),  # deploy name
                       'is_can_scale': i.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.autoscale', ''),  # 是否支持弹性伸缩
                       # pod所属deployment
                       'status': i.get('status', {}).get('phase'),
                       'service_threshold': '',  # 服务阈值
                       'node_name': i.get('spec').get('nodeName', ''),  # pod所属主机名
                       'pod_name': i.get('metadata', {}).get('name', ''),  # pod名称
                       'container_list': i.get('status', {}).get('containerStatuses', []),  # 容器列表
                       'host_ip': i.get('status', {}).get('hostIP', ''),  # 主机ip
                       'pod_uid': i.get('metadata', {}).get('uid', ''),
                       'container_resouse': i.get('spec', {}).get('containers', [])
                       }
                Log(4, "elastic pod:{}".format(pod))
                if pod['group'] and pod['namespace'] and pod['deploy'] and pod['status'] == 'Running':
                    check_threshold = DeployClient.instance().get_threshold(pod['deploy'], pod['group'],
                                                                            pod['namespace'])
                    Log(4, "get_threashold:{}".format(check_threshold))
                    if check_threshold and check_threshold.get('deployed', '') is True:
                        pod['service_threshold'] = check_threshold

                if pod['service_threshold']:
                    content_list.append(pod)
        content_1 = []
        re_content = []
        deploy_name_list = []
        for j in content_list:
            # Log(3, "service_name:{}".format(j.get('service', '')))
            deploy_name = j.get('deploy', '')
            if deploy_name:
                deploy_name_list.append(deploy_name)
        deploy_name_list = set(deploy_name_list)
        for k in deploy_name_list:
            temp_dic = {'deploy_name': k, 'pod_list': []}
            for m in content_list:
                if k == m.get('deploy', ''):
                    temp_dic['pod_list'].append(m)
            re_content.append(temp_dic)
        for m in re_content:
            content_1.append(random.sample(m['pod_list'], 1)[0])
        return content_1
        # return re_content

    def get_host_pod_list(self, namespace, host_ip):
        url = '/namespaces/%s/pods' % (namespace)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
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
            pod_list = data.get('items', [])
            for pod in pod_list:
                if pod.get('hostIP') == host_ip:
                    # info = self.parse_pod_info(pod)
                    # info['namespace'] = namespace
                    # info['group_name'] = group
                    # if info['status'] == 'running':
                    arr.append(pod)

            return Result(arr)
        else:
            Log(1, 'get_pod_list[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', FAIL, r.text)

    def get_all_pods(self):
        url = 'pods'
        t1 = datetime.datetime.now()
        Log(4, "******** now:{}".format(datetime.datetime.now()))
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            Log(1, 'get request from apiserver error:{}'.format(e.message))
            return Result('', msg='get_pod_list except{}'.format(e.message), result=400)
        Log(4, "******************* now:{}".format(datetime.datetime.now()))
        Log(4, "get_all_pods cost:{}".format(datetime.datetime.now() - t1))
        if r.status_code == 200:
            data = r.json()
            pod_list = data.get('items', [])
            return Result(pod_list)
        else:
            Log(1, 'get all pods list fail,as[%s]' % r.text)
            return Result('', FAIL, r.text)

    def get_host_pod_num(self, ns_list, host_ip):
        t1 = datetime.datetime.now()
        pod_num = 0
        for ns in ns_list:
            url = 'namespaces/%s/pods' % ns
            try:
                r = self.client.request(method='GET', url=url, timeout=self.timeout)
            except Exception as e:
                Log(1, 'get_pod_list except{}'.format(e))
                return Result('', msg='get_pod_list except{}'.format(e), result=400)
            Log(3, "get_host_pod_num host_ip:{}, time1:{}".format(host_ip, datetime.datetime.now() - t1))

            if r.status_code == 200:
                data = r.json()
                pod_list = data.get('items', [])
                for pod in pod_list:
                    if pod.get('status', {}).get('hostIP') == host_ip and pod.get('metadata', {}).get('namespace') in ns_list:
                        info = self.parse_pod_info(pod)
                        if info['status'] == 'running':
                            pod_num += 1
            else:
                Log(1, 'get_pod_list[%s]fail,as[%s]' % (ns_list, r.text))
                return Result('', FAIL, r.text)
        return Result(pod_num)

    def get_node_pods(self, node_name):
        """
        获取某个node上的pods
        :param node_name:
        :return:
        """
        url = 'proxy/nodes/{}/pods'.format(node_name)
        t1 = datetime.datetime.now()
        Log(4, "******** now:{}".format(datetime.datetime.now()))
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            Log(2, 'get all  pods list except{}'.format(e))
            return Result('', msg='get_pod_list except{}'.format(e), result=400)
        Log(4, "get_all_pods cost:{}".format(datetime.datetime.now() - t1))
        if r.status_code == 200:
            data = r.json()
            pod_list = data.get('items', [])
            if pod_list:
                return Result(pod_list)
            else:
                Log(1, "get node pod None:{}".format(pod_list))
                return Result([])
        else:
            Log(1, 'get all pods list fail,as[%s]' % r.text)
            return Result('', FAIL, r.text)

    def get_pod_set(self, namespace):
        """
        # 获取pod的限制
        # pod的限制是根据namespace设置大小确定的，默认和namespace的值相等
        """
        url = '/namespaces/' + namespace + '/limitranges'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            return Result('', 400, e.message)
        if r.status_code != 200:
            return Result('', FAIL, r.text)

        pod_limit = r.json()
        data = pod_limit.get('items', [])
        if data:
            data = data[0]

            for i in data.get('spec', {}).get('limits', []):
                re_data = {}
                if i.get('type') == "Pod":
                    cpu_1 = i.get('max', {}).get('cpu', '')
                    if 'm' in cpu_1:
                        cpu_2 = int(cpu_1[:-1]) / 1000
                    else:
                        cpu_2 = int(cpu_1)
                    re_data['cpu'] = cpu_2

                    mem_1 = i.get('max', {}).get('memory', '')
                    if 'Gi' in mem_1:
                        mem_2 = int(mem_1[:-2])
                    elif 'Mi' in mem_1:
                        mem_2 = int(mem_1[:-2]) / 1024
                    elif 'm' in mem_1:
                        mem_2 = int(mem_1[:-1]) / (1024 ** 3 * 1000)
                    else:
                        mem_2 = int(mem_1)
                    re_data['mem'] = mem_2
                    return Result(re_data)
        return Result('', FAIL, 'data invalid')

    def get_all_nodes(self):
        """
        #  通过api获取添加成功的主机
        """
        url = '/nodes'
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            Log(3, 'get_apinodes except{}'.format(e))
            return Result('', msg='get_apinodes except{}'.format(e), result=500)

        if r.status_code != 200:
            return Result('', FAIL, r.text)

        data = r.json()
        return Result(data.get('items', []))

    def get_node_info(self, node_name):
        url = '/nodes/%s' % (node_name)
        try:
            r = self.client.request(method='GET', url=url, timeout=self.timeout)
        except Exception as e:
            Log(1, 'get_node_info except{}'.format(e))
            return Result('', msg='get_node_info except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result(r.json())
        else:
            Log(1, 'get_node_info[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', FAIL, r.text)

    def delete_namespace(self, namespace):
        url = '/namespaces/' + namespace
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception as e:
            Log(1, 'delete_namespace except{}'.format(e))
            return Result('', msg='delete_namespace except{}'.format(e), result=400)

        if r.status_code == 200:
            return Result('')
        else:
            Log(1, 'delete_namespace[%s]fail,as[%s]' % (namespace, r.text))
            return Result('', FAIL, r.text)

    def delete_node(self, node_name):
        url = '/nodes/' + node_name
        try:
            r = self.client.request(method='DELETE', url=url, timeout=self.timeout)
        except Exception as e:
            return Result('', 400, 'delete_node except:{}'.format(e.message))
        if r.status_code == 200:
            return Result('')
        else:
            Log(1, 'delete_node[%s]fail,as[%s]' % (node_name, r.text))
            return Result('', FAIL, r.text)

    def clu_status(self):
        """
        cluster status
        :return:
        """
        try:
            r = self.client.request(method='GET', url='componentstatuses', timeout=self.timeout)
            # status_list = []
            # if r.status_code == 200:
            #     for i in r.json().get('items', []):
            #         for j in i.get('conditions'):
            #             if j.get('type') == 'Healthy':
            #                 s = j.get('status')
            #                 if s:
            #                     status_list.append(s)
            return Result(r.json().get('items', []))
        except Exception as e:
            return Result('', 500, e.message, 500)
        except ValueError:
            # return Result(r.text)
            return Result('')