# 睡前消息智能体

[English](README.md) | [中文](README.zh-CN.md)

睡前消息知识库的智能RAG（检索增强生成）系统。提供具有自动路由、语义搜索和基于引用的准确回答的智能问答服务。

> **立即体验：** [chat.bedtime.blog](https://chat.bedtime.blog)

## 概述

本系统对[睡前消息档案库](https://archive.bedtime.news/)的视频文稿进行索引，并通过LLM驱动的问答实现语义搜索。基于LangGraph、可插拔的 LLM/embedding 提供方（默认使用 DeepSeek 对话模型与 SiliconFlow 的 Qwen3 embedding）以及 PostgreSQL + pgvector 构建。

**核心功能：**

- 自动查询路由（RAG路径 vs 直接回答）
- 查询优化与语义搜索
- 基于LLM的文档相关性评分
- 带引用标注的准确回答
- 自动化文档索引与增量更新
- 网页聊天界面

## 内容覆盖

本系统索引来自[bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents)的视频文稿，涵盖多个节目的多元主题：

**节目目录：**

| 目录          | 节目名称   | 描述                     |
| ------------- | ---------- | ------------------------ |
| `main/`       | 睡前消息   | 全面覆盖所有主题         |
| `reference/`  | 参考信息   | 每日新闻聚合             |
| `business/`   | 产经破壁机 | 经济、产业、商业、技术   |
| `commercial/` | 讲点黑话   | 国际关系、地缘政治       |
| `opinion/`    | 高见       | 技术分析、基础设施、工程 |
| `daily/`      | 每日新闻   | 每日新闻更新             |
| `others/`     | 其它文稿   | 直播问答及其它相关内容   |

**主题分类：**

1. **国内经济与产业** - 经济政策、产业发展、房地产、地方政府债务、城市发展
2. **科技创新** - 人工智能、芯片、半导体、自动驾驶、航天、工程技术
3. **跨境电商与出海** - SHEIN、TikTok、中国制造优势、全球市场
4. **企业治理与监管** - 企业丑闻、审计、金融监管、食品安全、税收监管
5. **国际关系与地缘政治** - 中美关系、俄乌冲突、中东局势、朝鲜半岛、印太地区
6. **社会民生** - 教育、医疗、人口问题、社会福利、城市治理
7. **加密货币与金融科技** - 比特币、区块链、去中心化金融、数字资产
8. **人口与社会政策** - 人口危机、社会化抚养、教育体系、社会福利改革
9. **基础设施与工程** - 铁路建设、能源基础设施、城市发展、公用事业
10. **法律与司法事务** - 企业纠纷、刑事司法、消费者权益保护、监管框架

## 架构

```plaintext
                     ┌─────────────┐
                     │   Browser   │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │    Caddy    │
                     │   (HTTPS)   │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  Chainlit   │
                     │ (Frontend)  │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐      ┌──────────────┐
                     │   Agent     │      │    Indexer   │
                     │ (LangGraph) │      │  (Embedding) │
                     └──────┬──────┘      └──────┬───────┘
                            │                    │
                            ▼                    ▼
                         ┌───────────────────────────┐
                         │  PostgreSQL + pgvector    │
                         │      (Vector DB)          │
                         └───────────────────────────┘
```

**组件说明：**

- **[Caddy](https://caddyserver.com)**：反向代理，自动配置 HTTPS（仅公网部署）
- **[Frontend](frontend/README.md)**：基于 Chainlit 的聊天 UI
- **[Agent](agent/README.md)**：基于 LangGraph 的智能 RAG 服务
- **[Indexer](indexer/README.md)**：自动化文档 embedding 流水线
- **Database**：PostgreSQL + pgvector 扩展的向量数据库

本地测试时可直接访问 `http://localhost:8000`（无需 Caddy）。

## 快速开始

### 前置要求

- Docker
- 所选提供方的 API 密钥（默认：对话用 `DEEPSEEK_API_KEY`，embedding 用 `SILICONFLOW_API_KEY`）

### 部署模式

本系统支持两种部署模式：

#### 本地测试（localhost）
无需公网访问或 TLS 的快速设置：

```bash
# 不使用 Caddy 启动（Chainlit 在 localhost:8000）
docker compose --profile local up -d
```

访问 `http://localhost:8000`。无需域名、防火墙或 TLS 配置。

#### 公网部署（推荐用于生产环境）
支持自动 HTTPS 的公网访问：

```bash
# 使用 Caddy 反向代理启动
docker compose --profile public up -d
```

访问 `https://<你的域名>`。**需要：**
- `.env` 中的 `DOMAIN` 设置为你控制的域名（A 记录指向本服务器 IP）
- `.env` 中的 `ACME_EMAIL` 用于 Let's Encrypt 过期提醒
- 防火墙对全世界开放 80 和 443 端口（Let's Encrypt ACME 验证）

**重要：** 此配置仅支持 Cloudflare 的**灰云（仅 DNS）**模式。如需启用橙云代理，参见下方的 [Cloudflare 设置](#cloudflare-设置)。

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

   > **API 密钥从 shell 环境变量读取，而非 `.env` 文件。** `.env` 仅保存非敏感配置
   > （提供方/模型选择、端口、数据库设置）；请在 shell 中导出密钥，例如：
   >
   > ```bash
   > export DEEPSEEK_API_KEY=...      # 对话提供方
   > export SILICONFLOW_API_KEY=...   # embedding 提供方
   > ```

3. **启动服务**

   本地测试（无 TLS）：
   ```bash
   docker compose --profile local up -d
   ```

   公网部署（含 Caddy + TLS）：
   ```bash
   docker compose --profile public up -d
   ```

4. **访问界面**

   - **本地：** 打开 `http://localhost:8000`
   - **公网：** 打开 `https://<你的域名>`（例如 <https://chat.bedtime.blog>）

   > **公网部署要求：** [Caddy](https://caddyserver.com) 为 `DOMAIN` 申请/续期
   > Let's Encrypt 证书。需要满足：
   > - `.env` 中的 `DOMAIN` —— 你控制的域名，A/AAAA 记录指向本服务器
   > - `.env` 中的 `ACME_EMAIL` —— 用于 Let's Encrypt 过期提醒的邮箱
   > - 防火墙允许入站 80 和 443 端口（来源 0.0.0.0/0）
   >
   > Caddy 自动处理 HTTP→HTTPS 重定向和证书续期。

### 验证安装

```bash
# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

## Cloudflare 设置

本配置支持 Cloudflare 的**灰云（仅 DNS）**模式。域名直接解析到你的源服务器，Let's Encrypt 可以直接访问以完成 ACME 验证。

如启用**橙云代理**，默认的 Caddy 配置将**无法续期证书**（Cloudflare 终止 TLS，阻断 ACME 验证）。要使用橙云：

1. **先保持灰云：** 首先按上述文档获取 Let's Encrypt 证书。
2. **再切换橙云：** HTTPS 使用现有证书可继续工作约 90 天。
3. **证书过期前（~90 天内）：** 实现以下方案之一：
   - **Cloudflare Origin Certificate：** 在 CF 控制台生成 15 年期证书并挂载到 Caddy（推荐，更简单）
   - **DNS-01 验证：** 为 Caddy 添加 Cloudflare DNS 插件，通过 DNS API 进行 ACME 验证（继续使用 Let's Encrypt）

**Cloudflare SSL/TLS 模式：** 使用橙云时，上述两种方案均需设置为 **Full (strict)**。

## 服务专属文档

- **[Frontend](frontend/README.md)**：UI定制
- **[Agent](agent/README.md)**：API端点、Agentic RAG实现
- **[Indexer](indexer/README.md)**：文档处理

## 数据持久化

数据在重启后持久保存：

- **PostgreSQL 数据**（chunks 与 embedding）：绑定挂载到 `./storage/postgres/volume`
- **服务日志**：Docker 命名卷 `bedtimenews_indexer_logs` 与 `bedtimenews_agent_logs`

## 项目结构

```plaintext
bedtimenews-agent/
├── agent/              # LangGraph 智能RAG服务
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── frontend/           # Chainlit 聊天UI
│   ├── app.py
│   ├── Dockerfile
│   └── README.md
├── indexer/            # 文稿 embedding 流水线
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── storage/            # 数据库初始化脚本
│   └── postgres/
├── docker-compose.yml  # 服务编排（含 profile 配置）
├── Caddyfile           # Caddy 反向代理配置
├── .env                # 环境配置（不在 git 中）
├── .env.example        # 环境配置模板
├── THIRD_PARTY_NOTICES.md  # 第三方组件许可证
└── README.md           # 本文件
```

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

本项目在公网部署中使用 [Caddy](https://caddyserver.com)（Apache-2.0 许可证）实现自动 HTTPS。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
