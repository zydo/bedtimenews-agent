# 睡前消息智能体

[English](README.md) | [中文](README.zh-CN.md)

睡前消息知识库的智能RAG（检索增强生成）系统。提供具有自动路由、语义搜索和基于引用的准确回答的智能问答服务。

> **立即体验：** [bedtime.blog](https://bedtime.blog)

## 概述

本系统对[睡前消息档案库](https://archive.bedtime.news/)的视频文稿进行索引，并通过LLM驱动的问答实现语义搜索。基于LangGraph、OpenAI embedding模型和PostgreSQL + pgvector构建。

**核心功能：**

- 自动查询路由（RAG路径 vs 直接回答）
- 查询优化与语义搜索
- 基于LLM的文档相关性评分
- 带引用标注的准确回答
- 自动化文档索引与增量更新
- 网页聊天界面

## 内容覆盖

本系统索引来自[bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents)的视频文稿，涵盖多元主题：

1. **国内经济与产业** - 经济政策、产业发展、房地产、地方政府债务
2. **治理与政策** - 政府治理、财政政策、行政改革
3. **社会问题与公民生活** - 教育、医疗、人口问题、社会福利
4. **国际关系与地缘政治** - 中美关系、俄乌冲突、中东局势、印太地区
5. **科技创新** - 人工智能、航天、半导体、自动驾驶
6. **基础设施与工程** - 铁路建设、能源基础设施、城市发展
7. **法律与司法事务** - 企业纠纷、刑事司法、消费者权益保护
8. **体育文化** - 奥运会、电竞、娱乐产业、文化软实力
9. **媒体与信息** - 每日新闻聚合、媒体监管、社交媒体
10. **自然灾害与环境问题** - 地震、洪水、气候变化、环境保护
11. **历史与比较分析** - 历史先例、国际发展模式

**节目目录：**

| 目录          | 节目名称   | 集数（2026年2月） | 主要话题                 |
| ------------- | ---------- | ----------------- | ------------------------ |
| `main/`       | 睡前消息   | 800               | 全面覆盖所有主题         |
| `reference/`  | 参考信息   | 538               | 每日新闻聚合             |
| `business/`   | 产经破壁机 | 81                | 经济、产业、商业、技术   |
| `commercial/` | 讲点黑话   | 61                | 国际关系、地缘政治       |
| `opinion/`    | 高见       | 45                | 技术分析、基础设施、工程 |

## 架构

```plaintext
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Frontend   │ ──────> │     Agent    │ ──────> │   Indexer   │
│ (Chainlit)  │ <────── │  (LangGraph) │         │ (Embedding) │
└─────────────┘         └──────┬───────┘         └─────┬───────┘
                               │                       │
                               ▼                       ▼
                        ┌──────────────────────────────────────┐
                        │        PostgreSQL + pgvector         │
                        │          (Vector Database)           │
                        └──────────────────────────────────────┘
```

**组件说明：**

- **[Frontend](frontend/README.md)**：基于Chainlit的聊天UI
- **[Agent](agent/README.md)**：基于LangGraph的智能RAG服务
- **[Indexer](indexer/README.md)**：自动化文档embedding流水线
- **Database**：PostgreSQL + pgvector扩展的向量数据库

## 快速开始

### 前置要求

- Docker
- OpenAI API密钥

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/zydo/bedtimenews-agent.git
   cd bedtimenews-agent
   ```

2. **配置环境变量**

   复制[`.env.example`](.env.example)到`.env`并配置：

   ```bash
   cp .env.example .env
   # 编辑 .env
   ```

3. **启动所有服务**

   ```bash
   docker compose up -d
   ```

4. **访问界面**

   在浏览器中打开 <http://localhost>

   索引器将在后台自动开始处理文档。

### 验证安装

```bash
# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

## 服务专属文档

- **[Frontend](frontend/README.md)**：UI定制
- **[Agent](agent/README.md)**：API端点、Agentic RAG实现
- **[Indexer](indexer/README.md)**：文档处理

## 数据持久化

文稿embedding数据保存在Docker卷中：

- `bedtimenews-postgres-data`：PostgreSQL数据库

## 项目结构

```plaintext
bedtimenews-agent/
├── agent/              # LangGraph智能RAG服务
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── frontend/           # Chainlit聊天UI
│   ├── app.py
│   ├── Dockerfile
│   └── README.md
├── indexer/            # 文稿embedding流水线
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── storage/            # 数据库初始化脚本
│   └── postgres/
├── docker-compose.yml  # 服务编排
├── .env                # 环境配置（不在git中）
└── README.md           # 本文件
```

## 许可证

MIT
