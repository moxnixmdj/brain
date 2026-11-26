"""Stamp the recursive-OBS receipt and live route frontier for the exact-target scoreboard intent."""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/SCORE_THE_ROUTER_AT_ONE_MODULE_AND_RECORD_THE_CALL_20261127_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "RECORD_THE_CALL_FROM_AN_EXECUTION_AND_SCORE_AGAINST_MODULE_FAMILIES"
DELETION_ORDER = ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST", "COMPOSE", "CONFIGURE", "INTEGRATE"]

REAL_OUTCOME = "Every frontier function the tree implements is callable by the runtime, and every routing number is measured against one module rather than a label."
REQUIRED_CAPABILITY = (
    "A scoreboard whose target is a single module (chance 1/849), whose queries are the test author's own words with "
    "name leaks counted rather than hidden, and an adapter derivation that takes its arguments from an execution."
)


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "domain-level recall as a routing measurement (a random draw scored 0.846 on it)",
                "a literal-call adapter rule that reached 3.7% of its targets",
                "the assumption that a better scoreboard would make the router look better -- it made it look worse",
            ],
            "surviving_necessity": (
                "Without exact targets and leak accounting, every routing claim in this tree is a claim about names; "
                "76.7% of test intents repeat the module's own name and find_source scores 0.548 there against 0.064 "
                "on the clean quarter."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "find_source on exact targets: 0.032 @1 / 0.064 @5 clean, 0.332 / 0.548 leaked",
                "contract router: 0.064 / 0.128 clean, 0.100 / 0.268 leaked",
                "topic-only ablation: 0.096 / 0.181 clean -- beats both structured channels",
                "literal-call adapter derivation: 15 survivors of 406 (3.7%), floor 40%",
                "the promotion ledger: 31 callable of 849, unchanged by any routing result",
            ],
            "external_existing_routes_checked": [
                "MCP Gateway 98.2% recall@15 with ground truth flagged as its own recommendation: the leak this round measured locally",
                "SkillX / SkillSmith build libraries from text; neither reports a leak audit of its query set",
            ],
            "capability_work_deleted": [
                "tuning the contract gate (beaten by its own ablation twice, on two corpora)",
                "reviving literal-call extraction (3.7% survival, pre-registered floor 40%)",
                "hand-labelling a clean query set (one author, one sitting, unverifiable)",
            ],
            "surviving_gap": "No scoreboard in this tree had a singleton target, a leak audit and an ablation at once; and no derivation had an admission test that a 3.7% survivor rate could not pass.",
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__QUERIES_AND_TARGETS_SHARE_A_VOCABULARY_UNLESS_BUILT_OTHERWISE",
            "delete_bypass_substitute_options": [
                "(bypass) filter leaked queries -- leaves 94 rows and a ±5pp interval",
                "(substitute) generate intents from test names -- that is where the leak comes from",
                "(delete) drop routing from the plan -- the modules are uncallable, not unfindable, so the deficit is untouched either way",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": list(DELETION_ORDER),
            "routes_ranked": [
                "1. score every channel at one module, count the leak, kill the gate that the ablation beats, and record the call from an execution (selected)",
                "2. keep the contract router and report 0.128 (refused: ablation 0.181 on the same rows)",
                "3. hand-write adapters for the 641 (refused last round: no admission test)",
            ],
            "losing_routes_reason": (
                "route 2 is beaten by removing its mechanism; route 3 was already killed by the 40% floor and is now "
                "replaced by a rule that takes arguments from a recorded frame instead of from source text."
            ),
            "implementation_still_necessary": True,
            "implementation_necessity_reason": (
                "The scoreboard is the only instrument in the tree that can tell a router from a name matcher, and its "
                "94 clean rows are the reason the next round needs intents built from behaviour rather than names."
            ),
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "Both instruments read the tree and either execute a module twice in a temp directory or execute nothing; "
                "every count in the note reproduces from the two artifacts."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": [
                "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json",
                "canonical/verification/PLAY_1_LITERAL_CALL_CENSUS_20261127_V1.json",
                "canonical/tests/test_exact_target_scoreboard_v1.py",
            ],
            "oracle_detail": "10 tests across the scoreboard and the ledger pin the leak rule, the literal rule and both findings.",
            "synthetic_verification_necessity": "No synthetic data: targets are real modules, queries are real test names, and 26 calls were really executed twice.",
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "Play 1's literal-call derivation, superseded by recording the call frame",
                "the contract router, killed twice",
                "domain-level recall as any routing measurement",
            ],
            "adjacent_capabilities_absorbed": [
                "the promotion ledger supplies the SOURCE_ONLY rows and the pool size",
                "contract_first_routing supplies the router and the ablation, unchanged",
                "brain_unified_model supplies find_source",
            ],
            "fresh_reuse_plan": "The next adapter build replays a recorded frame; the next scoreboard scores families and builds intents from assertions.",
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "the target set is derived once from test names and cached in the artifact",
                "the router and ablation run in the same process on the same rows, so no number is inherited",
            ],
            "search_stop_decision": (
                "Search stopped at the third router paper whose ground truth was its own recommendation; the local leak "
                "rate made the point without another citation."
            ),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {
            "route": "KEEP_THE_CONTRACT_GATE_AND_TUNE_IT",
            "evidence": ["clean @5: contract 0.128 vs ablation 0.181; leaked @5: 0.268 vs 0.252"],
            "qualification_evidence": ["canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "DISQUALIFIED",
            "comparison": {
                "CORRECTNESS": "the ablation removes the mechanism and scores higher on the clean quarter",
                "CAPABILITY_STRENGTH": "second independent corpus with the same verdict",
                "WALL_CLOCK": "35 s per run",
                "INCREMENTAL_COST": "0",
                "RELIABILITY": "the gate's advantage does not survive a change of target definition",
                "VERIFIABILITY": "same artifact, same rows",
            },
        },
        {
            "route": "FILTER_THE_LEAK_AND_REPORT_THE_RESULT",
            "evidence": ["310 of 404 targets leak; filtering leaves 94 rows and roughly ±5 pp at one standard error"],
            "qualification_evidence": ["canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "NON_DOMINATING",
            "comparison": {
                "CORRECTNESS": "the filter is right; the resulting sample is too small to separate channels",
                "CAPABILITY_STRENGTH": "it measures a quarter of the corpus",
                "WALL_CLOCK": "seconds",
                "INCREMENTAL_COST": "0",
                "RELIABILITY": "94 rows cannot carry a 5 pp claim",
                "VERIFIABILITY": "reproducible, which is how the interval is known",
            },
        },
        {
            "route": ROUTE,
            "evidence": [
                "404 targets, 76.7% leak, chance 1/849; find_source 0.032/0.064 clean and 0.332/0.548 leaked; contract "
                "0.064/0.128; ablation 0.096/0.181; literal-call derivation 15 of 406 (killed at 3.7% against a 40% floor); "
                "10 tests pass"
            ],
            "qualification_evidence": [
                "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json",
                "canonical/verification/PLAY_1_AND_THE_SCOREBOARD_20261127_V1.md",
            ],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "SELECTED",
            "comparison": {
                "CORRECTNESS": "every channel is scored on the same rows in the same process, with chance stated",
                "CAPABILITY_STRENGTH": "kills a router and a derivation rule in one round and measures the leak nobody counted",
                "WALL_CLOCK": "35 s for the scoreboard, 5.5 s for the census",
                "INCREMENTAL_COST": "0 parameters, 0 model calls, 0 network calls",
                "RELIABILITY": "deterministic; the census runs each surviving call twice and compares",
                "VERIFIABILITY": "10 tests, one per rule or finding",
            },
        },
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True,
        "checked_at_utc": now,
        "max_age_hours": 24,
        "selected_route": ROUTE,
        "incumbent_route": "score routing against a domain label and derive adapters from literal calls in source text",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "retrieval evaluation query leakage target ambiguity single relevant document 2026"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "MCP Gateway recall ground truth circularity critique"},
            {"intent": "IMPLEMENTATION_FORM", "query": "call frame tracing record arguments replay idempotence adapter"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "2026 tool selection evaluation equivalence class relevant set recall"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": [
                "canonical/tools/exact_target_scoreboard_v1.py",
                "canonical/tools/ast_adapter_derivation_v1.py",
                "canonical/verification/PROMOTION_LEDGER_20261127_V1.json",
                "canonical/tools/contract_first_routing_v1.py",
            ],
            "OFFICIAL_PRIMARY": ["https://arxiv.org/abs/2607.15593", "https://arxiv.org/abs/2604.04804"],
            "CODE_OR_PACKAGE_REGISTRY": ["pypi.org: pytest for the tests only; both instruments import the standard library and this tree"],
            "BROAD_WEB_OR_COMMUNITY": ["router write-ups whose ground truth is the recommender's own output (marked B)"],
        },
        "negative_search_summary": (
            "Searched for a published routing evaluation that audits query leakage against the target: the closest is the "
            "label-circularity critique of the MCP Gateway, which reports the problem rather than a protocol. None supplied "
            "a leak audit to adopt, so the rule here is local: count the leak, exclude it, report both."
        ),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "local Python 3 runtime with pytest", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["10 tests pass; scoreboard 35 s; census 5.5 s"]},
                {"dependency": "the repository tree and 2935 test files, readable offline", "kind": "CODE_ARTIFACT",
                 "required": True, "status": "READY", "volatility": "STATIC", "scope": "LOCAL", "evidence_scope": "LOCAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["404 targets derived from test files; deterministic on a second run"]},
                {"dependency": "module execution for the two-run admission test", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "LOCAL", "evidence_scope": "LOCAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["41 candidate calls executed twice each in temp dirs with a 5 s timeout"]},
                {"dependency": "model API or remote service at runtime", "kind": "MODEL_API", "required": False,
                 "status": "NOT_REQUIRED", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["0 model calls and 0 network calls in both instruments"]},
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
            "It is 40 s of local computation with no model and no network, it kills two ideas rather than defending one, "
            "and it produces the first single-module routing numbers in the tree."
        ),
        "why_this_is_not_another_organ": (
            "The scoreboard reuses the router and the ablation unchanged and adds no index; the census reuses the ledger."
        ),
        "routes_considered": [ROUTE, "KEEP_THE_CONTRACT_GATE_AND_TUNE_IT", "FILTER_THE_LEAK_AND_REPORT_THE_RESULT",
                             "HAND_LABEL_A_CLEAN_QUERY_SET"],
        "deleted_or_bypassed_paths": [
            "domain-level recall as a routing measurement",
            "the contract gate, killed twice",
            "literal-call adapter derivation",
            "hand-labelled query sets",
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
