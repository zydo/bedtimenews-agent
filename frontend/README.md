# Frontend Service

Custom chat UI for the BedtimeNews Agentic RAG system. A static single-page app
(HTML/CSS/JS) served by a small FastAPI app that also proxies the chat stream to
the internal agent backend.

See the [main README](../README.md) for full-stack setup.

## Design

- **Theme:** colors are derived from the show logo — a deep navy-black base, a
  royal-blue primary accent, and a golden-yellow accent for live/in-progress
  signals. Light and dark themes are both supported via a masthead toggle
  (persisted to `localStorage`, defaulting to the OS `prefers-color-scheme`).
- **Color tokens** are semantic and themeable (`--bg`, `--surface`, `--line`,
  `--text`, `--text-dim`, `--muted`, `--accent`, `--accent-2`), defined for dark
  in `:root` and overridden under `[data-theme="light"]`.
- **Type:** system CJK stack (PingFang SC / Microsoft YaHei / Noto Sans SC) for
  reading and a monospace stack for labels/data. Fonts are system-only by design
  — no webfont CDN, so the page loads reliably from mainland China.
- **Signal-acquisition log:** the RAG pipeline stages
  (route → rewrite → retrieve → grade → generate) render as a live log that
  locks once the answer starts, then collapses.

## Features

- Anonymous chat (no authentication)
- Light/dark theme toggle
- Sample questions grouped by category (full question is the clickable text)
- Real-time SSE streaming with visible pipeline steps
- Markdown answers rendered with [markdown-it](https://github.com/markdown-it/markdown-it)
  (vendored locally; `html:false` for XSS safety) plus app-specific citation chips
- Ephemeral, in-page conversation (cleared on refresh)
- Responsive to mobile; keyboard-accessible; respects `prefers-reduced-motion`

## Architecture

```plaintext
┌─────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────┐
│   Browser   │ ───> │   Caddy   │ ───> │ Web (FastAPI│ ───> │ Agent (API)  │
│             │ <─── │  (HTTPS)  │ <─── │  + static)  │ <─── │   Backend    │
└─────────────┘      └───────────┘      └─────────────┘      └──────────────┘
  Ports 80/443         Port 8000           Port 8000
   (Host)              (Internal)          (Internal)
```

The frontend:

- Runs in a Docker container on internal port 8000 (not published in the public
  profile; published to the host in the local profile)
- Sits behind a [Caddy](https://caddyserver.com) reverse proxy that terminates
  TLS and forwards to it over the internal Docker network (`web:8000`)
- Proxies `/chat` to the agent over the internal network; the agent is never
  exposed to the host

## Components

- **server.py** — FastAPI app: serves `static/`, exposes `/api/starters`, and
  proxies `/chat` SSE to the agent
- **starters.py** — sample-question data (categories + questions); plain data,
  no UI-framework dependency
- **static/index.html** — page markup, theme-boot script, and turn templates
- **static/styles.css** — themeable design system (`:root` + `[data-theme="light"]`)
- **static/app.js** — sample-question list, composer, theme toggle, SSE parsing,
  Markdown rendering
- **static/markdown-it.min.js** — vendored Markdown renderer (MIT)
- **static/bedtimenews.jpg** — favicon / brand logo
- **pyproject.toml** — dependency metadata (`fastapi`, `uvicorn`, `httpx`)

## Endpoints

| Method | Path             | Purpose                                       |
| ------ | ---------------- | --------------------------------------------- |
| GET    | `/`              | Serves the SPA (`static/index.html`)          |
| GET    | `/api/starters`  | Sample questions JSON (`categories`)          |
| POST   | `/chat`          | Proxies the agent SSE stream to the browser   |
| GET    | `/healthz`       | Liveness check                                |

## Development Workflow

The container runs `uvicorn server:app`. After changing Python or static files,
rebuild and restart:

```bash
# Local profile publishes the frontend on the host (FRONTEND_PORT, default 8000)
docker compose --profile local build web-local
docker compose --profile local up -d web-local
open http://localhost:8000
```

For public deployment the service is named `web` (behind Caddy):

```bash
docker compose --profile public build web
docker compose --profile public up -d web
```

> Use `--no-cache` if a rebuild appears to serve stale code.

### Run without Docker

```bash
cd frontend
pip install .
# Point at a reachable agent backend:
AGENT_BACKEND_HOST=localhost AGENT_BACKEND_PORT=8000 \
  uvicorn server:app --reload --port 8000
```

### Customization

- **Starter questions / categories:** edit `starters.py` (`CATEGORIES`).
- **Styling:** edit `static/styles.css` (design tokens live in `:root`).
- **Copy / layout:** edit `static/index.html`.
- **Logo / favicon:** replace `static/bedtimenews.jpg`.

## Configuration

| Variable             | Default | Purpose                                  |
| -------------------- | ------- | ---------------------------------------- |
| `AGENT_BACKEND_HOST` | `agent` | Agent service name on the Docker network |
| `AGENT_BACKEND_PORT` | `8000`  | Agent port                               |
| `FRONTEND_PORT`      | `8000`  | Host port published by `web-local`       |

## Debugging

```bash
# Logs
docker compose logs -f web        # or web-local for the local profile

# Backend connectivity from inside the container
docker compose exec web ping agent
docker compose exec web curl -N http://agent:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "测试", "stream": true}'
```

## API Contract

The frontend proxies the agent's `/chat` endpoint.

### Request

```json
{ "question": "string (required)", "stream": true }
```

### Streaming response (SSE)

```javascript
{"type": "step", "step": "route|rewrite|retrieve|grade|generate", "content": "…"}
{"type": "answer_chunk", "content": "…"}
{"type": "error", "content": "…"}
// stream terminates with:
"data: [DONE]"
```

## Limitations (MVP)

- **No authentication** — anonymous only
- **No persistence** — conversation is cleared on refresh
- **Per-tab session** — no cross-tab or server-side history

## Troubleshooting

**Port 80/443 in use (Caddy):**

```bash
sudo lsof -i :80 -i :443
# stop the conflicting service (e.g. host nginx), then:
docker compose --profile public up -d caddy
```

**TLS certificate not issued:**

- Confirm `DOMAIN` resolves (A record) to this server's public IP
- Confirm ports 80/443 are reachable from the internet
- Check Caddy logs: `docker compose logs -f caddy`

**Cannot connect to backend:**

- `docker compose ps agent` and `docker compose logs agent`
- `docker compose exec web ping agent`

**Changes not appearing:** rebuild (`--no-cache`) and hard-refresh the browser
(Cmd/Ctrl+Shift+R).
