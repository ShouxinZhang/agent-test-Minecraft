#!/bin/bash
set -euo pipefail

# 启动 Minecraft 研究服务器 (PaperMC 1.20.4, 离线模式)
cd "$(dirname "$0")/../server"
echo "=== 启动 Minecraft Agent 研究服务器 ==="
echo "  版本: PaperMC 1.20.4"
echo "  模式: 离线 (无需登录)"
echo "  端口: 25565"
echo "=================================="
java -Xmx4G -Xms2G -jar paper-1.20.4.jar --nogui
