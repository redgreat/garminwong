-- @author wangcw
-- @copyright (c) 2026, redgreat
-- created : 2026-02-15 21:38:17
-- 佳明健康数据表结构，适配garth API

-- 设置查询路径
alter role user_eadm set search_path to eadm, public;

--设置 本地时区
set time zone 'asia/shanghai';

-- 表最后一次更新时间函数
drop function if exists lastupdate cascade;
create or replace function lastupdate()
returns trigger as $$
begin
    new.updatedat := current_timestamp;
    return new;
end;
$$ language plpgsql;

-- =============================================
-- 佳明_活动记录表
-- =============================================
drop table if exists garmin_activity cascade;
create table garmin_activity (
  id serial,
  activityid varchar(50) not null,
  activityname varchar(255),
  activitytype varchar(100),
  sporttype varchar(100),
  starttime timestamptz,
  endtime timestamptz,
  duration numeric(12,2),
  distance numeric(12,2),
  calories int,
  avghr int,
  maxhr int,
  avgspeed numeric(10,4),
  maxspeed numeric(10,4),
  avgcadence int,
  maxcadence int,
  elevationgain numeric(10,2),
  elevationloss numeric(10,2),
  startlat numeric(12,8),
  startlng numeric(12,8),
  endlat numeric(12,8),
  endlng numeric(12,8),
  trainingeffect numeric(4,2),
  anaerobiceffect numeric(4,2),
  avgpower int,
  maxpower int,
  vo2max numeric(6,2),
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_activity owner to user_eadm;
alter table garmin_activity drop constraint if exists pk_activity_id cascade;
alter table garmin_activity add constraint pk_activity_id primary key (id);
alter table garmin_activity drop constraint if exists uni_activity_activityid cascade;
alter table garmin_activity add constraint uni_activity_activityid unique (activityid);

drop index if exists non_activity_starttime;
create index non_activity_starttime on garmin_activity using btree (starttime desc nulls last);
drop index if exists non_activity_activitytype;
create index non_activity_activitytype on garmin_activity using btree (activitytype asc nulls last);

comment on column garmin_activity.id is '自增主键';
comment on column garmin_activity.activityid is '佳明活动id';
comment on column garmin_activity.activityname is '活动名称';
comment on column garmin_activity.activitytype is '活动类型';
comment on column garmin_activity.sporttype is '运动类型';
comment on column garmin_activity.starttime is '开始时间';
comment on column garmin_activity.endtime is '结束时间';
comment on column garmin_activity.duration is '持续时长(秒)';
comment on column garmin_activity.distance is '距离(米)';
comment on column garmin_activity.calories is '消耗卡路里';
comment on column garmin_activity.avghr is '平均心率';
comment on column garmin_activity.maxhr is '最大心率';
comment on column garmin_activity.avgspeed is '平均速度(m/s)';
comment on column garmin_activity.maxspeed is '最大速度(m/s)';
comment on column garmin_activity.avgcadence is '平均步频';
comment on column garmin_activity.maxcadence is '最大步频';
comment on column garmin_activity.elevationgain is '累计爬升(米)';
comment on column garmin_activity.elevationloss is '累计下降(米)';
comment on column garmin_activity.startlat is '起点纬度';
comment on column garmin_activity.startlng is '起点经度';
comment on column garmin_activity.endlat is '终点纬度';
comment on column garmin_activity.endlng is '终点经度';
comment on column garmin_activity.trainingeffect is '有氧训练效果';
comment on column garmin_activity.anaerobiceffect is '无氧训练效果';
comment on column garmin_activity.avgpower is '平均功率(w)';
comment on column garmin_activity.maxpower is '最大功率(w)';
comment on column garmin_activity.vo2max is '最大摄氧量';
comment on column garmin_activity.rawjson is '原始json数据';
comment on column garmin_activity.createdat is '创建时间';
comment on column garmin_activity.updatedat is '更新时间';
comment on table garmin_activity is '佳明_活动记录表';

drop trigger if exists activity_lastupdate on garmin_activity cascade;
create or replace trigger activity_lastupdate
before update on garmin_activity
for each row
execute function lastupdate();

-- =============================================
-- 佳明_活动详情表（GPS轨迹点）
-- =============================================
drop table if exists garmin_activity_detail cascade;
create table garmin_activity_detail (
  id serial,
  activityid varchar(50) not null,
  pointtime timestamptz not null,
  latitude numeric(12,8),
  longitude numeric(12,8),
  elevation numeric(10,2),
  heartrate int,
  speed numeric(10,4),
  cadence int,
  power int,
  temperature numeric(5,1),
  distance numeric(12,2),
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_activity_detail owner to user_eadm;
alter table garmin_activity_detail drop constraint if exists pk_activity_detail_id cascade;
alter table garmin_activity_detail add constraint pk_activity_detail_id primary key (id);
alter table garmin_activity_detail drop constraint if exists uni_activity_detail_point cascade;
alter table garmin_activity_detail add constraint uni_activity_detail_point unique (activityid, pointtime);

drop index if exists non_activity_detail_activityid;
create index non_activity_detail_activityid on garmin_activity_detail using btree (activityid asc nulls last);
drop index if exists non_activity_detail_pointtime;
create index non_activity_detail_pointtime on garmin_activity_detail using btree (pointtime desc nulls last);

comment on column garmin_activity_detail.id is '自增主键';
comment on column garmin_activity_detail.activityid is '活动id';
comment on column garmin_activity_detail.pointtime is '轨迹点时间';
comment on column garmin_activity_detail.latitude is '纬度';
comment on column garmin_activity_detail.longitude is '经度';
comment on column garmin_activity_detail.elevation is '海拔(米)';
comment on column garmin_activity_detail.heartrate is '心率';
comment on column garmin_activity_detail.speed is '速度(m/s)';
comment on column garmin_activity_detail.cadence is '步频';
comment on column garmin_activity_detail.power is '功率(w)';
comment on column garmin_activity_detail.temperature is '温度(℃)';
comment on column garmin_activity_detail.distance is '累计距离(米)';
comment on column garmin_activity_detail.createdat is '创建时间';
comment on column garmin_activity_detail.updatedat is '更新时间';
comment on table garmin_activity_detail is '佳明_活动详情表(gps轨迹点)';

drop trigger if exists activity_detail_lastupdate on garmin_activity_detail cascade;
create or replace trigger activity_detail_lastupdate
before update on garmin_activity_detail
for each row
execute function lastupdate();

-- =============================================
-- 佳明_心率时序表
-- =============================================
drop table if exists garmin_heartrate_detail cascade;
create table garmin_heartrate_detail (
  id serial,
  hrdate date not null,
  pointtime timestamptz not null,
  heartrate int not null,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_heartrate_detail owner to user_eadm;
alter table garmin_heartrate_detail drop constraint if exists pk_heartrate_detail_id cascade;
alter table garmin_heartrate_detail add constraint pk_heartrate_detail_id primary key (id);
alter table garmin_heartrate_detail drop constraint if exists uni_heartrate_detail_point cascade;
alter table garmin_heartrate_detail add constraint uni_heartrate_detail_point unique (hrdate, pointtime);

drop index if exists non_heartrate_detail_hrdate;
create index non_heartrate_detail_hrdate on garmin_heartrate_detail using btree (hrdate desc nulls last);

comment on column garmin_heartrate_detail.id is '自增主键';
comment on column garmin_heartrate_detail.hrdate is '心率日期';
comment on column garmin_heartrate_detail.pointtime is '时间点';
comment on column garmin_heartrate_detail.heartrate is '心率值';
comment on column garmin_heartrate_detail.createdat is '创建时间';
comment on column garmin_heartrate_detail.updatedat is '更新时间';
comment on table garmin_heartrate_detail is '佳明_心率时序明细表';

drop trigger if exists heartrate_detail_lastupdate on garmin_heartrate_detail cascade;
create or replace trigger heartrate_detail_lastupdate
before update on garmin_heartrate_detail
for each row
execute function lastupdate();

-- =============================================
-- 佳明_压力时序表
-- =============================================
drop table if exists garmin_stress_detail cascade;
create table garmin_stress_detail (
  id serial,
  stressdate date not null,
  pointtime timestamptz not null,
  stresslevel int not null,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_stress_detail owner to user_eadm;
alter table garmin_stress_detail drop constraint if exists pk_stress_detail_id cascade;
alter table garmin_stress_detail add constraint pk_stress_detail_id primary key (id);
alter table garmin_stress_detail drop constraint if exists uni_stress_detail_point cascade;
alter table garmin_stress_detail add constraint uni_stress_detail_point unique (stressdate, pointtime);

drop index if exists non_stress_detail_stressdate;
create index non_stress_detail_stressdate on garmin_stress_detail using btree (stressdate desc nulls last);

comment on column garmin_stress_detail.id is '自增主键';
comment on column garmin_stress_detail.stressdate is '压力日期';
comment on column garmin_stress_detail.pointtime is '时间点';
comment on column garmin_stress_detail.stresslevel is '压力值';
comment on column garmin_stress_detail.createdat is '创建时间';
comment on column garmin_stress_detail.updatedat is '更新时间';
comment on table garmin_stress_detail is '佳明_压力时序明细表';

drop trigger if exists stress_detail_lastupdate on garmin_stress_detail cascade;
create or replace trigger stress_detail_lastupdate
before update on garmin_stress_detail
for each row
execute function lastupdate();

-- =============================================
-- 佳明_睡眠明细表（睡眠阶段）
-- =============================================
drop table if exists garmin_sleep_detail cascade;
create table garmin_sleep_detail (
  id serial,
  sleepdate date not null,
  starttime timestamptz not null,
  endtime timestamptz,
  activitylevel numeric(4,1) not null,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_sleep_detail owner to user_garmin;
alter table garmin_sleep_detail drop constraint if exists pk_sleep_detail_id cascade;
alter table garmin_sleep_detail add constraint pk_sleep_detail_id primary key (id);
alter table garmin_sleep_detail drop constraint if exists uni_sleep_detail_point cascade;
alter table garmin_sleep_detail add constraint uni_sleep_detail_point unique (sleepdate, starttime);

drop index if exists non_sleep_detail_sleepdate;
create index non_sleep_detail_sleepdate on garmin_sleep_detail using btree (sleepdate desc nulls last);

comment on column garmin_sleep_detail.id is '自增主键';
comment on column garmin_sleep_detail.sleepdate is '睡眠日期';
comment on column garmin_sleep_detail.starttime is '阶段开始时间';
comment on column garmin_sleep_detail.endtime is '阶段结束时间';
comment on column garmin_sleep_detail.activitylevel is '睡眠阶段(0深睡/1浅睡/2rem/3清醒)';
comment on column garmin_sleep_detail.createdat is '创建时间';
comment on column garmin_sleep_detail.updatedat is '更新时间';
comment on table garmin_sleep_detail is '佳明_睡眠明细表(睡眠阶段)';

drop trigger if exists sleep_detail_lastupdate on garmin_sleep_detail cascade;
create or replace trigger sleep_detail_lastupdate
before update on garmin_sleep_detail
for each row
execute function lastupdate();


-- =============================================
drop table if exists garmin_sleep cascade;
create table garmin_sleep (
  id serial,
  sleepdate date not null,
  sleepstart timestamptz,
  sleepend timestamptz,
  totalsleep int,
  deepsleep int,
  lightsleep int,
  remsleep int,
  awaketime int,
  sleepscore int,
  sleepquality varchar(20),
  restlesscount int,
  avgspo2 numeric(5,2),
  lowspo2 numeric(5,2),
  highspo2 numeric(5,2),
  avgrespiration numeric(5,2),
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_sleep owner to user_eadm;
alter table garmin_sleep drop constraint if exists pk_sleep_id cascade;
alter table garmin_sleep add constraint pk_sleep_id primary key (id);
alter table garmin_sleep drop constraint if exists uni_sleep_sleepdate cascade;
alter table garmin_sleep add constraint uni_sleep_sleepdate unique (sleepdate);

drop index if exists non_sleep_sleepdate;
create index non_sleep_sleepdate on garmin_sleep using btree (sleepdate desc nulls last);

comment on column garmin_sleep.id is '自增主键';
comment on column garmin_sleep.sleepdate is '睡眠日期';
comment on column garmin_sleep.sleepstart is '入睡时间';
comment on column garmin_sleep.sleepend is '起床时间';
comment on column garmin_sleep.totalsleep is '总睡眠时长(分钟)';
comment on column garmin_sleep.deepsleep is '深睡眠时长(分钟)';
comment on column garmin_sleep.lightsleep is '浅睡眠时长(分钟)';
comment on column garmin_sleep.remsleep is 'rem睡眠时长(分钟)';
comment on column garmin_sleep.awaketime is '清醒时长(分钟)';
comment on column garmin_sleep.sleepscore is '睡眠评分';
comment on column garmin_sleep.sleepquality is '睡眠质量';
comment on column garmin_sleep.restlesscount is '翻身次数';
comment on column garmin_sleep.avgspo2 is '平均血氧';
comment on column garmin_sleep.lowspo2 is '最低血氧';
comment on column garmin_sleep.highspo2 is '最高血氧';
comment on column garmin_sleep.avgrespiration is '平均呼吸频率';
comment on column garmin_sleep.rawjson is '原始json数据';
comment on column garmin_sleep.createdat is '创建时间';
comment on column garmin_sleep.updatedat is '更新时间';
comment on table garmin_sleep is '佳明_睡眠数据表';

drop trigger if exists sleep_lastupdate on garmin_sleep cascade;
create or replace trigger sleep_lastupdate
before update on garmin_sleep
for each row
execute function lastupdate();

-- =============================================
-- 佳明_心率数据表
-- =============================================
drop table if exists garmin_heartrate cascade;
create table garmin_heartrate (
  id serial,
  hrdate date not null,
  restinghr int,
  maxhr int,
  minhr int,
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_heartrate owner to user_eadm;
alter table garmin_heartrate drop constraint if exists pk_heartrate_id cascade;
alter table garmin_heartrate add constraint pk_heartrate_id primary key (id);
alter table garmin_heartrate drop constraint if exists uni_heartrate_hrdate cascade;
alter table garmin_heartrate add constraint uni_heartrate_hrdate unique (hrdate);

drop index if exists non_heartrate_hrdate;
create index non_heartrate_hrdate on garmin_heartrate using btree (hrdate desc nulls last);

comment on column garmin_heartrate.id is '自增主键';
comment on column garmin_heartrate.hrdate is '心率日期';
comment on column garmin_heartrate.restinghr is '静息心率';
comment on column garmin_heartrate.maxhr is '最大心率';
comment on column garmin_heartrate.minhr is '最低心率';
comment on column garmin_heartrate.rawjson is '原始json数据';
comment on column garmin_heartrate.createdat is '创建时间';
comment on column garmin_heartrate.updatedat is '更新时间';
comment on table garmin_heartrate is '佳明_心率数据表';

drop trigger if exists heartrate_lastupdate on garmin_heartrate cascade;
create or replace trigger heartrate_lastupdate
before update on garmin_heartrate
for each row
execute function lastupdate();

-- =============================================
-- 佳明_压力数据表
-- =============================================
drop table if exists garmin_stress cascade;
create table garmin_stress (
  id serial,
  stressdate date not null,
  overalllevel int,
  restduration int,
  lowduration int,
  mediumduration int,
  highduration int,
  stressscore int,
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_stress owner to user_eadm;
alter table garmin_stress drop constraint if exists pk_stress_id cascade;
alter table garmin_stress add constraint pk_stress_id primary key (id);
alter table garmin_stress drop constraint if exists uni_stress_stressdate cascade;
alter table garmin_stress add constraint uni_stress_stressdate unique (stressdate);

drop index if exists non_stress_stressdate;
create index non_stress_stressdate on garmin_stress using btree (stressdate desc nulls last);

comment on column garmin_stress.id is '自增主键';
comment on column garmin_stress.stressdate is '压力日期';
comment on column garmin_stress.overalllevel is '综合压力水平';
comment on column garmin_stress.restduration is '休息时长(秒)';
comment on column garmin_stress.lowduration is '低压力时长(秒)';
comment on column garmin_stress.mediumduration is '中等压力时长(秒)';
comment on column garmin_stress.highduration is '高压力时长(秒)';
comment on column garmin_stress.stressscore is '压力评分';
comment on column garmin_stress.rawjson is '原始json数据';
comment on column garmin_stress.createdat is '创建时间';
comment on column garmin_stress.updatedat is '更新时间';
comment on table garmin_stress is '佳明_压力数据表';

drop trigger if exists stress_lastupdate on garmin_stress cascade;
create or replace trigger stress_lastupdate
before update on garmin_stress
for each row
execute function lastupdate();

-- =============================================
-- 佳明_血氧数据表
-- =============================================
drop table if exists garmin_spo2 cascade;
create table garmin_spo2 (
  id serial,
  spo2date date not null,
  avgspo2 numeric(5,2),
  lowspo2 numeric(5,2),
  highspo2 numeric(5,2),
  latestspo2 numeric(5,2),
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_spo2 owner to user_eadm;
alter table garmin_spo2 drop constraint if exists pk_spo2_id cascade;
alter table garmin_spo2 add constraint pk_spo2_id primary key (id);
alter table garmin_spo2 drop constraint if exists uni_spo2_spo2date cascade;
alter table garmin_spo2 add constraint uni_spo2_spo2date unique (spo2date);

drop index if exists non_spo2_spo2date;
create index non_spo2_spo2date on garmin_spo2 using btree (spo2date desc nulls last);

comment on column garmin_spo2.id is '自增主键';
comment on column garmin_spo2.spo2date is '血氧日期';
comment on column garmin_spo2.avgspo2 is '平均血氧';
comment on column garmin_spo2.lowspo2 is '最低血氧';
comment on column garmin_spo2.highspo2 is '最高血氧';
comment on column garmin_spo2.latestspo2 is '最近一次血氧';
comment on column garmin_spo2.rawjson is '原始json数据';
comment on column garmin_spo2.createdat is '创建时间';
comment on column garmin_spo2.updatedat is '更新时间';
comment on table garmin_spo2 is '佳明_脉搏血氧数据表';

drop trigger if exists spo2_lastupdate on garmin_spo2 cascade;
create or replace trigger spo2_lastupdate
before update on garmin_spo2
for each row
execute function lastupdate();

-- =============================================
-- 佳明_血氧明细表（时序数据点）
-- =============================================
drop table if exists garmin_spo2_detail cascade;
create table garmin_spo2_detail (
  id serial,
  spo2date date not null,
  pointtime timestamptz not null,
  spo2value numeric(5,2) not null,
  readingsource varchar(20),
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_spo2_detail owner to user_garmin;
alter table garmin_spo2_detail drop constraint if exists pk_spo2_detail_id cascade;
alter table garmin_spo2_detail add constraint pk_spo2_detail_id primary key (id);
alter table garmin_spo2_detail drop constraint if exists uni_spo2_detail_point cascade;
alter table garmin_spo2_detail add constraint uni_spo2_detail_point unique (spo2date, pointtime);

drop index if exists non_spo2_detail_spo2date;
create index non_spo2_detail_spo2date on garmin_spo2_detail using btree (spo2date desc nulls last);

comment on column garmin_spo2_detail.id is '自增主键';
comment on column garmin_spo2_detail.spo2date is '血氧日期';
comment on column garmin_spo2_detail.pointtime is '采集时间';
comment on column garmin_spo2_detail.spo2value is '血氧值';
comment on column garmin_spo2_detail.readingsource is '读取来源(hourly/continuous/single)';
comment on column garmin_spo2_detail.createdat is '创建时间';
comment on column garmin_spo2_detail.updatedat is '更新时间';
comment on table garmin_spo2_detail is '佳明_血氧明细表(时序数据点)';

drop trigger if exists spo2_detail_lastupdate on garmin_spo2_detail cascade;
create or replace trigger spo2_detail_lastupdate
before update on garmin_spo2_detail
for each row
execute function lastupdate();

-- =============================================
-- 佳明_呼吸数据表
-- =============================================

drop table if exists garmin_respiration cascade;
create table garmin_respiration (
  id serial,
  respdate date not null,
  avgwaking numeric(5,2),
  highwaking numeric(5,2),
  lowwaking numeric(5,2),
  avgsleeping numeric(5,2),
  highsleeping numeric(5,2),
  lowsleeping numeric(5,2),
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_respiration owner to user_eadm;
alter table garmin_respiration drop constraint if exists pk_respiration_id cascade;
alter table garmin_respiration add constraint pk_respiration_id primary key (id);
alter table garmin_respiration drop constraint if exists uni_respiration_respdate cascade;
alter table garmin_respiration add constraint uni_respiration_respdate unique (respdate);

drop index if exists non_respiration_respdate;
create index non_respiration_respdate on garmin_respiration using btree (respdate desc nulls last);

comment on column garmin_respiration.id is '自增主键';
comment on column garmin_respiration.respdate is '呼吸日期';
comment on column garmin_respiration.avgwaking is '清醒时平均呼吸(次/分钟)';
comment on column garmin_respiration.highwaking is '清醒时最高呼吸(次/分钟)';
comment on column garmin_respiration.lowwaking is '清醒时最低呼吸(次/分钟)';
comment on column garmin_respiration.avgsleeping is '睡眠时平均呼吸(次/分钟)';
comment on column garmin_respiration.highsleeping is '睡眠时最高呼吸(次/分钟)';
comment on column garmin_respiration.lowsleeping is '睡眠时最低呼吸(次/分钟)';
comment on column garmin_respiration.rawjson is '原始json数据';
comment on column garmin_respiration.createdat is '创建时间';
comment on column garmin_respiration.updatedat is '更新时间';
comment on table garmin_respiration is '佳明_呼吸数据表';

drop trigger if exists respiration_lastupdate on garmin_respiration cascade;
create or replace trigger respiration_lastupdate
before update on garmin_respiration
for each row
execute function lastupdate();

-- =============================================
-- 佳明_呼吸明细表（时序数据点）
-- =============================================
drop table if exists garmin_respiration_detail cascade;
create table garmin_respiration_detail (
  id serial,
  respdate date not null,
  pointtime timestamptz not null,
  respvalue numeric(5,2) not null,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_respiration_detail owner to user_garmin;
alter table garmin_respiration_detail drop constraint if exists pk_respiration_detail_id cascade;
alter table garmin_respiration_detail add constraint pk_respiration_detail_id primary key (id);
alter table garmin_respiration_detail drop constraint if exists uni_respiration_detail_point cascade;
alter table garmin_respiration_detail add constraint uni_respiration_detail_point unique (respdate, pointtime);

drop index if exists non_respiration_detail_respdate;
create index non_respiration_detail_respdate on garmin_respiration_detail using btree (respdate desc nulls last);

comment on column garmin_respiration_detail.id is '自增主键';
comment on column garmin_respiration_detail.respdate is '呼吸日期';
comment on column garmin_respiration_detail.pointtime is '采集时间';
comment on column garmin_respiration_detail.respvalue is '呼吸频率(次/分钟)';
comment on column garmin_respiration_detail.createdat is '创建时间';
comment on column garmin_respiration_detail.updatedat is '更新时间';
comment on table garmin_respiration_detail is '佳明_呼吸明细表(时序数据点)';

drop trigger if exists respiration_detail_lastupdate on garmin_respiration_detail cascade;
create or replace trigger respiration_detail_lastupdate
before update on garmin_respiration_detail
for each row
execute function lastupdate();

-- =============================================
-- 佳明_HRV数据表
-- =============================================

drop table if exists garmin_hrv cascade;
create table garmin_hrv (
  id serial,
  hrvdate date not null,
  weeklyavg numeric(8,2),
  lastnightavg numeric(8,2),
  lastnight5minhigh numeric(8,2),
  baselinelowupper numeric(8,2),
  baselinebalancedlow numeric(8,2),
  baselinebalancedupper numeric(8,2),
  hrvstatus varchar(20),
  rawjson json,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_hrv owner to user_eadm;
alter table garmin_hrv drop constraint if exists pk_hrv_id cascade;
alter table garmin_hrv add constraint pk_hrv_id primary key (id);
alter table garmin_hrv drop constraint if exists uni_hrv_hrvdate cascade;
alter table garmin_hrv add constraint uni_hrv_hrvdate unique (hrvdate);

drop index if exists non_hrv_hrvdate;
create index non_hrv_hrvdate on garmin_hrv using btree (hrvdate desc nulls last);

comment on column garmin_hrv.id is '自增主键';
comment on column garmin_hrv.hrvdate is 'hrv日期';
comment on column garmin_hrv.weeklyavg is '周平均值';
comment on column garmin_hrv.lastnightavg is '昨晚平均值';
comment on column garmin_hrv.lastnight5minhigh is '昨晚5分钟最高值';
comment on column garmin_hrv.baselinelowupper is '基线低值上限';
comment on column garmin_hrv.baselinebalancedlow is '基线平衡低值';
comment on column garmin_hrv.baselinebalancedupper is '基线平衡上限';
comment on column garmin_hrv.hrvstatus is 'hrv状态';
comment on column garmin_hrv.rawjson is '原始json数据';
comment on column garmin_hrv.createdat is '创建时间';
comment on column garmin_hrv.updatedat is '更新时间';
comment on table garmin_hrv is '佳明_hrv数据表';

drop trigger if exists hrv_lastupdate on garmin_hrv cascade;
create or replace trigger hrv_lastupdate
before update on garmin_hrv
for each row
execute function lastupdate();

-- =============================================
-- 数据同步记录表（下载保存记录，做去重用）
-- =============================================
drop table if exists garmin_sync cascade;
create table garmin_sync (
  id serial,
  datasource varchar(20) not null,
  datatype varchar(50) not null,
  datadate date not null,
  dataid varchar(50),
  syncstatus smallint not null default 1,
  errmessage text,
  createdat timestamptz default current_timestamp,
  updatedat timestamptz default current_timestamp
);

alter table garmin_sync owner to user_eadm;
alter table garmin_sync drop constraint if exists pk_sync_id cascade;
alter table garmin_sync add constraint pk_sync_id primary key (id);
alter table garmin_sync drop constraint if exists uni_sync_source_type_date cascade;
alter table garmin_sync add constraint uni_sync_source_type_date unique (datasource, datatype, datadate);

drop index if exists non_sync_datasource;
create index non_sync_datasource on garmin_sync using btree (datasource asc nulls last);
drop index if exists non_sync_datatype;
create index non_sync_datatype on garmin_sync using btree (datatype asc nulls last);
drop index if exists non_sync_datadate;
create index non_sync_datadate on garmin_sync using btree (datadate desc nulls last);

comment on column garmin_sync.id is '自增主键';
comment on column garmin_sync.datasource is '数据来源(garmin/polar/coros)';
comment on column garmin_sync.datatype is '数据类型(activity/sleep/heartrate/stress/spo2/respiration/hrv)';
comment on column garmin_sync.datadate is '数据日期';
comment on column garmin_sync.dataid is '数据唯一标识(如activityid)';
comment on column garmin_sync.syncstatus is '同步状态(1成功0失败)';
comment on column garmin_sync.errmessage is '错误信息';
comment on column garmin_sync.createdat is '创建时间';
comment on column garmin_sync.updatedat is '更新时间';
comment on table garmin_sync is '数据同步记录表';

drop trigger if exists sync_lastupdate on garmin_sync cascade;
create or replace trigger sync_lastupdate
before update on garmin_sync
for each row
execute function lastupdate();