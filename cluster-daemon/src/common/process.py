#! /usr/bin/env python
# -*- coding:utf-8 -*-

# 启动一个线程用户管理多线程


import threading
import time
import datetime
from frame.logger import Log
from frame.logger import PrintStack
import os


def process_start(s_time, task):
    try:
        while True:
            t1 = datetime.datetime.now()
            p = threading.Thread(target=task.timeout, args=())
            # p.setDaemon(True)
            p.start()
            p.join()  # 等待子线程执行完成才继续往下执行  p.setDaemon(True)则相反，不会等待p结束，就会直接往下执行
            Log(3, "task:{}, pid:{}, ppid:{}, run timeout cost:{}".format(task, os.getpid(), os.getppid(), datetime.datetime.now() - t1))
            time.sleep(s_time)
    except Exception as e:
        PrintStack()
        Log(1, 'process_start error:{}'.format(e.message))