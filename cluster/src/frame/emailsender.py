# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2016年6月21日

@author: Cloudsoar
'''

from email.mime.text import MIMEText
import smtplib

from common.util import Result, AESDecrypt
from frame.logger import Log, PrintStack
from core.errcode import SEND_EMAIL_FAIL_ERR
from mongoimpl.setting.logdbimpl import LogDBImpl


class EmailSender(object):
    
    def __init__(self, param):
        self.from_addr = ''
        self.username = ''
        self.password = ''
        self.senderDomainName = 'cloudsoar.com'
        self.smtphost = 'smtp.mxhichina.com'
        self.port = 25
        self.ssl = False
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
            
        if 'username' in param:
            self.username = param['username']
            
        if 'port' in param:
            self.port = int(param['port'])
            
        if 'password' in param:
            self.password = AESDecrypt(param['password'])
            
        if 'domain' in param:
            self.senderDomainName = param['domain']
            
        if 'ssl' in param:
            self.ssl = param['ssl']
        
    def send_email(self, to_addr, subject, content):
        emails = ";".join(to_addr)
        msg = self.message(emails, subject, content)
        
        try:
            smtp = smtplib.SMTP(timeout=30)
            smtp.connect(self.smtphost, self.port)
            #smtp.set_debuglevel(1)
            #smtp.ehlo()
            if self.ssl:
                smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.sendmail(self.from_addr, to_addr, msg) 
            smtp.close()
        except Exception,e:
            PrintStack()
            return Result('', SEND_EMAIL_FAIL_ERR, 'send_email subject[%s]to[%s]fail,as[%s]'%(subject, emails, str(e)))
        else:
            return Result('ok')
            
    
    def message(self, to_addr, subject, content):
        msg = MIMEText(content,_subtype='plain',_charset='gb2312')
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = to_addr
        return msg.as_string()
    
class SendTask(object):
    
    def __init__(self, email_tool, to_addr, subject, content, log_ids):
        self.status = 0
        self.email_tool = email_tool
        self.to_addr = to_addr
        self.subject = subject
        self.log_ids = log_ids
        self.log_content = content

        
    def is_finished(self):
        return self.status > 0
    
    def run(self):
        rlt = self.email_tool.send_email(self.to_addr, self.subject, self.log_content)
        if rlt.success:
            self.send_success(rlt)
        else:
            self.send_fail(rlt)
    
    def send_success(self, result):
        self.status = 1
        Log(3, 'send email to[%s][%s]success.'%(str(self.to_addr), self.subject))
        LogDBImpl.instance().send_email_success(self.log_ids, self.to_addr)
    
    def send_fail(self, result):
        self.status = 2
        Log(1, 'send email to[%s][%s] fail,as[%s]'%(str(self.to_addr), self.subject, result.message))
        LogDBImpl.instance().send_email_fail(self.log_ids, self.to_addr)
        
        
        