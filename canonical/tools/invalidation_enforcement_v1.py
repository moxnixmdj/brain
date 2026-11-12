#!/usr/bin/env python3
"""An INVALIDATED rule must not be applicable, and nothing may make it one again.

THE DEFECT
----------
The store already learns from counterexamples: `refine_scope_from_counterexample` runs, decides
`INVALIDATED`, writes `state='INVALIDATED'` and a counterexample, and bumps the generation.
Measured 2026-11-12 on a rule induced from one correct edit (`x <= 100` -> `x < 100`):

    store says:               INVALIDATED
    store view via lookup_rules: ['INVALIDATED']
    recall_and_apply_verified (strict or permissive verifier):  refused

So the *recall* path enforces invalidation (line 1241: `rule.get('state') not in (None, 'ACTIVE')`).
But the *apply* primitive does not:

    apply_crystallized_code_rule("def tier(a):\\n    return a <= 50\\n", rule)
        -> "def tier(a):\\n    return a < 50\\n"        # still edits, still wrong

and one production consumer pairs the state-blind public read with that primitive:

    software_repair_crossfile_choreograph_v1.py:1126
        for rule in VerifiedSkillStore().lookup_rules("python", "python_test_repair"):
            c_out = apply_crystallized_code_rule(src, rule)
            candidates.insert(0, c_out)          # <-- highest priority

A refuted edit was being offered as the first candidate for repair. The sibling consumer
(`cow_impact_repair_engine_v1.py:1152`) guards by hand; this one did not. Enforcement that
lives in eleven call sites is not enforcement.

WHY THIS CHECKS STORAGE RATHER THAN PATCHING THE READS
------------------------------------------------------
The tempting fix is to filter invalidated rules out of `lookup_rules()`. Rejected, and the
reason is measured: `auditability_report_v1` enumerates exactly that call to compute its
denominator. Filtering the default would have *raised* the reported auditability by hiding the
rules it could not verify. An observability tool that improves when you delete the evidence is
the failure this session keeps finding, so the read keeps returning everything and the write
side refuses instead.

WHAT IT DOES
------------
`apply_crystallized_code_rule` gains one guard: not applicable unless
`state in (None, "ACTIVE")`, returning None -- the same contract as "the rule did not fire", so
every caller already handles it. `_load_rules` additionally *forbids* the transition
INVALIDATED -> ACTIVE inside the store, so a stale bundle import or a hand-edited row cannot
quietly revive a refuted rule.

Authority: NONE. This does not make a stored rule correct; it stops a refuted one from acting.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
from typing import Any, Mapping

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

SCHEMA = "PROJECT_BRAIN_INVALIDATION_ENFORCEMENT_V1"

#: The only states in which a rule may edit code. ``None`` preserves the legacy contract for
#: rules written before the state field existed; it does not re-open a refuted rule, because a
#: refuted rule always carries the string.
APPLICABLE_STATES = (None, "ACTIVE")

REFUTED = "INVALIDATED"


def rule_is_applicable(rule: Mapping[str, Any]) -> bool:
    """The one predicate every application path should agree on."""
    return rule.get("state") in APPLICABLE_STATES


def measure() -> dict[str, Any]:
    """Reproduce the three paths on a real store and report which of them enforce the state.

    The store is created in a temporary directory: this must never touch the live skill db,
    because the probe deliberately creates a rule and then refutes it.
    """
    from canonical.swe_kernel.boundary_disjunction_normalization_v1 import (
        propose_semantic_swaps,
    )
    from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
        propose_egraph_algebraic_rewrites,
    )
    from canonical.swe_kernel.language_neutral_skill_bridge_v1 import (
        cross_language_candidates,
        recall_across_languages,
    )
    from canonical.swe_kernel.operator_generalization_v1 import propose_operator_swaps
    from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
        iter_cst_skeleton_candidates,
        recall_across_languages_cst,
    )
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        VerifiedSkillStore,
        _load_rules,
        anti_unify_code_rule,
        apply_crystallized_code_rule,
        iter_crystallized_code_rule_candidates,
        narrow_rule_at_apply_time,
    )

    db = pathlib.Path(tempfile.mkdtemp()) / "probe.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)

    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"
    taught = store.crystallize_code_fix(
        before_snippet=before, after_snippet=after, language="python", error_class="boundary"
    )
    skill_id = taught["skill_id"]

    # The victim the learner will get wrong: here the spec keeps 50 INCLUSIVE.
    victim = "def tier(a):\n    return a <= 50\n"
    spec = lambda candidate: "a < 50" not in candidate      # noqa: E731 - the oracle under test

    refutation = store.refine_scope_from_counterexample(
        skill_id, {"source_text": victim, "label": "inclusive_50"}, spec
    )

    stored = _load_rules(db, "python")
    stored_rule = stored[0] if stored else {}
    primitive = apply_crystallized_code_rule(victim, stored_rule) if stored_rule else None
    iter_candidates = list(iter_crystallized_code_rule_candidates(victim, stored_rule)) if stored_rule else []
    narrowed = narrow_rule_at_apply_time(stored_rule) if stored_rule else None
    op_swaps = list(propose_operator_swaps(victim, stored_rule)) if stored_rule else []
    sem_swaps = list(
        propose_semantic_swaps(
            "def tier(a):\n    return a < 50 or a == 50\n",
            stored_rule,
            operator_swaps=propose_operator_swaps,
        )
    ) if stored_rule else []
    cst_candidates = list(
        iter_cst_skeleton_candidates(
            "fn tier(a: i32) -> bool { a <= 50 }\n",
            stored_rule,
            target_language="rust",
        )
    ) if stored_rule else []

    alg_rule = anti_unify_code_rule(
        "def f(a, b):\n    return a * b + a * 1\n",
        "def f(a, b):\n    return a * (b + 1)\n",
    )
    alg_rule["state"] = REFUTED
    egraph_rewrites = propose_egraph_algebraic_rewrites("def g(x, y):\n    return x * y + x\n", alg_rule)

    lexical_cross = cross_language_candidates(
        store, source_language="python", target_language="javascript"
    )
    lexical_recall = recall_across_languages(
        store,
        source_text="function tier(a) { return a <= 50; }\n",
        target_language="javascript",
        verifier=lambda c: True,
    )
    cst_recall = recall_across_languages_cst(
        store,
        source_text="fn tier(a: i32) -> bool { a <= 50 }\n",
        target_language="rust",
        verifier=lambda c: True,
    )
    cross_lang_snippets = {
        "rust": "fn tier(a: i32) -> bool {\n    a <= 50\n}\n",
        "go": "package p\nfunc tier(a int) bool {\n    return a <= 50\n}\n",
        "typescript": "export function tier(a: number): boolean {\n    return a <= 50;\n}\n",
        "javascript": "function tier(a) {\n    return a <= 50;\n}\n",
        "java": "class C {\n    static boolean tier(int a) {\n        return a <= 50;\n    }\n}\n",
        "cpp": "bool tier(int a) {\n    return a <= 50;\n}\n",
    }
    cross_lang_recall_fires = {
        lang: store.recall_and_apply_verified(
            source_text=src, language=lang, verifier=lambda c: True
        ) is not None
        for lang, src in cross_lang_snippets.items()
    }

    strict_recall = store.recall_and_apply_verified(source_text=victim, language="python", verifier=spec)
    permissive_recall = store.recall_and_apply_verified(
        source_text=victim, language="python", verifier=lambda c: True
    )
    public_view = store.lookup_rules("python")

    any_bypass = bool(
        primitive is not None
        or iter_candidates
        or narrowed is not None
        or op_swaps
        or sem_swaps
        or cst_candidates
        or egraph_rewrites
        or lexical_cross
        or lexical_recall is not None
        or cst_recall is not None
        or any(cross_lang_recall_fires.values())
    )

    return {
        "schema": SCHEMA, "authority": "NONE",
        "refutation_action": refutation.get("action"),
        "stored_states": [r.get("state") for r in stored],
        "public_view_states": [r.get("state") for r in public_view],
        "public_view_includes_refuted": any(
            r.get("state") == REFUTED for r in public_view
        ),
        "primitive_applies_refuted_rule": primitive is not None,
        "primitive_output": primitive,
        "iter_candidates_fires": bool(iter_candidates),
        "narrow_at_apply_time_fires": narrowed is not None,
        "operator_swaps_fires": bool(op_swaps),
        "semantic_swaps_fires": bool(sem_swaps),
        "cst_skeleton_candidates_fires": bool(cst_candidates),
        "egraph_algebraic_rewrites_fires": bool(egraph_rewrites),
        "lexical_cross_language_fires": bool(lexical_cross) or (lexical_recall is not None),
        "cst_cross_language_fires": cst_recall is not None,
        "cross_language_recall_fires_by_lang": cross_lang_recall_fires,
        "any_path_applies_refuted_rule": any_bypass,
        "recall_strict_refused": strict_recall is None,
        "recall_permissive_refused": permissive_recall is None,
    }


def main(argv: list[str] | None = None) -> int:
    import json

    report = measure()
    if argv and "--json" in argv:
        print(json.dumps(report, indent=2))
    else:
        print("invalidation enforcement: does a refuted rule still edit code?\n")
        print(f"  refutation action           {report['refutation_action']}")
        print(f"  stored states               {report['stored_states']}")
        print(f"  public view                 {report['public_view_states']}")
        print(f"  primitive applies it        {report['primitive_applies_refuted_rule']}"
              f"   -> {report['primitive_output']!r}")
        print(f"  recall refuses (strict)     {report['recall_strict_refused']}")
        print(f"  recall refuses (permissive) {report['recall_permissive_refused']}")
        print(f"  any path applies refuted    {report['any_path_applies_refuted_rule']}")
    # Exit 1 while any generator or cross-language path can still act on a refuted rule.
    return 1 if report["any_path_applies_refuted_rule"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
