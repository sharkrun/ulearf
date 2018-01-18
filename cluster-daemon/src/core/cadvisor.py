#! /usr/bin/env python
# -*- coding:utf-8 -*-
import requests
from frame.logger import Log, PrintStack
from common.util import Result


class Cadvisor(object):
    def __init__(self, host_ip, uri='/api/v1.2/docker', timeout=5):
        self.host_ip = host_ip
        self.uri = uri
        self.timeout = timeout

    def get(self, container_id=None):
        try:
            if container_id:
                container_id = container_id.split('//')[1] if '//' in container_id else container_id
                url = 'http://{}:4194'.format(self.host_ip) + self.uri + '/' + container_id
            else:
                url = 'http://{}:4194'.format(self.host_ip) + self.uri
            r = requests.get(url, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            Log(2, "can not get request from cadvisor:{}".format(e.message))
            return Result('', 500, e.message, 400)
        except Exception as e:
            Log(1, "cadvisor Exception:{}".format(e.message))
            return Result('', 500, e.message, 500)
        else:
            if r.status_code == 200:
                try:
                    return Result(r.json())
                except Exception as e:
                    Log(3, "from cadvisor data.json() error:{}".format(e.message))
                    PrintStack()
                    return Result('', 500, e.message, 500)
            else:
                return Result('', r.status_code, r.text, r.status_code)

if __name__ == '__main__':
    # c = Cadvisor('192.168.3.122', '/api/v1.3/machine')
    # rlt = c.get()
    # if rlt.success:
    #     print rlt.content
    cadvisor_cli = Cadvisor('192.168.3.122', '/api/v1.3/machine')
    rlt = cadvisor_cli.get()
    if rlt.success:
        filesystems = rlt.content.get('filesystems', [])
        disk_num = 0
        for f in filesystems:
            disk_num += f.get('capacity', 0)
        print(str(round(disk_num / (1024 ** 3), 3)) + 'GB')
    else:
        Log(1, "node get_disk_info error:{}".format(rlt.message))
        print('')
