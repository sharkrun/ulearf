# -*- coding: utf-8 -*-
# Copyright (c) 2017  the ufleet
import json

from common.decorators import list_route
from common.util import Result
from core.errcode import INTERNAL_EXCEPT_ERR
from core.workspacemgr import WorkspaceMgr
from frame.authen import ring0, ring5, ring3
from frame.logger import Log, PrintStack
from core.networkmgr import NetworkMgr


class Workspace(object):
    """
    workspace
    """

    def __init__(self):
        self.datamgr = WorkspaceMgr()

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def create(self, post_data, **args):
        """
        # 将指定集群放在指定的workspacegoup下管理，创建namespace
        :return:
        workspace_name:需要创建的workspace的名称，全局唯一
        """

        try:
            info = json.loads(post_data.replace("'", "\'"))
            passport = args.get('passport', {})
            # username = args.get('passport', {}).get('username')
            rlt = self.datamgr.workspace_create(passport, info)
            if not rlt.success:
                Log(1, 'Workspace.create workspace_create fail,as[%s]' % (rlt.message))
            return rlt
        except Exception as e:
            PrintStack()
            Log(1, "Workspace.create error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def update(self, post_data, **args):
        """
        # 修改namespace
        # 已完成
        :param post_data:
        :return:
        """
        try:
            info = json.loads(post_data.replace("'", "\'"))
            passport = args.get('passport', {})
            # creater = args.get('passport', {}).get('username', 'unknown')
            rlt = self.datamgr.workspace_update(passport, info)
            if not rlt.success:
                Log(1, 'Workspace.update workspace_update fail,as[%s]' % (rlt.message))
            return rlt
        except Exception as e:
            PrintStack()
            Log(1, "error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspace_delete(self, **kwargs):
        """
        # 删除workspace
        # 已经实现
        """
        try:
            cluster_name = kwargs.get('cluster_name', '')
            workspacegroup_name = kwargs.get('workspacegroup_name', '')
            workspace_name = kwargs.get('workspace_name', '')
            passport = kwargs.get('passport', {})
            # username = kwargs.get('passport', {}).get('username')
            return self.datamgr.workspace_delete(workspace_name, workspacegroup_name, cluster_name, passport)
        except Exception as e:
            PrintStack()
            Log(1, "error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspace_remain(self, **kwargs):
        """
        # 统计workspace中cpu mem
        :param kwargs:
        :return:
        """
        try:
            cluster_name = kwargs.get('cluster_name', '')
            rlt = self.datamgr.workspce_remain(cluster_name)
            if not rlt.success:
                Log(1, "workspace_remain error:{}".format(rlt.message))
            return rlt
        except Exception as e:
            PrintStack()
            Log(1, "error:{}".format(e))
            return Result('', INTERNAL_EXCEPT_ERR, 'server error')

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspace_num(self, **kwargs):
        """
        # 获取workspace个数
        :return:
        """
        group = kwargs.get('group', None)
        rlt = self.datamgr.workspace_num(group)
        if not rlt.success:
            Log(1, 'Workspace.workspace_num fail,as[%s]' % (rlt.message))
        return rlt

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspace_list_name(self, **kwargs):
        """
        # 获取一个group下的所有workspace名称
        :return:
        """
        rlt = self.datamgr.group_ws_name_list(kwargs.get('group_name', ''))
        if not rlt.success:
            Log(1, 'Workspace.workspace_list_name group_ws_name_list fail,as[%s]' % (rlt.message))
        return rlt

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspace_list(self, **kwargs):
        """
        # 获取一个workspacegroup下面的所有workspace
        :return:
        """
        rlt = self.datamgr.group_ws_list(kwargs.get('group_name', ''))
        if not rlt.success:
            Log(1, 'Workspace.workspace_list group_ws_list fail,as[%s]' % (rlt.message))
        return rlt

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def cluster_list(self, **kwargs):
        """
        通过用户组查看集群列表
        :param kwargs:
        :return:
        """
        group_name = kwargs.get('group_name', '')
        return self.datamgr.cluster_list(group_name)

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def get_subnet_workspace(self, **kwargs):
        """
        # 获取可被指派的workspace
        :return:
        """
        cluster_name = kwargs.get('cluster_name')
        rlt = self.datamgr.subnet_workspace(cluster_name)
        if not rlt.success:
            Log(1, 'Workspace.get_subnet_workspace subnet_workspace fail,as[%s]' % (rlt.message))
        return rlt

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def workspaces(self, **kwargs):
        """
        # 通过clu和group获取workspace 列表
        :param kwargs:
        :return:
        """
        cluster_name = kwargs.get('cluster_name')
        group = kwargs.get('group')
        if not cluster_name or not group:
            return Result('', 400, 'param error', 400)
        rlt = self.datamgr.get_by_clu(cluster_name, group)
        if not rlt.success:
            Log(1, 'Workspace.workspaces get_by_clu fail,as[%s]' % (rlt.message))
        return rlt

    @ring0
    @ring5
    @ring3
    @list_route(methods=['GET'])
    def isolate(self, **kwargs):
        """
        isolate workspace
        :param kwargs:
        isolate: 0 or 1
        :return:
        """
        cluster_name = kwargs.get('cluster_name')  # st
        workspace = kwargs.get('workspace')  # str
        isolate = kwargs.get('isolate')  # int
        if cluster_name and workspace and isolate in ['0', '1']:
            return NetworkMgr.instance().is_isolated(cluster_name, workspace, isolate)

        return Result('', 400, 'invalid param', 400)
