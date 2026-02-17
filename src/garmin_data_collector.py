#!/usr/bin/env python3
"""
佳明数据收集器
基于 garth API 获取各类健康数据并存入数据库
"""

import json
import garth
import logging
from datetime import datetime, timedelta, timezone
from garth_utils import GarminLogin
from database import GarminDatabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class GarminDataCollector:
    """佳明数据收集器"""

    ACTIVITIES_URL = "/activitylist-service/activities/search/activities"

    def __init__(self):
        self.garmin_login = GarminLogin()
        self._display_name = None
        self.db = GarminDatabase()

    def ensure_login(self):
        """确保佳明登录状态"""
        self.garmin_login.ensure_login()
        try:
            settings = garth.connectapi("/userprofile-service/userprofile/user-settings")
            self._display_name = settings.get("userData", {}).get("displayName")
        except Exception:
            pass
        if not self._display_name:
            self._display_name = garth.client.username

    # ==================== 活动数据 ====================

    def get_activities(self, start=0, limit=20):
        return garth.connectapi(self.ACTIVITIES_URL, params={"start": str(start), "limit": str(limit)})

    def get_activity_detail(self, activity_id):
        try:
            return garth.connectapi(f"/activity-service/activity/{activity_id}")
        except Exception as e:
            logger.warning(f"获取活动详情失败 {activity_id}: {e}")
            return None

    def get_activity_track(self, activity_id):
        """获取活动GPS轨迹点 (details API)"""
        try:
            return garth.connectapi(f"/activity-service/activity/{activity_id}/details")
        except Exception as e:
            logger.warning(f"获取活动轨迹失败 {activity_id}: {e}")
            return None

    def _parse_activity_summary(self, act_list_item, detail=None):
        """从活动列表项 + 详情API 解析汇总数据"""
        summary = {}
        if detail:
            summary = detail.get("summaryDTO", {})

        aid = str(act_list_item.get("activityId", ""))
        start_time_str = act_list_item.get("startTimeLocal")
        end_time_str = act_list_item.get("endTimeGMT")

        return {
            "activityid": aid,
            "activityname": act_list_item.get("activityName"),
            "activitytype": act_list_item.get("activityType", {}).get("typeKey"),
            "sporttype": act_list_item.get("activityType", {}).get("typeKey"),
            "starttime": start_time_str,
            "endtime": end_time_str,
            "duration": summary.get("duration") or act_list_item.get("duration"),
            "distance": summary.get("distance") or act_list_item.get("distance"),
            "calories": summary.get("calories") or act_list_item.get("calories"),
            "avghr": summary.get("averageHR") or act_list_item.get("averageHR"),
            "maxhr": summary.get("maxHR") or act_list_item.get("maxHR"),
            "avgspeed": summary.get("averageSpeed") or act_list_item.get("averageSpeed"),
            "maxspeed": summary.get("maxSpeed") or act_list_item.get("maxSpeed"),
            "avgcadence": summary.get("averageRunCadence") or act_list_item.get("averageRunningCadenceInStepsPerMinute"),
            "maxcadence": summary.get("maxRunCadence") or act_list_item.get("maxRunningCadenceInStepsPerMinute"),
            "elevationgain": summary.get("elevationGain"),
            "elevationloss": summary.get("elevationLoss"),
            "startlat": summary.get("startLatitude"),
            "startlng": summary.get("startLongitude"),
            "endlat": summary.get("endLatitude"),
            "endlng": summary.get("endLongitude"),
            "trainingeffect": act_list_item.get("aerobicTrainingEffect"),
            "anaerobiceffect": act_list_item.get("anaerobicTrainingEffect"),
            "avgpower": act_list_item.get("avgPower"),
            "maxpower": act_list_item.get("maxPower"),
            "vo2max": act_list_item.get("vO2MaxValue"),
            "rawjson": json.dumps(act_list_item, ensure_ascii=False, default=str),
        }

    def _parse_track_points(self, track_data, activity_start_gmt):
        """解析轨迹点数据"""
        if not track_data or not isinstance(track_data, dict):
            return []

        # 构建指标名->索引映射
        descriptors = track_data.get("metricDescriptors", [])
        idx_map = {}
        for desc in descriptors:
            idx_map[desc.get("key")] = desc.get("metricsIndex")

        points = []
        metrics_list = track_data.get("activityDetailMetrics", [])
        for m in metrics_list:
            metrics = m.get("metrics", [])
            if not metrics:
                continue

            def _get(key):
                i = idx_map.get(key)
                if i is not None and i < len(metrics):
                    return metrics[i]
                return None

            # 用 directTimestamp (毫秒) 或相对秒数推算时间
            ts = _get("directTimestamp")
            if ts:
                pt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            else:
                elapsed = _get("sumElapsedDuration")
                if elapsed is not None and activity_start_gmt:
                    try:
                        base = datetime.strptime(activity_start_gmt, "%Y-%m-%dT%H:%M:%S.%f")
                        base = base.replace(tzinfo=timezone.utc)
                    except ValueError:
                        base = datetime.strptime(activity_start_gmt, "%Y-%m-%dT%H:%M:%S")
                        base = base.replace(tzinfo=timezone.utc)
                    pt = base + timedelta(seconds=elapsed)
                else:
                    continue

            points.append({
                "pointtime": pt,
                "latitude": _get("directLatitude"),
                "longitude": _get("directLongitude"),
                "elevation": _get("directElevation"),
                "heartrate": int(_get("directHeartRate")) if _get("directHeartRate") else None,
                "speed": _get("directSpeed"),
                "cadence": int(_get("directRunCadence")) if _get("directRunCadence") else None,
                "power": int(_get("directPower")) if _get("directPower") else None,
                "temperature": _get("directAirTemperature"),
                "distance": _get("sumDistance"),
            })
        return points

    def collect_activities(self, days_back=7):
        """收集活动数据并存入数据库"""
        print(f"🏃 获取最近{days_back}天的活动数据...")
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_ts = int(cutoff_date.timestamp() * 1000)
        all_activities = []
        start = 0

        while True:
            activities = self.get_activities(start=start, limit=20)
            if not activities:
                break
            for act in activities:
                if act.get("beginTimestamp", 0) < cutoff_ts:
                    break
                all_activities.append(act)
            else:
                start += 20
                continue
            break

        print(f"  📋 获取到 {len(all_activities)} 条活动")
        saved = 0
        skipped = 0
        for act in all_activities:
            aid = str(act.get("activityId", ""))
            # 检查活动是否已存在
            if self.db.activity_exists(aid):
                print(f"  ⏭️ {act.get('activityName')} (已存在)")
                skipped += 1
                continue
            try:
                # 获取活动详情
                detail = self.get_activity_detail(aid)
                parsed = self._parse_activity_summary(act, detail)
                self.db.upsert_activity(parsed)

                # 获取GPS轨迹
                if act.get("hasPolyline", False):
                    track = self.get_activity_track(aid)
                    start_gmt = None
                    if detail:
                        start_gmt = detail.get("summaryDTO", {}).get("startTimeGMT")
                    points = self._parse_track_points(track, start_gmt)
                    if points:
                        self.db.batch_upsert_activity_details(aid, points)
                        print(f"  ✅ {act.get('activityName')} - {len(points)} 个轨迹点")
                    else:
                        print(f"  ✅ {act.get('activityName')} (无轨迹)")
                else:
                    print(f"  ✅ {act.get('activityName')} (无GPS)")

                saved += 1
            except Exception as e:
                logger.error(f"活动 {aid} 处理失败: {e}")

        print(f"  📊 活动数据: 新增{saved}, 跳过{skipped}, 共{len(all_activities)}")

    # ==================== 心率数据 ====================

    def collect_heart_rate_data(self, target_date):
        try:
            return garth.connectapi(
                "/wellness-service/wellness/dailyHeartRate",
                params={"date": target_date}
            )
        except Exception as e:
            logger.warning(f"心率数据获取失败 {target_date}: {e}")
            return None

    def _save_heart_rate(self, target_date, data):
        if not data:
            return False
        try:
            # 汇总
            self.db.upsert_heartrate({
                "hrdate": target_date,
                "restinghr": data.get("restingHeartRate"),
                "maxhr": data.get("maxHeartRate"),
                "minhr": data.get("minHeartRate"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            # 时序明细
            hr_values = data.get("heartRateValues")
            if hr_values:
                self.db.batch_upsert_heartrate_details(target_date, hr_values)
            self.db.upsert_sync("garmin", "heartrate", target_date)
            return True
        except Exception as e:
            logger.error(f"心率存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "heartrate", target_date, status=0, errmsg=str(e))
            return False

    # ==================== 睡眠数据 ====================

    def collect_sleep_data(self, target_date):
        try:
            return garth.connectapi(
                f"/wellness-service/wellness/dailySleepData/{self._display_name}",
                params={"date": target_date, "nonSleepBufferMinutes": 60}
            )
        except Exception as e:
            logger.warning(f"睡眠数据获取失败 {target_date}: {e}")
            return None

    def _save_sleep(self, target_date, data):
        if not data:
            return False
        dto = data.get("dailySleepDTO", {})
        if not dto or dto.get("sleepTimeSeconds") is None:
            return False
        try:
            scores = dto.get("sleepScores", {})
            overall = scores.get("overall", {})
            self.db.upsert_sleep({
                "sleepdate": target_date,
                "sleepstart": GarminDatabase._ts_to_dt(dto.get("sleepStartTimestampGMT")),
                "sleepend": GarminDatabase._ts_to_dt(dto.get("sleepEndTimestampGMT")),
                "totalsleep": (dto.get("sleepTimeSeconds") or 0) // 60,
                "deepsleep": (dto.get("deepSleepSeconds") or 0) // 60,
                "lightsleep": (dto.get("lightSleepSeconds") or 0) // 60,
                "remsleep": (dto.get("remSleepSeconds") or 0) // 60,
                "awaketime": (dto.get("awakeSleepSeconds") or 0) // 60,
                "sleepscore": overall.get("value"),
                "sleepquality": overall.get("qualifierKey"),
                "restlesscount": dto.get("awakeCount"),
                "avgspo2": dto.get("averageSpO2Value"),
                "lowspo2": dto.get("lowestSpO2Value"),
                "highspo2": dto.get("highestSpO2Value"),
                "avgrespiration": dto.get("averageRespirationValue"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            # 睡眠阶段明细
            sleep_levels = data.get("sleepLevels")
            if sleep_levels:
                self.db.batch_upsert_sleep_details(target_date, sleep_levels)
            self.db.upsert_sync("garmin", "sleep", target_date)
            return True
        except Exception as e:
            logger.error(f"睡眠存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "sleep", target_date, status=0, errmsg=str(e))
            return False

    # ==================== 压力数据 ====================

    def collect_stress_data(self, target_date):
        try:
            return garth.connectapi(f"/wellness-service/wellness/dailyStress/{target_date}")
        except Exception as e:
            logger.warning(f"压力数据获取失败 {target_date}: {e}")
            return None

    def _save_stress(self, target_date, data):
        if not data:
            return False
        try:
            self.db.upsert_stress({
                "stressdate": target_date,
                "overalllevel": data.get("avgStressLevel"),
                "restduration": None,
                "lowduration": None,
                "mediumduration": None,
                "highduration": None,
                "stressscore": data.get("maxStressLevel"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            # 时序明细
            stress_values = data.get("stressValuesArray")
            if stress_values:
                self.db.batch_upsert_stress_details(target_date, stress_values)
            self.db.upsert_sync("garmin", "stress", target_date)
            return True
        except Exception as e:
            logger.error(f"压力存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "stress", target_date, status=0, errmsg=str(e))
            return False

    # ==================== 血氧数据 ====================

    def collect_spo2_data(self, target_date):
        try:
            return garth.connectapi(f"/wellness-service/wellness/daily/spo2/{target_date}")
        except Exception as e:
            logger.warning(f"血氧数据获取失败 {target_date}: {e}")
            return None

    def _save_spo2(self, target_date, data):
        if not data:
            return False
        try:
            self.db.upsert_spo2({
                "spo2date": target_date,
                "avgspo2": data.get("averageSpO2"),
                "lowspo2": data.get("lowestSpO2"),
                "highspo2": data.get("lastSevenDaysAvgSpO2"),
                "latestspo2": data.get("latestSpO2"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            # 血氧时序明细
            self.db.batch_upsert_spo2_details(target_date, data)
            self.db.upsert_sync("garmin", "spo2", target_date)
            return True
        except Exception as e:
            logger.error(f"血氧存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "spo2", target_date, status=0, errmsg=str(e))
            return False

    # ==================== 呼吸数据 ====================

    def collect_respiration_data(self, target_date):
        try:
            return garth.connectapi(f"/wellness-service/wellness/daily/respiration/{target_date}")
        except Exception as e:
            logger.warning(f"呼吸数据获取失败 {target_date}: {e}")
            return None

    def _save_respiration(self, target_date, data):
        if not data:
            return False
        try:
            self.db.upsert_respiration({
                "respdate": target_date,
                "avgwaking": data.get("avgWakingRespirationValue"),
                "highwaking": data.get("highestRespirationValue"),
                "lowwaking": data.get("lowestRespirationValue"),
                "avgsleeping": data.get("avgSleepRespirationValue"),
                "highsleeping": data.get("highestRespirationValue"),
                "lowsleeping": data.get("lowestRespirationValue"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            # 呼吸时序明细
            resp_values = data.get("respirationValuesArray")
            if resp_values:
                self.db.batch_upsert_respiration_details(target_date, resp_values)
            self.db.upsert_sync("garmin", "respiration", target_date)
            return True
        except Exception as e:
            logger.error(f"呼吸存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "respiration", target_date, status=0, errmsg=str(e))
            return False

    # ==================== HRV数据 ====================

    def collect_hrv_data(self, target_date):
        try:
            return garth.connectapi(f"/hrv-service/hrv/{target_date}")
        except Exception as e:
            logger.warning(f"HRV数据获取失败 {target_date}: {e}")
            return None

    def _save_hrv(self, target_date, data):
        if not data:
            return False
        summary = data.get("hrvSummary", data)
        baseline = summary.get("baseline", {})
        try:
            self.db.upsert_hrv({
                "hrvdate": target_date,
                "weeklyavg": summary.get("weeklyAvg"),
                "lastnightavg": summary.get("lastNightAvg"),
                "lastnight5minhigh": summary.get("lastNight5MinHigh"),
                "baselinelowupper": baseline.get("lowUpper"),
                "baselinebalancedlow": baseline.get("balancedLow"),
                "baselinebalancedupper": baseline.get("balancedUpper"),
                "hrvstatus": summary.get("status"),
                "rawjson": json.dumps(data, ensure_ascii=False, default=str),
            })
            self.db.upsert_sync("garmin", "hrv", target_date)
            return True
        except Exception as e:
            logger.error(f"HRV存储失败 {target_date}: {e}")
            self.db.upsert_sync("garmin", "hrv", target_date, status=0, errmsg=str(e))
            return False

    # ==================== 汇总采集 ====================

    def collect_all_data(self, days_back=7):
        print(f"\n🚀 开始采集最近{days_back}天的佳明健康数据...")
        print(f"{'='*60}")

        # 活动数据
        self.collect_activities(days_back)

        # 按日采集的数据类型
        daily_types = [
            ("❤️ 心率", "heartrate", self.collect_heart_rate_data, self._save_heart_rate),
            ("💤 睡眠", "sleep", self.collect_sleep_data, self._save_sleep),
            ("😰 压力", "stress", self.collect_stress_data, self._save_stress),
            ("🩸 血氧", "spo2", self.collect_spo2_data, self._save_spo2),
            ("🌬️ 呼吸", "respiration", self.collect_respiration_data, self._save_respiration),
            ("💓 HRV", "hrv", self.collect_hrv_data, self._save_hrv),
        ]

        for label, dtype, fetch_func, save_func in daily_types:
            print(f"\n{label} 数据...")
            success = 0
            for i in range(days_back):
                target_date = (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')

                # 检查是否已同步
                if self.db.is_synced("garmin", dtype, target_date):
                    print(f"  ⏭️ {target_date}: 已同步")
                    success += 1
                    continue

                data = fetch_func(target_date)
                if save_func(target_date, data):
                    print(f"  ✅ {target_date}: 已保存")
                    success += 1
                else:
                    print(f"  ⚠️ {target_date}: 无数据")

            print(f"  📊 {label} {success}/{days_back}")

        print(f"\n{'='*60}")
        print("✅ 数据采集完成！")
        print(f"{'='*60}")

    def cleanup(self):
        """清理资源"""
        self.db.close()


if __name__ == "__main__":
    collector = GarminDataCollector()
    try:
        collector.ensure_login()
        collector.collect_all_data(days_back=7)
    except Exception as e:
        print(f"❌ 数据采集失败: {e}")
        logger.error(f"数据采集失败: {e}", exc_info=True)
    finally:
        collector.cleanup()