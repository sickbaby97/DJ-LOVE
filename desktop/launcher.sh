#!/bin/bash
# DJ LOVE 启动器
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="$HOME"
unset PYTHONPATH
exec "$HOME/.djlove/venv/bin/python" "$HOME/.djlove/djlove_app.py"
