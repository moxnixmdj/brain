"""Keeping a test run from mutating the creature's persistent memory.

The decomposition law now consults and updates `canonical/runtime/state/experience_v1.json`,
so measuring in a test writes product state into the working tree. Measured before this
existed: a full run added dozens of lines to that file, which means CI and a laptop
disagreed depending on what had already been recorded, and `git status` was dirty after
every pytest run.

This is a small helper rather than a `conftest.py` fixture for a reason. The referee
forbids conftest from importing the runtime, writing attributes, or defining hooks, and it
is right to: conftest is imported before collection, so anything it does is invisible and
an import failure there is swallowed and reported as a collection error. A fixture that
says what it is doing, in the file that needs it, is honest.

Usage, in any module that asks the door a question:

    from canonical.tests._memory import no_persistent_memory

    @pytest.fixture(autouse=True)
    def _quiet():
        with no_persistent_memory():
            yield
"""

from __future__ import annotations

import contextlib


@contextlib.contextmanager
def no_persistent_memory():
    """Measure without remembering, for the duration of the block."""
    from canonical.runtime import decomposition_law_v1 as D

    was = D.REMEMBER
    D.REMEMBER = False
    D._CACHE.clear()
    try:
        yield
    finally:
        D.REMEMBER = was
        D._CACHE.clear()
