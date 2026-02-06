#!/bin/bash
#
# ETH 钱包生成服务 - 快速启动脚本
# 用于本地开发和测试
#

set -e

# 加载环境变量
if [ -f "eth_wallet_service.env" ]; then
    echo "📋 加载环境变量配置..."
    set -a  # 自动导出所有变量
    source eth_wallet_service.env
    set +a  # 关闭自动导出
    echo "✅ 环境变量已加载"
fi

echo "=========================================="
echo "ETH 钱包生成服务 - 快速启动"
echo "=========================================="

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查 Python 依赖..."
MISSING_DEPS=()

for pkg in flask flask_socketio eth_account mysql.connector pybloom_live; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING_DEPS+=($pkg)
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "❌ 缺少以下依赖: ${MISSING_DEPS[@]}"
    echo ""
    read -p "是否自动安装? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在安装依赖..."
        pip3 install --break-system-packages flask flask-socketio eth-account mysql-connector-python pybloom-live
    else
        echo "请手动安装依赖后再运行"
        exit 1
    fi
fi

echo "✅ 所有依赖已安装"

# 检查是否使用数据库
USE_DB="${USE_DATABASE:-true}"
if [ "$USE_DB" = "true" ]; then
    echo ""
    echo "📊 数据源: 数据库 (eth_active_addresses)"
else
    # 检查数据文件
    echo ""
    echo "📁 检查数据文件..."
    # 使用环境变量，如果未设置则使用默认值
    DATA_DIR="${DATA_DIR:-./data/databases32G}"

    if [ ! -d "$DATA_DIR" ]; then
        echo "❌ 数据目录不存在: $DATA_DIR"
        echo "   请确保数据文件位于正确位置"
        exit 1
    fi

    PKL_COUNT=$(ls -1 $DATA_DIR/*.pkl 2>/dev/null | wc -l)
    if [ $PKL_COUNT -eq 0 ]; then
        echo "❌ 未找到 pickle 数据文件"
        exit 1
    fi

    echo "✅ 找到 $PKL_COUNT 个数据文件"
fi

# 检查前端文件
echo ""
echo "🌐 检查前端文件..."
# 使用环境变量，如果未设置则使用默认值
TEMPLATE_DIR="${TEMPLATE_DIR:-./crypto-wallet-generator}"

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "⚠️  前端目录不存在: $TEMPLATE_DIR"
    echo "   Web 界面可能无法访问"
fi

# 启动服务
echo ""
echo "=========================================="
echo "🚀 启动服务..."
echo "=========================================="
echo ""
echo "配置信息:"
echo "  - 数据目录: $DATA_DIR"
echo "  - 前端目录: $TEMPLATE_DIR"
echo "  - 监听地址: 0.0.0.0:5001"
echo "  - 工作线程: 8"
echo ""
echo "访问地址: http://localhost:5001"
echo "健康检查: http://localhost:5001/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 运行服务
python3 eth_wallet_service_cloud.py \
    --data-dir "$DATA_DIR" \
    --workers 8 \
    --log-level INFO

echo ""
echo "服务已停止"
