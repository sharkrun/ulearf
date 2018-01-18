# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
from common.range import DigitRange, strRange

class SysConfig(object):
    RequestOffset    = DigitRange(30,5,300)        # 请求超前或滞后服务器时间的最大值.
    RequestTimeout   = DigitRange(30,30,60)        # 与云节点通信超时时间.
    XMLRPCPort       = DigitRange(8080,4000,65535) # 服务器XMLRPC服务的端口号.
    HeartInterval    = DigitRange(60,30,120)       # 与扩展节点心跳的时间间隔.
    SessionTimeout   = DigitRange(60,10,720)       # 管理后台session超时时间(分钟).
    CheckStockInterval = DigitRange(3,1,60)        # 补货的间隔时间.
    CloudBootSign     = strRange("CloudBoot",1,60) # cloudBoot模板的标记.
    
    store = {
        "time_offset":RequestOffset,
        "request_timeout":RequestTimeout,
        "server_port":XMLRPCPort,
        "session_timeout":SessionTimeout,
        "check_stock_interval":CheckStockInterval,
        "cloud_boot_sign":CloudBootSign
    }