#!/usr/bin/env python3
"""
统一配置读取模块
从 conf/config.yml 加载所有配置
"""

import os
import yaml


def _find_config_path():
    """
    查找配置文件路径
    优先级: 环境变量 CONFIG_PATH > ./conf/config.yml > ../conf/config.yml > /app/conf/config.yml
    """
    env_path = os.getenv('CONFIG_PATH')
    if env_path and os.path.exists(env_path):
        return env_path

    local_path = os.path.join(os.getcwd(), 'conf', 'config.yml')
    if os.path.exists(local_path):
        return local_path

    parent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'conf', 'config.yml')
    parent_path = os.path.normpath(parent_path)
    if os.path.exists(parent_path):
        return parent_path

    docker_path = '/app/conf/config.yml'
    if os.path.exists(docker_path):
        return docker_path

    raise FileNotFoundError("找不到配置文件 config.yml")


_config = None


def get_config():
    """获取全局配置（单例）"""
    global _config
    if _config is None:
        with open(_find_config_path(), 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
    return _config


def get_db_config():
    """获取数据库配置"""
    return get_config().get('database', {})


def get_garmin_config():
    """获取佳明配置"""
    return get_config().get('garmin', {})
