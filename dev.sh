#!/bin/bash

# FastWhisper 开发启动脚本
# 用法: ./dev.sh [backend|worker|frontend|all]

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

prefer_local_backend() {
    [ -f "$PROJECT_ROOT/.env" ] || return 1
    grep -Eq '^DATABASE_URL=sqlite' "$PROJECT_ROOT/.env" && return 0
    grep -Eq '^TASK_RUNNER=inline' "$PROJECT_ROOT/.env" && return 0
    return 1
}

setup_local_python_env() {
    if [ -d "$PROJECT_ROOT/.venv311" ]; then
        source "$PROJECT_ROOT/.venv311/bin/activate"
        return 0
    fi

    if command -v uv &> /dev/null; then
        info "使用 uv 创建 Python 3.11 虚拟环境..."
        uv python install 3.11 >/dev/null
        uv venv "$PROJECT_ROOT/.venv311" --python 3.11 >/dev/null
        source "$PROJECT_ROOT/.venv311/bin/activate"
        return 0
    fi

    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        info "创建 Python 虚拟环境..."
        python3 -m venv "$PROJECT_ROOT/venv"
    fi
    source "$PROJECT_ROOT/venv/bin/activate"
}

# 检查依赖
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python3 未安装"
    fi
    local version
    version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    info "Python3: $(python3 --version)"
    if [[ "$version" != "3.11" ]]; then
        warn "当前本地 Python 为 $version，仓库锁定依赖按 Python 3.11 维护，建议切换到 3.11 或使用 Docker。"
    fi
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
        if ! docker compose version &> /dev/null; then
            warn "未检测到 Docker Compose 插件（docker compose）"
            return 1
        fi
        return 0
    fi
    return 1
}

compose_cmd() {
    docker compose "$@"
}

# 启动后端
start_backend() {
    info "启动后端服务..."

    cd "$PROJECT_ROOT"
    check_python

    # 检查 .env 文件
    if [ ! -f .env ]; then
        warn ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env
        warn "请编辑 .env 文件配置必要的环境变量"
    fi

    # 本地最小模式优先使用 SQLite + inline 处理
    if prefer_local_backend; then
        info "检测到本地简化模式，使用 SQLite + inline 任务处理..."

        setup_local_python_env

        if [ ! -f "$PROJECT_ROOT/.venv_local_installed" ]; then
            info "安装本地运行依赖..."
            pip install -r requirements-local.txt
            touch "$PROJECT_ROOT/.venv_local_installed"
        fi

        mkdir -p storage/uploads storage/results

        info "启动 FastAPI 服务..."
        uvicorn app.main:app --host 0.0.0.0 --port 8000 &

        success "后端服务已启动（API 内联处理模式）"
        info "API: http://localhost:8000"
        info "Docs: http://localhost:8000/docs"
    elif check_docker && [ -f docker-compose.yml ]; then
        info "使用 Docker Compose 启动数据库与缓存..."
        compose_cmd up -d postgres redis

        # 等待数据库就绪
        info "等待数据库就绪..."
        sleep 3

        # 运行迁移
        info "运行数据库迁移..."
        compose_cmd run --rm api alembic upgrade head

        # 启动 API 和 Worker
        compose_cmd up -d api worker

        success "后端服务已启动（API + Worker）"
        info "API: http://localhost:8000"
        info "Docs: http://localhost:8000/docs"
    else
        info "使用本地环境启动 API + Worker..."

        # 创建虚拟环境
        if [ ! -d venv ]; then
            info "创建 Python 虚拟环境..."
            python3 -m venv venv
        fi

        # 激活虚拟环境
        source venv/bin/activate

        # 安装依赖
        if [ ! -f "$PROJECT_ROOT/.venv_installed" ]; then
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
        info "启动 Worker 进程..."
        python -m app.worker &

        success "后端服务已启动（API + Worker）"
        info "API: http://localhost:8000"
        info "Docs: http://localhost:8000/docs"
    fi
}

# 停止后端
stop_backend() {
    info "停止后端服务..."

    cd "$PROJECT_ROOT"

    if check_docker && [ -f docker-compose.yml ]; then
        compose_cmd down
    else
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        pkill -f "python -m app.worker" 2>/dev/null || true
    fi

    success "后端服务已停止"
}

# 启动独立 Worker
start_worker() {
    info "启动 Worker 服务..."
    cd "$PROJECT_ROOT"
    check_python

    if [ ! -f .env ]; then
        warn ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env
        warn "请编辑 .env 文件配置必要的环境变量"
    fi

    if prefer_local_backend; then
        warn "当前配置是 inline 本地模式，不需要单独启动 Worker。"
        return 0
    fi

    if check_docker && [ -f docker-compose.yml ]; then
        compose_cmd up -d postgres redis worker
    else
        if [ ! -d venv ]; then
            info "创建 Python 虚拟环境..."
            python3 -m venv venv
        fi
        source venv/bin/activate
        if [ ! -f "$PROJECT_ROOT/.venv_installed" ]; then
            info "安装 Python 依赖..."
            pip install -r requirements.txt
            touch "$PROJECT_ROOT/.venv_installed"
        fi
        python -m app.worker &
    fi

    success "Worker 服务已启动"
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
    echo "  worker     启动独立 Worker"
    echo "  frontend   启动前端服务"
    echo "  all        启动所有服务"
    echo "  stop       停止所有服务"
    echo "  status     查看服务状态"
    echo "  help       显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 backend    # 仅启动后端"
    echo "  $0 worker     # 仅启动 Worker"
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

    # 检查 Worker
    if prefer_local_backend; then
        echo -e "  Worker: ${YELLOW}已跳过${NC} (inline 模式)"
    elif pgrep -f "python -m app.worker" > /dev/null 2>&1; then
        echo -e "  Worker: ${GREEN}运行中${NC}"
    else
        echo -e "  Worker: ${RED}未运行${NC}"
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
        compose_cmd ps 2>/dev/null || true
    fi
}

# 主入口
case "${1:-help}" in
    backend)
        start_backend
        ;;
    worker)
        start_worker
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
