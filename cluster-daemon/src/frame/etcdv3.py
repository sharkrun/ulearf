# -*- coding: utf-8 -*-

import json
import os
import threading

import etcd3.exceptions

from common.guard import LockGuard
from common.util import Result
from core.const import ETCD_ROOT_PATH, ETCD_UFLEET_NODE_PATH
from core.errcode import UNCAUGHT_EXCEPTION_ERR, ETCD_CONNECT_FAIL_ERR, ETCD_KEY_EXISTED, ETCD_DELETE_FAIL_ERR
from frame.configmgr import GetSysConfig, GetSysConfigInt
from frame.logger import Log, PrintStack

ID = '_id'


def connect_check(query):
    def do_query(*args, **keyargs):
        try:
            return query(*args, **keyargs)
        except etcd3.exceptions.ConnectionFailedError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd3.exceptions.ConnectionTimeoutError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd connect timeout')
        except etcd3.exceptions.InternalServerError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd interal server error')
        except etcd3.exceptions.PreconditionFailedError:
            return Result(False, ETCD_CONNECT_FAIL_ERR, 'Etcd precdition failed error')
        except Exception as e:
            Log(1, "ETCDClient error:{}".format(e.message))
            return Result(0, UNCAUGHT_EXCEPTION_ERR, e.message)

    def etcd_safe_query(self, *args, **keyargs):
        if self.client:
            return do_query(self, *args, **keyargs)

        self.connect()
        if self.client:
            return do_query(self, *args, **keyargs)
        else:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'etcd not ready')

    return etcd_safe_query


class ETCDClient(object):
    __lock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.client = None
        self.connect()

    def connect(self):
        host = GetSysConfig('etcd_host')
        port = GetSysConfigInt('etcd_port', 2379)

        cfg = {'port': port, 'timeout': 10}
        if host is not None:
            cfg['host'] = host

        try:
            self.client = etcd3.client(**cfg)
        except:
            PrintStack()

    @connect_check
    def safe_get(self, path):
        r, _ = self.client.get(path)
        return Result(r)

    @connect_check
    def safe_get_prefix(self, key_prefix, sort_order=None, sort_target='key'):
        if key_prefix[-1] != "/":
            key_prefix += "/"

        arr = list(self.client.get_prefix(key_prefix, sort_order, sort_target))
        return Result(arr)

    @connect_check
    def safe_put(self, key, value, lease=None):
        self.client.put(key, value, lease)
        return Result('done')

    @connect_check
    def safe_delete(self, key):
        status = self.client.delete(key)
        if status:
            return Result(status)
        else:
            return Result(status, ETCD_DELETE_FAIL_ERR, '')

    @connect_check
    def transaction(self, path, value, succes, fail):
        return self.client.transaction(
            compare=[self.client.transactions.value(path) == value],
            success=[self.client.transactions.put(path, succes)],
            failure=[self.client.transactions.put(path, fail)]
        )

    @connect_check
    def update_json_value(self, path, json_data):
        try:
            lock = self.client.lock(path)
            r, _ = self.client.get(path)

            is_json, value = self._parse_2_json(r)
            if is_json:
                value.update(json_data)
                txt = json.dumps(value)
            else:
                txt = json.dumps(json_data)

            self.client.put(path, txt)
            return Result('done')
        finally:
            if lock:
                lock.release()

    def _parse_2_json(self, txt):
        try:
            return True, json.loads(txt)
        except TypeError:
            return False, txt
        except Exception as e:
            Log(1, "e:{}".format(e))
            PrintStack()
            return False, txt

    def set(self, path, value, recover=True):
        if not recover:
            rlt = self.safe_get(path)
            if rlt.success and rlt.content:
                return Result("", ETCD_KEY_EXISTED, 'the key is existed')

        if not isinstance(value, basestring):
            value = json.dumps(value)
        else:
            value = value.encode('utf8')

        return self.safe_put(path, value)

    def read_map(self, key_prefix, sort_order=None, sort_target='key'):
        rlt = self.safe_get_prefix(key_prefix, sort_order, sort_target)
        if not rlt.success:
            Log(1, 'read_map[{}] fail,as[{}]'.format(key_prefix, rlt.message))
            return rlt

        arr = {}

        for value, meta in rlt.content:
            _, data = self._parse_2_json(value)
            arr[meta.key] = data
        return Result(arr)

    def read(self, path, **args):
        rlt = self.safe_get(path)
        if not rlt.success:
            return rlt

        if args.get('json', True):
            _, data = self._parse_2_json(rlt.content)
            return Result(data)

        return rlt

    def read_list(self, key_prefix, **args):
        sort_order = args.get('sort_order')
        sort_target = args.get('sort_target', 'key')

        rlt = self.safe_get_prefix(key_prefix, sort_order, sort_target)
        if not rlt.success:
            Log(1, 'read_list[{}] fail,as[{}]'.format(key_prefix, rlt.message))
            return rlt

        length = len(key_prefix) + 1
        suffix = args.get('suffix', '')
        suffix_length = len(suffix)

        skip = args.get('skip_suffix', '')
        skip_length = len(skip)

        key_id = args.get('key_id', ID)

        arr = []
        for value, meta in rlt.content:
            if 0 == len(value):
                continue

            if suffix_length and meta.key[-suffix_length:] != suffix:
                continue

            if skip_length and meta.key[-skip_length:] == skip:
                continue

            is_json, value = self._parse_2_json(value)
            if is_json:
                value[key_id] = meta.key[length:]
                arr.append(value)
            else:
                arr.append({key_id: meta.key[length:], 'value': value})

        return Result(arr)

    def is_exist(self, path):
        rlt = self.safe_get(path)
        if rlt.success and rlt.content is not None:
            return True

        return False


class ETCDMgr(object):
    def __init__(self, identity_key, root_path=ETCD_ROOT_PATH):
        self.prefix = ''
        self.identity_key = identity_key
        self.root_path = "%s/%s" % (root_path, identity_key)
        self.etcd = ETCDClient.instance()
        self.ufleet_id = os.environ.get('UFLEET_NODE_ID')

    def ismaster(self):
        if not self.ufleet_id:
            return True

        rlt = self.etcd.read(ETCD_UFLEET_NODE_PATH, json=True)
        if not rlt.success:
            Log(1, 'read master statu info fail')
            return False

        if isinstance(rlt.content, dict):
            return rlt.content.get('id') == self.ufleet_id

        return False

    def read(self, key, **args):
        return self.etcd.read('%s/%s' % (self.root_path, key), **args)

    def is_key_exist(self, key=None):
        path = self.root_path if key is None else '%s/%s' % (self.root_path, key)
        return self.etcd.is_exist(path)

    def read_list(self, child_key=None, **args):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_list(path, **args)

    def read_map(self, key=None, **args):
        if key:
            return self.etcd.read_map('%s/%s' % (self.root_path, key), **args)
        else:
            return self.etcd.read_map(self.root_path)

    def delete(self, key):
        return self.etcd.safe_delete('%s/%s' % (self.root_path, key))

    def set(self, key, value):
        return self.etcd.set('%s/%s' % (self.root_path, key), value)

    def update_json_value(self, key, value):
        return self.etcd.update_json_value('%s/%s' % (self.root_path, key), value)

    def all_value_list(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_list(path)

    def update_int_value(self, path, int_data):
        return self.etcd.safe_put('%s/%s' % (self.root_path, path), str(int_data))
