import json
from types import SimpleNamespace

from src import eval_retriever


class _FakeRetriever:
    def __init__(self, results_by_query):
        self.results_by_query = results_by_query

    def retrieve(self, request):
        doc_ids = self.results_by_query[request.query]
        results = [
            SimpleNamespace(doc_id=doc_id) for doc_id in doc_ids[: request.match_count]
        ]
        return SimpleNamespace(results=results)


def test_labelled_set_has_twenty_known_queries():
    labels = eval_retriever._load_labelled_queries()

    assert len(labels) == 20
    assert all(label["doc_id"] for label in labels)


def test_labelled_run_calculates_recall_at_k(monkeypatch):
    queries = [
        {"category": "one", "query": "hit", "doc_id": "doc-good"},
        {"category": "two", "query": "miss", "doc_id": "doc-missing"},
    ]
    fake = _FakeRetriever(
        {
            "hit": ["doc-other", "doc-good"],
            "miss": ["doc-other"],
        }
    )
    monkeypatch.setattr(eval_retriever, "retriever", fake)

    result = eval_retriever._run_retrieval_test(
        queries, match_count=2, match_threshold=0.5
    )

    assert result["metrics"]["recall@2"] == 0.5
    assert result["metrics"]["hits"] == 1
    assert result["queries"][0]["relevant_rank"] == 2
    assert result["queries"][1]["relevant_rank"] is None


def test_run_history_appends_without_discarding_previous_results(tmp_path):
    results_file = tmp_path / "retriever.json"

    eval_retriever._append_run_result(results_file, {"run_label": "before"})
    eval_retriever._append_run_result(results_file, {"run_label": "after"})

    assert results_file.read_text(encoding="utf-8").endswith("\n")
    history = json.loads(results_file.read_text(encoding="utf-8"))
    assert [run["run_label"] for run in history["runs"]] == ["before", "after"]
