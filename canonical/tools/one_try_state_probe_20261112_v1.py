#!/usr/bin/env python3
"""One-try state probe, 2026-11-12. Measurements only. Authority: NONE.

The owner's question is whether one demonstration of an advanced action makes the
machine learn it permanently, and whether experience compounds into solving new
kinds of computer work. This tool does not answer that by reading the project's
notes. It drives three live mechanisms on the current tree and reports what they
do:

  1. the SKILL -> concept-library bridge (`_skill_organ_to_concept_entry`),
  2. the wake-sleep compressor (`CompoundingConceptLibrary.sleep_abstract`),
  3. the newest taught action (`edit_by_example_v1`), which is the tree's
     closest current answer to "show it once".

Every store is a fresh TemporaryDirectory. Nothing is written to the repository,
no network is used, no model is called, no capability is registered, and no
governance file is read or changed. `truth.achieved` stays false.

Run from anywhere:
    python3 canonical/tools/one_try_state_probe_20261112_v1.py
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    CompoundingConceptLibrary,
    executable_ast_bytes,
)
from canonical.swe_kernel.meta_circular_organ_graph_v1 import (  # noqa: E402
    SKILL,
    ExecutableOrgan,
    MetaCircularOrganGraph,
    _skill_organ_to_concept_entry,
)
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe  # noqa: E402


SINGLE_RETURN = "def run(x0):\n    return x0 * 2 + 1\n"


def _period(block: str, expr: str = "x0 - (x0 // _n) * _n") -> str:
    """The three-statement shape the period/periodic synthesizer actually emits."""
    return (
        "def run(x0):\n"
        "    _block = %s\n"
        "    _n = len(_block)\n"
        "    return _block[%s]\n" % (block, expr)
    )


def _organ(organ_id: str, source: str) -> ExecutableOrgan:
    return ExecutableOrgan(
        organ_id=organ_id,
        stratum=SKILL,
        name=organ_id,
        task_signature="sig_" + organ_id,
        entrypoint="run",
        source_code=source,
        code_bytes=len(source.encode("utf-8")),
        verified_passes=10,
    )


def _file_digest(rel: str) -> str:
    p = pathlib.Path(__file__).resolve().parents[2] / rel
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def measure_bridge() -> dict[str, Any]:
    """Does a solved program reach the concept library G_t?"""
    multi = _period("(-2.0, 5.0, 1.0)")
    one = SINGLE_RETURN
    bridge_multi = _skill_organ_to_concept_entry(_organ("organ_skill_multi", multi)) is not None
    bridge_single = _skill_organ_to_concept_entry(_organ("organ_skill_single", one)) is not None
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        lib = CompoundingConceptLibrary(state_path=root / "concepts.json")
        graph = MetaCircularOrganGraph(
            state_path=root / "organs.json", concept_library=lib
        )
        before = len(lib.concepts())
        graph.register_organ(_organ("organ_skill_multi", multi))
        after_multi = len(lib.concepts())
        graph.register_organ(_organ("organ_skill_single", one))
        after_single = len(lib.concepts())
    return {
        "bridge_admits_single_return_body": bridge_single,
        "bridge_admits_multi_statement_body": bridge_multi,
        "concepts_before": before,
        "concepts_after_registering_multi_statement_skill": after_multi,
        "concepts_after_also_registering_single_return_skill": after_single,
    }


def _affine_corpus() -> list[str]:
    out = []
    for var, const in [("a", 3), ("b", 4), ("c", 5), ("d", 6)]:
        out.append(
            "def run(%s):\n"
            "    t = ((%s * 2) + (%s * 2)) + 7\n"
            "    u = t * t + 1\n"
            "    return u - %d\n" % (var, var, var, const)
        )
    return out


def _period_corpus(n: int) -> list[str]:
    blocks = [
        "(-2.0, 5.0, 1.0)",
        "(-1.0, -5.0, 2.0, -2.0, 5.0)",
        "(1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0)",
        "(2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0)",
        "(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)",
    ]
    return [_period(b) for b in blocks[:n]]


def measure_sleep() -> dict[str, Any]:
    """Does the compressor fire on a favourable corpus and on the real corpus?"""
    result: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        for label, corpus in [
            ("affine_4_programs", _affine_corpus()),
            ("period_3_programs", _period_corpus(3)),
            ("period_5_programs", _period_corpus(5)),
        ]:
            lib = CompoundingConceptLibrary(state_path=root / (label + ".json"))
            out = lib.sleep_abstract(corpus)
            result[label] = {
                "admitted_count": out.get("admitted_count"),
                "admitted_body_exprs": [
                    a.get("body_expr") for a in out.get("admitted", [])
                ],
            }
    return result


def measure_mdl_why() -> dict[str, Any]:
    """Why the real corpus is refused: B_exec of a helper definition is not a saving.

    Uses the library's own `executable_ast_bytes` measure and a hand-written
    rewrite of the one shared expression, matching the sleep-phase's accounting.
    This is an approximation of the admission gate, not a re-run of it.
    """
    corpus = _period_corpus(4)
    shared = "x0 - (x0 // _n) * _n"
    helper = "def concept_probe(_v0, _v1):\n    return _v0 - _v0 // _v1 * _v1\n\n"
    rewritten = [p.replace(shared, "concept_probe(x0, _n)") for p in corpus]
    baseline = executable_ast_bytes("\n\n".join(corpus))
    after = executable_ast_bytes(helper + "\n\n".join(rewritten))
    return {
        "measure": "executable_ast_bytes (zlib of canonical AST text)",
        "baseline_B_exec": baseline,
        "after_helper_B_exec": after,
        "delta_B_exec_baseline_minus_after": baseline - after,
        "admission_requires": "delta_B_exec > 0",
        "note": (
            "The four programs differ only in a literal table, which zlib already "
            "compresses almost for free. A helper definition is therefore a byte "
            "COST on this corpus, so the compressive gate correctly refuses it. "
            "Fixing only the bridge predicate cannot make this corpus compound."
        ),
    }


def measure_taught_action() -> dict[str, Any]:
    """One example teaches a shape; it does not teach when the shape applies."""
    before = "def inside(a, hi):\n    return a <= hi\n"
    after = "def inside(a, hi):\n    return a < hi\n"
    # Same shape as the example. Here `<=` is the *correct* boundary: the last
    # index is included. Repeating the demonstrated edit makes this function wrong.
    same_shape_wrong_meaning = "def is_last_index(a, hi):\n    return a <= hi\n"
    different_shape = "def is_last_index(i, n):\n    return i <= n - 1\n"
    try:
        edited = ebe.edit_by_example(same_shape_wrong_meaning, before, after)
        applied: str | bool = edited
        changed = edited != same_shape_wrong_meaning
    except ebe.Refused as exc:
        applied, changed = "REFUSED: " + str(exc)[:160], False
    try:
        ebe.edit_by_example(different_shape, before, after)
        other_shape = "APPLIED"
    except ebe.Refused:
        other_shape = "REFUSED (scope boundary holds)"
    return {
        "example": "return a <= hi  ->  return a < hi (one changed place)",
        "target_same_shape_but_different_meaning": "def is_last_index(a, hi): return a <= hi",
        "result_on_target": applied,
        "target_was_changed": changed,
        "semantic_oracle_consulted": False,
        "result_on_different_shaped_target": other_shape,
        "note": (
            "The module's own docstring says it repeats a change and does not check "
            "that the change is right for the code it is repeated on. Two distinct "
            "hypotheses fit one example ('make this boundary strict here' and 'make "
            "every <= strict'); the tree picks one by its own inductive bias, not by "
            "evidence. Negative examples and an applicability predicate are the "
            "missing information, not more demonstrations of the same success."
        ),
    }


def main() -> int:
    report = {
        "schema": "PROJECT_BRAIN_ONE_TRY_STATE_PROBE_V1",
        "date": "2026-11-12",
        "authority": "NONE",
        "truth_achieved": False,
        "claim": "MEASUREMENTS_ONLY__NO_CAPABILITY_OR_TERMINAL_CREDIT",
        "modules_measured": {
            "canonical/swe_kernel/meta_circular_organ_graph_v1.py": _file_digest(
                "canonical/swe_kernel/meta_circular_organ_graph_v1.py"
            ),
            "canonical/swe_kernel/concept_library_v1.py": _file_digest(
                "canonical/swe_kernel/concept_library_v1.py"
            ),
            "canonical/swe_kernel/taught_actions/edit_by_example_v1.py": _file_digest(
                "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
            ),
        },
        "bridge": measure_bridge(),
        "sleep_abstract": measure_sleep(),
        "mdl_gate_on_real_corpus": measure_mdl_why(),
        "taught_action": measure_taught_action(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
