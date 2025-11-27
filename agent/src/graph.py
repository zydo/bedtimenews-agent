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
from typing import Annotated, Any, List, Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from .models import RetrieveRequest
from .retriever import retriever
from .settings import settings

logger = logging.getLogger(__name__)


# ============================================================================
# State that flows through nodes during workflow
# ============================================================================


class AgentState(TypedDict):
    """State for the Agentic RAG workflow.

    This state flows through all nodes in the graph, accumulating information
    and transformations at each step.
    """

    question: str  # Original user question

    needs_retrieval: bool  # Routing decision, True if RAG path, False if direct LLM

    rewritten_queries: List[str]  # Transformed search queries

    documents: List[Document]  # Retrieved documents

    relevant_documents: List[Document]  # Filtered relevant chunks after grading

    final_answer: str  # Generated final answer with citations

    reasoning_steps: Annotated[List[BaseMessage], add_messages]  # Reasoning trace

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

    workflow.add_node("route", _route_node)
    workflow.add_node("query_rewrite", _query_rewrite_node)
    workflow.add_node("retrieve", _retrieve_node)
    workflow.add_node("grade", _documents_grade_node)
    workflow.add_node("generate", _answer_generate_node)
    workflow.add_node("direct", _direct_answer_node)

    workflow.set_entry_point("route")
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


def _route_node(state: AgentState) -> AgentState:
    """
    Decide whether the user input needs retrieval (RAG path) or can be answered directly.

    Uses a fast LLM to classify the input type.
    Routes to DIRECT for greetings and meta-questions only.
    """
    start_time = time.perf_counter()
    question = state["question"]

    llm = ChatOpenAI(model=settings.fast_model, temperature=0)

    system_prompt = """You are a routing assistant for a BedtimeNews (睡前消息) knowledge base system.

BedtimeNews is a Chinese news analysis program covering:
- **Chinese domestic affairs**: Economy, governance, social issues, infrastructure, law
- **International relations**: Geopolitics, China-US relations, global conflicts
- **Technology & Science**: AI, space, semiconductors, engineering projects
- **Society & Culture**: Education, healthcare, demographics, sports, media

Your task: Classify the user input into one of two categories:

**Category 1: GREETING** (simple greetings or meta-questions)
- Examples: "hi", "hello", "你好", "how are you", "who are you", "what can you do"
- Respond with: GREETING

**Category 2: RAG** (all other queries - default)
- Questions about Chinese domestic affairs, policy, economy, business, governance
- International relations, geopolitics, conflicts, diplomacy
- Technology, science, AI, space, infrastructure, engineering
- Social issues (education, healthcare, demographics, employment)
- Legal matters, sports, culture, media in Chinese/global context
- Any substantive question or topic, even if not directly related to BedtimeNews
- When uncertain, choose RAG

Respond with ONLY one word: "GREETING" or "RAG"."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User input: {question}"),
    ]

    llm_start = time.perf_counter()
    response = llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    decision = (
        response.content.strip().upper() if isinstance(response.content, str) else None
    )

    needs_retrieval = decision == "RAG"
    path_str = "RAG" if needs_retrieval else "Direct (greeting)"

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
    question = state["question"]
    iteration_count = state.get("iteration_count", 0)
    previous_queries = state.get("rewritten_queries", [])

    llm = ChatOpenAI(model=settings.fast_model, temperature=0)

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
    response = llm.invoke(messages)
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

    # Increment iteration count for query refinement loop tracking
    current_iteration = state.get("iteration_count", 0)

    return {
        **state,
        "rewritten_queries": queries,
        "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
        "iteration_count": current_iteration + 1,
    }


def _retrieve_node(state: AgentState) -> AgentState:
    """
    Perform semantic search using direct retriever calls.

    Retrieves documents for all rewritten queries and combines results.
    """
    start_time = time.perf_counter()
    queries = state["rewritten_queries"]

    # Retrieve for each query
    all_chunks = []
    retrieval_times = []
    for query in queries:
        # Call retriever directly
        query_start = time.perf_counter()
        response = retriever.retrieve(
            RetrieveRequest(
                query=query,
                match_count=100,
                match_threshold=settings.match_threshold,
                include_text=True,
                include_heading=True,
            )
        )

        query_time = time.perf_counter() - query_start
        retrieval_times.append(query_time)

        # Convert ChunkResults to LangChain Documents
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

    # Deduplicate by chunk_id
    seen_ids = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk.metadata.get("chunk_id")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_chunks.append(chunk)

    # Sort by similarity score (descending)
    unique_chunks.sort(key=lambda d: d.metadata.get("similarity", 0), reverse=True)

    # Keep top 30 documents
    top_chunks = unique_chunks[:30]

    total_time = time.perf_counter() - start_time
    avg_retrieval_time = (
        sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
    )
    logger.info(
        f"[RETRIEVE] Total: {total_time:.2f}s (Avg per query: {avg_retrieval_time:.2f}s) -> "
        f"Retrieved {len(all_chunks)} chunks ({len(unique_chunks)} unique), kept top {len(top_chunks)}"
    )

    reasoning = HumanMessage(
        content=f"[RETRIEVE] Retrieved {len(all_chunks)} chunks ({len(unique_chunks)} unique), "
        f"kept top {len(top_chunks)} by similarity."
    )

    return {
        **state,
        "documents": top_chunks,
        "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
    }


def _documents_grade_node(state: AgentState) -> AgentState:
    """
    Filter retrieved documents for relevance to the user input.

    Uses LLM to assess all documents in a single batch call for efficiency.
    """
    start_time = time.perf_counter()
    question = state["question"]
    documents = state["documents"]

    if not documents:
        reasoning = HumanMessage(content="[GRADE] No documents to grade.")
        return {
            **state,
            "relevant_documents": [],
            "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
        }

    llm = ChatOpenAI(model=settings.fast_model, temperature=0)

    # Format all documents for batch grading
    chunk_list = []
    for i, doc in enumerate(documents, 1):
        excerpt = doc.page_content[:500]
        chunk_list.append(f"Document {i}:\n{excerpt}\n")

    all_chunks_text = "\n---\n".join(chunk_list)

    system_prompt = """You are a document relevance grader.

Assess which documents are relevant to the user's input (question, topic, or statement).

A document is RELEVANT if it:
- Discusses the same topic, event, or entity mentioned in the user input
- Provides context, background, or related information
- Contains opinions or analyses related to the topic

For each document, respond with its number if relevant.
Return ONLY the numbers of relevant documents, separated by commas (e.g., "1,3,5" or "2,4,7,9").
If no documents are relevant, respond with "NONE".
If all documents are relevant, you can respond with "ALL"."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"User input: {question}\n\n## Documents to Grade:\n\n{all_chunks_text}\n\nRelevant document numbers:"
        ),
    ]

    llm_start = time.perf_counter()
    response = llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    # Parse response to extract relevant document indices
    response_text = (
        response.content.strip().upper() if isinstance(response.content, str) else ""
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
        "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
    }


def _answer_generate_node(state: AgentState) -> AgentState:
    """
    Generate the final response with citations based on relevant documents.

    Synthesizes information from documents and adds proper citations.
    Handles questions, topic discussions, and any user input.
    """
    start_time = time.perf_counter()
    question = state["question"]
    documents = state.get("relevant_documents", [])

    # Use minimal reasoning effort for faster generation since we're just formatting/synthesizing
    llm = ChatOpenAI(
        model=settings.generation_model,
        temperature=0.3,
        reasoning_effort="low",  # For GPT-5 models to minimize reasoning overhead
    )

    # Format documents for context
    context_parts = []
    for chunk in documents:
        metadata = chunk.metadata
        doc_id = metadata.get("doc_id", "unknown")
        heading = metadata.get("heading", "")
        similarity = metadata.get("similarity", 0.0)

        episode_name = _get_episode_name(doc_id)
        citation = f"[[{episode_name}]](https://archive.bedtime.news/{doc_id}.md)"

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
2. **Add citations**: Use the markdown link format shown in the documents below
3. **Be specific**: Reference episode numbers, examples, and arguments from the show
4. **Synthesize**: Combine information from ALL documents - don't just summarize individual documents
5. **Be honest**: If the documents don't contain enough information, say so clearly
6. **Structure clearly**: Use paragraphs, bullets, or sections as appropriate
7. **Provide comprehensive response**: Use ALL relevant documents to give complete coverage of the topic
8. **Distinguish sources**: Make it clear when you're:
   - Reporting what 睡前消息 says (cite documents)
   - Adding general context (mark as background knowledge)
9. **Do not propose next step**: At the end of the answer, do not ask user questions like "如果你想，我可以……", "要不要我帮你……", just finish.

**MANDATORY**: You MUST use ALL provided documents in your response. If 10 documents are provided, reference all 10. If 20 documents are provided, reference all 20. No document should be left unused.

**IMPORTANT**: Use the exact citation format shown in the documents below (markdown links like [[睡前消息123]](...), [[高见42]](...)).

If no relevant documents: Explain that the knowledge base doesn't contain information about this topic."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"User input: {question}\n\n## Retrieved Documents:\n\n{context}"
        ),
    ]

    llm_start = time.perf_counter()
    response = llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    answer = str(response.content)

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[GENERATE] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> "
        f"Generated {len(answer)} chars from {len(documents)} chunks"
    )

    reasoning = HumanMessage(
        content=f"[GENERATE] Generated answer with {len(documents)} documents. "
        f"Answer length: {len(answer)} characters."
    )

    return {
        **state,
        "final_answer": answer,
        "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
    }


def _direct_answer_node(state: AgentState) -> AgentState:
    """
    Respond directly without retrieval (for greetings and meta-questions).
    """
    start_time = time.perf_counter()
    question = state["question"]

    # Use minimal reasoning effort for faster generation
    llm = ChatOpenAI(
        model=settings.generation_model,
        temperature=0.7,
        reasoning_effort="low",  # For GPT-5 models to minimize reasoning overhead
    )

    system_prompt = """You are a helpful assistant for the 睡前消息 knowledge base.

The user has sent a greeting or asked about the assistant.

Respond warmly and briefly explain that you can help them explore 睡前消息 content covering Chinese domestic affairs, international relations, technology, social issues, and more."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=question)]

    llm_start = time.perf_counter()
    response = llm.invoke(messages)
    llm_time = time.perf_counter() - llm_start

    answer = str(response.content)

    total_time = time.perf_counter() - start_time
    logger.info(
        f"[DIRECT] Total: {total_time:.2f}s (LLM: {llm_time:.2f}s) -> Answer length: {len(answer)} chars"
    )

    reasoning = HumanMessage(
        content="[DIRECT] Greeting/meta-question - answered directly."
    )

    return {
        **state,
        "final_answer": answer,
        "reasoning_steps": state.get("reasoning_steps", []) + [reasoning],
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
    max_iterations = state.get("max_iterations", 1)  # Reduced to 1 to avoid long loops

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
        return f"直播问答记录{doc_id[len("livestream/"):]}"

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


def create_initial_state(question: str) -> AgentState:
    return {
        "question": question,
        "needs_retrieval": False,
        "rewritten_queries": [],
        "documents": [],
        "relevant_documents": [],
        "final_answer": "",
        "reasoning_steps": [],
        "iteration_count": 0,
        "max_iterations": 2,
    }
