# -*- coding: utf-8 -*-

from frame.etcdv3 import ETCDMgr
import threading
from common.guard import LockGuard
from frame.logger import Log
from common.util import Result
from core.errcode import ETCD_KEY_NOT_FOUND_ERR


class Networkdb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'network')


    def save_clu_ippool(self, data_dic):
        """
        保存ippool
        :param data:
        :return:
        """
        return self.smart_set(data_dic)

    def is_fa_ip_exist(self, cluster_name, ip):
        """
        查看子网在集群中是否存在
        :param cluster_name:
        :param ip:
        :return:
        """
        if self.is_key_exist(cluster_name + '/' + ip):
            return True
        else:
            return False

    def network_value_list(self):
        """
        返回所有value
        :return: []
        """
        return self.all_value_list()

    def key_value_map(self, child_key=None):
        """
        返回map
        :param child_key:
        :return:
        """
        return self.read_map(child_key)

    def key_value_list(self, child_key=None):
        """
        :return: Result(['<cluster_name>': [{}, {}], '<cluster_name>': [{}, {}]])
        """
        rlt = self.all_value_list(child_key)
        if not rlt.success:
            return rlt
        net_dic = {}
        for i in rlt.content:
            if isinstance(i, dict):
                net_dic.setdefault(i['cluster_name'], []).append(i)
        return Result(net_dic)

    def subnet_value_list(self, child_key=None):
        """
        读取一个子网的子网列表
        :param child_key:
        :return:
        """
        return self.all_value_list(child_key)

    def del_net(self, clu_name, index_id):
        """
        删除子网
        :param clu_name:
        :param index_id:
        :return:
        """
        return self.delete_dir(clu_name + '/' + index_id)

    def del_ippool_dir(self, clu_name):
        """
        删除网络池
        :param clu_name:
        :return:
        """
        rlt = self.delete_dir(clu_name)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, "del_ippool : {} error:{}".format(clu_name, rlt.message))
            return rlt
        return Result('')

    def read_subnet(self, clu_name, index_id, subnet_id):
        """
        返回一个子网的具体信息
        :param clu_name:
        :param index_id:
        :param subnet_id:
        :return:
        """
        return self.read(clu_name + '/' + index_id + '/' + subnet_id)

    def get_subnet_by_clu(self, clu_name):
        """
        获取某个集群下的subnet
        :param clu_name:
        :return:
        """
        rlt = self.read_map(clu_name)
        if not rlt.success:
            return rlt
        d = []
        for i in rlt.content.values():
            d.append(i['subnet'])
        return Result(d)

    def update_subnet(self, clu_name, index_id, subnet_id, json_data):
        """
        更新子网
        :param clu_name:
        :param index_id:
        :return:
        """
        return self.update_json_value(clu_name + '/' + index_id + '/' + subnet_id, json_data)