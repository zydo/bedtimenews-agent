"""Unit tests for config-based file filtering."""

from src import file_scanner
from src.file_scanner import _should_include_file


def _make_file(base, rel_path, size):
    path = base / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return rel_path


class TestShouldIncludeFile:
    def test_included_when_matches_include_and_size_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        _make_file(tmp_path, "episode.md", size=100)
        config = {"include": ["*.md"]}
        assert _should_include_file("episode.md", config) is True

    def test_excluded_when_not_matching_include(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        config = {"include": ["*.txt"]}  # .md does not match -> excluded early
        assert _should_include_file("episode.md", config) is False

    def test_excluded_when_matches_exclude(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        config = {"exclude": ["draft_*.md"]}
        assert _should_include_file("draft_episode.md", config) is False

    def test_rejected_when_below_min_size(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        _make_file(tmp_path, "tiny.md", size=5)
        config = {"validation": {"min_file_size": 100}}
        assert _should_include_file("tiny.md", config) is False

    def test_rejected_when_above_max_size(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        _make_file(tmp_path, "huge.md", size=200)
        config = {"validation": {"max_file_size": 100}}
        assert _should_include_file("huge.md", config) is False

    def test_empty_config_includes_any_sized_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_scanner, "BEDTIMENEWS_ARCHIVE_CONTENTS_DIR", tmp_path)
        _make_file(tmp_path, "anything.md", size=50)
        assert _should_include_file("anything.md", {}) is True
