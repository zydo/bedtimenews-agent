"""Workspace-root pytest guard.

This conftest is only loaded when pytest is invoked with the workspace root as
its rootdir (e.g. a bare `uv run pytest` at the repo root). That invocation
cannot work: agent/ and indexer/ each define their own top-level `src` package,
and two different packages with the same name cannot coexist in one Python
process. Tests must run one process per component, which resolves the correct
`src` via each component's pyproject.toml.

Component-scoped runs (`cd agent && uv run pytest`, or
`uv run pytest agent/tests` from the root) use the component's pyproject.toml
as rootdir and never load this file.
"""

import pytest


def pytest_configure(config):
    raise pytest.UsageError(
        "Running pytest from the workspace root is not supported: agent/ and "
        "indexer/ both define a `src` package and must be tested in separate "
        "processes. Run one component at a time instead:\n"
        "  uv run pytest agent/tests\n"
        "  uv run pytest indexer/tests\n"
        "or, equivalently: (cd agent && uv run pytest). "
        "CI runs the same per-component loop (see .github/workflows/ci.yml)."
    )
