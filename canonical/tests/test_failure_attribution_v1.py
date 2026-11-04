"""Attributing a failure to the concept that caused it -- and to nothing else.

The load-bearing test here is `test_inlining_is_vacuous`. The first version of the mechanism used a
substitution counterfactual and measured nothing, because inlining a definition cannot change a
program's behaviour. That test exists so the mistake cannot come back disguised as a fix.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.concept_failure_attribution_v1 import (  # noqa: E402
    attribute_failure,
    concepts_used_by,
    substitute_concept,
    viable_scenarios,
)
from canonical.runtime.generalization_check_v1 import _compile_body, classify  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    SCHEMA,
    CompoundingConceptLibrary,
)

GOOD = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0"
BAD = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1 + 1.0) if _v2 > _v1 else 0.0"

TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]


def _normalise(v, l, h):
    return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0


def _concept(cid, body, corpus_sites=8):
    return {"concept_id": cid, "arity": 3, "param_names": ["_v0", "_v1", "_v2"],
            "body_expr": body, "domain_kind": "numeric", "mdl_gain_bytes": 50,
            "corpus_sites": corpus_sites, "uses": 0, "verified_hits": 0,
            "disconfirmations": 0}


def _library(tmp_path: Path, concepts: dict) -> Path:
    path = tmp_path / "library.json"
    path.write_text(json.dumps({"schema": SCHEMA, "concepts": concepts}))
    return path


def _train():
    return [(p, _normalise(*p) + 0.5) for p in TRAIN]


def _held():
    return [(p, _normalise(*p) + 0.5) for p in HELD]


def test_finds_the_concepts_a_body_uses():
    body = "return (concept_a0000001(v, l, h) + concept_b0000002(v, l, h))"
    assert concepts_used_by(body) == ["concept_a0000001", "concept_b0000002"]
    assert concepts_used_by("return v + l") == []


def test_inlining_is_vacuous(tmp_path):
    """Why substitution cannot be the counterfactual.

    Inlining a concept's definition preserves semantics exactly, so "does it still fail without
    concept X" has the same answer as "does it fail". Any mechanism built on substitution therefore
    has no information, and the first version of this module reported a GUILTY concept innocent.
    """
    path = _library(tmp_path, {"concept_bad0001": _concept("concept_bad0001", BAD, 40)})
    library = CompoundingConceptLibrary(path)
    # Self-contained, the way the synthesizer actually returns a body: helper def, then the return.
    body = ("def concept_bad0001(_v0, _v1, _v2):\n    return " + BAD + "\n"
            "return (concept_bad0001(v, l, h) * 2)")
    inlined = substitute_concept(body, library, "concept_bad0001")
    assert inlined is not None
    assert "concept_bad0001(" not in inlined.splitlines()[-1], "the call was not inlined"

    original = _compile_body(body, ["v", "l", "h"])
    inlined_fn = _compile_body(inlined, ["v", "l", "h"])
    for point in TRAIN:
        assert abs(original(*point) - inlined_fn(*point)) < 1e-12, (
            "inlining changed behaviour, which would mean the vacuity control is wrong")


def test_guilty_concept_is_charged_and_innocent_is_spared(tmp_path):
    """The point of attribution: one failed program, two concepts, one culprit."""
    path = _library(tmp_path, {
        "concept_good0001": _concept("concept_good0001", GOOD, 8),
        "concept_bad0001": _concept("concept_bad0001", BAD, 40),
    })
    body = synthesize_python_function_body(
        ["v", "l", "h"], _train(), extra_constants=(0.5,), max_weight=4,
        concept_library=CompoundingConceptLibrary(path))
    assert body, "the search must emit something for there to be a failure to attribute"

    report = attribute_failure(
        CompoundingConceptLibrary(path), body, synthesize_python_function_body,
        ["v", "l", "h"], _train(), extra_constants=(0.5,), max_weight=4)

    assert "concept_bad0001" in report["suspects"]
    assert "concept_good0001" not in report["suspects"]
    retired = CompoundingConceptLibrary(path).retired_concept_ids()
    assert "concept_bad0001" in retired
    assert "concept_good0001" not in retired


def test_charging_repairs_the_next_answer(tmp_path):
    path = _library(tmp_path, {
        "concept_good0001": _concept("concept_good0001", GOOD, 8),
        "concept_bad0001": _concept("concept_bad0001", BAD, 40),
    })
    first = synthesize_python_function_body(
        ["v", "l", "h"], _train(), extra_constants=(0.5,), max_weight=4,
        concept_library=CompoundingConceptLibrary(path))
    verdict_first, _ = classify(first, ["v", "l", "h"], _held())
    assert verdict_first != "SOLVED"

    attribute_failure(CompoundingConceptLibrary(path), first or "",
                      synthesize_python_function_body, ["v", "l", "h"], _train(),
                      extra_constants=(0.5,), max_weight=4)

    second = synthesize_python_function_body(
        ["v", "l", "h"], _train(), extra_constants=(0.5,), max_weight=4,
        concept_library=CompoundingConceptLibrary(path))
    verdict_second, _ = classify(second, ["v", "l", "h"], _held())
    assert verdict_second == "SOLVED"
    assert "concept_bad0001" not in (second or "")


def test_no_culprit_is_manufactured_for_an_unsolvable_problem(tmp_path):
    """A concept must not be punished for a problem nobody could solve."""
    path = _library(tmp_path, {"concept_good0001": _concept("concept_good0001", GOOD, 8)})
    adversarial = [((5, 2, 4), 1000.0), ((7, 0, 10), -42.0), ((-3, 0, 10), 3.75)]
    body = synthesize_python_function_body(
        ["v", "l", "h"], adversarial, extra_constants=(0.5, 1.0, 100.0), max_weight=4,
        concept_library=CompoundingConceptLibrary(path))
    if body:
        report = attribute_failure(
            CompoundingConceptLibrary(path), body, synthesize_python_function_body,
            ["v", "l", "h"], adversarial, extra_constants=(0.5, 1.0, 100.0), max_weight=4)
        assert report["suspects"] == []
    assert len(CompoundingConceptLibrary(path).retired_concept_ids()) == 0


def test_revision_is_reversible(tmp_path):
    path = _library(tmp_path, {"concept_bad0001": _concept("concept_bad0001", BAD, 40)})
    library = CompoundingConceptLibrary(path)
    for _ in range(3):
        library.record_concept_outcome("concept_bad0001", helped=False)
    assert "concept_bad0001" in CompoundingConceptLibrary(path).retired_concept_ids()

    assert CompoundingConceptLibrary(path).revive("concept_bad0001") is True
    reloaded = CompoundingConceptLibrary(path)
    assert "concept_bad0001" not in reloaded.retired_concept_ids()
    assert reloaded._concepts["concept_bad0001"].disconfirmations == 0
    assert reloaded.revive("concept_bad0001") is False, "reviving a live concept must be a no-op"


def test_scope_states_both_capabilities_and_gaps():
    """The module must not imply it detects failures."""
    text = viable_scenarios()
    assert "CAN:" in text and "CANNOT:" in text
    assert "notice" in text.lower()
