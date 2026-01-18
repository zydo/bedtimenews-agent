"""
Chainlit frontend for BedtimeNews Agentic RAG chat.

This app provides a chat interface that sends user messages to the
FastAPI backend and displays responses with intermediate RAG pipeline steps.
Conversation history is maintained per-session in Chainlit's user_session.
"""

import json
import os
import re

import chainlit as cl
import httpx

from starters import STARTERS, create_starter_actions


def _strip_tag_prefix(content: str) -> str:
    """Remove [TAG] prefixes from step content."""
    return re.sub(r'^\[[A-Z_]+\]\s*', '', content)


AGENT_BACKEND_HOST = os.environ["AGENT_BACKEND_HOST"]
AGENT_BACKEND_PORT = os.environ["AGENT_BACKEND_PORT"]
BACKEND_URL = f"http://{AGENT_BACKEND_HOST}:{AGENT_BACKEND_PORT}"
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"


# Step labels for processing status
STEP_CONFIG = {
    "route": "路由分析",
    "rewrite": "查询优化",
    "retrieve": "检索文档",
    "grade": "相关性评分",
    "generate": "生成答案",
}


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

    # Create one message that will be updated with progress
    progress_msg = cl.Message(content="**处理中...**")
    await progress_msg.send()

    displayed_steps = []
    first_answer_chunk = False

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", CHAT_ENDPOINT, json={"question": user_question, "stream": True}) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        payload = line[len("data: ") :]
                        if payload == "[DONE]":
                            break
                        event = json.loads(payload)
                        event_type = event.get("type")

                        # Handle intermediate pipeline steps (replace message content)
                        if event_type == "step":
                            step_type = event.get("step", "")
                            step_content = event.get("content", "")
                            step_label = STEP_CONFIG.get(step_type, step_type)

                            # Only display each step once
                            if step_content not in displayed_steps:
                                displayed_steps.append(step_content)
                                # Strip duplicate [TAG] prefixes
                                clean_content = _strip_tag_prefix(step_content)
                                # Replace the message content with current step
                                progress_msg.content = f"{step_label}: {clean_content}"
                                await progress_msg.update()

                        # Handle answer chunks (replace message with answer)
                        elif event_type == "answer_chunk":
                            chunk = event.get("content")
                            if not chunk:
                                continue

                            # On first answer chunk, clear and start streaming
                            if not first_answer_chunk:
                                progress_msg.content = ""
                                await progress_msg.update()
                                first_answer_chunk = True

                            # Stream answer chunks
                            await progress_msg.stream_token(chunk)

                    except json.JSONDecodeError:
                        continue  # Skip malformed events

        # Save final answer to history (clean content without steps)
        final_content = progress_msg.content if hasattr(progress_msg, 'content') else ""
        history.append({"role": "assistant", "content": final_content})
        cl.user_session.set("history", history)

        # Send starters after successful response
        actions = create_starter_actions()
        await cl.Message(content="", actions=actions).send()

    except httpx.TimeoutException:
        if not first_answer_chunk:
            await progress_msg.remove()
        await cl.Message(content="请求超时，请稍后重试。").send()

    except httpx.HTTPStatusError as e:
        if not first_answer_chunk:
            await progress_msg.remove()
        status_code = e.response.status_code

        if status_code >= 500:
            error_msg = "服务暂时不可用，请稍后重试。"
        elif status_code == 422:
            error_msg = "问题格式有误，请检查后重试。"
        else:
            error_msg = f"服务错误 (代码 {status_code})，请稍后重试。"

        await cl.Message(content=error_msg).send()

    except Exception as e:
        if not first_answer_chunk:
            await progress_msg.remove()
        await cl.Message(content=f"发生未知错误: {str(e)}，请稍后重试。").send()
