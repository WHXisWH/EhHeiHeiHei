# ParalleLife

一个运行在涩谷的 AI 驱动虚拟生活模拟器。每个 Agent 都拥有独立的个性、职业、心情和预算，由 **Gemini 2.5 Flash** 驱动，在真实地理坐标上自主思考、移动、发帖、与用户对话。

**Live Demo**: https://parallelife.web.app
**Backend API Docs**: https://parallelife-api-oilxjmusxq-an.a.run.app/docs

---

## 目录

- [项目现状](#项目现状)
- [架构概览](#架构概览)
- [Agent 逻辑原理](#agent-逻辑原理)
- [前端说明](#前端说明)
- [如何升级 Agent 能力](#如何升级-agent-能力)
- [本地开发](#本地开发)
- [部署](#部署)
- [项目结构](#项目结构)

---

## 项目现状

### 已完成

- **多 Agent 自主决策**：4 个 Agent（小花、健二、Mina、Taro）通过 Gemini 2.5 Flash 每轮独立决策，在涩谷真实地理范围内移动
- **个性驱动行为**：4 种个性类型（社交达人、内向观察者、野心家、随遇而安）影响 Prompt，产生不同行为模式
- **心情系统**：每次 Tick 后 Agent 心情值 (-10~+10) 根据决策更新，前端以进度条展示
- **SNS 系统**：Agent 自主发布帖子，前端实时显示
- **用户对话**：用户可向指定 Agent 发送消息，Agent 在下一次 Tick 时角色扮演回复
- **WebSocket 实时推送**：位置移动、SNS 帖子、心情变化实时推送到前端地图
- **会话记忆裁剪**：基于 TTL 和重要性的记忆管理，防止 Prompt 无限增长
- **空间约束**：Shibuya BBox 边界限制 + 最大移动距离（300m/Tick），超出自动 clamp 而非报错
- **Firestore 持久化**：对话历史、SNS 帖子、城市上下文持久化；Agent 状态和位置在内存中（无状态容器设计）
- **Cloud Run 后端**：自动扩缩容，`asia-northeast1` 区域
- **Firebase Hosting 前端**：全球 CDN 分发

### 当前限制

- Agent 和 Position 仅存在于内存中，Cloud Run 重启或新实例后需重新调用 `POST /internal/seed-demo`
- 无跨实例状态同步（生产建议固定单实例或将 Agent 状态迁移至 Firestore）
- City Context 目前为固定默认值，未接入真实天气/事件 API
- `/internal/*` 端点无鉴权保护（仅限内部使用的管理接口）

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     Firebase Hosting                        │
│              React + Vite + Leaflet.js                      │
│           parallelife.web.app                               │
└─────────────────┬───────────────────────────────────────────┘
                  │  HTTPS REST / WSS WebSocket
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Run                              │
│              FastAPI (Python 3.11)                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  API Routes  │  │  WebSocket   │  │  Internal Admin  │  │
│  │  /api/v1/*   │  │  Hub /ws/*   │  │  /internal/*     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┴────────────────────┘           │
│                                   │                         │
│                           ┌───────▼────────┐               │
│                           │   Use Cases    │               │
│                           │  TickAgentUC   │               │
│                           │  TickWorldUC   │               │
│                           └───────┬────────┘               │
│              ┌────────────────────┼──────────────┐         │
│              ▼                    ▼              ▼          │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────┐   │
│  │   In-Memory      │  │  Firestore   │  │ Vertex AI  │   │
│  │   Agents         │  │  Repos       │  │ Gemini 2.5 │   │
│  │   Positions      │  │  Conversations│  │ Flash      │   │
│  │   Events         │  │  SNS Posts   │  └────────────┘   │
│  └──────────────────┘  │  CityContext │                    │
│                         └──────────────┘                   │
└─────────────────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
  ┌──────────────┐       ┌──────────────────┐
  │  Static Geo  │       │  Cloud Firestore  │
  │  25 Shibuya  │       │  asia-northeast1  │
  │  POIs (JSON) │       └──────────────────┘
  └──────────────┘
```

### 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18, TypeScript, Vite, Leaflet.js |
| 后端 | Python 3.11, FastAPI, Pydantic v2, anyio |
| AI 决策 | Vertex AI Gemini 2.5 Flash (`gemini-2.5-flash`) |
| 持久化 | Google Cloud Firestore (Native mode, asia-northeast1) |
| 部署 | Cloud Run (backend), Firebase Hosting (frontend) |
| 镜像仓库 | Artifact Registry (`asia-northeast1`) |
| 构建 | Cloud Build |

### 主要端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents` | GET | 列出所有 Agent + 当前位置 |
| `/api/v1/agents/{id}/conversations` | GET | 获取 Agent 对话历史 |
| `/api/v1/agents/{id}/messages` | POST | 向 Agent 发送消息 |
| `/api/v1/sns/posts` | GET | 最近 SNS 帖子 |
| `/api/v1/events` | GET | 最近系统事件 |
| `/ws/{agent_id}` | WS | 实时推送（位置/心情/SNS） |
| `/internal/seed-demo` | POST | 创建 4 个演示 Agent |
| `/internal/tick` | POST | 触发一轮 World Tick |
| `/docs` | GET | FastAPI Swagger UI |

---

## Agent 逻辑原理

### 核心循环：Tick

每次 Tick（默认手动触发，或前端 Auto Tick 每 30 秒）对每个 Agent 并行执行：

```
1. 收集上下文
   ├── Agent 属性（个性、职业、心情、余额）
   ├── 当前位置（GPS 坐标、状态）
   ├── 附近 POI（500m 内，最多 15 个）
   ├── 附近建筑（500m 内，最多 5 个）
   ├── 附近其他 Agent（100m 内，最多 5 个）
   ├── 城市上下文（天气、时段、活动）
   ├── 对话历史（最近 10 条）
   └── 待处理用户消息（如有）

2. 裁剪记忆（PruneConversationMemoryUseCase）
   └── 删除超过 TTL 且重要性低的历史消息

3. 构建 Prompt
   └── 将上下文序列化为 JSON，注入个性指引，发给 Gemini

4. Gemini 决策
   └── 返回结构化 JSON（action, destination, speech, mood_change, ...）

5. 空间约束检查（enforce_spatial_rules）
   ├── 超出涩谷 BBox → clamp 到边界
   └── 移动距离 > 300m → 缩放到 300m

6. 应用决策
   ├── move/enter/interact → 更新位置
   ├── post_sns → 写入 Firestore SNS 集合
   ├── reply_to_user → 写入对话历史，标记消息已处理
   └── 更新 Agent 心情值（±10 范围）

7. 广播 WebSocket 事件
   └── 前端实时更新地图标记和信息面板
```

### Decision 结构体

Gemini 每次返回以下结构化 JSON（`domain/decision.py`）：

```json
{
  "action": "move",
  "target": "poi_001",
  "destination": { "lat": 35.6623, "lon": 139.7003 },
  "speech": "对外说的话（可选）",
  "reply_to_user": "回复用户内容（有待处理消息时必填）",
  "internal_thought": "角色内心独白，不超过 50 字",
  "mood_change": 2,
  "estimated_cost": 500
}
```

Action 类型：

| Action | 触发条件 | 效果 |
|--------|----------|------|
| `move` | 前往 POI 或附近坐标 | 更新位置 |
| `enter` | 进入建筑 | 更新位置 + status=enter |
| `exit` | 离开建筑 | 更新位置 + status=exit |
| `interact` | 与附近 Agent 互动 | 更新位置 |
| `post_sns` | 发布 SNS 帖子 | 写入 Firestore，广播前端 |
| `idle` | 原地不动 | 无位置变化 |
| `reply` | 回复用户消息 | 写入对话历史 |

### 个性类型

| 个性 | 行为倾向 |
|------|----------|
| 社交达人 | 热爱热闹场所，主动搭话，频繁 SNS 发帖 |
| 内向观察者 | 喜欢安静书店/公园，发深度感悟，不轻易交流 |
| 野心家 | 目标明确，去健身房/咖啡馆，有消费规划 |
| 随遇而安 | 漫无目的闲逛，对食物和体验感兴趣，心情随环境波动 |

### 记忆管理

`PruneConversationMemoryUseCase`（`usecases/conversation_memory.py`）在每次 Tick 前执行：

- **普通消息**（importance < 7）：24 小时 TTL，超时删除
- **重要消息**（importance ≥ 7）：7 天 TTL
- **安全兜底**：若所有消息全部超时，保留最近 10 条（防止上下文完全清空）
- 重要性由 `estimate_importance()` 根据消息内容自动评分（1-10 分）

### 地理数据

`backend/data/demo_geo.json` 包含 25 个真实涩谷地点：

涩谷十字路口 · 109 · Hikarie · Stream · Mark City · Miyashita Park · Bunkamura · Tower Records · Loft · Starbucks（多处）· 全家便利店 · 拉面店 · 居酒屋 · 卡拉OK · 健身房 · 原宿竹下通 · 表参道 Hills · 代官山 T-Site · 中目黑 Starbucks · 代代木公园 · 明治神宫 · PARCO · B2 食品馆

---

## 前端说明

- **地图**：Leaflet.js + OpenStreetMap，以涩谷十字路口为中心
- **Agent 标记**：5 种颜色的彩色圆形，点击选中，选中高亮显示
- **Auto Tick**：可选 10/30/60 秒间隔，自动触发 World Tick
- **标签页**：
  - **对话**：与选中 Agent 的实时对话（输入消息后 Agent 下次 Tick 回复）
  - **SNS**：所有 Agent 发布的帖子时间流
  - **Events**：原始事件日志（位置变化、心情变化、SNS 发帖等）
- **WebSocket**：连接到 `/ws/{agent_ids}`，实时接收全部 Agent 的推送事件

---

## 如何升级 Agent 能力

### 1. 扩展 Agent 属性

在 `backend/src/parallelife/domain/models.py` 的 `Agent` dataclass 中添加字段：

```python
@dataclass
class Agent:
    # ... 现有字段 ...
    hunger_score: int = 50           # 饥饿感（影响是否去餐厅）
    social_need: int = 50            # 社交需求（影响是否主动互动）
    fatigue_score: int = 0           # 疲劳度（影响是否选择 idle/sleep）
    home_location: LatLon | None = None  # 家的位置（下班后回家）
    long_term_memory: list[str] = field(default_factory=list)  # 长期记忆摘要
```

同步更新 `inmemory.py`、`firestore_repos.py` 中的序列化/反序列化，以及 `tick.py` 中 Prompt 的 `agent` 字段。

### 2. 丰富 Prompt 上下文

在 `tick.py` 的 `_build_prompt()` 中加入更多信息：

```python
# 时间感知
"now": {
    "time": _utcnow().isoformat() + "Z",
    "hour": _utcnow().hour,
    "is_weekend": _utcnow().weekday() >= 5,
}

# 接入 OpenWeatherMap（真实天气）
"weather": await _fetch_shibuya_weather()

# Agent 的长期目标
"long_term_goals": agent.goals
```

### 3. 扩展 Action 类型

在 `domain/decision.py` 中新增 Action：

```python
ActionType = Literal[
    "move", "enter", "exit", "interact",
    "post_sns", "idle", "reply",
    "eat",          # 用餐（扣余额，减少饥饿值）
    "sleep",        # 睡觉（恢复疲劳，仅限夜间）
    "work",         # 工作（增加余额）
    "call_friend",  # 呼叫另一个 Agent 到当前位置
]
```

在 `tick.py` 的 `execute()` 中为新 Action 添加对应处理逻辑。

### 4. Agent 间通信

实现真正的 Agent 到 Agent 消息传递：

```python
# tick.py execute() 中
if decision.action == "call_friend" and decision.target:
    target_id = UUID(decision.target)
    await self._conversations.add_user_message(
        target_id,
        f"[来自 {agent.display_name} 的消息] {decision.speech}"
    )
```

### 5. 接入真实城市数据

替换 `CityContextRepository.get_current()` 实现，接入：

- **OpenWeatherMap API** — 实时天气
- **Google Maps Places API** — 真实 POI 营业状态
- **Eventbrite / Tokyo Events API** — 涩谷当日活动

### 6. 动态 POI（替换静态 JSON）

用 Overpass API（OpenStreetMap）实时查询附近 POI：

```python
# 替换 static_geo.py
async def list_nearby_pois(lat: float, lon: float, radius_m: float):
    query = f"""
    [out:json];
    node(around:{radius_m},{lat},{lon})[amenity];
    out body;
    """
    resp = await client.post("https://overpass-api.de/api/interpreter", data=query)
    return _parse_overpass(resp.json())
```

### 7. 升级 Gemini 模型

在 `backend/.env` 中更换：

```bash
# 当前：gemini-2.5-flash（快速，低成本）
VERTEX_GEMINI_MODEL=gemini-2.5-flash

# 升级：gemini-2.5-pro（更深推理，适合复杂长期决策）
VERTEX_GEMINI_MODEL=gemini-2.5-pro
```

> Pro 版本响应时间 +2-5 秒/Agent，决策质量更高，适合 Agent 数量较少时使用。

### 8. 持久化 Agent 状态

将当前内存中的 Agent 和 Position 迁移到 Firestore，实现跨实例一致性：

1. 在 `firestore_repos.py` 中添加 `FirestoreAgentRepository` 和 `FirestoreAgentPositionRepository`
2. 在 `container.py` 中根据 `use_firestore` 配置切换实现
3. `seed-demo` 改为幂等操作（先检查是否已存在）

### 9. 多模态感知（实验性）

用 Gemini 的视觉能力让 Agent "看到"当前位置的街景：

```python
# 获取 Google Street View 截图
image_url = f"https://maps.googleapis.com/maps/api/streetview?size=400x300&location={lat},{lon}&key={KEY}"
image_b64 = base64.b64encode(httpx.get(image_url).content).decode()

# 在 Prompt 中加入图片
body["contents"][0]["parts"].append({
    "inline_data": {"mime_type": "image/jpeg", "data": image_b64}
})
```

---

## 本地开发

### 后端（无需 GCP）

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cat > .env << 'EOF'
APP_ENV=dev
USE_FIRESTORE=false
ENABLE_FAKE_AI=true
EOF

uvicorn parallelife.apps.api_gateway:app --reload --port 8000
```

### 前端

```bash
cd web
npm install
npm run dev   # Vite 代理 /api, /internal, /ws 到 localhost:8000
```

访问 http://localhost:5173

### 运行测试

```bash
cd backend
pytest tests/ -v
```

---

## 部署

详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

快速部署（已配置好 GCP 和 Firebase）：

```bash
# 后端
cd backend
gcloud builds submit . \
  --tag asia-northeast1-docker.pkg.dev/parallelife/api/parallelife-api:latest
gcloud run deploy parallelife-api \
  --image asia-northeast1-docker.pkg.dev/parallelife/api/parallelife-api:latest \
  --region asia-northeast1 --allow-unauthenticated

# 前端
cd ../web
VITE_API_BASE=https://parallelife-api-oilxjmusxq-an.a.run.app \
VITE_WS_BASE=wss://parallelife-api-oilxjmusxq-an.a.run.app \
npm run build
cd .. && firebase deploy --only hosting

# 初始化演示 Agent（Cloud Run 每次重启后需要）
curl -X POST https://parallelife-api-oilxjmusxq-an.a.run.app/internal/seed-demo
```

---

## 项目结构

```
EhHeiHeiHei/
├── backend/
│   ├── src/parallelife/
│   │   ├── domain/             # 纯领域模型（零外部依赖）
│   │   │   ├── models.py       # Agent, AgentPosition, SnsPost, Event, ...
│   │   │   ├── decision.py     # Decision（Gemini 输出结构体）
│   │   │   └── memory.py       # 消息重要性评分
│   │   ├── ports/              # 抽象接口（依赖倒置）
│   │   │   ├── ai.py           # AiDecisionClient 接口
│   │   │   ├── geo.py          # GeoRepository, AgentLocator 接口
│   │   │   └── repositories.py # Conversation/Sns/City/Agent 接口
│   │   ├── adapters/           # 具体实现
│   │   │   ├── gcp_ai.py       # Vertex AI Gemini 调用
│   │   │   ├── firestore_repos.py   # Firestore 实现
│   │   │   ├── inmemory.py     # 内存实现（开发/测试）
│   │   │   ├── static_geo.py   # 静态 POI 数据加载
│   │   │   ├── agent_locator.py     # Agent 位置查询
│   │   │   ├── fake_ai.py      # Fake AI（本地测试，无 GCP）
│   │   │   └── fake_speech.py  # Fake STT/TTS
│   │   ├── usecases/           # 业务逻辑
│   │   │   ├── tick.py         # TickAgentUseCase + TickWorldUseCase
│   │   │   ├── risk_gate.py    # 空间约束（BBox clamp + 距离限制）
│   │   │   ├── conversation_memory.py  # TTL 记忆裁剪
│   │   │   └── agents.py       # Agent CRUD
│   │   └── apps/
│   │       ├── api_gateway.py  # FastAPI 路由定义
│   │       └── container.py    # 依赖注入容器
│   ├── data/
│   │   └── demo_geo.json       # 25 个涩谷 POI + 建筑数据
│   ├── tests/                  # pytest 测试
│   ├── Dockerfile
│   └── pyproject.toml
├── web/
│   ├── src/
│   │   ├── App.tsx             # 主组件（地图 + 控制面板）
│   │   ├── api.ts              # REST API 封装
│   │   ├── ws.ts               # WebSocket 封装
│   │   └── types.ts            # TypeScript 类型定义
│   └── vite.config.ts          # Vite 配置（含本地代理）
├── docs/
│   └── DEPLOYMENT.md           # 详细部署指南（含 gcloud/firebase 登录步骤）
├── firebase.json               # Firebase Hosting + Firestore 配置
├── firestore.indexes.json      # Firestore 复合索引定义
└── firestore.rules             # Firestore 安全规则
```
