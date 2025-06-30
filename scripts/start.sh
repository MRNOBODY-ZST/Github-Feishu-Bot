#!/bin/bash

# 设置工作目录
cd /home/ubuntu/Github-Feishu-Bot

# 创建日志目录
mkdir -p logs

# 获取Poetry虚拟环境路径
VENV_PATH=$(poetry env info --path)

# 使用Poetry虚拟环境中的gunicorn启动应用（注意这里是main:app）
exec $VENV_PATH/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --worker-class sync \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output \
    main:app
