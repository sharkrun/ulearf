# -*- coding: utf-8 -*-
import json
import os

import requests
from requests.auth import HTTPBasicAuth

from common.util import Result
from frame.logger import Log, PrintStack
from core.errcode import FAIL


HTTP_OK_200 = 200   #OK

class HttpsClient():
    
    __config_path = None
    
    def __init__(self, user_name, password):
        cert_path = self.get_cert_path()
        if not os.path.isfile(cert_path):
            Log(1,"The cert file [%s] is not exist."%(cert_path))
            return
        self.__config_path = cert_path
        self.user_name = user_name
        self.password = password
    
    
    def get_cert_path(self):
        workdir = os.path.dirname(os.path.abspath(__file__))
        workdir = os.path.join(workdir,"ssl")
        return os.path.join(workdir,"server.crt")
    
    def do_get(self,url, scope, service):
        param = {'scope': scope, 'service': service, 'account':self.user_name}
        auth = HTTPBasicAuth(self.user_name, self.password)
        try:
            r = requests.get(url, verify=False, auth=auth, params=param)
        except Exception, e:
            PrintStack()
            return Result('', FAIL, str(e))
        else:
            if r.status_code == HTTP_OK_200:
                return Result(r.json())
            else:
                Log(5, "do_get return status_code[%s],content[%s]"%(r.status_code, str(r.json())))
                return Result(r.json(), FAIL, 'get token fail')

    def do_post(self, url, params):
        body = json.dumps({u"body": u"Sounds great! I'll get right on it!"})
        auth = HTTPBasicAuth(self.user_name, self.password)
        r = requests.post(url, data=body, cert=('/path/server.pem'), auth=auth)
