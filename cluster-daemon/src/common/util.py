# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

import base64
from datetime import date, datetime
import hashlib
import hmac
import json
import os
import platform
from random import Random
import re
import sha
from subprocess import Popen, PIPE
import subprocess
import sys
import time

from keyczar import keyczar
from twisted.internet import defer

from core.errcode import RESULT_FORMAT_INVALID

FAULT = 1
TRUE = 0
RESULT_CONTENT = "return"
RESULT_CODE = "result"
RESULT_MSG = "message"
INNER_RESULT = "Success"
INNER_MSG = "Describe"


def generateHash(timestamp, security_key, method):
    security_key = str(security_key)
    msg = "<" + str(timestamp) + "><" + str(method) + ">"
    security_hash = base64.encodestring(
        hmac.new(security_key, msg, sha).hexdigest()).strip()
    return security_hash


def getMD5(arg):
    return str(hashlib.md5(arg).hexdigest())


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = todict(obj[k], classkey)
        return obj
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


def Object2Json(obj):
    return json.dumps(todict(obj))


# def ID2ObjectId(_id):
#    '''from string uuid to mongodb ObjectId
#    '''
#    return ObjectId(_id)


def FailResult(msg):
    return {RESULT_CODE: -1, RESULT_CONTENT: msg, RESULT_MSG: msg}


def AjaxResult(data, ret=True, msg="done"):
    '''For simple data request,e.g. string,number,dict '''
    return {"Success": ret, "Data": data, "Describe": msg}


def MsgResult(ret, desc="", msg=""):
    '''When just need the result,use this method'''
    return {"success": ret, "message": desc, "KernelMessage": msg}


def RpcResult(data, code=0, msg="done"):
    return {"result": code, "return": data, "message": msg}


# def SummaryResult


def WebSummaryListResult(_data, row_count):
    return {"RecordCount": row_count, "data": _data}


class osexecute():
    '''linux 系统指令操作工具类 '''

    @staticmethod
    def rawExec(rcmd):
        '''
        run command and wait command finished.
        @param rcmd: tuple type value for subprocess modules.
        @return: return {"result":0,"return":"","message":""}
            result: 0 for success, none zero for error.
            message: record the stderr if fail
            return: record the stdout if success
        '''
        ret = {"result": 0, "return": "", "message": ""}
        print rcmd
        f = subprocess.Popen(
            rcmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        f.wait()

        if f.returncode != 0:
            ret["message"] = repr(f.stderr.read())
            ret["result"] = f.returncode
        else:
            ret["message"] = "done"
            ret["result"] = 0
            ret["return"] = repr(f.stdout.read())

        return ret

    @staticmethod
    def ShellExec(rcmd):
        '''
        run command(with shell=True) and wait command finished.
        @param rcmd: tuple type value for subprocess modules.
        @return: return {"result":0,"return":"","message":""}
            result: 0 for success, none zero for error.
            message: record the stderr if fail
            return: record the stdout if success
        '''
        ret = {"result": 0, "return": "", "message": ""}
        print rcmd
        f = subprocess.Popen(
            rcmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        f.wait()

        if f.returncode != 0:
            ret["message"] = repr(f.stderr.read())
            ret["result"] = f.returncode
        else:
            ret["message"] = "done"
            ret["result"] = 0
            ret["return"] = repr(f.stdout.read())

        return ret


# update by tank at 2012-11-16 15:04:21
#
def currentTime(time_format="%Y-%m-%d %H:%M:%S"):
    return time.strftime(time_format, time.gmtime())


# 用逆向检查法获取指定月份的总天数
# 因为每个月的总天数最多是31天,如果转换出现异常则递减1,直到成功则返回
def getCurrentMonthDays(year=None, month=None):
    day = 31
    temp = str(currentTime('%Y-%m')).split("-")
    if not year:
        year = temp[0]
    if not month:
        month = temp[1]
    while day:
        try:
            time.strptime('%s-%s-%d' % (year, month, day), '%Y-%m-%d')
            return day
        except:
            day -= 1


def GetDynamicClass(class_name, file_name, package):
    class_full_name = package + "." + file_name
    if not sys.modules.has_key(class_full_name):
        try:
            __import__(class_full_name)
        except Exception:
            return None
    model = sys.modules.get(class_full_name)
    return getattr(model, class_name)


def analyzeAndRemoveFilterItem(my_filter):
    if not my_filter:
        return
    _keys = my_filter.keys()
    for key in _keys:
        value = my_filter.get(key)
        if isinstance(value, basestring):
            if (not value) or (not value.strip()) or value.upper() == "ALL":
                del my_filter[key]
    return my_filter


def regex_filter(_filter, regex_attrs):
    for regex_key in regex_attrs:
        if _filter.has_key(regex_key) and _filter.get(regex_key).strip():
            _filter[regex_key] = {'$regex': _filter[regex_key].strip()}
    return _filter


# 格式化日期
def getFormatCurrentTime(time_format="%Y-%m-%d %H:%M:%S"):
    return currentTime(time_format)


def isCanBetInt(value):
    if value is None:
        return False
    if isinstance(value, int):
        return True
    if not isinstance(value, basestring):
        return False
    if value.isdigit():
        return True
    return False


def isNumber(value):
    if value is None:
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return True
    if not isinstance(value, basestring):
        return False
    if value.isdigit():
        return True
    _regex = re.compile("^\d+[.]?\d{0,4}$")
    try:
        float(value)
        return True
    except Exception:
        return False
    return _regex.match(value)


def minus(list1, list2, key="uuid"):
    retlist = [
        binfo for binfo in list2
        if binfo[key] not in [ainfo[key] for ainfo in list1]
        ]
    return retlist


class LawResult(object):
    def __init__(self):
        super(LawResult, self).__init__()


class PageResult(LawResult):
    def __init__(self, DataList, total=0, identity='_id', message='ok'):
        super(PageResult, self).__init__()
        self.data = DataList
        self.identity = identity
        self.message = message
        self.total = total or len(DataList)
        self.result = 0

    @property
    def success(self):
        return True

    def __str__(self):
        return "PageResult<'total':%d,'message':'%s','return':%s>" % (
            self.total, self.message, str(self.data))

    def to_ext_result(self):
        return {
            "root": self.data,
            "total": self.total,
            "message": self.message,
            "success": True,
            "id": self.identity
        }

    def to_json(self):
        return {
            "content": self.data,
            "total": self.total,
            "message": self.message,
            "result": 0
        }


def PageCondition(**args):
    try:
        page_index = int(args.get('__pages_index', 1))
    except Exception:
        page_index = 1

    page_index = 1 if page_index < 1 else page_index

    try:
        page_number = int(args.get('__pages_number', 10))
    except Exception:
        page_number = 10

    sorts = args.get('__pages_sort', [])
    if not isinstance(sorts, list):
        sorts = [sorts]

    param = {}
    for sort in sorts:
        arr = sort.split(':')
        if len(arr) == 2:
            param[arr[0]] = 1 if arr[1] == '1' else -1

    return page_number, (page_index - 1) * page_number, param if len(
        param) == 1 else param.items()


def CPageResult(rltDict):
    if isinstance(rltDict, list):
        return PageResult(rltDict)

    if not isinstance(rltDict, dict):
        return PageResult([])

    total = 0
    content = []
    if "total" in rltDict:
        total = int(rltDict.get("total"))

    identity = rltDict.get("identity", "_id")
    msg = rltDict.get("message", "done")
    if "content" in rltDict:
        content = rltDict["content"]

    return PageResult(content, total, identity, msg)


class TreeResult(LawResult):
    def __init__(self, data, key_map):
        arr = []
        for record in data:
            arr.append(self.parse(record, key_map))

        self.data = arr

    def parse(self, record, key_map):
        return {
            'id': record.get(key_map['id'], ""),
            'text': record.get(key_map['text'], ""),
            'leaf': key_map['leaf'],
            'cls': key_map['cls'],
            'qtip': key_map['qtip'],
            'qtitle': key_map['qtitle'],
            'parentId': record.get(key_map['parent_key'], "root")
        }

    def to_ext_result(self):
        return self.data


class TreeGridResult(LawResult):
    def __init__(self, data, message="Done"):
        self.message = message
        arr = []
        for record in data:
            arr.append(self.parse(record))

        self.data = arr

    def parse(self, record):
        record["id"] = record.get("_id", "")
        record["node"] = record.get("_id", "")
        record["children"] = []
        return record

    def to_ext_result(self):
        return {"root": self.data, "message": self.message, "success": True}


class Result(LawResult):
    def __init__(self, data, result=0, msg="done", code=200):
        super(Result, self).__init__()
        self.content = data
        self.result = result
        self.message = msg
        self.code = code

    @property
    def success(self):
        return self.result == 0

    @property
    def code_info(self):
        return self.code == 200

    def __str__(self):
        return "Result<'result':%d,'message':'%s','return':%s>" % (
            self.result, self.message, str(self.content))

    def to_ext_result(self):
        return {
            "success": self.result == 0,
            "KernelMessage": self.content,
            "message": self.message
        }

    def to_json(self):
        return {
            'error_code': self.result,
            'error_msg': self.message,
            'content': self.content
        }


def StrResult(rlt_str):
    try:
        if IsStr(rlt_str):
            rltDict = json.loads(rlt_str)
        else:
            rltDict = rlt_str
    except Exception, e:
        return Result("StrResult", RESULT_FORMAT_INVALID,
                      "json.loads[%s]fail,as[%s]" % (str(e)))

    return CResult(rltDict)


def CResult(rltDict):
    if isinstance(rltDict, LawResult):
        return rltDict
    elif not isinstance(rltDict, dict):
        return Result(rltDict)
    result = 0
    content = 0
    if "result" in rltDict:
        result = int(rltDict.pop("result"))
    elif "success" in rltDict:
        result = 0 if rltDict.pop("success") else 1
    else:
        return Result(0, 1, "The result is incorrect")

    msg = rltDict.pop("message", "done")

    ## 正常情况下，这里应该只剩下一个字段，
    ## 如果超过两个，则认为，剩下的这个dict共同组成返回值。
    if len(rltDict) > 1:
        content = rltDict
    elif "content" in rltDict:
        content = rltDict["content"]
    else:
        content = rltDict

    return Result(content, result, msg)


def DateNowStr():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def UTCNowStr():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def TimestampFromStr(date_str):
    try:
        timeArray = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return int(time.mktime(timeArray))
    except:
        return 0


def TimestampToStr(timestamp, time_format='%Y-%m-%d %H:%M:%S'):
    x = time.localtime(timestamp)
    return time.strftime(time_format, x)


_DATE_REGEX = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'(?:[ T](?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})'
    r'(?:\.(?P<microsecond>\d{1,6}))?)?')


def ConvertToDatetime(timeStr):
    """
    Converts the given object to a datetime object, if possible.
    If an actual datetime object is passed, it is returned unmodified.
    If the input is a string, it is parsed as a datetime.

    Date strings are accepted in three different forms: date only (Y-m-d),
    date with time (Y-m-d H:M:S) or with date+time with microseconds
    (Y-m-d H:M:S.micro).

    :rtype: datetime
    """
    if isinstance(timeStr, datetime):
        return timeStr
    elif isinstance(timeStr, date):
        return datetime.fromordinal(timeStr.toordinal())
    elif IsStr(timeStr):
        m = _DATE_REGEX.match(timeStr)
        if not m:
            raise ValueError('Invalid date string')
        values = [(k, int(v or 0)) for k, v in m.groupdict().items()]
        values = dict(values)
        return datetime(**values)
    raise TypeError('Unsupported input type: %s' % type(timeStr))


def NowMilli():
    return int(time.time() * 1000)


def IsStr(obj):
    return isinstance(obj, unicode) or isinstance(obj, str)


def DeferResult(d):
    if not isinstance(d, defer.Deferred):
        return d

    count = 0
    while count < 30:
        count += 1
        if isinstance(getattr(d, "result", None), Result):
            return d.result
        else:
            time.sleep(1)
    return Result("", 1, "DeferResult get result fail.")


def ParseJsonStr(rlt):
    try:
        if IsStr(rlt):
            result = json.loads(rlt)
        else:
            return rlt
    except Exception, ex:
        return Result("", 1, "parse_result fail,as[%s]." % (str(ex)))
    return result


def GetDiskSummary(disk_list):
    boot_disk = ""
    data_disk = ""
    for disk in disk_list:
        if disk.get("is_boot_disk", False):
            boot_disk = "%sGB" % (disk.get("disk_size_in_gb", "0"))
        else:
            data_disk += "%sGB," % (disk.get("disk_size_in_gb", "0"))
    if data_disk:
        data_disk = data_disk[:-1]
    return boot_disk, data_disk


def GetSelfIP():
    """
    # 取本机IP地址，
    """
    osname = platform.system()
    cmd = 'ipconfig' if osname == "Windows" else "ifconfig"
    return re.search('\d+\.\d+\.\d+\.\d+',
                     Popen(cmd, stdout=PIPE).stdout.read()).group(0)


def RandomNumStr(randomlength=8):
    chars = '0123456789'
    length = len(chars) - 1
    random = Random()
    s = str(chars[random.randint(1, length)])
    for _ in range(randomlength - 1):
        s += chars[random.randint(0, length)]
    return s


def ParsePostFile(post_data):
    m = re.search(r'^-{29}.+', post_data)
    if not m:
        return post_data

    txt = m.group(0)
    index = post_data.rfind(txt)
    content = post_data[len(txt) + 1:index]

    m = re.search(r'^Content-Disposition:.+\nContent-Type:.+\n', content)
    if not m:
        return content

    txt = m.group(0)
    return content[len(txt):].strip()


def IsValidNamespace(namespace):
    m = re.match("([a-z0-9]+(?:[._-][a-z0-9]+)*)", namespace)
    if not m:
        return False

    return m.group(1) == namespace


def ParseNamespace(repository, default_name_space=''):
    arr = repository.split('/')
    return default_name_space if len(arr) < 2 else arr[0]


def CalculateDigest(filepath):
    if not os.path.isfile(filepath):
        return False

    sh = hashlib.sha256()
    with open(filepath, "rb") as fd:
        sh.update(fd.read())

    return sh.hexdigest()


def AESEncrypt(msg, sec_dir='frame/conf/AES'):
    if not os.path.isdir(sec_dir):
        return False

    if not msg:
        return msg

    crypter = keyczar.Crypter.Read(sec_dir)
    return crypter.Encrypt(msg)


def AESDecrypt(text, sec_dir='frame/conf/AES'):
    if not os.path.isdir(sec_dir):
        return False

    if not text:
        return text

    crypter = keyczar.Crypter.Read(sec_dir)
    return crypter.Decrypt(text)


def Base64Decode(pwd):
    try:
        return base64.decodestring(pwd)
    except:
        return pwd


def utc2local(utc_st):
    """UTC时间转本地时间（+8:00）"""
    now_stamp = time.time()
    local_time = datetime.fromtimestamp(now_stamp)
    utc_time = datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return local_st
