# 数据目录

此目录用于存放地址数据文件。

## 目录结构

```
data/
├── databases32G/          # Pickle 数据文件目录
│   └── data*.pkl         # 地址数据文件
└── README.md             # 本说明文件
```

## 数据文件说明

- 数据文件不包含在 Git 仓库中（文件过大）
- 请将你的 `.pkl` 数据文件放在 `databases32G/` 目录下
- 或者配置 `USE_DATABASE=true` 从数据库加载地址

## 使用数据库模式

如果使用数据库加载地址，不需要本地数据文件：

1. 在 `eth_wallet_service.env` 中设置 `USE_DATABASE=true`
2. 配置数据库连接信息
3. 确保数据库中有 `eth_active_addresses` 表
