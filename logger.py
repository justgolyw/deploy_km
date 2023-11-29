#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建一个FileHandler,并将日志写入指定的日志文件中
file_handler = logging.FileHandler('deploy.log', mode='w')
file_handler.setLevel(logging.INFO)

# 定义Handler的日志输出格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s\n')
file_handler.setFormatter(formatter)

# 添加Handler
logger.addHandler(file_handler)