# -*- coding: utf-8 -*-

"""
Created on 2017年3月01日

@author: ufleet

"""
from __future__ import division
from frame.logger import PrintStack
import re
from frame.logger import Log
import datetime
import pytz
from common.commcluster import my_request
from etcddb.monitormgr import Monitordb
from etcddb.nodemgr import CluNodedb
import time
import Queue
from common.inter import Factory
from etcddb.mastermgr import Masterdb


class NodeMonitor(object):
    """
    将该类的实类放到队列中进行执行run任务
    """

    def __init__(self, host_ip, num):
        self.host_ip = host_ip
        self.num = num
        self.status = 0

    def node_time(self, data):
        """
        主机时间
        :param data:
        :return:
        """
        time_data = re.findall(
            r"# TYPE node_time gauge(.+?)#",
            data, re.S)
        return float(time_data[0].split(' ')[1])

    def cpu_anly(self, data):
        """
        cpu利用率
        :param data:
        :return:
        """
        cpu_data = re.findall(
            r"# TYPE node_cpu counter(.+?)#",
            data, re.S)
        a = cpu_data[0].split('\n')

        temp_list = []
        v = {'num_all': 0, 'idle_all': 0}
        for i in a:
            if 'cpu0' in i:
                k_v = i.split(' ')
                temp_list.append(k_v[1])
                v['num_all'] += float(k_v[1])
                if "idle" in k_v[0]:
                    v['idle_all'] += float(k_v[1])
        Log(4, "cpu_anly.................:{},num_all:{}, idle_all:{}".format(temp_list, v['num_all'], v['idle_all']))
        return v

    def mem_anly(self, data):
        """
        内存使用率
        :param data:
        :return:
        """
        a = re.findall(
            r"# TYPE node_memory_MemTotal gauge(.+?)#",
            data, re.S)
        mem_total = float(a[0].split(' ')[1])

        b = re.findall(
            r"# TYPE node_memory_MemFree gauge(.+?)#",
            data, re.S
        )
        mem_free = float(b[0].split(' ')[1])
        c = re.findall(
            r"# TYPE node_memory_Cached gauge(.+?)#",
            data, re.S
        )
        mem_cache = float(c[0].split(' ')[1])
        d = re.findall(
            r"# TYPE node_memory_Buffers gauge(.+?)# ",
            data, re.S
        )
        mem_buffer = float(d[0].split(' ')[1])

        e = re.findall(
            r"# TYPE node_memory_SReclaimable gauge(.+?)#",
            data, re.S
        )
        mem_srec = float(e[0].split(' ')[1])

        Log(4, "node_monitor mem_anly, node:{}, mem_total:{}, mem_free:{}, mem_cache:{}, mem_buffer:{}, percent:{}".format(self.host_ip, mem_total,
                                                                                              mem_free, mem_cache, mem_buffer, round(
                100 * (1 - (mem_free + mem_cache + mem_buffer + mem_srec) / mem_total), 2)))
        return round(100 * (1 - (mem_free + mem_cache + mem_buffer + mem_srec) / mem_total), 2)

    def disk_anly(self, data):
        """
        磁盘使用率
        :param data:
        :return:
        """
        a = re.findall(
            r"# TYPE node_filesystem_size gauge(.+?)#",
            data, re.S)
        disk_all = 0
        for i in a[0].split('\n'):
            if i:
                if "mountpoint=\"/rootfs\"" in i:
                    disk_all = float(i.split(' ')[1])
                    break

        b = re.findall(
            r"# TYPE node_filesystem_avail gauge(.+?)#",
            data, re.S)
        disk_avail = 0
        for i in b[0].split('\n'):
            if i:
                if "mountpoint=\"/rootfs\"" in i:
                    disk_avail = float(i.split(' ')[1])
                    break
        if disk_all and disk_avail:
            return round(100 * (1 - disk_avail / disk_all), 2)
        else:
            return 0

    def network_anly(self, data):
        """
        网络平均流量 byte/s
        """
        try:
            rx = re.findall(
                r"# TYPE node_network_receive_bytes gauge(.+?)#",
                data, re.S)
            rx_d = 0
            for i in rx[0].split('\n'):
                if i:
                    rx_d += float(i.split(' ')[1])

            tx = re.findall(
                r"# TYPE node_network_transmit_bytes gauge(.+?)#",
                data, re.S)
            tx_d = 0
            for i in tx[0].split('\n'):
                if i:
                    tx_d += float(i.split(' ')[1])
        except Exception as e:
            # Log(1, "node monitor error:{}".format(e.message))
            return None
        return {'rx': rx_d, 'tx': tx_d, 'aver_bytes': 0}

    def run(self):
        """
        主机监控
        cong指定端口9100上取得数据并分析，将数据存到etcd中
        :param host_ip:
        :return:
        """
        Log(4, "node monitor:{} #run at:{}".format(self.host_ip, datetime.datetime.now()))
        url1 = 'http://' + self.host_ip + ':9100/metrics'
        r = my_request(url1, 'GET', 5)
        t1 = time.time()
        if r.success:
            if r.content.status_code == 200:
                r = r.content.text
                tz = pytz.timezone('Asia/Shanghai')
                date_now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                data = {
                    'datetime': self.node_time(r),
                    'anlytime': date_now,
                    'anlycpu': self.cpu_anly(r),
                    'mem': self.mem_anly(r),
                    'disk': self.disk_anly(r),
                    'network': self.network_anly(r),
                    'num': self.num
                }

                # 先检查主机是否被删除
                # if Monitordb.instance().is_host_exist(self.host_ip.replace('.', '-')):
                if Masterdb.instance().is_master_exist(self.host_ip.replace('.', '-')):
                    s1 = Monitordb.instance().save_monitornode(self.host_ip.replace('.', '-'), self.num, data)
                    Log(3, 'nodemonitor running finished. num:{}, cost:{}'.format(self.num, time.time() - t1))
                    if s1.success:
                        self.num += 1
                else:
                    Log(3, "node monitor finished. the host is deleted:{}. cost:{}".format(self.host_ip, time.time() - t1))
        else:
            Log(1, "cluster node monitor error, can not get request from node:{}".format(self.host_ip))
        self.status = 1
        return

    def is_finished(self):
        return self.status > 0


class Monitor(object):
    """
    生产者  通过timeout函数将所有的主机ip加到队列中
    由Factory这个工厂执行
    """

    def __init__(self):
        super(Monitor, self).__init__()
        self.task_queue = Queue.Queue()
        self.threads = []
        self.__init_thread_pool(5, 'Monitor')
        self.num = 0

    def __init_thread_pool(self, thread_num, schedule_name):
        while thread_num:
            name = "%s_%s" % (schedule_name, thread_num)
            thread_num -= 1
            Factory(self.task_queue, name)  # 执行队列中的任务

    def get_all_nodes(self):
        """
        获取所有正常运行的主机
        :return:
        """
        all_nodes = CluNodedb.instance().read_clunode_map()
        # all_nodes = self.etcd.read_map(ETCD_ROOT_PATH + '/clusternodes')

        node_ip_list = []
        if all_nodes.success:
            for k in all_nodes.content.keys():
                sp_key = k.split('/')
                if sp_key[-3] == 'clusternodes':
                    node_ip_list.append(sp_key[-1].replace('-', '.'))
        return node_ip_list

    def start(self, s_time=10):
        try:
            while True:
                Log(3, "node_monitor  #start at:{}".format(datetime.datetime.now()))
                t1 = datetime.datetime.now()
                self.timeout()
                Log(3, 'node_monitor all cost:{}'.format(datetime.datetime.now() - t1))
                time.sleep(s_time)
        except Exception as ex:
            return

    def timeout(self):
        Log(3, "node_monitor  #timeout start at:{}".format(datetime.datetime.now()))
        if not CluNodedb.instance().ismaster():
            Log(3, "nodemonitor this node is not master")
            return

        # 当队列中有任务不添加
        if self.task_queue.qsize():
            Log(3, "nodemonitor timeout task_queue.qsize:{},".format(self.task_queue.qsize()))
            return

        try:
            # --- 通过多线程方式
            self.num %= 1440
            for i in self.get_all_nodes():
                task = NodeMonitor(i, self.num)
                self.create_task(task)
            self.num += 1
            Log(3, "node monitor create task done at:{}".format(datetime.datetime.now()))
            return None
        except Exception as e:
            Log(1, "nodemonitor catch unexcept error:{}".format(e.message))
            PrintStack()
            return None

    def create_task(self, task):
        self.task_queue.put(task)