# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

from common.inter import my_request
from common.timer import Timer
from common.util import Result, NowMilli
from core.errcode import USER_RESPONSE_DATA_INVALID_ERR, \
    CALL_REMOTE_API_FAIL_ERR, INVALID_PARAM_ERR
from frame.configmgr import GetSysConfig
from frame.logger import Log


class UserClient(object):
    """
    # 对接用户模块
    """

    def __init__(self):
        self.domain = GetSysConfig('user_server_addr')
        self.__store = {}
        # CURLClient.__init__(self, domain)
        self.timer = Timer(10, self, 'UserTokenCheck')
        self.timer.start()

    def timeout(self):
        if len(self.__store) == 0:
            return

        data = {}
        for k, v in self.__store.items():
            if v['expire'] > NowMilli():
                data[k] = v
        self.__store = data

    def parse_token(self, token_str):
        if not token_str:
            Log(3, 'Unauthorized visit.')
            return {'ring': 'ring8'}

        if isinstance(token_str, list):
            token_str = token_str[0]

        data = self.__store.get(token_str, None)
        if data:
            return data['passport']

        passport = self._parse_token(token_str)
        if passport:
            self.__store[token_str] = {'passport': passport, 'expire': NowMilli() + 60000}

        return passport

    def _parse_token(self, token_str):
        rlt = self.get_user_info(token_str)
        if not rlt.success:
            Log(3, "parse token get_user_info error not success:{}, token:{}".format(rlt.message, token_str))
            return None

        passport = rlt.content.get('systemProfile', {})
        passport.update(rlt.content.get('profile', {}))
        passport['username'] = rlt.content.get('username', '')
        passport['id'] = rlt.content.get('id', '')
        passport['licensed'] = rlt.content.get('licensed', '')
        role = rlt.content.get('role', '')

        if role == 'superadmin':
            passport['ring'] = 'ring0'
        elif role == 'admin':
            passport['ring'] = 'ring3'
        elif passport.get('isActive', False) and passport.get('isValid', False):
            passport['ring'] = 'ring5'

            result = self.get_user_group(rlt.content.get('id'), token_str)
            if result.success:
                passport['group'] = result.content
            else:
                passport['group'] = []

        else:
            passport['ring'] = 'ring8'

        return passport

    def get_user_info(self, token_str):
        """
         "systemProfile": {
            "authType": "string",
            "createTime": 0,
            "isActive": true,
            "isSuperAdmin": true,
            "isValid": true,
            "lastLogin": 0
          },
        """
        url = "http://" + self.domain + '/v1/user/verify/' + token_str
        r = my_request(url=url, method='GET', timeout=5, headers={"token": token_str})
        if r.success:
            r = r.content
            if r.status_code == 200:
                data = r.json()
                if data is None:
                    return Result('', USER_RESPONSE_DATA_INVALID_ERR, 'get_user_info data parse to json fail.')
                return Result(data)
            else:
                return Result('', r.status_code, r.text, r.status_code)
        else:
            # response.log('UserClient.get_user_info')
            Log(1, "user auth :{},url:{}".format(r.message, url))
            return Result('', CALL_REMOTE_API_FAIL_ERR, 'get_user_info fail,as{}.'.format(r.message))

    def get_user_group(self, user_id, token_str):
        if not user_id:
            # Log(1, 'get_user_group fail,as user_id[%s]invalid' % (str(user_id)))
            return Result('', INVALID_PARAM_ERR, 'user_id invalid')

        url = "http://" + self.domain + '/v1/usergroup/user/' + user_id
        r = my_request(url=url, method='GET', timeout=5, headers={"token": token_str})
        if r.success:
            r = r.content
            if r.status_code == 200:
                data = r.json()
                if data is None:
                    return Result('', USER_RESPONSE_DATA_INVALID_ERR, 'get_user_group data parse to json fail.')
                return Result(data)
            else:
                return Result('', r.status_code, r.text, r.status_code)
        else:
            # response.log('UserClient.get_user_group')
            return Result('', CALL_REMOTE_API_FAIL_ERR, 'get_user_group fail,as{},url:{}'.format(r.message, url))