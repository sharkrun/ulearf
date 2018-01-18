# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年4月7日

@author: Cloudsoar
'''

from base64 import b32encode
import os
import time

from Crypto.Hash import SHA256
from M2Crypto import X509
import jwt

from common.util import RandomNumStr
from frame.logger import PrintStack
from frame.configmgr import GetSysConfig, GetSysConfigInt
from core.errcode import CERT_NOT_EXIST_ERR
from frame.exception import InternalException


class JWTImpl(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        self.load_cert()
        self.typ = 'JWT'
        self.alg = 'RS256'
        self.header = {"typ":self.typ,"alg":self.alg,"kid":self.kid}
        self.Issuer = GetSysConfig('registry_issuer')
        self.Audience = GetSysConfig('registry_service')
        self.token_effective_time = GetSysConfigInt('token_effective_time', 24) * 3600
        self.load_private_key()
        
    def set_account(self, account):
        self.Subject = account
        
    def create_token(self, act_info):
        self.Subject = act_info['Account']
        if act_info['Service'] != self.Audience:
            return {'msg':'registry service and this service must be the same'}
        
        return {'token':self.encode(act_info['Scopes'])}
        
    def get_cert_path(self):
        workdir = os.path.dirname(os.path.abspath(__file__))
        workdir = os.path.join(workdir,"ssl")
        filepath =  os.path.join(workdir,"server.crt")
        if os.path.isfile(filepath):
            return filepath
        raise InternalException("cert not exist", CERT_NOT_EXIST_ERR)
    
    def load_private_key(self):
        workdir = os.path.dirname(os.path.abspath(__file__))
        workdir = os.path.join(workdir,"ssl")
        filepath =  os.path.join(workdir,"server.key")
        if not os.path.isfile(filepath):
            raise InternalException("private key not exist", CERT_NOT_EXIST_ERR)
        
        with open(filepath) as keyfile:
            self.key = keyfile.read()
        
    def load_cert(self):
        cert_path = self.get_cert_path()
        with open(cert_path) as certfile:
            key = certfile.read()
        self.cert = X509.load_cert_string(key)
        self.kid = self.key_id(self.cert)
    
    def encode(self, access):
        now = int(time.time())
        payload = {"iss":self.Issuer,
                      "sub":self.Subject,
                      "aud":self.Audience,
                      "exp":now + self.token_effective_time,
                      "nbf":now - 1,
                      "iat":now,
                      "jti":RandomNumStr(19),
                      "access":access}
        try:
            return jwt.encode(payload, self.key, algorithm=self.alg, headers=self.header)
        except Exception:
            PrintStack()
            return ''

    
    def decode(self):
        pass    
    
    def key_id(self, cert):
        pub = cert.get_pubkey()
        
        _hash = SHA256.new()
        _hash.update(pub.as_der())
        txt = _hash.digest()
        return self.key_id_encode(txt[:30])
        
        
    def key_id_encode(self, txt):
        s = b32encode(txt).rstrip('=')
        
        arr = []
        count = len(s)/4-1
        for i in range(count):
            start = i * 4
            end = start + 4
            arr.append(s[start:end])
        arr.append(s[count * 4:])
        return ':'.join(arr)

