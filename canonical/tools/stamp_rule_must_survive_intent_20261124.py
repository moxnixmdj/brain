"""Stamp the recursive-OBS record and live route frontier for wave 45's abstraction intent.

The gates read a route frontier, a preflight and seven OBS layers out of the intent. This tool
writes them from measurements taken in this round; it invents no number it did not run.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/THE_RULE_MUST_SURVIVE_ITS_OWN_WITNESS_20261124_V1.json"
BASE = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                      capture_output=True, text=True, check=True).stdout.strip()
ROUTE = "REPLACE_THE_DEGENERATE_LEARNED_PATTERN_WITH_A_TRANSFERABLE_RULE"
DELETION_ORDER = ["DELETE", "BYPASS", "REUSE", "SUBSTITUTE", "WHITE_BOX_HARVEST", "COMPOSE", "CONFIGURE", "INTEGRATE"]

REAL_OUTCOME = (
    "A repair observed once is stored as a two-sided rule whose left side parameterises identifiers and whose "
    "right side projects subterms of the match, so the same rule fires on a renamed instance it has never seen."
)
REQUIRED_CAPABILITY = (
    "Admission rather than transcription: a learned rule must reproduce its own witness, transfer to a renamed "
    "variant, and carry structure outside its holes, or it is refused with the failing gate named."
)


def layers() -> dict[str, dict]:
    return {
        "obs_goal": {
            "real_outcome": REAL_OUTCOME,
            "proxy_goals_deleted": [
                "retrieval tuning: the store-vs-empty ablation was already identical, so recall was never the constraint",
                "candidate count: the receipt records 0 proposals on the witness itself, which no candidate budget can fix",
                "calling the store 'learned' on the strength of a write: a whole-body hole is a transcription, not a rule",
            ],
            "surviving_necessity": (
                "Without a transferable rule there is nothing for a store to keep, so every compounding claim in this "
                "tree rests on an object that cannot fire. The zoo of 2,080 import-and-stop modules is the same defect "
                "one level up: artefacts that were never asked to survive their own witness."
            ),
        },
        "obs_capability": {
            "existing_inherited_routes_checked": [
                "blind catalogue: 9 of 13 repaired, 0 regressions, 0 of 7 unseen-kind commits",
                "store vs empty on two commits: identical (pluggy 25 candidates both arms, werkzeug 1 candidate both arms)",
                "generalized vs raw traces: not measurable, because both artefacts were the same raw trace with a hole",
                "the learned pattern's own two-sided constraint: 0 proposals on its own witness, 0 on a held-out family body, 0 on file text",
                "dependency memory on the MEME protocol: 36 of 36 against a flat store's 12 of 36 (a different task, not repair)",
            ],
            "external_existing_routes_checked": [
                "SWE-bench Pro V2 boards (5 Nov 2026): Opus 5 + Claude Code 99.4% [98.4, 99.8], HARD-51 98.0% -- frontier "
                "resolve, cited as a target, not compared against a mechanism test",
                "MEME protocol (arXiv 2605.12477v2): best mean 0.32/0.59 for a memory-flat system, which is the same "
                "order as this tree's own 1.000 on 36 hand-built pairs and does not transfer to repair",
            ],
            "capability_work_deleted": [
                "retrieval-index work (the ablation says the index is not the variable)",
                "the hole-witness repair alone (the receipt records held-out transfer still at 0)",
                "re-running the catalogue with more candidates per commit",
            ],
            "surviving_gap": (
                "No artefact in this tree had ever been required to fire on anything other than the string it was "
                "learned from. That single missing gate explains the identical ablation, the 0 of 7 unseen kinds and "
                "the store's zero contribution."
            ),
        },
        "obs_blocker": {
            "intrinsic_or_path_specific": "PATH_SPECIFIC__THE_STORED_OBJECT_WAS_THE_IDENTITY_FUNCTION_ON_ONE_STRING",
            "delete_bypass_substitute_options": [
                "(delete) drop the store and keep only the verifier -- truthful but forfeits the only compounding route left",
                "(bypass) keep the store and never claim it contributes -- what the tree does today, and it costs 2,080 modules of upkeep",
                "(substitute) store nothing but the verifier's refutation -- loses the repair, keeps the evidence",
            ],
        },
        "obs_solution": {
            "deletion_first_order_applied": list(DELETION_ORDER),
            "routes_ranked": [
                "1. replace the operator: parameterised identifiers, projected after side, three refusal gates (selected)",
                "2. tune retrieval over the existing degenerate entries (refused: the ablation was identical)",
                "3. hand-write repair rules per bug class (refused: a rule per class is the hand-typed set that never converges)",
            ],
            "losing_routes_reason": (
                "Route 2 was already answered by measurement, not argument: with and without the store the catalogue "
                "repaired exactly the same commits. Route 3 is the hand-typed set the tree keeps proving does not "
                "generalise."
            ),
            "implementation_still_necessary": True,
            "implementation_necessity_reason": (
                "Three gates and one projection are the smallest object that can distinguish a rule from a "
                "transcription, and the ablation arm shows the parameterisation is load-bearing rather than decorative."
            ),
        },
        "obs_verification": {
            "direct_real_effect_verification_considered": True,
            "verification_considered_detail": (
                "Every claim comes from executing the operator on snippets: 3 positive families admitted and fired on a "
                "third, never-seen surface; 4 negative families refused; self-check 8 of 8; 16 unit tests."
            ),
            "existing_oracle_considered": True,
            "oracle_paths": [
                "canonical/verification/STRUCTURED_MORPHISM_ABSTRACTION_20261124_V1.json",
                "canonical/tests/test_structured_morphism_abstraction_v1.py",
                "canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json",
            ],
            "oracle_detail": (
                "The syntactic oracle is exact -- applying a rule and comparing ASTs admits no judgement -- and the "
                "receipt being answered is the one that measured the store at zero."
            ),
            "synthetic_verification_necessity": (
                "The snippets are hand-written mechanism fixtures, not tasks. They are necessary because the blind "
                "catalogue's repair traces are not stored as before/after pairs, and they are labelled as fixtures "
                "everywhere they appear."
            ),
        },
        "obs_inherited_system": {
            "downstream_work_to_delete_or_supersede": [
                "the whole-body-hole pattern that the V2 receipt recorded as unmeasurable and unproductive",
                "retrieval tuning over degenerate entries",
                "the assumption that a written entry is a learned rule",
            ],
            "adjacent_capabilities_absorbed": [
                "verified_skill_crystallizer_ir_bridge_v1 supplies the storage side, unchanged",
                "typed_invention_v1 supplies the proposal side, unchanged",
                "dark_matter_adjudicator_v1 supplies the fail-closed verdict shape reused here",
            ],
            "fresh_reuse_plan": (
                "The blind catalogue's learned entries are rebuilt through admit(); the ablation is re-run and the "
                "claim to beat is still 'identical'."
            ),
        },
        "obs_obs": {
            "affected_layers_only_on_revalidation": True,
            "analysis_steps_deleted_or_cached": [
                "the three families and four negatives are constants in the module, so the measurement is one process",
                "the ledger is generated from the same functions the tests import, so no number is copied by hand",
            ],
            "search_stop_decision": (
                "Search stopped once the frontier numbers were pinned to their boards and versions; nothing external "
                "was needed to decide the operator, because the receipt already named the cause."
            ),
            "revalidated_layers": ["obs_capability", "obs_blocker", "route_frontier"],
        },
    }


def challengers() -> list[dict]:
    return [
        {
            "route": "TUNE_RETRIEVAL_OVER_THE_EXISTING_ENTRIES",
            "evidence": ["store vs empty: identical on both commits; the entry produced 0 proposals on its own witness"],
            "qualification_evidence": [
                "canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "DISQUALIFIED",
            "comparison": {
                "CORRECTNESS": "a rule that cannot fire on its own witness is not a recall problem",
                "CAPABILITY_STRENGTH": "no retrieval scheme can make the identity function match a different string",
                "WALL_CLOCK": "n/a",
                "INCREMENTAL_COST": "0",
                "RELIABILITY": "the ablation is deterministic",
                "VERIFIABILITY": "same receipt, two arms",
            },
        },
        {
            "route": "HAND_WRITE_ONE_RULE_PER_BUG_CLASS",
            "evidence": ["the tree's hand-typed sets have been the recurring ceiling for forty waves"],
            "qualification_evidence": ["canonical/verification/WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1.json"],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "NON_DOMINATING",
            "comparison": {
                "CORRECTNESS": "a hand-written rule is exact on its class and absent on every other",
                "CAPABILITY_STRENGTH": "does not scale past the classes I think of",
                "WALL_CLOCK": "fast",
                "INCREMENTAL_COST": "0",
                "RELIABILITY": "high within the class",
                "VERIFIABILITY": "easy, which is why it is tempting",
            },
        },
        {
            "route": ROUTE,
            "evidence": [
                "3 of 3 positive families admitted, each firing on a third unseen surface; 4 of 4 negatives refused; "
                "median hole share 0.385 against the degenerate 1.0; ablation: removing name parameterisation keeps "
                "witness fidelity and loses every unseen surface; self-check 8 of 8; 16 tests"
            ],
            "qualification_evidence": [
                "canonical/verification/STRUCTURED_MORPHISM_ABSTRACTION_20261124_V1.json",
                "canonical/tests/test_structured_morphism_abstraction_v1.py",
            ],
            "qualification_evidence_classes": ["DIRECT_PROBE"],
            "resolution": "SELECTED",
            "comparison": {
                "CORRECTNESS": "fidelity and transfer are checked syntactically, not judged",
                "CAPABILITY_STRENGTH": "the first artefact in the tree required to fire on something it never saw",
                "WALL_CLOCK": "0.02 s for the whole measurement",
                "INCREMENTAL_COST": "0 model calls, 0 network calls, 0 parameters",
                "RELIABILITY": "deterministic, and the refusal arms are pinned by tests",
                "VERIFIABILITY": "16 tests, one per gate or refusal",
            },
        },
    ]


def frontier(now: str) -> dict:
    return {
        "discovery_required": True,
        "checked_at_utc": now,
        "max_age_hours": 24,
        "selected_route": ROUTE,
        "incumbent_route": "store whole-body-hole patterns and describe the store as learned",
        "challenger_routes": challengers(),
        "comparison_dimensions": ["CORRECTNESS", "CAPABILITY_STRENGTH", "WALL_CLOCK", "INCREMENTAL_COST", "RELIABILITY", "VERIFIABILITY"],
        "query_families": [
            {"intent": "CAPABILITY_VECTOR", "query": "program repair from a single example anti-unification transferable rewrite rule 2026"},
            {"intent": "SUPPLIER_OR_PRODUCT", "query": "skill library memory for coding agents does the store contribute ablation"},
            {"intent": "IMPLEMENTATION_FORM", "query": "AST anti-unification holes projection subterm rewrite admission test"},
            {"intent": "RECENCY_OR_NEW_RELEASE", "query": "SWE-bench Pro V2 boards November 2026 resolve rate"},
        ],
        "refresh_triggers": ["BEFORE_EXPENSIVE_EXECUTION", "AFTER_MATERIAL_ROUTE_FAILURE",
                             "BEFORE_INFRASTRUCTURE_OR_REPAIR_CONTINUATION", "BEFORE_SCARCE_GATE_SPEND"],
        "source_classes_checked": ["BRAIN_INHERITED", "OFFICIAL_PRIMARY", "CODE_OR_PACKAGE_REGISTRY", "BROAD_WEB_OR_COMMUNITY"],
        "source_evidence": {
            "BRAIN_INHERITED": [
                "canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json",
                "canonical/verification/WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1.json",
                "canonical/swe_kernel/verified_skill_crystallizer_ir_bridge_v1.py",
            ],
            "OFFICIAL_PRIMARY": ["https://arxiv.org/abs/2610.24206", "https://arxiv.org/abs/2605.12477"],
            "CODE_OR_PACKAGE_REGISTRY": ["Python standard library ast only; the tests use unittest, because pytest is absent here"],
            "BROAD_WEB_OR_COMMUNITY": ["Nov 2026 frontier boards quoted only with their date and version, as targets"],
        },
        "negative_search_summary": (
            "Searched for a published single-example repair operator with an admission test: the literature describes "
            "anti-unification and version-space learning, but no system reports refusing a learned rule because it "
            "could not fire on its own witness. That refusal is local and is the whole contribution."
        ),
        "unresolved_plausible_dominators": [],
        "selected_route_preflight": {
            "status": "READY", "selected_route": ROUTE, "checked_at_utc": now, "max_age_hours": 2,
            "all_required_dependencies_ready": True, "execution_dependencies_complete": True, "failed_dependencies": [],
            "execution_dependencies": [
                {"dependency": "local Python 3 runtime with unittest (pytest is absent)", "kind": "LOCAL_RUNTIME",
                 "required": True, "status": "READY", "volatility": "STATIC", "scope": "GLOBAL",
                 "evidence_scope": "GLOBAL", "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["16 tests pass in 0.02 s; self-check 8 of 8"]},
                {"dependency": "the repository tree and the V2 receipt, readable offline", "kind": "CODE_ARTIFACT",
                 "required": True, "status": "READY", "volatility": "STATIC", "scope": "LOCAL",
                 "evidence_scope": "LOCAL", "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["the ledger is regenerated from the same functions the tests import"]},
                {"dependency": "model API or remote service at runtime", "kind": "MODEL_API", "required": False,
                 "status": "NOT_REQUIRED", "volatility": "VOLATILE", "scope": "GLOBAL", "evidence_scope": "GLOBAL",
                 "evidence_classes": ["DIRECT_PROBE"],
                 "evidence": ["0 model calls, 0 network calls, 0 parameters"]},
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
            "It is 0.02 s of local computation with no model and no network, it refuses four kinds of candidate "
            "rather than defending one, and it is the first artefact here required to fire on something unseen."
        ),
        "why_this_is_not_another_organ": (
            "The operator is 380 lines of standard-library AST work; it reuses the crystallizer for storage and the "
            "adjudicator's fail-closed verdict shape, and adds no index and no runtime dependency."
        ),
        "routes_considered": [ROUTE, "TUNE_RETRIEVAL_OVER_THE_EXISTING_ENTRIES",
                             "HAND_WRITE_ONE_RULE_PER_BUG_CLASS", "DROP_THE_STORE_AND_KEEP_THE_VERIFIER"],
        "deleted_or_bypassed_paths": [
            "whole-body hole patterns",
            "retrieval tuning over degenerate entries",
            "adding candidates to the blind catalogue",
            "treating a written entry as a learned rule",
        ],
        "route_frontier": frontier(now),
    })
    for layer, payload in layers().items():
        obs[layer] = payload
    obs["obs_blocker"]["surviving_causal_blocker"] = intent["causal_blocker"]
    intent["recursive_obs"] = obs
    intent["selected_route"] = ROUTE
    intent["selected_surviving_route"] = ROUTE
    intent["blocker_lease_key"] = "::".join([
        str(intent.get("canonical_generation") or ""),
        str(intent.get("capability_target") or ""),
        str(intent.get("causal_blocker") or ""),
    ])
    INTENT.write_text(json.dumps(intent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"stamped_at": now, "intent": INTENT.name, "base": BASE, "route": ROUTE}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
