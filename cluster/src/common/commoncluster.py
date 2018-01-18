# -*- coding: utf-8 -*-
# cluster模块通用的函数方法
from common.util import Result
import requests
from frame.logger import Log
import datetime
import time
# from core.kubeclientmgr import KubeClientMgr
from core.cadvisor import Cadvisor
import imp


def utc2local(utc_st):
    """UTC时间转本地时间（+8:00）"""
    now_stamp = time.time()
    local_time = datetime.datetime.fromtimestamp(now_stamp)
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st


def requestexcept(actual_do):
    def f(*args, **kwargs):
        try:
            return actual_do(*args, **kwargs)
        except Exception as e:
            Log(1, "{0} error:{1}".format(actual_do.__name__, e.message))
            return Result('', 400, msg=e.message, code=400)

    return f

def syn_nodeinfo(node_one, j):
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

    unschede = j.get('spec', {}).get('unschedulable', '')

    if node_one['unschedulable'] != unschede:
        update_node['unschedulable'] = unschede

    # # 检查主机作为master的状态
    # if node_one['type'] == 'master':

    # 主机节点状态
    status = node_one['status']
    status_message = ''
    conditions = j.get('status', {}).get('conditions', [])
    Log(4, "node status conditions:{}".format(conditions))
    for k in conditions:
        if k.get('type', {}) == 'Ready':
            status1 = k.get('status', '')
            status_message = k.get('message', '')
            if status1 == 'True':
                status = 'running'
            else:
                Log(4, "network plugin:{}".format(status_message))
                if 'network plugin is not ready' in status_message:
                    Log(4, "network plugin is not ready&&&&:{}".format(node_one['ip']))
                    status = 'running'
                else:
                    status = 'error'

            break
    Log(3, 'node[{}] old_status:{}, new_status:{}'.format(node_one['ip'], node_one['status'], status))
    if node_one['status'] != status:
        update_node['status'] = status
        update_node['message'] = status_message

    # 主机标签
    labels = j.get('metadata', {}).get('labels', {})
    for label_key in labels.keys():
        if 'kubernetes' in label_key:
            del labels[label_key]
    if node_one['label'] != labels:
        update_node['label'] = labels

    # 磁盘信息
    # url = 'http://' + node_one['ip'] + ':4194/api/v1.3/machine'
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

    Log(3, "syn_nodeinfo cluster:{},node:{}, time:{}".format(node_one.get('cluster_name'), node_one.get('name'), datetime.datetime.now() - t11))
    return update_node
