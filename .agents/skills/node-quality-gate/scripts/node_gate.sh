#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

if [[ ! -f "$ROOT_DIR/agent/package.json" ]]; then
  echo "[node-gate] 未找到 agent/package.json"
  exit 1
fi

echo "[node-gate] 运行 Node 门禁: npm run gate"
(cd "$ROOT_DIR/agent" && npm run gate)

if ss -tln 2>/dev/null | grep -q ':25565'; then
  echo "[node-gate] 检测到服务器在线，执行 smoke: npm run research"
  (cd "$ROOT_DIR/agent" && npm run research)
else
  echo "[node-gate] 未检测到 25565 端口监听，跳过 smoke"
fi

echo "[node-gate] 完成"
