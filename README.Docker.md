# GarminWong Docker 部署

## 构建镜像

```bash
docker build -t garminwong:latest .
```

## 运行

### Docker Compose（推荐）

```bash
# 编辑配置
cp conf/config.yml.simple conf/config.yml
vim conf/config.yml

# 启动
docker compose up -d

# 查看日志
docker compose logs -f garminwong
```

### Docker Run

```bash
docker run -d \
  --name garminwong \
  --restart unless-stopped \
  -m 1G \
  -e TZ=Asia/Shanghai \
  -e PYTHONPATH=/app/src \
  -e PYTHONUNBUFFERED=1 \
  -v ./conf/config.yml:/app/conf/config.yml:ro \
  -v ./garmin_session:/app/garmin_session \
  -v ./logs:/app/logs \
  garminwong:latest
```

## 持久化目录

| 路径 | 说明 |
|------|------|
| `conf/config.yml` | 配置文件（只读挂载） |
| `garmin_session/` | 佳明登录会话缓存，避免频繁登录 |
| `logs/` | 运行日志 |

## 健康检查

容器内置健康检查，每 30 秒检测 `main.py` 进程是否存活：

```bash
docker inspect --format='{{.State.Health.Status}}' garminwong
```

## 本地开发

使用 `DockerfileLocal` 和 `docker-compose-local.yml` 进行本地调试：

```bash
docker compose -f docker-compose-local.yml up --build
```
