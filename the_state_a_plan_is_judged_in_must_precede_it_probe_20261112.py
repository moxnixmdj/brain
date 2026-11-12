#!/usr/bin/env python3
"""The state a plan is judged in must exist before the plan runs.

`applicability_v1` and the `context` argument on `macro_v1` shipped, and then sat unused: every
live caller still called `record(clauses, steps)` and `note_failure(key)` with no context at all.
Measured on the chain battery before this change: 3 macros stored, **0 evidence rows**. A learner
nothing feeds is not a capability.

This probe wires the primary executor and measures the wiring. It also measures the trap that
 wiring walks straight into, because the obvious source of "the state" is wrong:

`chain_v1` starts `established` EMPTY and fills it from each verified step's `provides`. At the end
of a successful chain it holds exactly the effects the plan created; at the end of a failed chain
it holds a shorter prefix of them. Feed that to the learner and it identifies a requirement made
of THE PLAN'S OWN OUTPUTS -- true of every success and false of every failure by construction. It
looks like a perfectly identified boundary. It then withholds the plan in every fresh state,
because a fresh state has none of those effects yet, and reuse is silently destroyed.

That is `false lesson propagation` (arXiv 2605.20023): a spurious causal lesson drawn from a few
trajectories and applied where it does not hold. Arm 2 below executes it rather than asserting it.

Authority NONE. Real chains run against a redirected macro store; the repository's own macro
state is restored. Zero model dependency, $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import chain_v1 as C  # noqa: E402
from canonical.runtime import macro_v1 as MC  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THE_STATE_MUST_PRECEDE_THE_PLAN_V1"

#: A real two-clause job from the repository's own chain battery.
GOAL = (
    "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx "
    "and create a tar.gz archive from the manifest"
)


def measure_live_wiring() -> dict[str, Any]:
    """The executor now records the state it started in, on the real path."""
    result = C.run(GOAL, memory=True)
    key = MC.signature(C.decompose(GOAL))
    entry = (MC._load().get("macros") or {}).get(key) or {}
    evidence = entry.get("evidence") or []
    produced = set(result.get("established_effects") or [])
    recorded_facts = {f for row in evidence for f in (row.get("facts") or [])}
    return {
        "arm": "LIVE_WIRING",
        "chain_ok": bool(result.get("ok")),
        "clauses": result.get("clause_count"),
        "macro_recorded": bool(result.get("macro_recorded")),
        "preconditions_reported": result.get("preconditions_observed") is not None,
        "evidence_rows": len(evidence),
        "recorded_facts": sorted(recorded_facts),
        "effects_the_plan_produced": sorted(produced),
        "recorded_facts_that_are_the_plans_own_outputs": sorted(recorded_facts & produced),
    }


def measure_the_killed_idea() -> dict[str, Any]:
    """Execute the naive post-state wiring and show the boundary it fabricates.

    Nothing here is configured into the runtime. It is the counterfactual, run so the reason for
    the pre-state snapshot is a measurement rather than an opinion.
    """
    success = C.run(GOAL, memory=False)
    produced = list(success.get("established_effects") or [])
    if not produced:
        return {"arm": "THE_KILLED_IDEA", "ran": False, "reason": "NO_EFFECTS_OBSERVED"}
    # A successful run establishes every effect; a run that fails at the last step establishes
    # only the prefix. That difference is an artifact of how far the plan got, not of the world.
    post_success = frozenset(produced)
    post_failure = frozenset(produced[:-1])
    fabricated = APP.learn([(post_success, True), (post_failure, False)])
    fresh_state: frozenset[str] = frozenset()
    return {
        "arm": "THE_KILLED_IDEA",
        "ran": True,
        "status": fabricated.status,
        "required": None if fabricated.required is None else list(fabricated.required),
        "survivors": fabricated.survivor_count,
        "most_general": list(fabricated.most_general),
        # The danger does not require exact identification: withholding uses the LEAST demanding
        # survivor, so a unanimous-but-ambiguous boundary is enough to refuse every cold start.
        "requirement_is_made_of_the_plans_own_outputs": (
            bool(fabricated.most_general)
            and set(fabricated.most_general) <= set(produced)
        ),
        "would_withhold_the_plan_in_a_fresh_state": APP.explains_failure(fabricated, fresh_state),
        "note": (
            "A fresh state cannot contain the effects the plan has not produced yet, so this "
            "boundary refuses every cold start. Reuse would be destroyed by a 'perfect' boundary."
        ),
    }


def measure_the_offer_is_actually_gated() -> dict[str, Any]:
    """The recorded evidence is used, not just stored: an out-of-scope plan is withdrawn."""
    C.run(GOAL, memory=True)  # ensure a macro exists to withhold
    original = MC.applicable
    try:
        MC.applicable = lambda key, context: False
        refused = C.run(GOAL, memory=True)
    finally:
        MC.applicable = original
    allowed = C.run(GOAL, memory=True)
    return {
        "arm": "THE_OFFER_IS_GATED",
        "withheld_when_out_of_scope": bool(refused.get("macro_withheld_out_of_scope")),
        "used_macro_when_withheld": bool(refused.get("used_macro")),
        "chain_still_completed_while_withheld": bool(refused.get("ok")),
        "withheld_when_in_scope": bool(allowed.get("macro_withheld_out_of_scope")),
    }


def measure_fail_open() -> dict[str, Any]:
    """A perceiver that cannot decide must not break the snapshot or invent facts.

    Only what this change owns is tested. The executor has its own dependence on the sensor, so
    a sensor that RAISES breaks planning with or without this wiring; that is not a property of
    this change and is not claimed. The mode that matters here is the real one: a premise the
    perceiver reports as UNDECIDABLE must be absent from the snapshot, never guessed true.
    """
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import world_probe_v1 as WP

    original_loader = GA.load_registry
    try:
        def _boom():
            raise RuntimeError("REGISTRY_UNAVAILABLE")
        GA.load_registry = _boom
        ctx = C.precondition_context(["a", "b"], ROOT, "a and b")
    finally:
        GA.load_registry = original_loader

    original_probe = WP.probe_effect
    try:
        def _undecidable(*a, **k):
            return {"true": False, "how": "UNDECIDABLE__NOT_ESTABLISHED", "evidence": None}
        WP.probe_effect = _undecidable
        blind_ctx = C.precondition_context(C.decompose(GOAL), ROOT, GOAL)
    finally:
        WP.probe_effect = original_probe
    return {
        "arm": "FAIL_OPEN",
        "context_is_none_when_the_registry_cannot_load": ctx is None,
        "undecidable_premises_are_absent_not_guessed": blind_ctx == frozenset(),
        "snapshot_survives_an_undecidable_world": blind_ctx is not None,
    }


ARMS = (
    measure_live_wiring,
    measure_the_killed_idea,
    measure_the_offer_is_actually_gated,
    measure_fail_open,
)


def run() -> dict[str, Any]:
    records = []
    original_state = MC.STATE
    original_bytes = original_state.read_bytes() if original_state.is_file() else None
    try:
        with tempfile.TemporaryDirectory(prefix="prestate_") as tmp:
            MC.STATE = pathlib.Path(tmp) / "chain_macros_v1.json"
            for arm in ARMS:
                records.append(arm())
    finally:
        MC.STATE = original_state
        if original_bytes is not None:
            original_state.write_bytes(original_bytes)
    live, killed, gated, fail_open = records
    return {
        "schema": SCHEMA,
        "probe": "the_state_a_plan_is_judged_in_must_precede_it",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "records": records,
        "summary": {
            "live_evidence_rows": live["evidence_rows"],
            "learner_is_fed_on_the_live_path": live["evidence_rows"] > 0,
            "recorded_state_excludes_the_plans_own_outputs": (
                live["recorded_facts_that_are_the_plans_own_outputs"] == []
            ),
            "naive_post_state_fabricates_a_circular_requirement": bool(
                killed.get("requirement_is_made_of_the_plans_own_outputs")
            ),
            "naive_post_state_would_destroy_cold_start_reuse": bool(
                killed.get("would_withhold_the_plan_in_a_fresh_state")
            ),
            "offer_is_withheld_when_out_of_scope": gated["withheld_when_out_of_scope"],
            "offer_is_kept_when_in_scope": gated["withheld_when_in_scope"] is False,
            "undecidable_premises_are_never_guessed_true": fail_open["undecidable_premises_are_absent_not_guessed"],
            "snapshot_fails_open_when_the_registry_is_unavailable": fail_open["context_is_none_when_the_registry_cannot_load"],
        },
        "hard_nonclaims": [
            "ONE_REAL_GOAL__NOT_A_BENCHMARK_OF_ARBITRARY_ENVIRONMENTS",
            "SUCCESS_EVIDENCE_ALONE_IDENTIFIES_NOTHING__A_CONTRASTING_FAILURE_IS_STILL_REQUIRED",
            "BLIND_PREMISES_ARE_NOT_MADE_DECIDABLE_BY_THIS",
            "NO_CAPABILITY_REGISTERED",
            "NO_TRUTH_ACHIEVED",
        ],
    }


def render(report: dict[str, Any]) -> str:
    s = report["summary"]
    return "\n".join([
        "The state a plan is judged in must precede the plan",
        "=" * 72,
        f"  evidence rows on the live path                   {s['live_evidence_rows']}",
        f"  the learner is actually fed                      {s['learner_is_fed_on_the_live_path']}",
        f"  recorded state excludes the plan's own outputs   {s['recorded_state_excludes_the_plans_own_outputs']}",
        "",
        "The idea that was killed before shipping",
        "-" * 72,
        f"  post-state wiring fabricates a circular rule     {s['naive_post_state_fabricates_a_circular_requirement']}",
        f"  ...and would destroy cold-start reuse            {s['naive_post_state_would_destroy_cold_start_reuse']}",
        "",
        "The evidence is used, not just stored",
        "-" * 72,
        f"  offer withheld when out of scope                 {s['offer_is_withheld_when_out_of_scope']}",
        f"  offer kept when in scope                         {s['offer_is_kept_when_in_scope']}",
        f"  undecidable premises are never guessed true      {s['undecidable_premises_are_never_guessed_true']}",
        f"  snapshot fails open without a registry           {s['snapshot_fails_open_when_the_registry_is_unavailable']}",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
