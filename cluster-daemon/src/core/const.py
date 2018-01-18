# -*- coding: utf-8 -*-

ETCD_ROOT_PATH = '/ufleet/cluster'
ETCD_UFLEET_NODE_PATH = '/ufleet/master'
ETCD_SETTING_PATH = 'setting'
ETCD_IDENTITY_PATH = 'identity'
ETCD_VERSION_PATH = 'setting/version'
APP_VERSION = 1
TEST_GROUP = 'GroupA'
PUBLIC_GROUP = '__public__'
DEBUG = False
class ScheduStatus(object):
    """计划任务的状态"""
    ENABLE = 1     #
    DISABLE = 0    # 
    TERMINATE = -1 # 对应已删除状态
    
class ScheduleType():
    WEEK = "w"
    MONTH = "m"
    INTERVAL = "i"
    
class TaskStatus(object):
    SUCCESS    = "success"  
    FAIL       = "fail"
    CANCEL     = "cancel"
    PROCESSING = "processing" 
    WAITING    = "waiting"
