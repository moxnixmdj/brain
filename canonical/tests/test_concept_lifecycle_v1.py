"""A library that can be wrong about itself.

Before 2026-11-04 the concept library could only accumulate: `helped=False` was never called
anywhere, the synthesizer credited a concept for being *emitted*, and `log_prior` had no term that
could lower it. Measured consequence: 20 junk concepts filled all 16 slots the search can see and
generalising reach fell 2/2 -> 0/2. These tests hold the three fixes in place.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.generalization_check_v1 import classify  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    SCHEMA,
    CompoundingConceptLibrary,
)

NORMALISE = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0"
TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]


def _reference(v, l, h):
    return (min(max(v, l), h) - l) / (h - l) * 2.0 if h > l else 0.0


def _concept(cid, body, *, corpus_sites):
    return {"concept_id": cid, "arity": 3, "param_names": ["_v0", "_v1", "_v2"],
            "body_expr": body, "domain_kind": "numeric", "mdl_gain_bytes": 50,
            "corpus_sites": corpus_sites, "uses": 0, "verified_hits": 0,
            "disconfirmations": 0}


def _library(tmp_path: Path, concepts: dict) -> Path:
    path = tmp_path / "library.json"
    path.write_text(json.dumps({"schema": SCHEMA, "concepts": concepts}))
    return path


def _ask(path: Path):
    library = CompoundingConceptLibrary(path)
    body = synthesize_python_function_body(
        ["v", "l", "h"], [(p, _reference(*p)) for p in TRAIN],
        extra_constants=(2.0,), max_weight=4, concept_library=library)
    verdict, _ = classify(body, ["v", "l", "h"], [(p, _reference(*p)) for p in HELD])
    return verdict, body


def test_emitting_a_body_is_not_verification(tmp_path):
    """The credit bug: `helped=True` fired when a body was emitted, before any verdict.

    Measured before the fix: a concept used only inside WRONG bodies reached verified_hits=1.
    """
    path = _library(tmp_path, {"concept_norm0001": _concept(
        "concept_norm0001", NORMALISE, corpus_sites=8)})
    _ask(path)
    entry = CompoundingConceptLibrary(path).concepts()[0]
    assert entry.uses == 1, "the concept was emitted into a body, so it was used"
    assert entry.verified_hits == 0, "nothing verified it, so it gets no credit"


def test_a_helpful_verdict_still_credits(tmp_path):
    """The fix must not make the record write-only: real evidence still counts."""
    path = _library(tmp_path, {"concept_norm0001": _concept(
        "concept_norm0001", NORMALISE, corpus_sites=8)})
    before = CompoundingConceptLibrary(path).concepts()[0].verified_hits
    CompoundingConceptLibrary(path).record_concept_outcome("concept_norm0001", helped=True)
    after = CompoundingConceptLibrary(path).concepts()[0].verified_hits
    assert after == before + 1


def test_disconfirmation_lowers_the_prior(tmp_path):
    path = _library(tmp_path, {"concept_norm0001": _concept(
        "concept_norm0001", NORMALISE, corpus_sites=8)})
    priors = [CompoundingConceptLibrary(path).concepts()[0].log_prior]
    work = CompoundingConceptLibrary(path)
    for _ in range(2):
        work.record_concept_outcome("concept_norm0001", helped=False)
        priors.append(CompoundingConceptLibrary(path).concepts()[0].log_prior)
    assert priors[1] < priors[0]
    assert priors[2] < priors[1]


def test_history_changes_the_answer_to_the_same_question(tmp_path):
    """The creature analogy, made measurable: identical code, identical question, different answer.

    This is the whole point of a lifecycle. The synthesizer is not recompiled between these calls;
    only the creature's record of how its own concept behaved changes.
    """
    path = _library(tmp_path, {"concept_norm0001": _concept(
        "concept_norm0001", NORMALISE, corpus_sites=8)})
    verdict_before, body_before = _ask(path)
    assert verdict_before == "SOLVED"
    assert "concept_norm0001" in (body_before or "")

    work = CompoundingConceptLibrary(path)
    for _ in range(3):
        work.record_concept_outcome("concept_norm0001", helped=False)

    verdict_after, body_after = _ask(path)
    assert verdict_after != "SOLVED"
    assert "concept_norm0001" not in (body_after or "")


def test_retirement_preserves_already_built_bodies(tmp_path):
    """Retirement removes an option from future search; it must not rewrite the past."""
    path = _library(tmp_path, {"concept_norm0001": _concept(
        "concept_norm0001", NORMALISE, corpus_sites=8)})
    work = CompoundingConceptLibrary(path)
    for _ in range(3):
        work.record_concept_outcome("concept_norm0001", helped=False)
    reloaded = CompoundingConceptLibrary(path)
    assert "concept_norm0001" in reloaded.retired_concept_ids()
    assert "concept_norm0001" not in {c.concept_id for c in reloaded.concepts()}
    assert "concept_norm0001" in reloaded.callable_map()


def test_junk_cannot_permanently_crowd_out_a_useful_concept(tmp_path):
    """The measured failure that motivated all of this: 16 visible slots, 16 junk, reach 0/2."""
    concepts = {"concept_norm0001": _concept("concept_norm0001", NORMALISE, corpus_sites=2)}
    for j in range(20):
        concepts[f"concept_junk{j:04d}"] = _concept(
            f"concept_junk{j:04d}",
            f"(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1 + {float(j) + 1.0}) "
            f"if _v2 > _v1 else 0.0", corpus_sites=40 + j)
    path = _library(tmp_path, concepts)

    crowded = CompoundingConceptLibrary(path).concepts()[:16]
    assert sum(1 for c in crowded if "junk" in c.concept_id) == 16, "precondition: junk floods"
    assert _ask(path)[0] != "SOLVED", "precondition: reach is lost"

    work = CompoundingConceptLibrary(path)
    for j in range(20):
        for _ in range(3):
            work.record_concept_outcome(f"concept_junk{j:04d}", helped=False)

    window = CompoundingConceptLibrary(path).concepts()[:16]
    assert sum(1 for c in window if "junk" in c.concept_id) == 0
    assert "concept_norm0001" in {c.concept_id for c in window}
    assert _ask(path)[0] == "SOLVED"


def test_no_recovery_without_evidence(tmp_path):
    """The control separating learning from forgetting.

    Same crowded library, no verdicts supplied. If reach recovered on a use count or a timer, the
    mechanism would be decay. It must not recover.
    """
    concepts = {"concept_norm0001": _concept("concept_norm0001", NORMALISE, corpus_sites=2)}
    for j in range(20):
        concepts[f"concept_junk{j:04d}"] = _concept(
            f"concept_junk{j:04d}",
            f"(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1 + {float(j) + 1.0}) "
            f"if _v2 > _v1 else 0.0", corpus_sites=40 + j)
    path = _library(tmp_path, concepts)
    for _ in range(3):
        _ask(path)
    assert _ask(path)[0] != "SOLVED"
    assert len(CompoundingConceptLibrary(path).retired_concept_ids()) == 0
