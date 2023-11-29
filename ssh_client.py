import time

import paramiko
from scp import SCPClient
from util import get_envs_from_yml
from logger import logger


class SSH:
    """
    Paramiko 远程连接操作
    """

    def __init__(self, host, port, username, password, timeout=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.conn = self.ssh_conn()

    def ssh_conn(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                self.host, self.port, self.username, self.password,
                timeout=self.timeout, banner_timeout=self.timeout
            )
        except Exception as e:
            raise e
        return ssh

    def exec_command(self, cmd, timeout=None):
        stdin, stdout, stderr = self.conn.exec_command(cmd, timeout=timeout)
        result = stdout.read().decode('utf-8').strip()
        error_info = stderr.read().decode('utf-8').strip()
        if not result and error_info:
            return [error_info, False]
        return [result, True]

    def exec_command2(self, cmd, timeout=None):
        stdin, stdout, stderr = self.conn.exec_command(cmd, timeout=timeout)
        while not stdout.channel.exit_status_ready():
            output = stdout.channel.recv(1024)
            print(output.decode('utf-8'), end='', flush=True)
            # logger.info(output.decode('utf-8'))

    def send_curl(self, url, is_file=False):
        cmd = "curl " + url
        if is_file:
            cmd = "cd /root/download && curl -O {} --retry 3 --retry-delay 1" \
                  "; rm -rf /root/download/*".format(url)
        return self.exec_command(cmd)

    def close_(self):
        self.conn.close()

    def get_real_time_data(self, cmd):
        try:
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            for line in stdout:
                strip_line = line.strip("\n")
                logger.info(strip_line)
                yield strip_line
        except Exception as e:
            raise AttributeError(
                "execute command %s error, error message is %s" % (cmd, e)
            )

    def get_remote_files(self, remote_files, local_path, **kwargs):
        """将远端服务器上的文件拷贝到本地"""
        with SCPClient(self.conn.get_transport()) as cp:
            if isinstance(remote_files, list):
                for remote_file in remote_files:
                    cp.get(remote_file, local_path, **kwargs)
            elif isinstance(remote_files, str):
                cp.get(remote_files, local_path, **kwargs)
            else:
                raise TypeError(f"'remote_files'类型错误.")
            logger.info(f"拷贝文件到 {local_path} 完成!")

    def put_local_files(self, local_files, remote_path, **kwargs):
        """将本地文件拷贝到远端服务器上"""
        with SCPClient(self.conn.get_transport()) as cp:
            cp.put(local_files, remote_path, **kwargs)
            logger.info(f"拷贝文件({local_files}) 至 {remote_path} 完成!")

    def __enter__(self):
        print("开启远程连接")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("关闭远程连接")
        self.close_()


def local_ssh_client():
    """
    建立ssh连接,进入管理集群后台
    :return: ssh client
    """
    envs = get_envs_from_yml()
    host = envs.get("ssh_host", "")
    port = envs.get("ssh_port", 22)
    username = envs.get("ssh_uname", "root")
    password = envs.get("ssh_pwd", "Sangfor@123")
    ssh_client = SSH(host=host, port=port, username=username, password=password)
    return ssh_client


if __name__ == '__main__':
    ssh_client = SSH(host="10.113.78.126", port=22, username="root", password="Sangfor-paas.237")
    ssh_client.exec_command2("cat test.env")

