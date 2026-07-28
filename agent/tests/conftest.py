"""Test environment for the agent package.

`src.settings` resolves provider-prefixed model names at import time and raises
if they are missing, and `src.graph` builds chat models at import time too. These
values are set before any `src.*` module is imported so the suite runs with no
real credentials, no network and no database.
"""

import os

os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")
os.environ.setdefault("OPENAI_FAST_MODEL", "test-fast-model")
os.environ.setdefault("OPENAI_GENERATION_MODEL", "test-generation-model")
os.environ.setdefault("OPENAI_EMBEDDING_MODEL", "test-embedding-model")
