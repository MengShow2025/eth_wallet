#!/bin/bash
#
# ETH 钱包生成服务 - 云服务器部署脚本
# 使用方法: sudo bash deploy.sh
#

set -e

echo "=========================================="
echo "ETH 钱包生成服务 - 云服务器部署"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 权限运行此脚本"
    echo "   sudo bash deploy.sh"
    exit 1
fi

# 配置变量
SERVICE_NAME="eth-wallet-service"
INSTALL_DIR="/opt/eth_wallet_service"
DATA_DIR="/data/eth_addresses"
LOG_DIR="/var/log"
SERVICE_USER="www-data"

echo ""
echo "📦 1. 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx supervisor

echo ""
echo "📁 2. 创建目录结构..."
mkdir -p $INSTALL_DIR
mkdir -p $DATA_DIR
mkdir -p $INSTALL_DIR/frontend
mkdir -p $LOG_DIR

echo ""
echo "🐍 3. 安装 Python 依赖..."
pip3 install --break-system-packages flask flask-socketio eth-account mysql-connector-python pybloom-live gunicorn eventlet

echo ""
echo "📋 4. 复制服务文件..."
echo "   请手动执行以下步骤:"
echo "   1) 上传 eth_wallet_service_cloud.py 到 $INSTALL_DIR/"
echo "   2) 上传 data/databases32G/*.pkl 到 $DATA_DIR/"
echo "   3) 上传 crypto-wallet-generator/* 到 $INSTALL_DIR/frontend/"
echo "   4) 复制 .env 配置文件到 $INSTALL_DIR/.env"
echo ""
read -p "   完成后按回车继续..."

echo ""
echo "🔐 5. 设置权限..."
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_USER $DATA_DIR
chmod +x $INSTALL_DIR/eth_wallet_service_cloud.py

echo ""
echo "⚙️  6. 配置 systemd 服务..."
cp eth_wallet_service.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo ""
echo "🔥 7. 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 5001/tcp
    echo "   已开放端口 5001"
fi

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📝 后续操作:"
echo ""
echo "1. 编辑配置文件:"
echo "   vim $INSTALL_DIR/.env"
echo ""
echo "2. 启动服务:"
echo "   systemctl start $SERVICE_NAME"
echo ""
echo "3. 查看状态:"
echo "   systemctl status $SERVICE_NAME"
echo ""
echo "4. 查看日志:"
echo "   journalctl -u $SERVICE_NAME -f"
echo "   tail -f $LOG_DIR/eth_wallet_service.log"
echo ""
echo "5. 停止服务:"
echo "   systemctl stop $SERVICE_NAME"
echo ""
echo "6. 重启服务:"
echo "   systemctl restart $SERVICE_NAME"
echo ""
echo "=========================================="
