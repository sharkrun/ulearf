# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
"""

import threading

from common.guard import LockGuard
from common.util import Result, NowMilli
from core.errcode import ETCD_CREATE_KEY_FAIL_ERR, ETCD_KEY_NOT_FOUND_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class Launcherdb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'launcher/clusters/')

    def save_master_info(self, cluster_name, host_name, data):
        """
        保存主机信息到launcher目录
        :param data:
        :return:
        """
        path = cluster_name + '/masters/' + host_name
        return self.set(path, data)

    def save_name_info(self, cluster_name, host_name, data):
        """
        保存主机name到launcher
        :param data:
        :return:
        """
        path = cluster_name + '/name/' + host_name
        return self.set(path, data)

    def save_status_info(self, cluster_name, host_name, data):
        """
        保存集群信息到launcher目录
        :param data:
        :return:
        """
        path = cluster_name + '/status/' + host_name
        return self.set(path, data)

    def read_group_content(self, wgroup_name):
        rlt = self.read(wgroup_name)

    def wgroup_is_exit(self, wgroup_name):
        if self.is_key_exist(wgroup_name):
            return True
        else:
            return False

    def read_wgroup(self, project_id, workspace_id):
        rlt = self.read('%s/%s' % (project_id, workspace_id), json=True)
        if not rlt.success:
            Log(1, 'Launcherdb.read_workspace fail,as[%s]' % (rlt.message))

        return rlt

    def read_workspace_content(self, project_id, workspace_id):
        return self.read('%s/%s' % (project_id, workspace_id), json=True)

    def read_workspace_list(self, project_id):
        return self.read_list(project_id, key_id='workspace_id')

    def create_workspace(self, project_id, data):
        rlt = self.get_identity_id()
        if not rlt.success:
            Log(1, 'Launcherdb.create_workspace.get_identity_id fail,as[%s]' % (rlt.message))
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')

        key = rlt.content
        data['create_time'] = NowMilli()
        rlt = self.set('%s/%s' % (project_id, key), data)
        if not rlt.success:
            Log(1, 'Launcherdb.create_workspace save info fail,as[%s]' % (rlt.message))
            return rlt

        return Result(key)

    def update_workspace(self, project_id, workspace_id, data):
        if not self.is_key_exist('%s/%s' % (project_id, workspace_id)):
            Log(1, 'Launcherdb.update_workspace [%s/%s]fail,as the key not exist' % (project_id, workspace_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The workspace not exist.')

        data['create_time'] = NowMilli()
        rlt = self.update_json_value('%s/%s' % (project_id, workspace_id), data)
        if not rlt.success:
            Log(1, 'Launcherdb.update_workspace save info fail,as[%s]' % (rlt.message))
            return rlt

        return Result(workspace_id)

    def del_workspace(self, project_id, workspace_id):
        rlt = self.delete('%s/%s' % (project_id, workspace_id))
        if not rlt.success:
            Log(1, 'Launcherdb.delete_workspace info fail,as[%s]' % (rlt.message))
            return rlt

        return Result('ok')

    def is_name_exist(self, project_id, tpl_name, workspace_id=None):
        rlt = self.read_list(project_id, key_id='workspace_id')
        if not rlt.success:
            Log(1, 'is_name_exist.read workspace list [%s] fail,as[%s]' % (project_id, rlt.message))
            return False

        for cfg in rlt.content:
            if workspace_id and cfg.get('workspace_id') == workspace_id:
                continue

            if cfg.get('name') == tpl_name:
                return True

        return False

