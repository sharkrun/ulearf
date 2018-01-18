# -*- coding: utf-8 -*-

import etcd3
from common.guard import LockGuard
from common.util import Result
import threading
from frame.configmgr import GetSysConfig, GetSysConfigInt
import os
from core.errcode import UNCAUGHT_EXCEPTION_ERR, ETCD_CONNECT_FAIL_ERR, ETCD_KEY_EXISTED
import json
from frame.logger import Log, PrintStack
import etcd3.exceptions


def robust(actual_do):
    def add_robust(*args, **keyargs):
        try:
            return actual_do(*args, **keyargs)
        except etcd3.exceptions.ConnectionFailedError:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd3.exceptions.ConnectionTimeoutError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd connect timeout')
        except etcd3.exceptions.InternalServerError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd interal server error')
        except etcd3.exceptions.PreconditionFailedError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd precdition failed error')
        except Exception as e:
            PrintStack()
            Log(1, "ETCDClient error:{}".format(e.message))
            return Result(0, UNCAUGHT_EXCEPTION_ERR, e.message)
    return add_robust


class ETCDClient(object):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        host = GetSysConfig('etcd_host')
        port = GetSysConfigInt('etcd_port', 2379)
        self.ufleet_id = os.environ.get('UFLEET_NODE_ID')

        protocol = GetSysConfig('etcd_protocol')

        cfg = {'port': port}
        if host is not None:
            cfg['host'] = host

        if protocol in ['http', 'https']:
            if protocol == 'https':
                cfg['ca_cert'] = GetSysConfig('ca_cert')
                cfg['cert_key'] = GetSysConfig('cert_key')
                cfg['cert_cert'] = GetSysConfig('cert_cert')
        self.client = etcd3.client(**cfg)

    @robust
    def is_exist(self, path):
        """
        检查文件或者文件夹是否存在
        :param path:
        :return:
        """
        if self.client.get(path)[0]:
            return Result(True)
        else:
            return Result(False)

    def _parse_2_json(self, txt):
        try:
            return True, json.loads(txt)
        except:
            PrintStack()
            return False, txt

    @robust
    def set(self, path, value, re=True):
        """
        当re为False时候，需要检查key是否存在，如果存在则不覆盖
        :param path:
        :param value:
        :param re:
        :return:
        """
        if re is False:
            if self.is_exist(path).content is True:
                return Result(data=0, result=ETCD_KEY_EXISTED, msg='the key is existed', code=400)
        if not isinstance(value, basestring):
            value = json.dumps(value)
        self.client.put(path, value)

    @robust
    def mkdir(self, path):
        spl = path.split('/')
        if spl[-1] != '/':
            path += '/'
        return Result(self.client.put(path, None))

    @robust
    def safe_mkdir(self, path, drop_key=False):
        spl = path.split('/')
        if spl[-1] != '/':
            path += '/'
        s = self.client.put(path, None)
        return Result(s)

    @robust
    def read(self, path, **args):
        """
        client 返回数据结构如下：
        ('test etcd set', <etcd3.client.KVMetadata object at 0x7fbbf8e306d0>)
        当传入json=True时，返回的值保持存入的数据类型
        :param path:
        :param args:
        :return:
        """
        rlt = self.client.get(path)

        if args.get('json', False):
            _, data = self._parse_2_json(rlt[0])
            return Result(data)

        return Result(rlt[0])

    @robust
    def read_path_one_file_list(self, path):
        """
        读取该目录下的下一级目录的所有文件
        注:path最后需要加上"/"
        :param path:
        :return:
        """
        # <generator object handler at 0x7f60cc1434b0>
        r = self.client.get_prefix(path)
        arr = []
        for i in r:
            spl = i[1].key.split('/')
            if len(spl) == len(path.split('/')) and i[0]:
                arr.append(spl[-1])
        return Result(arr)

    @robust
    def read_path_one_dir_list(self, path):
        pass

    @robust
    def read_map(self, path):
        """
        :param path:
        :return:
        """
        r = self.client.get_prefix(path)
        arr = {}
        for i in r:
            arr[i[1].key] = i[0]
        return Result(arr)
