import ast
import re
from pathlib import Path

from src.graph import FOLLOWUPS_DELIMITER

REPOSITORY_ROOT = Path(__file__).parents[2]
APP_JS = REPOSITORY_ROOT / "frontend" / "static" / "app.js"
BACKEND_EVENT_SOURCES = [
    REPOSITORY_ROOT / "agent" / "src" / "agent.py",
    REPOSITORY_ROOT / "agent" / "src" / "chat.py",
]


def _backend_event_types():
    event_types = set()
    for source in BACKEND_EVENT_SOURCES:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "type"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    event_types.add(value.value)
    return event_types


def test_frontend_stream_contract_matches_backend():
    app_js = APP_JS.read_text(encoding="utf-8")
    delimiter = re.search(
        r'^const FOLLOWUPS_DELIMITER = "([^"]+)";$', app_js, re.MULTILINE
    )
    assert delimiter
    assert delimiter.group(1) == FOLLOWUPS_DELIMITER

    frontend_event_types = set(re.findall(r'case "([a-z_]+)":', app_js))
    assert frontend_event_types == _backend_event_types()
