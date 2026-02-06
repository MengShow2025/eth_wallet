# ETH 钱包生成服务 - 云服务器优化版

## 📦 文件清单

已为你创建以下文件，全部保存在桌面：

### 核心文件
1. **eth_wallet_service_cloud.py** - 优化后的主程序
2. **eth_wallet_service.env** - 环境变量配置模板
3. **eth_wallet_service.service** - systemd 服务配置
4. **deploy.sh** - 自动部署脚本
5. **start.sh** - 本地快速启动脚本
6. **DEPLOYMENT_GUIDE.md** - 完整部署指南

---

## 🚀 主要优化内容

### 1. 配置管理优化
- ✅ 支持环境变量配置（.env 文件）
- ✅ 支持命令行参数
- ✅ 配置与代码分离
- ✅ 敏感信息可通过环境变量管理

### 2. 云服务器适配
- ✅ 支持 systemd 服务管理
- ✅ 支持开机自启动
- ✅ 支持优雅关闭（信号处理）
- ✅ 完善的日志记录
- ✅ 健康检查接口

### 3. 性能优化
- ✅ 可配置工作线程数
- ✅ 数据库连接池优化
- ✅ 内存使用优化
- ✅ 支持 Gunicorn 生产部署

### 4. 运维友好
- ✅ 详细的日志输出
- ✅ 健康检查接口 `/health`
- ✅ 统计信息接口 `/api/stats`
- ✅ 自动重启机制
- ✅ 资源限制配置

---

## 📖 快速开始

### 本地测试

```bash
# 1. 进入桌面目录
cd ~/Desktop

# 2. 赋予执行权限
chmod +x start.sh

# 3. 运行启动脚本
./start.sh
```

### 云服务器部署

```bash
# 1. 上传所有文件到服务器
scp eth_wallet_service_cloud.py user@server:/tmp/
scp eth_wallet_service.env user@server:/tmp/
scp eth_wallet_service.service user@server:/tmp/
scp deploy.sh user@server:/tmp/

# 2. SSH 登录服务器
ssh user@server

# 3. 运行部署脚本
cd /tmp
chmod +x deploy.sh
sudo bash deploy.sh

# 4. 按照提示完成部署
```

详细部署步骤请查看 **DEPLOYMENT_GUIDE.md**

---

## 🔧 配置说明

### 环境变量配置 (eth_wallet_service.env)

```bash
# 数据库配置
DB_HOST=your-db-host.com
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=token

# 数据目录（重要！）
DATA_DIR=/data/eth_addresses          # pickle 文件目录
TEMPLATE_DIR=/opt/eth_wallet_service/frontend  # 前端文件目录

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
python3 eth_wallet_service_cloud.py \
    --host 0.0.0.0 \
    --port 5001 \
    --workers 16 \
    --data-dir /data/eth_addresses \
    --log-level INFO \
    --auto-start  # 自动开始生成钱包
```

---

## 📊 新增功能

### 1. 健康检查接口

```bash
curl http://localhost:5001/health

# 返回示例:
{
  "status": "healthy",
  "bloom_filter_loaded": true,
  "total_addresses": 180763814,
  "is_running": true
}
```

### 2. 统计信息接口

```bash
curl http://localhost:5001/api/stats

# 返回示例:
{
  "generated": 1234567,
  "matched": 0,
  "speed": 12345,
  "elapsed": 3600,
  "is_running": true,
  "total_addresses": 180763814,
  "load_time": 1644.0
}
```

### 3. 自动启动选项

```bash
# 服务启动后自动开始生成钱包
python3 eth_wallet_service_cloud.py --auto-start
```

---

## 🛠️ 运维管理

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

# 查看日志
sudo journalctl -u eth-wallet-service -f
```

### 日志查看

```bash
# 查看应用日志
tail -f /var/log/eth_wallet_service.log

# 查看 systemd 日志
sudo journalctl -u eth-wallet-service -n 100
```

---

## 📈 性能建议

### CPU 和线程配置

```bash
# 查看 CPU 核心数
nproc

# 推荐配置
# 工作线程数 = CPU 核心数 × 2
# 例如: 8核 CPU → NUM_WORKERS=16
```

### 内存要求

- **最小**: 2GB（基础运行）
- **推荐**: 4GB+（稳定运行）
- **最佳**: 8GB+（高性能）

### 数据库连接池

```bash
# 根据并发需求调整
DB_POOL_SIZE=10  # 默认 5，可根据需要增加
```

---

## 🔒 安全建议

1. **修改默认密码**: 更改数据库密码
2. **配置防火墙**: 只开放必要端口
3. **使用 HTTPS**: 配置 Nginx 反向代理
4. **限制访问**: 使用 IP 白名单
5. **定期备份**: 备份数据库和配置文件

---

## 🐛 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   sudo journalctl -u eth-wallet-service -xe
   ```

2. **数据加载失败**
   ```bash
   ls -lh /data/eth_addresses/*.pkl
   ```

3. **数据库连接失败**
   ```bash
   mysql -h DB_HOST -u DB_USER -p
   ```

4. **端口被占用**
   ```bash
   sudo lsof -i :5001
   ```

详细故障排查请查看 **DEPLOYMENT_GUIDE.md**

---

## 📝 与原版本的区别

| 功能 | 原版本 | 优化版 |
|------|--------|--------|
| 配置管理 | 硬编码 | 环境变量 + 命令行参数 |
| 路径配置 | 绝对路径 | 可配置路径 |
| 日志记录 | print 输出 | logging 模块 |
| 服务管理 | 手动运行 | systemd 服务 |
| 健康检查 | 无 | /health 接口 |
| 信号处理 | 无 | 优雅关闭 |
| 自动启动 | 无 | --auto-start 参数 |
| 部署脚本 | 无 | 完整部署工具 |

---

## 📚 相关文档

- **DEPLOYMENT_GUIDE.md** - 完整部署指南
- **eth_wallet_service.env** - 配置文件模板
- **eth_wallet_service.service** - systemd 服务配置

---

## 💡 使用建议

### 本地开发
使用 `start.sh` 快速启动，方便调试和测试。

### 云服务器生产环境
1. 使用 `deploy.sh` 自动部署
2. 配置 systemd 服务
3. 启用开机自启动
4. 配置日志轮转
5. 设置监控告警

---

## 🎯 下一步

1. ✅ 阅读 **DEPLOYMENT_GUIDE.md** 了解详细部署步骤
2. ✅ 修改 **eth_wallet_service.env** 配置文件
3. ✅ 上传数据文件到服务器
4. ✅ 运行 **deploy.sh** 完成部署
5. ✅ 启动服务并监控运行状态

---

**祝部署顺利！** 🚀
