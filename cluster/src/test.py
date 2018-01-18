#! /usr/bin/env python
# -*- coding:utf-8 -*-

from core.deployclient import DeployClient


if __name__ == '__main__':
    r = DeployClient.instance().get_clusterrole('clu1')
    print r