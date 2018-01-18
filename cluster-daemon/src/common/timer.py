# -*- coding: utf-8 -*-
# Copyright (c) 20016-2016 The Cloudsoar.
# See LICENSE for details.

import threading
import time


class Timer(threading.Thread):
    def __init__(self, interval, timeout_handler, thread_name="Timer"):
        super(Timer, self).__init__(name=thread_name)
        self.interval = interval
        self.handler = timeout_handler
        self.daemon = True

    def run(self):
        while True:
            self.handler.timeout()
            time.sleep(self.interval)
