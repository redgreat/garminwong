#!/usr/bin/env python3
"""
佳明登录工具类
"""

import garth
from config import get_garmin_config


class GarminLogin:

    def __init__(self):
        cfg = get_garmin_config()
        self.email = cfg.get('email')
        self.password = cfg.get('password')
        self.domain = cfg.get('domain', 'garmin.cn')
        self.save_path = cfg.get('save_path', '~/.garth')

        if not self.email or not self.password:
            raise ValueError("请在 conf/config.yml 中设置 garmin.email 和 garmin.password")

    def login(self):
        try:
            garth.configure(domain=self.domain)
            print(f"正在登录佳明账号: {self.email}")
            garth.login(self.email, self.password)
            garth.save(self.save_path)
            print("✅ 登录成功！")
            return True
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return False

    def is_logged_in(self):
        try:
            garth.resume(self.save_path)
            garth.client.username
            return True
        except Exception:
            return False

    def ensure_login(self):
        if not self.is_logged_in():
            print("🔐 未登录，开始登录...")
            if not self.login():
                raise Exception("佳明登录失败")
        else:
            garth.resume(self.save_path)
            print(f"✅ 佳明会话恢复: {garth.client.username}")
