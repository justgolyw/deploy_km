#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from pathlib import Path
import time
import urllib3
import requests
from util import get_envs_from_yml
from ssh_client import local_ssh_client
from minio_client import MinioClient
from minio_client import read_checksum, write_checksum
from acloud_client import acloud_client, snapshot_recovery, start_vm
import logging

urllib3.disable_warnings()

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
#
# # 创建一个FileHandler,并将日志写入指定的日志文件中
# file_handler = logging.FileHandler('deploy.log', mode='w')
# file_handler.setLevel(logging.INFO)
#
# # 定义Handler的日志输出格式
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)
#
# # 添加Handler
# logger.addHandler(file_handler)

envs = get_envs_from_yml()
HOST = envs.get("ssh_host", "")


def install_wget(ssh_client):
    """
    添加dns resolv.conf，安装wget
    """
    cmd1 = "ls /etc/resolv.conf"
    ret = ssh_client.exec_command(cmd1)
    if not ret[1]:
        cmd2 = "echo nameserver 10.113.64.155 > /etc/resolv.conf && dnf install -y wget"
        ret = ssh_client.exec_command(cmd2)
        assert ret[1] is True
    else:
        pass


def download_run_object(ssh_client, wget_url=""):
    """
    下载run包
    """
    minio = MinioClient()
    # object_name = minio.get_run_object().object_name
    # down_name = object_name.split("/")[1]
    # 获取下载链接
    if wget_url:
        link = wget_url
    else:
        link = minio.get_run_url()
    # 安装wget
    # install_wget(ssh_client)
    # 下载run包到/sf/data/pgsql目录下
    # command = f"cd /sf/data/pgsql && wget '{link}' -O km.run"
    command = f"cd /sf/data/pgsql && nohup wget '{link}' -O km.run > wget_run.log 2>&1 &"
    print("下载run包:", command)
    ssh_client.exec_command(command)
    print("下载完成")


def check_md5(ssh_client, expect_sum):
    """
    检查run包的md5值
    """
    # 登录管理主机
    print("检查run包的MD5值")
    res = ssh_client.exec_command(f"md5sum km.run | awk '{{print $1}}'")[0]
    assert res == expect_sum


def scp_file(ssh_client):
    # 拷贝hosts.ini文件到远程/sf/data/pgsql目录下
    file_path = Path(__file__).absolute().parent / "data" / "hosts.ini"
    ssh_client.put_local_files(file_path, "/sf/data/pgsql/")


def deploy_skm(ssh_client):
    """
    部署km
    """
    # 拷贝hosts.ini文件到远程/sf/data/pgsql目录下
    # file_path = Path(__file__).absolute().parent / "data" / "hosts.ini"
    # ssh_client.put_local_files(file_path, "/sf/data/pgsql/")
    start = time.time()
    scp_file(ssh_client)
    print("开始部署km")
    command = f"cd /sf/data/pgsql &&" \
               f"chmod +x km.run &&" \
               f"export TMPDIR=/sf/data/pgsql &&" \
               f"nohup ./km.run --km-hosts hosts.ini > deploy_km.log 2>&1 &"
    ssh_client.conn.exec_command(command)
    while True:
        result = ssh_client.exec_command("ps -ef")[0]
        ret = re.findall("nohup ./km.run --km-hosts hosts.ini", result)
        if ret:
            # print(ret)
            time.sleep(60)
        else:
            break
    end = time.time()
    print(f"部署完成:耗时{(end - start) / 3600}h")


# def clear_km(ssh_client):
#     """
#     清理KM集群
#     """
#     command = "curl -s http://mq.code.sangfor.org/10037/my-project/raw/master/km-cleanup.sh -o ./cleanup.sh  && chmod +x cleanup.sh && ./cleanup.sh"
#     print("清理KM集群")
#     ssh_client.exec_command(command)
#     print("清理完成")


# def edit_skm_system(ssh_client):
#     """
#     编辑skm,开启local集群
#     """
#     print("编辑skm yaml文件,开启local集群")
#     command = "kubectl get deploy skm -n skm-system -o yaml > skm.yaml && " \
#               "sed -i 's/--add-local=False/--add-local=true/g' skm.yaml &&" \
#               "kubectl apply -f skm.yaml"
#     ssh_client.exec_command(command)


def change_password(ssh_client):
    """
    初次登陆修改密码
    """
    print("初次登陆修改密码")
    # admin用户的初始密码为admin
    login_url = f"https://{HOST}/v3-public/localproviders/local?action=login"
    json_data = {"username": "admin", "password": "admin", "responseType": "cookie"}
    response = requests.post(login_url, json=json_data, verify=False)
    cookie = response.headers["Set-Cookie"].split(";")[0]
    headers = {"Cookie": cookie}
    # 后台查看user_id
    command = "kubectl get users | grep user | awk '{{print $1}}'"
    result = ssh_client.exec_command(command)[0]
    user_id = result.strip()
    setpwd_url = f"https://{HOST}/v3/users/{user_id}?action=setpassword"
    json_data = {"newPassword": "Admin@123"}
    resp = requests.post(setpwd_url, json=json_data, headers=headers, verify=False)
    assert resp.status_code == 200


def set_server_url():
    """
    设置server url
    """
    print("设置server url")
    login_url = f"https://{HOST}/v3-public/localproviders/local?action=login"
    json_data = {"username": "admin", "password": "Admin@123", "responseType": "cookie"}
    response = requests.post(login_url, json=json_data, verify=False)
    cookie = response.headers["Set-Cookie"].split(";")[0]
    headers = {"Cookie": cookie}
    set_server_url = f"https://{HOST}/v3/settings/server-url"
    json_data = {
        "id": "server-url",
        "value": f"https://{HOST}"
    }
    resp = requests.put(set_server_url, json=json_data, headers=headers, verify=False)
    assert resp.status_code == 200


def deploy_kubemanager(no_rollback=False, no_download=False, wget_url=""):
    """
    部署km环境，获取到新的run包后重新部署
    """
    # 1.从文件中读取run包的checksum
    file_path = Path(__file__).absolute().parent / "data" / "checksum.txt"
    old_checksum = read_checksum(file_path)
    # 2.获取run包的checksum
    minio = MinioClient()
    new_checksum = minio.get_run_checksum()
    if new_checksum != old_checksum:
        if not no_rollback:
            # km环境回滚
            acloud = acloud_client()
            snapshot_recovery(acloud)
            time.sleep(120)

            # 启动虚拟机
            start_vm(acloud)
            time.sleep(180)

        with local_ssh_client() as ssh_client:
            if not no_download:
                # 下载run包
                download_run_object(ssh_client, wget_url)
                # 检查run包的md5值
                # check_md5(ssh_client, new_checksum)

            # 部署km
            deploy_skm(ssh_client)
            time.sleep(30)

            # 初次登录修改密码和设置server-url
            change_password(ssh_client)
            time.sleep(10)
            set_server_url()

        # 将new_checksum的值写入文件保存
        write_checksum(file_path, new_checksum)
    else:
        print("run包没有更新，km环境不需要更新")