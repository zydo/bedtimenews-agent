"""
Chainlit frontend for BedtimeNews Agentic RAG chat.

This app provides a simple chat interface that sends user messages to the
FastAPI backend and displays responses. Conversation history is maintained
per-session in Chainlit's user_session (ephemeral, lost on page refresh).
"""

import json
import os

import chainlit as cl
import httpx

from starters import STARTERS, create_starter_actions


AGENT_BACKEND_HOST = os.environ["AGENT_BACKEND_HOST"]
AGENT_BACKEND_PORT = os.environ["AGENT_BACKEND_PORT"]
BACKEND_URL = f"http://{AGENT_BACKEND_HOST}:{AGENT_BACKEND_PORT}"
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history", [])
    actions = create_starter_actions()
    await cl.Message(
        content="欢迎使用睡前消息知识库！请选择一个示例问题开始，或直接输入您的问题。",
        actions=actions,
    ).send()


async def _handle_starter_action(action):
    """Handle starter question button clicks."""
    await on_message(cl.Message(content=action.payload["question"]))
    await action.remove()


for starter in STARTERS:
    cl.action_callback(starter["name"])(_handle_starter_action)


@cl.on_message
async def on_message(message: cl.Message):
    user_question = message.content.strip()
    if not user_question:
        await cl.Message(content="请输入有效的问题。").send()
        return

    history = cl.user_session.get("history") or []
    history.append({"role": "user", "content": user_question})

    payload = {"question": user_question, "stream": True}
    full_answer = ""
    msg = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:

            async with client.stream("POST", CHAT_ENDPOINT, json=payload) as response:
                response.raise_for_status()

                # Process OpenAI format SSE stream
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        payload = line[len("data: ") :]  # Remove "data: " prefix
                        if payload == "[DONE]":
                            break
                        event = json.loads(payload)
                        event_type = event.get("type")
                        if event_type != "answer_chunk":
                            continue
                        chunk = event.get("content")
                        if not chunk:
                            continue
                        full_answer += chunk
                        if not msg:
                            msg = cl.Message(content="")
                        await msg.stream_token(chunk)
                    except json.JSONDecodeError:
                        continue  # Skip malformed events

        history.append({"role": "assistant", "content": full_answer})
        cl.user_session.set("history", history)

        # Send starters after successful response
        actions = create_starter_actions()
        await cl.Message(content="", actions=actions).send()

    except httpx.TimeoutException:
        await cl.Message(content="请求超时，请稍后重试。").send()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code

        if status_code >= 500:
            error_msg = "服务暂时不可用，请稍后重试。"
        elif status_code == 422:
            error_msg = "问题格式有误，请检查后重试。"
        else:
            error_msg = f"服务错误 (代码 {status_code})，请稍后重试。"

        await cl.Message(content=error_msg).send()

    except Exception as e:
        await cl.Message(content="发生未知错误，请稍后重试。").send()
