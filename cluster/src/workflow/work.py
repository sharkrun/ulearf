# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
这是一个调度执行的基类
"""


from common.util import Result
from core.errcode import WORK_INFO_INVALID_ERR, UNCAUGHT_EXCEPTION_ERR
from etcddb.workflow.subtask import SubTaskDB
from etcddb.workflow.work import WorkDB
from frame.etcdv3 import ID
from frame.logger import Log
from workflow.workschedule import WorkSchedule


INIT_STORAGE_CLUSTER_WORK = 'InitStorageCluster'
DELETE_STORAGE_CLUSTER_WORK = 'DeleteStorageCluster'
ADD_STORAGE_NODE_WORK = 'AddStorageNode'
DELETE_STORAGE_NODE_WORK = 'DeleteStorageNode'
ADD_PERSISTENT_VOLUME_WORK = 'AddPersistentVolume'
ADD_STORAGE_CLASS_WORK = 'AddStorageClass'

class Work(WorkSchedule):
    
    def __init__(self, task_info):
        """
        info["workbench"] = workbench
        """
        self.user_id = ''
        self.task_key = task_info.pop("task_key", '')
        workbench = task_info.pop("workbench",None)
        super(Work, self).__init__(task_info)
        if workbench is None:
            self.workbench = self.load_workbench(task_info)
        else:
            self.workbench = workbench
            
    def test(self, save=True):
        if self.workbench is None:
            return Result('', WORK_INFO_INVALID_ERR, 'workbench init fail')
        
        if save:
            return self.save_to_db()
        else:
            return Result(self._id)
    
    def get_queue_key(self, level=None):
        return self.task_type
            
    def new_workbench(self,work_info):
        """
        # 由子类构造一个工作台
        """
        
    def load_workbench(self, task_info):
        workbench_id = task_info.get("workbench_id",None)
        if workbench_id is None:
            Log(1,"Work.load_workbench fail,as[workbench_id not exist]")
            return None

        rlt = WorkDB.instance().read_work_info(workbench_id)
        if rlt.success and rlt.content:
            return self.new_workbench(rlt.content)
        else:
            Log(1,"Work.read_work_info[%s] fail,as[%s]"%(workbench_id, rlt.message))
            return None
        

    def read_sub_task_info(self):
        task_info = {"parent_task_id": self._id}
        rlt = SubTaskDB.instance().read_task_list(self._id)
        if rlt.success:
            for sub_task in rlt.content:
                _id = sub_task[ID]
                task_info[_id] = sub_task
        else:
            Log(2,"Work.read_sub_task_info[%s] fail,as[%s]"%(self._id, rlt.message))
                
        return task_info
        
    def pre_work(self):
        """
        # 由子类来实现
        """
        
    def snapshot(self):
        snap = super(Work, self).snapshot()
        snap["user_id"] = self.user_id
        snap["workbench_id"] = self.workbench._id
        snap["is_initialized"] = self.is_initialized
        snap["task_key"] = self.task_key
        return snap
            
    def update_task_state(self):
        pass
            
    def end_work(self, task_rlt):
        self.task_result = task_rlt.to_json()
        if self.is_success():
            Log(4,"work finished.")
            self.workbench.on_success()
        else:
            Log(1,"work failed.")
            self.error_code = task_rlt.result
            self.workbench.on_fail(task_rlt)
        self.update()

    def set_fail(self, reason, code=UNCAUGHT_EXCEPTION_ERR):
        if self.workbench:
            self.workbench.set_fail(reason, code)
        
        super(Work, self).set_fail(reason, code)

    
    
    