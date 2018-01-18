#! /usr/bin/env python
# -*- coding:utf-8 -*-
from etcddb.ufleethost import UfleetHostdb
from common.util import NowMilli
from common.util import Result
from frame.logger import Log
from frame.etcdv3 import ETCDClient
from core.const import ETCD_SCHEDULE


class UfleetHostMgr(object):
    def __init__(self):
        self.db = UfleetHostdb.instance()
        self.expiry_time = 0
        self.__store = {}
        self.loaddata()

    def reload(self, flush=0):

        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def loaddata(self):
        self.expiry_time = NowMilli() + 2000
        self.allhostinfo()

    def allhostinfo(self):
        rlt = self.db.hostallinfo()
        if rlt.success:
            host_dic = {}
            for k, v in rlt.content.items():
                sp_key = k.split('/')
                if sp_key[-1] == 'info':
                    host_dic.setdefault(sp_key[-2], {}).setdefault('info', v)
                else:
                    host_dic.setdefault(sp_key[-2], {}).setdefault('anlydata', []).append(v)
            # Log(4, "allhostinfo:{}".format(host_dic))
            self.__store = host_dic

    def hosts(self):
        self.reload()
        data = []
        for v in self.__store.values():
            info = v.get('info', {})
            etcd = ETCDClient().instance()
            rlt = etcd.read('%s/%s/%s' % (ETCD_SCHEDULE, 'status', info.get('ip', '').replace('.', '-')))
            if rlt.success and rlt.content is not None:
                info['status'] = rlt.content.get('status', '').lower()
                info['message'] = rlt.content.get('message', '')
            else:
                Log(3, "ufleethost read error:{}".format(rlt.message))
            data.append(info)
        return Result(data)

    def detail(self, ip):
        self.reload()

        # 默认统计两个小时的数据
        d = self.__store.get(ip, {}).get('anlydata', [])[-120:]
        d_s = sorted(d, key=lambda s: s['num'])
        Log(3, "detail len(d_s):{}".format(len(d_s)))
        for i in range(len(d_s)):
            if i > 0:
                rx_tx_1 = d_s[i]['network']['rx'] + d_s[i]['network']['tx']
                rx_tx_2 = d_s[i - 1]['network']['rx'] + d_s[i - 1]['network']['tx']
                t_ = (d_s[i]['datetime'] - d_s[i - 1]['datetime'])
                d_s[i]['datetime'] = int(d_s[i]['datetime'])
                if t_:
                    d_s[i]['network']['aver_bytes'] = round((rx_tx_1 - rx_tx_2) / t_, 3)

        return Result(d_s[1:])

    def error_msg(self):
        pass