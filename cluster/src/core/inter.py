# -*- coding: utf-8 -*-


def get_kwargs(data):
    kwargs = {}
    for (k, v) in data.items():
        kwargs[k] = v
    return kwargs
