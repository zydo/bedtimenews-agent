# BedtimeNews Agent

[English](README.md) | [中文](README.zh-CN.md)

Agentic RAG (Retrieval-Augmented Generation) system for the 睡前消息 (BedtimeNews) knowledge base. Provides intelligent Q&A with automatic routing, semantic search, and grounded responses with citations.

> **Try it out:** [bedtime.blog](https://bedtime.blog)

## Overview

This system indexes video transcripts from the [BedtimeNews archive](https://archive.bedtime.news/) and enables semantic search with LLM-powered Q&A. Built with LangGraph, OpenAI embeddings, and PostgreSQL + pgvector.

**Key Features:**

- Automatic query routing (RAG vs direct answer)
- Query optimization and semantic search
- LLM-based document grading
- Grounded answers with markdown citations
- Automated document indexing with incremental updates
- Web-based chat interface

## Content Coverage

The system indexes video transcripts from [bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents) covering diverse topics:

1. **Domestic Economy & Industry** - Economic policy, industrial development, real estate, local government debt
2. **Governance & Policy** - Government administration, fiscal policy, administrative reform
3. **Social Issues & Civil Life** - Education, healthcare, demographics, social welfare
4. **International Relations & Geopolitics** - US-China relations, Russia-Ukraine conflict, Middle East, Indo-Pacific
5. **Technology & Innovation** - AI, aerospace, semiconductors, autonomous vehicles
6. **Infrastructure & Engineering** - Railway construction, energy infrastructure, urban development
7. **Law & Judicial Affairs** - Corporate disputes, criminal justice, consumer protection
8. **Sports & Culture** - Olympics, esports, entertainment industry, cultural soft power
9. **Media & Information** - Daily news aggregation, media regulation, social media
10. **Natural Disasters & Environmental Issues** - Earthquakes, floods, climate change, environmental protection
11. **History & Comparative Analysis** - Historical precedents, international development models

**Program Catalog:**

| Catalog       | Name       | Episodes (Until Nov 2025) | Topics                                          |
| ------------- | ---------- | ------------------------- | ----------------------------------------------- |
| `main/`       | 睡前消息   | 900+                      | Comprehensive coverage across all topics        |
| `reference/`  | 参考信息   | 600+                      | Daily news aggregation                          |
| `business/`   | 产经破壁机 | 86                        | Economy, industry, business, technology         |
| `commercial/` | 讲点黑话   | 66                        | International relations, geopolitics            |
| `opinion/`    | 高见       | 51                        | Technical analysis, infrastructure, engineering |

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
- OpenAI API key

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

3. **Start all services**

   ```bash
   docker compose up -d
   ```

4. **Access the UI**

   Open browser to <http://localhost>

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

Document embeddings are persisted in Docker volumes:

- `bedtimenews-postgres-data`: PostgreSQL database

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
