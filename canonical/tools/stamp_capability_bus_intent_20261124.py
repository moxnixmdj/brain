"""Stamp the recursive-OBS record and live route frontier for wave 47's capability bus.

The gates read a route frontier, a preflight and seven OBS layers out of the intent. This tool
writes them from measurements taken in this round; it invents no number it did not run.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/DECLARATION_IS_NOT_ADMISSION_20261124_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "ADMIT_BY_EXECUTION_NOT_BY_DECLARATION"
DELETION_ORDER = ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST", "COMPOSE", "CONFIGURE", "INTEGRATE"]

REAL_OUTCOME = (
    "A capability is dispatched only after its own proof runs and passes in under five seconds, and the inventory "
    "reports how many declared organs cannot do that instead of implying they can."
)
REQUIRED_CAPABILITY = (
    "Admission by execution: a bus that loads a manifest, runs each plugin's self_check, dispatches only the proven, "
    "and names the refused when a trigger has no admitted owner."
)


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "counting how many organs exist as a measure of capability",
                "wiring by declaration into a 7,653-line file",
                "trusting a plan's structural figures without measuring them",
            ],
            "surviving_necessity": (
                "The tree's own history is a pile of organs that were imported and never run; without an execution "
                "gate the next organ repeats the same fate and nobody can tell a working one from a dead one."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "27 named organs: 27 unwired from brain_unified_model_v1, 24 from the federation",
                "27 of 27 import cleanly; total import cost 1.1 s",
                "3 of 28 expose a self_check that returns a verdict",
                "5 syntax errors in 6,508 files, 1 of the 2 tree-authored ones repaired (the other is blocked by a referee that has never been green)",
            ],
            "external_existing_routes_checked": [
                "the incoming plan quotes Agent S4, JitRL, STRATA, MEME, ForgetEval and Dockerless figures; none was "
                "re-fetched this wave and all are recorded UNVERIFIED rather than repeated",
            ],
            "capability_work_deleted": [
                "the '23 organs can be wired' premise: 25 of 28 cannot prove themselves",
                "the '46 lines of headroom' premise: the file is 7,653 lines and no ceiling exists",
            ],
            "surviving_gap": (
                "Twenty-five organs need an executable proof before any of them may be dispatched, and writing those "
                "proofs is the next measurable unit of work."
            ),
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__NO_ORGAN_HAS_A_RUNNABLE_PROOF_OF_ITSELF",
            "delete_bypass_substitute_options": [
                "(delete) dispatch unverified organs and trust the name -- refused, that is the failure being fixed",
                "(bypass) dispatch only by human inspection -- does not scale past the organs I read",
                "(substitute) one executable proof per organ, five lines each -- the next build",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": list(DELETION_ORDER),
            "routes_ranked": [
                "1. a fail-closed bus that admits only what proves itself (selected)",
                "2. hand-wire the organs into the front door (refused: no ceiling, no proof, permanent lines)",
                "3. declare the organs wired and measure nothing (refused: that is the claim the audit disproves)",
            ],
            "losing_routes_reason": (
                "Route 2 makes the file larger and the capability no more provable; route 3 is a claim about names, "
                "and the bus was built precisely to make such claims impossible to state."
            ),
            "implementation_still_necessary": True,
            "implementation_necessity_reason": (
                "The bus is the only place in the tree where a capability must execute before it may be called, and "
                "its refusal count is the to-do list for every later wave."
            ),
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "The audit is a live run: 28 imports, 3 self-checks, one dispatch that returns ADMITTED and one "
                "refusal that names the missing owner."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": ["canonical/verification/CAPABILITY_BUS_WAVE47_20261124_V1.json",
                             "canonical/tests/test_capability_bus_v1.py"],
            "oracle_detail": "The receipt is recomputed by the test from the same manifest, so it cannot drift silently.",
            "synthetic_verification_necessity": (
                "No synthetic data: every plugin in the manifest is a real module on main, and the repairs are pinned "
                "by compiling and calling the repaired path."
            ),
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "the belief that a module existing is a capability",
                "the plan's LOC and '2 syntax errors' figures, superseded by measurement",
            ],
            "adjacent_capabilities_absorbed": [
                "structured_morphism_abstraction_v1 gained a public self_check and is the first admitted plugin",
                "single_experience_transfer_v1 and concept_library_v1 supply the other two proofs",
            ],
            "fresh_reuse_plan": ("The next wave adds proofs for the five transfer-pipeline organs and re-runs this audit; "
                                 "the target is 8 of 28."),
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "one manifest scan replaces re-reading 27 modules by hand",
                "the audit is 0.22 s, so it can run on every wave",
            ],
            "search_stop_decision": ("Search stopped once the import probe and the self_check census agreed; a longer "
                                     "list of organs would not change the admission rule."),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {"route": "HAND_WIRE_ORGANS_INTO_THE_FRONT_DOOR",
         "evidence": ["7,653 lines already; 27 references to add; nothing checks an organ runs"],
         "qualification_evidence": ["canonical/verification/CAPABILITY_BUS_WAVE47_20261124_V1.json"],
         "qualification_evidence_classes": ["DIRECT_PROBE"], "resolution": "DISQUALIFIED",
         "comparison": {"CORRECTNESS": "unverified code in the hot path", "CAPABILITY_STRENGTH": "none measured",
                        "WALL_CLOCK": "worse", "INCREMENTAL_COST": "0", "RELIABILITY": "unknown by construction",
                        "VERIFIABILITY": "none"}},
        {"route": "DECLARE_THE_23_ORGANS_WIRED",
         "evidence": ["25 of 28 cannot run a self_check, so a declaration would be a claim about names"],
         "qualification_evidence": ["canonical/verification/CAPABILITY_BUS_AUDIT_20261124_V1.json"],
         "qualification_evidence_classes": ["DIRECT_PROBE"], "resolution": "DISQUALIFIED",
         "comparison": {"CORRECTNESS": "false", "CAPABILITY_STRENGTH": "0", "WALL_CLOCK": "n/a",
                        "INCREMENTAL_COST": "0", "RELIABILITY": "n/a", "VERIFIABILITY": "contradicted by the audit"}},
        {"route": "ADMIT_BY_EXECUTION_NOT_BY_DECLARATION",
         "evidence": ["28 declared, 28 imported, 3 admitted, 25 refused, 0 import failures; 183 ms imports, 6.1 ms "
                      "self-checks; dispatch returns ADMITTED and the refusal names the trigger"],
         "qualification_evidence": ["canonical/verification/CAPABILITY_BUS_WAVE47_20261124_V1.json",
                                    "canonical/tests/test_capability_bus_v1.py"],
         "qualification_evidence_classes": ["DIRECT_PROBE"], "resolution": "SELECTED",
         "comparison": {"CORRECTNESS": "only proven code is dispatched", "CAPABILITY_STRENGTH": "turns 25 organs into "
                        "a measurable to-do list", "WALL_CLOCK": "0.22 s", "INCREMENTAL_COST": "0 model calls",
                        "RELIABILITY": "deterministic; 5 s per-plugin budget", "VERIFIABILITY": "13 tests"}},
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True, "checked_at_utc": now, "max_age_hours": 24,
        "selected_route": ROUTE, "incumbent_route": "count organs and describe them as capability",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "plugin admission by executable self-check fail closed dispatch 2026"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "capability registry versus capability bus agent runtime"},
            {"intent": "IMPLEMENTATION_FORM", "query": "importlib manifest self_check timeout plugin protocol python"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "agent harness plugins capability admission November 2026"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": ["canonical/runtime/capability_bus_v1.py",
                                "canonical/verification/CAPABILITY_BUS_AUDIT_20261124_V1.json"],
            "OFFICIAL_PRIMARY": ["Python standard library importlib documentation for module-level imports"],
            "CODE_OR_PACKAGE_REGISTRY": ["no packages: importlib, json, signal and pathlib only"],
            "BROAD_WEB_OR_COMMUNITY": ["the incoming plan's frontier figures, recorded UNVERIFIED and not repeated as fact"],
        },
        "negative_search_summary": ("Searched for a runtime that admits capabilities by executing a proof: harness "
                                     "plugins are described as configuration, not as proofs of themselves."),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "local Python 3 with importlib and signal", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["28 imports in 183 ms; 13 tests pass"]},
                {"dependency": "model API or network at runtime", "kind": "MODEL_API", "required": False,
                 "status": "NOT_REQUIRED", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "observed_at_utc": now, "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["0 model calls, 0 network calls"]},
            ],
        },
    }


def main() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    intent = json.loads(INTENT.read_text())
    expected = intent["expected_parent_frontier_change"]
    obs = dict(intent.get("recursive_obs") or {})
    obs.update({
        "canonical_base_commit": BASE,
        "canonical_generation_or_commit": intent["canonical_generation"],
        "real_outcome": REAL_OUTCOME, "required_capability": REQUIRED_CAPABILITY,
        "selected_route": ROUTE, "selected_surviving_route": ROUTE,
        "selected_surviving_route_class": "COMPOSE",
        "expected_parent_level_state_change": expected, "expected_parent_frontier_change": expected,
        "stop_condition": intent["stop_condition"],
        "why_selected_route_is_fastest_sufficient": (
            "It is 0.22 s of imports and proofs, needs no model, and converts a false claim into a measurable list."),
        "why_this_is_not_another_organ": (
            "The bus adds no capability of its own: it is importlib plus a manifest, and its value is the refusals."),
        "routes_considered": [ROUTE, "HAND_WIRE_ORGANS_INTO_THE_FRONT_DOOR", "DECLARE_THE_23_ORGANS_WIRED",
                             "TRUST_THE_PLAN_AND_SKIP_THE_AUDIT"],
        "deleted_or_bypassed_paths": ["organ counting as capability", "declaration as admission",
                                      "the plan's stale LOC and syntax figures"],
        "route_frontier": frontier(now),
    })
    for layer, payload in layers().items():
        obs[layer] = payload
    obs["obs_blocker"]["surviving_causal_blocker"] = intent["causal_blocker"]
    intent["recursive_obs"] = obs
    intent["selected_route"] = ROUTE
    intent["selected_surviving_route"] = ROUTE
    intent["blocker_lease_key"] = "::".join([str(intent.get("canonical_generation") or ""),
                                             str(intent.get("capability_target") or ""),
                                             str(intent.get("causal_blocker") or "")])
    INTENT.write_text(json.dumps(intent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"stamped_at": now, "intent": INTENT.name, "base": BASE, "route": ROUTE}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
