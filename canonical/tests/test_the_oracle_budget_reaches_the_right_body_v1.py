"""Position is part of the mechanism: a correct body the oracle never reaches is not a candidate.

Measured failure this pins. Each judging chunk was given `per_body_seconds * chunk` = 125 s out
of a 180 s deadline, so the SECOND chunk already exhausted the budget and every candidate past
roughly position 50 was unreachable, however correct. scipy 133's passing body
(`median_filter(A,size=size,axes=[1,2])`) sat at index 247 of 600 -- inside MAX_CANDIDATES, in
the search space, and never executed. It read as eight separate scipy filter failures; it was
one budget bug.

The fix is not a bigger timeout. It is that a chunk's allowance must be its FAIR SHARE of the
remaining budget, so no chunk can starve the ones after it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import body_grammar_v1 as G  # noqa: E402


def test_a_mid_definition_stub_is_completed_from_its_own_imports_and_prose():
    """pytest 228: the stub ends at `def pytest_ignore_collect(`. The reference body is the
    parameter declaration, the closing paren and `pass`. The prose states the parameter's
    meaning and the stub's own `import pathlib` states its type."""
    cands = G.compositions(
        [], {}, problem="defines a hook function named pytest_ignore_collect which takes a "
                        "single parameter (representing a filesystem collection path)",
        stub_source="import pytest\nimport pathlib\n\n@pytest.hookimpl()\n"
                    "def pytest_ignore_collect(",
    )
    bodies = [c["body"] for c in cands]
    assert any(b.endswith("):\n    pass") for b in bodies), bodies[:6]
    # the stated noun is "filesystem ... path", and the artifact's own convention is
    # `<noun>_path`, so that spelling must be offered FIRST rather than after the bare noun --
    # the bare noun also passes, but only because this hook accepts any parameter name, and a
    # test that pins a coincidence pins nothing
    assert bodies[0].startswith("filesystem_path:"), bodies[:3]


def test_the_axis_form_of_a_stated_ordinal_is_emitted_early_enough_to_be_tried():
    """`batched in the first dimention` is `axes=[1,2]`. Emitting it at the END of a 600-body
    space is the same as not emitting it, because the deadline never reaches the end."""
    cands = G.compositions(
        ["A", "size"], {}, problem="applies a median filter on batched images "
                                   "(batched in the first dimention)",
        stated_symbols=["median_filter"],
        stub_imports=["from scipy.ndimage import median_filter"],
        stub_source="from scipy.ndimage import median_filter\n"
                    "def f(A, size):",
    )
    bodies = [c["body"] for c in cands]
    want = "return median_filter(A, size=size, axes=[1, 2])"
    assert want in bodies, bodies[:12]
    # and it must be near the front: within the first chunks the deadline actually reaches
    assert bodies.index(want) < 200, bodies.index(want)
