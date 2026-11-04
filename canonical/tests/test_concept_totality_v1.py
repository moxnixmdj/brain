"""A concept must be defined on the domain it claims.

Measured before this existed: **2 of 2 admitted concepts raised on the repository's own numeric probe
grid.** The verification loop did `except Exception: continue`, so probes that raised were skipped
rather than counted, and the library certified the subdomain where the expression happened to
survive. Every probe in the original grid had distinct coordinates, which meant a division by
`(_v2 - _v1)` was never once evaluated at the input where it dies.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    CompoundingConceptLibrary,
    _generate_probe_grids,
)

GUARDED = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0"
UNGUARDED = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1)"
DISTANCE = "max(_v0, _v1) - min(_v0, _v1)"
MEAN = "(_v0 + _v1) / 2.0"
RECIPROCAL = "1.0 / _v0"

TRIPLES = [("val", "lo", "hi"), ("u", "a", "b"), ("x", "mn", "mx"), ("t", "low", "high"),
           ("q", "pp", "qq"), ("zz", "k0", "k1"), ("mm", "n0", "n1"), ("hh", "g0", "g1")]


def _library(tmp_path: Path) -> CompoundingConceptLibrary:
    return CompoundingConceptLibrary(tmp_path / "library.json")


def _corpus() -> list[str]:
    out = []
    for i, v in enumerate(TRIPLES):
        out.append("def na%d(%s):\n    return (min(max(%s, %s), %s) - %s) / (%s - %s)"
                   " if %s > %s else 0.0" % (i, ", ".join(v), v[0], v[1], v[2],
                                             v[1], v[2], v[1], v[2], v[1]))
    return out


def test_unguarded_division_is_rejected(tmp_path):
    """The exact concept the old gate admitted and then handed to the search as a building block."""
    ok, reason = _library(tmp_path)._verify_candidate_concept(UNGUARDED, 3)
    assert not ok
    assert reason.startswith("PARTIAL_DOMAIN:numeric:")


def test_guarded_form_of_the_same_idea_is_admitted(tmp_path):
    """The corpus contained both forms. The gate must prefer the total one, not merely reject."""
    ok, _ = _library(tmp_path)._verify_candidate_concept(GUARDED, 3)
    assert ok


def test_total_concepts_are_still_admitted(tmp_path):
    library = _library(tmp_path)
    assert library._verify_candidate_concept(DISTANCE, 2)[0]
    assert library._verify_candidate_concept(MEAN, 2)[0]


def test_unguarded_reciprocal_is_rejected(tmp_path):
    assert not _library(tmp_path)._verify_candidate_concept(RECIPROCAL, 1)[0]


def test_probe_grid_includes_equal_arguments():
    """Without these the grid never evaluates `a - b` at `a == b`, which is the silent hole."""
    numeric = _generate_probe_grids(3)[0][1]
    assert any(len(set(row)) == 1 for row in numeric), "no equal-argument probe in the numeric grid"


def test_no_admitted_concept_raises_on_its_own_domain(tmp_path):
    """The measurement that was 2/2 before the fix."""
    library = _library(tmp_path)
    library.sleep_abstract(_corpus() + _corpus())
    grown = _library(tmp_path)
    concepts = list(grown.concepts())
    assert concepts, "the corpus must admit something, or this test measures nothing"
    callables = grown.callable_map()
    for concept in concepts:
        fn = callables[concept.concept_id]
        for row in _generate_probe_grids(concept.arity)[0][1]:
            try:
                fn(*row)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"{concept.concept_id} raises {type(exc).__name__} on {row}")


def test_rejection_reason_names_the_failure():
    """A rejection must say what went wrong, not just that something did."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        library = CompoundingConceptLibrary(Path(tmp) / "l.json")
        ok, reason = library._verify_candidate_concept(UNGUARDED, 3)
        assert not ok
        assert "ZeroDivisionError" in reason or "PARTIAL_DOMAIN" in reason
