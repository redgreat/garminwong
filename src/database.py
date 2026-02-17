#!/usr/bin/env python3
"""
数据库操作模块
负责佳明健康数据的存储
"""

import json
import logging
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone
from config import get_db_config

logger = logging.getLogger(__name__)


class GarminDatabase:
    """佳明数据库操作类"""

    def __init__(self):
        db_cfg = get_db_config()
        self.conn_params = {
            "host": db_cfg.get("host"),
            "port": db_cfg.get("port", 5432),
            "dbname": db_cfg.get("db"),
            "user": db_cfg.get("user"),
            "password": db_cfg.get("password"),
        }
        self._conn = None

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.conn_params)
        return self._conn

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    @staticmethod
    def _ts_to_dt(ts_ms):
        """毫秒时间戳转 datetime (UTC)"""
        if ts_ms is None:
            return None
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

    # ==================== 活动汇总 ====================

    def upsert_activity(self, data: dict):
        """插入或更新活动汇总"""
        sql = """
            INSERT INTO garmin_activity
                (activityid, activityname, activitytype, sporttype,
                 starttime, endtime, duration, distance, calories,
                 avghr, maxhr, avgspeed, maxspeed, avgcadence, maxcadence,
                 elevationgain, elevationloss, startlat, startlng, endlat, endlng,
                 trainingeffect, anaerobiceffect, avgpower, maxpower, vo2max, rawjson)
            VALUES
                (%(activityid)s, %(activityname)s, %(activitytype)s, %(sporttype)s,
                 %(starttime)s, %(endtime)s, %(duration)s, %(distance)s, %(calories)s,
                 %(avghr)s, %(maxhr)s, %(avgspeed)s, %(maxspeed)s, %(avgcadence)s, %(maxcadence)s,
                 %(elevationgain)s, %(elevationloss)s, %(startlat)s, %(startlng)s, %(endlat)s, %(endlng)s,
                 %(trainingeffect)s, %(anaerobiceffect)s, %(avgpower)s, %(maxpower)s, %(vo2max)s, %(rawjson)s)
            ON CONFLICT (activityid) DO UPDATE SET
                activityname = EXCLUDED.activityname,
                duration = EXCLUDED.duration,
                distance = EXCLUDED.distance,
                calories = EXCLUDED.calories,
                avghr = EXCLUDED.avghr,
                maxhr = EXCLUDED.maxhr,
                avgspeed = EXCLUDED.avgspeed,
                maxspeed = EXCLUDED.maxspeed,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"活动汇总写入失败: {e}")
            raise

    # ==================== 活动详情(GPS轨迹点) ====================

    def batch_upsert_activity_details(self, activity_id: str, points: list):
        """批量插入活动轨迹点"""
        if not points:
            return
        sql = """
            INSERT INTO garmin_activity_detail
                (activityid, pointtime, latitude, longitude, elevation,
                 heartrate, speed, cadence, power, temperature, distance)
            VALUES %s
            ON CONFLICT (activityid, pointtime) DO NOTHING
        """
        values = []
        for p in points:
            pt = p.get("pointtime")
            if pt is None:
                continue
            values.append((
                activity_id,
                pt,
                p.get("latitude"),
                p.get("longitude"),
                p.get("elevation"),
                p.get("heartrate"),
                p.get("speed"),
                p.get("cadence"),
                p.get("power"),
                p.get("temperature"),
                p.get("distance"),
            ))
        if not values:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"活动 {activity_id} 写入 {len(values)} 个轨迹点")
        except Exception as e:
            conn.rollback()
            logger.error(f"活动详情写入失败 {activity_id}: {e}")
            raise

    # ==================== 睡眠 ====================

    def upsert_sleep(self, data: dict):
        sql = """
            INSERT INTO garmin_sleep
                (sleepdate, sleepstart, sleepend, totalsleep, deepsleep, lightsleep,
                 remsleep, awaketime, sleepscore, sleepquality, restlesscount,
                 avgspo2, lowspo2, highspo2, avgrespiration, rawjson)
            VALUES
                (%(sleepdate)s, %(sleepstart)s, %(sleepend)s, %(totalsleep)s,
                 %(deepsleep)s, %(lightsleep)s, %(remsleep)s, %(awaketime)s,
                 %(sleepscore)s, %(sleepquality)s, %(restlesscount)s,
                 %(avgspo2)s, %(lowspo2)s, %(highspo2)s, %(avgrespiration)s, %(rawjson)s)
            ON CONFLICT (sleepdate) DO UPDATE SET
                sleepstart = EXCLUDED.sleepstart,
                sleepend = EXCLUDED.sleepend,
                totalsleep = EXCLUDED.totalsleep,
                deepsleep = EXCLUDED.deepsleep,
                lightsleep = EXCLUDED.lightsleep,
                remsleep = EXCLUDED.remsleep,
                awaketime = EXCLUDED.awaketime,
                sleepscore = EXCLUDED.sleepscore,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"睡眠数据写入失败: {e}")
            raise

    # ==================== 睡眠明细(阶段) ====================

    def batch_upsert_sleep_details(self, sleep_date: str, levels: list):
        """批量插入睡眠阶段数据 levels: [{startGMT, endGMT, activityLevel}, ...]"""
        if not levels:
            return
        sql = """
            INSERT INTO garmin_sleep_detail (sleepdate, starttime, endtime, activitylevel)
            VALUES %s
            ON CONFLICT (sleepdate, starttime) DO NOTHING
        """
        values = []
        for lv in levels:
            start = lv.get("startGMT")
            end = lv.get("endGMT")
            al = lv.get("activityLevel")
            if start is None or al is None:
                continue
            values.append((sleep_date, start, end, al))
        if not values:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"睡眠明细 {sleep_date} 写入 {len(values)} 条")
        except Exception as e:
            conn.rollback()
            logger.error(f"睡眠明细写入失败 {sleep_date}: {e}")
            raise

    # ==================== 心率汇总 ====================

    def upsert_heartrate(self, data: dict):
        sql = """
            INSERT INTO garmin_heartrate (hrdate, restinghr, maxhr, minhr, rawjson)
            VALUES (%(hrdate)s, %(restinghr)s, %(maxhr)s, %(minhr)s, %(rawjson)s)
            ON CONFLICT (hrdate) DO UPDATE SET
                restinghr = EXCLUDED.restinghr,
                maxhr = EXCLUDED.maxhr,
                minhr = EXCLUDED.minhr,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"心率汇总写入失败: {e}")
            raise

    # ==================== 心率时序明细 ====================

    def batch_upsert_heartrate_details(self, hr_date: str, points: list):
        """批量插入心率时序数据 points: [[timestamp_ms, hr_value], ...]"""
        if not points:
            return
        sql = """
            INSERT INTO garmin_heartrate_detail (hrdate, pointtime, heartrate)
            VALUES %s
            ON CONFLICT (hrdate, pointtime) DO NOTHING
        """
        values = []
        for p in points:
            if p is None or len(p) < 2 or p[1] is None:
                continue
            pt = self._ts_to_dt(p[0])
            if pt is None:
                continue
            values.append((hr_date, pt, int(p[1])))

        if not values:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"心率明细 {hr_date} 写入 {len(values)} 条")
        except Exception as e:
            conn.rollback()
            logger.error(f"心率明细写入失败 {hr_date}: {e}")
            raise

    # ==================== 压力汇总 ====================

    def upsert_stress(self, data: dict):
        sql = """
            INSERT INTO garmin_stress
                (stressdate, overalllevel, restduration, lowduration, mediumduration,
                 highduration, stressscore, rawjson)
            VALUES
                (%(stressdate)s, %(overalllevel)s, %(restduration)s, %(lowduration)s,
                 %(mediumduration)s, %(highduration)s, %(stressscore)s, %(rawjson)s)
            ON CONFLICT (stressdate) DO UPDATE SET
                overalllevel = EXCLUDED.overalllevel,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"压力汇总写入失败: {e}")
            raise

    # ==================== 压力时序明细 ====================

    def batch_upsert_stress_details(self, stress_date: str, points: list):
        """批量插入压力时序数据 points: [[timestamp_ms, stress_level], ...]"""
        if not points:
            return
        sql = """
            INSERT INTO garmin_stress_detail (stressdate, pointtime, stresslevel)
            VALUES %s
            ON CONFLICT (stressdate, pointtime) DO NOTHING
        """
        values = []
        for p in points:
            if p is None or len(p) < 2 or p[1] is None:
                continue
            # 压力值 -1/-2 代表无数据/休息，跳过
            if p[1] < 0:
                continue
            pt = self._ts_to_dt(p[0])
            if pt is None:
                continue
            values.append((stress_date, pt, int(p[1])))

        if not values:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"压力明细 {stress_date} 写入 {len(values)} 条")
        except Exception as e:
            conn.rollback()
            logger.error(f"压力明细写入失败 {stress_date}: {e}")
            raise

    # ==================== 血氧 ====================

    def upsert_spo2(self, data: dict):
        sql = """
            INSERT INTO garmin_spo2 (spo2date, avgspo2, lowspo2, highspo2, latestspo2, rawjson)
            VALUES (%(spo2date)s, %(avgspo2)s, %(lowspo2)s, %(highspo2)s, %(latestspo2)s, %(rawjson)s)
            ON CONFLICT (spo2date) DO UPDATE SET
                avgspo2 = EXCLUDED.avgspo2,
                lowspo2 = EXCLUDED.lowspo2,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"血氧数据写入失败: {e}")
            raise

    # ==================== 血氧明细(时序) ====================

    def batch_upsert_spo2_details(self, spo2_date: str, data: dict):
        """批量插入血氧时序数据，从多个来源合并"""
        values = []

        # spO2HourlyAverages: [[timestamp_ms, value], ...]
        hourly = data.get("spO2HourlyAverages")
        if hourly and isinstance(hourly, list):
            for p in hourly:
                if p and len(p) >= 2 and p[1] is not None:
                    pt = self._ts_to_dt(p[0])
                    if pt:
                        values.append((spo2_date, pt, float(p[1]), "hourly"))

        # continuousReadingDTOList: [{spo2, readingTimeGMT, ...}, ...]
        continuous = data.get("continuousReadingDTOList")
        if continuous and isinstance(continuous, list):
            for p in continuous:
                ts = p.get("readingTimeGMT")
                val = p.get("spo2")
                if ts and val:
                    pt = self._ts_to_dt(ts) if isinstance(ts, (int, float)) else ts
                    values.append((spo2_date, pt, float(val), "continuous"))

        if not values:
            return
        sql = """
            INSERT INTO garmin_spo2_detail (spo2date, pointtime, spo2value, readingsource)
            VALUES %s
            ON CONFLICT (spo2date, pointtime) DO NOTHING
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"血氧明细 {spo2_date} 写入 {len(values)} 条")
        except Exception as e:
            conn.rollback()
            logger.error(f"血氧明细写入失败 {spo2_date}: {e}")
            raise

    # ==================== 呼吸 ====================

    def upsert_respiration(self, data: dict):
        sql = """
            INSERT INTO garmin_respiration
                (respdate, avgwaking, highwaking, lowwaking, avgsleeping, highsleeping, lowsleeping, rawjson)
            VALUES
                (%(respdate)s, %(avgwaking)s, %(highwaking)s, %(lowwaking)s,
                 %(avgsleeping)s, %(highsleeping)s, %(lowsleeping)s, %(rawjson)s)
            ON CONFLICT (respdate) DO UPDATE SET
                avgwaking = EXCLUDED.avgwaking,
                avgsleeping = EXCLUDED.avgsleeping,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"呼吸数据写入失败: {e}")
            raise

    # ==================== 呼吸明细(时序) ====================

    def batch_upsert_respiration_details(self, resp_date: str, points: list):
        """批量插入呼吸时序数据 points: [[timestamp_ms, resp_value], ...]"""
        if not points:
            return
        sql = """
            INSERT INTO garmin_respiration_detail (respdate, pointtime, respvalue)
            VALUES %s
            ON CONFLICT (respdate, pointtime) DO NOTHING
        """
        values = []
        for p in points:
            if p is None or len(p) < 2 or p[1] is None:
                continue
            pt = self._ts_to_dt(p[0])
            if pt is None:
                continue
            values.append((resp_date, pt, float(p[1])))

        if not values:
            return
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, values, page_size=500)
            conn.commit()
            logger.info(f"呼吸明细 {resp_date} 写入 {len(values)} 条")
        except Exception as e:
            conn.rollback()
            logger.error(f"呼吸明细写入失败 {resp_date}: {e}")
            raise

    # ==================== HRV ====================


    def upsert_hrv(self, data: dict):
        sql = """
            INSERT INTO garmin_hrv
                (hrvdate, weeklyavg, lastnightavg, lastnight5minhigh,
                 baselinelowupper, baselinebalancedlow, baselinebalancedupper, hrvstatus, rawjson)
            VALUES
                (%(hrvdate)s, %(weeklyavg)s, %(lastnightavg)s, %(lastnight5minhigh)s,
                 %(baselinelowupper)s, %(baselinebalancedlow)s, %(baselinebalancedupper)s,
                 %(hrvstatus)s, %(rawjson)s)
            ON CONFLICT (hrvdate) DO UPDATE SET
                weeklyavg = EXCLUDED.weeklyavg,
                lastnightavg = EXCLUDED.lastnightavg,
                rawjson = EXCLUDED.rawjson
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, data)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"HRV数据写入失败: {e}")
            raise

    # ==================== 活动去重 ====================

    def activity_exists(self, activity_id: str) -> bool:
        """检查活动是否已存在"""
        sql = "SELECT 1 FROM garmin_activity WHERE activityid = %s"
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (activity_id,))
                return cur.fetchone() is not None
        except Exception:
            return False

    # ==================== 同步记录 ====================

    def upsert_sync(self, datasource: str, datatype: str, datadate: str,
                    dataid: str = None, status: int = 1, errmsg: str = None):
        sql = """
            INSERT INTO garmin_sync (datasource, datatype, datadate, dataid, syncstatus, errmessage)
            VALUES (%(datasource)s, %(datatype)s, %(datadate)s, %(dataid)s, %(syncstatus)s, %(errmessage)s)
            ON CONFLICT (datasource, datatype, datadate) DO UPDATE SET
                dataid = EXCLUDED.dataid,
                syncstatus = EXCLUDED.syncstatus,
                errmessage = EXCLUDED.errmessage
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, {
                    "datasource": datasource,
                    "datatype": datatype,
                    "datadate": datadate,
                    "dataid": dataid,
                    "syncstatus": status,
                    "errmessage": errmsg,
                })
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"同步记录写入失败: {e}")
            raise

    def is_synced(self, datasource: str, datatype: str, datadate: str) -> bool:
        """检查某日数据是否已同步"""
        sql = """
            SELECT 1 FROM garmin_sync
            WHERE datasource = %s AND datatype = %s AND datadate = %s AND syncstatus = 1
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (datasource, datatype, datadate))
                return cur.fetchone() is not None
        except Exception:
            return False
