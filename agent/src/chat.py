"""Chat endpoint implementation, stream and non-stream."""

import json
import logging
from typing import AsyncGenerator

from .agent import agent_stream_query, agent_query
from .models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


def nonstream_chat(request: ChatRequest) -> ChatResponse:
    result = agent_query(request.question)
    answer = result["answer"]
    logger.info(f"Chat completed: {len(answer)} chars")
    return ChatResponse(answer=answer)


async def stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream chat responses in Server-Sent Events (SSE) format compatible with OpenAI's chat completions API.

    This function acts as a streaming endpoint that:
    1. Takes a chat request with a user question
    2. Streams the agent's response as SSE events
    3. Formats each event according to OpenAI's streaming format
    4. Handles errors gracefully within the stream

    Args:
        request: ChatRequest object containing the user's question and optional parameters

    Yields:
        str: SSE-formatted events in the format "data: {json_event}\n\n"
             Each event contains answer chunks from the agent
             Stream ends with "data: [DONE]"

    Event Format:
        Each yielded event is a JSON object with structure:
        {
            "type": "answer_chunk",
            "content": "text content from the agent"
        }

    Error Handling:
        If an exception occurs during streaming, yields an error event:
        {
            "type": "error",
            "content": "error message"
        }

    Example:
        async for event in stream_chat(ChatRequest(question="What is the capital of France?")):
            print(event)  # "data: {\"type\": \"answer_chunk\", \"content\": \"Paris\"}\n\n"
    """
    try:
        # Prepend "data: " to stream events from agent (SSE format)
        async for event in agent_stream_query(request.question):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]"

    except Exception as e:
        logger.error(f"Error streaming chat response: {e}")
        error_event = {"type": "error", "content": str(e)}
        yield f"data: {json.dumps(error_event)}\n\n"
