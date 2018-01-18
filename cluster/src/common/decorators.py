# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from frame.logger import Log
from common.util import Result

def detail_route(methods=None, **kwargs):
    """
    Used to mark a method on a ViewSet that should be routed for detail requests.
    """
    methods = ['get'] if (methods is None) else methods

    def decorator(func):
        func.bind_to_methods = methods
        func.detail = True
        func.kwargs = kwargs
        return func
    return decorator


def list_route(methods=None, **kwargs):
    """
    Used to mark a method on a ViewSet that should be routed for list requests.
    """
    methods = ['get'] if (methods is None) else methods

    def decorator(func):
        func.bind_to_methods = methods
        func.detail = False
        func.kwargs = kwargs
        return func
    return decorator


def requestexcept(actual_do):
    def f(*args, **kwargs):
        try:
            return actual_do(*args, **kwargs)
        except Exception as e:
            Log(1, "{0} error:{1}".format(actual_do.__name__, e.message))
            return Result('', 400, msg=e.message, code=400)

    return f