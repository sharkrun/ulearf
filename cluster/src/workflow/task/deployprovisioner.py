# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
"""
给集群添加license
"""

from common.util import Result
from frame.exception import InternalException
from frame.logger import PrintStack, Log
from frame.subtask import SubTask, DEPLOY_PROVISIONER_TASK_SUFFIX, DEPLOY_PROVISIONER_TASK, \
    DEPLOY_PROVISIONER_INDEX


class DeployProvisionerTask(SubTask):
    
    def __init__(self, task_info, workbench):
        super(DeployProvisionerTask, self).__init__(task_info, DEPLOY_PROVISIONER_TASK_SUFFIX)
        self.task_type = DEPLOY_PROVISIONER_TASK
        self.index = DEPLOY_PROVISIONER_INDEX
        self.weight = 0.8
        self.workbench = workbench
    
    def launch_task(self):
        Log(4,"DeployProvisionerTask.launch_task")
        try:
            rlt = self.workbench.deploy_provisioner()
            if rlt.success:
                self.log("deploy_provisioner success.")
            else:
                self.log("deploy_provisioner fail. as[%s]"%(rlt.message))
                return rlt
                    
        except InternalException,ex:
            self.log("DeployProvisionerTask deploy fail,as[%s]"%(ex.value),ex.errid)
            return Result('InternalException', ex.errid, "DeployProvisionerTask launch_task fail,as[%s]"%(ex.value))
                
        except Exception,e:
            PrintStack()
            self.log("launch_task except[%s]"%(str(e)))
            Log(1,"DeployProvisionerTask launch_task fail,as[%s]"%(str(e)))
            return Result(self._id, 1, "DeployProvisionerTask launch_task fail,as[%s]"%(str(e)))
        
        return Result(self._id)

    def snapshot(self):
        snap = super(DeployProvisionerTask, self).snapshot()
        return snap
        
    
    def rollback(self):
        """
        # rollback 由外部触发，任务本身失败了，不会触发rollback
        """
        Log(4,"DeployProvisionerTask.rollback")
        rlt = self.workbench.uninstall_provisioner()
        if rlt.success:
            self.log("uninstall_provisioner success.")
        else:
            self.log("uninstall_provisioner fail. as[%s]"%(rlt.message))
        return rlt

        