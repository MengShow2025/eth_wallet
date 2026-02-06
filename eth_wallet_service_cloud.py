#!/usr/bin/env python3
"""
ETH 钱包生成与地址比对服务 - 云服务器优化版 v3
- 支持环境变量配置
- 支持命令行参数
- 优化内存使用
- 支持 systemd 服务
- 完善的日志记录
- 支持 Gunicorn 生产部署
"""

import os
import sys
import time
import json
import secrets
import pickle
import threading
import glob
import argparse
import logging
import signal
from datetime import datetime
from typing import Optional, Set
from pathlib import Path

# Web 框架
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

# 以太坊
from eth_account import Account

# 数据库
import mysql.connector
from mysql.connector import pooling

# Bloom Filter
from pybloom_live import BloomFilter

# ==================== 配置管理 ====================

class Config:
    """配置类 - 支持环境变量和命令行参数"""

    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'sh-cynosdbmysql-grp-g1mnllo4.sql.tencentcdb.com')
    DB_PORT = int(os.getenv('DB_PORT', '26937'))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'RMuxA3kh')
    DB_NAME = os.getenv('DB_NAME', 'token')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))

    # 数据目录配置
    DATA_DIR = os.getenv('DATA_DIR', './data/databases32G')
    TEMPLATE_DIR = os.getenv('TEMPLATE_DIR', './crypto-wallet-generator')

    # 数据源配置
    USE_DATABASE = os.getenv('USE_DATABASE', 'true').lower() == 'true'

    # 服务配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5001'))
    NUM_WORKERS = int(os.getenv('NUM_WORKERS', '8'))

    # Bloom Filter 配置
    BLOOM_ERROR_RATE = float(os.getenv('BLOOM_ERROR_RATE', '0.000001'))

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'eth_wallet_service.log')

    @classmethod
    def get_db_config(cls):
        """获取数据库配置"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME,
            'pool_name': 'eth_pool',
            'pool_size': cls.DB_POOL_SIZE
        }

# ==================== 日志配置 ====================

def setup_logging(log_level='INFO', log_file=None):
    """配置日志"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

    return logging.getLogger(__name__)

logger = setup_logging(Config.LOG_LEVEL, Config.LOG_FILE)

# ==================== 全局变量 ====================

app = Flask(__name__,
            template_folder=Config.TEMPLATE_DIR,
            static_folder=Config.TEMPLATE_DIR)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

bloom_filter: Optional[BloomFilter] = None
address_set: Set[str] = set()
db_pool = None
is_running = False
shutdown_flag = False

stats = {
    'generated': 0,
    'matched': 0,
    'start_time': None,
    'speed': 0,
    'load_time': 0,
    'total_addresses': 0
}

# ==================== 数据库操作 ====================

def create_tables():
    """创建数据库表"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eth_wallet (
                id              BIGINT AUTO_INCREMENT PRIMARY KEY,
                address         VARCHAR(42) NOT NULL UNIQUE,
                private_key     VARCHAR(66) NOT NULL,
                balance         DECIMAL(36,18) DEFAULT 0,
                matched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_eth_wallet_address (address)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✅ eth_wallet 表已就绪")
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        raise

# ==================== Bloom Filter 加载 ====================

def load_bloom_filter_from_database():
    """从数据库加载地址到 Bloom Filter"""
    global bloom_filter, address_set, stats

    logger.info("📥 正在从数据库加载地址...")
    start_time = time.time()

    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()

        # 先获取总数
        logger.info("   统计地址总数...")
        cursor.execute("SELECT COUNT(*) FROM eth_active_addresses")
        total_addresses = cursor.fetchone()[0]
        logger.info(f"   找到 {total_addresses:,} 个地址")

        if total_addresses == 0:
            logger.warning("⚠️  数据库中没有地址数据")
            cursor.close()
            conn.close()
            return

        # 创建 Bloom Filter
        logger.info("   创建 Bloom Filter...")
        bloom_filter = BloomFilter(
            capacity=total_addresses + 1000000,
            error_rate=Config.BLOOM_ERROR_RATE
        )

        # 分批加载地址
        logger.info("   加载地址到 Bloom Filter...")
        batch_size = 100000
        loaded = 0

        cursor.execute("SELECT address FROM eth_active_addresses")

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break

            for row in rows:
                addr = row[0]
                # 统一格式：添加 0x 前缀并转小写
                full_addr = f"0x{addr.lower()}" if not addr.startswith('0x') else addr.lower()
                bloom_filter.add(full_addr)
                address_set.add(full_addr)
                loaded += 1

            if loaded % 1000000 == 0:
                logger.info(f"         已加载: {loaded:,} / {total_addresses:,}")

        cursor.close()
        conn.close()

        elapsed = time.time() - start_time
        memory_mb = bloom_filter.num_bits / 8 / 1024 / 1024

        logger.info(f"\n✅ 加载完成!")
        logger.info(f"   耗时: {elapsed:.1f} 秒")
        logger.info(f"   地址数: {len(address_set):,}")
        logger.info(f"   Bloom Filter 内存: ~{memory_mb:.1f} MB")

        stats['load_time'] = elapsed
        stats['total_addresses'] = len(address_set)

    except Exception as e:
        logger.error(f"❌ 从数据库加载失败: {e}")
        raise

def load_bloom_filter_from_pickle():
    """从 pickle 文件加载地址到 Bloom Filter"""
    global bloom_filter, address_set, stats

    logger.info("📥 正在从本地 pickle 文件加载...")
    start_time = time.time()

    # 检查数据目录
    data_dir = Path(Config.DATA_DIR)
    if not data_dir.exists():
        logger.error(f"❌ 数据目录不存在: {data_dir}")
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    # 获取所有 pickle 文件
    pkl_files = sorted(data_dir.glob('data*.pkl'))
    if not pkl_files:
        logger.error(f"❌ 未找到 pickle 文件: {data_dir}/data*.pkl")
        raise FileNotFoundError(f"未找到 pickle 文件")

    logger.info(f"   找到 {len(pkl_files)} 个数据文件")

    # 加载所有地址
    total_addresses = 0
    all_addresses = []

    for i, pkl_file in enumerate(pkl_files, 1):
        logger.info(f"   [{i}/{len(pkl_files)}] 加载: {pkl_file.name}")
        try:
            with open(pkl_file, 'rb') as f:
                addresses = pickle.load(f)
                all_addresses.append(addresses)
                total_addresses += len(addresses)
            logger.info(f"         包含 {len(addresses):,} 个地址")
        except Exception as e:
            logger.error(f"❌ 加载文件失败 {pkl_file}: {e}")
            raise

    logger.info(f"\n   总地址数: {total_addresses:,}")

    # 创建 Bloom Filter
    logger.info("   创建 Bloom Filter...")
    bloom_filter = BloomFilter(
        capacity=total_addresses + 1000000,
        error_rate=Config.BLOOM_ERROR_RATE
    )

    # 批量添加到 Bloom Filter
    logger.info("   添加地址到 Bloom Filter...")
    loaded = 0

    for addresses in all_addresses:
        for addr in addresses:
            # 统一格式：添加 0x 前缀并转小写
            full_addr = f"0x{addr.lower()}" if not addr.startswith('0x') else addr.lower()
            bloom_filter.add(full_addr)
            address_set.add(full_addr)
            loaded += 1

            if loaded % 10000000 == 0:
                logger.info(f"         已加载: {loaded:,} / {total_addresses:,}")

    elapsed = time.time() - start_time
    memory_mb = bloom_filter.num_bits / 8 / 1024 / 1024

    logger.info(f"\n✅ 加载完成!")
    logger.info(f"   耗时: {elapsed:.1f} 秒")
    logger.info(f"   地址数: {len(address_set):,}")
    logger.info(f"   Bloom Filter 内存: ~{memory_mb:.1f} MB")

    stats['load_time'] = elapsed
    stats['total_addresses'] = len(address_set)

# ==================== 钱包生成 ====================

def generate_eth_wallet():
    """生成 ETH 钱包"""
    private_key = secrets.token_hex(32)
    private_key_bytes = bytes.fromhex(private_key)
    account = Account.from_key(private_key_bytes)

    return {
        'address': account.address.lower(),
        'private_key': '0x' + private_key
    }

def check_and_save_match(wallet: dict) -> bool:
    """检查地址是否匹配并保存"""
    global stats

    address = wallet['address']

    # Bloom Filter 快速检查
    if address not in bloom_filter:
        return False

    # 精确验证
    if address not in address_set:
        return False  # 假阳性

    # 真正匹配！保存到数据库
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT IGNORE INTO eth_wallet (address, private_key)
            VALUES (%s, %s)
        """, (address, wallet['private_key']))
        conn.commit()

        cursor.close()
        conn.close()

        stats['matched'] += 1
        logger.info(f"🎉 发现匹配! {address}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存失败: {e}")
        return False

def wallet_generator_worker():
    """钱包生成工作线程"""
    global stats, is_running

    while is_running and not shutdown_flag:
        try:
            wallet = generate_eth_wallet()
            stats['generated'] += 1

            if check_and_save_match(wallet):
                # 发现匹配！通知前端
                match_data = {
                    'address': wallet['address'],
                    'private_key': wallet['private_key'],
                    'matched_at': datetime.now().isoformat(),
                    'total_matched': stats['matched']
                }
                socketio.emit('wallet_matched', match_data)
        except Exception as e:
            logger.error(f"❌ 生成钱包错误: {e}")
            time.sleep(0.1)

def start_generation():
    """启动钱包生成"""
    global is_running, stats

    if is_running:
        return False

    is_running = True
    stats['generated'] = 0
    stats['matched'] = 0
    stats['start_time'] = time.time()
    stats['speed'] = 0

    # 启动多个工作线程
    num_workers = Config.NUM_WORKERS
    for _ in range(num_workers):
        thread = threading.Thread(target=wallet_generator_worker, daemon=True)
        thread.start()

    # 启动速度计算线程
    def speed_calculator():
        last_count = 0
        while is_running and not shutdown_flag:
            time.sleep(1)
            current = stats['generated']
            stats['speed'] = current - last_count
            last_count = current

    threading.Thread(target=speed_calculator, daemon=True).start()

    logger.info(f"🚀 已启动 {num_workers} 个生成线程")
    return True

def stop_generation():
    """停止钱包生成"""
    global is_running
    is_running = False
    logger.info("⏹️ 生成已停止")

# ==================== Flask 路由 ====================

@app.route('/')
def index():
    return render_template('wallet_generator.html')

@app.route('/api/stats')
def get_stats():
    elapsed = time.time() - stats['start_time'] if stats['start_time'] else 0
    return jsonify({
        'generated': stats['generated'],
        'matched': stats['matched'],
        'speed': stats['speed'],
        'elapsed': int(elapsed),
        'is_running': is_running,
        'total_addresses': stats['total_addresses'],
        'load_time': stats['load_time']
    })

@app.route('/api/matches')
def get_matches():
    """获取所有匹配的钱包"""
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT address, private_key, matched_at
            FROM eth_wallet
            ORDER BY matched_at DESC
            LIMIT 100
        """)

        matches = cursor.fetchall()
        cursor.close()
        conn.close()

        for m in matches:
            if m['matched_at']:
                m['matched_at'] = m['matched_at'].isoformat()

        return jsonify(matches)
    except Exception as e:
        logger.error(f"❌ 获取匹配记录失败: {e}")
        return jsonify([])

@app.route('/health')
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'bloom_filter_loaded': bloom_filter is not None,
        'total_addresses': len(address_set),
        'is_running': is_running
    })

# ==================== WebSocket 事件 ====================

@socketio.on('connect')
def handle_connect():
    logger.info('客户端已连接')
    emit('stats_update', {**stats, 'total_addresses': len(address_set)})

@socketio.on('start')
def handle_start():
    if start_generation():
        emit('status', {'message': '生成已启动', 'is_running': True})
    else:
        emit('status', {'message': '已在运行中', 'is_running': True})

@socketio.on('stop')
def handle_stop():
    stop_generation()
    emit('status', {'message': '生成已停止', 'is_running': False})

def stats_broadcaster():
    """定期广播统计数据"""
    while not shutdown_flag:
        if is_running:
            socketio.emit('stats_update', {
                'generated': stats['generated'],
                'matched': stats['matched'],
                'speed': stats['speed'],
                'is_running': is_running,
                'total_addresses': stats['total_addresses']
            })
        time.sleep(1)

# ==================== 信号处理 ====================

def signal_handler(signum, frame):
    """处理退出信号"""
    global shutdown_flag
    logger.info(f"\n收到退出信号 {signum}，正在关闭服务...")
    shutdown_flag = True
    stop_generation()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== 主函数 ====================

def main():
    global db_pool

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='ETH 钱包生成与比对服务')
    parser.add_argument('--host', default=Config.HOST, help='监听地址')
    parser.add_argument('--port', type=int, default=Config.PORT, help='监听端口')
    parser.add_argument('--workers', type=int, default=Config.NUM_WORKERS, help='工作线程数')
    parser.add_argument('--data-dir', default=Config.DATA_DIR, help='数据目录')
    parser.add_argument('--log-level', default=Config.LOG_LEVEL, help='日志级别')
    parser.add_argument('--auto-start', action='store_true', help='自动开始生成')
    args = parser.parse_args()

    # 更新配置
    Config.HOST = args.host
    Config.PORT = args.port
    Config.NUM_WORKERS = args.workers
    Config.DATA_DIR = args.data_dir
    Config.LOG_LEVEL = args.log_level

    # 重新配置日志
    global logger
    logger = setup_logging(Config.LOG_LEVEL, Config.LOG_FILE)

    logger.info("=" * 60)
    logger.info("🚀 ETH 钱包生成与比对服务 v3 (云服务器优化版)")
    logger.info("=" * 60)
    logger.info(f"配置信息:")
    logger.info(f"  - 数据目录: {Config.DATA_DIR}")
    logger.info(f"  - 监听地址: {Config.HOST}:{Config.PORT}")
    logger.info(f"  - 工作线程: {Config.NUM_WORKERS}")
    logger.info(f"  - 日志级别: {Config.LOG_LEVEL}")
    logger.info("=" * 60)

    try:
        # 初始化数据库连接池
        logger.info("\n📡 初始化数据库连接池...")
        db_pool = pooling.MySQLConnectionPool(**Config.get_db_config())
        logger.info("✅ 数据库连接池已就绪")

        # 创建表
        create_tables()

        # 根据配置选择数据源
        if Config.USE_DATABASE:
            logger.info("\n📊 数据源: 数据库")
            load_bloom_filter_from_database()
        else:
            logger.info("\n📊 数据源: 本地 pickle 文件")
            load_bloom_filter_from_pickle()

        # 启动统计广播线程
        broadcaster = threading.Thread(target=stats_broadcaster, daemon=True)
        broadcaster.start()

        # 自动开始生成
        if args.auto_start:
            logger.info("\n🚀 自动启动钱包生成...")
            start_generation()

        # 启动 Flask 服务
        logger.info(f"\n🌐 启动 Web 服务...")
        logger.info(f"   访问: http://{Config.HOST}:{Config.PORT}")
        logger.info(f"   健康检查: http://{Config.HOST}:{Config.PORT}/health")
        logger.info("=" * 60)

        socketio.run(
            app,
            host=Config.HOST,
            port=Config.PORT,
            debug=False,
            allow_unsafe_werkzeug=True
        )

    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
