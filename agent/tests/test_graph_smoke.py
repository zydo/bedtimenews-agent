"""End-to-end smoke test for the streaming contract.

The agent depends on LangChain and LangGraph behaviour that is not public API:

  * ``astream_events(version="v2")`` must emit ``on_chat_model_stream`` while a
    node is running a *blocking* ``.invoke()`` — that is the only reason tokens
    reach the browser at all.
  * every event must carry ``metadata.langgraph_node``, which is what routes
    reasoning steps, the citation map and the final answer to the right place.

Neither is covered by a type checker or by the linters, and a dependency bump
can change either without anything going red. This test drives the real compiled
graph with a stubbed chat model, so a regression in that contract fails here
instead of silently shipping an agent that no longer streams.

No credentials, no network, no database: the chat models, the retriever and the
chunk-text fetch are all replaced.
"""

import asyncio
import re

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from src import agent as agent_mod
from src import graph as graph_mod
from src.models import ChunkResult, RetrieveResponse

ANSWER = "鹤岗是资源枯竭型城市的代表 [[参考信息490]](https://archive.bedtime.news/reference/401-500/490.md)。"
FOLLOWUPS = ["鹤岗的房价现在怎么样？", "还有哪些收缩型城市？"]

# What the generation model returns: the answer, the delimiter, then suggestions.
GENERATION_OUTPUT = f"{ANSWER}\n\n{graph_mod.FOLLOWUPS_DELIMITER}\n" + "\n".join(
    FOLLOWUPS
)


class _ScriptedFastModel(GenericFakeChatModel):
    """Answers the fast-model nodes in the order the graph calls them."""


def _fake_chunk(i: int) -> ChunkResult:
    return ChunkResult(
        chunk_id=f"chunk-{i}",
        doc_id=f"reference/401-500/{490 + i}",
        chunk_index=i,
        heading="大家好，欢迎收看睡前消息",  # deliberately uninformative, as in the corpus
        text=None,
        word_count=800,
        similarity=0.7 - i * 0.01,
        rank=i + 1,
    )


class _FakeRetriever:
    def retrieve_batch(self, requests):
        return [
            RetrieveResponse(
                query=r.query,
                match_threshold=r.match_threshold,
                match_count=r.match_count,
                results=[_fake_chunk(i) for i in range(3)],
            )
            for r in requests
        ]


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace every outbound dependency of the graph."""
    # route -> RAG, query_rewrite -> one query, grade -> both documents relevant.
    fast = GenericFakeChatModel(messages=iter(["RAG", "鹤岗 收缩型城市", "1,2,3"]))
    generation = GenericFakeChatModel(messages=iter([GENERATION_OUTPUT]))

    monkeypatch.setattr(graph_mod, "_fast_llm", fast)
    monkeypatch.setattr(graph_mod, "_generation_llm", generation)
    monkeypatch.setattr(graph_mod, "retriever", _FakeRetriever())
    monkeypatch.setattr(
        graph_mod,
        "fetch_chunk_texts",
        lambda ids: {i: f"关于鹤岗的正文内容 {i}" for i in ids},
    )


def _collect(question, history=None):
    async def run():
        return [e async for e in agent_mod.agent_stream_query(question, history)]

    return asyncio.run(run())


def test_streaming_turn_emits_the_documented_event_sequence(stub_pipeline):
    events = _collect("鹤岗为什么成了收缩型城市的代表？")
    kinds = [e["type"] for e in events]

    # The token stream is the contract most likely to break on an upgrade: it
    # only exists because astream_events surfaces on_chat_model_stream from a
    # blocking .invoke() inside the generate node.
    assert "answer_chunk" in kinds, (
        "no answer_chunk events — astream_events stopped surfacing "
        "on_chat_model_stream, so the UI would show nothing while generating"
    )

    streamed = "".join(e["content"] for e in events if e["type"] == "answer_chunk")
    assert "鹤岗" in streamed

    # Steps depend on metadata.langgraph_node being present and matching the
    # node names in _NODE_STEP_TYPES.
    steps = {e["step"] for e in events if e["type"] == "step"}
    assert {"route", "rewrite", "retrieve", "grade"} <= steps, (
        f"missing pipeline steps, got {steps} — langgraph_node metadata or the "
        "node names changed"
    )

    # Grading kept documents, so the citation map must reach the client before
    # the answer does; otherwise citations stay dead text for the whole answer.
    citations = [e for e in events if e["type"] == "citations"]
    assert citations, "no citations event — client cannot linkify while streaming"
    assert kinds.index("citations") < kinds.index("answer_chunk")

    # Exactly one terminal event carrying groundedness.
    terminal = [e for e in events if e["type"] in ("answer_final", "answer_meta")]
    assert len(terminal) == 1, f"expected one terminal event, got {terminal}"
    assert terminal[0]["grounded"] is True


def test_followups_are_split_out_of_the_answer(stub_pipeline):
    events = _collect("鹤岗为什么成了收缩型城市的代表？")

    followups = [e for e in events if e["type"] == "followups"]
    assert followups, "no followups event"
    assert followups[0]["items"] == FOLLOWUPS

    # The delimiter must never survive into the answer the client renders.
    terminal = next(e for e in events if e["type"] in ("answer_final", "answer_meta"))
    if terminal["type"] == "answer_final":
        assert graph_mod.FOLLOWUPS_DELIMITER not in terminal["content"]
        assert FOLLOWUPS[0] not in terminal["content"]


def test_condense_rewrites_a_follow_up_against_history(monkeypatch):
    """A follow-up must be resolved before routing, retrieval or grading see it."""
    seen_queries = []

    class _RecordingRetriever(_FakeRetriever):
        def retrieve_batch(self, requests):
            seen_queries.extend(r.query for r in requests)
            return super().retrieve_batch(requests)

    # condense -> standalone question, then route / rewrite / grade.
    fast = GenericFakeChatModel(
        messages=iter(["鹤岗的房价现在怎么样？", "RAG", "鹤岗 房价", "1"])
    )
    monkeypatch.setattr(graph_mod, "_fast_llm", fast)
    monkeypatch.setattr(
        graph_mod, "_generation_llm", GenericFakeChatModel(messages=iter([ANSWER]))
    )
    monkeypatch.setattr(graph_mod, "retriever", _RecordingRetriever())
    monkeypatch.setattr(
        graph_mod, "fetch_chunk_texts", lambda ids: {i: "正文" for i in ids}
    )

    history = [
        {
            "question": "鹤岗为什么成了收缩型城市的代表？",
            "answer": "鹤岗是资源枯竭型城市。",
            "grounded": True,
        }
    ]
    events = _collect("那它的房价现在怎么样？", history)

    condensed = [e for e in events if e.get("step") == "condense"]
    assert condensed, "condense produced no step — the rewrite was not surfaced"
    assert "鹤岗" in condensed[0]["content"], (
        "the pronoun was not resolved against history; retrieval would search "
        "for the wrong subject"
    )
    assert seen_queries, "retrieval never ran"


def test_single_turn_skips_condense(stub_pipeline):
    """With no history there is nothing to resolve, so no extra model call."""
    events = _collect("鹤岗为什么成了收缩型城市的代表？")
    assert not [e for e in events if e.get("step") == "condense"]


@pytest.mark.parametrize(
    "raw,expected_answer,expected_followups",
    [
        (f"答案。\n{graph_mod.FOLLOWUPS_DELIMITER}\n问题一？\n问题二？", "答案。", 2),
        ("没有分隔符的普通答案。", "没有分隔符的普通答案。", 0),
        (f"答案。\n{graph_mod.FOLLOWUPS_DELIMITER}\n", "答案。", 0),
    ],
)
def test_followup_split_degrades_safely(raw, expected_answer, expected_followups):
    answer, followups = graph_mod._split_followups(raw)
    assert answer == expected_answer
    assert len(followups) == expected_followups


def test_uncited_answer_gets_a_source_list(monkeypatch):
    """A grounded answer must never reach the reader with nothing to check.

    The repair pass can only rewrite citations that are present. When the model
    omits them entirely — observed in the wild on an answer built from six
    documents — the result is fluent, specific and completely unattributed.
    """
    uncited = "SHEIN的成功来自珠三角产业链与数据驱动的供应链。"
    fast = GenericFakeChatModel(messages=iter(["RAG", "SHEIN 出海", "1,2,3"]))
    monkeypatch.setattr(graph_mod, "_fast_llm", fast)
    monkeypatch.setattr(
        graph_mod, "_generation_llm", GenericFakeChatModel(messages=iter([uncited]))
    )
    monkeypatch.setattr(graph_mod, "retriever", _FakeRetriever())
    monkeypatch.setattr(
        graph_mod, "fetch_chunk_texts", lambda ids: {i: "正文" for i in ids}
    )

    events = _collect("SHEIN出海为什么成功？")
    terminal = next(e for e in events if e["type"] in ("answer_final", "answer_meta"))

    # Appending sources is invisible to the token stream, so the canonical text
    # has to be re-sent or the reader keeps the uncited version.
    assert terminal["type"] == "answer_final", (
        "sources were appended but answer_final was not sent, so the client "
        "would still be showing the uncited answer"
    )
    assert "](https://archive.bedtime.news/" in terminal["content"]
    assert "参考来源" in terminal["content"]
    assert uncited in terminal["content"], "the model's answer must be preserved"


def test_source_list_is_not_appended_when_the_model_cited(stub_pipeline):
    """The fallback must stay out of the way when the model behaved."""
    events = _collect("鹤岗为什么成了收缩型城市的代表？")
    answer = "".join(e["content"] for e in events if e["type"] == "answer_chunk")
    terminal = next(e for e in events if e["type"] in ("answer_final", "answer_meta"))
    text = terminal.get("content", answer)
    assert "参考来源" not in text


def test_citation_repair_covers_both_spellings():
    citation_map = {
        "产经破壁机67": "[[产经破壁机67]](https://archive.bedtime.news/business/67.md)"
    }
    for raw in ("见 [[产经破壁机67]] 的分析", "见 《产经破壁机67》 的分析"):
        repaired, count = graph_mod._repair_citations(raw, citation_map)
        assert count == 1
        assert "https://archive.bedtime.news/business/67.md" in repaired

    # A real book title shares the 《》 spelling but is not a known episode.
    untouched, count = graph_mod._repair_citations("他读了《三体》", citation_map)
    assert count == 0
    assert untouched == "他读了《三体》"


def test_streamed_text_matches_final_when_no_repair_needed(stub_pipeline):
    """answer_meta is only safe if the client can reproduce the answer itself."""
    events = _collect("鹤岗为什么成了收缩型城市的代表？")
    terminal = next(e for e in events if e["type"] in ("answer_final", "answer_meta"))
    if terminal["type"] != "answer_meta":
        pytest.skip("a repair occurred, so the server had to re-send the answer")

    streamed = "".join(e["content"] for e in events if e["type"] == "answer_chunk")
    # What the client does: strip from the delimiter onward.
    client_view = streamed.split(graph_mod.FOLLOWUPS_DELIMITER)[0].strip()
    assert re.sub(r"\s+", "", client_view) == re.sub(r"\s+", "", ANSWER)
