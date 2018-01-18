#! /usr/bin/env python
# -*- coding:utf-8 -*-

import threading
from common.guard import LockGuard
from core.kubeclientmgr import KubeClientMgr
from frame.logger import Log
from common.datatype import clusterrole
from etcddb.clusterrolemgr import ClusterRoledb
from frame.auditlogger import WebLog
from common.util import Result


class ClusterRolesMgr(object):
    __lock = threading.Lock()
    __rlock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, '_instance'):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        pass

    def create(self, data):
        """
        :param data:
        :return:
        """
        content = data.get('content', '')
        # c_data = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": {"name": data.get('name')},
        #           "rules": content}
        name = content.get('metadata', {}).get('name')
        clu_name = data.get('cluster_name', '')
        if not all([name, clu_name]):
            return Result('', 400, 'param error', 400)
        rlt = KubeClientMgr.instance().create_clusterrole(clu_name, name, content)
        if not rlt.success:
            Log(1, "clusterroles create error:{}".format(rlt.message))
            return rlt

        # d_s = clusterrole(data)
        # 保存到etcd
        # rlt = ClusterRoledb.instance().save(name, d_s)
        # if not rlt.success:
        #     return rlt
        WebLog(3, u'创建', "clusterrole[{}]".format(name, data.get('creater')))
        return Result('')

    def list(self, cluster_name):
        return KubeClientMgr.instance().list_clusterrole(cluster_name)

    def detail(self, name):
        pass

    def delete(self, cluster_name, name):
        return KubeClientMgr.instance().delete_clusterrole(cluster_name, name)
