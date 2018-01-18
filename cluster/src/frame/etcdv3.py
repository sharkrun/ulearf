# -*- coding: utf-8 -*-

import json
import os
import threading

import etcd3.exceptions

from common.guard import LockGuard
from common.util import Result, TreeResult
from core.const import ETCD_ROOT_PATH, ETCD_UFLEET_NODE_PATH
from core.errcode import UNCAUGHT_EXCEPTION_ERR, ETCD_CONNECT_FAIL_ERR, ETCD_KEY_EXISTED, \
    ETCD_REPLACE_FAIL_ERR, ETCD_DELETE_FAIL_ERR, INTERNAL_EXCEPT_ERR, ETCD_CREATE_KEY_FAIL_ERR, INVALID_PARAM_ERR, \
    ETCD_KEY_NOT_FOUND_ERR
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
            PrintStack()
            Log(1, "ETCDClient except:{}".format(str(e)))
            return Result(0, UNCAUGHT_EXCEPTION_ERR, str(e))
    
    
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
        if r is None:
            return Result('', ETCD_KEY_NOT_FOUND_ERR, 'value is None')
        return Result(r)

    @connect_check
    def safe_get_prefix(self, key_prefix, sort_order=None, sort_target='key'):
        if key_prefix[-1] != "/":
            key_prefix += "/"

        arr = list(self.client.get_prefix(key_prefix, sort_order, sort_target))
        return Result(arr)

    @connect_check
    def safe_get_all(self, sort_order=None, sort_target='key'):
        arr = list(self.client.get_all(sort_order, sort_target))
        return Result(arr)

    @connect_check
    def safe_put(self, key, value, lease=None):
        self.client.put(key, value, lease)
        return Result('done')

    @connect_check
    def safe_replace(self, key, initial_value, new_value):
        status = self.client.replace(key, initial_value, new_value)
        if status:
            return Result(status)
        else:
            return Result(status, ETCD_REPLACE_FAIL_ERR, '')

    @connect_check
    def safe_delete(self, key):
        status = self.client.delete(key)
        if status:
            return Result(status)
        else:
            return Result(status, ETCD_DELETE_FAIL_ERR, '')

    @connect_check
    def safe_delete_prefix(self, prefix):
        if prefix[-1] != "/":
            response = self.client.delete_prefix(prefix + "/")
            self.client.delete(prefix)
        else:
            response = self.client.delete_prefix(prefix)
        return Result(response.deleted)

    @connect_check
    def transaction(self, path, value, succes, fail):
        return self.client.transaction(
            compare=[self.client.transactions.value(path) == value],
            success=[self.client.transactions.put(path, succes)],
            failure=[self.client.transactions.put(path, fail)]
        )

    @connect_check
    def get_machines(self):
        return self.client.members()

    @connect_check
    def auto_increase(self, path, step=1):
        try:
            lock = self.client.lock(path)
            r, _ = self.client.get(path)
            data = 1
            if r is not None:
                data = int(r) + step
            self.client.put(path, str(data))
            return Result(data)
        finally:
            if lock:
                lock.release()

    @connect_check
    def update_json_value(self, path, json_data):
        try:
            lock = self.client.lock(path)
            r, _ =  self.client.get(path)
            if r is None:
                return Result(path, ETCD_KEY_NOT_FOUND_ERR, 'value is None')
        
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
        except:
            Log(3, '_parse_2_json[%s]except'%(txt))
            #PrintStack()
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
            if not value:
                continue
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
            if not value:
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

    def read_tree_list(self, key_prefix, **args):
        sort_order = args.get('sort_order')
        sort_target = args.get('sort_target', 'key')

        rlt = self.safe_get_prefix(key_prefix, sort_order, sort_target)
        if not rlt.success:
            Log(1, 'read_list[{}] fail,as[{}]'.format(key_prefix, rlt.message))
            return rlt

        arr = []
        length = len(key_prefix)
        length = 1 if length == 1 else length + 1
        keys = []

        for value, meta in rlt.content:
            data = {}
            index = meta.key.find('/', length)

            if index != -1:
                _id = meta.key[:index]
                if _id in keys:
                    continue
                keys.append(_id)

                data['parent_key'] = key_prefix
                data['leaf'] = False
                data['cls'] = 'folder'
                data['text'] = meta.key[length:index]
                data['id'] = _id
                data['qtitle'] = 'read'
                data['qtip'] = ""
            elif value:
                data['parent_key'] = key_prefix
                data['leaf'] = True
                data['cls'] = 'file'
                data['text'] = meta.key[length:]
                data['id'] = meta.key
                data['qtitle'] = 'read'
                data['qtip'] = value
            else:
                continue
            arr.append(data)

        return TreeResult(arr)

    def read_key_list(self, key_prefix, **args):
        sort_order = args.get('sort_order')
        sort_target = args.get('sort_target', 'key')

        rlt = self.safe_get_prefix(key_prefix, sort_order, sort_target)
        if not rlt.success:
            Log(1, 'read_list[{}] fail,as[{}]'.format(key_prefix, rlt.message))
            return rlt

        index = len(key_prefix) + 1
        arr = []
        for _, meta in rlt.content:
            arr.append(meta.key[index:])

        return Result(arr)

    def count(self, key_prefix, **args):
        rlt = self.safe_get_prefix(key_prefix)
        if not rlt.success:
            Log(1, 'read_list[{}] fail,as[{}]'.format(key_prefix, rlt.message))
            return rlt
        return Result(len(rlt.content))

    def is_exist(self, path):
        rlt = self.safe_get(path)
        if rlt.success:
            return True

        return False

    @connect_check
    def add_list_value(self, path, list_data):
        try:
            lock = self.client.lock(path)
            r, _ = self.client.get(path)

            is_json, value = self._parse_2_json(r)
            if is_json and isinstance(value, list):
                value.extend(list_data)
                txt = json.dumps(value)
            else:
                txt = json.dumps(list_data)

            self.client.put(path, txt)
            return Result('done')
        finally:
            if lock:
                lock.release()

    @connect_check
    def del_list_value(self, path, list_data):
        try:
            lock = self.client.lock(path)
            r, _ = self.client.get(path)

            is_json, value = self._parse_2_json(r)
            if is_json and isinstance(value, list):
                for i in list_data:
                    if i in value:
                        value.remove(i)

                txt = json.dumps(value)

                self.client.put(path, txt)
            return Result('done')
        finally:
            if lock:
                lock.release()


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
    
    def increment(self, key, step=1):
        try:
            return self.etcd.auto_increase('%s/%s'%(self.root_path, key), step=step)
        except:
            PrintStack()
            Log(1, 'increment except,as[uncautch except]')
            return Result('', INTERNAL_EXCEPT_ERR, 'increment raise except')


    def get_identity_id(self):
        """
        """
        path = "%s/%s/%s" % (ETCD_ROOT_PATH, 'identity', self.identity_key)
        try:
            rlt = self.etcd.auto_increase(path)
        except:
            PrintStack()
            Log(1, 'get_identity_id except,as[uncautch except]')
            return Result('', INTERNAL_EXCEPT_ERR, 'auto_increase raise except')

        if rlt.success:
            _id = '%x' % (rlt.content)
            return Result('%s%s' % (self.prefix, _id.rjust(8, '0')))

        Log(1, 'get_identity_id fail,as[%s]' % (rlt.message))
        return rlt

    def generate_increate_id(self, identity_key, prifix):
        path = "%s/%s/%s" % (ETCD_ROOT_PATH, 'identity', identity_key)
        try:
            rlt = self.etcd.auto_increase(path)
        except:
            PrintStack()
            Log(1, 'generate_increate_id fail,as[uncautch except]')
            return Result('', INTERNAL_EXCEPT_ERR, 'auto_increase raise except')

        if rlt.success:
            _id = '%x' % (rlt.content)
            return Result('%s%s' % (prifix, _id.rjust(8, '0')))

        Log(1, 'generate_increate_id fail,as[%s]' % (rlt.message))
        return rlt

    def read(self, key, **args):
        return self.etcd.read('%s/%s' % (self.root_path, key), **args)

    def is_key_exist(self, key=None):
        path = self.root_path if key is None else '%s/%s' % (self.root_path, key)
        return self.etcd.is_exist(path)

    def read_list(self, child_key=None, **args):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_list(path, **args)

    def count(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.count(path)

    def read_map(self, key=None, **args):
        if key:
            return self.etcd.read_map('%s/%s' % (self.root_path, key), **args)
        else:
            return self.etcd.read_map(self.root_path)

    def read_key_list(self, key=None):
        path = '%s/%s' % (self.root_path, key) if key else self.root_path
        return self.etcd.read_key_list(path)

    def read_all(self, **args):
        return self.etcd.read_list(self.root_path, **args)

    def delete(self, key):
        return self.etcd.safe_delete('%s/%s' % (self.root_path, key))

    def delete_dir(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.safe_delete_prefix(path)

    def set(self, key, value):
        return self.etcd.set('%s/%s' % (self.root_path, key), value)

    def create(self, value):
        rlt = self.get_identity_id()
        if not rlt.success:
            return Result(0, ETCD_CREATE_KEY_FAIL_ERR, 'get_identity_id fail.')

        key = rlt.content
        rlt = self.etcd.set('%s/%s' % (self.root_path, key), value)
        if not rlt.success:
            Log(1, 'ETCDMgr.create fail,as[%s]' % (rlt.message))
            return rlt

        return Result(key)

    def update_json_value(self, key, value):
        return self.etcd.update_json_value('%s/%s' % (self.root_path, key), value)

    def smart_set(self, data):
        if isinstance(data, dict):
            for k, v in data.iteritems():
                self.etcd.set('%s/%s' % (self.root_path, k), v)

            return Result(0)

        return Result(0, INVALID_PARAM_ERR, 'Not support the data.')

    def smart_delete(self, *keys):
        for key in keys:
            self.etcd.delete('%s/%s' % (self.root_path, key))
        return Result(0)

    def smart_read(self, *keys, **args):
        data = {}
        for key in keys:
            rlt = self.etcd.read('%s/%s' % (self.root_path, key), **args)
            if rlt.success:
                data[key] = rlt.content
            else:
                Log(1, 'etcd read [%s/%s]fail, as[%s]' % (self.root_path, key, rlt.message))
                data[key] = None

        return Result(data)

    def smart_read_key_list(self, *keys):
        arr = []
        for key in keys:
            rlt = self.etcd.read_key_list('%s/%s' % (self.root_path, key))
            if rlt.success:
                arr.extend(rlt.content)
            else:
                Log(1, 'etcd read_list[%s/%s]fail,as[%s]' % (self.root_path, key, rlt.message))

        return Result(arr)

    def smart_read_list(self, *keys):
        arr = []
        for key in keys:
            rlt = self.etcd.read_list('%s/%s' % (self.root_path, key))
            if rlt.success:
                arr.extend(rlt.content)
            else:
                Log(1, 'etcd read_list[%s/%s]fail,as[%s]' % (self.root_path, key, rlt.message))

        return Result(arr)

    def smart_read_map(self, *keys):
        data = {}
        for key in keys:
            rlt = self.etcd.read_map('%s/%s' % (self.root_path, key))
            if rlt.success:
                data.update(rlt.content)
            else:
                Log(1, 'etcd read_list[%s/%s]fail,as[%s]' % (self.root_path, key, rlt.message))

        return Result(data)

    def add_list_value(self, key, list_value):
        """
        # 更新value值是list类型的数据
        """
        return self.etcd.add_list_value('%s/%s/member' % (self.root_path, key), list_value)

    def del_list_value(self, key, list_value):
        """
        # 从value值是list的数据中移除一个数据
        """
        return self.etcd.del_list_value('%s/%s/member' % (self.root_path, key), list_value)

    def all_value_list(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_list(path)

    def update_int_value(self, path, int_data):
        return self.etcd.safe_put('%s/%s' % (self.root_path, path), str(int_data))
