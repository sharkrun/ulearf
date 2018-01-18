# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年6月21日

@author: Cloudsoar
'''


from email.mime.text import MIMEText
from frame.logger import Log
from mongodb.dbconst import ID


from twisted.internet import reactor, defer
from twisted.mail.smtp import ESMTPSenderFactory
from mongoimpl.setting.logdbimpl import LogDBImpl

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class TwistedEmailTool(object):
    def __init__(self, param):
        self.from_addr = ''
        self.username = ''
        self.password = ''
        self.senderDomainName = 'cloudsoar.com'
        self.smtphost = 'smtp.mxhichina.com'
        self.port = 25
        self.update(param)
        
    def test(self):
        if not (self.from_addr and self.username and self.password and self.smtphost and self.port):
            return False
        return True
        
    def update(self, param):
        if 'host' in param:
            self.smtphost = param['host']
            
        if 'from_addr' in param:
            self.from_addr = param['from_addr']
            self.username = param['from_addr']
            
        if 'port' in param:
            self.port = int(param['port'])
            
        if 'password' in param:
            self.password = param['password']
            
        if 'domain' in param:
            self.senderDomainName = param['domain']
        
    def send_email(self, to_addr, subject, content):
        msg = self.message(to_addr, subject, content)
        
        d = defer.Deferred()
        factory = ESMTPSenderFactory(self.username, self.password, self.from_addr, to_addr, msg, d, requireTransportSecurity=False)
        
        if self.senderDomainName is not None:
            factory.domain = self.senderDomainName
        
        reactor.connectTCP(self.smtphost, self.port, factory)

        return d
    
    def message(self, to_addr, subject, content):
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = to_addr
        return StringIO(msg.as_string())
    

class SendTask(object):
    
    def __init__(self, email_tool, to_addr, subject, log):
        self.status = 0
        self.email_tool = email_tool
        self.to_addr = to_addr
        self.subject = subject
        self.log = log

        
    def is_finished(self):
        return self.status > 0
    
    def run(self):
        self.d = self.email_tool.send_email(self.to_addr, self.subject, self.log['content'])
        self.d.addCallback(self.send_success)
        self.d.addErrback(self.send_fail)

    
    def send_success(self, result):
        self.status = 1
        Log(3, 'send email success,[%s]'%(str(result)))
        LogDBImpl.instance().send_email_success(self.log[ID], self.to_addr)
    
    def send_fail(self, result):
        self.status = 2
        Log(1, 'send email fail,[%s]'%(str(result)))
        LogDBImpl.instance().send_email_fail(self.log[ID], self.to_addr)
        
        
        