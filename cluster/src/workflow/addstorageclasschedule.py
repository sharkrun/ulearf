# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年12月6日

@author: Jack
'''
from frame.logger import Log
from workflow.data.addstorageclasswork import AddStorageClassWork
from workflow.task.adddatavolume import AddDataVolumeTask
from workflow.task.checkcapacity import CheckCapacityTask
from workflow.task.createstorageclass import CreateStorageClassTask
from workflow.task.deployprovisioner import DeployProvisionerTask
from workflow.task.savestorageclass import SaveStorageClassInfoTask
from workflow.work import Work, ADD_STORAGE_CLASS_WORK


class AddStorageClassSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(AddStorageClassSchedule, self).__init__(task_info)
        self.task_type = ADD_STORAGE_CLASS_WORK
        
    def new_workbench(self, work_info):
        workbench = AddStorageClassWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'AddStorageClassSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench

    def pre_work(self):
        Log(3, 'AddStorageClassSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        self.create_task(CheckCapacityTask(task_info, self.workbench))
        self.create_task(AddDataVolumeTask(task_info, self.workbench))
        self.create_task(DeployProvisionerTask(task_info, self.workbench))
        self.create_task(CreateStorageClassTask(task_info, self.workbench))
        self.create_task(SaveStorageClassInfoTask(task_info, self.workbench))

        