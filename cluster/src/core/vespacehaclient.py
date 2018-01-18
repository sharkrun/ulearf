# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年10月19日

@author: Cloudsoar
'''

import time

from core.vespaceclient import VeSpaceClient
from frame.curlclient import Response, HTTP_EXCEPTION, HEADER_HOST, HEADER_DATE, \
    HEADER_AUTH
from frame.exception import InternalException
from frame.logger import Log, PrintStack


HA_URL_STR = '[HA-URL]'

class VeSpaceHAClient(VeSpaceClient):
    '''
    classdocs
    '''

    def __init__(self, domains, username, password):
        VeSpaceClient.__init__(self, HA_URL_STR, username, password)
        self.ha_domains = domains
        self._cluster_leader = ""
        
    def callRemote(self, url, method, token=None, post_data=None, **args):
        if url.find(HA_URL_STR) < 0:
            return self.single_call_remote(url, method, token, post_data, **args)
        
        return self.ha_call_remote(url, method, token, post_data, **args)
        
    def get_cluster_leader(self):
        if self._cluster_leader:
            return self._cluster_leader
        
        for domain in self.ha_domains:
            rlt = self.members(domain)
            if rlt.success:
                self._cluster_leader = rlt.content.get('leader')
                break
            else:
                Log(1, 'get_cluster_leader from [%s]fail,as[%s]'%(domain, rlt.message))
            
        return self._cluster_leader
        
    def single_call_remote(self, url, method, token, post_data, **args):
        try:
            domain = args.pop('domain','')
            return self._call_remote(domain, url, method, token, post_data, **args)
        except InternalException,e:
            Log(1, '_call_remote[%s][%s]except[%s]'%(domain, url, e.value))

        return Response('', '', HTTP_EXCEPTION, '')
    
    def ha_call_remote(self, url, method, token, post_data, **args):
        for _ in range(2):
            try:
                domain = self.get_cluster_leader()
                if not domain:
                    return Response('', '', HTTP_EXCEPTION, '')
                
                url = url.replace(HA_URL_STR, domain)
                return self._call_remote(domain, url, method, token, post_data, **args)
            except InternalException,e:
                Log(1, '_call_remote[%s][%s]except[%s]'%(domain, url, e.value))
                self._cluster_leader = ""
                continue
        
        return Response('', '', HTTP_EXCEPTION, '')

 
    def _call_remote(self, current_domain, url, method, token, post_data, retry=False, **args):
        if token is None:
            token = self.get_token(current_domain)
            
        Headers = self.getBasicHeaders(token, **args)
        Headers.append(HEADER_HOST + ": " + current_domain)
        
        response = self.send_http_request(url, Headers, method, post_data)
        Log(4, "HA _call_remote[%s][%s]return[%s]"% (method, url, response.respond_body))
        
        if response.success:
            data = response.json_data()
            if data and data.get('ecode') == 2799:
                raise InternalException(data.get('message'), 2799)
            
        return response
                

    
    def getBasicHeaders(self, token=None, **args):
        '''
        return the basic required headers
        '''
        if 'Header' in args:
            Header = args['Header']
        else:
            Header = []

        # Header.append( 'Content-Type: application/json' )
        Header.append(HEADER_DATE + ": " + time.strftime("%a, %d %b %Y %X +0000", time.gmtime()))

        if token:
            Header.append(HEADER_AUTH + ": Bearer %s" % (token))
        return Header
    
    
    def test(self):
        if self._cluster_leader:
            return True
        
        try:
            if self.get_cluster_leader():
                return True
        except Exception,e:
            PrintStack()
            Log(1, 'VeSpaceClient.test.login except,as[%s]'%(str(e)))
            
        return False

    