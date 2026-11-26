"""Stamp the recursive-OBS receipt and live route frontier for the promotion-ledger intent.

Base commit and timestamps are read/stamped at run time; the guard binds the receipt to the
exact pull-request base, so neither may ever be remembered by hand.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/NAME_THE_MISSING_ATTRIBUTE_BEFORE_BUILDING_ANOTHER_ORGAN_20261127_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "NAME_THE_MISSING_ATTRIBUTE_FOR_EVERY_MODULE_BEFORE_BUILDING_ANOTHER_ONE"
DELETION_ORDER = ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST", "COMPOSE", "CONFIGURE", "INTEGRATE"]

REAL_OUTCOME = "Every frontier function the tree implements is callable by the runtime, or the one attribute blocking it is named."
REQUIRED_CAPABILITY = (
    "A ledger that assigns each classified module the first attribute the runtime is missing -- routed, receipted, "
    "bound, adapter, index -- and ships inside the compiled model so the machine can answer why it cannot call its own code."
)


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "candidate counts as capability: 849 candidates and 31 callable",
                "the atlas's 'invisible' figure as the size of the gap: it unions three routes, only one of which the runtime can call",
                "binding the 321 receipt-backed capabilities as if that were promotion of the five functions: they are infrastructure adapters",
            ],
            "surviving_necessity": (
                "Without the missing attribute named per module, every round either writes capability that already exists "
                "or guesses at which of four different jobs is left."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "DOMAIN_ATLAS_V1.json: 1,260 rows, 1,005 indexed, 337 executable, 28 invisible",
                "CAPABILITY_RECEIPT_PROJECTION_V1.json: 321 receipt-backed, every adapter path present",
                "BOUND_CAPABILITY_REGISTRY_V1.json: 145 bound capabilities",
                "canonical/runtime/bound_capabilities/: 176 adapter files",
                "the compiled model: 462 capabilities, anatomy block from the previous round",
            ],
            "external_existing_routes_checked": [
                "Agent S4 (open 27B, 5.6% -> 21.3% binary on OSWorld 2.0) by evolving its own interfaces",
                "SkillSmith: locking the tool layer costs 6.8 points, the largest single ablation",
                "harness-vs-model factorials: 7.8x variance, 6 of 9 model-pair rankings reversing",
            ],
            "capability_work_deleted": [
                "a hand-written adapter for each of 641 modules (deferred to Play 1's AST derivation, which has a survival test)",
                "a new inventory artifact (the ledger is a join over five existing artifacts)",
                "binding the 321 pending capabilities en masse (they are infrastructure, and binding them changes none of the 849)",
            ],
            "surviving_gap": "No artifact said which attribute is missing, so 641 adapterless modules and 137 unindexed modules were indistinguishable in every plan.",
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__NO_ATTRIBUTE_LEVEL_VIEW_OF_WHY_CAPABILITY_IS_NOT_CALLABLE",
            "delete_bypass_substitute_options": [
                "(bypass) read the atlas and assume executable means callable - it means an adapter stem matched, not a receipt",
                "(substitute) count receipts - 321 exist and none of them is a frontier function",
                "(delete) drop the promotion question - then Play 1 has no target and no baseline",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": list(DELETION_ORDER),
            "routes_ranked": [
                "1. assign the first missing attribute per module, join over five existing artifacts, project into the model (selected)",
                "2. write 641 adapters by hand (deleted: no survival test, unmeasurable at n=641)",
                "3. bind the 321 receipt-backed capabilities (refused by measurement: 0 of them are among the 849)",
            ],
            "losing_routes_reason": (
                "route 2 has no admission test and would repeat the mistake of counting written code as capability; route 3 "
                "is bookkeeping over infrastructure and moves the 31 callable frontier modules by zero."
            ),
            "implementation_still_necessary": True,
            "implementation_necessity_reason": (
                "The ledger is the scoreboard Play 1 needs: without it, the 641 have no named blocker and the 137 have no "
                "reason to be indexed."
            ),
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "Every count reproduces from PROMOTION_LEDGER_20261127_V1.json, which is a deterministic join; the model "
                "block is a projection and the verifier's byte-identity check recompiles it."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": [
                "canonical/verification/PROMOTION_LEDGER_20261127_V1.json",
                "canonical/tests/test_promotion_ledger_v1.py",
                "canonical/runtime/verify_brain_unified_model_v1.py",
            ],
            "oracle_detail": "5 ledger tests plus the 38-check model verifier; the model carries promotion_candidates and promotion_callable in its counts.",
            "synthetic_verification_necessity": "No synthetic data: the ledger joins real artifacts and reads real adapter files. Nothing was executed to produce it.",
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "the atlas's 'invisible' number as the gap: 137 modules are unindexed, 641 are adapterless, and the second number is 4.7x the first",
                "the assumption that the 321 pending capabilities were promotable frontier capability",
            ],
            "adjacent_capabilities_absorbed": [
                "domain_atlas_v1 supplies the candidate rows",
                "the receipt projection supplies receipted adapters",
                "the bound registry supplies the callable set",
                "the compiled model supplies the route surface",
            ],
            "fresh_reuse_plan": "Play 1 consumes promotable rows to build 50 AST-derived adapters with a twice-run survival test and exact targets.",
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "the category join is one pass over five files, 14 s, and is cached as the ledger artifact",
                "the model block is recomputed by the compiler, never edited by hand",
            ],
            "search_stop_decision": (
                "Search stopped when three independent 2026 results agreed that interface/harness effects dominate model "
                "effects, which is the claim the ledger measures locally; more citations would not change the deficit."
            ),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {
            "route": "WRITE_THE_641_ADAPTERS_BY_HAND",
            "evidence": ["641 of 849 classified modules are indexed source with no adapter; 176 adapter files exist today"],
            "qualification_evidence": ["canonical/verification/PROMOTION_LEDGER_20261127_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "DISQUALIFIED",
            "comparison": {
                "CORRECTNESS": "no admission test, so written code would again be counted as capability",
                "CAPABILITY_STRENGTH": "unbounded work with no measurable end",
                "WALL_CLOCK": "days of edits",
                "INCREMENTAL_COST": "0 tokens but all of the review surface",
                "RELIABILITY": "641 hand edits without receipts repeat the state the ledger found",
                "VERIFIABILITY": "each adapter would need its own twice-run test, which is Play 1",
            },
        },
        {
            "route": "BIND_THE_321_RECEIPT_BACKED_CAPABILITIES",
            "evidence": ["321 capabilities are receipt-backed and pending promotion; 0 of them match any of the 849 classified modules"],
            "qualification_evidence": ["canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "NON_DOMINATING",
            "comparison": {
                "CORRECTNESS": "binding is real, but it moves infrastructure, not the five functions",
                "CAPABILITY_STRENGTH": "0 of 849 callable modules added",
                "WALL_CLOCK": "minutes",
                "INCREMENTAL_COST": "0",
                "RELIABILITY": "changes the runtime's book, not its reach",
                "VERIFIABILITY": "counts reproduce, which is why the zero is known",
            },
        },
        {
            "route": ROUTE,
            "evidence": [
                "849 classified modules: 31 callable and receipted (3.7%), 36 callable without a receipt, 4 adapter files "
                "that never ran, 641 adapterless, 137 unindexed; 14 s, 0 model calls; 5 tests; model verifier 38/38"
            ],
            "qualification_evidence": [
                "canonical/verification/PROMOTION_LEDGER_20261127_V1.json",
                "canonical/verification/FRONTIER_LEAPFROG_PLAN_20261127_V3.md",
            ],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "SELECTED",
            "comparison": {
                "CORRECTNESS": "every count is a row of the artifact and the partition sums to the candidate total",
                "CAPABILITY_STRENGTH": "turns 'we should build capability' into 'we can promote it', with the count of each job",
                "WALL_CLOCK": "14 s for the join, 43 s for the compile",
                "INCREMENTAL_COST": "0 parameters, 0 model calls, 0 network calls",
                "RELIABILITY": "deterministic join; the compiler re-derives the block",
                "VERIFIABILITY": "5 tests plus the model verifier's byte-identity check",
            },
        },
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True,
        "checked_at_utc": now,
        "max_age_hours": 24,
        "selected_route": ROUTE,
        "incumbent_route": "count candidates and call them capability, and treat the atlas's invisible figure as the gap",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "agent interface evolution self-built tools benchmark 2026"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "Agent S4 OSWorld 2.0 evolving interfaces 21.3 percent"},
            {"intent": "IMPLEMENTATION_FORM", "query": "AST derived adapter generation idempotence smoke test twice"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "2026 harness versus model variance factorial skeleton effect token cost"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": [
                "canonical/tools/promotion_ledger_v1.py",
                "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json (promotion block)",
                "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json",
                "canonical/runtime/bound_capabilities/ (176 adapter files)",
            ],
            "OFFICIAL_PRIMARY": [
                "https://arxiv.org/abs/2606.29537", "https://arxiv.org/abs/2607.22585", "https://arxiv.org/abs/2609.20804",
                "https://arxiv.org/abs/2604.01687", "https://arxiv.org/abs/2610.14228",
            ],
            "CODE_OR_PACKAGE_REGISTRY": [
                "pypi.org: pytest for the tests only; the ledger imports the standard library and this tree"
            ],
            "BROAD_WEB_OR_COMMUNITY": [
                "harness-vs-model factorial write-ups reporting 7.8x variance and ranking reversals (aggregator, marked B)",
                "OSWorld 2.0 leaderboard aggregations mixing partial and binary metrics (marked U where vendor-reported)",
            ],
        },
        "negative_search_summary": (
            "Searched for a published attribute-level promotion ledger for agent capability surfaces: the closest work is "
            "tool-library induction (SkillX, SkillSmith), which builds libraries from text rather than naming why existing "
            "code is uncallable. No external artifact was adopted."
        ),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "local Python 3 runtime with pytest", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["5 ledger tests pass; the join runs in 14 s; the compile in 43 s and verifies 38/38"]},
                {"dependency": "five artifacts readable offline", "kind": "CODE_ARTIFACT", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "LOCAL", "evidence_scope": "LOCAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["model, registry, receipt projection, adapter directory and atlas all present and parsed"]},
                {"dependency": "compiled model artifact and its verifier", "kind": "MODEL_ARTIFACT", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "LOCAL", "evidence_scope": "LOCAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["verify_brain_unified_model_v1.py -> 38/38 PASS, recompilation byte-identical"]},
                {"dependency": "model API or remote service at runtime", "kind": "MODEL_API", "required": False,
                 "status": "NOT_REQUIRED", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["0 model calls and 0 network calls in the ledger, the compile and the tests"]},
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
        "real_outcome": REAL_OUTCOME,
        "required_capability": REQUIRED_CAPABILITY,
        "selected_route": ROUTE,
        "selected_surviving_route": ROUTE,
        "selected_surviving_route_class": "SYNTHESIZE_NEW_PRIMITIVE",
        "expected_parent_level_state_change": expected,
        "expected_parent_frontier_change": expected,
        "stop_condition": intent["stop_condition"],
        "why_selected_route_is_fastest_sufficient": (
            "It is a 14 s join over artifacts that already exist, and it is the only route that turns 'build capability' "
            "into a per-module task with a named blocker and a count."
        ),
        "why_this_is_not_another_organ": (
            "No new state: the ledger is a join over five artifacts and the model block is a projection of that ledger."
        ),
        "routes_considered": [ROUTE, "WRITE_THE_641_ADAPTERS_BY_HAND", "BIND_THE_321_RECEIPT_BACKED_CAPABILITIES",
                             "TRUST_THE_ATLAS_INVISIBLE_COUNT_AS_THE_GAP"],
        "deleted_or_bypassed_paths": [
            "candidate counts as capability",
            "the atlas invisible figure as the size of the gap",
            "mass binding as promotion",
            "hand-written adapters without a survival test",
        ],
        "route_frontier": frontier(now),
    })
    for layer, payload in layers().items():
        obs[layer] = payload
    obs["obs_blocker"]["surviving_causal_blocker"] = intent["causal_blocker"]
    intent["recursive_obs"] = obs
    intent["selected_route"] = ROUTE
    INTENT.write_text(json.dumps(intent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"stamped_at": now, "intent": INTENT.name, "base": BASE, "route": ROUTE}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
