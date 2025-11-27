# Agent Service

Agentic RAG service implementing intelligent routing, query optimization, semantic retrieval, and grounded answer generation with citations.

See [main README](../README.md) for setup instructions.

## Architecture

### Agentic RAG Workflow

```plaintext
            START
              ↓
            Route ──────────────────┐
              │                     │
              │                     │
            [RAG]               [Direct]
              │                     │
              ↓                     ↓
        ╔═══════════════════╗   Direct Answer
        ║  RAG Pipeline     ║       │
        ║  (with retry)     ║       │
        ╠═══════════════════╣       │
        ║                   ║       │
        ║  Query Rewrite ←──╫───┐   │
        ║       ↓           ║   │   │
        ║    Retrieve       ║   │   │
        ║       ↓           ║   │   │
        ║  Grade Docs       ║   │   │
        ║       ↓           ║   │   │
        ║    Decision       ║   │   │
        ║       │           ║   │   │
        ║       ├─ no docs ─╫───┘   │
        ║       │   & retry ║       │
        ║       │           ║       │
        ║       └─ has docs ║       │
        ║          or max   ║       │
        ║            ↓      ║       │
        ║        Generate   ║       │
        ║            ↓      ║       │
        ╚═══════════=╪══════╝       │
                     │              │
                     └──────────────┘
                            ↓
                           END
```

**Components:**

- `agent.py`: Public API (`agent_query()`, `agent_stream_query()`)
- `graph.py`: LangGraph workflow with intelligent routing
- `retriever.py`: Semantic search (embeddings + pgvector)
- `chat.py`: FastAPI endpoint handlers
- `main.py`: FastAPI server
- `vector_db.py`: PostgreSQL + pgvector operations

### Routing Behavior

**Direct Path** (no retrieval):

- Simple greetings: "hi", "hello", "你好"
- Questions about the assistant

**RAG Path** (retrieval-augmented):

- All other input (questions, topics, keywords)
- Ensures answers are grounded in knowledge base

## API Reference

### POST /chat

**Request:**

```json
{
  "question": "独山县的债务问题有多严重？",
  "stream": false
}
```

**Parameters:**

- `question` (required): User query
- `stream` (optional, default: false): Enable SSE streaming

**Response (Non-streaming):**

```json
{
  "answer": "根据[[睡前消息588]](https://archive.bedtime.news/main/501-600/588.md)..."
}
```

**Response (Streaming):**

```plaintext
data: {"type": "answer_chunk", "content": "根据"}
data: {"type": "answer_chunk", "content": "睡前"}
...
data: [DONE]
```

## Testing

### Test Agent (Full Agentic RAG Flow)

```bash
# Test a single custom query
docker compose exec agent python -m src.test_agent -q "独山县的债务问题"
docker compose exec agent python -m src.test_agent --query "王文银的创业故事有哪些可疑之处"

# List query categories
docker compose exec agent python -m src.test_agent --list-categories

# Test specific category
docker compose exec agent python -m src.test_agent --category education

# Random sample
docker compose exec agent python -m src.test_agent --random 10

# Limit to first N queries
docker compose exec agent python -m src.test_agent --limit 3
```

### Test Retriever (Retrieval Only)

```bash
# Test a single custom query
docker compose exec agent python -m src.test_retriever -q "独山县"
docker compose exec agent python -m src.test_retriever --query "你的问题"

# Test retrieval with custom parameters
docker compose exec agent python -m src.test_retriever \
  --category education \
  --match-count 10 \
  --threshold 0.3

# Random sample
docker compose exec agent python -m src.test_retriever --random 20
```

## Configuration

### Model Selection

Configure in `.env`:

```bash
# Fast model (routing, query rewrite, grading)
FAST_MODEL=gpt-5-mini

# Generation model (final answer)
GENERATION_MODEL=gpt-5

# Embedding model
EMBEDDING_MODEL=text-embedding-3-small
```

**Recommendations:**

- **Fast Model**: `gpt-5-mini` (balanced) or `gpt-5-nano` (fastest)
- **Generation Model**: `gpt-5` (best quality) or `gpt-5-mini` (faster/cheaper)
- **Embedding**: `text-embedding-3-small` (1536-dim, default) or `text-embedding-3-large` (3072-dim, better quality)

**Query Parameters**:

- `match_count`: Default 5, increase for better recall
- `similarity_threshold`: Default 0.5, increase for higher precision (but fewer results)
- `max_iterations`: Default 2, limits query refinement loops

## Development

### Project Structure

```plaintext
agent/src/
├── main.py            # FastAPI server
├── chat.py            # Endpoint handlers
├── agent.py           # Agentic RAG API
├── graph.py           # LangGraph workflow
├── retriever.py       # Semantic search
├── vector_db.py       # Database operations
├── models.py          # Pydantic models
├── settings.py        # Configuration
├── test_agent.py      # Pipeline testing
├── test_retriever.py  # Retrieval testing
└── test_data.py       # Test queries
```

### Network Access

The agent service runs on **internal Docker network only** (not exposed to host):

```bash
# Access from host (via docker exec)
docker compose exec agent curl http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'

# Access from another container (via service name)
curl http://agent:8000/chat -d '{"question": "test"}'
```

For production deployment, use a reverse proxy (nginx, traefik, caddy) instead of direct exposure.

### Debugging

```bash
# View logs
docker compose logs -f agent

# Access container
docker compose exec agent bash

# Test database connection
docker compose exec agent python -c "from src.vector_db import VectorDB; db = VectorDB(); print('OK')"

# Test single query
docker compose exec agent python -m src.test_agent --limit 1
```

## Episode Type Mapping (from doc_id path)

- `main/*` → "睡前消息"
- `reference/*` → "参考信息"
- `opinion/*` → "高见"
- `daily/*/*` → "每日新闻"
- `commercial/*` → "讲点黑话"
- `business/*` → "产经破壁机"
- `livestream/*/*` → "直播问答记录"
