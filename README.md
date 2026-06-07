# BedtimeNews Agent

[English](README.md) | [中文](README.zh-CN.md)

Agentic RAG (Retrieval-Augmented Generation) system for the 睡前消息 (BedtimeNews) knowledge base. Provides intelligent Q&A with automatic routing, semantic search, and grounded responses with citations.

> **Try it out:** [bedtime.blog](https://bedtime.blog)

## Overview

This system indexes video transcripts from the [BedtimeNews archive](https://archive.bedtime.news/) and enables semantic search with LLM-powered Q&A. Built with LangGraph, pluggable LLM/embedding providers (DeepSeek for chat and SiliconFlow's Qwen3 embeddings by default), and PostgreSQL + pgvector.

**Key Features:**

- Automatic query routing (RAG vs direct answer)
- Query optimization and semantic search
- LLM-based document grading
- Grounded answers with markdown citations
- Automated document indexing with incremental updates
- Web-based chat interface

## Content Coverage

The system indexes video transcripts from [bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents) covering diverse topics across multiple programs:

**Program Catalog:**

| Catalog       | Name       | Description                                     |
| ------------- | ---------- | ----------------------------------------------- |
| `main/`       | 睡前消息   | Comprehensive coverage across all topics        |
| `reference/`  | 参考信息   | Daily news aggregation                          |
| `business/`   | 产经破壁机 | Economy, industry, business, technology         |
| `commercial/` | 讲点黑话   | International relations, geopolitics            |
| `opinion/`    | 高见       | Technical analysis, infrastructure, engineering |
| `daily/`      | 每日新闻   | Daily news updates                              |
| `others/`     | 其它文稿   | Live Q&A and other related content              |

**Topic Categories:**

1. **Domestic Economy & Industry** - Economic policy, industrial development, real estate, local government debt, urban development
2. **Technology & Innovation** - AI, chips, semiconductors, autonomous vehicles, aerospace, engineering
3. **Cross-border E-commerce & Global Expansion** - SHEIN, TikTok, Chinese manufacturing advantages, global markets
4. **Corporate Governance & Regulation** - Corporate scandals, auditing, financial supervision, food safety, tax regulation
5. **International Relations & Geopolitics** - US-China relations, Russia-Ukraine conflict, Middle East, Korean Peninsula, Indo-Pacific
6. **Social Issues & Civil Life** - Education, healthcare, demographics, social welfare, urban governance
7. **Cryptocurrency & Fintech** - Bitcoin, blockchain, decentralized finance, digital assets
8. **Population & Social Policy** - Population crisis, socialized childcare, education system, social welfare reform
9. **Infrastructure & Engineering** - Railway construction, energy infrastructure, urban development, public utilities
10. **Law & Judicial Affairs** - Corporate disputes, criminal justice, consumer protection, regulatory frameworks

## Architecture

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

**Components:**

- **[Frontend](frontend/README.md)**: Chainlit based chat UI
- **[Agent](agent/README.md)**: LangGraph-based agentic RAG service
- **[Indexer](indexer/README.md)**: Automated document embedding pipeline
- **Database**: PostgreSQL with pgvector extension as Vector Database

## Quick Start

### Prerequisites

- Docker
- API keys for your chosen providers (by default: `DEEPSEEK_API_KEY` for chat and `SILICONFLOW_API_KEY` for embeddings)

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/zydo/bedtimenews-agent.git
   cd bedtimenews-agent
   ```

2. **Configure environment**

   Copy [`.env.example`](.env.example) to `.env` and configure:

   ```bash
   cp .env.example .env
   # Edit .env 
   ```

   > **API keys are read from the shell environment, not from `.env`.** `.env`
   > holds non-secret config (provider/model selection, ports, DB settings);
   > export your secrets in the shell instead, e.g.:
   >
   > ```bash
   > export DEEPSEEK_API_KEY=...      # chat provider
   > export SILICONFLOW_API_KEY=...   # embedding provider
   > ```

3. **Start all services**

   ```bash
   docker compose up -d
   ```

4. **Access the UI**

   Open browser to <http://localhost:80>

   > **Note:** This assumes `FRONTEND_PORT=80` (the default) in `.env`. If you changed this port, update the URL accordingly.

   The indexer will automatically start processing documents in the background.

### Verify Installation

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f
```

## Service-Specific Documentation

- **[Frontend](frontend/README.md)**: UI customization
- **[Agent](agent/README.md)**: API endpoints, Agentic RAG implementation
- **[Indexer](indexer/README.md)**: Document processing

## Data Persistence

Data is persisted across restarts:

- **PostgreSQL data** (chunks + embeddings): bind-mounted to `./storage/postgres/volume`
- **Service logs**: Docker named volumes `bedtimenews_indexer_logs` and `bedtimenews_agent_logs`

## Project Structure

```plaintext
bedtimenews-agent/
├── agent/              # LangGraph agentic RAG service
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── frontend/           # Chainlit chat UI
│   ├── app.py
│   ├── Dockerfile
│   └── README.md
├── indexer/            # Document embedding pipeline
│   ├── src/
│   ├── Dockerfile
│   └── README.md
├── storage/            # Database initialization scripts
│   └── postgres/
├── docker-compose.yml  # Service orchestration
├── .env                # Environment configuration (not in git)
└── README.md           # This file
```

## License

MIT
