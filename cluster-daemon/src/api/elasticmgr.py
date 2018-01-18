# -*- coding: utf-8 -*-

"""
Created on 2017年3月01日

@author: ufleet

"""

from __future__ import division
from frame.logger import Log, PrintStack
import datetime
from etcddb.clustermgr import Clusterdb
from core.kubeclientmgr import KubeClientMgr
from core.deployclient import DeployClient
import time
from etcddb.clunodes import CluNodedb
import Queue
from common.inter import Factory
from operator import itemgetter
from core.cadvisor import Cadvisor
import threading


class DeployAnly(object):
    """
    deploy的弹性伸缩
    监控deploy下的容器，并进行弹性伸缩
    """

    def __init__(self, clu_name, nodes, deploys):
        self.status = 0
        self.clu_name = clu_name
        self.nodes = nodes
        self.deploys = deploys

    def disk_anly(self, disk_list):
        """
        对disk进行分析
        :param disk_list:
        :return:
        """
        pass

    def get_net_data(self, host_ip, pause_id):
        """
        get net data
        :param host_ip:
        :return:
        """
        r_d = []
        cadvisor_cli = Cadvisor(host_ip)
        rlt = cadvisor_cli.get(pause_id)
        if rlt.success:
            net_data = rlt.content
            if net_data and isinstance(net_data, dict):
                data = net_data.values()[0]
                j = data.get('stats', [])
                for k in j:
                    net_info = {
                        'timestamp': k.get('timestamp', ''),
                        'net': k.get('network', {}).get('interfaces', [])
                    }
                    r_d.append(net_info)
        else:
            Log(1, "get net data from cadvisor error:{}".format(rlt.message))
        return r_d

    def cpu_anly(self, cpu_list):
        """
        对container's cpu进行数据分析
        :return:
        """
        num = 0
        cpu_data = []
        cpu_list1 = sorted(cpu_list, key=itemgetter('timestamp'))
        for i in range(len(cpu_list1) - 1):
            t_d = cpu_list1[i + 1]['timestamp'] - cpu_list1[i]['timestamp']
            t_micro = t_d.seconds * 10 ** 6 + t_d.microseconds
            Log(3, "cpu_anly t_micro:{}".format(t_micro))
            if t_micro:
                c_use = cpu_list1[i + 1]['cpu']['usage']['total'] - cpu_list1[i]['cpu']['usage']['total']
                Log(4, "c_use:{}, t_micro:{}, {}".format(c_use, 10 ** 3 * t_micro, c_use / (10 ** 3 * t_micro)))
                cpu_data.append(c_use / (10 ** 3 * t_micro))
                num += 1
        return round(sum(cpu_data) / num, 3) * 100 if num else None

    def mem_one_container(self, mem_list):
        """
        对container's mem进行数据分析
        :param mem_list:
        :return:
        """
        mem = 0
        num = 0
        for k in mem_list:
            mem += k.get('memory', {}).get('usage', 0)
            num += 1
        if num:
            return round(mem / num, 3)
        else:
            return None

    def anly_one_pod_flow(self, pod):
        """
        对网络进行分析
        :param net_list:
        :return:
        """
        d_list = []
        net_r = []
        Log(4, "anly_one_pod_flow pause_data:{}".format(pod.get('pause_data')))
        for i in pod.get('pause_data', {}).get('stats', []):
            Log(3, "net_anly:{}".format(i))
            network = i.get('network', {})
            if not network:
                continue
            for j in network.get('interfaces', []):
                if j.get('name', '').startswith('eth'):
                    timestamp = i.get('timestamp', '')[0:26]
                    Log(4, "anly_one_pod_flow timestamp:{}, tx_bytes0:{}, rx_bytes0:{}".format(timestamp,
                                                                                               j.get('tx_bytes'),
                                                                                               j.get('rx_bytes')))
                    r = {
                        'time': datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f'),
                        'tx_bytes0': j.get('tx_bytes'),
                        'rx_bytes0': j.get('rx_bytes')
                    }
                    net_r.append(r)
                    break
        d_s = sorted(net_r, key=lambda s: s['time'])
        for index, item in enumerate(d_s):
            if not index:
                continue
            t_del = item['time'] - d_s[index - 1]['time']
            t_ = t_del.seconds + t_del.microseconds / 10 ** 6
            Log(3, "anly_one_pod_flow, t1:{}, t2:{}. t_:{}, rx1:{}, tx1:{}".format(item['time'], d_s[index - 1]['time'],
                                                                                   t_, item['rx_bytes0'],
                                                                                   d_s[index - 1]['rx_bytes0']))
            if t_:
                rx_bytes = round(abs(item['rx_bytes0'] - d_s[index - 1]['rx_bytes0']) / (t_ * 1024), 2)
                tx_bytes = round(abs(item['tx_bytes0'] - d_s[index - 1]['tx_bytes0']) / (t_ * 1024), 2)
                d_list.append(round(rx_bytes + tx_bytes, 3))
        Log(3, 'net_anly:{}'.format(d_list))
        return round(sum(d_list) / len(d_list), 3) if len(d_list) else None

    def anly_one_pod_cpu(self, pod):
        """
        对cpu进行数据分析
        :return:
        """
        Log(3, "anly_one_pod_cpu:{}".format(pod))
        pod_all_cpu = 0
        for i in pod.get('container_data', []):
            cpu_list = []
            if i:
                j = i.get('stats', [])
                for k in j:
                    try:
                        timestamp = datetime.datetime.strptime(k.get('timestamp')[0:-9], "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        Log(1, "elasticmgr timestamp:{}".format(k.get('timestamp')))
                        continue
                    except Exception as e:
                        Log(1, "elasticmgr :{}".format(e.message))
                        continue
                    cpu_info = {
                        'timestamp': timestamp,
                        'cpu': k.get('cpu', ''),
                    }
                    cpu_list.append(cpu_info)

                # cpu检查
                cpu_use = self.cpu_anly(cpu_list)
                if cpu_use is not None:
                    pod_all_cpu += cpu_use

                Log(3, "pod_all_info:{}".format(pod_all_cpu))
            else:
                continue

        return pod_all_cpu

    def anly_one_pod_mem(self, pod):
        """
        对mem进行数据分析
        :return:
        """
        mem_p = 0
        for i in pod.get('container_data', []):
            if not i:
                continue
            mem_one = self.mem_one_container(i.get('stats', []))
            if mem_one is None:
                continue
            Log(4, "naly_one_pod_mem, mem_one:{}".format(mem_one))
            mem_p += mem_one

        pod_mem_set = self.pod_set(pod.get('resource', []))
        Log(4, "anly_one_pod_mem:{}, mem_p:{}, per:{}".format(pod_mem_set, mem_p,
                                                              round(mem_p * 100 / (1024 * 1024 * 1024 * pod_mem_set),
                                                                    2)))
        return round(mem_p * 100 / (1024 * 1024 * 1024 * pod_mem_set), 2) if pod_mem_set else None

    def compare_metrics(self, deploy, m_type, cur_data, min_data, max_data):
        """
        :param m_type:
        :param cur_data:
        :param min_data:
        :param max_data:
        """
        cur_replicas = deploy.get('hpa', {}).get('replicas')
        min_replicas = deploy.get('hpa', {}).get('minReplicas')
        max_replicas = deploy.get('hpa', {}).get('maxReplicas')

        if max_replicas == 0:
            max_replicas = 10000000

        Log(3, "elastic compare_metrics deploy:{}, type:{}, current data:{}, set_min:{}, set_max:{}, cur_replicas:{},\
        min_replicas:{}, max_replicas:{}".format(deploy.get('name'), m_type, cur_data, min_data, max_data,
                                                 cur_replicas, min_replicas, max_replicas))
        if cur_data < min_data and cur_replicas - 1 >= min_replicas:  # elastic -1
            r = DeployClient.instance().service_up(deploy.get('name'), deploy.get('group', ''),
                                                   deploy.get('workspace', ''), -1)
            if r:
                Log(3, u"deploy {} , 缩容 -1 成功".format(deploy.get('name')))
            else:
                Log(1, u"deploy {}, 缩容 -1 失败".format(deploy.get('name')))
            return
        if cur_data > max_data and cur_replicas + 1 <= max_replicas:  # elastic +1
            r = DeployClient.instance().service_up(deploy.get('name'), deploy.get('group', ''),
                                                   deploy.get('workspace', ''), 1)
            if r:
                Log(3, u"deploy {}, 扩容 1 成功".format(deploy.get('name')))
            else:
                Log(1, u"deploy {}, 扩容 1 失败".format(deploy.get('deploy', '')))
            return
        return

    def pod_set(self, resource_list):
        """
        :param :
        :return:
        """
        mem_total = 0
        for con in resource_list:
            s_mem = con.get('resources', {}).get('limits', {}).get('memory', '')
            if 'Gi' in s_mem:
                mem_total += int(s_mem[:-2])
            elif 'Mi' in s_mem:
                mem_total += int(s_mem[:-2]) / 1024
            elif 'm' in s_mem:
                mem_total += int(s_mem[:-1]) / (1024 ** 3 * 1000)
            else:
                try:
                    Log(1, "pod_set can not anly the mem data:{}".format(s_mem))
                except ValueError:
                    PrintStack()

        Log(4, "pod all limit mem:{}, resource_list:{}".format(mem_total, resource_list))
        if not mem_total:
            Log(1, "get pod limit error.{}".format(mem_total))
            return None
        return mem_total

    def anly_one_deploy(self, deploy):
        h = deploy.get('hpa', {}).get('hpa', {})
        # elastic cpu
        pods_list = deploy.get('pods_list', [])
        if not pods_list:
            return
        Log(4, "anly_one_deploy len(pods):{}".format(len(pods_list)))
        # elastic cpu
        if h.get('min_cpu') or h.get('max_cpu'):
            all_cpu = 0
            for pod in pods_list:
                one_pod_cpu = self.anly_one_pod_cpu(pod)
                if one_pod_cpu is None:
                    Log(1, "anly_one_deploy anly_one_pod_cpu get None data}")
                    continue
                all_cpu += one_pod_cpu
            per_pod = round(all_cpu / len(pods_list), 3)
            self.compare_metrics(deploy.get('hpa', {}), 'cpu', per_pod, h.get('min_cpu'), h.get('max_cpu'))
            return
        # elastic mem
        elif h.get('min_mem') or h.get('max_mem'):
            all_mem = 0
            for pod in pods_list:
                one_pod_mem = self.anly_one_pod_mem(pod)
                if one_pod_mem is None:
                    Log(1, "anly_one_deploy anly_one_pod_mem get None data}")
                    continue
                Log(4, "&&&&&&&&&&&&&&&&&&&&&&&&&&one_pod_mem:{}".format(one_pod_mem))
                all_mem += one_pod_mem
            per_pod = round(all_mem / len(pods_list), 3)
            self.compare_metrics(deploy.get('hpa', {}), 'mem', per_pod, h.get('min_mem'), h.get('max_mem'))
            return
        # elastic net
        elif h.get('min_flow') or h.get('max_flow'):
            all_flow = 0
            for pod in pods_list:
                one_pod_flow = self.anly_one_pod_flow(pod)
                if one_pod_flow is None:
                    Log(1, "anly_one_deploy anly_one_pod_flow get None data}")
                    continue
                all_flow += one_pod_flow
            per_pod = round(all_flow / len(pods_list))
            self.compare_metrics(deploy.get('hpa', {}), 'flow', per_pod, h.get('min_flow'), h.get('max_flow'))
            return
        else:
            return

    def one_node_cadvisor(self, ip, queue):
        cadvisor_cli = Cadvisor(ip, timeout=15)
        rlt = cadvisor_cli.get()
        Log(4, "one_node_cadvisor, ip:{}, len(all_containers):{}".format(ip, queue.qsize()))
        queue.put(rlt)
        Log(4, "one_node_cadvisor1, ip:{}, len(all_containers):{}".format(ip, queue.qsize()))

    def clu_pods(self):
        # 一个集群下所有主机的所有容器的cadvisor监控数据 all_containers = {'container_id': {}, 'container_id': {}, ....}
        all_containers = dict()
        tasks = []
        data_queue = Queue.Queue()
        num = 0
        for node in self.nodes:
            one = threading.Thread(target=self.one_node_cadvisor, args=(node.get('ip'), data_queue))
            tasks.append(one)
            num += 1
        t1 = time.time()
        for t in tasks:
            t.start()
        for t in tasks:
            t.join()
        while True:
            if num == 0:
                break
            rlt = data_queue.get(timeout=2)
            if rlt:
                num -= 1
                if not rlt.success:
                    continue
                for k, v in rlt.content.items():
                    c_id = v.get('id')
                    if c_id:
                        all_containers[c_id] = v
            else:
                time.sleep(0.01)

        Log(3, "clu_pods all cost:{}".format(time.time() - t1))

        # 获取一个集群的所有Ready pod
        rlt = KubeClientMgr.instance().all_pods(self.clu_name)
        if not rlt.success:
            Log(1, "get all_pods error:{}".format(rlt.message))
            return
        Log(3, "all_pods... cluster:{}, len(pods):{}".format(self.clu_name, len(rlt.content)))
        deploy_pods = {}
        for pod in rlt.content:
            time.sleep(0.001)
            ns = pod.get('metadata', {}).get('namespace')
            name = pod.get('metadata', {}).get('annotations', {}).get('com.appsoar.ufleet.deploy', '')
            d_p = '%s-%s' % (ns, name)
            dep = self.deploys.get(d_p)
            if dep:
                Log(4, 'found a deployment:{}, pod:{}'.format(d_p, pod.get('metadata').get('name')))
                pod_rep = {'resource': pod.get('spec', {}).get('containers', [])}
                for i in pod.get('status', {}).get('containerStatuses', []):
                    container_id = i.get('containerID', '')
                    if not container_id:
                        Log(4, "not found the containerID from pod:{}".format(container_id))
                        continue
                    container_id = container_id.split('//')[1] if '//' in container_id else container_id
                    c = all_containers.pop(container_id, {})
                    if c:
                        pause_id = c.get('labels', {}).get('io.kubernetes.sandbox.id', '')
                        pod_rep.setdefault('container_data', []).append(c)
                        pause_data = all_containers.get(pause_id, {})
                        if pause_data:
                            pod_rep.setdefault('pause_data', pause_data)
                        else:
                            Log(2, "not found the pause_data:{}".format(pause_data))
                        deploy_pods.setdefault(d_p, {}).setdefault('pods_list', []).append(pod_rep)
                        deploy_pods.setdefault(d_p, {}).setdefault('hpa', dep)

                    else:
                        Log(2,
                            "not found the container:{}, host:{}".format(container_id, pod.get('status').get('hostIP')))

        Log(3, "deploy_pods all cost:{}, cluster:{}".format(time.time() - t1, self.clu_name))
        return deploy_pods

    def run(self):
        t1 = time.time()

        # 将deploy、pod、container关联起来
        deploy_pods = self.clu_pods()
        if not deploy_pods:
            Log(3, "elastic deploy_pods is None. cluster:{}".format(self.clu_name))
            self.status = 1
            return
        Log(4, "elastic deploy_pods.keys():{}, cluster:{}".format(deploy_pods.keys(), self.clu_name))

        Log(3, "elastic running ......... cluster:{}, run cost:{}".format(self.clu_name, time.time() - t1))

        # 对每个pod进行分析
        for dep_name, dep_v in deploy_pods.items():
            self.anly_one_deploy(dep_v)

        self.status = 1

        Log(3, "elastic running finished. cluster:{}, run cost:{}".format(self.clu_name, time.time() - t1))

    def is_finished(self):
        return self.status > 0


class ElasticMgr(object):
    """
    # 这个类用来弹性伸缩
    """

    def __init__(self):
        """
        Constructor
        """
        super(ElasticMgr, self).__init__()
        self.task_queue = Queue.Queue()
        self.threads = []
        self.__init_thread_pool(5, 'Elastic check')

    def __init_thread_pool(self, thread_num, schedule_name):
        while thread_num:
            name = "%s_%s" % (schedule_name, thread_num)
            thread_num -= 1
            Factory(self.task_queue, name)

    def start(self, s_time=10):
        try:
            while True:
                Log(3, "elastic #start start at:{}".format(datetime.datetime.now()))
                t1 = datetime.datetime.now()
                self.timeout()
                Log(3, 'elastic all cost:{}'.format(datetime.datetime.now() - t1))
                time.sleep(s_time)
        except Exception as e:
            PrintStack()
            return

    def timeout_before(self):
        # all ns's all deployments
        deploys = {}
        all_deploys = DeployClient.instance().all_deploy()
        if not all_deploys:
            return
        Log(4, 'all_deploys:{}'.format(all_deploys))
        for deploy in all_deploys:
            ns = deploy.get('workspace')
            name = deploy.get('name')
            if ns and name:
                deploys.setdefault('%s-%s' % (ns, name), deploy)

        clu_nodes = self.get_clu_nodes()
        if not clu_nodes:
            return

        for clu_name, nodes in clu_nodes.items():
            if deploys and nodes:
                self.create_task(clu_name, nodes, deploys)

    def timeout(self):
        Log(3, "elastic timeout start at:{}".format(datetime.datetime.now()))
        if not Clusterdb.instance().ismaster():
            Log(3, "elastic this node is not master")
            return

        if self.task_queue.qsize():
            Log(3, "elastic the queue is not None. queue size:{}".format(self.task_queue.qsize()))
            return

        try:
            self.timeout_before()
            Log(3, "elastic create task done at:{}".format(datetime.datetime.now()))
            return None
        except Exception as e:
            PrintStack()
            Log(3, "elastic timeout:{}".format(e.message))
            return None
        except KeyboardInterrupt:
            Log(3, "elastic killed")
            return None

    def create_task(self, clu_name, nodes, deploys):
        Log(4, "elastid create task:{}".format(deploys))
        self.task_queue.put(DeployAnly(clu_name, nodes, deploys))

    def get_clu_nodes(self):
        """
        :return:
        """
        rlt = CluNodedb.instance().get_clu_node()
        if rlt.success:
            return rlt.content
        else:
            Log(1, "get clu nodes error:{}, elastic exited.".format(rlt.message))
            return None
