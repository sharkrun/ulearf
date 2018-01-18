# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年5月18日

@author: Cloudsoar
'''
import json
import os
import shutil
import tarfile
import threading
import time
from common.timer import Timer
from common.util import Result
from frame.logger import Log, FileGuard, PrintStack
from frame.authen import ring0, ring5, ring3
from frame.configmgr import ConfigMgr
# from frame.dockerclient import DockerClient
from core.errcode import INVALID_PARAM_ERR, LOG_FILE_NOT_EXIST_ERR
from frame.host import LinuxHost
# from mongodb.commondb import ExportAllData, ImportData, CommonDB
# from mongoimpl.registry.repositorydbimpl import RepositoryDBImpl
from common.decorators import list_route


class HostMgr(object):
    '''
    # 实现主机信息管理
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.host = LinuxHost()
        self.timer = Timer(1, self.host, 'host time')
        self.timer.start()
        self.net_stats = []
        # cli = DockerClient.instance()
        # if cli:
        #     self.container_net_stats = ContainerNetStats(cli, self.net_stats)
        #     self.container_net_stats.start()

    # @ring0
    # def info(self):
    #     rlt = RepositoryDBImpl.instance().exec_db_script('overview')
    #     if not rlt.success:
    #         Log(1, 'namespaces.read_record_list fail,as[%s]' % (rlt.message))
    #
    #     rlt.content.update(self.host.get_host_info())
    #     return rlt

    @ring5
    @ring3
    @ring0
    @list_route(methods=['GET'])
    def hostinfo(self, **kwargs):
        return Result(self.host.get_host_info())

    @ring0
    @list_route(methods=['GET'])
    def netifs(self, **kwargs):
        iface = kwargs.get('iface', '')
        if iface:
            # return Result(self.host.get_network_data(iface))
            return Result(self.net_stats)
        else:
            return Result(self.host.find_all_Ethernet_interface())

    @ring0
    def ifacelist(self):
        """ netifs
        """
        return Result(self.host.find_all_Ethernet_interface())

    @ring0
    @list_route(methods=['GET'])
    def netstat(self, **kwargs):
        iface = kwargs.get('iface', '')
        return Result(self.host.get_network_data(iface))

    @ring0
    def exportLogs(self):
        file_name = time.strftime("Log_%Y%m%d.tar.gz", time.localtime())
        wwwroot = ConfigMgr.instance().get_www_root_path()
        fullpath = os.path.join(wwwroot, file_name)
        if os.path.exists(fullpath):
            os.remove(fullpath)

        self.create_tar('Trace', fullpath)
        return Result(file_name)

    # @ring0
    # def exportData(self):
    #     file_name = time.strftime("Data_%Y%m%d.tar.gz", time.localtime())
    #     wwwroot = ConfigMgr.instance().get_www_root_path()
    #     fullpath = os.path.join(wwwroot, file_name)
    #     if os.path.exists(fullpath):
    #         os.remove(fullpath)
    #
    #     ExportAllData('ApphouseData')
    #
    #     self.create_tar('ApphouseData', fullpath)
    #     return Result(file_name)

    # @ring0
    # def importData(self, post_data, **args):
    #     f = FormData(post_data)
    #     filepath = f.save_tar_file('_tmp')
    #     if not filepath:
    #         return Result('', UPLOAD_DATA_FILE_FAIL_ERR, 'save tar file fail.')
    #
    #     if self.extract_files(filepath, './_tmp'):
    #         return ImportData('_tmp/ApphouseData')
    #     return Result('', EXTRACT_DATA_FILE_FAIL_ERR, 'extract file fail.')

    # @ring0
    # def backups(self):
    #     db = CommonDB('', [])
    #     arr = db.get_back_up_db()
    #     return Result(arr)
    #
    # @ring0
    # def restore_backup(self, backup_name):
    #     db = CommonDB('', [])
    #     return db.restore_backup(backup_name)
    #
    # @ring0
    # def delete_backup(self, backup_name):
    #     db = CommonDB('', [])
    #     if db.drop_back_db(backup_name):
    #         return Result('droped')
    #     return Result('', DROP_DATABASE_FAIL_ERR, 'drop data base fail.')

    def create_tar(self, folder, file_name):
        try:
            t = tarfile.open(file_name, "w:gz")
            for root, _, files in os.walk(folder):
                for _file in files:
                    fullpath = os.path.join(root, _file)
                    t.add(fullpath)
        except Exception:
            PrintStack()
        finally:
            if t:
                t.close()

    def extract_files(self, tar_path, ext_path):
        try:
            if os.path.isdir('_tmp/ApphouseData'):
                shutil.rmtree('_tmp/ApphouseData')

            with tarfile.open(tar_path) as tar:
                tar.extractall(path=ext_path)

            if os.path.isdir('_tmp/ApphouseData'):
                return True
        except:
            PrintStack()

        return False

    @ring0
    def logs(self, line_num, skip=0):
        try:
            line_num = int(line_num)
            skip = int(skip)
        except Exception:
            return Result('', INVALID_PARAM_ERR, 'Param invalid')

        workdir = os.path.abspath('.')
        workdir = os.path.join(workdir, "Trace")
        workdir = os.path.join(workdir, "logs")
        log_path = os.path.join(workdir, "operation.log")

        if not os.path.isfile(log_path):
            Log(1, "The log file [%s] is not exist." % (log_path))
            return Result('', LOG_FILE_NOT_EXIST_ERR, 'File not exist')
        arr = []
        size = skip
        with FileGuard(log_path, 'r') as fp:
            fp.seek(skip)

            for line in fp:
                if line_num == 0:
                    break;
                size += len(line)
                line_num -= 1
                arr.append(line)

        return Result(arr, 0, size)


class ContainerNetStats(threading.Thread):
    def __init__(self, client, net_stats, thread_name="container_net_stats"):
        super(ContainerNetStats, self).__init__(name=thread_name)
        self.net_stats = net_stats
        self.cli = client
        self.setDaemon(True)

    def run(self):
        while True:
            try:
                self.container_net_stats()
            except Exception:
                PrintStack()
            time.sleep(3)

    def container_net_stats(self):
        o_stats = {'rx_bytes': 0, 'tx_bytes': 0}

        stats_obj = self.cli.net_status()
        Log(3, "stats_obj:{}".format(stats_obj))
        for stat in stats_obj:
            te = json.loads(stat)
            stats = {'rx_bytes': 0, 'tx_bytes': 0}
            Log(3, "te :{}".format(te))
            stats['rx_bytes'] = te['networks']['eth0']['rx_bytes'] - o_stats['rx_bytes']
            stats['tx_bytes'] = te['networks']['eth0']['tx_bytes'] - o_stats['tx_bytes']
            o_stats['rx_bytes'] = te['networks']['eth0']['rx_bytes']
            o_stats['tx_bytes'] = te['networks']['eth0']['tx_bytes']
            if (len(self.net_stats) == 10):
                self.net_stats.pop(0)
            self.net_stats.append(stats)
