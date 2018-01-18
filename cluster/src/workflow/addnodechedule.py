# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月17日

@author: Jack
'''
from frame.logger import Log
from workflow.data.addnodework import AddStorageNodeWork
from workflow.task.addapplicationhost import AddApplicationHostTask
from workflow.task.addstoragehost import AddStorageHostTask
from workflow.task.checkservice import CheckServiceTask
from workflow.task.savenodeinfo import SaveNodeInfoTask
from workflow.work import Work, ADD_STORAGE_NODE_WORK


class AddNodeSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(AddNodeSchedule, self).__init__(task_info)
        self.task_type = ADD_STORAGE_NODE_WORK
        
    def new_workbench(self, work_info):
        workbench = AddStorageNodeWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'AddNodeSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench

    def pre_work(self):
        Log(3, 'AddNodeSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        self.create_task(CheckServiceTask(task_info, self.workbench))
        self.create_task(AddStorageHostTask(task_info, self.workbench))
        self.create_task(AddApplicationHostTask(task_info, self.workbench))
        self.create_task(SaveNodeInfoTask(task_info, self.workbench))

        