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
┌─────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────┐
│   Browser   │ ───> │   Caddy   │ ───> │  Chainlit   │ ───> │ Agent (API)  │
│             │ <─── │  (HTTPS)  │ <─── │  Frontend   │ <─── │   Backend    │
└─────────────┘      └───────────┘      └─────────────┘      └──────────────┘
  Ports 80/443         Port 8000           Port 8000
   (Host)              (Internal)          (Internal)
```

The frontend:

- Runs in Docker container on internal port 8000 (not published to the host)
- Sits behind a [Caddy](https://caddyserver.com) reverse proxy that terminates
  TLS (ports 80/443) and proxies requests to it over the internal Docker network
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

# 4. Test in browser (via Caddy, using the DOMAIN set in .env)
open https://${DOMAIN}
```

> For local-only iteration without TLS, you can temporarily reach Chainlit
> directly by adding `ports: ["8000:8000"]` to the `chainlit` service, then
> open <http://localhost:8000>. Remove it before deploying — in production
> Caddy is the only public entry point.

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

**Port 80/443 in use:**

Caddy needs both ports for ACME challenges and HTTPS. Find and stop whatever is
holding them (often a host nginx/Apache):

```bash
sudo lsof -i :80 -i :443
# then stop the conflicting service, e.g.:
sudo systemctl stop nginx

# Restart Caddy
docker compose up -d caddy
```

**TLS certificate not issued:**

- Confirm `DOMAIN` in `.env` resolves (A record) to this server's public IP
- Confirm ports 80 and 443 are reachable from the internet (cloud firewall)
- Check Caddy logs: `docker compose logs -f caddy`

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
