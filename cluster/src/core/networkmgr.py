# -*- coding: utf-8 -*-
import threading
from common.guard import LockGuard
from common.util import NowMilli
from etcddb.networkmgr import Networkdb
from common.datatype import network_pool
from common.util import Result
from core.errcode import IPIP_EXISTED_CLUSTER, CLUSTER_NOT_EXISTED, SUBNET_IPIS_USED
from etcddb.kubernetes.clustermgr import Clusterdb
from IPy import IP
from frame.auditlogger import WebLog
from frame.logger import Log
import uuid
from frame.ipcalc import Network
import math
from core.remoteclient import RemoteParam
import sys
from etcddb.kubernetes.nodemgr import CluNodedb
import os
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from core.errcode import ETCD_RECORD_NOT_EXIST_ERR
from etcddb.kubernetes.mastermgr import Masterdb


class SubnetMgr(Network):
    def __init__(self, ip, zone_id=None):
        self.zone_id = zone_id
        super(SubnetMgr, self).__init__(ip, None)

    def assign_new_subnet(self, vlan_id, n):
        """
        :param vlan_id: 主机位数
        :param n:
        :return:
        """
        try:
            ip = self.host_index(2 ** vlan_id * n).dq
            return Result(ip)
        except ValueError as e:
            return Result('', 400, e.message)


class NetworkMgr(object):
    """
    网络设置模块
    """
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.networkdb = Networkdb.instance()
        self.expiry_time = 0
        self.loaddata()

    def reload(self, flush=0):
        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def loaddata(self):
        self.expiry_time = NowMilli() + 30000

        clu_node = {}
        rlt = CluNodedb.instance().read_clunode_map()
        if not rlt.success:
            return Result('', rlt.result, rlt.message, 500)
        if rlt.success:
            for k, v in rlt.content.items():
                sp_key = k.split('/')
                if sp_key[-3] == 'clusternodes':
                    clu_node.setdefault(sp_key[-2], []).append(v)

        for k, v in clu_node.items():
            master_num = 0
            run_num = 0
            for i in v:
                if i['type'] == 'master':
                    master_num += 1
                    if i['status'] != 'running':
                        run_num += 1
            # 单集群判断集群状态
            if master_num == 1 and run_num == 1:
                clu_node.pop(k)
            # ha集群判断集群状态
            if master_num == 3 and (run_num == 2 or run_num == 3):
                clu_node.pop(k)

        all_ippool = []
        for i in clu_node.keys():
            one_ippool = {
                'key': str(uuid.uuid1()),
                'pool_name': '',
                'cluster_name': '',
                'creater': '',
                'subnetnum': '',
                'subnet': []
            }
            rlt_net = Networkdb.instance().key_value_map(i)
            if not rlt_net.success:
                continue
            subnet_num = 0
            # fa_ip = set()
            d = {}
            for k, v in rlt_net.content.items():
                d.setdefault(v['fa_ip'], []).append(v)
                subnet_num += 1
            for k, v in d.items():
                sub = {'subnet': k, 'children': v, 'creater': v[0].get('creater', ''),
                       'create_time': v[0].get('create_time', ''), 'key': str(uuid.uuid1()), 'cluster_name': i}
                one_ippool['subnet'].append(sub)
            one_ippool['pool_name'] = i
            one_ippool['cluster_name'] = i
            one_ippool['subnetnum'] = subnet_num
            all_ippool.append(one_ippool)

        self.__store = all_ippool

    def get_config_dir(self):
        if hasattr(sys, "_MEIPASS"):
            base_path = os.environ.get('CLUSTER_WORK_ROOT', '/opt/cluster')
            return os.path.join(base_path, 'conf')
        else:
            base_path = os.path.abspath(".")
            return os.path.join(base_path, 'frame', 'conf')

    def create_subnet(self, data):
        """
        创建网络池
        :param data: ip: str   netmask: int
        :return:
        """
        cluster_name = data.get('cluster_name', '')
        # 检查集群是否存在
        if not Clusterdb.instance().clu_is_exist(cluster_name):
            return Result('', CLUSTER_NOT_EXISTED, 'the cluster:{} not existed'.format(cluster_name), 400)

        rlt = self.networkdb.get_subnet_by_clu(cluster_name)
        if not rlt.success:
            return rlt
        clu_all_sub = rlt.content

        subnet = data.get('subnet', '')  # 被划分的网段
        subnet_num = data.get('subnet_num')  # 要划分的子网个数
        subnet_net = subnet.split('/')[0]
        mask_bit = int(subnet.split('/')[-1])  # 掩码位数
        net_log = math.log(subnet_num, 2)  # 网络位需要向主机位借的位数

        # 检查子网是否已经被划分过
        fa_ip = IP(subnet_net).make_net(mask_bit).strNormal(1)
        if self.networkdb.is_fa_ip_exist(cluster_name, fa_ip.split('/')[0]):
            return Result('', IPIP_EXISTED_CLUSTER, 'the subnet has been divided')

        if 2 ** int(net_log) == subnet_num:
            net_log = int(net_log)
        else:
            net_log = int(net_log) + 1
        new_mask = mask_bit + net_log  # 新子网的掩码位数
        # IP pool size is too small (min /26) for use with Calico IPAM
        if new_mask > 26:
            return Result('', 400, 'IP pool size is too small (min /26) for use with Calico IPAM', 400)
        subnet_num_max = 2 ** (32 - mask_bit)
        if subnet_num > subnet_num_max:
            return Result('', 400, 'the max number that net can be divided to subnet is:{}'.format(subnet_num_max))
        sub = SubnetMgr(str(subnet))

        net_list = []
        for i in range(2**net_log):
            new_subnet = sub.assign_new_subnet(32 - new_mask, i)
            if not new_subnet.success:
                return new_subnet
            subnet_id = str(uuid.uuid1())
            # k = data['cluster_name'] + '/' + fa_ip.split('/')[0] + '/' + subnet_id
            net_ = network_pool(cluster_name, new_subnet.content, new_mask, data.get('creater'), 1,
                                data.get('ipip'),
                                data.get('nat'), 1, fa_ip, subnet_id)
            # 判断新的子网是否被创建过
            if net_['subnet'] not in clu_all_sub:
                net_list.append(net_)

        # 为空表示该子网已经被划分过
        if not net_list:
            return Result('', 400, IPIP_EXISTED_CLUSTER, 400)
        # 保存到etcd
        pool_data = {}
        for i in net_list:
            k = data['cluster_name'] + '/' + fa_ip.split('/')[0] + '/' + i['key']
            pool_data[k] = i

        rlt = self.networkdb.save_clu_ippool(pool_data)
        if not rlt.success:
            return rlt
        WebLog(3, u'创建', u"集群[{}]的网络池[{}]".format(data['cluster_name'], fa_ip), data['creater'])
        self.reload(flush=1)
        return Result('')

    def get_ippool(self):
        """
        获取所有的网络池
        :return:
        """
        self.reload()
        return Result(self.__store)

    def delelte_subnet(self, kwargs):
        """
        删除集群的某个子网集合
        :param kwargs: subnet: 子网ip   cluster_name
        :return:
        """
        # 检查集群是否存在
        cluster_name = kwargs.get('cluster_name')
        fa_ip = kwargs.get('fa_ip', '')
        ip = fa_ip.split('/')[0]
        if not Clusterdb.instance().clu_is_exist(cluster_name):
            return Result('', CLUSTER_NOT_EXISTED, '', 400)
        creater = kwargs.get('passport', {}).get('username', '')

        # 检查子网是否有被使用
        all_net = self.networkdb.subnet_value_list(cluster_name + '/' + ip)
        if not all_net.success:
            return all_net
        for i in all_net.content:
            if i['status'] == 0:
                return Result('', SUBNET_IPIS_USED, '')

        # 删除etcd中数据
        rlt = self.networkdb.del_net(cluster_name, ip)
        if not rlt.success:
            return rlt
        self.reload(flush=1)
        WebLog(3, u'删除', u"集群:[{}]的网络池:[{}]".format(cluster_name, fa_ip), creater)

        # 删除主机上的网络池
        rlt = CluNodedb.instance().read_node_list(cluster_name)
        if not rlt.success:
            return rlt
        master_ip = ''
        for i in rlt.content:
            if i.get('type') == 'master':
                master_ip = i.get('ip')
                break
        rlt = Masterdb.instance().read_master(master_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        con = rlt.content
        username = con.get('username', None)
        passwd = con.get('userpwd', None)
        prikey = con.get('prikey', None)
        prikeypwd = con.get('prikeypwd', None)
        port = int(con.get('port', 22))
        remot = RemoteParam(master_ip, port, username, passwd, prikey, prikeypwd)
        rlt = remot.create_sshclient()
        if not rlt.success:
            return rlt
        for i in all_net.content:
            if not i.get('workspace'):
                continue
            ippool_command = "ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl delete ippool {}".format(i['subnet'])

            rlt = remot.exec_command(ippool_command)
            if not rlt.success or 'Successfully' not in rlt.content[0]:
                continue
        remot.close()
        return Result('')

    def update_subip(self, data):
        """
        更新设置子网
        :param kwargs:
        :return:
        """
        key_list = data.keys()
        if 'fa_ip' in key_list and 'key' in key_list and 'cluster_name' in key_list:
            fa_ip = data.pop('fa_ip')
            key = data.pop('key')
            cluster_name = data.pop('cluster_name')
        else:
            return Result('', 400, 'param error', 400)

        # 检查子网是否被分配， 如果被分配，则不能修改is_show状态
        rlt = self.networkdb.read_subnet(cluster_name, fa_ip.split('/')[0], key)
        if not rlt.success:
            return rlt
        if rlt.content.get('status') == 0:
            return Result('', 400, '')

        # 检查集群是否存在
        if not Clusterdb.instance().clu_is_exist(cluster_name):
            return Result('', CLUSTER_NOT_EXISTED, '', 400)

        rlt = self.networkdb.update_subnet(cluster_name, fa_ip.split('/')[0], key, data)
        if not rlt.success:
            return rlt
        self.reload(flush=1)
        return Result('')

    def get_ippool_clu(self, cluster_name, status=0, offset=0, limit=None):
        """
        获取一个集群的所有子网：  require=0被分配  require=1:未被分配
        :param cluster_name:
        :return:
        """
        self.reload()
        if limit:
            limit = int(limit)

        # 检查集群是否存在
        if not Clusterdb.instance().clu_is_exist(cluster_name):
            return Result('', CLUSTER_NOT_EXISTED, '', 400)

        r_data = []
        subnet_list = []
        for i in self.__store:
            if i['cluster_name'] == cluster_name:
                for j in i['subnet']:
                    subnet_list.extend(j['children'])
        for i in subnet_list:
            if i['is_show'] == 1 and i['status'] == status:
                r_data.append(i)

        return Result(r_data[offset:limit])

    def get_subnet_by_ws(self, workspace):
        """
        通过workspace获取一个网段：
        :param cluster_name:
        :return:
        """
        self.reload()

        subnet_list = []
        for i in self.__store:
            for j in i['subnet']:
                subnet_list.extend(j['children'])
        for i in subnet_list:
            if i['is_show'] == 1 and i['status'] == 0 and i['workspace'] == workspace:
                return Result(i)

        return Result('')

    def set_workspace(self, data):
        """
        指派工作区
        :param data:
        :return:
        """
        workspace = data.get('workspace')
        if not workspace:
            return Result('', 400, 'param error', 400)
        # 检查工作区是否存在
        if not WorkSpacedb.instance().workspace_is_exist(workspace):
            return Result('', ETCD_RECORD_NOT_EXIST_ERR, '', 400)

        # 检查子网是否存在
        rlt = self.networkdb.read_subnet(data.get('cluster_name'), data.get('fa_ip').split('/')[0], data.get('key'))
        if not rlt.success:
            return rlt
        subnet_info = rlt.content

        # 先检查子网是否被指派过
        if rlt.content.get('status') == 0:
            return Result('', 400, 'the subnet has been assigned')

        # 检查工作区是否被指派过
        rlt = self.get_ippool_clu(data.get('cluster_name'))
        if not rlt.success:
            return rlt
        for i in rlt.content:
            if i.get('workspace') == workspace:
                return Result('', 400, 'the workspace has been assigned', 400)

        # 连接主机  指派工作区
        rlt = CluNodedb.instance().read_node_list(data['cluster_name'])
        if not rlt.success:
            return rlt
        master_ip = ''
        for i in rlt.content:
            if i.get('type') == 'master':
                master_ip = i.get('ip')
                break

        rlt = Masterdb.instance().read_master(master_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        con = rlt.content
        username = con.get('username', None)
        passwd = con.get('userpwd', None)
        prikey = con.get('prikey', None)
        prikeypwd = con.get('prikeypwd', None)
        port = int(con.get('port', 22))
        remot = RemoteParam(master_ip, port, username, passwd, prikey, prikeypwd)
        rlt = remot.create_sshclient()
        if not rlt.success:
            return rlt

        # 执行创建子网命令
        cidr = subnet_info['subnet'].split('/')[0] + '/' + subnet_info['subnet'].split('/')[1]
        ipip = 'true' if subnet_info['ipip'] else 'false'
        nat = 'true' if subnet_info['nat'] else 'false'
        ippool_content = """
        apiVersion: v1
        kind: ipPool
        metadata:
          cidr: {}
        spec:
          ipip:
            enabled: {}
          nat-outgoing: {}""".format(cidr, ipip, nat)
        ipp_command = "cat << EOF | ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl apply -f - {}\nEOF".format(ippool_content)

        rlt = remot.exec_command(ipp_command)
        Log(3, "set_workspace ssh exec command:{}, {}".format(ipp_command, rlt.content))
        remot.close()
        # 对于已经存在的ippool，忽略
        if not rlt.success or ('Successfully' not in rlt.content[0] and 'resource already exists' not in rlt.content[0]):
            return Result('', 400, rlt.content, 400)

        # 更新etcd
        group_name = ''
        rlt = WorkSpacedb.instance().read_workspace(workspace)
        if rlt.success:
            group_name = rlt.content.get('group', '')

        rlt = self.networkdb.update_subnet(data.get('cluster_name'), data.get('fa_ip').split('/')[0], data.get('key'),
                                           {"workspace": workspace, "status": 0, "group": group_name})
        if not rlt.success:
            return rlt
        self.reload(1)
        return Result('')

    def del_subnet_ws(self, data):
        """
        删除工作区的指派
        :param data:
        :return:
        """
        # 先更新etcd中数据
        rlt = self.networkdb.update_subnet(data.get('cluster_name'),
                                           data.get('fa_ip').split('/')[0],
                                           data.get('key'),
                                           {"workspace": '', "status": 1}
                                           )
        if not rlt.success:
            return rlt
        self.reload(1)

        rlt = self.networkdb.read_subnet(data.get('cluster_name'), data.get('fa_ip').split('/')[0], data.get('key'))
        if not rlt.success:
            return rlt
        subnet_info = rlt.content

        # 连接主机  删除工作区指派
        rlt = CluNodedb.instance().read_node_list(data['cluster_name'])
        if not rlt.success:
            return rlt
        master_ip = ''
        for i in rlt.content:
            if i.get('type') == 'master':
                master_ip = i.get('ip')
                break

        rlt = Masterdb.instance().read_master(master_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        con = rlt.content
        username = con.get('username', None)
        passwd = con.get('userpwd', None)
        prikey = con.get('prikey', None)
        prikeypwd = con.get('prikeypwd', None)
        port = int(con.get('port', 22))
        remot = RemoteParam(master_ip, port, username, passwd, prikey, prikeypwd)
        rlt = remot.create_sshclient()
        if not rlt.success:
            return rlt

        # 删除网络池
        # 删除工作区的指派profile
        command = "ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl delete ippool {}".format(subnet_info['subnet'])

        rlt = remot.exec_command(command)
        remot.close()
        if not rlt.success or ('Successfully' not in rlt.content[0] or 'resource does not exist' not in rlt.content[0]):
            Log(1, "del_subnet_ws failed:{}".format(rlt.content))
        return Result('')

    def is_isolated(self, cluster_name, workspace, isolate):
        """
        isolate workspace
        :param workspace:
        :return:
        """
        # 检查工作区是否存在
        if not WorkSpacedb.instance().workspace_is_exist(workspace):
            return Result('', ETCD_RECORD_NOT_EXIST_ERR, 'workspace:{} is not existd'.format(workspace), 400)

        # connect node
        rlt = CluNodedb.instance().read_node_list(cluster_name)
        if not rlt.success:
            return rlt
        master_ip = ''
        for i in rlt.content:
            if i.get('type') == 'master':
                master_ip = i.get('ip')
                break

        rlt = Masterdb.instance().read_master(master_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        con = rlt.content
        username = con.get('username', None)
        passwd = con.get('userpwd', None)
        prikey = con.get('prikey', None)
        prikeypwd = con.get('prikeypwd', None)
        port = int(con.get('port', 22))
        remot = RemoteParam(master_ip, port, username, passwd, prikey, prikeypwd)
        rlt = remot.create_sshclient()
        if not rlt.success:
            return rlt

        # isolate workspace
        if isolate == '1':
            policy_content = """
            - apiVersion: v1
              kind: policy
              metadata:
                name: {}
              spec:
                selector: calico/k8s_ns == '{}'
                ingress:
                - action: allow
                  source:
                    selector: calico/k8s_ns == '{}'
                - action: deny
                  source:
                    selector: calico/k8s_ns != '{}'
                - action: allow
                egress:
                - action: allow""".format(workspace, workspace, workspace, workspace)
        else:
            policy_content = """
            - apiVersion: v1
              kind: policy
              metadata:
                name: {}
              spec:
                selector: calico/k8s_ns == '{}'
                ingress:
                - action: allow
                egress:
                - action: allow""".format(workspace, workspace)
        policy_command = "cat << EOF | ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl apply -f - {}\nEOF".format(policy_content)
        rlt = remot.exec_command(policy_command)
        Log(3, "set isolate command:{}, {}".format(policy_command, rlt.content))
        remot.close()
        if not rlt.success or (
                'Successfully' not in rlt.content[0] and 'resource already exists' not in rlt.content[0]):
            return Result('', 400, rlt.content, 400)

        # 更新etcd
        rlt = WorkSpacedb.instance().update_workspace(workspace, {'isolate': isolate})
        if not rlt.success:
            return rlt
        return Result(0)