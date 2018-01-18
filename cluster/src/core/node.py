# -*- coding: utf-8 -*-
import datetime
from common.util import utc2local
from etcddb.kubernetes.nodemgr import CluNodedb
from frame.logger import Log
from cadvisor import Cadvisor


class Node(object):
    """
    """

    def __init__(self, info=None):
        """
        :param info:
        """
        self.cluster_name = ''
        self.name = ''
        self.system = ''
        self.docker_version = ''
        self.status = ''
        self.type = 'node'
        self.pod_num = 0
        self.ip = ''
        self.cpu = ''
        self.memory = ''
        self.label = ''
        self.disk = ''
        self.unschedulable = ''
        self.slave = ''
        self.datetime = ''

        if isinstance(info, dict):
            self.__dict__.update(info)

    def __parse_status(self, node_info):
        status = ''
        conditions = node_info.get('status', {}).get('conditions', [])
        for k in conditions:
            if k.get('type', {}) == 'Ready':
                status1 = k.get('status', '')
                if status1 == 'True':
                    status = 'running'
                else:
                    status = 'error'
                break
        return status

    def __parse_memory(self, node_info):
        return str(round(float(node_info.get('status', {}).get('capacity', {}).get('memory', '')[:-2]) / (1024 * 1024),
                         3)) + 'GB'

    def __parse_lables(self, node_info):
        labels = node_info.get('metadata', {}).get('labels', {})
        labels.pop('kubernetes.io/hostname', None)
        labels.pop('beta.kubernetes.io/os', None)
        labels.pop('beta.kubernetes.io/arch', None)
        return labels

    def __parse_create_time(self, node_info):
        t1 = node_info.get('metadata', {}).get('creationTimestamp', '')
        t2 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%SZ')
        t3 = utc2local(t2)
        return datetime.datetime.strftime(t3, "%Y-%m-%d %H:%M:%S")

    def __parse_node_ip(self, node_info):
        address = node_info.get('status', {}).get('addresses', [])
        for add in address:
            if 'InternalIP' == add.get('type', ''):
                return add.get('address', '')
        return ''

    def apply(self, node_info):
        self.ip = self.__parse_node_ip(node_info)
        self.name = node_info.get('metadata', {}).get('name', '')
        self.system = ''
        self.docker_version = node_info.get('status', {}).get('nodeInfo', {}).get('containerRuntimeVersion', '')
        self.status = self.__parse_status(node_info)
        self.type = 'node'
        self.pod_num = 0
        self.cpu = node_info.get('status', {}).get('capacity', {}).get('cpu', '')
        self.memory = self.__parse_memory(node_info)
        self.label = self.__parse_lables(node_info)
        self.disk = self.get_disk_info()
        self.unschedulable = node_info.get('spec', {}).get('unschedulable', '')
        self.slave = ''
        self.datetime = self.__parse_create_time(node_info)
        return self

    def snap(self):
        return {
            'cluster_name': self.cluster_name,
            'name': self.name,
            'system': self.system,
            'docker_version': self.docker_version,
            'status': self.status,
            'type': self.type,
            'pod_num': self.pod_num,
            'ip': self.ip,
            'cpu': self.cpu,
            'memory': self.memory,
            'label': self.label,
            'disk': self.disk,
            'unschedulable': self.unschedulable,
            'slave': self.slave,
            'datetime': self.datetime
        }

    def save(self):
        data = self.snap()
        host_id = self.ip.replace('.', '-')

        rlt = CluNodedb.instance().create_node(self.cluster_name, host_id, data)
        if not rlt.success:
            Log(1, 'Node.save node[%s][%s]fail,as[%s]' % (self.cluster_name, host_id, rlt.message))

        return rlt

    def get_disk_info(self):
        cadvisor_cli = Cadvisor(self.ip, '/api/v1.3/machine')
        rlt = cadvisor_cli.get()
        if rlt.success:
            filesystems = rlt.content.get('filesystems', [])
            disk_num = 0
            for f in filesystems:
                disk_num += f.get('capacity', 0)
            return str(round(disk_num / (1024 ** 3), 3)) + 'GB'
        else:
            Log(1, "node get_disk_info error:{}".format(rlt.message))
            return ''
        # try:
        #     disk_data = requests.get('http://' + self.ip + ':4194/api/v1.3/machine', timeout=2)
        # except requests.exceptions.RequestException:
        #     return ''
        #
        # if disk_data.status_code == 200:
        #     filesystems = disk_data.json().get('filesystems', [])
        #     disk_num = 0
        #     for f in filesystems:
        #         disk_num += f.get('capacity', 0)
        #
        #     return str(round(disk_num / (1024 ** 3), 3)) + 'GB'
        # return ''
