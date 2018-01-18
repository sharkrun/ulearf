# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年2月15日

@author: Cloudsoar
'''

from __builtin__ import isinstance
import json
import os
from random import Random
import threading
from time import sleep

import etcd

from common.guard import LockGuard
from common.util import Result, TreeResult
from core.const import ETCD_ROOT_PATH, ETCD_UFLEET_NODE_PATH
from core.errcode import ETCD_KEY_NOT_FOUND_ERR, INVALID_PARAM_ERR, \
    UNCAUGHT_EXCEPTION_ERR, ETCD_CONNECT_FAIL_ERR, \
    ETCD_EXCEPTION_ERR, ETCD_CREATE_KEY_FAIL_ERR, \
    INTERNAL_EXCEPT_ERR, ETCD_UPDATE_FAIL_ERR
from frame.configmgr import GetSysConfig, GetSysConfigInt
from frame.logger import Log, PrintStack

ID = '_id'


class ETCDClient(object):
    '''
    classdocs
    '''

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
        reconnect = GetSysConfig('etcd_allow_reconnect')
        protocol = GetSysConfig('etcd_protocol')

        cfg = {'port': port, 'read_timeout': 10}
        if host is not None:
            cfg['host'] = host

        if reconnect is not None:
            cfg['allow_reconnect'] = True if reconnect == '1' else False

        if protocol in ['http', 'https']:
            cfg['protocol'] = protocol

        self.client = etcd.Client(**cfg)

    def set(self, path, value, is_json=True):
        try:
            if not isinstance(value, basestring) and is_json:
                value = json.dumps(value)
            else:
                value = value.encode('utf8')
            self.client.write(path, value)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.set catch uncaught except')

        return Result(0)

    def mkdir(self, path):
        try:
            self.client.write(path, None, dir=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdException, e:
            return Result(0, ETCD_EXCEPTION_ERR, 'mkdir [%s] fail,as[%s].' % (path, str(e.payload)))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.mkdir catch uncaught except')

        return Result(0)

    def read(self, path, **args):
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        if args.get('json', True):
            _, data = self._parse_2_json(rlt.value)
            return Result(data)

        return Result(rlt.value)

    def watch(self, path):
        try:
            data = self.client.watch(path, recursive=True)
            return Result(data)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path [%s] is not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

    def is_exist(self, path):
        """
        读取key是否存在
        :param path:
        :return:
        """
        try:
            Log(4, "etcd is_exit:{}".format(path))
            self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(False)
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        return Result(True)
    

    def read_map(self, path):
        """
        读取map值 {'<path/path/>': '<value>', '<path/path>': '<value>'}其中value为写入时的类型，value为None不返回
        :param path:
        :return:
        """
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        arr = {}
        for child in r.children:
            if child.value:
                _, value = self._parse_2_json(child.value)
                arr[child.key] = value
        return Result(arr)

    def all_value_list(self, path):
        """
        返回所有value
        :param path:
        :return: []
        """
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        arr = []
        for child in r.children:
            if child.value:
                arr.append(json.loads(child.value))
        return Result(arr)


    def read_list(self, path, **args):
        """
        # 获取下一级value列表 [*] or [{'key': '', 'value': ''}]
        :param path:
        :param args:
        :return:
        """
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            Log(4, 'read_list fail,as The path[%s]not exist.'%(path))
            return Result([])
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        arr = []
        length = len(path) + 1
        suffix = args.get('suffix', '')
        suffix_length = len(suffix)

        skip = args.get('skip_suffix', '')
        skip_length = len(skip)

        key_id = args.get('key_id', ID)

        for child in r._children:
            if suffix_length and child['key'][-suffix_length:] != suffix:
                continue

            if skip_length and child['key'][-skip_length:] == skip:
                continue

            if child.get('dir', False):
                continue

            is_json, value = self._parse_2_json(child['value'])
            if is_json:
                value[key_id] = child['key'][length:]
                arr.append(value)
            else:
                arr.append({key_id: child['key'][length:], 'value': value})

        return Result(arr)

    def read_tree_list(self, path, **args):
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        arr = []
        length = len(path) + 1

        for child in r._children:
            data = {}
            data['parent_key'] = path
            data['leaf'] = False if child.get('dir', False) else True
            data['cls'] = 'folder' if child.get('dir', False) else 'file'
            data['text'] = child['key'][length:]
            data['id'] = child['key']
            data['qtitle'] = 'read'
            data['qtip'] = child.get('value', 'folder')
            data['createdIndex'] = child.get('createdIndex', -1)
            data['modifiedIndex'] = child.get('modifiedIndex', -1)
            arr.append(data)

        return TreeResult(arr)

    def _parse_2_json(self, txt):
        try:
            return True, json.loads(txt)
        except:
            # PrintStack()
            return False, txt

    def read_key_list(self, path):
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        index = len(path) + 1
        arr = []
        for child in r._children:
            arr.append(child['key'][index:])

        return Result(arr)
    
    def count(self, path):
        try:
            r = self.client.read(path, recursive=True, sorted=True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read catch uncaught except')

        return Result(len(r._children))

    def delete(self, path):
        try:
            self.client.delete(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'Etcd key not found')
        except etcd.EtcdException, e:
            return Result(0, ETCD_EXCEPTION_ERR, 'delete [%s] fail,as[%s].' % (path, str(e.payload)))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.read delete uncaught except')

        return Result(0)

    def delete_dir(self, path):
        try:
            self.client.delete(path, True, True)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'Etcd key not found')
        except etcd.EtcdException, e:
            return Result(0, ETCD_EXCEPTION_ERR, 'delete dir [%s] fail,as[%s].' % (path, str(e.payload)))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.delete_dir catch uncaught except')
        return Result(0)

    def get_leader(self):
        return self.client.leader

    def get_machines(self):
        return self.client.machines

    def auto_increase(self, path):
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            self.client.write(path, 1)
            return Result(1)

        updated = True
        while updated:
            rlt.value = int(rlt.value) + 1
            updated = self.client.update(rlt)
            if updated:
                return Result(int(updated.value))

            random = Random()
            s = random.randrange(0.001, 0.1)
            sleep(s)
            rlt = self.client.read(path)

    def add_list_value(self, path, list_data):
        """
        :param path:
        :param list_data:
        :return:
        """
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        Log(4, "add_list_value:{}".format(rlt.value))
        value = json.loads(rlt.value)
        rlt.value = json.dumps(value + list_data)
        result = self.client.update(rlt)
        if result:
            return Result('')
        return Result('', ETCD_UPDATE_FAIL_ERR, 'update_list_value fail.')

    def del_list_value(self, path, v):
        """
        :param path:
        :param list_data:
        :return:
        """
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        Log(4, "add_list_value:{}".format(rlt.value))
        value = json.loads(rlt.value)
        for i in v:
            if i in value:
                value.remove(i)
        rlt.value = json.dumps(value)
        result = self.client.update(rlt)
        if result:
            return Result('')
        return Result('', ETCD_UPDATE_FAIL_ERR, 'update_list_value fail.')
    
    def update_int_value(self, path, int_data):
        """
        :param path:
        :param int_data:
        :return:
        """
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))
        except:
            PrintStack()
            return Result(0, UNCAUGHT_EXCEPTION_ERR, 'ETCDClient.delete_dir catch uncaught except')

        rlt.value = json.dumps(int_data)

        result = self.client.update(rlt)
        if result:
            return Result('')

        return Result('', ETCD_UPDATE_FAIL_ERR, 'update_json_value fail.')


    def update_json_value(self, path, json_data):
        """
        当传入{}格式数据，则部分更新 否则全部替换
        :param path:
        :param json_data:
        :return:
        """
        try:
            rlt = self.client.read(path)
        except etcd.EtcdConnectionFailed:
            return Result(0, ETCD_CONNECT_FAIL_ERR, 'Etcd Connection Failed.')
        except etcd.EtcdKeyNotFound:
            return Result(0, ETCD_KEY_NOT_FOUND_ERR, 'The path[%s]not exist.' % (path))

        is_json, value = self._parse_2_json(rlt.value)
        if is_json:
            value.update(json_data)
            rlt.value = json.dumps(value)
        else:
            rlt.value = json.dumps(json_data)

        result = self.client.update(rlt)
        if result:
            return Result('')

        return Result('', ETCD_UPDATE_FAIL_ERR, 'update_json_value fail.')


class ETCDMgr(object):
    def __init__(self, identity_key, root_path=ETCD_ROOT_PATH):
        self.prefix = ''
        self.identity_key = identity_key
        self.root_path = "%s%s" % (root_path, identity_key)
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

    def get_identity_id(self):
        """
        """
        path = "%s/%s/%s" % (ETCD_ROOT_PATH, 'identity', self.identity_key)
        try:
            rlt = self.etcd.auto_increase(path)
        except:
            PrintStack()
            Log(1, 'get_identity_id fail,as[uncautch except]')
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
        """
        查看key是否存在
        :param key:
        :return:
        """
        path = self.root_path if key is None else '%s/%s' % (self.root_path, key)
        rlt = self.etcd.is_exist(path)
        if not rlt.success:
            Log(1, 'ETCDMgr.is_key_exist[%s]fail,as[%s]' % (path, rlt.message))
            return False

        return rlt.content

    def read_key_map(self, child_key=None):
        """
        :param child_key:
        :return:
        """
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_key_map(path)

    def all_value_list(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.all_value_list(path)

    def read_list(self, child_key=None, **args):
        """
        读取下一级的所有 [key:value]
        :param args:
        :return:
        """
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_list(path, **args)

    def count(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.count(path)


    def read_map(self, key=None):
        if key:
            return self.etcd.read_map('%s/%s' % (self.root_path, key))
        else:
            return self.etcd.read_map(self.root_path)

    def read_key_list(self, child_key=None):
        """
        读取该key下一级的所有key值
        :param child_key:
        :return:
        """
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.read_key_list(path)

    def delete(self, key):
        return self.etcd.delete('%s/%s' % (self.root_path, key))

    def delete_dir(self, child_key=None):
        path = self.root_path + '/' + child_key if child_key else self.root_path
        return self.etcd.delete_dir(path)

    def set(self, key, value, is_json=True):
        return self.etcd.set('%s/%s' % (self.root_path, key), value, is_json)

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

    def add_list_value(self, key, list_value):
        """
        更新value值是list类型的数据
        :param key:
        :param value:
        :return:
        """
        return self.etcd.add_list_value('%s/%s/member' % (self.root_path, key), list_value)

    def del_list_value(self, key, list_value):
        """
        从value值是list的数据中移除一个数据
        :param key:
        :param list_value: []
        :return:
        """
        return self.etcd.del_list_value('%s/%s/member' % (self.root_path, key), list_value)

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


class CacheEtcd(ETCDMgr):
    def __init__(self, identity_key, root_path=None, sub_dir=None):
        ETCDMgr.__init__(self, identity_key, root_path)
        self.sub_dir = sub_dir
        self.__store = self.load_data(sub_dir)

    def reload(self):
        return self.load_data(self.sub_dir)

    def load_data(self, sub_dir=None):
        if sub_dir is None:
            root_path = self.root_path
        else:
            root_path = '%s/%s' % (self.root_path, sub_dir)

        rlt = self.etcd.read_key_list(root_path)
        if not rlt.success:
            Log(1, 'ETCDMgr.load data[%s] fail,as[%s]' % (root_path, rlt.message))
            return {}

        data = {}
        for key in rlt.content:
            result = self.etcd.read_key_list('%s/%s' % (root_path, key))
            if result.success:
                for sub_key in result.content:
                    data[sub_key] = key

        return result(data)

    def add_cache(self, key, value):
        if isinstance(key, basestring) and value is not None:
            self.__store[key] = value
            return True
        else:
            Log(1, 'add_cache[%s=%s] fail,as' % (str(key), str(value)))
            return False

    def delele_cache(self, key):
        self.__store.pop(key)

    def get_key(self, key):
        if key not in self.__store:
            Log(1, 'key[%s] not in cache, reload' % (key))
            self.reload()

        return self.__store.get(key, None)


class TagMgr(ETCDMgr):
    def __init__(self, tag, cache=True):
        ETCDMgr.__init__(self, 'tag')
        self.tag = tag
        self.prefix = ''

    def add_tag(self, key, value=1):
        self.set("%s/%s" % (self.tag, key), value)

    def delete_tag(self, key):
        self.delete("%s/%s" % (self.tag, key))

    def has_tag(self, key):
        return self.is_key_exist("%s/%s" % (self.tag, key))

    def get_all_data(self):
        return self.read_list(self.tag)
