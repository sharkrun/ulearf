# -*- coding: utf-8 -*-
# Copyright (c) 20016-2017 The Cloudsoar.
# See LICENSE for details.
'''
Created on 2017年8月30日

@author: Jack
'''
from frame.logger import Log
from workflow.data.deletenodework import DeleteStorageNodeWork
from workflow.task.deleteapplicationhost import DeleteApplicationHostTask
from workflow.task.deletedatadisk import DeleteDataDiskTask
from workflow.task.deletenodeinfo import DeleteNodeInfoTask
from workflow.task.deletepv import DeletePVTask
from workflow.task.deletestorageclass import DeleteStorageClassTask
from workflow.task.deletestoragehost import DeleteStorageHostTask
from workflow.work import Work, DELETE_STORAGE_NODE_WORK


class DeleteNodeSchedule(Work):
    '''
    classdocs
    '''

    def __init__(self, task_info):
        '''
        Constructor
        '''
        super(DeleteNodeSchedule, self).__init__(task_info)
        self.task_type = DELETE_STORAGE_NODE_WORK
        
    def new_workbench(self, work_info):
        workbench = DeleteStorageNodeWork(work_info)
        rlt = workbench.check_valid()
        if not rlt.success:
            Log(1, 'DeleteNodeSchedule.new_workbench fail,as[%s]'%(rlt.message))
            return None
        
        return workbench

    def pre_work(self):
        Log(3, 'DeleteNodeSchedule begin')

        task_info = {"parent_task_id":self._id}
        if self.is_initialed():
            task_info = self.read_sub_task_info()

        #self.create_task(CheckServiceTask(task_info, self.workbench))
        self.create_task(DeletePVTask(task_info, self.workbench))
        self.create_task(DeleteStorageClassTask(task_info, self.workbench))
        self.create_task(DeleteDataDiskTask(task_info, self.workbench))
        self.create_task(DeleteApplicationHostTask(task_info, self.workbench))
        self.create_task(DeleteStorageHostTask(task_info, self.workbench))
        self.create_task(DeleteNodeInfoTask(task_info, self.workbench))

        