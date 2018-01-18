# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年5月23日

@author: Cloudsoar
'''



import os
import threading

from docker import Client

from common.guard import LockGuard
from common.util import Result
from frame.logger import Log, PrintStack
from frame.configmgr import GetSysConfig
from core.errcode import CALL_DOCKER_INTERFACE_FAIL_ERR, TAG_IMAGE_FAIL_ERR, \
    LOGIN_TO_REGISTRY_FAIL_ERR


class DockerClient(object):
    '''
    classdocs
    '''
    
    __lock = threading.Lock()

        
    @classmethod
    def instance(cls):
        if not os.path.exists('/var/run/docker.sock'):
            Log(1, 'DockerClient init fail,as the sock file not exist.')
            return None
        
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.registry_ct_id = GetSysConfig('registry_container_id') or 'install_registry_1'
        self.client = Client(base_url='unix://var/run/docker.sock')
        
    
    def garbage_collect(self):
        try:
            exec_id = self.client.exec_create(self.registry_ct_id, ['bin/registry', 'garbage-collect', '/etc/docker/registry/config.yml'])
            Log(3, 'exec_create return[%s]'%(str(exec_id)))

            res = b''
            for chunk in self.client.exec_start(exec_id, stream=True):
                res += chunk
            Log(3, 'garbage_collect return[%s]'%(res))
            self.client.restart(self.registry_ct_id)
        except Exception, e:
            PrintStack()
            return Result('',CALL_DOCKER_INTERFACE_FAIL_ERR, 'garbage_collect except[%s]'%(str(e)) )
        else:
            return Result(res)
    
    def net_status(self):
        return self.client.stats(self.registry_ct_id)
    
    def get_host_port(self, container, port):
        try:
            return self.client.port(container, port)[0]['HostPort']
        except Exception:
            PrintStack()
            return False
    
    def search(self, key):
        arr = self.client.search(key)
        return Result(arr)
    
    def pull(self, repository, tag='latest'):
        arr = []
        for line in self.client.pull(repository, tag, stream=True):
            arr.append(line)
        
        Log(3, 'DockerClient.pull return[%s]'%(';'.join(arr)))
        return Result(arr)

    def push(self, repository, tag):
        arr = [line for line in self.client.push(repository, tag, stream=True)]
        Log(3, 'DockerClient.push return[%s]'%(';'.join(arr)))
        return Result(arr)
    
    def tag(self, image, repository, tag):
        if self.client.tag(image, repository, tag):
            return Result('ok')
        return Result('', TAG_IMAGE_FAIL_ERR, 'tag fail.')
    
    
    def login(self, username, password, email, registry, reauth=True):
        try:
            info = self.client.login(username, password, email, registry, reauth)
            Log(3, 'DockerClient.login return[%s]'%(info))
        except Exception,e:
            PrintStack()
            return Result('', LOGIN_TO_REGISTRY_FAIL_ERR, 'Login to registry fail,as[%s]'%(str(e)))
        
        return Result(info)
        
        