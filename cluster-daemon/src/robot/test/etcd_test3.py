# -*- coding: utf-8 -*-

'''
Created on 2017年2月23日

@author: Cloudsoar
'''

import unittest

from etcd import EtcdNotFile
import etcd


class TestEtcdMethods(unittest.TestCase):
    """
    # 先创建第三级目录，再创建第二级目录
    1、创建目录  /test/dir1/dir2/dir3
    2、读取目录信息 /test/dir1/dir2/dir3
    3、创建目录  /test/dir1
    4、读取目录信息 /test/dir1/dir2
    5、读取目录信息 /test/dir1
    6、删除目录/test

    
    
    """
    def setUp(self):
        cfg = {'port':2379}
        self.client = etcd.Client(**cfg)

    def tearDown(self):
        pass
    

    def test_1_mkdir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': True, 'raft_index': 172, '_children': [], 'createdIndex': 99, 'modifiedIndex': 99, 
        'value': None, 'etcd_index': 99, 'expiration': None, 'key': u'/test/dir1/dir2/dir3', 'ttl': None, 'action': u'set', 'dir': True})
        """
        rlt = self.client.write('/test/dir1/dir2/dir3', None, dir=True)
        print 'test_1_mkdir:'
        print str(rlt)
        self.assertTrue(rlt)

    def test_2_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 172, '_children': [], 'createdIndex': 99, 'modifiedIndex': 99, 
        'value': None, 'etcd_index': 99, 'expiration': None, 'key': u'/test/dir1/dir2/dir3', 'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test/dir1/dir2/dir3')
        print 'test_2_read_dir:'
        print str(rlt)
        self.assertTrue(rlt)
        
    def test_3_mkdir_dir(self):
        """
        """
        with self.assertRaises(EtcdNotFile):
            self.client.write('/test/dir1', None, dir=True)
            
    def test_4_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 173, '_children': [{u'createdIndex': 99, u'modifiedIndex': 99, 
        u'dir': True, u'key': u'/test/dir1/dir2/dir3'}], 'createdIndex': 99, 'modifiedIndex': 99, 'value': None, 'etcd_index': 99, 
        'expiration': None, 'key': u'/test/dir1/dir2', 'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test/dir1/dir2')
        print 'test_4_read_dir:'
        print str(rlt)
        self.assertTrue(rlt)
        
    def test_5_read_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, 'raft_index': 173, '_children': [{u'createdIndex': 99, u'modifiedIndex': 99, 
        u'dir': True, u'key': u'/test/dir1/dir2'}], 'createdIndex': 99, 'modifiedIndex': 99, 'value': None, 'etcd_index': 99, 
        'expiration': None, 'key': u'/test/dir1', 'ttl': None, 'action': u'get', 'dir': True})
        """
        rlt = self.client.read('/test/dir1')
        print 'test_5_read_dir:'
        print str(rlt)
        self.assertTrue(rlt)

          
    def test_6_delete_dir(self):
        """
        <class 'etcd.EtcdResult'>({'newKey': False, '_prev_node': <class 'etcd.EtcdResult'>({'newKey': False, '_children': [], 
        'createdIndex': 99, 'modifiedIndex': 99, 'value': None, 'expiration': None, 'key': u'/test', 'ttl': None, 'action': None, 
        'dir': True}), 'raft_index': 174, '_children': [], 'createdIndex': 99, 'modifiedIndex': 100, 'value': None, 'etcd_index': 100, 
        'expiration': None, 'key': u'/test', 'ttl': None, 'action': u'delete', 'dir': True})
        """
        rlt = self.client.delete('/test', True, True)
        print 'test_6_delete_dir:'
        print str(rlt)
        self.assertTrue(rlt)


if __name__ == '__main__':
    unittest.main()
