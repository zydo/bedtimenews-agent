"""Shared test fixtures/config for the indexer.

The indexer's `settings` module validates a required embedding-model env var at
import time, and some modules under test (e.g. change_detector -> vector_db ->
settings) import it transitively. Provide a dummy value so those imports succeed
without a real .env. `setdefault` leaves any real value in place.
"""

import os

os.environ.setdefault("OPENAI_EMBEDDING_MODEL", "test-embedding-model")
