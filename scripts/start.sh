#!/bin/bash
set -e

echo "======================================"
echo "  AutoOps 一键启动脚本"
echo "======================================"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] 未检测到 Docker，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[ERROR] 未检测到 Docker Compose，请先安装"
    exit 1
fi

# 复制环境变量文件
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "[INFO] 已创建 backend/.env，请根据需要修改配置"
fi

# 启动服务
echo "[INFO] 启动所有服务..."
docker compose up -d --build

echo ""
echo "======================================"
echo "  AutoOps 启动完成！"
echo "======================================"
echo ""
echo "  前端地址:      http://localhost"
echo "  后端 API:      http://localhost:8000/docs"
echo "  Grafana:       http://localhost:3000  (admin/admin123)"
echo "  Prometheus:    http://localhost:9090"
echo "  Alertmanager:  http://localhost:9093"
echo ""
echo "  默认账号: admin / admin123"
echo "======================================"
