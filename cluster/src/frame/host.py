# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年3月22日

@author: Jack
'''


from multiprocessing import cpu_count
import os
import re

from frame.logger import PrintStack, Log

from collections import OrderedDict
import time

# from common.timer import Timer
# from test.test_cmath import INF
# import time


class LinuxHost(object):
    '''
    Constructor
    '''
    """
        self.info = [{
          cpuUsage: 21,
          cpu_Count: 4,
          availableRam: '100',
          totalRam: '4000',
          availableDisk: '20000',
          totalDisk: '30000'
        }];
    """
    def __init__(self):
        self.cal_times = 0
        self.cputimedata = {'alltime': 0, 'idletime': 0}
        self.cpu_usage = 0
        self.cpu_num = cpu_count()

        self.ifacedata = {}
        self.ifacerel = {}

    def timeout(self):
        try:
            self.calculate()
        except Exception as e:
            PrintStack()

    def calculate(self):
        # 每秒计算一次ＣPU使用率
        self.cal_times += 1
        Log(3, '-'*20)
        alltime, idletime = self.alltime_idletime()

        if self.cputimedata['alltime'] == 0:
            self.cpu_usage = 0
            self.cputimedata['alltime'] = alltime
            self.cputimedata['idletime'] = idletime
        else:
            self.cpu_usage = float((alltime - idletime) -
                                   (self.cputimedata['alltime'] - self.cputimedata['idletime'])) / \
                float(alltime - self.cputimedata['alltime']) * 100
            self.cputimedata['alltime'] = alltime
            self.cputimedata['idletime'] = idletime

        # 每秒计算一次网卡流量
        for k, v in self.ifacedata.iteritems():
            if v is None:
                self.ifacedata[k] = self.get_network_data_o(k)
                self.ifacerel[k] = {'RxBytes': 0, 'TxBytes': 0}
            else:
                curdata = self.get_network_data_o(k)

                self.ifacerel[k]['RxBytes'] = (curdata['RxBytes'] - self.ifacedata[k]['RxBytes'])/1024/1024
                self.ifacerel[k]['TxBytes'] = (curdata['TxBytes'] - self.ifacedata[k]['TxBytes'])/1024/1024

                self.ifacedata[k]['RxBytes'] = curdata['RxBytes']
                self.ifacedata[k]['TxBytes'] = curdata['TxBytes']

    def get_meminfo(self):
        if not os.path.isfile('/proc/meminfo'):
            return 0, 0

        meminfo = OrderedDict()
        with open('/proc/meminfo') as f:
            for line in f:
                meminfo[line.split(':')[0]] = long(line.split(':')[1].strip().split()[0])
            meminfo["TotalFree"] = meminfo['MemFree'] + meminfo['Buffers'] + meminfo['Cached']
            Log(3,'meminfo:Total[%s]Free[%s]Buffers[%s]Cached[%s]'%(meminfo["TotalFree"], meminfo['MemFree'], meminfo['Buffers'], meminfo['Cached']))

        return meminfo['MemTotal'], meminfo["TotalFree"]

    def read_cpu_stat(self):
        if not os.path.isfile('/proc/stat'):
            return False

        """Read the current system cpu usage from /proc/stat."""
        with open('/proc/stat', 'r') as lines:
            # lines = FileGuard("/proc/stat").readlines()
            for line in lines:
                # print "l = %s" % line
                arr = line.split()
                if len(arr) < 5:
                    continue
                if arr[0].startswith('cpu'):
                    return arr
            return False

    def alltime_idletime(self):
        stat = self.read_cpu_stat()
        if not stat:
            return 0, 0

        if len(stat) < 9:
            return 0, 0

        alltime = 0     # LinuxHos
        for x in range(1, 8):
            alltime += long(stat[x])
        # Log(4, "alltime_idletime:{}".format(stat))
        idletime = long(stat[4]) + long(stat[5])
        return alltime, idletime

    def get_disk_stat(self, path="/home/lear/project/ufleet/cluster"):
        if not os.path.exists(path):
            return 0, 0
        disk = os.statvfs(path)
        # capacity = disk.f_bsize * disk.f_blocks / (1024 * 1024 * 1024)
        # available = disk.f_bsize * disk.f_bavail / (1024 * 1024 * 1024)
        capacity = disk.f_bsize * disk.f_blocks / 1024
        available = disk.f_bsize * disk.f_bavail / 1024
        # hd['used'] = hd['capacity'] - hd['available']
        return available, capacity

    def get_host_info(self):
        host_info = {}
        host_info['cpuUsage'] = float('%.1f' % self.cpu_usage)
        host_info['totalCpu'] = self.cpu_num
        host_info['totalRam'], host_info['availableRam'] = self.get_meminfo()
        host_info['availableDisk'], host_info['totalDisk'] = self.get_disk_stat()

        return host_info

    def find_all_Ethernet_interface(self):
        """获取当前主机的所有网卡列表。
           #  参数: 无参数
           #  返回值: 网卡列表
           #  不显示容器网卡（veth,docker开头的.）
        """
        if not os.path.isfile('/proc/net/dev'):
            return []

        ethernet_list = []
        with open('/proc/net/dev', 'r') as fp:
            for line in fp:
                if (line.find('docker') >= 0) or (line.find('veth') >= 0) or (line.find('lo:') >= 0):
                    continue
                elif line.find(':') >= 0:
                    index = line.index(':')
                    line = line[0:index]
                    ethernet_list.append(line.strip())
                    # return Result(ethernet_list)
                    Log(4,"find a network iface[%s]"%(line.strip()))
            return ethernet_list

    def get_network_data_o(self, iface="eth0"):
        if not os.path.isfile('/proc/net/dev'):
            return {'RxBytes': 0, 'TxBytes': 0}

        with open('/proc/net/dev', 'r') as fp:
            for line in fp:
                if line.find(iface) >= 0:
                    index = line.index(":")
                    line = line[index:]
                    data = re.findall(r"\d+", line)
                    if len(data) < 9:
                        return {'RxBytes': 0, 'TxBytes': 0}
                    # return {'iface': iface, 'RxBytes': long(data[0]), 'TxBytes': long(data[8])}
                    return {'RxBytes': float(data[0]), 'TxBytes': float(data[8])}
        # return {'iface': iface, 'RxBytes': 0, 'TxBytes': 0}
        return {'RxBytes': 0, 'TxBytes': 0}

    def get_network_data(self, iface=""):
        # self.ifacedata = {'eth0': {'RxBytes': 0, 'TxBytes': 0}}
        if iface in self.ifacerel:
            d = self.ifacerel.get(iface)
            return {'iface': iface, 'RxBytes': d.get('RxBytes'), 'TxBytes': d.get('TxBytes')}
        else:
            self.ifacedata.setdefault(iface)
            return {'iface': iface, 'RxBytes': 0, 'TxBytes': 0}

if __name__ == '__main__':
    hostinfo = LinuxHost()
    print(hostinfo.get_network_data("eno1"))
    print(hostinfo.find_all_Ethernet_interface())
    print(hostinfo.get_host_info())
