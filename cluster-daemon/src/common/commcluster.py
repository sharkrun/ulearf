# -*- coding: utf-8 -*-
# cluster模块通用的函数方法
from common.util import Result
import requests
from frame.logger import Log
import datetime
import time
# from core.kubeclientmgr import KubeClientMgr
import imp
from core.cadvisor import Cadvisor


def utc2local(utc_st):
    """UTC时间转本地时间（+8:00）"""
    now_stamp = time.time()
    local_time = datetime.datetime.fromtimestamp(now_stamp)
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st


def my_request(url, method, timeout, data=None, headers=None):
    """
    :param url:
    :param method:
    :param timeout:
    :param data:
    :return:
    headers={"content-type": "application/json", "token": "1234567890987654321"}
    """
    try:
        if method == 'GET':
            r = requests.get(url=url, headers=headers, timeout=timeout)
            return Result(r)
        elif method == 'DELETE':
            r = requests.delete(url, timeout=timeout)
            return Result(r)
        elif method == 'POST':
            r = requests.post(url=url, data=data, headers=headers, timeout=timeout)
            return Result(r)
        elif method == 'PUT':
            r = requests.put(url=url, headers=headers, timeout=timeout)
            return Result(r)
        else:
            return Result('', 400, 'method error')
    except requests.exceptions.RequestException as e:
        Log(1, "my_request error:{}, url:{}".format(e.message, url))
        return Result('', msg=str(e), result=500)


def syn_pods_num(j, node_ip):
    pod_num = 0
    for pod in j:
        if pod.get('status', {}).get('hostIP') == node_ip:
            conditions = pod.get('status', {}).get('conditions', [])
            for k in conditions:
                if k.get('type', '') == 'Ready':
                    status = k.get('status', '')
                    if status == 'True':
                        pod_num += 1
                    break
    return pod_num


def component_statuses(self):
    """
    #~ kubectl get componentstatus
    检查master的状态  scheduler controller-manager etcd-0
    :param client:
    :param clu_name:
    :return:
    """
    rlt = self.client.clu_status()
    s_info = []
    if rlt.success:
        for i in rlt.content:
            name = i.get('metadata', {}).get('name')
            if 'etcd' in name:
                continue
            for j in i.get('conditions'):
                if j.get('type') == 'Healthy':
                    s_info.append({'name': name, 'status': j.get('status'), 'message': j.get('message')})
        s = list(set([i['status'] for i in s_info]))
        message = [i['message'] for i in s_info]

        if s == ['True']:
            return {'status': 'running', 'message': ''}
        else:
            return {'status': 'error', 'message': ';'.join(message)}
    else:
        Log(3, "get cluster components tatuses error:{}".format(rlt.message))
        return None


def syn_nodeinfo(node_one, j, m_s_info):
    """
    :param node_one: {}
    :param j: {}
    :return:{'node_one': dic, 'change_num': int}
    """
    # Log(4, "j:{}".format(j))
    t11 = datetime.datetime.now()
    update_node = {}
    # 主机内存
    name = j.get('metadata', {}).get('name', '')
    if node_one['name'] != name:
        update_node['name'] = name

    # 主机cpu
    cpu = j.get('status', {}).get('capacity', {}).get('cpu', '')
    if node_one['cpu'] != cpu:
        update_node['cpu'] = cpu

    # 主机添加时间
    t1 = j.get('metadata', {}).get('creationTimestamp', '')
    if t1:
        imp.acquire_lock()
        t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
        imp.release_lock()
        t3 = utc2local(t2)
        add_date = datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")
        if node_one['datetime'] != add_date:
            update_node['datetime'] = add_date

    # 主机内存
    mem = j.get('status', {}).get('capacity', {}).get('memory', '')[:-2]
    if mem:
        mem = str(round(float(mem) / (1024 * 1024), 3)) + 'GB'
        if node_one['memory'] != mem:
            update_node['memory'] = mem

    # 主机的维护模式
    docker_version = j.get('status', {}).get('nodeInfo', {}).get(
        'containerRuntimeVersion', '')
    if node_one['docker_version'] != docker_version:
        update_node['docker_version'] = docker_version
    true = True
    false = False
    unschede = j.get('spec', {}).get('unschedulable', '')

    if node_one['unschedulable'] != unschede:
        update_node['unschedulable'] = unschede

    # 主机状态
    status = node_one['status']
    status_message = ''
    conditions = j.get('status', {}).get('conditions', [])
    # if node_one['type'] == 'node':
    for k in conditions:
        if k.get('type', {}) == 'Ready':
            status1 = k.get('status', '')
            status_message = k.get('message', '')
            if status1 == 'True':
                status = 'running'
            else:
                if 'network plugin is not ready' in status_message:
                    Log(4, "network plugin is not ready&&&&:{}".format(node_one['ip']))
                    status = 'running'
                else:
                    status = 'error'

            break
    Log(4, 'node[{}] old_status:{}, new_status:{}'.format(node_one['ip'], node_one['status'], status))
    if m_s_info:
        if any([m_s_info.get('status') == 'error', status == 'error']):
            a_status = 'error'
            a_message = ','.join([status_message, m_s_info.get('message', '')])
        else:
            a_status = 'running'
            a_message = ''
    else:
        a_status = status
        a_message = status_message

    if node_one['status'] != a_status:
        update_node['status'] = a_status
        update_node['message'] = a_message

    # 主机标签
    labels = j.get('metadata', {}).get('labels', {})
    for label_key in labels.keys():
        if 'kubernetes' in label_key:
            del labels[label_key]
    if node_one['label'] != labels:
        update_node['label'] = labels

    # 磁盘信息
    cadvisor_cli = Cadvisor(node_one['ip'], '/api/v1.3/machine')
    rlt = cadvisor_cli.get()
    if rlt.success:
        filesystems = rlt.content.get('filesystems', [])
        disk_num = 0
        for f in filesystems:
            disk_num += f.get('capacity', 0)
        if node_one['disk'] != str(round(disk_num / (1024 ** 3), 3)) + 'GB':
            update_node['disk'] = str(round(disk_num / (1024 ** 3), 3)) + 'GB'
    else:
        Log(1, "syn node:{} disk info error:{}".format(node_one['ip'], rlt.message))

    Log(4, "syn_nodeinfo cluster:{},node:{}, time:{}".format(node_one.get('cluster_name'), node_one.get('name'),
                                                             datetime.datetime.now() - t11))
    return update_node
