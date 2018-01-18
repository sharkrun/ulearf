# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月17日

@author: Jack
'''
from frame.logger import Log
from workflow.data.addpvwork import AddPVWork
from workflow.task.adddatavolume import AddDataVolumeTask
from workflow.task.addpv import AddPVTask
from workflow.task.addpvc import AddPVCTask
from workflow.task.checkcapacity import CheckCapacityTask
from workflow.task.mountvolume import MountVolumeTask
from workflow.task.savepvinfo import SavePVInfoTask
from workflow.work import Work, ADD_PERSISTENT_VOLUME_WORK


class AddPVSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(AddPVSchedule, self).__init__(task_info)
        self.task_type = ADD_PERSISTENT_VOLUME_WORK
        
    def new_workbench(self, work_info):
        workbench = AddPVWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'AddPVSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench

    def pre_work(self):
        Log(3, 'AddPVSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        self.create_task(CheckCapacityTask(task_info, self.workbench))
        self.create_task(AddDataVolumeTask(task_info, self.workbench))
        self.create_task(MountVolumeTask(task_info, self.workbench))
        self.create_task(AddPVTask(task_info, self.workbench))
        self.create_task(AddPVCTask(task_info, self.workbench))
        self.create_task(SavePVInfoTask(task_info, self.workbench))

        