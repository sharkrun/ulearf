# -*- coding: utf-8 -*-

"""
集群子网列表
"""
from frame.authen import ring0, ring5, ring3
from core.networkmgr import NetworkMgr
from frame.logger import Log, PrintStack
from common.util import Result
import json
from common.decorators import list_route


class Ippool(object):
    def __init__(self):
        pass

    def check_param(self, need_keys, post_keys):
        """
        :param data:
        :return:
        """
        if all(i in post_keys for i in need_keys):
            return True
        else:
            return False

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def create_subnet(self, post_data, **kwargs):
        """
        创建子网
        :param  {"cluster_name": str, "subnet": str, "netmask": int, "ipip": int(0 or 1), "nat": int(0 or 1)}
        :return: Result()  34002:网络池已经存在  31004：集群不存在
        """
        try:
            data_info = json.loads(post_data.replace("'", "\'"))
            cluster_name = data_info.get('cluster_name')
            ipip = data_info.get('ipip')
            nat = data_info.get('nat')
            subnet = data_info.get('subnet')
            subnet_num = data_info.get('subnet_num')
            if not all([isinstance(cluster_name, basestring), isinstance(ipip, int), isinstance(nat, int),
                        isinstance(subnet, basestring), isinstance(subnet_num, int)]):
                return Result('', 400, 'param error', 400)

            data_info['creater'] = kwargs.get('passport', {}).get('username', '')
            if not data_info:
                return Result('', 400, 'the post data is invalid', 400)
            rlt = NetworkMgr.instance().create_subnet(data_info)
            if not rlt.success:
                return Result('', rlt.result, rlt.message, 400)
            return Result('')
        except Exception as e:
            PrintStack()
            Log(1, "create_ippool error:{}".format(e.message))
            return Result('', 500, str(e.message), 500)

    # @ring5
    # @ring3
    # @ring0
    # def del_subip_list(self, post_data, **kwargs):
    #     """
    #     删除集群下的某个子网列表
    #     :param {"<cluster_name>": "", "subnet": []}
    #     :return:
    #     """
    #     try:
    #         data_info = json.loads(post_data.replace("'", "\'"))
    #         data_info['creater'] = kwargs.get('passport', {}).get('username', '')
    #         rlt = NetworkMgr.instance().delete_subnet_list(data_info)
    #         if not rlt.success:
    #             Log(3, 'del_ippool error:{}'.format(rlt.message))
    #             return Result('', rlt.result, rlt.message, 400)
    #         return Result('')
    #     except Exception as e:
    #         PrintStack()
    #         Log(1, "del_ippool error:{}".format(e.message))
    #         return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def del_subnet(self, **kwargs):
        """
        删除一个集群下的一个子网集合
        :param kwargs: {"<cluster_name>": ""}
        :return:
        """
        try:
            rlt = NetworkMgr.instance().delelte_subnet(kwargs)
            if not rlt.success:
                Log(3, 'del_subnet error:{}'.format(rlt.message))
                return Result('', rlt.result, rlt.message, 400)
            return Result('')
        except Exception as e:
            PrintStack()
            Log(1, "del_subnet error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_all_subnet(self, **kwargs):
        """
        获取所有网络池的所有子网
        :param kwargs:
        :return:
        """
        try:
            rlt = NetworkMgr.instance().get_ippool()
            if not rlt.success:
                Log(3, 'get_ippool error:{}'.format(rlt.message))
                return Result('', rlt.result, '')
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def update_subnet(self, post_data, **kwargs):
        """
        编辑子网
        :param kwargs:
        :return:
        """
        try:
            data_info = json.loads(post_data.replace("'", "\'"))
            data_info['creater'] = kwargs.get('passport', {}).get('username', '')
            rlt = NetworkMgr.instance().update_subip(data_info)
            if not rlt.success:
                return Result('', rlt.result, '', 400)
            else:
                return Result('')
        except Exception as e:
            PrintStack()
            Log(1, "update_subnet error:{}".format(e.message))
            return Result('')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def get_subnet_by_workspace(self, **kwargs):
        """
        通过工作区获取子网
        :param kwargs:
        :return:
        """
        try:
            rlt = NetworkMgr.instance().get_subnet_by_ws(kwargs.get('workspace'))
            if not rlt.success:
                Log(3, 'subnet_workspace error:{}'.format(rlt.message))
                return Result('', rlt.result, '')
            # data = {'num': len(rlt.content), 'data': rlt.content}
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "get_ippool error:{}".format(e.message))
            return Result('', 500, '', 500)
