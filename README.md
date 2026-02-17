# GarminWong

佳明 Connect 健康数据自动采集工具，定时获取活动、心率、睡眠、压力、血氧、呼吸、HRV 等数据并存储至 PostgreSQL。

## 功能

- 🏃 **活动数据** — 汇总信息 + GPS 轨迹点
- ❤️ **心率** — 每日汇总 + 时序明细
- 💤 **睡眠** — 每日汇总 + 睡眠阶段（深睡/浅睡/REM/清醒）
- 😰 **压力** — 每日汇总 + 时序明细
- 🩸 **血氧** — 每日汇总 + 时序明细
- 🌬️ **呼吸** — 每日汇总 + 时序明细
- 💓 **HRV** — 每日汇总

## 技术栈

- Python 3.13
- [garth](https://github.com/matin/garth) — Garmin Connect API
- PostgreSQL + psycopg2
- schedule — 定时任务
- Docker + Supervisor — 部署运行

## 项目结构

```
├── conf/config.yml          # 配置文件（数据库 + 佳明账号）
├── sql/datastruct.sql       # 数据库建表脚本
├── src/
│   ├── main.py              # 主程序入口
│   ├── config.py            # 配置加载
│   ├── garth_utils.py       # 佳明登录封装
│   ├── garmin_data_collector.py  # 数据采集
│   └── database.py          # 数据库操作
├── docker/supervisord.conf  # Supervisor 配置
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 快速开始

### 1. 配置

```bash
cp conf/config.yml.simple conf/config.yml
# 编辑 config.yml 填入数据库和佳明账号信息
```

### 2. 建表

```bash
psql -h <host> -U <user> -d <db> -f sql/datastruct.sql
```

### 3. 运行

```bash
# 本地运行
pip install -r requirements.txt
python src/main.py

# Docker 运行
docker compose up -d
```

## 配置说明

```yaml
database:
  host: localhost
  port: 5432
  db: dbname
  user: username
  password: password

garmin:
  email: your@email.com
  password: your_password
  domain: garmin.cn          # 国际版用 garmin.com
  save_path: ./garmin_session
  schedule: "08:00"          # 每日定时采集时间
  # init_days: 30            # 首次回溯天数，不设置则回溯到 2016-06-01
```

## 采集策略

- **首次运行**：按 `init_days` 配置回溯，未设置则从 2016-06-01 至今全量采集
- **每日定时**：只获取前 1 天数据，已同步的自动跳过
- **活动去重**：按 `activityId` 检查，已存在的活动跳过详情获取
- **健康数据去重**：按 `(datasource, datatype, datadate)` 检查同步记录

## License

[MIT](LICENSE)
