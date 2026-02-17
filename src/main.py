#!/usr/bin/env python3
"""
运动健康数据收集器主程序
支持多平台数据源：Garmin / Polar / Coros
"""

import sys
import schedule
import time
import logging
from datetime import datetime, date
from config import get_config
from garmin_data_collector import GarminDataCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 最早回溯日期
EARLIEST_DATE = date(2016, 6, 1)


def run_garmin(days_back=1):
    """执行佳明数据收集"""
    print(f"\n📡 [GARMIN] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 数据收集开始 (回溯{days_back}天)...")
    collector = None
    try:
        collector = GarminDataCollector()
        collector.ensure_login()
        collector.collect_all_data(days_back=days_back)
        print(f"✅ [GARMIN] 数据收集完成")
    except Exception as e:
        print(f"❌ [GARMIN] 数据收集失败: {e}")
        logger.error(f"[GARMIN] {e}", exc_info=True)
    finally:
        if collector:
            collector.cleanup()


def calc_init_days(garmin_cfg):
    """计算首次运行回溯天数"""
    init_days = garmin_cfg.get('init_days')
    if init_days:
        return int(init_days)
    # 未设置则回溯到 EARLIEST_DATE
    delta = date.today() - EARLIEST_DATE
    return delta.days


def main():
    try:
        config = get_config()
        garmin_cfg = config.get('garmin', {})
        print("🚀 运动健康数据收集器启动")
        print("=" * 50)

        # 首次运行：按 init_days 配置回溯
        init_days = calc_init_days(garmin_cfg)
        print(f"📊 首次运行，回溯 {init_days} 天数据...")
        run_garmin(days_back=init_days)

        # 每日定时：只获取昨天1天
        garmin_schedule = garmin_cfg.get('schedule', '08:00')
        schedule.every().day.at(garmin_schedule).do(run_garmin, days_back=1)
        print(f"\n⏰ 定时任务:")
        print(f"   - Garmin 每日 {garmin_schedule} (获取前1天数据)")

        # TODO: 后续扩展
        # polar_schedule = config.get('polar', {}).get('schedule', '08:30')
        # coros_schedule = config.get('coros', {}).get('schedule', '09:00')

        print("\n🔄 定时任务运行中...")

        while True:
            schedule.run_pending()
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n👋 程序停止")
        return 0
    except Exception as e:
        print(f"❌ 程序错误: {e}")
        logger.error(f"{e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())