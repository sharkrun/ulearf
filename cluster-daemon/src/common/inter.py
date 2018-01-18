# -*- coding: utf-8 -*-

import threading
from frame.logger import Log, PrintStack
import time
import Queue
import datetime


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
        # Log(4, "Factory start-----------:{}-----------, status:{}".format(self.thread_name, self.task_queue.empty()))
        while True:
            try:
                # 任务异步出队，Queue内部实现了同步机制
                # Log(4, "name:{}, run queue size:{}, id(self):{}, id(thread):{}".format(self.thread_name,
                # self.task_queue.qsize(), id(self), id(self.thread_name)))
                if not self.task_queue.empty():
                    task = self.task_queue.get(timeout=2)
                    task.run()
                    while True:
                        if task.is_finished():  # task中有一个status属性，用于标志任务是否执行完成
                            # 通知系统任务完成
                            self.task_queue.task_done()
                            break
                        time.sleep(2)
                time.sleep(10)  # 防止cpu占用过高
                Log(4, "factory run one finished. name:{}, at:{}".format(self.thread_name, datetime.datetime.now()))
            except Queue.Empty:
                Log(3, "Factory.run empty...")
            except Exception as e:
                PrintStack()
                Log(3, "Factory run error:{}".format(e.message))
