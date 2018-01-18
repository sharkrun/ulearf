# -*- coding: utf-8 -*-

'''
Created on 2017年2月23日

@author: Cloudsoar
'''

import os
import unittest

from etcd import EtcdException, EtcdKeyNotFound, EtcdNotFile
import etcd

os.chdir('../')


class TestEtcdMethods(unittest.TestCase):
    """
    1、创建目录
    2、读取目录信息
    3、写入key1
    4、重复写入key1
    5、删除目录的方式删除key1
    6、正常删除key1
    7、重复删除key1
    8、删除key的方式删除dir
    9、删除dir
    10、重复删除dir
    
    
    """

    def setUp(self):
        cfg = {'port': 2379}
        self.client = etcd.Client(**cfg)

    def tearDown(self):
        pass

    def test_1_mkdir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 54, '_children': [], 
        'createdIndex': 27, 'modifiedIndex': 27, 'value': None, 'etcd_index': 27, 
        'expiration': None, 'key': u'/test', 'ttl': None, 'action': u'set', 'dir': True})
        """
        rlt = self.client.write('/test', None, dir=True)
        print str(rlt)
        self.assertTrue(rlt)

    def test_2_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 54, '_children': [], 
        'createdIndex': 27, 'modifiedIndex': 27, 'value': None, 
        'etcd_index': 27, 'expiration': None, 'key': u'/test', 
        'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test')
        print str(rlt)
        self.assertTrue(rlt)

    def test_3_write_key(self):
        """
        EtcdResult: <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 58, '_children': [], 'createdIndex': 30, 
         'modifiedIndex': 30, 'value': u'key1', 'etcd_index': 30, 'expiration': None, 'key': u'/test/key1', 'ttl': None, 
         'action': u'set', 'dir': False})
        """
        rlt = self.client.write('/test/key1', 'key1')
        print str(rlt)
        self.assertTrue(rlt)

    def test_4_write_key2(self):
        """
         EtcdResult: <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>
         ({'newKey': False, '_children': [], 'createdIndex': 35, 'modifiedIndex': 35, 'value': u'key1', 'expiration': 
         None, 'key': u'/test/key1', 'ttl': None, 'action': None, 'dir': False}), 'raft_index': 66, '_children': [], 
         'createdIndex': 36, 'modifiedIndex': 36, 'value': u'key2', 'etcd_index': 36, 'expiration': None, 'key': 
         u'/test/key1', 'ttl': None, 'action': u'set', 'dir': False})
        """
        rlt = self.client.write('/test/key1', 'key2')
        print str(rlt)
        self.assertTrue(rlt)

    def test_5_delete_key_as_dir(self):
        """
        EtcdResult: <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>
         ({'newKey': False, '_children': [], 'createdIndex': 56, 'modifiedIndex': 56, 'value': u'key2', 'expiration': 
         None, 'key': u'/test/key1', 'ttl': None, 'action': None, 'dir': False}), 'raft_index': 101, '_children': [], 
         'createdIndex': 56, 'modifiedIndex': 57, 'value': None, 'etcd_index': 57, 'expiration': None, 'key': 
         u'/test/key1', 'ttl': None, 'action': u'delete', 'dir': False})
        """
        rlt = self.client.delete('/test/key1', True, True)
        print str(rlt)
        self.assertTrue(rlt)

    def test_6_delete_key(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>({'newKey': False, '_children': [], 'createdIndex': 36, 'modifiedIndex': 36,
        'value': u'key2', 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': None, 'dir': False}), 'raft_index': 67, '_children': [], 'createdIndex': 36,
        'modifiedIndex': 37, 'value': None, 'etcd_index': 37, 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': u'delete', 'dir': False})
        """
        with self.assertRaises(EtcdKeyNotFound):
            self.client.delete('/test/key1')

    def test_7_delete_key2(self):
        """
        """
        with self.assertRaises(EtcdKeyNotFound):
            self.client.delete('/test/key1')

    def test_8_delete_dir_as_key(self):
        """
        """
        with self.assertRaises(EtcdNotFile):
            self.client.delete('/test')

    def test_9_delete_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node':
         <class 'etcd.EtcdResult'>({'newKey': False, '_children': [], 'createdIndex': 27, 
         'modifiedIndex': 27, 'value': None, 'expiration': None, 'key': u'/test', 'ttl': None, 
         'action': None, 'dir': True}),
          'raft_index': 55, '_children': [], 'createdIndex': 27, 'modifiedIndex': 28, 
          'value': None, 'etcd_index': 28, 'expiration': None, 'key': u'/test', 
          'ttl': None, 'action': u'delete', 'dir': True})
        """
        rlt = self.client.delete('/test', True, True)
        print str(rlt)
        self.assertTrue(rlt)

    def test_10_delete_dir1(self):
        with self.assertRaises(EtcdException):
            self.client.delete('/test', True, True)


if __name__ == '__main__':
    unittest.main()
