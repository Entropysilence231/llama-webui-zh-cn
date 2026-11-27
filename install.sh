#!/usr/bin/env bash
# 一键生成简中 WebUI：镜像英文原版 → 生成 webui-zh
set -euo pipefail
cd "$(dirname "$0")"
BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"

echo "[1/2] 从 ${BASE_URL} 镜像英文原版 UI ..."
BASE_URL="$BASE_URL" python3 scripts/mirror_en.py

echo "[2/2] 生成简体中文 UI ..."
python3 scripts/apply_zh.py

echo
echo "完成。重启 llama-server 时加参数：--path $(pwd)/webui-zh"
