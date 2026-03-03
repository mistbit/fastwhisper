# FastWhisper - 录音转会议纪要服务

基于 Whisper 的录音转会议纪要服务，支持说话人识别和自动生成会议纪要。

## 功能特性

- 🎤 **音频转录** - 使用 faster-whisper 进行高精度语音识别
- 👥 **说话人分离** - 使用 pyannote 识别不同说话人
- 📝 **会议纪要** - 使用 LLM 自动生成结构化会议纪要
- 🔌 **REST API** - 完整的 RESTful API 接口
- 🖥️ **Web UI** - 现代化的 Web 界面

## 技术栈

**后端:**
- Python 3.11
- FastAPI
- PostgreSQL + SQLAlchemy
- Redis
- faster-whisper
- pyannote.audio

**前端:**
- Vue 3 + Vite
- TailwindCSS
- Pinia

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- NVIDIA GPU (推荐)

### 使用启动脚本

```bash
# 启动所有服务
./dev.sh all

# 仅启动后端
./dev.sh backend

# 仅启动前端
./dev.sh frontend

# 停止所有服务
./dev.sh stop

# 查看服务状态
./dev.sh status
```

### Docker 部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 手动启动

**后端:**

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 运行数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端:**

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
echo "VITE_API_TOKEN=your_token" > .env

# 启动开发服务器
npm run dev
```

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger 文档。

### 主要接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/tasks | 上传音频创建任务 |
| GET | /api/v1/tasks/{task_id}/progress | 查询任务进度 |
| GET | /api/v1/tasks/{task_id}/minutes | 获取会议纪要 |
| GET | /api/v1/tasks | 获取任务列表 |
| DELETE | /api/v1/tasks/{task_id} | 删除任务 |

## 环境配置

主要环境变量 (`.env` 文件):

```bash
# 数据库
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=fastwhisper

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 认证
API_TOKEN=your_secure_token

# Whisper
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda

# HuggingFace (用于 pyannote)
HUGGINGFACE_TOKEN=your_huggingface_token

# LLM
LLM_PROVIDER=qwen
LLM_API_KEY=your_api_key
LLM_MODEL=qwen-max
```

## 项目结构

```
fastwhisper/
├── app/
│   ├── api/           # API 路由
│   ├── core/          # 核心配置
│   ├── models/        # 数据模型
│   ├── schemas/       # Pydantic 模型
│   ├── services/      # 业务服务
│   └── workers/       # 后台任务
├── frontend/          # Vue 前端
│   └── src/
│       ├── api/       # API 封装
│       ├── stores/    # 状态管理
│       ├── components/# UI 组件
│       └── views/     # 页面视图
├── alembic/           # 数据库迁移
├── storage/           # 文件存储
├── dev.sh             # 开发启动脚本
└── docker-compose.yml # Docker 配置
```

## License

MIT