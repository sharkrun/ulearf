#! /usr/bin/env python
# -*- coding:utf-8 -*-

from frame.authen import ring8, ring0, ring5, ring3
from common.decorators import list_route, detail_route
from core.clusterrolesmgr import ClusterRolesMgr
from common.util import Result
from core.deployclient import DeployClient


class ClusterRole(object):
    """
    #clusterroles create delete put get
    """
    def __init__(self):
        self.clurole = ClusterRolesMgr.instance()

    # @ring0
    # @ring3
    # @list_route(methods=['POST'])
    # def create(self, post_data, **kwargs):
    #     data = json.loads(post_data)
    #     rlt = self.clurole.create(data)
    #     if not rlt.success:
    #         return rlt
    #     return Result('done')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def list(self, **kwargs):
        """
        list
        :param kwargs:
            "cluster_name" : cluster name
            "name": clusterrole name
        :return: Result object
        """
        cluster_name = kwargs.get('cluster_name')
        if not cluster_name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().get_clusterrole(cluster_name)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def one(self, **kwargs):
        """
        list or one
        :param kwargs:
            "cluster_name" : cluster name
            "name": clusterrole name
        :return: Result object
        """
        clu_name = kwargs.get('cluster_name')
        name = kwargs.get('name')
        if not clu_name or not name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().get_clusterrole(clu_name, name)

    @ring0
    @ring3
    @list_route(methods=['DELETE'])
    def delete(self, **kwargs):
        cluster_name = kwargs.get('cluster_name')
        name = kwargs.get('name')
        if not name or not cluster_name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().del_clusterrole(name, cluster_name)
    #
    # @ring0
    # @ring3
    # @detail_route(methods=['GET'])
    # def detail(self, **kwargs):
    #     pass
