# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.
"""
这个类主要功能：
1、实现任务信息分拣，恢复，
2、实现通用数据操作
"""

import time

from etcddb.workflow.subtask import SubTaskDB
from frame.etcdv3 import ID
from frame.logger import Log
from frame.task import Task


WAIT_TASK_SUFFIX = 'WAIT'
WAIT_TASK = 'wait'
WAIT_INDEX = 0

CHECK_SERVICE_TASK_SUFFIX = 'CHECK'
CHECK_SERVICE_TASK = 'check_service'
CHECK_SERVICE_INDEX = 100

CREATE_STORAGE_CLUSTER_TASK_SUFFIX = 'CREATE'
CREATE_STORAGE_CLUSTER_TASK = 'create_storage_cluster'
CREATE_STORAGE_CLUSTER_INDEX = 200

ADD_LICENSE_TASK_SUFFIX = 'LICENSE'
ADD_LICENSE_TASK = 'add_license'
ADD_LICENSE_INDEX = 300

ADD_STRATEGY_TASK_SUFFIX = 'STRATEGY'
ADD_STRATEGY_TASK = 'add_strategy'
ADD_STRATEGY_INDEX = 400

ADD_STORAGE_TASK_SUFFIX = 'STORAGE'
ADD_STORAGE_TASK = 'add_storage'
ADD_STORAGE_INDEX = 500

ADD_APPLICATION_TASK_SUFFIX = 'APPLICATION'
ADD_APPLICATION_TASK = 'add_application'
ADD_APPLICATION_INDEX = 600


SAVE_NODE_INFO_TASK_SUFFIX = 'SAVE'
SAVE_NODE_INFO_TASK = 'save_data'
SAVE_NODE_INFO_INDEX = 700

CHECK_CAPACITY_TASK_SUFFIX = 'CHECK'
CHECK_CAPACITY_TASK = 'check_capacity'
CHECK_CAPACITY_INDEX = 101

ADD_DATA_VOLUME_TASK_SUFFIX = 'ADDVOLUME'
ADD_DATA_VOLUME_TASK = 'add_volume'
ADD_DATA_VOLUME_INDEX = 201

ADD_PV_TASK_SUFFIX = 'ADDPV'
ADD_PV_TASK = 'add_pv'
ADD_PV_INDEX = 301

ADD_PVC_TASK_SUFFIX = 'ADDPVC'
ADD_PVC_TASK = 'add_pvc'
ADD_PVC_INDEX = 401

UPDATE_PV_TASK_SUFFIX = 'UPDATEPV'
UPDATE_PV_TASK = 'update_pvc'
UPDATE_PV_INDEX = 501

DELETE_STORAGE_NODE_TASK_SUFFIX = 'DELETE'
DELETE_STORAGE_NODE_TASK = 'delete_data'
DELETE_STORAGE_NODE_INDEX = 601


DEPLOY_PROVISIONER_TASK_SUFFIX = 'DEPLOY'
DEPLOY_PROVISIONER_TASK = 'deploy_privisioner'
DEPLOY_PROVISIONER_INDEX = 302

CREATE_STORAGE_CLASS_TASK_SUFFIX = 'CREATECLASS'
CREATE_STORAGE_CLASS_TASK = 'create_storage_class'
CREATE_STORAGE_CLASS_INDEX = 402

SAVE_STORAGE_CLASS_TASK_SUFFIX = 'SAVECLASS'
SAVE_STORAGE_CLASS_TASK = 'save_storage_class'
SAVE_STORAGE_CLASS_INDEX = 502

class SubTask(Task):
    def __init__(self,task_info,suffix):
        parent_task_id = task_info.get("parent_task_id", "")
        _id = '%s%s'%(parent_task_id, suffix)
        info = {}
        self.message = ''
        self.task_type = None
        self.weight = 1
        self.progress = 0
        if _id in task_info:
            info = task_info[_id]
        else:
            info[ID] = _id
            info["parent_task_id"] = parent_task_id

        super(SubTask, self).__init__(info)
        
    def pre_work(self):
        self.save_to_db()
        
    def snapshot(self):
        snap = super(SubTask, self).snapshot()
        snap[ID] = self._id
        snap["parent_task_id"] = self.parent_task_id
        snap["task_type"] = self.task_type
        snap["progress"] = self.progress
        
        return snap
    
    def save_to_db(self):
        taskObj = self.snapshot()
        
        rlt = SubTaskDB.instance().create_task(self.parent_task_id, self._id, taskObj)
        if not rlt.success:
            Log(1,"SubTask.save_to_db[%s][%s]fail,as[%s]"%(self.parent_task_id, self._id, rlt.message))
            
    def update(self, taskObj=None):
        if taskObj is None:
            taskObj = self.snapshot()
        rlt = SubTaskDB.instance().update_to_db(self.parent_task_id, self._id, taskObj)
        if not rlt.success:
            Log(1,"SubTask.update[%s][%s] fail,as[%s]"%(self.parent_task_id, self._id, rlt.message))
            
    def end_work(self,task_rlt):
        self.progress = 100
        snap = super(SubTask, self).snapshot()
        snap["progress"] = 100
        snap["cost_time"] = time.time() * 1000 - snap.get("create_time",0)
        snap["finish_time"] = time.time() * 1000
        self.update(snap)
        
    def get_progress(self):
        return self.weight * self.progress
    
    def add_progress(self, step=1):
        self.progress += step
        self.progress = 99 if self.progress > 99 else self.progress

    
    
    
    
    
    
    
    
    
        
            
            