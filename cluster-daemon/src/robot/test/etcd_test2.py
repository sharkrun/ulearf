# -*- coding: utf-8 -*-

'''
Created on 2017年2月23日

@author: Cloudsoar
'''

import unittest

from etcd import EtcdException, EtcdKeyNotFound, EtcdNotDir
import etcd


class TestEtcdMethods(unittest.TestCase):
    """
    # 测试把key当成目录
    1、创建目录/test
    2、读取目录信息/test
    3、写入key /test/key1
    4、写入key /test/key1/subkey
    5、删除/test/key1
    6、重复删除/test/key1
    7、创建目录/test/key1
    8、读取目录/test/key1
    9、删除目录/test/key1
    10、重复删除目录/test/key1
    
    
    """
    def setUp(self):
        cfg = {'port':2379}
        self.client = etcd.Client(**cfg)

    def tearDown(self):
        pass
    

    def test_1_mkdir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 155, '_children': [], 'createdIndex': 88, 'modifiedIndex': 88, 'value': None, 
        'etcd_index': 88, 'expiration': None, 'key': u'/test', 'ttl': None, 'action': u'set', 'dir': True})
        """
        rlt = self.client.write('/test', None, dir=True)
        print 'test_1_mkdir:'
        print str(rlt)
        self.assertTrue(rlt)

    def test_2_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 155, '_children': [], 'createdIndex': 88, 'modifiedIndex': 88, 'value': None, 
        'etcd_index': 88, 'expiration': None, 'key': u'/test', 'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test')
        print 'test_2_read_dir:'
        print str(rlt)
        self.assertTrue(rlt)
        
    def test_3_write_key(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 156, '_children': [], 'createdIndex': 89, 'modifiedIndex': 89, 'value': u'key1', 
        'etcd_index': 89, 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': u'set', 'dir': False})
        """
        rlt = self.client.write('/test/key1', 'key1')
        print 'test_3_write_key:'
        print str(rlt)
        self.assertTrue(rlt)
        
    def test_4_write_sub_key(self):
        """
        """
        with self.assertRaises(EtcdNotDir):
            self.client.write('/test/key1/subkey', 'subkey')

        
    def test_5_delete_key(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>({'newKey': False, '_children': [], 'createdIndex': 89, 
        'modifiedIndex': 89, 'value': u'key1', 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': None, 'dir': False}), 'raft_index':
        158, '_children': [], 'createdIndex': 89, 'modifiedIndex': 90, 'value': None, 'etcd_index': 90, 'expiration': None, 'key': u'/test/key1', 
        'ttl': None, 'action': u'delete', 'dir': False})
        """
        rlt = self.client.delete('/test/key1', True, True)
        print 'test_5_delete_key:'
        print str(rlt)
        self.assertTrue(rlt)

            
    def test_6_delete_key(self):
        """
        """
        with self.assertRaises(EtcdKeyNotFound):
            self.client.delete('/test/key1')

        
    def test_7_mkdir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 160, '_children': [], 'createdIndex': 91, 'modifiedIndex': 91, 'value': None, 
        'etcd_index': 91, 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': u'set', 'dir': True})
        """
        rlt = self.client.write('/test/key1', None, dir=True)
        print 'test_7_mkdir:'
        print str(rlt)
        self.assertTrue(rlt)
        
    def test_8_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 160, '_children': [], 'createdIndex': 91, 'modifiedIndex': 91, 'value': None, 
        'etcd_index': 91, 'expiration': None, 'key': u'/test/key1', 'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test/key1')
        print 'test_8_read_dir:'
        print str(rlt)
        self.assertTrue(rlt)
          
    def test_9_delete_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>({'newKey': False, '_children': [], 'createdIndex': 88,
        'modifiedIndex': 88, 'value': None, 'expiration': None, 'key': u'/test', 'ttl': None, 'action': None, 'dir': True}), 'raft_index': 161, 
        '_children': [], 'createdIndex': 88, 'modifiedIndex': 92, 'value': None, 'etcd_index': 92, 'expiration': None, 'key': u'/test', 'ttl': None,
        'action': u'delete', 'dir': True})
        """
        rlt = self.client.delete('/test', True, True)
        print 'test_9_delete_dir:'
        print str(rlt)
        self.assertTrue(rlt)
             
    def test_10_delete_dir1(self):
        with self.assertRaises(EtcdException):
            self.client.delete('/test', True, True)


if __name__ == '__main__':
    unittest.main()
