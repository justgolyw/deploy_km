### SIEP自动化部署说明文档

提供了一个一键自动化部署/更新SIEP环境的自动化脚本，整个部署流程包含以下几个步骤：

1. KM环境回滚
2. 下载部署run包
3. 上传hosts.ini文件
4. KM环境部署
5. 初次登陆修改密码
6. 设置server-url

#### 项目路径

http://mq.code.sangfor.org/paas/kubespace/automatic-test/tree/deploy_km

将项目clone到本地后执行main.py程序即可运行


#### 自定义配置项

执行main.py部署环境之前需要先提供hosts.ini 文件，以及在env.yml 中配置环境信息，env.yml需要自定义配置的环境信息包括以下几项：
```
# km后台登录信息
ssh_host: 10.113.78.100
ssh_port: 22
ssh_uname: root
ssh_pwd: Sangfor@123

# minio 登录信息
minio_host: 10.113.64.3
minio_port: 31609
minio_uname: admin
minio_pwd: 5d7bqhpgxn5nfrklw455nnnlnh6b8z7wqzz9kqbpnfghlgwxwgfj6f

# acloud登录信息
acloud_host: 10.113.69.13
acloud_uname: admin
acloud_pwd: admin123
# 云主机ID
vm_id: 3109050786830
```

这几项需要根据自己的实际情况进行配置，配置错误将部署失败，其中vm_id是KM管理集群主机的虚拟机id，请自行到HCI上进行查看。

hosts.ini 文件配置信息如下：
```
[all]
[all:vars]
ansible_ssh_common_args='-o ServerAliveInterval=300 -o ServerAliveCountMax=5 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
[km]
192.168.0.40 ansible_ssh_user=root ansible_ssh_port=22 ansible_ssh_pass=Sangfor@123 ansible_become=yes ansible_become_user=root ansible_become_password=Sangfor@123
[km:vars]
km_server_vip=192.168.0.38
km_harbor_vip=192.168.0.39
km_harbor_endpoint=10.113.83.100
kube_keepalived_vip_vrid=188
km_deploy_dir=/sf/data/pgsql/km-deploy
km_ssh_port=22
[scale]
```

注意：在这个配置文件中添加了一行配置项：km_ssh_port=22，这样能保证km管理主机在部署前后的主机端口始终为22（不配置的话环境部署完成后主机端口会修改为22345），
我在程序中已经默认将云主机端口设置为了22，所以为了保证不出错，务必加上这一行配置。


备注：在使用过程中如果某些步骤不需要，可自行进行注释。


#### 定时更新环境

参考：https://blog.csdn.net/David_jiahuan/article/details/99960427


#### 新增功能
1. 支持不同平台（aCloud/scp/sCloud）上的云主机进行回滚操作
2. 支持单节点和多节点的KM回滚到指定的快照版本
3. 主机不存在wget命令时安装wget
4. 程序执行完成后自动关闭ssh连接
5. 将下载run包和部署run包的命令放到后台执行，输出日志保存到文件
6. 使用stdout.channel.recv()来循环获取部署过程中的输出，避免阻塞
7. 支持使用命令行来设置部署过程中是否需要回滚主机和下载run包
8. 支持使用命令行指定run包下载地址