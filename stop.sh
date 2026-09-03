#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f data/pid ] && kill -0 "$(cat data/pid)" 2>/dev/null; then
  kill "$(cat data/pid)"; rm -f data/pid; echo "geo-track 已停"
else
  echo "没在运行"
fi
