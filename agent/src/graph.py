"""
LangGraph workflow implementing the Agentic RAG (Retrieval-Augmented Generation) system.

This module defines the state machine that powers the BedtimeNews agent, orchestrating
query routing, retrieval optimization, and answer generation through a series of
interconnected nodes and conditional edges.

Graph Structure:
    The workflow is a directed graph where nodes represent processing steps and
    edges control flow between them:

    START → route → [RAG path] → query_rewrite → retrieve → grade → decision → [loop] → generate → END
                     [Direct path] → direct → END

    Key conditional edges:
    - route → retrieve/direct: Decides if query needs document retrieval
    - grade → generate/rewrite: Decides to generate answer or retry search

Node Functions:
    Each node function receives AgentState, performs computation, and returns updated state.

    - _route_node: Classifies input (greeting or RAG-needed)
    - _query_rewrite_node: Optimizes queries for vector search
    - _retrieve_node: Searches document embeddings via pgvector
    - _documents_grade_node: Filters search results by relevance
    - _answer_generate_node: Synthesizes answer with citations
    - _direct_answer_node: Answers greetings without retrieval

Control Flow Functions:
    Conditional edge functions that decide which path to take:

    - _should_retrieve: Returns 'retrieve' for RAG queries, 'direct' for greetings
    - _should_refine_query: Returns 'rewrite' to retry, 'generate' to answer

State Management:
    AgentState (TypedDict) holds all workflow state and evolves through nodes:
    - Initial state: question only
    - After route: needs_retrieval flag set
    - After query_rewrite: rewritten_queries added
    - After retrieve: documents populated with search results
    - After grade: relevant_documents filtered
    - After generate/direct: final_answer produced
    - Throughout: reasoning_steps accumulated for debugging

Retry Logic:
    The workflow supports automatic query refinement if first retrieval yields
    no relevant documents, controlled by iteration_count and max_iterations fields.

Singleton Graph:
    The compiled workflow graph is cached as a singleton (graph) for performance.

Note:
    This module focuses on workflow orchestration. Retrieval implementation is
    delegated to retriever.py, and LLM interactions use models configured in settings.py.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from .models import RetrieveRequest
from .providers import get_provider
from .retriever import retriever
from .settings import settings
from .vector_db import fetch_chunk_texts

logger = logging.getLogger(__name__)

# Initialize provider (module-level singleton)
_provider = get_provider()

# Cached LLM instances — created once and reused across all requests
_fast_llm = _provider.get_chat_model(model=settings.fast_model, temperature=0)
_generation_llm = _provider.get_chat_model(
    model=settings.generation_model,
    temperature=0.3,
    reasoning_effort="low",
)
_direct_llm = _provider.get_chat_model(
    model=settings.generation_model,
    temperature=0.7,
    reasoning_effort="low",
)

_GRADING_SYSTEM_PROMPT = """You are a document relevance grader.

Assess which documents are relevant to the user's input (question, topic, or statement).

Each document is shown as a heading followed by an excerpt from its text. Judge
by the excerpt. Headings in this archive are often just the episode's opening
greeting and say nothing about the content — an unhelpful heading is not
evidence that the document is irrelevant.

A document is RELEVANT if it:
- Discusses the same topic, event, or entity mentioned in the user input
- Provides context, background, or related information
- Contains opinions or analyses related to the topic

For each document, respond with its number if relevant.
Return ONLY the numbers of relevant documents, separated by commas (e.g., "1,3,5" or "2,4,7,9").
If no documents are relevant, respond with "NONE".
If all documents are relevant, you can respond with "ALL"."""


# ============================================================================
# State that flows through nodes during workflow
# ============================================================================


class AgentState(TypedDict):
    """State for the Agentic RAG workflow.

    This state flows through all nodes in the graph, accumulating information
    and transformations at each step.
    """

    question: str  # User input for this turn, as typed

    history: list[dict]  # Prior turns: {question, answer, grounded}

    # `question` resolved against `history` into something that stands alone
    # ("那它的房价呢" -> "鹤岗的房价怎么样"). Every node downstream of condense
    # reads this instead of `question`, which is what lets routing, retrieval and
    # grading stay exactly as they were for single-turn chats.
    standalone_question: str

    needs_retrieval: bool  # Routing decision, True if RAG path, False if direct LLM

    rewritten_queries: list[str]  # Transformed search queries

    documents: list[Document]  # Retrieved documents

    relevant_documents: list[Document]  # Filtered relevant chunks after grading

    final_answer: str  # Generated final answer with citations

    followups: list[str]  # Suggested next questions, drawn from retrieved docs

    reasoning_steps: Annotated[list[BaseMessage], add_messages]  # Reasoning trace

    iteration_count: int  # For query refinement loops

    max_iterations: int  # Limit for query refinement


# ============================================================================
# Graph Construction
# ============================================================================


def _create_agent_graph() -> CompiledStateGraph[AgentState, Any, Any, Any]:
    """
    Build the LangGraph workflow for Agentic RAG.

    Workflow:

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
    ║       ├─ no chunks╫───┘   │
    ║       │   & retry ║       │
    ║       │           ║       │
    ║       └─has chunks║       │
    ║          or max   ║       │
    ║            ↓      ║       │
    ║        Generate   ║       │
    ║            ↓      ║       │
    ╚═══════════╪═══════╝       │
                │               │
                └───────────────┘
                        ↓
                       END
    """
    workflow: StateGraph = StateGraph(AgentState)

    workflow.add_node("condense", _condense_node)
    workflow.add_node("route", _route_node)
    workflow.add_node("query_rewrite", _query_rewrite_node)
    workflow.add_node("retrieve", _retrieve_node)
    workflow.add_node("grade", _documents_grade_node)
    workflow.add_node("generate", _answer_generate_node)
    workflow.add_node("direct", _direct_answer_node)

    workflow.set_entry_point("condense")
    workflow.add_edge("condense", "route")
    workflow.add_conditional_edges(
        "route",
        _should_retrieve,
        {
            "retrieve": "query_rewrite",
            "direct": "direct",
        },
    )
    workflow.add_edge("query_rewrite", "retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        _should_refine_query,
        {
            "generate": "generate",
            "rewrite": "query_rewrite",  # Loop back for query refinement
        },
    )
    workflow.add_edge("generate", END)
    workflow.add_edge("direct", END)

    return workflow.compile()


# ============================================================================
# Node Functions
# ============================================================================

_CONDENSE_SYSTEM_PROMPT = """Your only task is to rewrite the user's latest input into a standalone question.

A standalone question is understandable without the conversation: pronouns
(它/这个/那边/他们, it/this/they) and omitted subjects are replaced with the
specific names they refer to.

Strict rules:
- Output only the rewritten question. No explanation, no quotes, no answer.
- Resolve references using ONLY information already present in the conversation.
  Never introduce a new fact, background detail, or guess.
- If the latest input is already standalone, or starts a new topic unrelated to
  the conversation, output it unchanged.
- Keep the user's original language and register. Do not expand it into a longer
  or more formal question.

Examples:

Conversation: user asked "鹤岗为什么成了收缩型城市的代表？"; assistant answered about 鹤岗.
Latest input: 那它的房价现在怎么样？
Output: 鹤岗的房价现在怎么样？

Conversation: user asked "台积电缺电反映了什么？"; assistant answered about Taiwan's power supply.
Latest input: 日本的半导体产业呢？
Output: 日本的半导体产业现在怎么样？

Conversation: user asked "鹤岗为什么成了收缩型城市的代表？"; assistant answered about 鹤岗.
Latest input: 什么是专项债？
Output: 什么是专项债？"""


def _resolved(state: AgentState) -> str:
    """The question every node after condense should work from.

    Falls back to the raw input so a state built without going through condense
    (or a condense that bailed) still behaves like the old single-turn pipeline.
    """
    return state.get("standalone_question") or state["question"]


def _format_history(history: list[dict], max_answer_chars: int = 300) -> str:
    """Render prior turns for a prompt, one line each.

    Whether a turn was grounded is recorded explicitly: without it the model can
    later treat an "I found nothing" turn as though it had produced sources.
    """
    lines = []
    for turn in history:
        question = str(turn.get("question", "")).strip()
        answer = str(turn.get("answer", "")).strip()
        if not question:
            continue
        if turn.get("grounded") and answer:
            if len(answer) > max_answer_chars:
                answer = answer[:max_answer_chars] + "…"
            lines.append(f"User asked: {question}\nAssistant answered: {answer}")
        else:
            lines.append(
                f"User asked: {question}\n"
                "Assistant answered: (nothing relevant found in the archive)"
            )
    return "\n\n".join(lines)


def _condense_node(state: AgentState) -> AgentState:
    """
    Resolve the latest input against the conversation into a standalone question.

    Everything downstream reads `standalone_question`, so routing, retrieval and
    grading behave for a follow-up exactly as they would for the same question
    asked cold. With no history there is nothing to resolve, so this is a pass
    through and single-turn latency is unchanged.
    """
    start_time = time.perf_counter()
    question = state["question"]  # the raw input is what condense resolves
    history = state.get("history") or []

    if not history:
        return {**state, "standalone_question": question, "reasoning_steps": []}

    messages = [
        SystemMessage(content=_CONDENSE_SYSTEM_PROMPT),
        HumanMessage(
            content=f"对话记录：\n{_format_history(history)}\n\n最新输入：{question}\n\n输出："
        ),
    ]

    try:
        resolved = str(_fast_llm.invoke(messages).content).strip()
    except Exception:  # noqa: BLE001 - a failed rewrite must not fail the turn
        logger.exception("[CONDENSE] rewrite failed; falling back to raw question")
        resolved = ""

    # Guard against the model explaining itself or answering instead of rewriting.
    if not resolved or len(resolved) > 2 * len(question) + 120:
        resolved = question

    elapsed = time.perf_counter() - start_time
    logger.info(
        f"[CONDENSE] Total: {elapsed:.2f}s -> {question!r} -> {resolved!r} "
        f"({len(history)} prior turn(s))"
    )

    steps = []
    if resolved != question:
        steps = [HumanMessage(content=f"[CONDENSE] 结合上下文理解为：{resolved}")]

    return {**state, "standalone_question": resolved, "reasoning_steps": steps}


def _route_node(state: AgentState) -> AgentState:
    """
    Decide whether the user input needs retrieval (RAG path) or can be answered directly.

    Uses a fast LLM to classify the input type.
    Routes to DIRECT for greetings and meta-questions only.
    """
    start_time = time.perf_counter()
    question = _resolved(state)

    system_prompt = """You are a routing assistant for a BedtimeNews (睡前消息) knowledge base system.

BedtimeNews is a Chinese news analysis program covering:
- **Chinese domestic affairs**: Economy, governance, social issues, infrastructure, law
- **International relations**: Geopolitics, China-US relations, global conflicts
- **Technology & Science**: AI, space, semiconductors, engineering projects
- **Society & Culture**: Education, healthcare, demographics, sports, media

Your task: Classify the user input into one of three categories:

**Category 1: GREETING** (simple greetings or meta-questions)
- Examples: "hi", "hello", "你好", "how are you", "who are you", "what can you do"
- Respond with: GREETING

**Category 2: DIRECT** (general knowledge or unrelated questions)
- Current weather, time, stock prices, real-time data
- General knowledge not covered by BedtimeNews (math, science basics, trivia)
- Topics completely unrelated to Chinese affairs, geopolitics, or the topics listed above
- Examples: "今天天气怎么样", "1+1等于几", "法国首都是哪里", "怎么煮面"
- Respond with: DIRECT

**Category 3: RAG** (BedtimeNews-related queries - default)
- Questions about Chinese domestic affairs, policy, economy, business, governance
- International relations, geopolitics, conflicts, diplomacy
- Technology, science, AI, space, infrastructure, engineering
- Social issues (education, healthcare, demographics, employment)
- Legal matters, sports, culture, media in Chinese/global context
- When uncertain, choose RAG
- Respond with: RAG

Respond with ONLY one word: "GREETING", "DIRECT", or "RAG"."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {question}"),
    ]

    llm_start = time.perf_counter()
    response = _fast_llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    decision = (
        response.content.strip().upper() if isinstance(response.content, str) else ""
    )

    # Substring matching tolerates extra punctuation/words from the LLM;
    # anything unrecognized defaults to RAG (matches the prompt's instruction).
    if "GREETING" in decision:
        needs_retrieval = False
        path_str = "Direct (greeting)"
    elif "DIRECT" in decision:
        needs_retrieval = False
        path_str = "Direct (general knowledge)"
    else:
        needs_retrieval = True
        path_str = "RAG"

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[ROUTE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> Decision: {decision}, Path: {path_str}"
    )

    reasoning = HumanMessage(content=f"[ROUTE] Decision: {decision}. Path: {path_str}")

    return {
        **state,
        "needs_retrieval": needs_retrieval,
        "reasoning_steps": [reasoning],
    }


def _query_rewrite_node(state: AgentState) -> AgentState:
    """
    Transform the user input into optimized retrieval queries.

    Extracts key entities, events, topics, and concepts to improve search quality.
    Handles questions, statements, topics, and any other user input.

    For retry attempts (iteration_count > 0), incorporates knowledge that
    previous queries found no relevant documents and includes previous queries
    to guide better reformulation.
    """
    start_time = time.perf_counter()
    question = _resolved(state)
    iteration_count = state.get("iteration_count", 0)
    previous_queries = state.get("rewritten_queries", [])

    if iteration_count == 0:
        # First attempt - use original prompt
        system_prompt = """You are a query optimization expert for BedtimeNews (睡前消息) semantic search.

Transform the user's input into 1-3 concise search queries optimized for vector similarity search.

The user input may be:
- A question asking for information
- A statement or topic for discussion
- Keywords or phrases to explore
- Any other form of text input

Guidelines:
- Extract key entities (names, places, organizations)
- Identify important events, topics, or themes
- Remove meta-language ("please tell me", "I want to know", "let's talk about")
- Use Chinese keywords when appropriate
- Each query should be 3-6 words
- Generate multiple queries if the input has different aspects or angles
- For statements/topics, formulate queries that would find relevant content

Examples:
KEYWORDS:
- "衡水中学" → "衡水 中学"
- "社会化抚养" → "社会化 抚养"
- "连花清瘟" → "连花清瘟"

QUESTIONS:
- "独山县的债务问题是什么？" → "独山县 债务 财政 困难"
- "tell me about Hengshui model" → "衡水中学 教育模式 高考"
- "连花清瘟真的有效吗？" → "连花清瘟 疗效", "以岭药业 药品"

Format: Return ONLY the queries, one per line, no numbering or explanation."""
        human_message = f"User input: {question}"
    else:
        # Retry attempt - guide to try simpler, broader queries
        system_prompt = f"""You are a query optimization expert for BedtimeNews (睡前消息) semantic search.

IMPORTANT: Your previous detailed queries found no relevant documents. This is retry attempt #{iteration_count}.

The user's original input: "{question}"

Your previous queries that found no results:
{chr(10).join(f"- {query}" for query in previous_queries)}

These complex queries apparently didn't match any content. Now try SIMPLER, BROADER queries with FEWER keywords:

Strategy: Use 1-2 core keywords per query instead of 3-4

Examples of simplification:
- Previous: "独山县 债务 财政 困难" → Retry: "独山 财政"
- Previous: "衡水中学 教育模式 高考 升学率" → Retry: "衡水 高考"
- Previous: "连花清瘟 疗效 以岭药业 药品质量" → Retry: "连花清瘟", "以岭药业"

Guidelines:
- Extract ONLY the most essential 1-2 keywords from each concept
- Try the core topic without modifiers or context
- Use shorter, more general terms
- Focus on proper nouns (names, places, organizations)
- Remove descriptive adjectives and contextual words
- Each query should have maximum 2-3 words
- Prioritize finding ANY mention of the core topic

Generate 1-3 SIMPLE, BROAD queries that might find relevant content where the detailed ones failed.

Format: Return ONLY the queries, one per line, no numbering or explanation."""
        human_message = f"User input: {question}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message),
    ]

    llm_start = time.perf_counter()
    response = _fast_llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    queries = (
        [q.strip() for q in response.content.strip().split("\n") if q.strip()]
        if isinstance(response.content, str)
        else []
    )

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[QUERY_REWRITE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> Generated {len(queries)} queries: {queries}"
    )

    reasoning = HumanMessage(
        content=f"[QUERY_REWRITE] Generated {len(queries)} queries: {queries}"
    )

    # reasoning_steps uses the add_messages reducer: return only the NEW
    # message, or downstream on_chain_end events re-emit old steps.
    return {
        **state,
        "rewritten_queries": queries,
        "reasoning_steps": [reasoning],
        "iteration_count": iteration_count + 1,
    }


def _retrieve_node(state: AgentState) -> AgentState:
    """
    Perform semantic search using batch retriever calls for efficiency.

    Retrieves documents for all rewritten queries and combines results.
    """
    start_time = time.perf_counter()
    queries = state["rewritten_queries"]

    # Build all requests for batch retrieval (skip text — it's only needed after grading)
    all_requests = [
        RetrieveRequest(
            query=q,
            match_count=settings.retrieval_match_count,
            match_threshold=settings.match_threshold,
            include_text=False,
            include_heading=True,
        )
        for q in queries
    ]

    # Batch retrieve all queries at once (more efficient)
    batch_start = time.perf_counter()
    all_responses = retriever.retrieve_batch(all_requests)
    batch_time = time.perf_counter() - batch_start

    # Convert ChunkResults to LangChain Documents
    all_chunks = []
    for response in all_responses:
        for result in response.results:
            chunk = Document(
                page_content=result.text or "",
                metadata={
                    "chunk_id": result.chunk_id,
                    "doc_id": result.doc_id,
                    "chunk_index": result.chunk_index,
                    "heading": result.heading,
                    "word_count": result.word_count,
                    "similarity": result.similarity,
                },
            )
            all_chunks.append(chunk)

    # Deduplicate by chunk_id (SQL DISTINCT ON already handles most, but this ensures safety)
    seen_ids = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk.metadata.get("chunk_id")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_chunks.append(chunk)

    # Sort by similarity score (descending)
    unique_chunks.sort(key=lambda d: d.metadata.get("similarity", 0), reverse=True)

    # Keep only the top-k documents to bound token usage and generation time
    top_chunks = unique_chunks[: settings.retrieval_top_k]

    # Fetch text for the survivors now rather than after grading. The grader
    # cannot judge relevance from a heading (see grading_excerpt_chars), and
    # doing it here means the generation node reuses these instead of issuing a
    # second query for the subset that passes.
    if top_chunks:
        chunk_ids = [cid for doc in top_chunks if (cid := doc.metadata.get("chunk_id"))]
        if chunk_ids:
            text_map = fetch_chunk_texts(chunk_ids)
            for doc in top_chunks:
                cid = doc.metadata.get("chunk_id")
                if cid and cid in text_map:
                    doc.page_content = text_map[cid]

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[RETRIEVE] Total: {total_time:.2f}s (Batch: {batch_time:.2f}s) -> "
        f"Retrieved {len(all_chunks)} chunks ({len(unique_chunks)} unique), kept top {len(top_chunks)}"
    )

    reasoning = HumanMessage(
        content=f"[RETRIEVE] Retrieved {len(all_chunks)} chunks ({len(unique_chunks)} unique), "
        f"kept top {len(top_chunks)} by similarity."
    )

    return {
        **state,
        "documents": top_chunks,
        "reasoning_steps": [reasoning],
    }


def _documents_grade_node(state: AgentState) -> AgentState:
    """
    Filter retrieved documents for relevance to the user input.

    Uses LLM to assess documents. For large document sets (>30), uses parallel
    processing for better performance.
    """
    start_time = time.perf_counter()
    question = _resolved(state)
    documents = state["documents"]

    if not documents:
        reasoning = HumanMessage(content="[GRADE] No documents to grade.")
        return {
            **state,
            "relevant_documents": [],
            "reasoning_steps": [reasoning],
        }

    # Format documents for grading. The excerpt is what makes this judgement
    # possible: headings average ~29 characters for chunks of ~736 words, and
    # more than half the corpus is headed by the show's opening greeting
    # ("大家好，……欢迎收看第N期睡前消息"), which describes nothing. Grading on
    # headings alone discarded chunks that were densely on-topic and had been
    # retrieved on the strength of their text.
    chunk_list = []
    for i, doc in enumerate(documents, 1):
        heading = doc.metadata.get("heading", "")
        similarity = doc.metadata.get("similarity", 0)
        excerpt = " ".join((doc.page_content or "").split())[
            : settings.grading_excerpt_chars
        ]
        chunk_list.append(
            f"Document {i} [{heading}] (similarity: {similarity:.2f})\n"
            f"Excerpt: {excerpt}\n"
        )

    # Use parallel processing for large document sets
    if len(documents) > settings.grading_parallel_threshold:
        # Split into batches for parallel processing
        batch_size = max(10, len(documents) // 3)
        batches = [
            chunk_list[i : i + batch_size]
            for i in range(0, len(chunk_list), batch_size)
        ]

        # Prepare messages for each batch
        messages_list = []
        for batch in batches:
            batch_text = "\n---\n".join(batch)
            messages_list.append(
                [
                    SystemMessage(content=_GRADING_SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"User input: {question}\n\n## Documents to Grade:\n\n{batch_text}\n\nRelevant document numbers:"
                    ),
                ]
            )

        # Run parallel LLM calls
        llm_start = time.perf_counter()
        responses = _parallel_llm_calls(_fast_llm, messages_list, max_concurrent=3)
        llm_time = time.perf_counter() - llm_start

        # Aggregate results from all batches
        relevant_indices = set()
        for batch_idx, response in enumerate(responses):
            response_text = (
                response.content.strip().upper()
                if isinstance(response.content, str)
                else ""
            )

            if response_text == "ALL":
                # All documents in this batch are relevant
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, len(documents))
                relevant_indices.update(range(batch_start, batch_end))
            elif response_text != "NONE":
                # Parse comma-separated numbers and adjust for batch offset
                numbers = re.findall(r"\d+", response_text)
                batch_offset = batch_idx * batch_size
                for n in numbers:
                    global_idx = batch_offset + int(n) - 1
                    if 0 <= global_idx < len(documents):
                        relevant_indices.add(global_idx)

        relevant_chunks = [documents[i] for i in sorted(relevant_indices)]

        total_time = time.perf_counter() - start_time
        logger.info(
            f"[GRADE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s, parallel mode, {len(batches)} batches) -> "
            f"Graded {len(documents)} chunks, {len(relevant_chunks)} relevant"
        )
    else:
        # Single batch mode for smaller document sets
        all_chunks_text = "\n---\n".join(chunk_list)

        messages = [
            SystemMessage(content=_GRADING_SYSTEM_PROMPT),
            HumanMessage(
                content=f"User input: {question}\n\n## Documents to Grade:\n\n{all_chunks_text}\n\nRelevant document numbers:"
            ),
        ]

        llm_start = time.perf_counter()
        response = _fast_llm.invoke(messages)
        llm_time = time.perf_counter() - llm_start

        # Parse response to extract relevant document indices
        response_text = (
            response.content.strip().upper()
            if isinstance(response.content, str)
            else ""
        )

        relevant_chunks = []
        if response_text == "NONE":
            # No relevant documents
            pass
        elif response_text == "ALL":
            # All documents are relevant
            relevant_chunks = documents
        else:
            # Parse comma-separated numbers
            try:
                # Extract numbers from response (handles "1,3,5" or "1, 3, 5" etc.)
                numbers = re.findall(r"\d+", response_text)
                relevant_indices = {
                    int(n) - 1 for n in numbers if 1 <= int(n) <= len(documents)
                }
                relevant_chunks = [documents[i] for i in sorted(relevant_indices)]
            except (ValueError, IndexError):
                # If parsing fails, log warning and keep all documents to be safe
                logger.warning(
                    f"Failed to parse grading response: {response_text}, keeping all documents"
                )
                relevant_chunks = documents

        total_time = time.perf_counter() - start_time
        logger.info(
            f"[GRADE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s, batch mode) -> "
            f"Graded {len(documents)} chunks, {len(relevant_chunks)} relevant"
        )

    reasoning = HumanMessage(
        content=f"[GRADE] Graded {len(documents)} documents, {len(relevant_chunks)} relevant."
    )

    return {
        **state,
        "relevant_documents": relevant_chunks,
        "reasoning_steps": [reasoning],
    }


def _answer_generate_node(state: AgentState) -> AgentState:
    """
    Generate the final response with citations based on relevant documents.

    Synthesizes information from documents and adds proper citations.
    Handles questions, topic discussions, and any user input.
    """
    start_time = time.perf_counter()
    question = _resolved(state)
    documents = state.get("relevant_documents", [])

    # Retrieval already populated page_content for everything it kept, so this
    # only has to cover documents that somehow arrived without it.
    missing = [
        cid
        for doc in documents
        if not doc.page_content and (cid := doc.metadata.get("chunk_id"))
    ]
    if missing:
        text_map = fetch_chunk_texts(missing)
        for doc in documents:
            cid = doc.metadata.get("chunk_id")
            if cid and cid in text_map:
                doc.page_content = text_map[cid]

    # Format documents for context
    context_parts = []
    # Map episode name -> canonical citation, used to repair the model's citations.
    citation_map: dict[str, str] = {}
    for chunk in documents:
        metadata = chunk.metadata
        doc_id = metadata.get("doc_id", "unknown")
        heading = metadata.get("heading", "")
        similarity = metadata.get("similarity", 0.0)

        episode_name = _get_episode_name(doc_id)
        citation = f"[[{episode_name}]]({_citation_url(doc_id)})"
        citation_map[episode_name] = citation

        context_parts.append(
            f"Citation: {citation}\n"
            f"Similarity: {similarity:.2f}\n"
            f"Heading: {heading}\n"
            f"Content: {chunk.page_content}\n"
        )

    context = (
        "\n---\n".join(context_parts)
        if context_parts
        else "No relevant documents found."
    )

    system_prompt = """You are a knowledgeable assistant for the 睡前消息 knowledge base.

Your task: Respond to the user's input based on the provided documents from 睡前消息 episodes.

CRITICAL REQUIREMENTS:
1. **Use ALL provided documents**: You MUST refer to every single document provided, no matter how many there are. Do not skip or ignore any documents.
2. **No length limits**: If many relevant documents are provided, write a comprehensive long response. Detailed answers are encouraged and preferred.
3. **Comprehensive coverage**: Synthesize information from ALL documents to provide complete coverage of the topic.

Guidelines:
1. **Ground your response in the documents**: Only make claims supported by the retrieved content
2. **Cite with the full markdown link**: Each retrieved document begins with a `Citation:` field that contains a complete markdown link (e.g. `[[产经破壁机70]](https://archive.bedtime.news/business/70.md)`). When you reference a document, copy its `Citation:` value **verbatim, including the entire `(https://...)` URL**. Never write the bare `[[名称]]` form, and never replace the URL with `(...)` or leave it out.
3. **Be specific**: Reference episode numbers, examples, and arguments from the show
4. **Synthesize**: Combine information from ALL documents - don't just summarize individual documents
5. **Be honest**: If the documents don't contain enough information, say so clearly
6. **Structure clearly**: Use paragraphs, bullets, or sections as appropriate
7. **Provide comprehensive response**: Use ALL relevant documents to give complete coverage of the topic
8. **Distinguish sources**: Make it clear when you're:
   - Reporting what 睡前消息 says (cite documents)
   - Adding general context (mark as background knowledge)
9. **Do not propose next step in prose**: Do not end the answer with offers like "如果你想，我可以……" or "要不要我帮你……". Suggested next questions belong only in the FOLLOW-UP block described below.
10. **Prior conversation is context, not evidence**: If earlier turns are shown, use them only to understand what the user is referring to and to avoid repeating yourself. They are NOT a source of facts. Every factual claim in this answer must come from the documents retrieved for THIS turn and carry a citation. If the conversation touched on something the current documents do not cover, say so rather than recalling it.

**MANDATORY**: You MUST use ALL provided documents in your response. If 10 documents are provided, reference all 10. If 20 documents are provided, reference all 20. No document should be left unused.

**CITATION FORMAT (MANDATORY)**: Every citation MUST be a complete markdown link, copied verbatim from a document's `Citation:` field — `[[名称]](https://archive.bedtime.news/...)`. The `[[名称]]` text and its `(https://...)` URL must always appear together.
- ✅ Correct: `[[睡前消息426]](https://archive.bedtime.news/main/401-500/426.md)`
- ❌ Wrong: `[[睡前消息426]]` (URL missing) or `[[睡前消息426]](...)` (placeholder URL)
- ❌ Wrong: `《睡前消息426》` — never use 书名号 for an episode reference, not even
  when the name appears mid-sentence as the subject of a clause. Write
  `[[睡前消息426]](https://archive.bedtime.news/main/401-500/426.md) 详细披露了…`,
  not `《睡前消息426》 详细披露了…`.
A `[[名称]]` written without its `(https://...)` URL is invalid — do not produce it.

If no relevant documents: Explain that the knowledge base doesn't contain information about this topic.

**FOLLOW-UP QUESTIONS (MANDATORY)**: After the answer, output the delimiter line
`<<<FOLLOWUPS>>>` on its own line, then 2-3 suggested next questions, one per
line, with no numbering, bullets or quotes.

Each suggested question MUST be answerable from the 睡前消息 archive — draw them
from topics the retrieved documents actually discuss but this answer did not
fully cover. Do not invent questions out of general curiosity: a suggestion the
archive cannot answer is worse than no suggestion. Write them in the user's
language, as a user would type them, each under 30 characters where possible.

If the retrieved documents were empty or irrelevant, output the delimiter with
nothing after it.

Example ending:

…以上就是专项债投向的主要问题。

<<<FOLLOWUPS>>>
地方政府的隐性债务有多大规模？
城投公司是怎么转型的？"""

    history_block = ""
    history = state.get("history") or []
    if history:
        history_block = (
            "## Earlier conversation "
            "(for resolving references and avoiding repetition — NOT a source of facts):\n\n"
            f"{_format_history(history)}\n\n"
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"{history_block}User input: {question}\n\n"
                f"## Retrieved Documents:\n\n{context}"
            )
        ),
    ]

    llm_start = time.perf_counter()
    response = _generation_llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    answer = str(response.content)

    # The follow-up suggestions ride along in the same completion, after a
    # delimiter, so they cost no extra call and can see what was retrieved.
    answer, followups = _split_followups(answer)

    # Repair citations the model may have written without (or with a placeholder)
    # URL — the prompt asks for full markdown links but can't guarantee them.
    answer, repaired = _repair_citations(answer, citation_map)

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[GENERATE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> "
        f"Generated {len(answer)} chars from {len(documents)} chunks"
        f"{f', repaired {repaired} citation(s)' if repaired else ''}"
        f"{f', {len(followups)} follow-up(s)' if followups else ''}"
    )

    # Don't add reasoning step for generation - the answer itself is sufficient
    return {
        **state,
        "final_answer": answer,
        "followups": followups,
        "reasoning_steps": [],
    }


def _direct_answer_node(state: AgentState) -> AgentState:
    """
    Respond directly without retrieval (for greetings and general knowledge questions).
    """
    start_time = time.perf_counter()
    question = _resolved(state)

    system_prompt = """You are the assistant for the 睡前消息 (BedtimeNews) transcript archive.

**Your role**: handle greetings and meta-questions, and turn everything else back
toward the archive. You answer *only* from 睡前消息 transcripts — and on this path
no transcripts have been retrieved, so you have nothing to answer from.

**For greetings** ("你好", "hi", "hello", etc.) and questions about what you are:
- Respond warmly and briefly
- Explain you can help explore BedtimeNews content covering:
  - Chinese domestic affairs (economy, governance, social issues, infrastructure, law)
  - International relations (geopolitics, China-US relations, global conflicts)
  - Technology & Science (AI, space, semiconductors, engineering projects)
  - Society & Culture (education, healthcare, demographics, sports, media)

**For anything else** (weather, arithmetic, trivia, real-time data, general
knowledge, topics unrelated to the show):
- **Do not answer it, even if you know the answer.** Answering from your own
  knowledge is exactly what this assistant must not do: an uncited claim sitting
  next to cited ones looks equally authoritative and is not.
- Say briefly that it falls outside the 睡前消息 transcripts
- Redirect: name a couple of subject areas above and invite a question about them
- Stay friendly and short — one or two sentences is enough, no apology loop

Always reply in the user's own language.

Example (Chinese input, showing the expected tone and length):
User: 今天天气怎么样？
You: 这个问题超出了睡前消息文稿的范围，我也没法获取实时信息。不过节目里聊过很多
话题——比如地方债务、半导体产业、人口结构，你想了解哪方面？"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=question)]

    llm_start = time.perf_counter()
    response = _direct_llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    answer = str(response.content)

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[DIRECT] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> Answer length: {len(answer)} chars"
    )

    # Don't add reasoning step for direct answers - routing step is sufficient
    return {
        **state,
        "final_answer": answer,
        "reasoning_steps": [],
    }


# ============================================================================
# Control Flow Functions
# ============================================================================


def _should_retrieve(state: AgentState) -> Literal["retrieve", "direct"]:
    """Decide whether to follow RAG path or direct answer path."""
    if state.get("needs_retrieval", False):
        return "retrieve"
    return "direct"


def _should_refine_query(state: AgentState) -> Literal["generate", "rewrite"]:
    """
    Decide whether to refine the query (if no relevant documents found).

    Only refine if we haven't exceeded max iterations.
    """
    relevant_chunks = state.get("relevant_documents", [])
    iteration_count = state.get("iteration_count", 0)
    # Fallback matters only if state was built outside create_initial_state
    max_iterations = state.get("max_iterations", 1)

    # If we have relevant documents, proceed to generation
    if relevant_chunks:
        return "generate"

    # If no relevant chunks and we can still iterate, refine query
    if iteration_count < max_iterations:
        logger.info(
            "[_should_refine_query] iteration_count=%d, max_iterations=%d",
            iteration_count,
            max_iterations,
        )
        # Important: State will be updated by query_rewrite_node to increment iteration_count
        return "rewrite"

    # Otherwise, proceed to generation (will generate "no info found" response)
    return "generate"


# ============================================================================
# Helper Functions
# ============================================================================


def _parallel_llm_calls(
    llm: Any, messages_list: list[list[Any]], max_concurrent: int = 3
) -> list[Any]:
    """
    Execute multiple LLM calls in parallel using a thread pool.

    Safe to call from sync or async contexts (no event loop conflicts).

    Args:
        llm: LangChain LLM instance
        messages_list: List of message lists for each LLM call
        max_concurrent: Maximum number of concurrent calls

    Returns:
        List of LLM responses in the same order as input
    """
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = [executor.submit(llm.invoke, messages) for messages in messages_list]
        return [f.result() for f in futures]


# Matches an episode citation plus an optional immediately-following (...) group,
# so we can normalize bare and placeholder-URL citations alike.
#
# Two spellings are accepted. `[[名称]]` is the format the prompt asks for. 《名称》
# is what the model falls back to on its own: it is the ordinary Chinese way to
# write a title, so it reaches for it even when told not to. Both are rewritten
# to the canonical markdown link. 《》 is only ever touched when the enclosed text
# is an exact episode name from this query's retrieved documents, so a genuine
# book or film title in the prose is left alone.
_CITATION_RE = re.compile(r"(?:\[\[([^\[\]]+?)\]\]|《([^《》]+?)》)(\([^)]*\))?")


def _repair_citations(answer: str, citation_map: dict[str, str]) -> tuple[str, int]:
    """
    Rewrite citations to their canonical full markdown link.

    The model is asked to emit `[[名称]](https://...)` but sometimes drops the URL
    (`[[名称]]`), writes a placeholder (`[[名称]](...)`), or abandons the bracket
    form entirely for Chinese title marks (`《名称》`) — all of which render as
    plain text instead of a link. For every citation whose name matches a
    retrieved document, replace the whole token (including any following
    parenthetical) with the canonical citation we built from that document's
    doc_id. Names not among the retrieved docs are left untouched: we have no URL
    for them, and this is what keeps a real 《书名》 in the prose from being
    rewritten into a link.

    Returns the repaired answer and the number of citations that were changed.
    """
    repaired = 0

    def _sub(match: "re.Match[str]") -> str:
        nonlocal repaired
        name = match.group(1) or match.group(2)
        canonical = citation_map.get(name)
        if canonical is None:
            return match.group(0)
        if match.group(0) != canonical:
            repaired += 1
        return canonical

    return _CITATION_RE.sub(_sub, answer), repaired


# The generation prompt asks for the answer, this delimiter, then the suggested
# questions. Shared with the frontend, which hides the tail while streaming.
FOLLOWUPS_DELIMITER = "<<<FOLLOWUPS>>>"

_MAX_FOLLOWUPS = 3
# Leading "1. ", "- ", "* " etc. the model adds despite being told not to.
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)、])\s*")


def _split_followups(answer: str) -> tuple[str, list[str]]:
    """Split a completion into the answer and its suggested follow-up questions.

    Returns the answer unchanged and no suggestions when the delimiter is absent,
    so a model that ignores the instruction degrades to the previous behaviour
    rather than leaking a half-written block into the prose.
    """
    head, sep, tail = answer.partition(FOLLOWUPS_DELIMITER)
    if not sep:
        return answer.strip(), []

    followups = []
    for line in tail.splitlines():
        line = _LIST_MARKER_RE.sub("", line).strip().strip("\"'“”")
        # A stray sentence of commentary is not a question; keep it out of the UI.
        if len(line) < 4 or len(line) > 60:
            continue
        followups.append(line)
        if len(followups) >= _MAX_FOLLOWUPS:
            break

    return head.strip(), followups


def _citation_url(doc_id: str) -> str:
    """Public transcript URL for a document."""
    return f"https://archive.bedtime.news/{doc_id}.md"


def build_citation_urls(documents: list[Document]) -> dict[str, str]:
    """
    Map episode display name -> transcript URL for the given documents.

    Sent to the streaming client so it can turn citations into links while the
    answer is still arriving. Server-side repair only runs once generation has
    finished, which is too late to help a reader watching the text appear.
    """
    urls: dict[str, str] = {}
    for chunk in documents:
        doc_id = chunk.metadata.get("doc_id", "unknown")
        urls[_get_episode_name(doc_id)] = _citation_url(doc_id)
    return urls


def _get_episode_name(doc_id: str) -> str:
    """
    Extract episode display name from doc_id.

    Args:
        doc_id: Document ID like 'main/501-600/588' or 'reference/1-100/42'

    Returns:
        Formatted episode name like '睡前消息588', '参考信息42', etc.

    Examples:
        'main/501-600/588' → '睡前消息588'
        'reference/1-100/42' → '参考信息42'
        'opinion/123' → '高见123'
        'daily/2023/11/15' → '每日新闻15'
        'commercial/5' → '讲点黑话5'
        'business/10' → '产经破壁机10'
        'livestream/2023/05/20' → '直播问答记录2023/05/20' (special handling!)
    """
    if doc_id.startswith("livestream/"):
        return f"直播问答记录{doc_id[len('livestream/') :]}"

    # Extract episode number (last numeric part in path)
    parts = doc_id.split("/")
    episode_num = parts[-1] if parts else doc_id

    # Remove .md extension if present
    episode_num = episode_num.replace(".md", "")

    # Determine episode type based on path pattern
    if doc_id.startswith("main/"):
        # main/*/[0-9]*.md
        return f"睡前消息{episode_num}"
    elif doc_id.startswith("reference/"):
        # reference/*/[0-9]*.md
        return f"参考信息{episode_num}"
    elif doc_id.startswith("opinion/"):
        # opinion/[0-9]*.md
        return f"高见{episode_num}"
    elif doc_id.startswith("daily/"):
        # daily/*/*/[0-9]*.md
        return f"每日新闻{episode_num}"
    elif doc_id.startswith("commercial/"):
        # commercial/[0-9]*.md
        return f"讲点黑话{episode_num}"
    elif doc_id.startswith("business/"):
        # business/[0-9]*.md or business/-[0-9]*.md
        return f"产经破壁机{episode_num}"
    else:
        # Fallback for unknown types
        return f"文档{episode_num}"


# ============================================================================
# Public Singleton Instance
# ============================================================================

graph = _create_agent_graph()

# ============================================================================
# Public Factory Function
# ============================================================================


def create_initial_state(
    question: str, history: list[dict] | None = None
) -> AgentState:
    return {
        "question": question,
        "history": history or [],
        "standalone_question": "",
        "followups": [],
        "needs_retrieval": False,
        "rewritten_queries": [],
        "documents": [],
        "relevant_documents": [],
        "final_answer": "",
        "reasoning_steps": [],
        "iteration_count": 0,
        "max_iterations": 2,
    }
