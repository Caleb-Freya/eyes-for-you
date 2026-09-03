#!/usr/bin/env bash
# 启动 geo-track，只绑 127.0.0.1:8098
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
if [ -f data/pid ] && kill -0 "$(cat data/pid)" 2>/dev/null; then
  echo "已在运行 (pid $(cat data/pid))"; exit 0
fi
nohup python3 server.py >> data/server.log 2>&1 &
echo $! > data/pid
sleep 0.6
if kill -0 "$(cat data/pid)" 2>/dev/null; then
  echo "geo-track 启动 (pid $(cat data/pid)) → 127.0.0.1:8098"
  echo "你的钥匙： $(cat data/token.txt)"
else
  echo "启动失败，看 data/server.log"; tail -n 20 data/server.log; exit 1
fi
