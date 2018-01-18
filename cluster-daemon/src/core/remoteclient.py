# -*- coding: utf-8 -*-
from common.util import Result
import paramiko
from etcddb.mastermgr import Masterdb
import sys
from frame.logger import Log


class RemoteParam(object):
    """
    ssh远程连接客户端
    """

    def __init__(self, host_ip):
        self.host_ip = host_ip
        self.sshclient = None
        self.sftpclient = None

    def connect(self):
        host_ip = self.host_ip
        rlt = Masterdb.instance().read_master(host_ip.replace('.', '-'))
        if not rlt.success:
            return rlt
        username = rlt.content.get('username', None)
        passwd = rlt.content.get('userpwd', None)
        pkey = rlt.content.get('pkey', None)
        port = int(rlt.content.get('port', 22))
        sshclient = paramiko.SSHClient()
        sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            sshclient.connect(host_ip, port, username=username, password=passwd, pkey=pkey, timeout=4)
        except Exception as e:
            Log(3, 'remoteparam connect error:{}'.format(e.message))
            return Result('', 400, 'connect host error:'+e.message)
        self.sshclient = sshclient

        t = paramiko.Transport((host_ip, port))
        try:
            t.connect(username=username, password=passwd,
                      pkey=pkey)  # 连接方式也可以用key，这里只需要将password=password改为pkey=key，其余的key代码与前面的一样
            sftp = paramiko.SFTPClient.from_transport(t)  # 使用t的设置方式连接远程主机
        except Exception as e:
            Log(3, 'remoteparam connect error:{}'.format(e.message))
            return Result('', 400, 'connect host error:'+e.message)
        self.sftpclient = sftp
        return Result('')
        # sftp.get('/tmp/hello.txt', 'hello.txt')  # 下载文件
        # sftp.put('ssh1.py', '/tmp/ssh1.py')

    def exec_command(self, command, timeout=5):
        """
        执行命令
        :param command:
        :param timeout:
        :return:
        """
        stdin, stdout, stderr = self.sshclient.exec_command(command, timeout=timeout)
        r_data = {'stdout': [], 'stderr': []}
        for std in stdout.readlines():
            r_data['stdout'].append(std)
        for error in stderr.readlines():
            r_data['stderr'].append(error)
        if len(r_data['stderr']) > 0:
            return Result('', msg=r_data['stderr'], result=400)
        else:
            return Result(r_data['stdout'])

    def put_file(self, file_name, path):
        """
        上传文件
        :param file_name_list:
        :return:
        """
        try:
            rlt = self.sftpclient.put(file_name, path)
            return Result(rlt)
        except Exception as e:
            return Result('', 400, e.message)

    def close(self):
        """
        关闭客户端
        :return:
        """
        self.sshclient.close()
        self.sftpclient.close()

if __name__ == '__main__':
    remote = RemoteParam('192.168.8.25')
    rlt = remote.connect()
    if rlt.success:
        rlt = remote.exec_command('mkdir ufleetnet; touch ufleetnet/calico.yaml')
        print rlt.content
        print sys.path[0]
        pwd_path = sys.path[0]
        rlt1 = remote.put_file(sys.path[0] + '/config.py', 'ufleetnet/calico.yaml')
        print rlt1.content
        print "sed -i '21c/^.*$/     'name': 'aa'/' root"