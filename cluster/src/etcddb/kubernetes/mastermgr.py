# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年7月4日

@author: Jack
'''

import threading

from common.guard import LockGuard
from common.util import Result
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, ETCD_RECORD_NOT_EXIST_ERR
from frame.etcdv3 import ETCDMgr
from frame.logger import Log


class Masterdb(ETCDMgr):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        ETCDMgr.__init__(self, 'masternodedir')

    def _is_match(self, data, query):
        for key, value in query.iteritems():
            if isinstance(value, list):
                if data.get(key) not in value:
                    return False
            elif data.get(key) != value:
                return False
        return True

    def query(self, condition):
        rlt = self.read_list(key_id='id')
        if not rlt.success:
            Log(1, 'MasterMgr.query read_all fail,as[%s]' % (rlt.message))
            return rlt

        arr = []
        for master in rlt.content:
            if self._is_match(master, condition):
                arr.append(master)

        return Result(arr)

    def read_master(self, master_id):
        return self.read(master_id, json=True)

    def save_master(self, master_id, data):
        """
        保存主机信息到masternodedir
        :param master_id:
        :param data:
        :return:
        """
        # data['datetime'] = DateNowStr()
        rlt = self.set(master_id, data)
        if not rlt.success:
            Log(1, 'MasterMgr.create_master fail,as[%s]' % (rlt.message))
            return rlt

        return Result(master_id)

    def update_master(self, master_id, data):
        if not self.is_key_exist(master_id):
            Log(1, 'MasterMgr.update_master [%s]fail,as the key not exist' % (master_id))
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'The master not exist.')

        if isinstance(data, dict):
            rlt = self.update_json_value(master_id, data)
            if not rlt.success:
                Log(1, 'MasterMgr.update_master save info fail,as[%s]' % (rlt.message))
                return rlt

        return Result(master_id)

    def delete_master(self, master_id):
        """
        删除master（删除/masternodedir/<master_id>)
        :param master_id:
        :return:
        """
        rlt = self.delete(master_id)

        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('')
            Log(1, "MasterMgr.delete_master error:{}".format(rlt.message))
            return rlt
        return Result('')

    def delete_master_by_name(self, workspace, app_name, master_name):
        rlt = self.read_list(key_id='id')
        if not rlt.success:
            Log(1, 'MasterMgr.delete_master_by_name read_all fail,as[%s]' % (rlt.message))
            return rlt

        if app_name:
            for master in rlt.content:
                if master.get('name') == app_name and master.get('workspace') == workspace:
                    return self.delete_master(master['id'])
        else:
            for master in rlt.content:
                if master.get('master_name') == master_name and master.get('workspace') == workspace:
                    return self.delete_master(master['id'])

        return Result('', ETCD_RECORD_NOT_EXIST_ERR, 'The master not exist')

    def is_master_exist(self, master_name):
        return self.is_key_exist(master_name)

    def read_masternode_map(self, key):
        """
        读取所有masternodedir下的主机
        :param key:
        :return:
        """
        return self.read_map(key)