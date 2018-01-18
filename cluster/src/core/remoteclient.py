# -*- coding: utf-8 -*-
from common.util import Result
import paramiko
from frame.logger import Log
import StringIO


class RemoteParam(object):
    """
    ssh远程连接客户端
    """

    def __init__(self, host_ip, port, username, passwd, prikey, prikeypwd):
        self.host_ip = host_ip
        self.username = username
        self.port = port
        self.passwd = passwd
        self.prikey = prikey
        self.prikeypwd = prikeypwd
        self.sshclient = None
        self.sftpclient = None
        self.not_read_a_file = ''
        self.trans = None

    def process_command(self, command):
        import multiprocessing
        p = multiprocessing.Pool()
        result = p.apply_async(self.exec_command, args=(command,))
        p.close()
        p.join()
        Log(3, "result.get():{}".format(result.get(2)))
        return result.get()

    def process_putfile(self, file_name, path):
        import multiprocessing
        p = multiprocessing.Pool()
        result = p.apply_async(self.put_file, args=(file_name, path))
        p.close()
        p.join()
        return result.get()

    def create_sshclient(self):
        # 构建客户端
        self.sshclient = paramiko.SSHClient()
        if self.prikey:
            not_read_a_file = StringIO.StringIO(self.prikey)
            private_key = paramiko.RSAKey.from_private_key(not_read_a_file, self.prikeypwd)
            not_read_a_file.close()
        else:
            private_key = None
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.sshclient.connect(self.host_ip, self.port, username=self.username, password=self.passwd,
                                   pkey=private_key, timeout=4)
        except Exception as e:
            Log(1, 'remoteparam connect error:{}'.format(e.message))
            return Result('', 400, 'connect host error:' + e.message)
        return Result('')

    def create_sftpclient(self):
        self.trans = paramiko.Transport((self.host_ip, self.port))
        if self.prikey:
            not_read_a_file = StringIO.StringIO(self.prikey)
            private_key = paramiko.RSAKey.from_private_key(not_read_a_file, self.prikeypwd)
            not_read_a_file.close()
        else:
            private_key = None
        try:
            self.trans.connect(username=self.username, password=self.passwd,
                      pkey=private_key)  # 连接方式也可以用key，这里只需要将password=password改为pkey=key，其余的key代码与前面的一样
            self.sftpclient = paramiko.SFTPClient.from_transport(self.trans)  # 使用t的设置方式连接远程主机
        except Exception as e:
            Log(3, 'remoteparam connect error:{}'.format(e.message))
            return Result('', 400, 'connect host error:' + e.message)
        return Result('')

    def exec_command(self, command, timeout=10):
        """
        执行命令
        :param command:
        :param timeout:
        :return:
        """
        try:
            # 执行命令
            _, stdout, stderr = self.sshclient.exec_command(command, timeout=timeout)
            r_data = {'stdout': [], 'stderr': []}
            for std in stdout.readlines():
                r_data['stdout'].append(std)
            for error in stderr.readlines():
                r_data['stderr'].append(error)

            if len(r_data['stderr']) > 0:
                return Result('', msg=r_data['stderr'], result=400)
            else:
                return Result(r_data['stdout'])
        except timeout:
            return Result('', msg='time out', result=400)
        except Exception as e:
            return Result('', msg=e.message, result=500)

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
        if self.sshclient:
            self.sshclient.close()
        if self.trans:
            self.trans.close()
        if self.sftpclient:
            self.sftpclient.close()

# if __name__ == '__main__':
#     remote = RemoteParam('192.168.8.25', 22, 'root', 'Cs123456', None, None)
#     rlt = remote.exec_command('mkdir ufleetnet; touch ufleetnet/a.yaml')
#     print rlt.content
#     print sys.path[0]
#     pwd_path = sys.path[0]
#     rlt1 = remote.put_file(sys.path[0] + '/config.py', 'ufleetnet/a.yaml')
#     print rlt1.content
#     print "sed -i '21c/^.*$/     'name': 'aa'/' root"