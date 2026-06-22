"""
Frontend server for the BedtimeNews Agentic RAG chat.

Responsibilities:
- Serve the static single-page UI from ./static
- Expose the sample questions as JSON at /api/starters
- Proxy the chat stream at /chat to the internal agent backend, which is not
  reachable from outside the Docker network

The agent's /chat endpoint speaks Server-Sent Events:
    data: {"type": "step", "step": "...", "content": "..."}
    data: {"type": "answer_chunk", "content": "..."}
    data: {"type": "error", "content": "..."}
    data: [DONE]
We stream those bytes straight through to the browser.
"""

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starters import CATEGORIES

AGENT_BACKEND_HOST = os.environ.get("AGENT_BACKEND_HOST", "agent")
AGENT_BACKEND_PORT = os.environ.get("AGENT_BACKEND_PORT", "8000")
CHAT_ENDPOINT = f"http://{AGENT_BACKEND_HOST}:{AGENT_BACKEND_PORT}/chat"

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="睡前消息知识库")


def _sse_error(message: str) -> bytes:
    """Emit a terminal SSE error event the frontend understands, then close."""
    event = json.dumps({"type": "error", "content": message}, ensure_ascii=False)
    return f"data: {event}\n\ndata: [DONE]\n\n".encode()


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/api/starters")
async def get_starters() -> JSONResponse:
    """Sample questions (grouped by category) for the empty-state list."""
    return JSONResponse({"categories": CATEGORIES})


@app.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    """Proxy the chat SSE stream from the internal agent to the browser."""
    body = await request.body()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        timeout = httpx.Timeout(120.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    CHAT_ENDPOINT,
                    content=body,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 422:
                yield _sse_error("问题格式有误，请检查后重试。")
            elif code >= 500:
                yield _sse_error("档案服务暂时不可用，请稍后重试。")
            else:
                yield _sse_error(f"服务错误（代码 {code}），请稍后重试。")
        except httpx.TimeoutException:
            yield _sse_error("信号超时，请稍后重试。")
        except Exception as exc:  # noqa: BLE001 - surface anything to the client
            yield _sse_error(f"信号中断：{exc}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Static assets and index.html (mounted last so API routes take precedence).
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
