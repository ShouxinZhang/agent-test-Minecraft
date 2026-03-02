#!/bin/bash
set -euo pipefail

# 启动交互式 Agent Bot
cd "$(dirname "$0")/../agent"
echo "=== 启动 Minecraft Agent Bot ==="
node bot.js
