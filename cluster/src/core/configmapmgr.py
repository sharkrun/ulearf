# -*- coding: utf-8 -*-

"""
#configmap 接口
"""
import threading
from common.guard import LockGuard
from common.util import NowMilli
from etcddb.configmapmgr import ConfigMapdb
from common.util import Result
from core.errcode import CONFIGMAP_EXISTED, ETCD_KEY_NOT_FOUND_ERR
from common.datatype import configmap_struct
from frame.auditlogger import WebLog
from core.kubeclientmgr import KubeClientMgr
from etcddb.kubernetes.workspacemgr import WorkSpacedb
from frame.logger import Log
import json
import yaml


class ConfigMapMgr(object):
    """
    """
    __lock = threading.Lock()
    __rlock = threading.Lock()

    @classmethod
    def instance(cls):
        with LockGuard(cls.__lock):
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.__gdata = {}
        self.__wsdata = {}
        self.__allvalue = []
        self.expiry_time = 0
        self.loaddata()

    def reload(self, flush=0):
        if flush == 1:
            self.loaddata()
        else:
            if self.expiry_time <= NowMilli():
                self.loaddata()

    def _parse_2_json(self, txt):
        try:
            return True, json.loads(txt)
        except:
            # PrintStack()
            return False, txt

    def loaddata(self):
        """
        加载configmap信息到内存中
        :return:
        """
        rlt = ConfigMapdb.instance().read_all_configmap()
        if not rlt.success:
            return rlt
        g_data = {}
        ws_data = {}
        for _, v in rlt.content.items():
            g_data.setdefault(v.get('group'), []).append(v)
            ws_data.setdefault(v.get('workspace'), []).append(v)
        self.__gdata = g_data
        self.__wsdata = ws_data
        self.__allvalue = rlt.content.values()

    def get_by_group(self, group):
        """
        获取所有configmap
        :return:
        """
        self.reload()
        return Result(self.__gdata.get(group, []))

    def get_all(self):
        """
        :return:
        """
        self.reload()
        return Result(self.__gdata)

    def creat_configmap(self, data):
        """
        创建configmap
        :param data:
        :return:
        """
        # 检查版本在workspace下否存在
        if ConfigMapdb.instance().is_existed(data.get('workspace'), data.get('name') + data.get('version')):
            return Result('', CONFIGMAP_EXISTED, 'is existed', 400)

        # 检查workspace是否存在
        rlt = WorkSpacedb.instance().read_all_gws()
        if not rlt.success:
            return rlt
        group_info = rlt.content.get(data.get('group'), [])
        if data.get('workspace') not in group_info:
            return Result('', 400, 'the workspace not in the group', 400)

        try:
            content = json.loads(data.get('content'))
            Log(4, "content1:{}".format(content))
        except ValueError:
            content = yaml.load(data.get('content'))
            Log(4, "content2:{}".format(content))
        except Exception as e:
            return Result('', 400, str(e.message), 400)

        c_data = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": data.get('name')+data.get('version')},
                  "data": content}

        Log(4, 'content:{}'.format(data.get('content', '')))

        rlt = KubeClientMgr.instance().create_configmap(data.get('workspace'), c_data)
        if not rlt.success:
            Log(3, "create_configmap error:{}".format(rlt.message))
            return rlt

        # 保存到etcd
        data['conf_keys'] = content.keys()
        con = configmap_struct(data)
        rlt = ConfigMapdb.instance().save_configmap(data.get('workspace'), data.get('name') + data.get('version'),
                                                    con)
        if not rlt.success:
            return rlt

        WebLog(3, u'创建', u"configmap[{}]".format(data.get('name', '') + data.get('version', '')), data.get('creater'))
        self.reload(1)
        return Result('')

    def delete(self, workspace, conf_name, username):
        """
        删除config
        :param name:
        :param version:
        :return:
        """
        rlt = ConfigMapdb.instance().read_configmap(workspace, conf_name)
        if not rlt.success:
            if rlt.result == ETCD_KEY_NOT_FOUND_ERR:
                return Result('', 400, 'the configmap[{}] not existed'.format(conf_name), 400)
            return rlt

        # 删除etcd中数据
        rlt = ConfigMapdb.instance().del_configmap(workspace, conf_name)
        if not rlt.success:
            if rlt.result != ETCD_KEY_NOT_FOUND_ERR:
                WebLog(3, u'删除', u"workspace[{}]下的configmap[{}]".format(workspace, conf_name), username)
                self.reload(1)
                return rlt

        # 通过apiserver删除configmap
        rlt = KubeClientMgr.instance().delete_configmap(workspace, conf_name)
        if not rlt.success:
            Log(1, "configmap delete get kubeclient error:{}".format(rlt.message))
            # if rlt.code == 404 or rlt.result == FAIL or rlt.result == ETCD_KEY_NOT_FOUND_ERR:
            #     pass
            # else:
            return rlt

        return Result('')

    def get_by_ws(self, workspace):
        """
        unique=True 只返回最新的configmap版本
        :param workspace:
        :return:
        """
        self.reload()
        r_data = self.__wsdata.get(workspace, [])
        r_d = {}
        for i in r_data:
            r_d.setdefault(i['name'], []).append(i)
        # for k, v in r_d.values():
        #
        #     r_d1.setdefault()
        return Result(r_d)

        # d = []
        # r_d = {}
        # for i in r_data:
        #     r_d.setdefault(i['name'], []).append(i)
        # all_v = r_d.values()
        # for v in all_v:
        #     for i in v:
        #         i['create_time'] = datetime.datetime.strptime(i['create_time'], "%Y-%m-%d %H:%M:%S")
        #     v = sorted(v, key=itemgetter('create_time'))
        #     if v:
        #         d.append(v[-1])
        # for i in d:
        #     i['create_time'] = datetime.datetime.strftime(i['create_time'], "%Y-%m-%d %H:%M:%S")
        # return Result(d)
