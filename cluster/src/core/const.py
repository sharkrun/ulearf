# -*- coding: utf-8 -*-

CLUSTER_INNER_VERSION = 1
ETCD_ROOT = '/ufleet'
ETCD_ROOT_PATH = '/ufleet/cluster'
ETCD_SCHEDULE = '/ufleet/schedule'
ETCD_UFLEET_NODE_PATH = '/ufleet/master'
ETCD_STORAGE_ROOT_PATH = '/ufleet/storage'
ETCD_SETTING_PATH = 'setting'
ETCD_IDENTITY_PATH = 'identity'
ETCD_VERSION_PATH = 'setting/version'
APP_VERSION = 1
TEST_GROUP = 'GroupA'
PUBLIC_GROUP = '__public__'
DEBUG = False

STORAGE_CLASS_DEFAULT_NAMESPACE = 'default'
STORAGE_CLASS_STATUS_NOT_READY = 0

class ScheduStatus(object):
    """计划任务的状态"""
    ENABLE = 1  #
    DISABLE = 0  #
    TERMINATE = -1  # 对应已删除状态


class ScheduleType():
    WEEK = "w"
    MONTH = "m"
    INTERVAL = "i"


class TaskStatus(object):
    SUCCESS = "success"
    FAIL = "fail"
    CANCEL = "cancel"
    PROCESSING = "processing"
    WAITING = "waiting"
