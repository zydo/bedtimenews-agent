"""
LangGraph-based Agentic RAG agent for BedtimeNews knowledge base.

Public API:
    agent_query(question: str) -> dict
        Process a user question and return complete result.

    agent_stream_query(question: str) -> AsyncIterator[dict]
        Process a user question and yield streaming events.

Usage:
    from agent import agent_query, agent_stream_query

    # Synchronous query
    result = agent_query("How much debt in Du Shan's county?")
    print(result["answer"])

    # Streaming query
    async for event in agent_stream_query("What is the Hengshui model?"):
        if event["type"] == "token":
            print(event["content"], end="")
"""

from typing import Any, AsyncIterator

from langchain_core.messages.ai import AIMessageChunk

from .graph import AgentState, create_initial_state, graph

# ============================================================================
# Public API
# ============================================================================


def agent_query(question: str) -> dict:
    """
    Process a user question through the agentic workflow.

    Args:
        question: User's question

    Returns:
        Dict with only the answer field
    """
    initial_state: AgentState = create_initial_state(question)
    final_state = graph.invoke(input=initial_state)
    return {"answer": final_state.get("final_answer", "")}


async def agent_stream_query(question: str) -> AsyncIterator[dict[str, Any]]:
    """
    Stream answer chunks and intermediate reasoning steps from the agentic RAG workflow.

    This function executes the LangGraph workflow and streams both intermediate steps
    and final answer content, providing visibility into the RAG pipeline progress.

    Args:
        question: The user's input question or query string

    Yields:
        dict: Events with structure:
            {
                "type": "step" | "answer_chunk",
                "step": "route" | "rewrite" | "retrieve" | "grade" | "generate",
                "content": "step description or text content"
            }

    Event Types:
        - "step": Intermediate pipeline steps with descriptions
        - "answer_chunk": LLM-generated answer content

    Steps Emitted:
        1. "route": Initial routing decision (direct/RAG)
        2. "rewrite": Query optimization
        3. "retrieve": Document retrieval results
        4. "grade": Document grading results
        5. "generate": Final answer generation (streamed as chunks)

    Example:
        async for event in agent_stream_query("What is the capital of France?"):
            if event["type"] == "step":
                print(f"[{event['step']}] {event['content']}")
            else:
                print(event["content"], end="")

    Note:
        This function provides full pipeline visibility for debugging and user feedback.
    """
    initial_state = create_initial_state(question)

    # Track which steps we've emitted to avoid duplicates
    emitted_steps = set()

    async for event in graph.astream_events(initial_state, version="v2"):
        event_name = event.get("event", "")
        langgraph_node = event.get("metadata", {}).get("langgraph_node", "")

        # Emit reasoning steps from each node completion
        if event_name == "on_chain_end" and langgraph_node and langgraph_node in ["route", "query_rewrite", "retrieve", "grade", "generate", "direct"]:
            output = event.get("data", {}).get("output")

            # Handle different output formats from LangGraph
            if isinstance(output, dict):
                state = output
            else:
                continue

            # Emit reasoning steps from each node
            reasoning_steps = state.get("reasoning_steps", [])
            for step in reasoning_steps:
                # Get step content safely
                step_content = step.content if hasattr(step, "content") else str(step)

                # Create a unique key for this step
                step_key = f"{langgraph_node}_{step_content}"

                if step_key not in emitted_steps:
                    emitted_steps.add(step_key)

                    # Map nodes to step types
                    step_type = None
                    if langgraph_node == "route":
                        step_type = "route"
                    elif langgraph_node == "query_rewrite":
                        step_type = "rewrite"
                    elif langgraph_node == "retrieve":
                        step_type = "retrieve"
                    elif langgraph_node == "grade":
                        step_type = "grade"
                    elif langgraph_node in ["generate", "direct"]:
                        step_type = "generate"

                    if step_type:
                        yield {
                            "type": "step",
                            "step": step_type,
                            "content": step_content,
                        }

        # Stream LLM tokens from answer generation nodes
        if event_name == "on_chat_model_stream":
            if langgraph_node != "direct" and langgraph_node != "generate":
                continue

            chunk = event.get("data", {}).get("chunk")
            if not isinstance(chunk, AIMessageChunk):
                continue

            yield {"type": "answer_chunk", "content": chunk.content}
