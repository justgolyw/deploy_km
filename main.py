#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from deploy_km import deploy_kubemanager

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="命令行传参")
    # 使用store时，将参数值存储到args的命名空间中。如果在命令行中指定了参数，则存储指定的参数值(True)；否则，将使用默认值(False)
    parser.add_argument('--no_rollback', action='store_true', default=False, help='是否回滚主机')
    parser.add_argument('--no_download', action='store_true', default=False, help='是否下载run包')
    parser.add_argument('--wget_url', type=str, default="", help='指定run包下载地址')
    args = parser.parse_args()
    deploy_kubemanager(no_rollback=args.no_rollback, no_download=args.no_download, wget_url=args.wget_url)
