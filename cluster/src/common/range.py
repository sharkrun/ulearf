# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.
from common.util import IsStr

"""
用于用户输入检查的配置文件
"""


class DigitRange(object):
    def __init__(self, default, _min, _max):
        self.default = default
        self.min = _min
        self.max = _max

    def check(self, value):
        if self.is_invalid(value):
            return self.default
        return value

    def is_invalid(self, value):
        return type(value) != type(1) or value < self.min or value > self.max


class strRange(DigitRange):
    def __init__(self, default, _min, _max):
        super(strRange, self).__init__(default, _min, _max)

    def is_invalid(self, value):
        return not IsStr(value) or len(value) < self.min or len(value) > self.max
