#! /usr/bin/env python
# -*- coding:utf-8 -*-

from frame.authen import ring8, ring0, ring5, ring3
from common.decorators import list_route, detail_route
from core.clusterrolebinding import ClusterRoleBindingMgr
import json
from common.util import Result
from core.deployclient import DeployClient


class ClusterRoleBinding(object):
    """
    #clusterroles create delete put get
    """
    def __init__(self):
        self.clurolebinding = ClusterRoleBindingMgr.instance()

    # @ring0
    # @ring3
    # @list_route(methods=['POST'])
    # def create(self, post_data, **kwargs):
    #     data = json.loads(post_data)
    #     rlt = self.clurolebinding.create(data)
    #     if not rlt.success:
    #         return rlt
    #     return Result('done')

    @ring0
    @ring3
    @list_route(methods=['GET'])
    def list(self, **kwargs):
        clu_name = kwargs.get('cluster_name')
        if not clu_name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().get_clusterrolebinding(clu_name)

    @ring0
    @ring3
    @list_route(methods=['GET'])
    def one(self, **kwargs):
        clu_name = kwargs.get('cluster_name')
        name = kwargs.get('name')
        if not clu_name or not name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().get_clusterrolebinding(clu_name, name)

    @ring0
    @ring3
    @list_route(methods=['DELETE'])
    def delete(self, **kwargs):
        cluster_name = kwargs.get('cluster_name')
        name = kwargs.get('name')
        if not name or not cluster_name:
            return Result('', 400, 'param error', 400)
        return DeployClient.instance().del_clusterrolebinding(name, cluster_name)
    #
    # @ring0
    # @ring3
    # @detail_route(methods=['GET'])
    # def detail(self, **kwargs):
    #     pass
