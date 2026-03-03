#!/bin/bash

# FastWhisper 开发启动脚本
# 用法: ./dev.sh [backend|frontend|all]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 检查依赖
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3 未安装"
    fi
    info "Python3: $(python3 --version)"
}

check_node() {
    if ! command -v node &> /dev/null; then
        error "Node.js 未安装"
    fi
    info "Node.js: $(node --version)"
    info "npm: $(npm --version)"
}

check_docker() {
    if command -v docker &> /dev/null; then
        info "Docker: $(docker --version)"
        return 0
    fi
    return 1
}

# 启动后端
start_backend() {
    info "启动后端服务..."

    cd "$PROJECT_ROOT"

    # 检查 .env 文件
    if [ ! -f .env ]; then
        warn ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env
        warn "请编辑 .env 文件配置必要的环境变量"
    fi

    # 检查是否使用 Docker
    if check_docker && [ -f docker-compose.yml ]; then
        info "使用 Docker Compose 启动..."
        docker-compose up -d postgres redis

        # 等待数据库就绪
        info "等待数据库就绪..."
        sleep 3

        # 运行迁移
        info "运行数据库迁移..."
        docker-compose exec -T api alembic upgrade head 2>/dev/null || \
            alembic upgrade head

        # 启动 API
        docker-compose up -d api

        success "后端服务已启动"
        info "API: http://localhost:8000"
        info "Docs: http://localhost:8000/docs"
    else
        info "使用本地环境启动..."

        # 创建虚拟环境
        if [ ! -d venv ]; then
            info "创建 Python 虚拟环境..."
            python3 -m venv venv
        fi

        # 激活虚拟环境
        source venv/bin/activate

        # 安装依赖
        if [ ! -d "$PROJECT_ROOT/.venv_installed" ]; then
            info "安装 Python 依赖..."
            pip install -r requirements.txt
            touch "$PROJECT_ROOT/.venv_installed"
        fi

        # 创建存储目录
        mkdir -p storage/uploads storage/results

        # 运行迁移
        info "运行数据库迁移..."
        alembic upgrade head

        # 启动服务
        info "启动 FastAPI 服务..."
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

        success "后端服务已启动"
        info "API: http://localhost:8000"
        info "Docs: http://localhost:8000/docs"
    fi
}

# 停止后端
stop_backend() {
    info "停止后端服务..."

    cd "$PROJECT_ROOT"

    if check_docker && [ -f docker-compose.yml ]; then
        docker-compose down
    else
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
    fi

    success "后端服务已停止"
}

# 启动前端
start_frontend() {
    info "启动前端服务..."

    cd "$PROJECT_ROOT/frontend"

    check_node

    # 检查 .env 文件
    if [ ! -f .env ]; then
        warn "前端 .env 文件不存在，创建默认配置..."
        echo "VITE_API_TOKEN=your_token_here" > .env
        warn "请编辑 frontend/.env 文件设置 VITE_API_TOKEN"
    fi

    # 安装依赖
    if [ ! -d node_modules ]; then
        info "安装前端依赖..."
        npm install
    fi

    # 启动开发服务器
    info "启动 Vite 开发服务器..."
    npm run dev &

    success "前端服务已启动"
    info "UI: http://localhost:3000"
}

# 停止前端
stop_frontend() {
    info "停止前端服务..."
    pkill -f "vite" 2>/dev/null || true
    success "前端服务已停止"
}

# 启动全部
start_all() {
    info "启动所有服务..."
    start_backend
    echo ""
    start_frontend
    echo ""
    success "所有服务已启动!"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  FastWhisper 服务已启动${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "  后端 API:  ${BLUE}http://localhost:8000${NC}"
    echo -e "  API 文档:  ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "  前端 UI:   ${BLUE}http://localhost:3000${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    warn "按 Ctrl+C 停止所有服务"
    wait
}

# 停止全部
stop_all() {
    info "停止所有服务..."
    stop_frontend
    stop_backend
    success "所有服务已停止"
}

# 显示帮助
show_help() {
    echo "FastWhisper 开发启动脚本"
    echo ""
    echo "用法: $0 <command>"
    echo ""
    echo "命令:"
    echo "  backend    启动后端服务"
    echo "  frontend   启动前端服务"
    echo "  all        启动所有服务"
    echo "  stop       停止所有服务"
    echo "  status     查看服务状态"
    echo "  help       显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 backend    # 仅启动后端"
    echo "  $0 frontend   # 仅启动前端"
    echo "  $0 all        # 启动前后端"
    echo "  $0 stop       # 停止所有服务"
}

# 查看状态
show_status() {
    echo "服务状态:"
    echo ""

    # 检查后端
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  后端:  ${GREEN}运行中${NC} (http://localhost:8000)"
    else
        echo -e "  后端:  ${RED}未运行${NC}"
    fi

    # 检查前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "  前端:  ${GREEN}运行中${NC} (http://localhost:3000)"
    else
        echo -e "  前端:  ${RED}未运行${NC}"
    fi

    # 检查 Docker 服务
    if check_docker && [ -f docker-compose.yml ]; then
        echo ""
        echo "Docker 容器:"
        docker-compose ps 2>/dev/null || true
    fi
}

# 主入口
case "${1:-help}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "未知命令: $1\n运行 '$0 help' 查看帮助"
        ;;
esac