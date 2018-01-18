# -*- coding: utf-8 -*-
#!/usr/bin/python27
from base64 import b32encode
import os
from random import Random
import time
import traceback

from Crypto.Hash import SHA256
from M2Crypto import X509
import jwt


def PrintStack():
    with open('log', 'a') as stream:
        stream.writelines(["\n",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),"\n","-" * 100,"\n"]) 
        traceback.print_exc(None,stream)
        stream.flush()
               
def Log(level, msg):
    with open('log', 'a') as stream:
        if level >=3 :
            stream.writelines([">"])
        else:
            stream.writelines(["\n",msg])
        stream.flush()
        
    with open('operate.log', 'a') as stream:
        stream.writelines(["\n",msg])
        stream.flush()
        
def RandomNumStr(randomlength=8):
    chars = '0123456789'
    length = len(chars) - 1
    random = Random()
    s = str(chars[random.randint(1, length)])
    for _ in range(randomlength - 1):
        s += chars[random.randint(0, length)]
    return s

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
        self.Issuer = "youruncloud"
        self.Audience = "Every One"
        self.Subject = "UFleet"
        self.token_effective_time = 30 * 24 * 3600
        self.load_private_key()

        
    def get_cert_path(self):
        workdir = os.path.dirname(os.path.abspath(__file__))
        workdir = os.path.join(workdir,"ssl")
        filepath =  os.path.join(workdir,"server.crt")
        if os.path.isfile(filepath):
            return filepath
        raise Exception("cert not exist", 1000)
    
    def load_private_key(self):
        workdir = os.path.dirname(os.path.abspath(__file__))
        workdir = os.path.join(workdir,"ssl")
        filepath =  os.path.join(workdir,"server.key")
        if not os.path.isfile(filepath):
            raise Exception("private key not exist", 1000)
        
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


def main():   
    jwt = JWTImpl()
    access = {}
    print jwt.encode(access)
    


if __name__ == '__main__':
    try:
        main()
    except Exception:
        PrintStack()

