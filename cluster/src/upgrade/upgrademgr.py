# -*- coding: utf-8 -*-
# !/usr/bin/env python
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年6月12日

@author: Cloudsoar
'''

from common.util import Result, GetDynamicClass
from core.const import APP_VERSION, ETCD_ROOT_PATH, ETCD_VERSION_PATH, ETCD_ROOT
from core.errcode import UPGRADE_FAIL_ERR
from etcddb.settingmgr import SettingMgr
from frame.auditlogger import WebLog
from frame.etcdv3 import ETCDClient
from frame.exception import InternalException
from frame.logger import SysLog, Log
from upgrade.data import data


class UpgradeMgr(object):
    '''
    # implement app house upgrade
    '''

    def __init__(self):
        '''
        Constructor
        '''

    def upgrade(self):
        if self.upgrade_to_latest_version():
            WebLog(3, 'upgrade to[latest version]success')
            return Result('upgrade success')
        else:
            WebLog(1, 'upgrade fail.')
            return Result('', UPGRADE_FAIL_ERR, 'upgrade fail')

    def is_latest_version(self):
        current = SettingMgr.instance().get_version()
        SysLog(3, 'UpgradeMgr.current version is[%s]' % (current))
        return APP_VERSION == current

    def upgrade_to_latest_version(self):
        pass


def init_etcd_data():
    etcd = ETCDClient().instance()
    for key, value in data.iteritems():
        if isinstance(value, list):
            for item in value:
                for k, v in item.iteritems():
                    etcd.set('%s/%s/%s' % (ETCD_ROOT, key, k), v)
        else:
            etcd.set('%s/%s' % (ETCD_ROOT, key), value)

    return True


def upgrade():
    current = SettingMgr.instance().get_version()
    if APP_VERSION == current:
        SysLog(3, 'upgrade.current is latest version [%s]' % (current))
        return

    if current is None:
        Log(1, 'upgrade.get_version fail.')
        raise InternalException('upgrade.get_version fail.')

    file_name = 'upgrade' + current
    handler = GetDynamicClass('UpgradeHandler', file_name, 'upgrade')
    if handler:
        u = handler()
        return u.upgrade()
    else:
        SysLog(3, 'no support this version[%s] upgrade' % (current))
        return Result(current)


def init_app_data(force=False, clear_data=False):
    etcd = ETCDClient().instance()

    rlt = etcd.read('%s/%s' % (ETCD_ROOT_PATH, ETCD_VERSION_PATH))
    if rlt.success and rlt.content:
        if clear_data:
            etcd.delete_dir(ETCD_ROOT_PATH)

        if force or clear_data:
            return init_etcd_data()
        else:
            return upgrade()

    return init_etcd_data()








