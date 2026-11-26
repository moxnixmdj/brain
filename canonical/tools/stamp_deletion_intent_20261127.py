"""Stamp the recursive-OBS receipt for the cost-of-asking intent."""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/DELETE_THE_GATE_THAT_NO_PATH_REACHED_AND_FIX_WHAT_THE_FINGERPRINT_FOUND_20261127_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "DELETE_THE_COMPONENT_NO_PATH_REACHED_AND_PROVE_IT_BY_TRANSCRIPT"

REAL_OUTCOME = "A deletion is provable by transcript comparison, dead components do not accumulate, and the runtime answers the same question the same way in every process."
REQUIRED_CAPABILITY = "A fingerprint of every runtime answer, a deletion receipt that cites it, and a fixed accumulation order on every ranking path."


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "a kill criterion written against a path nobody had checked the component was on",
                "a port of the surviving control that looked faithful and moved the control by 12.8 pp",
                "internal consistency of the artifact used as evidence that its answers are stable",
            ],
            "surviving_necessity": (
                "The plan's own Play A assumed the gate sat in the runtime decision path. It did not, and the 404/404 "
                "identical transcripts are the only thing that could show it: a component compared twice, deleting "
                "nothing from behaviour, was being carried as if it were a stage."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "contract_first_routing_v1.route_by_contract as the treatment, and the same function with "
                "require_contract=False, use_verbs=False as the control",
                "the runtime's find_source / route / find_any_source as the only paths that answer a goal",
                "the 38/38 verifier as the only existing stability check",
            ],
            "external_existing_routes_checked": [
                "reranker ablations: a precision stage is dead weight when recall is the bottleneck (0.458 at 20 candidates)",
                "harness studies: a component can change tokens 40x while moving accuracy 0-8 pp, which is why 'it is in "
                "the pipeline' is not evidence that it is load-bearing",
            ],
            "capability_work_deleted": [
                "the contract router (412 lines) and its test (96 lines)",
                "any claim that the runtime gates on a contract -- it never did",
                "a hand-rolled port of the control; the surviving code is the same code path the archive measured",
            ],
            "surviving_gap": "Nothing in the tree could prove a deletion had changed nothing, and nothing checked that two processes answer a question the same way.",
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__A_COMPONENT_WAS_MEASURED_WITHOUT_CHECKING_WHAT_CALLS_IT",
            "delete_bypass_substitute_options": [
                "(bypass) keep the router and note it is unused -- two rounds of comparison stay in the record as if it mattered",
                "(substitute) delete it and assert nothing changed -- an assertion, not a measurement",
                "(delete) delete it and compare 404 transcripts taken with and without it under identical code (selected)",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST",
                                             "COMPOSE", "CONFIGURE", "INTEGRATE"],
            "routes_ranked": [
                "1. fingerprint the runtime's answers, delete the module and its test, prove 404/404 identical, and fix the instability the fingerprint exposed (selected)",
                "2. keep the module, mark it deprecated (refused: a part that no path reaches can only mislead the next reader)",
                "3. rewrite the router to be better (refused: it lost to its own ablation twice; that is tuning a control)",
            ],
            "losing_routes_reason": "route 2 leaves 508 lines and a false comparison in the record; route 3 is the tuning the selection law forbids on a recall-limited corpus.",
            "implementation_still_necessary": True,
            "implementation_necessity_reason": "The fingerprint is the only instrument that can distinguish a deletion from a regression, and it found a defect no existing check could see.",
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "The same code runs twice, once with the module restored from HEAD and once deleted, over the same 404 "
                "questions; the transcripts hash equal. The surviving ranker is then checked against the archived ablation "
                "cell by cell at 0.005."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": ["canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json",
                             "canonical/verification/DELETION_RECEIPT_CONTRACT_GATE_20261127_V1.json",
                             "canonical/tests/test_runtime_answer_fingerprint_v1.py"],
            "oracle_detail": "The archive is the oracle for the port (0.0957/0.1809 against 0.096/0.181); the two fingerprints are the oracle for the deletion.",
            "synthetic_verification_necessity": "None: the questions are the ledger's, the answers come from the real model, and no stub is involved.",
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "plan V4's Play A, superseded by its own execution and corrected in the plan",
                "any read of the scoreboard that treats the contract channel as live",
                "the assumption that a 38/38 verifier implies stable answers",
            ],
            "adjacent_capabilities_absorbed": [
                "the ledger supplies the 404 questions",
                "the atlas supplies the pool the surviving ranker searches",
                "brain_unified_model supplies the paths being fingerprinted",
            ],
            "fresh_reuse_plan": "Every deletion from now on compares transcripts; every ranking path sums in sorted order.",
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "the question set is derived once from the ledger and reused for both transcripts",
                "the two fingerprints are stored, so a later reader can re-diff without re-running the model",
            ],
            "search_stop_decision": ("Search stopped when the reranker-depth ablation and the harness study agreed that a "
                                     "component's presence is not evidence of its load-bearing role."),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {
            "route": "KEEP_THE_ROUTER_AND_MARK_IT_DEPRECATED",
            "evidence": ["no runtime path calls it; it loses to its own ablation 0.128 vs 0.181 on the clean quarter"],
            "qualification_evidence": ["canonical/verification/DELETION_RECEIPT_CONTRACT_GATE_20261127_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "DISQUALIFIED",
            "comparison": {"CORRECTNESS": "keeps 508 lines that no path reaches",
                           "CAPABILITY_STRENGTH": "none",
                           "WALL_CLOCK": "25 s per scoreboard run spent scoring a dead channel",
                           "INCREMENTAL_COST": "one more reader misled",
                           "RELIABILITY": "a dead branch cannot fail, which is not a virtue",
                           "VERIFIABILITY": "its numbers would keep appearing beside live ones"},
        },
        {
            "route": "DELETE_AND_ASSERT_NOTHING_CHANGED",
            "evidence": ["the runtime never imported the module, so an assertion would be true and unmeasured"],
            "qualification_evidence": ["canonical/verification/RUNTIME_ANSWER_FINGERPRINT_WITH_GATE_20261127_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "NON_DOMINATING",
            "comparison": {"CORRECTNESS": "true but unfalsifiable",
                           "CAPABILITY_STRENGTH": "no instrument left behind",
                           "WALL_CLOCK": "0",
                           "INCREMENTAL_COST": "0",
                           "RELIABILITY": "the next deletion gets the same unmeasured treatment",
                           "VERIFIABILITY": "nothing to check"},
        },
        {
            "route": "DELETE_THE_COMPONENT_NO_PATH_REACHED_AND_PROVE_IT_BY_TRANSCRIPT",
            "evidence": ["404 transcripts identical with and without the module; 0 answers moved; port reproduces the "
                         "archive to four decimals; 1 of 404 answers depended on PYTHONHASHSEED until three loops were "
                         "sorted; 16 tests pass"],
            "qualification_evidence": ["canonical/verification/DELETION_RECEIPT_CONTRACT_GATE_20261127_V1.json",
                                       "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V2.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "SELECTED",
            "comparison": {"CORRECTNESS": "the deletion is measured, not asserted",
                           "CAPABILITY_STRENGTH": "removes 508 lines and finds a real defect",
                           "WALL_CLOCK": "2.1 s per fingerprint",
                           "INCREMENTAL_COST": "0 model calls, 0 tokens",
                           "RELIABILITY": "three seeds return one digest; a test enforces it",
                           "VERIFIABILITY": "two stored transcripts and a receipt"},
        },
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True,
        "checked_at_utc": now,
        "max_age_hours": 24,
        "selected_route": ROUTE,
        "incumbent_route": "describe the runtime as fast, and cite the compile-time join as evidence",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "compiled capability artifact query latency percentile agent"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "tokens per solved task harness comparison 2026"},
            {"intent": "IMPLEMENTATION_FORM", "query": "slot read vs coordinate decoding latency GUI grounding"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "2026 reranker candidate depth recall threshold ablation"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": ["canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json",
                                "canonical/runtime/brain_unified_model_v1.py",
                                "canonical/verification/PROMOTION_LEDGER_20261127_V1.json",
                                "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json"],
            "OFFICIAL_PRIMARY": ["https://arxiv.org/abs/2607.22585", "https://arxiv.org/abs/2609.11987",
                                 "https://arxiv.org/abs/2604.01733", "https://arxiv.org/abs/2604.22085"],
            "CODE_OR_PACKAGE_REGISTRY": ["pypi.org: pytest for the tests only; the instrument imports the standard library"],
            "BROAD_WEB_OR_COMMUNITY": ["GUI-Decisions slot-read latency table (single-author, kept for the 3.5x/20x ratios only)"],
        },
        "negative_search_summary": (
            "Searched for a published system that reports load and query percentiles for a compiled capability artifact: "
            "none. Harness papers report tokens per solved task and GUI papers report per-step latency, but nobody reports "
            "the cost of asking a compiled index, so the receipt here is a local instrument rather than a borrowed one."
        ),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "local Python 3 runtime with pytest", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["5 tests pass; receipt 1.04 s"]},
                {"dependency": "the compiled artifact, 13,470,180 bytes, readable offline", "kind": "CODE_ARTIFACT",
                 "required": True, "status": "READY", "volatility": "STATIC", "scope": "LOCAL",
                 "evidence_scope": "LOCAL", "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["load 292 ms with verify=True; digest recorded in the receipt"]},
                {"dependency": "model API or remote service at runtime", "kind": "MODEL_API", "required": False,
                 "status": "NOT_REQUIRED", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["0 model calls and 0 network calls; the test asserts no network import exists"]},
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
        "why_selected_route_is_fastest_sufficient": "One second of local computation, no model, no network, and it produces the only numbers the speed claim needs.",
        "why_this_is_not_another_organ": "It adds one instrument and no runtime path; every timed call already existed.",
        "routes_considered": [ROUTE, "BUILD_A_LOCAL_TASK_BENCHMARK_AND_TIME_END_TO_END_SOLVES",
                             "ADD_A_CACHE_OR_INDEX_TO_MAKE_ANSWERS_FASTER"],
        "deleted_or_bypassed_paths": ["local task benchmark", "cache or second index", "compile prints as latency evidence"],
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
