# ETH 钱包生成服务 - 云服务器部署指南

## 📋 目录

1. [系统要求](#系统要求)
2. [快速部署](#快速部署)
3. [手动部署](#手动部署)
4. [配置说明](#配置说明)
5. [运行管理](#运行管理)
6. [性能优化](#性能优化)
7. [故障排查](#故障排查)

---

## 系统要求

### 硬件要求
- **CPU**: 4核以上（推荐 8核+）
- **内存**: 4GB 以上（推荐 8GB+）
- **磁盘**: 20GB 以上（数据文件约 8GB）
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **Python**: 3.8+
- **MySQL**: 5.7+ 或 MariaDB 10.3+

---

## 快速部署

### 1. 下载部署文件

将以下文件上传到服务器：
```
eth_wallet_service_cloud.py    # 主程序
eth_wallet_service.env          # 配置文件模板
eth_wallet_service.service      # systemd 服务文件
deploy.sh                       # 部署脚本
```

### 2. 运行部署脚本

```bash
# 赋予执行权限
chmod +x deploy.sh

# 运行部署脚本
sudo bash deploy.sh
```

### 3. 上传数据文件

```bash
# 上传 pickle 数据文件到服务器
scp -r data/databases32G/*.pkl user@server:/data/eth_addresses/

# 上传前端文件
scp -r crypto-wallet-generator/* user@server:/opt/eth_wallet_service/frontend/
```

### 4. 配置环境变量

```bash
# 编辑配置文件
sudo vim /opt/eth_wallet_service/.env

# 修改以下配置：
# - 数据库连接信息
# - 数据目录路径
# - 工作线程数
```

### 5. 启动服务

```bash
# 启动服务
sudo systemctl start eth-wallet-service

# 查看状态
sudo systemctl status eth-wallet-service

# 查看日志
sudo journalctl -u eth-wallet-service -f
```

---

## 手动部署

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install -y python3 python3-pip
```

### 2. 安装 Python 依赖

```bash
sudo pip3 install flask flask-socketio eth-account mysql-connector-python pybloom-live
```

### 3. 创建目录结构

```bash
sudo mkdir -p /opt/eth_wallet_service
sudo mkdir -p /data/eth_addresses
sudo mkdir -p /opt/eth_wallet_service/frontend
```

### 4. 上传文件

```bash
# 上传主程序
scp eth_wallet_service_cloud.py user@server:/opt/eth_wallet_service/

# 上传数据文件
scp -r data/databases32G/*.pkl user@server:/data/eth_addresses/

# 上传前端文件
scp -r crypto-wallet-generator/* user@server:/opt/eth_wallet_service/frontend/
```

### 5. 配置环境变量

```bash
# 复制配置文件
cp eth_wallet_service.env /opt/eth_wallet_service/.env

# 编辑配置
vim /opt/eth_wallet_service/.env
```

### 6. 配置 systemd 服务

```bash
# 复制服务文件
sudo cp eth_wallet_service.service /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable eth-wallet-service
```

### 7. 启动服务

```bash
sudo systemctl start eth-wallet-service
```

---

## 配置说明

### 环境变量配置 (.env)

```bash
# 数据库配置
DB_HOST=your-db-host.com
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=token

# 数据目录
DATA_DIR=/data/eth_addresses
TEMPLATE_DIR=/opt/eth_wallet_service/frontend

# 服务配置
HOST=0.0.0.0
PORT=5001
NUM_WORKERS=16  # 根据 CPU 核心数调整

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/eth_wallet_service.log
```

### 命令行参数

```bash
python3 eth_wallet_service_cloud.py --help

选项:
  --host HOST           监听地址 (默认: 0.0.0.0)
  --port PORT           监听端口 (默认: 5001)
  --workers WORKERS     工作线程数 (默认: 8)
  --data-dir DATA_DIR   数据目录路径
  --log-level LEVEL     日志级别 (DEBUG/INFO/WARNING/ERROR)
  --auto-start          自动开始生成钱包
```

---

## 运行管理

### systemd 服务管理

```bash
# 启动服务
sudo systemctl start eth-wallet-service

# 停止服务
sudo systemctl stop eth-wallet-service

# 重启服务
sudo systemctl restart eth-wallet-service

# 查看状态
sudo systemctl status eth-wallet-service

# 开机自启
sudo systemctl enable eth-wallet-service

# 禁用自启
sudo systemctl disable eth-wallet-service
```

### 日志查看

```bash
# 查看 systemd 日志
sudo journalctl -u eth-wallet-service -f

# 查看应用日志
sudo tail -f /var/log/eth_wallet_service.log

# 查看最近 100 行日志
sudo journalctl -u eth-wallet-service -n 100
```

### 手动运行（调试模式）

```bash
# 进入目录
cd /opt/eth_wallet_service

# 手动运行
python3 eth_wallet_service_cloud.py \
    --data-dir /data/eth_addresses \
    --workers 16 \
    --auto-start \
    --log-level DEBUG
```

---

## 性能优化

### 1. 工作线程数优化

```bash
# 根据 CPU 核心数设置
# 推荐: CPU 核心数 × 2

# 查看 CPU 核心数
nproc

# 设置工作线程数
NUM_WORKERS=16  # 8核 CPU × 2
```

### 2. 内存优化

```bash
# 监控内存使用
free -h
htop

# 如果内存不足，可以：
# 1. 减少工作线程数
# 2. 增加 swap 空间
# 3. 升级服务器内存
```

### 3. 数据库连接池优化

```bash
# 调整连接池大小
DB_POOL_SIZE=10  # 根据并发需求调整
```

### 4. 使用 Gunicorn 部署（生产环境）

```bash
# 安装 Gunicorn
pip3 install gunicorn eventlet

# 使用 Gunicorn 运行
gunicorn --worker-class eventlet -w 4 \
    --bind 0.0.0.0:5001 \
    eth_wallet_service_cloud:app
```

---

## 故障排查

### 1. 服务无法启动

```bash
# 查看详细错误信息
sudo journalctl -u eth-wallet-service -xe

# 检查配置文件
cat /opt/eth_wallet_service/.env

# 检查文件权限
ls -la /opt/eth_wallet_service/
ls -la /data/eth_addresses/
```

### 2. 数据加载失败

```bash
# 检查数据文件是否存在
ls -lh /data/eth_addresses/*.pkl

# 检查文件权限
sudo chown -R www-data:www-data /data/eth_addresses/

# 手动测试加载
python3 -c "import pickle; pickle.load(open('/data/eth_addresses/data0.pkl', 'rb'))"
```

### 3. 数据库连接失败

```bash
# 测试数据库连接
mysql -h DB_HOST -P DB_PORT -u DB_USER -p

# 检查防火墙
sudo ufw status
sudo iptables -L

# 检查数据库配置
cat /opt/eth_wallet_service/.env | grep DB_
```

### 4. 内存不足

```bash
# 查看内存使用
free -h

# 查看进程内存
ps aux | grep eth_wallet

# 减少工作线程数
# 编辑 .env 文件
NUM_WORKERS=4
```

### 5. 端口被占用

```bash
# 查看端口占用
sudo lsof -i :5001
sudo netstat -tulpn | grep 5001

# 修改端口
# 编辑 .env 文件
PORT=5002
```

---

## API 接口

### 健康检查
```bash
curl http://localhost:5001/health
```

### 获取统计信息
```bash
curl http://localhost:5001/api/stats
```

### 获取匹配记录
```bash
curl http://localhost:5001/api/matches
```

---

## 安全建议

1. **修改默认端口**: 不要使用默认的 5001 端口
2. **配置防火墙**: 只开放必要的端口
3. **使用 HTTPS**: 配置 Nginx 反向代理 + SSL 证书
4. **数据库安全**: 使用强密码，限制访问 IP
5. **定期备份**: 备份数据库和匹配记录
6. **监控日志**: 定期检查异常日志

---

## 监控和告警

### 使用 Prometheus + Grafana

```bash
# 添加监控指标接口
@app.route('/metrics')
def metrics():
    return jsonify({
        'generated_total': stats['generated'],
        'matched_total': stats['matched'],
        'speed_per_second': stats['speed'],
        'is_running': is_running
    })
```

### 使用 Supervisor 管理

```bash
# 安装 Supervisor
sudo apt-get install supervisor

# 配置文件
sudo vim /etc/supervisor/conf.d/eth-wallet.conf
```

---

## 联系支持

如有问题，请查看日志文件或联系技术支持。
