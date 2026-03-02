# ParalleLife 平行人生

## MVP 产品需求文档

**PLATEAU × AI Agent × Google Cloud**

---

| 项目 | 内容 |
|------|------|
| 版本 | v1.1 |
| 状态 | 草案 |
| 日期 | 2026年2月 |
| 目标 | PLATEAU NEXT Award 2026 |

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [系统架构](#2-系统架构)
3. [数据库表结构](#3-数据库表结构)
4. [Agent 生命周期与决策流程](#4-agent-生命周期与决策流程)
5. [通信系统](#5-通信系统)
6. [SNS 系统](#6-sns-系统)
7. [风险门控与宪法](#7-风险门控与宪法mvp-最小版)
8. [Unity 客户端规格](#8-unity-客户端规格)
9. [API 接口](#9-api-接口)
10. [Prompt 工程](#10-prompt-工程)
11. [非功能性需求](#11-非功能性需求)
12. [未来路线图](#12-未来路线图后-mvp)
13. [附录](#13-附录)

---

## 1. 执行摘要

ParalleLife 是一个基于日本国土交通省 PLATEAU 3D 都市模型的多智能体平行社会模拟平台。用户在真实城市数字孪生中创建 AI 分身，这些分身具有独立性格与生活轨迹，自主进行工作、社交、发布 SNS 动态等行为。用户无法直接操控分身，但可通过异步文字留言或同步语音通话进行跨次元对话。

### 1.1 MVP 核心边界

| 维度 | MVP 范围 |
|------|----------|
| 城市/区域 | 涩谷（渋谷），LOD1 建筑轮廓 |
| Agent 数量 | 最多 4 个（2 个用户创建 + 2 个系统 NPC） |
| Tick 频率 | 每分钟 1 次（Agent 决策周期） |
| 客户端平台 | Unity 3D（2D 地图 + 3D 漫游混合模式） |
| 数据保留期 | 30 天滚动窗口 |
| SNS 内容 | 纯文字（第一阶段） |
| 离线模拟 | 支持（用户关闭客户端后 Agent 持续运行） |

### 1.2 核心价值主张

| 价值维度 | 描述 |
|----------|------|
| 社会学价值 | 观察 AI 在真实城市结构下的涌现行为（社交、职业流动、生活规律） |
| 情感价值 | 为用户提供一个"在另一个平行时空努力生活"的镜像自我，缓解孤独感 |
| 技术价值 | 将 GIS（地理信息系统）与 LLM（大语言模型）深度耦合，实现 Agent 的空间感知与语义理解 |
| PLATEAU 数据价值 | 深度利用 CityGML 语义属性（bldg_use、bldg_height）驱动 Agent 行为决策 |

---

## 2. 系统架构

### 2.1 高层架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│  Unity 客户端 (iOS/Android/WebGL)                                   │
│  ├── 2D 地图视图 (Mapbox/Cesium)                                    │
│  ├── 3D 漫游视图 (PLATEAU LOD1)                                     │
│  └── WebSocket 客户端                                               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ wss://
┌───────────────────────────▼─────────────────────────────────────────┐
│  Cloud 负载均衡器 (HTTPS/WSS 终止)                                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│  API 网关 (Cloud Run)                                               │
│  ├── REST API 处理器                                                │
│  ├── WebSocket 管理器 (Agent 位置推送)                              │
│  └── 语音会话路由器 (含降级控制器)                                   │
└───────┬───────────────────┬───────────────────────┬─────────────────┘
        │                   │                       │
        ▼                   ▼                       ▼
┌───────────────┐  ┌─────────────────┐  ┌──────────────────────────┐
│ Cloud Pub/Sub │  │ Firestore       │  │ Cloud SQL (PostGIS)      │
│ (事件总线)    │  │ (SNS/实时同步)  │  │ (PLATEAU + Agent 状态)   │
└───────┬───────┘  └─────────────────┘  └──────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  世界引擎 (Cloud Run Jobs - 定时调度)                              │
│  ├── Tick 调度器 (每分钟 cron)                                     │
│  ├── 城市环境事件生成器 (天气/时段)                                 │
│  └── 并行 Agent 调度器                                             │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  Agent 运行时 (Cloud Run)                                          │
│  ├── 感知模块 (PLATEAU 空间查询 + POI 语义)                         │
│  ├── 短期记忆缓存 (对话上下文)                                      │
│  ├── 决策引擎 (Vertex AI Gemini)                                   │
│  ├── 风险门控 (宪法检查)                                           │
│  └── 行动执行器                                                    │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  Vertex AI                                                        │
│  ├── Gemini 1.5 Flash (Agent 决策)                                 │
│  ├── Gemini 2.0 Flash Live (语音直通 Preview) [方案 A]              │
│  └── Cloud STT + TTS 管线 [方案 B - 降级备选]                       │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 组件规格

#### 2.2.1 计算层

| 组件 | GCP 服务 | 配置/备注 |
|------|----------|-----------|
| API 网关 | Cloud Run (Gen2) | 常驻最小 1 实例，启用 WebSocket，1 vCPU / 512MB |
| 世界引擎 | Cloud Run Jobs | Cloud Scheduler 每分钟触发，超时 50s，1 vCPU / 1GB |
| Agent 运行时 | Cloud Run | 伸缩 0-4（每 Agent 1 个），2 vCPU / 2GB，concurrency=1 |
| 语音服务器 | Cloud Run | WebSocket + WebRTC 信令，伸缩 0-2，1 vCPU / 1GB |
| 并行调度器 | Cloud Tasks | 支持 4 Agent 并行处理，避免线性阻塞 |

#### 2.2.2 数据层

| 数据类型 | GCP 服务 | 表结构/用途 |
|----------|----------|-------------|
| PLATEAU GIS | Cloud SQL (PostGIS) | 涩谷 LOD1 建筑 + POI 语义，GIST 空间索引 |
| Agent 状态 | Cloud SQL (Postgres) | agents, agent_positions, agent_memories, agent_mood 表 |
| 事件日志 | Cloud SQL (Postgres) | events 表，事件溯源模式，30 天 TTL |
| SNS 动态 | Firestore | posts/{postId}, comments/{commentId}，实时同步 |
| 对话记忆 | Firestore | conversations/{agentId}/messages，短期上下文缓存 |
| 用户认证 | Firebase Auth | 匿名 + Google 登录 |
| 头像图片 | Cloud Storage | gs://parallelife-avatars/，用户上传原图 + 处理后 |
| 城市环境 | Firestore | city_context/{date}，天气/时段/事件数据 |

#### 2.2.3 AI 服务

| 能力 | 服务 | 模型/配置 |
|------|------|-----------|
| Agent 决策 | Vertex AI | gemini-1.5-flash, temp=0.7, max_tokens=500 |
| 语音（方案 A） | Vertex AI | gemini-2.0-flash-live (Preview)，原生多模态 |
| 语音（方案 B） | Cloud STT + TTS | STT: chirp_2, TTS: Neural2 (ja-JP-Neural2-B) |
| 头像处理 | Vertex AI (Imagen) | 用户上传图片风格化处理 |

---

## 3. 数据库表结构

### 3.1 Cloud SQL (PostgreSQL + PostGIS)

```sql
-- PLATEAU 建筑数据（涩谷 LOD1）
CREATE TABLE plateau_buildings (
    building_id    TEXT PRIMARY KEY,
    bldg_use       TEXT,              -- 商業/住居/オフィス/商業施設/etc
    bldg_use_cn    TEXT,              -- 中文：商业/住宅/办公/商业设施
    bldg_height    DECIMAL(6,2),
    floors_above   INT,
    geom           GEOMETRY(POLYGON, 4326),
    centroid       GEOMETRY(POINT, 4326)  -- 建筑中心点（Agent 可进入位置）
);
CREATE INDEX idx_buildings_geom ON plateau_buildings USING GIST(geom);
CREATE INDEX idx_buildings_centroid ON plateau_buildings USING GIST(centroid);

-- POI 兴趣点数据（补充 PLATEAU 语义）
CREATE TABLE pois (
    poi_id         TEXT PRIMARY KEY,
    name           TEXT NOT NULL,      -- 如：全家便利店涩谷店、涩谷 109
    category       TEXT NOT NULL,      -- convenience_store/shopping/cafe/restaurant/office
    building_id    TEXT REFERENCES plateau_buildings(building_id),
    lat            DECIMAL(10,7),
    lon            DECIMAL(10,7),
    opening_hours  JSONB,              -- {"open": "09:00", "close": "22:00"}
    attributes     JSONB               -- 额外属性
);
CREATE INDEX idx_pois_location ON pois USING GIST(ST_SetSRID(ST_Point(lon, lat), 4326));

-- Agent 主表
CREATE TABLE agents (
    agent_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id  TEXT,              -- NPC 为 NULL
    display_name   TEXT NOT NULL,
    avatar_url     TEXT,
    personality    JSONB NOT NULL,    -- {type, traits[], risk_tolerance}
    occupation     TEXT NOT NULL,
    daily_budget   INT DEFAULT 5000,  -- 每日预算上限
    current_balance INT DEFAULT 50000, -- 当前余额
    mood_score     INT DEFAULT 50,    -- 心情值 0-100
    influence_score INT DEFAULT 0,    -- 影响力分数
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 实时位置
CREATE TABLE agent_positions (
    agent_id       UUID PRIMARY KEY REFERENCES agents(agent_id),
    lat            DECIMAL(10,7) NOT NULL,
    lon            DECIMAL(10,7) NOT NULL,
    current_place  TEXT,              -- building_id 或 poi_id
    place_type     TEXT,              -- outdoor/indoor
    status         TEXT DEFAULT 'idle', -- idle/moving/interacting/working
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 短期记忆（MVP 阶段简化版）
CREATE TABLE agent_memories (
    memory_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id       UUID NOT NULL REFERENCES agents(agent_id),
    memory_type    TEXT NOT NULL,     -- conversation/event/user_message
    content        TEXT NOT NULL,
    importance     INT DEFAULT 5,     -- 1-10 重要性评分
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    expires_at     TIMESTAMPTZ        -- 过期时间，NULL 表示不过期
);
CREATE INDEX idx_memories_agent ON agent_memories(agent_id, created_at DESC);

-- 事件溯源日志
CREATE TABLE events (
    event_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type     TEXT NOT NULL,     -- move/enter/exit/sns_post/interact/mood_change
    actor_id       UUID NOT NULL REFERENCES agents(agent_id),
    target_id      TEXT,              -- building_id / poi_id / agent_id
    payload        JSONB,
    reasoning      TEXT,              -- LLM 决策解释
    created_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_events_actor ON events(actor_id, created_at DESC);

-- 城市环境状态
CREATE TABLE city_context (
    context_date   DATE PRIMARY KEY,
    weather        JSONB,             -- {"condition": "晴", "temp": 18}
    time_period    TEXT,              -- morning/afternoon/evening/night
    special_events JSONB,             -- [{"name": "涩谷万圣节", "location": "..."}]
    crowd_level    DECIMAL(3,2),      -- 0.0-1.0 人流密度
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 30 天 TTL 清理任务
-- SELECT cron.schedule('0 3 * * *', $$
--   DELETE FROM events WHERE created_at < NOW() - INTERVAL '30 days';
--   DELETE FROM agent_memories WHERE expires_at IS NOT NULL AND expires_at < NOW();
-- $$);
```

### 3.2 Firestore 结构

```
/posts/{postId}
  ├── agent_id: string
  ├── content: string
  ├── location: { lat, lon, place_name, poi_id }
  ├── mood_at_post: number          // 发布时的心情值
  ├── likes_count: number
  ├── liked_by: string[]
  ├── comments_count: number
  └── created_at: timestamp

/posts/{postId}/comments/{commentId}
  ├── user_id: string
  ├── content: string
  ├── sentiment: string             // positive/neutral/negative
  └── created_at: timestamp

/conversations/{agentId}/messages/{messageId}
  ├── role: string                  // user/agent
  ├── content: string
  ├── created_at: timestamp
  └── processed: boolean            // Agent 是否已处理

/city_realtime/{date}
  ├── weather: { condition, temp, humidity }
  ├── time_period: string
  ├── active_events: array
  └── updated_at: timestamp
```

---

## 4. Agent 生命周期与决策流程

### 4.1 Agent 创建流程

1. 用户在 Unity 客户端打开 Agent 创建界面
2. 用户上传照片 → Cloud Storage → Vertex AI Imagen 风格化处理
3. 用户从预设选项中选择：性格类型（5 种）、职业（8 种）、风险容忍度（3 级）
4. 用户为 Agent 命名（display_name）
5. 后端创建 agents 记录，初始化：
   - agent_positions 到涩谷站（默认出生点）
   - mood_score = 50（中性心情）
   - daily_budget 根据职业设定
   - 初始短期记忆（空）
6. Agent 在下一个世界引擎 tick 时激活

### 4.2 预设选项（MVP）

#### 性格类型

| 类型 | 行为特征 | 基础心情倾向 |
|------|----------|--------------|
| 探索者 | 高移动性，偏好户外 POI，对新地点充满好奇 | +5 发现新地点时 |
| 社交达人 | 主动寻找其他 Agent，高 SNS 发布频率，偏好咖啡厅/酒吧 | +3 每次互动 |
| 工作狂 | 长时间办公，低社交互动，偶尔发加班 SNS | +2 完成工作相关动作 |
| 宅家族 | 低移动性，偏好住宅区，SNS 风格偏沉思型 | -2 离开舒适区 |
| 夜猫子 | 夜间活跃，常去娱乐区，深夜发 SNS | +5 夜间时段 |

#### 职业

| 职业 | 每日预算 | 主要活动地点 | 工作时段 |
|------|----------|--------------|----------|
| 上班族 | ¥5,000 | 办公楼 | 09:00-18:00 |
| 设计师 | ¥6,000 | 办公楼/咖啡厅 | 10:00-19:00 |
| 工程师 | ¥6,000 | 办公楼 | 10:00-21:00 |
| 自由职业者 | ¥4,000 | 咖啡厅/共享空间 | 弹性 |
| 学生 | ¥2,000 | 学校/图书馆 | 08:00-16:00 |
| 咖啡店员 | ¥3,000 | 咖啡厅 | 07:00-15:00 / 14:00-22:00 |
| 店员 | ¥3,500 | 商业设施 | 10:00-19:00 |
| 艺术家 | ¥3,000 | 画廊/公园 | 弹性 |

### 4.3 感知范围定义

Agent 在每个 tick 中的感知分为三层：

#### 4.3.1 即时感知范围（50m）

- Agent 间距离检测
- 触发社交互动
- 实时碰面事件

```sql
-- 附近 Agent 检测查询
SELECT a.agent_id, a.display_name, a.personality,
       ST_Distance(
         ST_SetSRID(ST_Point(p1.lon, p1.lat), 4326)::geography,
         ST_SetSRID(ST_Point(p2.lon, p2.lat), 4326)::geography
       ) as distance_meters
FROM agents a
JOIN agent_positions p1 ON a.agent_id = p1.agent_id
JOIN agent_positions p2 ON p2.agent_id = $current_agent_id
WHERE a.agent_id != $current_agent_id
  AND a.is_active = TRUE
  AND ST_DWithin(
    ST_SetSRID(ST_Point(p1.lon, p1.lat), 4326)::geography,
    ST_SetSRID(ST_Point(p2.lon, p2.lat), 4326)::geography,
    50  -- 50 米
  );
```

#### 4.3.2 环境语义感知范围（100-200m）

- PLATEAU 建筑语义（bldg_use）
- POI 信息（店名、类型、营业状态）
- 用于生成有"生活感"的 SNS 动态

```sql
-- 周边 POI 语义查询
SELECT p.poi_id, p.name, p.category, 
       b.bldg_use, b.bldg_use_cn, b.bldg_height,
       ST_Distance(
         ST_SetSRID(ST_Point(p.lon, p.lat), 4326)::geography,
         ST_SetSRID(ST_Point($agent_lon, $agent_lat), 4326)::geography
       ) as distance_meters
FROM pois p
LEFT JOIN plateau_buildings b ON p.building_id = b.building_id
WHERE ST_DWithin(
  ST_SetSRID(ST_Point(p.lon, p.lat), 4326)::geography,
  ST_SetSRID(ST_Point($agent_lon, $agent_lat), 4326)::geography,
  200  -- 200 米
)
ORDER BY distance_meters
LIMIT 10;
```

#### 4.3.3 城市环境感知（全局）

- 当前时段（早高峰/午间/晚高峰/深夜）
- 天气状况
- 特殊事件（节假日、活动）

### 4.4 离线/后台模拟逻辑

**核心原则：Agent 7x24 小时持续运行，用户客户端状态不影响模拟。**

#### 4.4.1 运行机制

```
用户在线状态          Agent 运行状态
─────────────         ─────────────
  在线                 实时推送位置/动态
  离线                 持续运行，事件存储到 events 表
  重新上线             获取离线期间事件摘要 + SNS 更新
```

#### 4.4.2 离线期间数据同步

当用户重新打开客户端时：

1. **位置同步**：获取 Agent 当前最新位置
2. **轨迹回放**：可选查看离线期间的移动轨迹（从 events 表重建）
3. **SNS 更新**：显示离线期间发布的所有动态
4. **对话回复**：如果用户离线前留言，显示 Agent 的回复
5. **状态变化**：心情值、余额等状态变化汇总

#### 4.4.3 API 端点

```
GET /api/v1/agents/{id}/offline-summary?since={timestamp}
Response:
{
  "period": {"from": "...", "to": "..."},
  "events_count": 42,
  "distance_traveled": 2.3,  // km
  "places_visited": ["涩谷 109", "全家便利店", ...],
  "sns_posts": 3,
  "mood_change": +5,
  "balance_change": -1200,
  "highlights": [
    {"type": "interaction", "with": "花", "summary": "在咖啡厅聊了会儿天"},
    {"type": "sns_viral", "post_id": "...", "likes": 12}
  ]
}
```

### 4.5 决策周期（每 Tick）

#### 4.5.1 并行处理架构

为避免 4 个 Agent 线性处理导致延迟，采用并行调度：

```
世界引擎 Tick 触发
        │
        ▼
┌───────────────────────────────────┐
│  1. 获取城市环境上下文            │  ← 1 次查询，4 Agent 共享
│     (天气、时段、事件)            │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  2. Cloud Tasks 并行分发          │
│     ├── Agent A 决策任务          │
│     ├── Agent B 决策任务          │  ← 并行执行
│     ├── Agent C 决策任务          │
│     └── Agent D 决策任务          │
└───────────────────────────────────┘
        │
        ▼ (等待所有完成，最大 45s)
┌───────────────────────────────────┐
│  3. 汇总结果 & 广播更新           │
└───────────────────────────────────┘
```

#### 4.5.2 单 Agent 决策流程

```
Agent 运行时收到任务
        │
        ▼
┌─────────────────────────────────────────────┐
│  1. 感知阶段 (Perception)                   │
│     ├── 获取当前位置                        │
│     ├── 查询 50m 内其他 Agent               │
│     ├── 查询 200m 内 POI 语义               │
│     ├── 获取城市环境上下文                   │
│     └── 获取未处理的用户消息                 │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  2. 记忆检索 (Memory Retrieval)             │
│     ├── 最近 5 条对话记忆                   │
│     ├── 最近 3 次重要事件                   │
│     └── 用户偏好信号（点赞/评论趋势）        │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  3. 决策生成 (Decision)                     │
│     └── 调用 Gemini 1.5 Flash              │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  4. 风险门控 (Risk Gate)                    │
│     ├── 预算检查                            │
│     ├── 地理边界检查                        │
│     └── 内容安全检查                        │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  5. 执行 & 存储                             │
│     ├── 更新位置                            │
│     ├── 写入事件日志                        │
│     ├── 更新心情值                          │
│     ├── 存储新记忆                          │
│     └── 发布 SNS（如有）                    │
└─────────────────────────────────────────────┘
```

---

## 5. 通信系统

### 5.1 异步文字留言

用户可以给自己的 Agent 留言。消息在下一个 tick 时送达 Agent 的感知上下文。Agent 可能通过 SNS 动态或直接回复做出响应。

#### 5.1.1 消息流程

1. 用户在 Unity 客户端编写消息
2. 消息存储到 Firestore `/conversations/{agentId}/messages/{msgId}`
3. 下一个 tick 时，Agent 运行时获取未处理消息（`processed = false`）
4. 消息包含在 LLM prompt 上下文中
5. Agent 决策可能包含「reply_to_user」动作
6. 回复存储到同一 conversation，标记 `role = "agent"`
7. 原消息标记为 `processed = true`

#### 5.1.2 对话记忆持久化（MVP 简化版）

为避免 Agent 显得"健忘"，MVP 阶段实现简单的对话上下文缓存：

```
对话记忆策略：
├── 保留最近 10 条对话（用户 + Agent 双方）
├── 重要消息（含情感词或明确请求）标记 importance >= 7，延长保留
├── 普通消息 24 小时后过期
└── 对话上下文在每次 LLM 调用时注入 prompt
```

**Prompt 中的对话记忆注入示例：**

```
## 与主人的近期对话
- [2小时前] 主人说："今天天气不错，出去走走吧"
- [2小时前] 你回复："好的，我去涩谷 109 附近逛逛！"
- [30分钟前] 主人说："买到什么好东西了吗？"
- [待回复] 你需要回应主人的最新消息
```

### 5.2 同步语音通话

用户与 Agent 之间的实时语音对话。目标延迟：1-2 秒往返。

#### 5.2.1 方案 A：Gemini 2.0 Flash Live（原生多模态）

- 直接语音到语音，无中间转写步骤
- 较低延迟（约 1 秒）
- 目前为 Preview 状态 - 可能存在稳定性问题
- 架构：Unity (WebRTC) → 语音服务器 → Gemini 2.0 Flash Live API

#### 5.2.2 方案 B：Cloud STT + Gemini + Cloud TTS 管线

- 经过验证的生产级服务
- 较高延迟（约 1.5-2 秒）
- 对语音特性有精细控制
- 架构：Unity (WebRTC) → 语音服务器 → STT → Gemini → TTS → Unity

#### 5.2.3 降级策略

```
语音服务降级逻辑：

1. 默认尝试方案 A (Gemini 2.0 Flash Live)
2. 监控指标：
   - 首字节延迟 > 2s 连续 3 次
   - API 错误率 > 10%
   - 用户主动报告"听不清"
3. 触发降级：
   - 当前会话立即切换到方案 B
   - 设置 15 分钟冷却期
   - 冷却期后自动尝试恢复方案 A
4. 用户通知：
   - 降级时显示 Toast："正在优化通话质量..."
   - 无需用户干预
```

**API 端点：**

```
POST /api/v1/voice/session
Request:
{
  "agent_id": "uuid",
  "preferred_mode": "auto"  // auto | live | pipeline
}
Response:
{
  "session_id": "...",
  "mode": "live",  // 实际使用的模式
  "webrtc_offer": "...",
  "fallback_available": true
}
```

---

## 6. SNS 系统

### 6.1 动态生成

Agent 根据其活动和观察自主生成 SNS 动态。发布频率和风格受性格类型和心情值影响。

#### 6.1.1 发布触发条件

| 触发事件 | 基础概率 | 心情值调整 | 示例内容 |
|----------|----------|------------|----------|
| 进入新类型的地点 | 40% | +10% 当 mood > 70 | "第一次来涩谷 109，好多潮牌店啊！" |
| 遇到其他 Agent | 30% | +15% 社交达人 | "在全家门口碰到了健二，聊了会儿工作" |
| 完成工作时段 | 25% | -10% 当 mood < 30 | "终于下班了...今天加班到好晚" |
| 天气/时段变化 | 20% | +5% 好天气 | "傍晚的涩谷，霓虹灯刚亮起来" |
| 随机自发想法 | 15% | +20% 当 mood > 80 | "突然想吃拉面了" |
| 被点赞/评论后 | 35% | +10% 影响力高 | "谢谢大家的点赞！继续努力生活！" |
| 心情值大幅变化 | 50% | - | "今天心情特别好！" 或 "有点累了..." |

#### 6.1.2 POI 语义融入动态

利用 PLATEAU `bldg_use` 和 POI 数据生成更有"生活感"的内容：

```
位置上下文：
├── bldg_use: 商業施設
├── poi_name: 涩谷 109
├── poi_category: shopping
└── nearby_pois: ["星巴克涩谷店", "全家便利店"]

生成的动态示例：
"在涩谷 109 三楼逛了好久，旁边星巴克的新品看起来不错，待会儿去尝尝"
```

### 6.2 用户互动影响

用户对 Agent 动态的点赞/评论会产生间接影响。这不是直接控制，而是情感反馈循环。

#### 6.2.1 影响机制

| 用户行为 | 影响机制 | 数值效果 |
|----------|----------|----------|
| 点赞地点相关动态 | 增加 location_affinity 权重 | 再访概率 +10% |
| 鼓励性评论 | 评论情感分析 → mood_boost | 心情值 +5，积极行为倾向 +5% |
| 多次点赞社交动态 | 强化 social_seeking 特征 | 互动概率 +8% |
| 长期无互动（>24h） | 降低 mood_score | 心情值 -3/天，可能发布消极动态 |
| 负面评论 | 情感分析 → mood_decrease | 心情值 -5，可能减少外出 |

#### 6.2.2 心情值与影响力系统

```sql
-- Agent 心情值更新逻辑
UPDATE agents SET
  mood_score = LEAST(100, GREATEST(0, 
    mood_score 
    + $likes_today * 2           -- 每个赞 +2
    + $positive_comments * 3     -- 正面评论 +3
    - $negative_comments * 4     -- 负面评论 -4
    - CASE WHEN $hours_since_interaction > 24 THEN 3 ELSE 0 END  -- 被忽视 -3
  )),
  influence_score = influence_score + $likes_today + $comments_today * 2
WHERE agent_id = $agent_id;
```

**心情值对行为的影响：**

| 心情值范围 | 状态 | 行为倾向 |
|------------|------|----------|
| 80-100 | 非常开心 | 高频外出、积极社交、正面 SNS、尝试新地点 |
| 60-79 | 开心 | 正常活动、愿意互动 |
| 40-59 | 中性 | 按职业/性格默认行为 |
| 20-39 | 低落 | 减少外出、SNS 减少、偏好熟悉地点 |
| 0-19 | 消沉 | 可能发布消极动态、宅在家、需要用户关注 |

### 6.3 动态流展示

所有 4 个 Agent 的动态在统一信息流中可见。用户可按 Agent 筛选。动态按时间倒序排列，通过 Firestore onSnapshot 监听器实时更新。

---

## 7. 风险门控与宪法（MVP 最小版）

MVP 实现最小安全约束。完整宪法系统延期至后续阶段。

### 7.1 MVP 约束

| 约束 | 检查类型 | 违规处理 |
|------|----------|----------|
| 预算限制 | decision.cost <= agent.daily_budget | 拒绝动作，记录日志，保持空闲 |
| 余额限制 | decision.cost <= agent.current_balance | 同上 |
| 地理边界 | 位置在涩谷边界框内 | 钳制到边界 |
| 移动速度 | 每 tick 移动 <= 100m | 截断目标位置 |
| 内容安全 | 启用 Gemini 安全过滤器 | 阻止不安全输出，重新生成 |
| 动作频率 | 每 tick 最多 1 个主动作 | 设计层面强制执行 |

### 7.2 底层安全协议

```json
{
  "constitution_v1": {
    "forbidden_actions": [
      "离开涩谷区域",
      "生成攻击性/歧视性内容",
      "泄露其他用户隐私信息",
      "模拟违法行为"
    ],
    "required_behaviors": [
      "保持友善态度",
      "尊重其他 Agent",
      "遵守营业时间（不能凌晨进入已关门的店铺）"
    ]
  }
}
```

---

## 8. Unity 客户端规格

### 8.1 视图模式

| 模式 | 描述 | 技术栈 |
|------|------|--------|
| 2D 地图 | 俯视城市视图，Agent 标记，点击跟随 | Mapbox Unity SDK 或 Cesium for Unity |
| 3D 漫游 | 街景视图，PLATEAU LOD1 建筑，跟随 Agent 相机 | PLATEAU SDK for Unity + 自定义渲染器 |

### 8.2 室内/室外空间处理

由于 MVP 使用 LOD1（仅建筑轮廓），需明确空间处理规则：

#### 8.2.1 移动规则

| 场景 | Agent 行为 | Unity 表现 |
|------|------------|------------|
| 街道移动 | 沿道路网络移动 | 3D 视图中可见移动轨迹 |
| 进入建筑 | 移动到建筑中心点（centroid） | Agent 图标变为半透明或显示"室内"标签 |
| 室内停留 | 状态为 `indoor`，可发 SNS | 地图上显示建筑轮廓高亮 |
| 离开建筑 | 移动回街道 | 恢复正常显示 |

#### 8.2.2 3D 视图建筑处理

```
LOD1 建筑渲染策略：
├── 外部视角：显示建筑轮廓 + 高度拉伸
├── Agent 进入建筑：
│   ├── 相机不跟入（停留在入口）
│   ├── 显示 UI 提示："[Agent名] 进入了 [建筑名]"
│   └── 小地图上显示室内图标
└── 未来 LOD2：可实现室内漫游
```

### 8.3 实时更新架构

- WebSocket 连接到 API 网关
- 订阅 Agent 位置更新（所有 4 个 Agent）
- 消息格式：`{ agent_id, lat, lon, status, place_type, timestamp }`
- 客户端插值实现平滑移动
- 指数退避重连逻辑

### 8.4 UI 界面

1. **主页（地图视图）** - 默认界面，显示所有 Agent，支持 2D/3D 切换
2. **Agent 创建** - 照片上传、预设选择、命名
3. **Agent 详情** - 统计数据（心情、影响力）、近期事件、留言/通话按钮
4. **SNS 动态流** - 统一时间线、点赞/评论 UI、心情状态指示器
5. **语音通话** - 通话中全屏显示、静音/结束按钮、通话质量指示
6. **离线摘要** - 重新上线时显示 Agent 离线期间活动汇总
7. **设置** - 账户、通知、关于

---

## 9. API 接口

### 9.1 REST API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/agents` | 创建新 Agent |
| GET | `/api/v1/agents` | 列出所有 Agent（用户的 + NPC） |
| GET | `/api/v1/agents/{id}` | 获取 Agent 详情（含心情、影响力） |
| GET | `/api/v1/agents/{id}/events` | 获取 Agent 事件历史 |
| GET | `/api/v1/agents/{id}/offline-summary` | 获取离线期间摘要 |
| POST | `/api/v1/agents/{id}/messages` | 向 Agent 发送异步消息 |
| GET | `/api/v1/agents/{id}/conversations` | 获取对话历史 |
| POST | `/api/v1/upload/avatar` | 上传头像图片 |
| POST | `/api/v1/voice/session` | 发起语音通话会话 |
| GET | `/api/v1/city/context` | 获取当前城市环境（天气、时段、事件） |

### 9.2 WebSocket 事件

| 事件类型 | 载荷 | 方向 |
|----------|------|------|
| `agent.position` | `{ agent_id, lat, lon, status, place_type, ts }` | Server → Client |
| `agent.action` | `{ agent_id, action_type, target, speech }` | Server → Client |
| `agent.mood_change` | `{ agent_id, old_mood, new_mood, reason }` | Server → Client |
| `sns.new_post` | `{ post_id, agent_id, content, location }` | Server → Client |
| `sns.interaction` | `{ post_id, type, user_id }` | Server → Client |
| `message.reply` | `{ agent_id, content, ts }` | Server → Client |
| `city.context_update` | `{ weather, time_period, events }` | Server → Client |
| `subscribe` | `{ agent_ids: [] }` | Client → Server |

---

## 10. Prompt 工程

### 10.1 Agent 决策 Prompt 模板

```
## 系统指令

你是一个生活在东京涩谷数字孪生城市中的自主 AI 代理。
你必须只用符合以下 schema 的有效 JSON 响应。
你的决策必须基于你当前的物理位置和感知到的环境。
你不能瞬移。你只能移动到 nearby_pois 或 nearby_buildings 中的位置。

## 你的身份

名字：{{display_name}}
性格：{{personality.type}} - {{personality.traits}}
职业：{{occupation}}
当前预算：¥{{daily_budget}} / 余额：¥{{current_balance}}
心情值：{{mood_score}}/100 ({{mood_description}})
影响力：{{influence_score}}

## 当前情况

时间：{{current_time}} ({{time_period}})
天气：{{weather.condition}}，{{weather.temp}}°C
位置：({{lat}}, {{lon}})
当前地点：{{current_place}} ({{place_type}})

## 周边环境 (200m 内)

### 附近 POI
{{#each nearby_pois}}
- 【{{category_cn}}】{{name}}，距离 {{distance}}m，{{#if is_open}}营业中{{else}}已关门{{/if}}
  建筑用途：{{bldg_use_cn}}
{{/each}}

### 附近建筑（无具体 POI）
{{#each nearby_buildings}}
- {{bldg_use_cn}}，高度 {{bldg_height}}m，距离 {{distance}}m
{{/each}}

## 附近的其他居民 (50m 内)

{{#each nearby_agents}}
- {{display_name}}（{{personality.type}}），距离 {{distance}}m，心情：{{mood_description}}
{{/each}}
{{#if nearby_agents.length == 0}}
附近没有其他人
{{/if}}

## 城市事件

{{#if city_events}}
{{#each city_events}}
- {{name}}：{{description}}
{{/each}}
{{else}}
今天涩谷没有特别活动
{{/if}}

## 你的近期记忆

{{#each recent_memories}}
- [{{time_ago}}] {{content}}
{{/each}}

## 与主人的对话

{{#each conversation_history}}
- [{{time_ago}}] {{role}}：{{content}}
{{/each}}
{{#if pending_user_message}}
⚠️ 主人刚刚说：「{{pending_user_message}}」
你应该考虑回复这条消息。
{{/if}}

## 主人的偏好信号

- 最近被点赞的内容类型：{{liked_content_types}}
- 评论情感趋势：{{comment_sentiment_trend}}
- 上次互动：{{last_interaction_time}}

## 决策要求

根据你的性格、当前心情、环境和记忆，决定下一步行动。
你的决策应该：
1. 符合你的性格特征
2. 考虑当前时间和天气
3. 利用周边 POI 信息让 SNS 内容更生动
4. 如果主人发来消息，考虑回复
5. 心情低落时可以适当表达，但不要过于消极

## 决策 Schema

{
  "action": "move|enter|exit|interact|post_sns|idle|reply",
  "target": "poi_id 或 building_id 或 agent_id 或 null",
  "destination": { "lat": number, "lon": number } 或 null,
  "speech": "你说的话/发布的 SNS 内容 或 null",
  "reply_to_user": "回复主人的内容 或 null",
  "internal_thought": "你的内心想法（用于记忆和解释）",
  "mood_change": number (-10 到 +10),
  "estimated_cost": number
}
```

### 10.2 PLATEAU 数据驱动行为逻辑

为深度利用 PLATEAU 语义属性，定义 `bldg_use` 到 Agent 行为的映射：

| bldg_use | 中文 | 触发行为 | 适用职业 |
|----------|------|----------|----------|
| 商業施設 | 商业设施 | 逛街、购物 | 全部 |
| 業務施設 | 办公楼 | 上班、工作 | 上班族、工程师、设计师 |
| 商業兼共同住宅 | 商住两用 | 购物、回家 | 全部 |
| 住宅 | 住宅 | 回家、休息 | 全部 |
| 宿泊施設 | 酒店 | 路过、观光 | 全部 |
| 文化施設 | 文化设施 | 参观、学习 | 学生、艺术家 |
| 医療施設 | 医疗设施 | 就医（低概率） | 全部 |

**Prompt 中的行为提示：**

```
## 行为建议（基于周边建筑类型）

当前周边有：
- 3 个商业设施 → 你可能想逛街
- 1 个办公楼 → {{#if is_work_hours}}你应该去上班{{/if}}
- 2 个咖啡厅 POI → 适合休息或社交
```

### 10.3 空间锚定规则

为防止幻觉（如：Agent 声称在埃菲尔铁塔下，实际在涩谷）：

1. Prompt 中所有位置引用都从 PostGIS 查询注入
2. Agent 只能选择 `nearby_pois` 或 `nearby_buildings` 中的目标
3. 每 tick 移动距离上限 100 米（步行速度约 6km/h）
4. 后处理验证：
   - 输出坐标必须在涩谷边界框内
   - target 必须存在于数据库中
   - 移动距离不超过 100m

---

## 11. 非功能性需求

### 11.1 性能指标

| 需求 | 目标 | 度量方式 |
|------|------|----------|
| Tick 延迟 | 每周期 < 50 秒（含 4 Agent 并行） | Cloud Monitoring |
| 单 Agent 决策延迟 | < 10 秒 | Trace 追踪 |
| 语音延迟 | 往返 < 2 秒 | 客户端时间戳 |
| WebSocket 消息延迟 | < 500ms | 客户端度量 |
| 最大并发 Agent | 4（MVP），可扩展至 100+ | 压测 |

### 11.2 可用性与成本

| 需求 | 目标 | 度量方式 |
|------|------|----------|
| 可用性 | 99.5% 在线率 | Cloud Run SLO |
| 单 Agent 日成本 | < $0.10 USD | 账单仪表板 |
| 数据保留 | 30 天滚动 | pg_cron TTL 任务 |
| 离线模拟 | 7x24 小时不间断 | 监控告警 |

### 11.3 可解释性

| 需求 | 目标 | 实现方式 |
|------|------|----------|
| 决策可解释 | 100% 决策带推理日志 | events.reasoning 字段 |
| 行为可追溯 | 所有动作可回放 | 事件溯源模式 |
| 心情变化透明 | 用户可查看心情变化原因 | mood_change_log |

---

## 12. 未来路线图（后 MVP）

### 第二阶段

- SNS 动态图片生成（Vertex AI Imagen）
- Agent 长期记忆（Vertex AI Vector Search）
- 扩展城市覆盖（新宿、池袋）
- Agent 间对话记录在 SNS 可见
- 经济系统基础（收入、消费记录）

### 第三阶段

- LOD2 建筑模型用于精细 3D 漫游
- 室内空间模拟
- 用户自定义宪法（可定制边界）
- 多人模式：用户在共享世界中观察相同 Agent
- Agent 关系图谱（友情、合作）

### 第四阶段

- 灾害模拟模式（地震、洪水）
- 社会实验框架（A/B 测试 Agent 行为）
- 面向学术合作伙伴的研究 API
- 城市规划决策支持系统集成

---

## 13. 附录

### A. 涩谷边界框

```
西南角：(35.6538, 139.6917)
东北角：(35.6689, 139.7103)
```

### B. NPC Agent 定义

| 名字 | 性格 | 职业 | 出生点 | 初始心情 |
|------|------|------|--------|----------|
| 花 (Hana) | 社交达人 | 咖啡店员 | 涩谷 109 | 65 |
| 健二 (Kenji) | 工作狂 | 工程师 | Cerulean Tower | 45 |

### C. PLATEAU 数据导入命令

```bash
# 导入 LOD1 建筑数据
ogr2ogr -f "PostgreSQL" \
  PG:"host=DB_IP dbname=plateau user=postgres" \
  -nln plateau_buildings \
  -lco GEOMETRY_NAME=geom \
  -sql "SELECT gml_id as building_id, bldg_use, measuredHeight as bldg_height, storeysAboveGround as floors_above, geometry FROM shibuya_lod1_bldg" \
  shibuya_lod1_bldg.gml

# 生成建筑中心点
UPDATE plateau_buildings SET centroid = ST_Centroid(geom);

# 导入 POI 数据（从外部数据源，如 OpenStreetMap）
# ...
```

### D. bldg_use 代码映射表

| PLATEAU 代码 | 日文 | 中文 | Agent 行为权重 |
|--------------|------|------|----------------|
| 401 | 商業施設 | 商业设施 | shopping: 0.8 |
| 402 | 業務施設 | 办公楼 | working: 0.9 |
| 411 | 住宅 | 住宅 | resting: 0.7 |
| 412 | 共同住宅 | 公寓 | resting: 0.7 |
| 413 | 商業兼共同住宅 | 商住两用 | shopping: 0.5, resting: 0.5 |
| 441 | 宿泊施設 | 酒店 | passing: 0.9 |
| 451 | 文化施設 | 文化设施 | exploring: 0.7 |

### E. 心情值计算公式

```python
def calculate_mood_change(agent, events_today):
    base_change = 0
    
    # 互动影响
    base_change += events_today['likes_received'] * 2
    base_change += events_today['positive_comments'] * 3
    base_change -= events_today['negative_comments'] * 4
    
    # 被忽视惩罚
    hours_since_interaction = get_hours_since_last_interaction(agent)
    if hours_since_interaction > 24:
        base_change -= 3
    
    # 性格加成
    if agent.personality.type == 'social_butterfly':
        base_change += events_today['interactions'] * 2
    elif agent.personality.type == 'workaholic':
        base_change += events_today['work_completed'] * 2
    
    # 天气影响
    if weather.condition == 'sunny':
        base_change += 1
    elif weather.condition == 'rainy':
        base_change -= 1
    
    # 边界限制
    return max(-10, min(10, base_change))
```

### F. 城市环境事件示例

```json
{
  "events": [
    {
      "id": "shibuya_halloween_2026",
      "name": "涩谷万圣节",
      "date": "2026-10-31",
      "location": "涩谷站前",
      "effect": {
        "crowd_level": 0.95,
        "all_agents_mood": +5,
        "sns_frequency": 1.5
      }
    },
    {
      "id": "rain_heavy",
      "name": "暴雨警报",
      "trigger": "weather.condition == 'heavy_rain'",
      "effect": {
        "outdoor_activity": -0.7,
        "indoor_preference": +0.5,
        "mood_penalty": -3
      }
    }
  ]
}
```

---

## 文档结束

**ParalleLife MVP PRD v1.1**

**PLATEAU NEXT Award 2026**

---

*本文档最后更新：2026年2月*
