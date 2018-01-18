# -*- coding: utf-8 -*-
# Copyright (c) 2017  the ufleet

import json
from common.util import Result
from frame.authen import ring0, ring5, ring3
from frame.logger import Log, PrintStack
from core.configmapmgr import ConfigMapMgr
from common.decorators import list_route


class Configmap(object):
    """
    configmap
    """

    def __init__(self):
        self.handler = ConfigMapMgr

    @ring5
    @ring3
    @ring0
    @list_route(methods=['POST'])
    def create(self, post_data, **kwargs):
        try:
            data = json.loads(post_data)
            if not all(['name' in data, 'version' in data, 'workspace' in data, 'content' in data]):
                return Result('', 400, 'param error', 400)
            data['creater'] = kwargs.get('passport', {}).get('username', '')
            rlt = ConfigMapMgr.instance().creat_configmap(data)
            if not rlt.success:
                return Result('', rlt.result, rlt.message, rlt.code)
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "configmaps create error:{}".format(e.message))
            return Result('', 500, str(e.message), 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['DELETE'])
    def configmap(self, workspace, conf_name, **kwargs):
        """
        /v1/configmap/configmap/<workspace>/<name>+<version>  [DELETE]
        :param name:
        :param version:
        :param kwargs:
        :return:
        """
        try:
            username = kwargs.get('passport', {}).get('username', '')
            rlt = ConfigMapMgr.instance().delete(workspace, conf_name, username)
            if not rlt.success:
                return Result('', rlt.result, rlt.message, rlt.code)
            return Result(rlt.content)
        except Exception as e:
            PrintStack()
            Log(1, "configmaps  delete error:{}".format(e.message))
            return Result('', 500, '', 500)

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def configmaps(self, **kwargs):
        """
        获取configmap信息
        unique: 1 只返回最新的版本 0:默认返回所有
        :param workspace:
        :return:
        """
        try:
            workspace = kwargs.get('workspace')
            group = kwargs.get('group')
            # 通过workspace获取
            if workspace:
                rlt = ConfigMapMgr.instance().get_by_ws(workspace)
                if not rlt.success:
                    return Result('', rlt.result, str(rlt.message), rlt.code)
                return Result(rlt.content)
            # 通过group获取
            elif group:
                rlt = ConfigMapMgr.instance().get_by_group(group)
                if not rlt.success:
                    return Result('', rlt.result, rlt.message, 500)
                return Result(rlt.content)
            # 获取所有
            else:
                # return Result('')
                return ConfigMapMgr.instance().get_all()
        except Exception as e:
            PrintStack()
            Log(1, "configmaps get error:{}".format(e.message))
            return Result('', 500, '', 500)