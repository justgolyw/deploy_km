#!/usr/bin/env python
# -*- coding: utf-8 -*-
import yaml
from pathlib import Path

env_path = Path(__file__).resolve().parent / "env.yml"


def read_yaml(yaml_path):
    """
    读取yaml文件
    """
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f.read())
    return data


def get_envs_from_yml():
    """
    从yml文件中读取配置信息
    """
    envs = {}
    if env_path.exists():
        envs = read_yaml(env_path)
    return envs
