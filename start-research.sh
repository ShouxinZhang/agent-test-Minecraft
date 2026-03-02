#!/bin/bash
set -euo pipefail

# 兼容入口：统一转发到 scripts/ 目录
"$(dirname "$0")/scripts/start-research.sh"
