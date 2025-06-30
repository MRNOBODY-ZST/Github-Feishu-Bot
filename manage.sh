#!/bin/bash

SERVICE_NAME="github-feishu-bot"

case "$1" in
    start)
        echo "🚀 启动服务..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    stop)
        echo "🛑 停止服务..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "🔄 重启服务..."
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    status)
        echo "📊 服务状态:"
        sudo systemctl status $SERVICE_NAME --no-pager -l
        ;;
    logs)
        echo "📋 实时日志 (Ctrl+C 退出):"
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    app-logs)
        echo "📋 应用日志:"
        echo "--- 错误日志 ---"
        tail -20 logs/error.log 2>/dev/null || echo "暂无错误日志"
        echo ""
        echo "--- 访问日志 ---"
        tail -10 logs/access.log 2>/dev/null || echo "暂无访问日志"
        ;;
    test)
        echo "🧪 测试服务..."
        echo "健康检查:"
        curl -s http://localhost:5000/health | python3 -m json.tool || echo "健康检查失败"
        echo ""
        echo "根路径:"
        curl -s http://localhost:5000/ | python3 -m json.tool || echo "根路径访问失败"
        ;;
    dev)
        echo "🔧 开发模式启动 (Ctrl+C 停止):"
        poetry run python main.py
        ;;
    shell)
        echo "🐍 进入Poetry Shell:"
        poetry shell
        ;;
    update)
        echo "🔄 更新依赖并重启服务..."
        sudo systemctl stop $SERVICE_NAME
        poetry update
        sudo systemctl start $SERVICE_NAME
        echo "更新完成"
        ;;
    env-info)
        echo "🐍 Poetry环境信息:"
        poetry env info
        echo ""
        echo "📦 已安装包:"
        poetry show
        ;;
    *)
        echo "GitHub-飞书Bot 管理脚本 (Poetry + main.py)"
        echo ""
        echo "用法: $0 {start|stop|restart|status|logs|app-logs|test|dev|shell|update|env-info}"
        echo ""
        echo "命令说明:"
        echo "  start     - 启动systemd服务"
        echo "  stop      - 停止systemd服务"
        echo "  restart   - 重启systemd服务"
        echo "  status    - 查看服务状态"
        echo "  logs      - 查看实时系统日志"
        echo "  app-logs  - 查看应用日志"
        echo "  test      - 测试服务接口"
        echo "  dev       - 开发模式运行（直接运行main.py）"
        echo "  shell     - 进入Poetry虚拟环境Shell"
        echo "  update    - 更新Poetry依赖并重启"
        echo "  env-info  - 显示Poetry环境信息"
        exit 1
        ;;
esac
