#! /usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import division
import Queue
from common.inter import Factory
from frame.configmgr import GetSysConfig
import os
import re
from etcddb.ufleethostmgr import UfleetHostdb
from frame.logger import PrintStack, Log
import time
from collections import OrderedDict
import datetime


class UfleetHost(object):
    def __init__(self, ip, times):
        self.hostip = ip
        self.times = times
        self.status = 0

    def run(self):
        t1 = time.time()

        # 主机系统信息
        self.check_info()

        # cpu mem disk net
        # cpu
        cpu = 0
        alltime1, idletime1 = self.alltime_idletime()
        time.sleep(0.2)
        alltime2, idletime2 = self.alltime_idletime()
        total = alltime2 - alltime1
        idle = idletime2 - idletime1
        if total:
            cpu = round(100 * (total - idle) / total, 3)

        # mem
        mem = 0
        memtotal, memfree = self.get_meminfo()
        if memtotal:
            mem = round(100 * (memtotal - memfree) / memtotal, 3)

        # disk
        disk = 0
        avaldisk, totaldisk = self.get_disk_stat()
        if totaldisk:
            disk = round(100 * (totaldisk - avaldisk) / totaldisk, 3)

        # net
        ethernet_list = self.find_all_Ethernet_interface()
        Rx = 0
        Tx = 0
        for i in ethernet_list:
            d = self.get_network_data_o(i)
            Rx += d['RxBytes']
            Tx += d['TxBytes']
        data = {'network': {'rx': Rx, 'tx': Tx}, 'mem': mem, 'num': self.times, 'disk': disk, 'cpu': cpu, 'datetime': time.time()}
        rlt = UfleetHostdb.instance().update_info(self.hostip+'/'+str(self.times), data)
        if not rlt.success:
            Log(1, "ufleethost monitor update data error:{}".format(rlt.message))
        self.status = 1
        Log(3, "ufleet host monitor finished. cost:{}".format(time.time() - t1))
        return

    def check_info(self):

        # ufleet 状态
        # 实时去etcd中查看

        rlt = UfleetHostdb.instance().read_host(self.hostip, 'info')
        if not rlt.success:
            return

        old_info = rlt.content

        # 系统
        osver = ''
        if os.path.exists('/host/etc/os-release'):
            with open('/host/etc/os-release') as fd:
                for line in fd:
                    if line.startswith('PRETTY_NAME'):
                        osver = line.split('=')[1].replace('\n', '').replace('"', '')
                        break

        # 主机名
        hostname = ''
        if os.path.exists('/host/proc/sys/kernel/hostname'):
            with open('/host/proc/sys/kernel/hostname') as fd:
                for line in fd:
                    hostname = line.strip()

        # cpu
        num = 0
        cpu_model = ''
        cpu_hz = ''
        if os.path.exists('/host/proc/cpuinfo'):
            with open('/host/proc/cpuinfo') as fd:
                for line in fd:
                    if line.startswith('processor'):
                        num += 1
                    if line.startswith('model name'):
                        cpu_model = line.split(':')[1].strip().split()
                        cpu_model = cpu_model[0] + ' ' + cpu_model[2] + ' ' + cpu_model[-1]
                cpu_hz = cpu_model.split(' ')[-1]

        # 内存
        mem = ''
        if os.path.exists('/host/proc/meminfo'):
            with open('/host/proc/meminfo') as fd:
                for line in fd:
                    if line.startswith('MemTotal'):
                        mem = int(line.split()[1].strip())
                        mem = '%.f' % (mem / 1024.0) + ' MB'

        # 磁盘
        disk = os.statvfs('/')
        capacity = round((disk.f_bsize * disk.f_blocks / 1024) / (1024 ** 2), 3)

        # docker
        # docker_version = GetSysConfig('docker_version')

        new_info = {'osversion': osver, 'ip': self.hostip, 'cpu_num': num, 'cpu_hz': cpu_hz, 'mem': mem,
                    'disk': '%.f' % capacity + 'GB', 'docker_version': '', 'hostname': hostname}
        if old_info != new_info:
            Log(3, "old_info:{}, new_info:{}, {}".format(old_info, new_info, new_info == old_info))
            rlt = UfleetHostdb.instance().update_info(self.hostip+'/'+'info', new_info)
            if not rlt.success:
                Log(1, "ufleethost monitor update info error:{}".format(rlt.message))

    def find_all_Ethernet_interface(self):
        """获取当前主机的所有网卡列表。
           #  参数: 无参数
           #  返回值: 网卡列表
           #  不显示容器网卡（veth,docker开头的.）
        """
        if not os.path.isfile('/host/proc/net/dev'):
            return []

        ethernet_list = []
        with open('/host/proc/net/dev', 'r') as fp:
            for line in fp:
                if (line.find('docker') >= 0) or (line.find('veth') >= 0) or (line.find('lo:') >= 0):
                    continue
                elif line.find(':') >= 0:
                    index = line.index(':')
                    line = line[0:index]
                    ethernet_list.append(line.strip())
                    # return Result(ethernet_list)
                    Log(4, "find a network iface[%s]" % (line.strip()))
            return ethernet_list

    def get_network_data_o(self, iface="eth0"):
        if not os.path.isfile('/host/proc/net/dev'):
            return {'RxBytes': 0, 'TxBytes': 0}

        with open('/host/proc/net/dev', 'r') as fp:
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

    def get_disk_stat(self, path="/"):
        if not os.path.exists(path):
            return 0, 0
        disk = os.statvfs(path)
        capacity = disk.f_bsize * disk.f_blocks / 1024
        available = disk.f_bsize * disk.f_bavail / 1024
        return available, capacity

    def get_meminfo(self):
        if not os.path.isfile('/host/proc/meminfo'):
            return 0, 0

        meminfo = OrderedDict()
        with open('/host/proc/meminfo') as f:
            for line in f:
                meminfo[line.split(':')[0]] = long(line.split(':')[1].strip().split()[0])
            meminfo["TotalFree"] = meminfo['MemFree'] + meminfo['Buffers'] + meminfo['Cached']
            Log(4, 'host:[%s],meminfo:MemTotal:[%s]TotalFree[%s]MemFree[%s]Buffers[%s]Cached[%s]' % (self.hostip, meminfo['MemTotal'],
                meminfo["TotalFree"], meminfo['MemFree'], meminfo['Buffers'], meminfo['Cached']))

        return meminfo['MemTotal'], meminfo["TotalFree"]

    def alltime_idletime(self):
        stat = self.read_cpu_stat()
        if not stat:
            return 0, 0

        if len(stat) < 9:
            return 0, 0

        alltime = 0  # LinuxHos
        for x in range(1, 10):
            alltime += long(stat[x])
        idletime = long(stat[4])
        return alltime, idletime

    def read_cpu_stat(self):
        if not os.path.isfile('/host/proc/stat'):
            return False

        """Read the current system cpu usage from /host/proc/stat."""
        with open('/host/proc/stat', 'r') as lines:
            for line in lines:
                arr = line.split()
                if len(arr) < 5:
                    continue
                if arr[0].startswith('cpu'):
                    return arr
            return False

    def is_finished(self):
        return self.status > 0


class UfleetMonitor(object):
    def __init__(self):
        self.hostip = GetSysConfig('current_host')
        self.task_queue = Queue.Queue()
        self.cal_times = 0
        self.__init_thread_pool(1, 'Ufleethost monitor')

    def __init_thread_pool(self, thread_num, schedule_name):
        while thread_num:
            name = "%s_%s" % (schedule_name, thread_num)
            thread_num -= 1
            Factory(self.task_queue, name)  # 执行队列中的任务

    def find_all_Ethernet_interface(self):
        """获取当前主机的所有网卡列表。
           #  参数: 无参数
           #  返回值: 网卡列表
           #  不显示容器网卡（veth,docker开头的.）
        """
        if not os.path.isfile('/host/proc/net/dev'):
            return []

        ethernet_list = []
        with open('/host/proc/net/dev', 'r') as fp:
            for line in fp:
                if (line.find('docker') >= 0) or (line.find('veth') >= 0) or (line.find('lo:') >= 0):
                    continue
                elif line.find(':') >= 0:
                    index = line.index(':')
                    line = line[0:index]
                    ethernet_list.append(line.strip())
                    # return Result(ethernet_list)
                    Log(4, "find a network iface[%s]" % (line.strip()))
            return ethernet_list

    def timeout(self):
        try:

            Log(3, "ufleet_host #timeout start at:{}".format(datetime.datetime.now()))
            # 当队列中有任务不添加
            if self.task_queue.qsize():
                Log(3, "ufleethost monitor timeout task_queue.qsize:{},".format(self.task_queue.qsize()))
                return
            self.cal_times %= 1440

            task = UfleetHost(self.hostip, self.cal_times)
            self.creat_task(task)
            self.cal_times += 1
        except Exception as e:
            PrintStack()
            Log(1, "ufleet_host monitor timeout error:{}".format(e.message))

    def creat_task(self, task):
        self.task_queue.put(task)
