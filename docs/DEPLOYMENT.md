# ParalleLife 部署指南

## 目录

1. [前置准备](#1-前置准备)
2. [GCP 项目初始化](#2-gcp-项目初始化)
3. [Firebase 初始化](#3-firebase-初始化)
4. [本地配置文件](#4-本地配置文件)
5. [部署后端（Cloud Run）](#5-部署后端cloud-run)
6. [部署前端（Firebase Hosting）](#6-部署前端firebase-hosting)
7. [部署 Firestore 索引和规则](#7-部署-firestore-索引和规则)
8. [验证部署](#8-验证部署)
9. [更新部署](#9-更新部署)
10. [排查问题](#10-排查问题)

---

## 1. 前置准备

### 安装工具

```bash
# Google Cloud CLI
brew install google-cloud-sdk   # macOS
# 或参考 https://cloud.google.com/sdk/docs/install

# Firebase CLI
npm install -g firebase-tools

# Docker（用于本地构建测试）
brew install --cask docker       # macOS
```

### 登录账号

```bash
# 登录 gcloud（打开浏览器授权）
gcloud auth login

# 设置 Application Default Credentials（给 SDK 调用 GCP API 用）
gcloud auth application-default login

# 登录 Firebase
firebase login
```

---

## 2. GCP 项目初始化

### 创建或选择项目

```bash
# 查看已有项目
gcloud projects list

# 设置默认项目（替换 YOUR_PROJECT_ID）
gcloud config set project YOUR_PROJECT_ID

# 确认当前配置
gcloud config list
```

### 启用必要的 API

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  --project YOUR_PROJECT_ID
```

> 全部启用约需 1-2 分钟。

### 创建 Artifact Registry 仓库

```bash
gcloud artifacts repositories create api \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project YOUR_PROJECT_ID
```

### 创建 Firestore 数据库

```bash
gcloud firestore databases create \
  --location=asia-northeast1 \
  --project YOUR_PROJECT_ID
```

> **注意**：Firestore 数据库每个项目只能创建一次，且 location 不可更改。

---

## 3. Firebase 初始化

### 关联 Firebase 项目

```bash
cd /path/to/EhHeiHeiHei   # 项目根目录

# 登录并初始化（选择 Hosting + Firestore）
firebase use YOUR_PROJECT_ID

# 验证关联
firebase projects:list
```

> 如果项目尚未在 Firebase Console 创建，先在 https://console.firebase.google.com 中将 GCP 项目添加到 Firebase。

---

## 4. 本地配置文件

### backend/.env

```bash
cat > backend/.env << 'EOF'
APP_ENV=production
GCP_PROJECT_ID=YOUR_PROJECT_ID
GCP_LOCATION=asia-northeast1
VERTEX_GEMINI_MODEL=gemini-2.5-flash
USE_FIRESTORE=true
ENABLE_FAKE_AI=false
EOF
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 运行环境（`dev`/`production`/`test`） | `dev` |
| `GCP_PROJECT_ID` | GCP 项目 ID | — |
| `GCP_LOCATION` | Vertex AI 区域 | `asia-northeast1` |
| `VERTEX_GEMINI_MODEL` | Gemini 模型名 | `gemini-2.5-flash` |
| `USE_FIRESTORE` | `true` 用 Firestore，`false` 用内存 | `true` |
| `ENABLE_FAKE_AI` | `true` 跳过 Gemini 调用（本地测试用） | `false` |

### 本地开发模式（不需要 GCP）

```bash
cat > backend/.env << 'EOF'
APP_ENV=dev
USE_FIRESTORE=false
ENABLE_FAKE_AI=true
EOF
```

---

## 5. 部署后端（Cloud Run）

### 构建并推送 Docker 镜像

```bash
cd backend

gcloud builds submit . \
  --tag asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/api/parallelife-api:latest \
  --project YOUR_PROJECT_ID
```

> 构建约需 2-4 分钟。Cloud Build 在 GCP 云端构建，无需本地 Docker。

### 部署到 Cloud Run

```bash
gcloud run deploy parallelife-api \
  --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/api/parallelife-api:latest \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --project YOUR_PROJECT_ID
```

记录输出的 **Service URL**，格式类似：

```
https://parallelife-api-xxxxxxxxxx-an.a.run.app
```

### IAM 确认

Cloud Run 使用默认计算服务账号（`PROJECT_NUMBER-compute@developer.gserviceaccount.com`），已有 `roles/editor` 权限，可访问 Firestore 和 Vertex AI。如需最小权限，可手动绑定：

```bash
SA="$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/aiplatform.user"
```

---

## 6. 部署前端（Firebase Hosting）

### 构建 Vite 应用

```bash
cd web

VITE_API_BASE=https://YOUR_CLOUD_RUN_URL \
VITE_WS_BASE=wss://YOUR_CLOUD_RUN_URL \
npm run build
```

> `VITE_API_BASE` 和 `VITE_WS_BASE` 在构建时被内嵌到 JS 中。WSS 是 WebSocket over TLS，对应 HTTPS 的 Cloud Run。

### 部署到 Firebase Hosting

```bash
cd ..   # 回到项目根目录

firebase deploy --only hosting
```

部署完成后访问：`https://YOUR_PROJECT_ID.web.app`

---

## 7. 部署 Firestore 索引和规则

首次部署或更改查询时，需要部署 Firestore 索引：

```bash
firebase deploy --only firestore
```

索引构建需要 1-5 分钟。可以查看状态：

```bash
gcloud firestore indexes composite list --project YOUR_PROJECT_ID
```

当 `STATE` 全部变为 `READY` 后即可正常使用。

当前项目中的索引（`firestore.indexes.json`）：

| Collection | Fields | 用途 |
|------------|--------|------|
| `messages` | `role` ASC, `processed` ASC, `created_at` ASC | 查询未处理的用户消息 |
| `messages` | `processed` ASC, `created_at` ASC | 会话记忆裁剪 |

---

## 8. 验证部署

### 后端健康检查

```bash
BACKEND=https://parallelife-api-oilxjmusxq-an.a.run.app

# API 文档（验证后端响应）
curl -s "$BACKEND/docs" | grep -o '<title>.*</title>'

# 查询 Agent 列表（此时应为空）
curl -s "$BACKEND/api/v1/agents"

# 初始化演示数据（创建 4 个默认 Agent）
curl -s -X POST "$BACKEND/internal/seed-demo"

# 再次查询（应返回 4 个 Agent）
curl -s "$BACKEND/api/v1/agents" | python3 -m json.tool | head -20

# 触发一次 Tick（Agent 决策 + 移动）
curl -s -X POST "$BACKEND/internal/tick" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('ok:', len(data['ok']), '| errors:', len(data['errors']))
for o in data['ok']:
    d = o['decision']
    print(f\"  {d['action']:10} | {d['internal_thought'][:60]}\")
"
```

期望输出：
```
ok: 4 | errors: 0
  move       | 好久没去涩谷109了，今天正好去看看有什么新衣服。
  move       | 喧嚣的十字路口让人疲惫，去星巴克找个安静的角落观察行人。
  move       | 有点冷，去星巴克暖和一下，顺便看看有什么新奇的。
  move       | 午后需要一杯咖啡提神，顺便处理些工作计划。
```

### 前端检查

1. 打开 `https://YOUR_PROJECT_ID.web.app`
2. 页面加载后地图上应出现 4 个彩色圆形标记（Agents）
3. 点击任意标记，右侧面板显示该 Agent 的对话历史
4. 点击 **Tick World** 触发一轮决策，标记应移动到新位置
5. 开启 **Auto Tick** 后，每 30 秒自动执行一轮

---

## 9. 更新部署

### 只更新后端

```bash
cd backend
gcloud builds submit . \
  --tag asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/api/parallelife-api:latest \
  --project YOUR_PROJECT_ID

gcloud run deploy parallelife-api \
  --image asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/api/parallelife-api:latest \
  --region asia-northeast1 \
  --project YOUR_PROJECT_ID
```

### 只更新前端

```bash
cd web
VITE_API_BASE=https://YOUR_CLOUD_RUN_URL \
VITE_WS_BASE=wss://YOUR_CLOUD_RUN_URL \
npm run build

cd ..
firebase deploy --only hosting
```

### 一键脚本（可选）

```bash
# backend/deploy.sh
#!/bin/bash
set -e
PROJECT=YOUR_PROJECT_ID
IMAGE=asia-northeast1-docker.pkg.dev/$PROJECT/api/parallelife-api:latest
BACKEND_URL=https://parallelife-api-oilxjmusxq-an.a.run.app

echo "==> Building backend..."
gcloud builds submit . --tag "$IMAGE" --project "$PROJECT"

echo "==> Deploying Cloud Run..."
gcloud run deploy parallelife-api \
  --image "$IMAGE" \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --project "$PROJECT"

echo "==> Building frontend..."
cd ../web
VITE_API_BASE="$BACKEND_URL" VITE_WS_BASE="wss://$(echo $BACKEND_URL | sed 's|https://||')" npm run build

echo "==> Deploying Firebase Hosting..."
cd ..
firebase deploy --only hosting

echo "Done."
```

---

## 10. 排查问题

### 查看 Cloud Run 日志

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=parallelife-api" \
  --limit=50 \
  --format="value(textPayload)" \
  --freshness=1h \
  --project YOUR_PROJECT_ID
```

### 常见错误和解决方法

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| `Cloud Firestore API has not been used` | Firestore API 未启用 | `gcloud services enable firestore.googleapis.com` |
| `The database (default) does not exist` | Firestore 数据库未创建 | `gcloud firestore databases create --location=asia-northeast1` |
| `The query requires an index` | 复合索引未部署 | `firebase deploy --only firestore` 并等待 READY |
| `finishReason: MAX_TOKENS` / 截断 JSON | Gemini 输出 token 不足 | 在 `container.py` 增大 `max_output_tokens`（当前已设为 2048） |
| `FileNotFoundError: demo_geo.json` | Docker 内包路径错误 | 确保 `Dockerfile` 使用 `pip install -e .`（editable install） |
| `python-multipart` 缺失 | FastAPI 文件上传依赖 | `pip install python-multipart`，加入 `pyproject.toml` |
| `GCP_PROJECT_ID is required` | 环境变量未设置 | 确认 `backend/.env` 中有 `GCP_PROJECT_ID` |
| Cloud Run 启动后无 Agent | 内存仓库为空 | 调用 `POST /internal/seed-demo` |

### 验证 Vertex AI 访问

```bash
# 用 gcloud 测试 Gemini API 是否可访问
gcloud auth print-access-token | xargs -I{} curl -s \
  -H "Authorization: Bearer {}" \
  "https://asia-northeast1-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT_ID/locations/asia-northeast1/publishers/google/models/gemini-2.5-flash:generateContent" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Hello"}]}]}' | python3 -m json.tool | head -20
```
