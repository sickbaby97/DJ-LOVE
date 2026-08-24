#!/bin/bash
# DJ LOVE 启动器 —— 强制 arm64 架构（匹配 Pillow）
export PATH="/Users/abie/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/abie"
unset PYTHONPATH
exec arch -arm64 /Users/abie/.djlove/venv/bin/python /Users/abie/.djlove/djlove_app.py >> /Users/abie/.djlove/app.log 2>&1
