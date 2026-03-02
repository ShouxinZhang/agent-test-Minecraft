#!/bin/bash
# 启动自动化研究脚本
cd "$(dirname "$0")/agent"
echo "=== 启动 Minecraft Agent 自动研究 ==="
node research.js
