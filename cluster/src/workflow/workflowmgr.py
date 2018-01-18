# -*- coding: utf-8 -*-
# Copyright (c) 2007-2012 The PowerallNetworks.
# See LICENSE for details.
"""
实现操作类型的任务管理
"""

import json
import threading

from common.guard import LockGuard
from common.timer import Timer
from common.util import Result
from core.errcode import FAIL, INVALID_JSON_DATA_ERR
from etcddb.workflow.task import TaskDB
from frame.authen import ring0, ring3, ring5
from frame.logger import Log, PrintStack
from frame.taskschedumgr import TaskScheduMgr
from workflow.addnodechedule import AddNodeSchedule
from workflow.addpvchedule import AddPVSchedule
from workflow.addstorageclasschedule import AddStorageClassSchedule
from workflow.deletenodechedule import DeleteNodeSchedule
from workflow.deletestoragechedule import DeleteStorageSchedule
from workflow.storagechedule import StorageSchedule
from workflow.work import INIT_STORAGE_CLUSTER_WORK, ADD_STORAGE_NODE_WORK, \
    DELETE_STORAGE_CLUSTER_WORK, DELETE_STORAGE_NODE_WORK


class WorkFlowMgr(TaskScheduMgr):
    
    __lock = threading.Lock()
    
    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        thread_num = 3
        schedule_name = 'WorkFlow'
        super(WorkFlowMgr,self).__init__(thread_num, schedule_name)
        schedu_timer = Timer(10, self, "WorkFlowDriver")
        schedu_timer.start()
        
                
    def load_schedu_list(self):
        type_list = [INIT_STORAGE_CLUSTER_WORK, ADD_STORAGE_NODE_WORK]
        rlt = TaskDB.instance().read_interrupt_task_list(type_list)
        if not rlt.success:
            Log(1,"load_task_schedu_list fail,as[%s]"%(rlt.message))
            return
        for task_info in rlt.content:
            try:
                self.load_task(task_info)
            except Exception,e:
                PrintStack()
                Log(1,"load_task fail,as[%s]"%(str(e)))

            
    def load_task(self, task_info):
        task_type = task_info.get("task_type",None)
        if not task_type:
            Log(1,"WorkFlowMgr.load_task invalid task info [%s]"%(str(task_info)))
            return Result(0,FAIL,"The key[task_type] is not exist.")
            
        task = None
        is_slow_task = False
        if task_type == INIT_STORAGE_CLUSTER_WORK:
            task = StorageSchedule(task_info)
        elif task_type == ADD_STORAGE_NODE_WORK:
            task = AddNodeSchedule(task_info)
        elif task_type == DELETE_STORAGE_CLUSTER_WORK:
            task = DeleteStorageSchedule(task_info)
        elif task_type == DELETE_STORAGE_NODE_WORK:
            task = DeleteNodeSchedule(task_info)
        else:
            Log(1,"WorkFlowMgr.load_task invalid task_type [%s]"%(task_type))
            return Result(0,FAIL,"The task type[%s]is invalid."%(task_type))
        Log(4, "task........:{}, is_slow_task:{}".format(task, is_slow_task))
        if task:
            rlt = task.test(False)
            if not rlt.success:
                Log(1, 'load_task[%s]fail,as[%s]'%(str(task_info), rlt.message))
                return rlt
            
            rlt = self.create_slow_task(task) if is_slow_task else self.create_task(task)
            if not rlt.success:
                Log(1,"load task[%s]fail,as[%s]"%(str(task_info),rlt.message))
            Log(4, "**********:{}".format(rlt))
            return rlt
        
        return Result(0,FAIL,"Construct the task object fail.")
    
    
    @ring0
    @ring3
    @ring5
    def myTasks(self, **args):
        user_id = args.get('passport',{}).get('access_uuid','')
        
        arr = []
        for tsk in self.task_store.values():
            if user_id == tsk.user_id:
                arr.append(tsk.get_task_status())
                
        return Result(arr)
    
    @ring0
    @ring3
    @ring5
    def delete_task(self, post_data, **args):
        try:
            _filter = json.loads(post_data.replace("'", "\'"))
            arr = []
            for task_id in _filter['id_list']:
                arr.append(int(task_id))
                
        except Exception,e:
            Log(1,"delete_task.parse data to json fail,input[%s]"%(post_data))
            return Result('',INVALID_JSON_DATA_ERR,str(e))
        
        user_id = args.get('passport',{}).get('access_uuid','')
        
        result = {}
        for task_id in arr:
            result[task_id] = self.drop_task(user_id, task_id)
                
        return Result(result)
    
    
    def create_init_storage_cluster_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task_data["task_key"] = task_data['cluster_name']
        task = StorageSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt
        
        self.delete_init_storage_cluster_task(task._id, task_data['cluster_name'])
        
        return self.create_task(task)
    
    def create_delete_storage_cluster_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task_data["task_key"] = task_data['cluster_name']
        task = DeleteStorageSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt
        
        return self.create_task(task)

    def create_add_storage_host_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task_data["task_key"] = '%s-%s'%(task_data['cluster_name'], task_data['ip'])
        task = AddNodeSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt
        
        self.delete_add_storage_host_task(task._id, task_data['cluster_name'], task_data['ip'])
        
        return self.create_task(task)
    
    def create_delete_storage_host_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task_data["task_key"] = '%s-%s'%(task_data['cluster_name'], task_data['ip'])
        task = DeleteNodeSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt
        
        return self.create_task(task)    
    
    def create_persistent_volume_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task = AddPVSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt

        return self.create_task(task)
   
    def delete_init_storage_cluster_task(self, task_id, cluster_name):
        rlt = TaskDB.instance().get_task_id_by_key(INIT_STORAGE_CLUSTER_WORK, cluster_name, task_id)
        if not rlt.success:
            Log(3, 'delete_init_storage_cluster_task get_schedule_id fail,as[%s]'%(rlt.message))
            return rlt
    
        return self.cancel_task(rlt.content)
        
    def delete_add_storage_host_task(self, task_id, cluster_name, host_ip):
        key = '%s-%s'%(cluster_name, host_ip)
        rlt = TaskDB.instance().get_task_id_by_key(ADD_STORAGE_NODE_WORK, key, task_id)
        if not rlt.success:
            Log(3, 'delete_add_storage_host_task get_schedule_id fail,as[%s]'%(rlt.message))
            return rlt
    
        return self.cancel_task(rlt.content)
    
    
    def create_storage_class_task(self, task_data, workbench):
        task_data["workbench"] = workbench
        task = AddStorageClassSchedule(task_data)
        rlt = task.test()
        if not rlt.success:
            return rlt

        return self.create_task(task)

