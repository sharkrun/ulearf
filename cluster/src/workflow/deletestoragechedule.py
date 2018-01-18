# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月30日

@author: Jack
'''
from frame.logger import Log
from workflow.data.deletestoragework import DeleteStorageWork
from workflow.task.checkservice import CheckServiceTask
from workflow.task.deletecluster import DeleteClusterTask
from workflow.task.deleteclusterinfo import DeleteClusterInfoTask
from workflow.work import Work, DELETE_STORAGE_CLUSTER_WORK


class DeleteStorageSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(DeleteStorageSchedule, self).__init__(task_info)
        self.task_type = DELETE_STORAGE_CLUSTER_WORK
        
    def new_workbench(self, work_info):
        workbench = DeleteStorageWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'DeleteStorageSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench

    def pre_work(self):
        Log(3, 'DeleteStorageSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        self.create_task(CheckServiceTask(task_info, self.workbench))
        self.create_task(DeleteClusterTask(task_info, self.workbench))
        self.create_task(DeleteClusterInfoTask(task_info, self.workbench))

        