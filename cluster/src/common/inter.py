# -*- coding: utf-8 -*-

import threading
from frame.logger import Log, PrintStack
import time
import Queue
import requests
from common.util import Result


def my_request(url, method, timeout, data=None, headers=None):
    """
    :param url:
    :param method:
    :param timeout:
    :param data:
    :return:
    headers={"content-type": "application/json", "token": "1234567890987654321"}
    """
    try:
        if method == 'GET':
            r = requests.get(url=url, headers=headers, timeout=timeout)
            return Result(r)
        elif method == 'DELETE':
            r = requests.delete(url, timeout=timeout)
            return Result(r)
        elif method == 'POST':
            r = requests.post(url=url, data=data, headers=headers, timeout=timeout)
            return Result(r)
        elif method == 'PUT':
            r = requests.put(url=url, headers=headers, timeout=timeout)
            return Result(r)
        else:
            return Result('', 400, 'method error')
    except requests.exceptions.RequestException as e:
        Log(4, "my_request error:{}".format(e.message))
        return Result('', msg=str(e), result=500)


class Factory(threading.Thread):
    """
    生产者消费者模型中的消费值
    """
    def __init__(self, task_queue, factory_name="Factory"):
        super(Factory, self).__init__(name=factory_name)
        self.task_queue = task_queue
        self.thread_name = factory_name
        self.setDaemon(True)
        self.start()

    def run(self):
        Log(4, "Factory start-----------:{}-----------, status:{}".format(self.thread_name, self.task_queue.empty()))
        while True:
            try:
                # 任务异步出队，Queue内部实现了同步机制
                t1 = time.time()
                Log(4, "name:{}, run queue size:{}, id(self):{}, id(thread):{}".format(self.thread_name, self.task_queue.qsize(), id(self), id(self.thread_name)))
                if not self.task_queue.empty():
                    task = self.task_queue.get(timeout=10)
                    task.run()
                    while True:
                        if task.is_finished():  # task中有一个status属性，用于标志任务是否执行完成
                            # 通知系统任务完成
                            self.task_queue.task_done()
                            Log(4, "run#{}# cost:{}".format(self.thread_name, time.time() - t1))
                            break
                        time.sleep(3)
                time.sleep(15)  # 防止cpu占用过高
            except Queue.Empty:
                Log(3, "Factory.run empty...")
            except Exception as e:
                PrintStack()
                Log(3, "Factory run error:{}".format(str(e)))