# -*- coding: utf8 -*-

"""
所有模块的数据类型
"""
from common.util import UtcDate
import json


# /ufleet/cluster/clustermanages/<cluster_name>/cluster_info  {}  集群基本信息  &不能改
# /ufleet/cluster/clustermanages/<cluster_name>/auth_info {}      集群认证信息  &不能改
# /ufleet/cluster/clustermanages/<cluster_name>/member []         集群成员
# /ufleet/cluster/clustermanages/<cluster_name>/apply_num []      集群应用个数

# /ufleet/cluster/clusternodes/<cluster_name>/<host_name> {}      主机详情

# /ufleet/cluster/masternodedir/<host_name>  {}                   保存所有添加主机的用户名和密码  &不能改

# /ufleet/cluster/workspacegroup/<group_name>  {}                 workspacegroup信息  &不能改

# /ufleet/cluster/workspace/<worksapce_name> {}                   workspace详情  &不能该

# /ufleet/cluster/nodemonitor/<host_name> {}                      主机的监控信息

# /ufleet/cluster/network/<cluster_naem>/<id> {}                  集群子网列表


def clu_struct(cluster_info):
    """
    集群信息
    :return:
        默认  {
            'auth_way': 'ca_auth', 认证方式
            'creater': '', 创建者
            'create_time': UtcDate(), 当前日期
            'cluster_name': '', 集群名称
            'cluster_type': 'create', 'create' or 'accept' 创建类型
            'type': '' , 'one': 单机   or  'ha': 高可用
         }
    """
    rlt = {
        'auth_way': 'ca_auth',
        'creater': '',
        'create_time': UtcDate(),
        'cluster_name': '',
        'cluster_type': '',
        'type': ''
    }
    if isinstance(cluster_info, dict):
        for k, v in cluster_info.items():
            if k in rlt:
                rlt[k] = v
        rlt['cluster_type'] = cluster_info['create_way']
    return rlt


def node_struct(cluster_name, ip, _type, creater):
    """
    主机的结构体
    status: node status
    m_status: master status
    the master host has both of the status
    :return:
    """
    node = {
        'cluster_name': cluster_name,
        'name': '',
        'system': '',
        'docker_version': '',
        'status': 'pending',
        'type': _type,
        'pod_num': 0,
        'ip': ip,
        'cpu': '',
        'memory': '',
        'label': '',
        'disk': '',
        'unschedulable': '',
        'slave': '',
        'is_eviction': 0,
        'evction_status': '',  # 应用迁移状态
        'datetime': UtcDate(),
        'creater': creater
    }
    if _type == 'master':
        node.update({'m_status': 'pending', 'm_message': ''})
    return node


def masternode_struct(creater, cluster_name, node_type, host_ip, port, host_name, username, userpwd, prikey, pripwd):
    """
    masternodedir目录
    :return:
    """
    return {
        'creater': creater,
        'datetime': UtcDate(),
        'cluster_name': cluster_name,
        'node_type': node_type,  # Master
        'host_ip': host_ip,
        'port': port,
        'host_name': host_name,
        'username': username,
        'userpwd': userpwd,
        'prikey': prikey,
        'prikeypwd': pripwd
    }


def auth_info_struct(cluster_info):
    """
    集群认证信息结构体
    :return:
    """
    if cluster_info.get('auth_way', '') == 'http':
        auth_way = 'http'
    else:
        auth_way = 'ca_auth'

    return {
        'authway': auth_way,
        'clustername': cluster_info.get('cluster_name', ''),
        'hostip': cluster_info.get('addr', '').split(':')[0],
        'cacert': cluster_info.get('cacerts', ''),
        'apiservercerts': cluster_info.get('apiservercerts', ''),
        'apiserverkey': cluster_info.get('apiserverkey', ''),
    }


def workspace_struce(w, creater):
    """
    返回workspace数据结构
    :param w:
    :return:
    """
    return {
        'creater': creater,
        'datetime': UtcDate(),
        'group': w.get('workspacegroup_name'),
        'cluster_name': w.get('cluster_name'),
        'name': w.get('workspace_name'),
        'isolate': '0',
        'cpu': w.get('resource_cpu'),
        'mem': w.get('resource_mem'),
        'pod_cpu_min': w.get('pod_cpu_min'),
        'pod_cpu_max': w.get('pod_cpu_max'),
        'pod_mem_min': w.get('pod_mem_min'),
        'pod_mem_max': w.get('pod_mem_max'),
        'c_cpu_default': w.get('c_cpu_default'),  # cpu默认最大值
        'c_cpu_default_min': w.get('c_cpu_default_min'),  # cpu默认最小值
        'c_mem_default': w.get('c_mem_default'),  # mem默认最大值
        'c_mem_default_min': w.get('c_mem_default_min'),  # mem默认最小值
        'c_cpu_min': w.get('c_cpu_min'),
        'c_cpu_max': w.get('c_cpu_max'),
        'c_mem_min': w.get('c_mem_min'),
        'c_mem_max': w.get('c_mem_max')
    }


def network_pool(cluster_name, subip, subnet_mask, creater, is_show, is_ipip, is_nat, status, fa_ip, subnet_id):
    """
    /ufleet/cluster/network/<cluster_name>/<father-ip>/<subnetip>  {'cluster_name': '', 'subnet': '', 'ipip': '', 'net': '', 'creater':''
    , 'index_id': int}
    设置集群网络池
    :param d:
    :param creater:
    :return:
    """
    return {
        'cluster_name': cluster_name,  # str  e.g:'clusterA'
        'fa_ip': fa_ip,
        'subnet': subip + '/' + str(subnet_mask),  # str  e.g: '192.168.5.6'
        'status': status,  # 状态 1:空闲  0:已经被分配
        'ipip': is_ipip,  # IPIP模式  1:开启  # 0:关闭
        'nat': is_nat,  # NATm模式 1:开启  # 0:关闭
        'is_show': is_show,  # 是否能被分配使用  0:不能被使用  1:允许被分配使用
        'creater': creater,
        'create_time': UtcDate(),
        'key': subnet_id,
        'workspace': '',
        'group': ''
    }


def configmap_struct(data):
    """
    /ufleet/cluster/configmap/<workspace>/<configmap_name>+<version>  {}
    :param data:
    :return:
    """
    return {
        "name": data.get('name', ''),  # 配置名称
        "version": data.get('version', ''),  # 版本
        "describe": data.get('describe', ''),  # 描述
        "content": """{}""".format(data.get('content', '')),  # 内容
        "conf_keys": data.get('conf_keys'),  # configmap的key列表
        "group": data.get('group', ''),
        "workspace": data.get('workspace', ''),  # worksapce名称
        "creater": data.get('creater', ''),  # 创建者
        "create_time": UtcDate()  # 创建时间
    }


def clusterrole(data):
    return {
        "name": data.get('name'),
        "clu_name": data.get('cluster_name'),
        "content": data.get('content'),
        "creater": data.get('creater', ''),
        "create_time": UtcDate()
    }