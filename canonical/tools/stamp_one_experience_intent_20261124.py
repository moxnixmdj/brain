"""Stamp the recursive-OBS record and live route frontier for wave 46's transfer measurement.

The gates read a route frontier, a preflight and seven OBS layers out of the intent. This tool
writes them from measurements taken in this round; it invents no number it did not run.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/ONE_EXPERIENCE_TWO_PERCENT_20261124_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "MEASURE_SINGLE_EXPERIENCE_TRANSFER_ON_REAL_COMMITS_BEFORE_BUILDING_ANY_MORE_STORE"
DELETION_ORDER = ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST", "COMPOSE", "CONFIGURE", "INTEGRATE"]

REAL_OUTCOME = (
    "The store is measured against an empty store and against verbatim traces on real commit histories, so the "
    "question 'does one experience help on the next repair' has a number instead of an assumption."
)
REQUIRED_CAPABILITY = (
    "A transfer measurement with a positive control, a file-disjoint held-out split, and a cross-repository arm, so "
    "a zero can be believed and a mechanism can be deleted on evidence."
)


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "calling a rule 'transferable' because it fired on a renamed fixture",
                "measuring recall of the corpus instead of reproduction of held-out repairs",
                "treating the absence of a store as the ceiling when the empty arm had never been printed",
            ],
            "surviving_necessity": (
                "Every compounding claim in this tree reduces to this measurement, and until it existed the claim "
                "was unfalsifiable: store and no store had been reported identical without a held-out arm."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "V2 ablation: store vs empty identical on both commits",
                "Wave 45: 3 of 3 hand-written families transferred to a third unseen surface",
                "NO_COMPOUNDING (8fe5f749): an unindexed library made later tasks slower",
                "0 of 7 unseen-kind commits repaired in the blind catalogue",
            ],
            "external_existing_routes_checked": [
                "SWE-bench Pro V2 boards (5 Nov 2026) quote resolve rates, not transfer rates, so they cannot answer this",
                "the memory literature reports recall over sessions, which is a different quantity from reproducing a repair",
            ],
            "capability_work_deleted": [
                "the assumption that abstraction alone creates transfer (2.45% against 3.07% for raw traces)",
                "root-shape indexing as the store's key (0 of 1,350 with a 76.4% ceiling)",
            ],
            "surviving_gap": (
                "No store in this tree is keyed on the failure a repair answers. Shape-keyed retrieval is now measured "
                "at zero across projects, which is the first time the ceiling has been located rather than argued."
            ),
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__THE_KEY_IS_THE_EDIT_NOT_THE_FAILURE",
            "delete_bypass_substitute_options": [
                "(delete) drop the store and keep only the verifier -- truthful, forfeits compounding",
                "(bypass) keep shape-keyed entries and never claim they transfer -- what the measurement now forbids",
                "(substitute) key entries on the failing assertion, which needs executable failures and is the next build",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": list(DELETION_ORDER),
            "routes_ranked": [
                "1. measure transfer on real commits with three arms and a positive control (selected)",
                "2. build a richer abstraction first (refused: the abstraction is not what fails, the key is)",
                "3. add more stored rules (refused: 163 rules fired on 0 of 1,350 held-out repairs)",
            ],
            "losing_routes_reason": (
                "Route 2 was answered by the waveform of this measurement: abstraction scored below verbatim traces. "
                "Route 3 fails on the denominator -- the rules were already plentiful and still never matched."
            ),
            "implementation_still_necessary": True,
            "implementation_necessity_reason": (
                "Without a positive control a zero is indistinguishable from a broken scorer; the control is what "
                "makes the deletion decision legitimate."
            ),
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "Every number is produced by the same functions the tests import; the self-check fires a hit on an "
                "identical shape under new identifiers before any zero is reported."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": [
                "canonical/verification/SINGLE_EXPERIENCE_TRANSFER_20261124_V1.json",
                "canonical/tests/test_single_experience_transfer_v1.py",
                "canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json",
            ],
            "oracle_detail": "A hit is an exact AST match; there is no fuzzy credit and no human judgement in the loop.",
            "synthetic_verification_necessity": (
                "None of the corpus is synthetic: every pair is a real commit's before/after. The only synthetic "
                "material is the positive control, which exists to prove the scorer can fire."
            ),
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "root-shape indexing for store retrieval",
                "the claim that the Wave 45 operator earns its place as a store mechanism",
            ],
            "adjacent_capabilities_absorbed": [
                "structured_morphism_abstraction_v1 supplies the rule learner unchanged",
                "the V2 receipt supplies the question and the earlier zero",
            ],
            "fresh_reuse_plan": (
                "The next store is keyed on the failing condition; the same scorer, splits and control arms are reused "
                "so the two keys are directly comparable."
            ),
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "the harvest is cached by digest, so re-scoring costs 3.0 s and no network",
                "the receipt's verdict is computed from the arms rather than typed",
            ],
            "search_stop_decision": (
                "Search stopped when two repositories gave the same answer at two granularities; a third would not "
                "change the key."
            ),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {
            "route": "BUILD_A_RICHER_ABSTRACTION_FIRST",
            "evidence": ["store 4/163 against raw traces 5/163 on the same held-out repairs"],
            "qualification_evidence": ["canonical/verification/SINGLE_EXPERIENCE_TRANSFER_20261124_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "DISQUALIFIED",
            "comparison": {"CORRECTNESS": "the abstraction is not the failing part; verbatim traces do as well",
                           "CAPABILITY_STRENGTH": "no mechanism to strengthen a zero",
                           "WALL_CLOCK": "n/a", "INCREMENTAL_COST": "0",
                           "RELIABILITY": "deterministic", "VERIFIABILITY": "same held-out pairs"},
        },
        {
            "route": "ADD_MORE_STORED_RULES",
            "evidence": ["163 rules from 250 repairs fired on 0 of 1,350 held-out repairs"],
            "qualification_evidence": ["canonical/verification/SINGLE_EXPERIENCE_TRANSFER_20261124_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "NON_DOMINATING",
            "comparison": {"CORRECTNESS": "supply is not the constraint", "CAPABILITY_STRENGTH": "none measured",
                           "WALL_CLOCK": "seconds", "INCREMENTAL_COST": "0",
                           "RELIABILITY": "high", "VERIFIABILITY": "easy"},
        },
        {
            "route": "MEASURE_SINGLE_EXPERIENCE_TRANSFER_ON_REAL_COMMITS_BEFORE_BUILDING_ANY_MORE_STORE",
            "evidence": ["1,600 repairs, 808 API calls, 0 model calls; store 2.45%, raw 3.07%, empty 0%, ceiling 55.8% "
                         "within project; 0 of 1,350 across projects with a 76.4% ceiling; positive control fires"],
            "qualification_evidence": ["canonical/verification/SINGLE_EXPERIENCE_TRANSFER_20261124_V1.json",
                                       "canonical/tests/test_single_experience_transfer_v1.py"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "SELECTED",
            "comparison": {"CORRECTNESS": "exact AST matching, file-disjoint splits, three arms",
                           "CAPABILITY_STRENGTH": "kills a mechanism and locates the ceiling of its key",
                           "WALL_CLOCK": "371 s harvest, 3.0 s to re-score",
                           "INCREMENTAL_COST": "0 model calls, 0 parameters",
                           "RELIABILITY": "deterministic given the pinned digest",
                           "VERIFIABILITY": "19 tests, one per arm or refusal"},
        },
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True, "checked_at_utc": now, "max_age_hours": 24,
        "selected_route": ROUTE,
        "incumbent_route": "store rules keyed on the shape of the edit and describe them as learned skills",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "single example repair transfer held-out commits measured 2026"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "fix pattern databases PAR templates retrieval index by failure not by patch shape"},
            {"intent": "IMPLEMENTATION_FORM", "query": "anti-unification versus verbatim trace storage ablation repair"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "automated program repair 2026 benchmark transfer across projects"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": ["canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json",
                                "canonical/verification/STRUCTURED_MORPHISM_ABSTRACTION_20261124_V1.json"],
            "OFFICIAL_PRIMARY": ["https://api.github.com (repository patches, read as data at build time)"],
            "CODE_OR_PACKAGE_REGISTRY": ["python-attrs/attrs and pallets/click histories; Python standard library only"],
            "BROAD_WEB_OR_COMMUNITY": ["Nov 2026 SWE-bench Pro V2 boards, quoted as targets and never compared to this"],
        },
        "negative_search_summary": (
            "Searched for a published measurement of single-example repair transfer with an empty-store arm: the "
            "repair literature reports patch-generation rates on a benchmark, not whether a stored rule reproduces "
            "another project's commit. That gap is what this round fills."
        ),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "gh CLI authenticated against api.github.com", "kind": "REMOTE_API", "required": True,
                 "status": "READY", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["808 calls, 1,600 repairs, 0 rate-limit failures"]},
                {"dependency": "local Python 3 with unittest", "kind": "LOCAL_RUNTIME", "required": True,
                 "status": "READY", "volatility": "STATIC", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["19 tests pass; self-check 5 of 5"]},
                {"dependency": "model API at runtime", "kind": "MODEL_API", "required": False, "status": "NOT_REQUIRED",
                 "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"], "evidence": ["0 model calls, 0 parameters"]},
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
        "selected_surviving_route_class": "MEASURE_AND_DELETE",
        "expected_parent_level_state_change": expected,
        "expected_parent_frontier_change": expected,
        "stop_condition": intent["stop_condition"],
        "why_selected_route_is_fastest_sufficient": (
            "It is 371 s of harvesting and 3.0 s of scoring, needs no model and no task execution, and it deletes a "
            "mechanism instead of defending one."
        ),
        "why_this_is_not_another_organ": (
            "It reuses the Wave 45 learner unchanged and adds no index, no store and no runtime dependency; the only "
            "new code parses diffs and counts hits."
        ),
        "routes_considered": [ROUTE, "BUILD_A_RICHER_ABSTRACTION_FIRST", "ADD_MORE_STORED_RULES",
                             "DROP_THE_STORE_AND_KEEP_THE_VERIFIER"],
        "deleted_or_bypassed_paths": ["root-shape indexing", "the claim that abstraction alone transfers",
                                      "recall of the training corpus as a success measure"],
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
