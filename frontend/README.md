# Frontend Service

Chainlit-based chat UI for the BedtimeNews Agentic RAG system.

See [main README](../README.md) for setup instructions.

## Features

- Anonymous chat interface (no authentication)
- Clickable starter prompts for common queries
- Real-time streaming responses
- Markdown citation formatting
- Session-based conversation history (ephemeral)

## Architecture

```plaintext
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│   Browser   │ ──────> │  Chainlit   │ ──────> │ Agent (API)  │
│             │ <────── │  Frontend   │ <────── │   Backend    │
└─────────────┘         └─────────────┘         └──────────────┘
   Port 8080               Port 8000               Port 8000
(Host, Configurable)      (Container)              (Internal)
```

The frontend:

- Runs in Docker container on internal port 8000
- Exposed to host on port 8080 by default (configurable via `FRONTEND_PORT` in `.env`)
- Communicates with agent service via internal Docker network

## Components

- **app.py**: Chainlit application with chat handlers
- **starters.py**: Starter action buttons configuration
- **chainlit.md**: Welcome message with example queries
- **.chainlit/config.toml**: Chainlit configuration
- **public/**: Static assets (logo, avatar, CSS)
- **requirements.txt**: Python dependencies

## Development Workflow

### Making Code Changes

**CRITICAL**: Always rebuild with `--no-cache` after code changes!

```bash
# 1. Edit code
vim app.py

# 2. Rebuild image (no-cache prevents stale code)
docker compose build --no-cache chainlit

# 3. Restart service
docker compose up -d chainlit

# 4. Test in browser
open http://localhost:${FRONTEND_PORT:-8080}

# Or with default port:
open http://localhost:8080
```

### Common Pitfalls

**Docker caching old code:**

- Symptom: Changes don't appear after rebuild
- Solution: Always use `--no-cache` flag
- Verify: Check line count matches local file

**Editing without rebuilding:**

- Chainlit does NOT support hot-reload in Docker
- Always rebuild + restart after changes

### Customization

**Modify welcome message:**

```bash
vim chainlit.md
docker compose restart chainlit  # No rebuild needed for markdown
```

**Modify starter prompts:**

```python
# Edit starters.py, update the STARTERS list
vim starters.py
docker compose restart chainlit
```

**Change UI styling:**

```css
# Edit public/custom.css
# Restart needed (no rebuild required)
```

**Update logo/avatar:**

```bash
# Replace files in frontend/public/
cp new-logo.jpg frontend/public/bedtimenews.jpg
docker compose restart chainlit
```

## Debugging

### View logs

```bash
# Real-time logs
docker compose logs -f chainlit

# Last N lines
docker compose logs chainlit --tail 50

# Search for errors
docker compose logs chainlit | grep -i error
```

### Test backend connection

```bash
# From inside container
docker compose exec chainlit ping agent

# Test HTTP request
docker compose exec chainlit curl http://agent:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```

## Limitations (MVP)

- **No authentication**: Anonymous mode only
- **No persistence**: History lost on page refresh
- **Basic error handling**: Generic messages for backend errors
- **Session-based**: Each browser tab has isolated history

## API Contract

The frontend communicates with the agent's `/chat` endpoint.

### Request Format

```json
{
  "question": "string (required)",
  "stream": true
}
```

### Streaming Response (SSE)

**Event types:**

```javascript
// Answer chunk 
{"type": "answer_chunk", "content": "text"}

// Stream completion
"[DONE]"
```

## Troubleshooting

**Port 8080 in use:**

```bash
# Edit .env file to use a different port
FRONTEND_PORT=8081

# Then restart
docker compose up -d chainlit
```

**Cannot connect to backend:**

- Check agent is running: `docker compose ps agent`
- Check logs: `docker compose logs agent`
- Test connectivity: `docker compose exec chainlit ping agent`

**Changes not appearing:**

- Rebuild with `--no-cache`
- Verify deployment with `wc -l`
- Clear browser cache (Cmd+Shift+R)

**Conversation history lost:**

- This is expected behavior (session-based, ephemeral storage)
- History lost on page refresh by design (MVP)
