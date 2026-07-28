"""Run each workspace component in an isolated pytest process.

Agent and indexer both expose a top-level ``src`` package, so importing their
tests into one interpreter would resolve one component's modules as the other.
For a bare workspace-root invocation, this hook transparently runs pytest once
per component instead. Component-scoped invocations use that component's
pyproject.toml as their root and never load this file.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parent
COMPONENTS = ("agent", "indexer", "frontend")


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config):
    """Forward root invocations and their options to isolated component runs."""
    if config.rootpath != REPOSITORY_ROOT:
        return None

    command = [sys.executable, "-m", "pytest", *config.invocation_params.args]
    for component in COMPONENTS:
        print(f"\n== pytest {component} ==", flush=True)
        result = subprocess.run(command, cwd=REPOSITORY_ROOT / component, check=False)
        if result.returncode:
            return result.returncode
    return pytest.ExitCode.OK
