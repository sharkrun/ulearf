# # -*- coding: utf-8 -*-
# import threading
# from common.guard import LockGuard
# from common.util import NowMilli
# from etcddb.networkmgr import Networkdb
# from common.util import Result
# from frame.logger import Log
# import uuid
# from core.remoteclient import RemoteParam
# import sys
# from etcddb.nodemgr import CluNodedb
# import os
#
#
# class NetworkMgr(object):
#     """
#     网络设置模块
#     """
#     __lock = threading.Lock()
#
#     @classmethod
#     def instance(cls):
#         with LockGuard(cls.__lock):
#             if not hasattr(cls, "_instance"):
#                 cls._instance = cls()
#         return cls._instance
#
#     def __init__(self):
#         self.networkdb = Networkdb.instance()
#         self.expiry_time = 0
#         self.loaddata()
#
#     def reload(self, flush=0):
#         if flush == 1:
#             self.loaddata()
#         else:
#             if self.expiry_time <= NowMilli():
#                 self.loaddata()
#
#     def loaddata(self):
#         self.expiry_time = NowMilli() + 30000
#
#         clu_node = {}
#         rlt = CluNodedb.instance().read_clunode_map()
#         if not rlt.success:
#             return Result('', rlt.result, rlt.message, 500)
#         if rlt.success:
#             for k, v in rlt.content.items():
#                 sp_key = k.split('/')
#                 if sp_key[-3] == 'clusternodes':
#                     true = True
#                     false = False
#                     clu_node.setdefault(sp_key[-2], []).append(v)
#
#         for k, v in clu_node.items():
#             for i in v:
#                 if i['type'] == 'master':
#                     if i['status'] != 'running':
#                         clu_node.pop(k)
#
#         all_ippool = []
#         for i in clu_node.keys():
#             one_ippool = {
#                 'key': str(uuid.uuid1()),
#                 'pool_name': '',
#                 'cluster_name': '',
#                 'creater': '',
#                 'subnetnum': '子网数',
#                 'subnet': []
#             }
#             rlt_net = Networkdb.instance().key_value_map(i)
#             if not rlt_net.success:
#                 continue
#             subnet_num = 0
#             # fa_ip = set()
#             d = {}
#             for k, v in rlt_net.content.items():
#                 d.setdefault(v['fa_ip'], []).append(v)
#                 subnet_num += 1
#             for k, v in d.items():
#                 sub = {'subnet': k, 'children': v, 'creater': v[0].get('creater', ''),
#                        'create_time': v[0].get('create_time', ''), 'key': str(uuid.uuid1()), 'cluster_name': i}
#                 one_ippool['subnet'].append(sub)
#             one_ippool['pool_name'] = i + '-ippool'
#             one_ippool['cluster_name'] = i
#             one_ippool['subnetnum'] = subnet_num
#             all_ippool.append(one_ippool)
#
#         self.__store = all_ippool
#
#     def get_config_dir(self):
#         if hasattr(sys, "_MEIPASS"):
#             base_path = os.environ.get('CLUSTER_WORK_ROOT', '/opt/cluster')
#             return os.path.join(base_path, 'conf')
#         else:
#             base_path = os.path.abspath(".")
#             return os.path.join(base_path, 'frame', 'conf')
#
#     def get_ippool(self):
#         """
#         获取所有的网络池
#         :return:
#         """
#         self.reload()
#         return Result(self.__store)
#
#     # def del_subnet_ws(self, data):
#     #     """
#     #     删除工作区的指派
#     #     :param data:
#     #     :return:
#     #     """
#     #     # 先更新etcd中数据
#     #     rlt = self.networkdb.update_subnet(data.get('cluster_name'),
#     #                                        data.get('fa_ip').split('/')[0],
#     #                                        data.get('key'),
#     #                                        {"workspace": '', "status": 1}
#     #                                        )
#     #     if not rlt.success:
#     #         return rlt
#     #     self.reload(1)
#     #
#     #     rlt = self.networkdb.read_subnet(data.get('cluster_name'), data.get('fa_ip').split('/')[0], data.get('key'))
#     #     if not rlt.success:
#     #         return rlt
#     #     subnet_info = rlt.content
#     #
#     #     # 连接主机  删除工作区指派
#     #     rlt = CluNodedb.instance().read_node_list(data['cluster_name'])
#     #     if not rlt.success:
#     #         return rlt
#     #     master_ip = ''
#     #     for i in rlt.content:
#     #         if i.get('type') == 'master':
#     #             master_ip = i.get('ip')
#     #             break
#     #     remot = RemoteParam(master_ip)
#     #     rlt = remot.connect()
#     #     if not rlt.success:
#     #         return rlt
#     #
#     #     # 删除网络池
#     #     # 删除工作区的指派profile
#     #     command = "ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl delete ippool {};" \
#     #               "ETCD_ENDPOINTS=http://127.0.0.1:12379 calicoctl delete profile {}".format(subnet_info['subnet'],
#     #                                                                                          data.get('workspace'))
#     #     rlt = remot.exec_command(command)
#     #     if not rlt.success or ('Successfully' not in rlt.content[0] or 'resource does not exist' not in rlt.content[0]):
#     #         remot.close()
#     #         Log(1, "del_subnet_ws failed:{}".format(rlt.content))
#     #         # return rlt
#     #     remot.close()
#     #     return Result('')
#
