#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import rsa
import struct
import requests
import urllib3
from util import get_envs_from_yml

urllib3.disable_warnings()

envs = get_envs_from_yml()
host = envs.get("acloud_host", "")

REG_RSA_MODULUS = re.compile('''RSAModulus\s*:\s*['"]([0-9a-f]{512})['"]''', re.I)
BASE_URL = f"https://{host}"
SERVER_URL = BASE_URL + "/vapi"
# HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
# HEADERS = {'Content-Type': 'application/json'}
HEADERS = {}

USERNAME = envs.get("acloud_uname", "admin")
PASSWORD = envs.get("acloud_pwd", "admin123")
VM_ID = envs.get("vm_id", "")


class Client(object):
    def __init__(self, url=None, headers=None, verify=True, **kw):
        if verify == 'False':
            verify = False
        self._headers = HEADERS.copy()
        if headers is not None:
            for k, v in headers.items():
                self._headers[k] = v
        self._url = url
        self._session = requests.Session()
        self._session.verify = verify

    def _get(self, url, data=None):
        resp = self._session.get(url, params=data, headers=self._headers)
        protect_response(resp)
        return resp

    def _post(self, url, data=None, json=None):
        resp = self._session.post(url, data=data, json=json, headers=self._headers)
        protect_response(resp)
        return resp

    def _put(self, url, data=None, json=None):
        resp = self._session.put(url, data=data, json=json, headers=self._headers)
        protect_response(resp)
        return resp

    def _delete(self, url):
        resp = self._session.delete(url, headers=self._headers)
        protect_response(resp)
        return resp


def protect_response(r):
    if r.status_code < 200 or r.status_code >= 300:
        message = f'Server responded with {r.status_code}\nbody:\n{r.text}'
        raise ValueError(message)


def encrypt_password(plan_password):
    """
    获取加密后的密码
    """
    pub_rsa_key = get_rsa_pub_key()
    encrypt_password = rsa.encrypt(bytes(plan_password, encoding='utf-8'), pub_rsa_key)
    unpack_format = str(len(encrypt_password)) + 'B'
    if not pub_rsa_key:
        return plan_password

    slices = struct.unpack(unpack_format, encrypt_password)
    return ''.join(['%02x' % s for s in slices])


def get_rsa_pub_key():
    """
    获取公钥模数字符串
    """
    login_html = requests.get(BASE_URL + '/login', timeout=30, verify=False)
    login_html = login_html.text
    rsa_modulus_mt = REG_RSA_MODULUS.search(login_html)

    if not rsa_modulus_mt:
        return None

    pub_key_n = int(rsa_modulus_mt.group(1), base=16)
    return rsa.PublicKey(n=pub_key_n, e=65537)


def acloud_login():
    """
    acloud用户登录
    """
    login_url = SERVER_URL + '/extjs/access/ticket'
    data = {
        'username': USERNAME,
        'password': encrypt_password(PASSWORD),
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(login_url, data=data, headers=headers, verify=False)
    assert response.status_code == 200


def acloud_client():
    """
    acloud用户登录, 返回登录后的client
    """
    login_url = SERVER_URL + '/extjs/access/ticket'
    data = {
        'username': USERNAME,
        'password': encrypt_password(PASSWORD),
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(login_url, data=data, headers=headers, verify=False)
    protect_response(response)
    cookie = response.headers["Set-Cookie"].split(";")[0]
    secure_token = response.json()["data"]["CSRFPreventionToken"]
    client = Client(url=SERVER_URL,
                    verify=False,
                    headers={"Cookie": cookie, "CSRFPreventionToken": secure_token})
    return client


def get_platform_name(client):
    """
    查看平台名称
    """
    url = client._url + f"/extjs/vapimain/webui/get_enterprise_custom_config?section=base"
    response = client._get(url)
    assert response.status_code == 200
    return response.json()["data"]["base"]["platform_en_name"]


def get_snapshot_id(client, vm_id, platform_name=""):
    """
    获取快照id
    """
    index = envs.get("snap_index", 0)
    if platform_name == "SANGFOR aCloud":
        url = client._url + f"/extjs/cluster/vm/{vm_id}/snapshot"
        response = client._get(url)
        assert response.status_code == 200
        return response.json()["data"][index]["snapid"]
    else:
        url = client._url + f"/json/vapimain/vm/{vm_id}/snapshots"
        response = client._get(url)
        assert response.status_code == 200
        return response.json()["data"]["snapshot"]["snaps"][index]["snap_id"]


def _snapshot_recovery(client, vm_id, snap_id, platform_name):
    """
    恢复快照
    """
    if platform_name == "SANGFOR aCloud":
        url = client._url + f"/extjs/cluster/vm/{vm_id}/recovery"
        data = {
            "rtype": "raw",
            'snapid': snap_id,
            "backup": 0
        }
        response = client._post(url, data=data)
        assert response.json()["success"] == 1
        return response.json()
    else:
        url = client._url + f"/json/vapimain/vm/{vm_id}/snapshots/{snap_id}/recover"
        json = {
          "snapshot": {
            "need_create_snap": 0,
            "auto_startvm": 0
          }
        }
        response = client._post(url, json=json)
        assert response.json()["success"] == 1
        # return response.json()


def snapshot_recovery(client):
    print("恢复快照")
    platform_name = get_platform_name(client)
    vm_ids = VM_ID
    if not isinstance(vm_ids, list):
        vm_ids = [vm_ids]
    for vm_id in vm_ids:
        snap_id = get_snapshot_id(client, vm_id=vm_id, platform_name=platform_name)
        _snapshot_recovery(client, vm_id, snap_id, platform_name)


def start_vm(client):
    """
    启动虚拟机
    """
    print("启动虚拟机")
    vm_ids = VM_ID
    if not isinstance(vm_ids, list):
        vm_ids = [vm_ids]
    for vm_id in vm_ids:
        url = client._url + f"/extjs/cluster/vm/{vm_id}/status/start"
        response = client._post(url)
        assert response.json()["success"] == 1
        # return response.json()


def shutdown_vm(client):
    """
    关闭虚拟机
    """
    print("关闭虚拟机")
    vm_ids = VM_ID
    if not isinstance(vm_ids, list):
        vm_ids = [vm_ids]
    for vm_id in vm_ids:
        url = client._url + f"/extjs/cluster/vm/{vm_id}/status/shutdown"
        print("url=", url)
        response = client._post(url)
        assert response.json()["success"] == 1
        # return response.json()


# def modify_dnat(client, dst_port, trans_port):
#     """
#     修改目的地址转换的端口
#     """
#     url = client._url + f"/extjs/network/route/vr6decfa37/modify_dnat"
#     data = {
#         "enable": 1,
#         'desc': "km-3",
#         "srcif": "vric443b508",
#         "protocol": 6,
#         "dst_port": dst_port,
#         "trans_port": trans_port,
#         "ignore_acl": 1,
#         "trans_ips_str": "192.168.0.180",
#         "natid": "nat_bb78b868"
#     }
#     response = client._put(url, data=data)
#     print("修改目的地址转换的端口为：", dst_port, trans_port)
#     assert response.json()["success"] == 1
#     return response.json()


if __name__ == '__main__':
    client = acloud_client()
    snapshot_recovery(client)
    # shutdown_vm(client)