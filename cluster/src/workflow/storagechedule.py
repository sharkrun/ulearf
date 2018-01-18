# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月17日

@author: Jack
'''
from frame.logger import Log
from workflow.data.initstoragework import InitStorageWork
from workflow.task.addlicensetask import AddLicenseTask
from workflow.task.checkservice import CheckServiceTask
from workflow.task.createcluster import CreateClusterTask
from workflow.task.savenodeinfo import SaveNodeInfoTask
from workflow.work import Work, INIT_STORAGE_CLUSTER_WORK


class StorageSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(StorageSchedule, self).__init__(task_info)
        self.task_type = INIT_STORAGE_CLUSTER_WORK
        
    def new_workbench(self, work_info):
        workbench = InitStorageWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'StorageSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench
            

    def pre_work(self):
        Log(3, 'StorageSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        self.create_task(CheckServiceTask(task_info, self.workbench))
        self.create_task(CreateClusterTask(task_info, self.workbench))
        self.create_task(AddLicenseTask(task_info, self.workbench))
        self.create_task(SaveNodeInfoTask(task_info, self.workbench))

        

        