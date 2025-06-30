#!/bin/bash

set -e

SERVICE_NAME="github-feishu-bot"
APP_DIR="/home/ubuntu/Github-Feishu-Bot"

echo "🚀 开始部署 GitHub-飞书Bot 服务 (Poetry环境)..."

# 检查当前目录和必要文件
if [ ! -f "main.py" ]; then
    echo "❌ 错误: 未找到 main.py 文件"
    exit 1
fi

if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 未找到 pyproject.toml 文件，请确保在Poetry项目目录中"
    exit 1
fi

# 检查Poetry是否安装
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry未安装，请先安装Poetry"
    exit 1
fi

echo "📦 Poetry版本: $(poetry --version)"

# 安装/更新依赖
echo "📦 安装Python依赖..."
poetry install

# 确保生产依赖已安装
echo "�� 检查生产依赖..."
poetry show gunicorn >/dev/null 2>&1 || {
    echo "📦 添加gunicorn..."
    poetry add gunicorn==21.2.0
}

# 创建日志目录
mkdir -p logs

# 测试应用能否正常导入
echo "🧪 测试应用..."
poetry run python -c "import main; print('✅ 应用导入成功')" || {
    echo "❌ 应用导入失败，请检查代码"
    exit 1
}

# 获取Poetry虚拟环境信息
echo "🐍 Poetry环境信息:"
poetry env info

# 复制systemd服务文件
echo "⚙️  配置systemd服务..."
sudo cp systemd/$SERVICE_NAME.service /etc/systemd/system/

# 重新加载systemd配置
sudo systemctl daemon-reload

# 停止现有服务（如果正在运行）
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "🛑 停止现有服务..."
    sudo systemctl stop $SERVICE_NAME
fi

# 启用并启动服务
echo "🚀 启动服务..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ 服务启动成功！"
    echo ""
    sudo systemctl status $SERVICE_NAME --no-pager -l
else
    echo "❌ 服务启动失败！"
    echo "错误日志："
    sudo journalctl -u $SERVICE_NAME --no-pager -n 20
    exit 1
fi

# 测试健康检查
echo ""
echo "🔍 测试健康检查..."
sleep 2
if curl -f -s http://localhost:5000/health > /dev/null; then
    echo "✅ 健康检查通过"
    echo "📱 健康检查响应："
    curl -s http://localhost:5000/health | python3 -m json.tool
else
    echo "⚠️  健康检查失败，服务可能还在启动中"
fi

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 服务信息:"
echo "- 服务名称: $SERVICE_NAME"
echo "- 主文件: main.py"
echo "- 运行环境: Poetry ($(poetry env info --path))"
echo "- 工作目录: $APP_DIR"
echo "- 监听端口: 5000"
echo ""
echo "🔧 常用命令:"
echo "- 查看状态: sudo systemctl status $SERVICE_NAME"
echo "- 查看日志: sudo journalctl -u $SERVICE_NAME -f"
echo "- 重启服务: sudo systemctl restart $SERVICE_NAME"
echo "- Poetry Shell: poetry shell"
echo "- 直接运行: poetry run python main.py"
echo ""
echo "🌐 访问地址:"
echo "- 健康检查: http://localhost:5000/health"
echo "- Webhook地址: http://1.117.70.65:5000/webhook"
