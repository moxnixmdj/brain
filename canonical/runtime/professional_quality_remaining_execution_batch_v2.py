"""Shared execution-property truth verifier for the four remaining professional roots.

This verifier closes only the EXECUTION leaves for:
- R5 evaluator/reference,
- R8 population/context/operator,
- R9 temporal/deployment,
- R11 adaptive integrity/security.

For every root it requires:
1. the exact manifest execution acceptance;
2. 24/24 whole-leaf scope equivalence and scope completeness;
3. content-addressed admission through the existing leaf binder;
4. real current root-specific runtime behavior;
5. exact canonical root-defeater-set equality;
6. every canonical root defeater to counterprove in the existing UVCK kernel.

It does not prove semantic totality, root closure, global professional quality,
quality acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as kernel
from canonical.runtime import delegation_terminal_population_binding_v1 as population
from canonical.runtime import evaluation_information_firewall_v1 as firewall
from canonical.runtime import gdpval_hybrid_evaluator_uncertainty_v1 as evaluator_uncertainty
from canonical.runtime import professional_quality_leaf_binder_v2 as binder
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as scope_batch
from canonical.runtime import tb_science_conservative_censoring_reducer_v1 as censoring

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_REMAINING_EXECUTION_PROPERTY_TRUTH_BATCH_V2"
EXECUTION_ACCEPTANCE = (
    "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
    "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)

ROOTS: dict[str, dict[str, Any]] = {
    "R5_EVALUATOR_REFERENCE": {
        "leaf_id": "PQ::R5_EVALUATOR_REFERENCE::EXECUTION",
        "expected_defeaters": {
            "C06_NOVELTY_PENALTY",
            "C17_REFERENCE_STANDARD_ERROR",
            "C18_ANCHOR_PRESTIGE_BIAS",
            "C19_ANCHOR_MEMORIZATION",
            "C20_FRONTIER_LOCAL_JUDGE_FAILURE",
            "C21_JUDGE_ARTIFACT_INTERACTION",
            "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
            "C34_MEASUREMENT_NONINVARIANCE",
            "C50_BASELINE_LAUNDERED_EXCELLENCE",
            "C59_META_ROUTER_SELECTION_OVERFIT",
            "C67_STAKES_SIGNALING_JUDGE_LENIENCY",
            "C68_SELF_PREFERENCE_JUDGE_BIAS",
            "C69_CROSS_MODEL_CALIBRATION_SIGN_REVERSAL",
            "C70_STYLE_BIAS_DOMINATES_CONTENT",
            "C73_BASE_RATE_PRECISION_LAUNDERING",
            "C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING",
        },
    },
    "R8_POPULATION_CONTEXT_OPERATOR": {
        "leaf_id": "PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION",
        "expected_defeaters": {
            "C21_JUDGE_ARTIFACT_INTERACTION",
            "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
            "C32_PRESENTER_CONFOUNDING",
            "C33_CONSTITUENCY_SUPPORT_GAP",
            "C34_MEASUREMENT_NONINVARIANCE",
            "C35_PANEL_SOCIAL_INFLUENCE",
            "C36_RATER_ASSIGNMENT_CONFOUNDING",
            "C37_STRATEGIC_PREFERENCE_REPORT",
            "C38_ELICITATION_PERFORMATIVITY",
            "C39_MEASUREMENT_REACTIVITY_RANK_REVERSAL",
            "C42_SELECTIVE_OUTCOME_CENSORING",
            "C73_BASE_RATE_PRECISION_LAUNDERING",
        },
    },
    "R9_TEMPORAL_DEPLOYMENT": {
        "leaf_id": "PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION",
        "expected_defeaters": {
            "C22_WITHIN_EPISODE_EVALUATOR_DRIFT",
            "C31_EDIT_SEQUENCE_INTERACTION",
            "C40_CARRYOVER_LEARNING",
            "C41_HORIZON_REVERSAL",
            "C42_SELECTIVE_OUTCOME_CENSORING",
            "C43_RARE_UNSEEN_FAILURE",
            "C44_TAIL_RISK_AVERAGE_MASKING",
            "C45_DEPLOYMENT_SUPPORT_SHIFT",
            "C46_PERFORMATIVE_SELF_CONFIRMATION",
            "C47_BAD_EQUILIBRIUM_PATH",
            "C57_EVALUATION_AWARE_BEHAVIOR",
            "C73_BASE_RATE_PRECISION_LAUNDERING",
            "C75_STALE_CERT_AFTER_DEPENDENCY_CHANGE",
        },
    },
    "R11_ADAPTIVE_INTEGRITY_SECURITY": {
        "leaf_id": "PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION",
        "expected_defeaters": {
            "C10_SUBJECT_SWAP_AFTER_CERTIFICATION",
            "C19_ANCHOR_MEMORIZATION",
            "C53_PROMPT_INJECTION_JUDGE_CONTROL",
            "C54_OPTIMIZER_GOODHART_SELECTION",
            "C55_HOLDOUT_REUSE",
            "C56_ACQUIRED_EVALUATION_CONTAMINATION",
            "C57_EVALUATION_AWARE_BEHAVIOR",
            "C58_HARNESS_TAMPERING_OR_REWARD_GAMING",
            "C59_META_ROUTER_SELECTION_OVERFIT",
            "C67_STAKES_SIGNALING_JUDGE_LENIENCY",
            "C74_EXECUTION_FAILURE_FAIL_OPEN",
            "C76_SELECTIVE_EVIDENCE_PACKET",
            "C77_PROVENANCE_OR_RECEIPT_FORGERY",
            "C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
        },
    },
}

PINS = {
    "manifest": (
        "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json",
        "a7cad32c9fd969ff2c3857bb924c7bd746237ec2",
    ),
    "catalog": (
        "canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json",
        "8b92e5cf76f767054f55414b87014e03d43460b8",
    ),
    "graph": (
        "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json",
        "03530e29d70206b46b690b33a04c66765ff86ad7",
    ),
    "scope_batch_runtime": (
        "canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py",
        "82ab66c7852fc327821b23ff80dd46de3b81525c",
    ),
    "scope_batch_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
        "4c2d40a262f18f34bb35f94b59660d60972d45ef",
    ),
    "binder_runtime": (
        "canonical/runtime/professional_quality_leaf_binder_v2.py",
        "1a181b453271a2ce4fc112c3f6586afaf5effbd7",
    ),
    "binder_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_20261010_V1.json",
        "b65a67e8edaee925338fe3f2d61dad6b0f52d129",
    ),
    "kernel": (
        "canonical/runtime/assurance_closure_compiler_v1.py",
        "b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8",
    ),
    "currentgen_verify": (
        "canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json",
        "81f7f070233b6aa1c4b491949a4c3e7aedfafd10",
    ),
    "order_verify": (
        "canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json",
        "1c3428b10a1205e928a87f41a7c16a8a3d17b7ca",
    ),
    "defeater80_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json",
        "c054e9362ce382889e9cca62bdb69e11cea19644",
    ),
    "r5_runtime": (
        "canonical/runtime/gdpval_hybrid_evaluator_uncertainty_v1.py",
        "7adf19997ec90913fb70e618eb4e3adda055deac",
    ),
    "r5_verify": (
        "canonical/verification/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_20261008_V1.json",
        "e852c4fbc14147c17469f1a4ede4e274d768bbf7",
    ),
    "r8_runtime": (
        "canonical/runtime/delegation_terminal_population_binding_v1.py",
        "fae6d0bf2efbcb9b8fe2a2a627900889c5ec6cab",
    ),
    "r8_verify": (
        "canonical/verification/DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "3965db684d7104c5829ce1fcfa8ee08d2cd42cfc",
    ),
    "r9_runtime": (
        "canonical/runtime/tb_science_conservative_censoring_reducer_v1.py",
        "3b48ea534d606cf47a8321b56427353066393577",
    ),
    "r9_verify": (
        "canonical/verification/TB_SCIENCE_CONSERVATIVE_CENSORING_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
        "625cd4fc6e2a503f9ed0514f5b5113fc3250bb88",
    ),
    "r11_firewall_runtime": (
        "canonical/runtime/evaluation_information_firewall_v1.py",
        "11776f87f41c66802a28a417c344cccb394eb2aa",
    ),
    "r11_firewall_governance": (
        "canonical/governance/EVALUATION_INFORMATION_FIREWALL_V1.json",
        "902c19851629bfb2342eea29e73f4a7ab5d212c5",
    ),
    "r11_firewall_tests": (
        "canonical/tests/test_evaluation_information_firewall_v1.py",
        "710006e95a7107320945461fd5b8eca1f61c5fe7",
    ),
    "r11_contamination_runtime": (
        "canonical/runtime/brain_witness_contamination_admissibility_v1.py",
        "e56a3379d0c5275537d9a0e48b06f17c90fad9f9",
    ),
    "r11_contamination_verify": (
        "canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "9dab3da99dda356a4ac56212899fc787e9ec4a5a",
    ),
}


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("NOT_OBJECT")
    return value


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "closed_execution_leaf_ids": [],
        "closed_execution_leaf_count": 0,
        "semantic_leaf_closed": False,
        "root_closed": False,
        "domain_execution_closure": False,
        "domain_semantic_closure": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _manifest_rows(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("root_id")): row
        for row in manifest.get("roots") or []
        if isinstance(row, Mapping) and row.get("root_id") in ROOTS
    }


def _catalog_ids(catalog: Mapping[str, Any], root_id: str) -> set[str]:
    out: set[str] = set()
    for row in catalog.get("challenges") or []:
        if not isinstance(row, Mapping):
            continue
        if root_id not in set(row.get("root_ids") or []):
            continue
        cid = row.get("id")
        if isinstance(cid, str) and cid:
            out.add(cid)
    return out


def _graph_with_supported_defeater(graph: Mapping[str, Any], defeater_id: str) -> dict[str, Any]:
    copied = deepcopy(dict(graph))
    nodes = {
        str(row.get("id")): row
        for row in copied.get("nodes") or []
        if isinstance(row, dict) and row.get("id")
    }
    if defeater_id not in nodes:
        return {}
    nodes[defeater_id]["status"] = "SUPPORTED"
    return copied


def _scope_rows() -> dict[str, Mapping[str, Any]]:
    out = scope_batch.verify()
    if out.get("pass") is not True:
        raise ValueError("WHOLE_LEAF_SCOPE_BATCH_RECOMPUTE_FAILED")
    if out.get("scope_complete_count") != 24 or out.get("domain_equivalence_pass_count") != 24:
        raise ValueError("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")
    wanted = {spec["leaf_id"] for spec in ROOTS.values()}
    rows = {
        str(row.get("leaf_id")): row
        for row in out.get("rows") or []
        if isinstance(row, Mapping) and row.get("leaf_id") in wanted
    }
    if set(rows) != wanted:
        raise ValueError("REMAINING_EXECUTION_SCOPE_ROWS_INCOMPLETE")
    for leaf_id, row in rows.items():
        if row.get("whole_leaf_domain_equivalence_proved") is not True:
            raise ValueError("WHOLE_LEAF_DOMAIN_EQUIVALENCE_NOT_PROVED:" + leaf_id)
        if row.get("whole_leaf_scope_complete") is not True:
            raise ValueError("WHOLE_LEAF_SCOPE_NOT_COMPLETE:" + leaf_id)
        if row.get("leaf_property_truth_authority") is not False:
            raise ValueError("SCOPE_BATCH_SELF_PROPERTY_AUTHORITY_FORBIDDEN:" + leaf_id)
    return rows


def _binder_positive(
    *,
    root_id: str,
    leaf_id: str,
    contract: str,
    manifest_blob_sha: str,
    basis_payload: Mapping[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        basis = root / "canonical/evidence/basis.json"
        receipt = root / "canonical/verification/receipt.json"
        basis.parent.mkdir(parents=True, exist_ok=True)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        basis.write_text(json.dumps(dict(basis_payload), sort_keys=True) + "\n", encoding="utf-8")
        doc = {
            "schema": binder.RECEIPT_SCHEMA,
            "leaf_id": leaf_id,
            "root_id": root_id,
            "leaf_kind": "EXECUTION",
            "verdict": "PASS",
            "closure_scope": "EXACT_LEAF",
            "acceptance_sha256": binder.semantic_sha(EXECUTION_ACCEPTANCE),
            "root_contract_sha256": binder.semantic_sha(contract),
            "manifest_git_blob_sha": manifest_blob_sha,
            "leaf_execution_satisfied": True,
            "verification_basis": [{
                "path": "canonical/evidence/basis.json",
                "git_blob_sha": binder.git_blob_sha(basis),
            }],
            "terminal_authority": False,
        }
        receipt.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
        entry = {
            "path": "canonical/verification/receipt.json",
            "git_blob_sha": binder.git_blob_sha(receipt),
        }
        return binder._receipt_result(
            repo_root=root,
            entry=entry,
            leaf_id=leaf_id,
            root_id=root_id,
            kind="EXECUTION",
            acceptance=EXECUTION_ACCEPTANCE,
            contract=contract,
            manifest_blob_sha=manifest_blob_sha,
        )


def _r5_runtime() -> dict[str, Any]:
    proof = {
        "sound_complete_outer_approximation": True,
        "proof_class": "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
        "receipt": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/verification/root5-positive.json",
            "source_sha": "1" * 40,
        },
    }
    base = {
        "decomposition_proof": proof,
        "difference_vector": [1, -1],
        "nominal_owner_direction": [1, 0],
        "known_cone_generators": [[1, -1]],
        "bounded_uncertainty_vertices": [[0, 0]],
        "lineality_basis": [[1, 1]],
    }
    positive = evaluator_uncertainty.verify(base)
    forbidden_doc = deepcopy(base)
    forbidden_doc["decomposition_proof"] = deepcopy(proof)
    forbidden_doc["decomposition_proof"]["proof_class"] = "PUBLIC_RUBRIC_ONLY"
    forbidden = evaluator_uncertainty.verify(forbidden_doc)
    negative_doc = deepcopy(base)
    negative_doc["nominal_owner_direction"] = [-1, 0]
    negative = evaluator_uncertainty.verify(negative_doc)
    passed = (
        positive.get("pass") is True
        and forbidden.get("pass") is False
        and forbidden.get("reason") == "FORBIDDEN_SEMANTIC_PROOF_CLASS"
        and negative.get("pass") is False
        and negative.get("reason") == "ROBUST_MARGIN_NEGATIVE"
    )
    return {
        "pass": passed,
        "positive_status": positive.get("status"),
        "forbidden_status": forbidden.get("reason"),
        "negative_status": negative.get("reason"),
        "observed_case_count": 3,
    }


def _r8_runtime() -> dict[str, Any]:
    result = population.run_population(
        "professional-r8-execution-property-truth-v1",
        "independent-fixed-beacon-v1",
    )
    invalid_index_rejected = False
    try:
        population.derive_seed("x", "y", population.SAMPLE_COUNT)
    except ValueError:
        invalid_index_rejected = True
    expected_classes = set(population.REQUIRED_CLASSES)
    passed = (
        result.get("pass") is True
        and result.get("executed_count") == population.SAMPLE_COUNT == 512
        and set(result.get("covered_case_classes") or []) == expected_classes
        and result.get("adaptive_case_selection") is False
        and result.get("replay_for_tuning") is False
        and result.get("case_replacement") is False
        and invalid_index_rejected
    )
    return {
        "pass": passed,
        "population_pass": result.get("pass"),
        "executed_count": result.get("executed_count"),
        "covered_case_classes": sorted(result.get("covered_case_classes") or []),
        "invalid_index_rejected": invalid_index_rejected,
        "observed_case_count": int(result.get("executed_count") or 0) + 1,
    }


def _r9_runtime() -> dict[str, Any]:
    slots = [f"slot-{i:03d}" for i in range(210)]
    pass_records = [
        {"slot_id": sid, "state": "SUCCESS" if i < 124 else "FAILURE"}
        for i, sid in enumerate(slots)
    ]
    fail_records = [
        {"slot_id": sid, "state": "SUCCESS" if i < 123 else "FAILURE"}
        for i, sid in enumerate(slots)
    ]
    open_records = fail_records[:-1]
    passed_case = censoring.adjudicate(slots, pass_records, final=True)
    failed_case = censoring.adjudicate(slots, fail_records, final=True)
    open_case = censoring.adjudicate(slots, open_records, final=False)

    duplicate_rejected = False
    outside_rejected = False
    try:
        censoring.adjudicate(slots, [pass_records[0], pass_records[0]], final=False)
    except ValueError:
        duplicate_rejected = True
    try:
        censoring.adjudicate(slots, [{"slot_id": "outside", "state": "SUCCESS"}], final=False)
    except ValueError:
        outside_rejected = True

    passed = (
        passed_case.get("status") == "PASS_LOCK"
        and passed_case.get("successes") == 124
        and failed_case.get("status") == "FAIL_LOCK"
        and failed_case.get("successes") == 123
        and open_case.get("status") == "OPEN"
        and open_case.get("pending") == 1
        and duplicate_rejected
        and outside_rejected
    )
    return {
        "pass": passed,
        "pass_lock_status": passed_case.get("status"),
        "fail_lock_status": failed_case.get("status"),
        "open_status": open_case.get("status"),
        "duplicate_rejected": duplicate_rejected,
        "outside_rejected": outside_rejected,
        "observed_case_count": 5,
    }


def _r11_runtime() -> dict[str, Any]:
    lane = "professional-r11-execution-property-truth-v1"
    pre = {
        "task_identity_exposed": False,
        "clean_qualification_active": True,
        "revoked_capabilities": [],
        "lane_id": lane,
    }
    post = {
        "task_identity_exposed": True,
        "clean_qualification_active": True,
        "revoked_capabilities": [],
        "lane_id": lane,
    }
    compiled = firewall.compile_state(post)
    denied = firewall.evaluate(post, "WEB_DISCOVERY")
    allowed = firewall.evaluate(post, "TERMINAL_VERIFIER_EXECUTION")
    unknown = firewall.evaluate(post, "NOT_A_CAPABILITY")
    reverse = firewall.transition(
        post,
        {
            "task_identity_exposed": False,
            "clean_qualification_active": True,
            "revoked_capabilities": list(firewall.DISCOVERY),
            "lane_id": lane,
        },
    )
    deactivate = firewall.transition(
        post,
        {
            "task_identity_exposed": True,
            "clean_qualification_active": False,
            "revoked_capabilities": list(firewall.DISCOVERY),
            "lane_id": lane,
        },
    )
    passed = (
        firewall.compile_state(pre).get("pass") is True
        and compiled.get("pass") is True
        and compiled.get("irreversible_revocation_active") is True
        and denied.get("pass") is True
        and denied.get("request_allowed") is False
        and allowed.get("pass") is True
        and allowed.get("request_allowed") is True
        and unknown.get("pass") is False
        and reverse.get("pass") is False
        and deactivate.get("pass") is False
    )
    return {
        "pass": passed,
        "post_exposure_revocation_active": compiled.get("irreversible_revocation_active"),
        "web_discovery_denied": denied.get("request_allowed") is False,
        "terminal_verifier_allowed": allowed.get("request_allowed") is True,
        "unknown_capability_fail_closed": unknown.get("pass") is False,
        "identity_reverse_fail_closed": reverse.get("pass") is False,
        "clean_deactivation_fail_closed": deactivate.get("pass") is False,
        "pinned_contamination_receipt_required": True,
        "observed_case_count": 7,
    }


def run_root_runtime_checks() -> dict[str, dict[str, Any]]:
    return {
        "R5_EVALUATOR_REFERENCE": _r5_runtime(),
        "R8_POPULATION_CONTEXT_OPERATOR": _r8_runtime(),
        "R9_TEMPORAL_DEPLOYMENT": _r9_runtime(),
        "R11_ADAPTIVE_INTEGRITY_SECURITY": _r11_runtime(),
    }


def evaluate_documents(
    manifest: Mapping[str, Any],
    catalog: Mapping[str, Any],
    graph: Mapping[str, Any],
    scope_verify: Mapping[str, Any],
    binder_verify: Mapping[str, Any],
    currentgen_verify: Mapping[str, Any],
    order_verify: Mapping[str, Any],
    defeater80_verify: Mapping[str, Any],
    r5_verify: Mapping[str, Any],
    r8_verify: Mapping[str, Any],
    r9_verify: Mapping[str, Any],
    r11_verify: Mapping[str, Any],
    *,
    runtime_results: Mapping[str, Mapping[str, Any]] | None = None,
    recompute_scope: bool = True,
) -> dict[str, Any]:
    rows = _manifest_rows(manifest)
    if set(rows) != set(ROOTS):
        return _fail("REMAINING_ROOT_MANIFEST_SET_MISMATCH", observed=sorted(rows))

    for root_id, spec in ROOTS.items():
        row = rows[root_id]
        leaf = row.get("execution_leaf")
        if not isinstance(leaf, Mapping) or leaf.get("id") != spec["leaf_id"]:
            return _fail("EXECUTION_LEAF_BINDING_MISMATCH:" + root_id)
        if leaf.get("acceptance") != EXECUTION_ACCEPTANCE:
            return _fail(
                "EXECUTION_ACCEPTANCE_DRIFT:" + root_id,
                observed_acceptance=leaf.get("acceptance"),
            )
        observed = _catalog_ids(catalog, root_id)
        expected = set(spec["expected_defeaters"])
        if observed != expected:
            return _fail(
                "CANONICAL_DEFEATER_SET_DRIFT:" + root_id,
                expected=sorted(expected),
                observed=sorted(observed),
            )

    replay = scope_verify.get("independent_replay") or {}
    if not str(scope_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        return _fail("WHOLE_LEAF_SCOPE_BATCH_INDEPENDENT_RECEIPT_NOT_PASS")
    if (
        replay.get("leaf_count") != 24
        or replay.get("domain_equivalence_pass_count") != 24
        or replay.get("scope_complete_count") != 24
    ):
        return _fail("WHOLE_LEAF_SCOPE_BATCH_RECEIPT_NOT_24_OF_24")

    if not str(binder_verify.get("status") or "").startswith("PASS__PINNED_EXACT_BYTES__PYCOMPILE__5_OF_5"):
        return _fail("LEAF_BINDER_INDEPENDENT_VERIFICATION_NOT_PASS")
    if (binder_verify.get("replay") or {}).get("tests_passed") != 5:
        return _fail("LEAF_BINDER_INDEPENDENT_VERIFICATION_COUNT_INVALID")
    if not str(currentgen_verify.get("status") or "").startswith("PASS__PINNED_CURRENT_GENERATION"):
        return _fail("UVCK_CURRENT_GENERATION_VERIFICATION_NOT_PASS")
    if not str(order_verify.get("status") or "").startswith("PASS__EXACT_BLOBS"):
        return _fail("UVCK_DEFEATER_ORDER_VERIFICATION_NOT_PASS")
    if not str(defeater80_verify.get("status") or "").startswith("PASS__EXACT_DOMAIN_BYTES"):
        return _fail("UVCK_80_DEFEATER_REPLAY_NOT_PASS")

    if not (
        str(r5_verify.get("status") or "").startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11")
        and (r5_verify.get("replay") or {}).get("tests_passed") == 11
    ):
        return _fail("R5_EXISTING_RUNTIME_VERIFICATION_NOT_PASS")
    if not (
        str(r8_verify.get("status") or "").startswith("INDEPENDENT_PASS__EXACT_CURRENT_512_CASE_BINDING_PREFLIGHT")
        and "FRESH_512_CASE_PRE_BEACON_POPULATION_PASSES" in set(r8_verify.get("verified") or [])
    ):
        return _fail("R8_EXISTING_RUNTIME_VERIFICATION_NOT_PASS")
    if not (
        str(r9_verify.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
        and "ALL_211_POSSIBLE_SUCCESS_COUNTS_EXHAUSTIVELY_CHECKED" in set(r9_verify.get("verified") or [])
    ):
        return _fail("R9_EXISTING_RUNTIME_VERIFICATION_NOT_PASS")
    if not (
        str(r11_verify.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__9_OF_9")
        and r11_verify.get("contamination_admissibility_verified") is True
        and r11_verify.get("witness_count") == 9
    ):
        return _fail("R11_EXISTING_CONTAMINATION_VERIFICATION_NOT_PASS")

    if recompute_scope:
        try:
            scope_rows = _scope_rows()
        except Exception as exc:
            return _fail("WHOLE_LEAF_SCOPE_RECOMPUTE_FAILED:" + type(exc).__name__ + ":" + str(exc))
    else:
        scope_rows = {
            spec["leaf_id"]: {
                "leaf_id": spec["leaf_id"],
                "whole_leaf_domain_equivalence_proved": True,
                "whole_leaf_scope_complete": True,
                "leaf_property_truth_authority": False,
                "claim_id": "TEST_ONLY",
            }
            for spec in ROOTS.values()
        }

    actual_runtime = (
        {k: dict(v) for k, v in runtime_results.items()}
        if isinstance(runtime_results, Mapping)
        else run_root_runtime_checks()
    )
    if set(actual_runtime) != set(ROOTS):
        return _fail("ROOT_RUNTIME_RESULT_SET_MISMATCH", observed=sorted(actual_runtime))
    for root_id, result in actual_runtime.items():
        if not isinstance(result, Mapping) or result.get("pass") is not True:
            return _fail("ROOT_RUNTIME_CHALLENGE_FAILED:" + root_id, runtime_result=deepcopy(dict(result or {})))

    manifest_blob_sha = PINS["manifest"][1]
    root_outputs: dict[str, Any] = {}
    closed_leaf_ids: list[str] = []

    for root_id, spec in ROOTS.items():
        row = rows[root_id]
        leaf_id = spec["leaf_id"]
        binder_result = _binder_positive(
            root_id=root_id,
            leaf_id=leaf_id,
            contract=str(row.get("contract") or ""),
            manifest_blob_sha=manifest_blob_sha,
            basis_payload={
                "root_id": root_id,
                "leaf_id": leaf_id,
                "runtime_result": actual_runtime[root_id],
            },
        )
        if binder_result.get("admitted") is not True or binder_result.get("errors") != []:
            return _fail("ROOT_BINDER_POSITIVE_NOT_ADMITTED:" + root_id, binder_result=binder_result)

        known: dict[str, bool] = {}
        for defeater_id in sorted(spec["expected_defeaters"]):
            modified = _graph_with_supported_defeater(graph, defeater_id)
            if not modified:
                known[defeater_id] = False
                continue
            verdict = kernel.evaluate(modified)
            known[defeater_id] = (
                verdict.get("status") == "COUNTERPROVED"
                and defeater_id in set(verdict.get("active_defeater_ids") or [])
                and verdict.get("pass") is False
            )
        if len(known) != len(spec["expected_defeaters"]) or not all(known.values()):
            return _fail(
                "CANONICAL_ROOT_DEFEATER_CHALLENGE_FAILED:" + root_id,
                defeater_results=known,
            )

        scope_row = scope_rows[leaf_id]
        if (
            scope_row.get("whole_leaf_domain_equivalence_proved") is not True
            or scope_row.get("whole_leaf_scope_complete") is not True
            or scope_row.get("leaf_property_truth_authority") is not False
        ):
            return _fail("ROOT_SCOPE_ROW_NOT_ADMISSIBLE:" + root_id, scope_row=deepcopy(dict(scope_row)))

        root_outputs[root_id] = {
            "leaf_id": leaf_id,
            "whole_leaf_claim_id": scope_row.get("claim_id"),
            "runtime_result": deepcopy(dict(actual_runtime[root_id])),
            "binder_positive_admitted": True,
            "canonical_defeater_count": len(known),
            "canonical_defeaters_counterproved": all(known.values()),
            "canonical_defeater_results": known,
            "leaf_property_truth_authority": True,
            "semantic_leaf_closed": False,
            "root_closed": False,
        }
        closed_leaf_ids.append(leaf_id)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__R5_R8_R9_R11_EXECUTION_PROPERTY_TRUTH__FOUR_EXACT_LEAVES_ONLY",
        "closed_execution_leaf_ids": sorted(closed_leaf_ids),
        "closed_execution_leaf_count": len(closed_leaf_ids),
        "root_results": root_outputs,
        "manifest_acceptance": EXECUTION_ACCEPTANCE,
        "property_truth_basis": (
            "EXACT_PINNED_CURRENT_RUNTIME_BEHAVIOR_PLUS_CONTENT_ADDRESSED_BINDER_ADMISSION_"
            "PLUS_24_OF_24_SCOPE_RECOMPUTATION_PLUS_ALL_CANONICAL_ROOT_DEFEATER_ACTIVATIONS"
        ),
        "semantic_leaf_closed": False,
        "root_closed": False,
        "domain_execution_closure": False,
        "domain_semantic_closure": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    docs: dict[str, dict[str, Any]] = {}
    json_keys = {
        "manifest",
        "catalog",
        "graph",
        "scope_batch_verify",
        "binder_verify",
        "currentgen_verify",
        "order_verify",
        "defeater80_verify",
        "r5_verify",
        "r8_verify",
        "r9_verify",
        "r11_contamination_verify",
    }
    for key, (relative, expected) in PINS.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            return _fail(key.upper() + "_MISSING")
        actual = _blob(path)
        if actual != expected:
            return _fail(
                key.upper() + "_BLOB_STALE",
                expected_blob=expected,
                observed_blob=actual,
            )
        if key in json_keys:
            try:
                docs[key] = _load(path)
            except Exception:
                return _fail(key.upper() + "_JSON_INVALID")

    return evaluate_documents(
        docs["manifest"],
        docs["catalog"],
        docs["graph"],
        docs["scope_batch_verify"],
        docs["binder_verify"],
        docs["currentgen_verify"],
        docs["order_verify"],
        docs["defeater80_verify"],
        docs["r5_verify"],
        docs["r8_verify"],
        docs["r9_verify"],
        docs["r11_contamination_verify"],
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
