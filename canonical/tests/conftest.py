"""Global test hygiene for the runtime suites.

A TEST RUN MUST NOT MUTATE THE COMMITTED EXPERIENCE STORE.

Measured: running the answer-path suites wrote dozens of lines into
`canonical/runtime/state/experience_v1.json`, because the decomposition law now consults
and updates the creature's persistent memory. That makes a test run a change to product
state -- CI and a laptop would disagree depending on what had already been recorded, and
the repository would drift every time anybody ran pytest.

Memory is a product behaviour. Tests still exercise it, but through `path=` fixtures that
point at a temporary file; the default store is never touched from a test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_persistent_memory(monkeypatch):
    from canonical.runtime import decomposition_law_v1 as D

    monkeypatch.setattr(D, "REMEMBER", False)
    D._CACHE.clear()
    yield
    D._CACHE.clear()
