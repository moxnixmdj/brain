from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_FINANCE_DIRECT_ROUTE_SOURCE_COVERAGE_AUDIT_V1"

PATHS = {
    "judgment": "canonical/runtime/judgment_control_envelope_v1.py",
    "semantic_ir": "canonical/runtime/source_traceable_semantic_ir.py",
    "protocol": "canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json",
    "substrate_receipt": "canonical/verification/DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json",
}
EXPECTED = {
    PATHS["judgment"]: "5ebfd1e7fa871da89ecca40ffeb8dd6575c21582",
    PATHS["semantic_ir"]: "cf40b0b4d8f71f15f0140f009b602ff913db6750",
    PATHS["protocol"]: "84973ca473cbb8f6160b45c025567c56f8a3d4ba",
    PATHS["substrate_receipt"]: "047b464ff60d4eaf04c31937b1103c8bf8d678fc",
    PATHS["authority"]: "09f11461c7aa1ee7719409723726712f68d03da8",
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _defs(tree: ast.AST):
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _is_mode_finance(node: ast.If) -> bool:
    t = node.test
    return (
        isinstance(t, ast.Compare)
        and isinstance(t.left, ast.Name)
        and t.left.id == "mode"
        and len(t.ops) == 1
        and isinstance(t.ops[0], ast.Eq)
        and len(t.comparators) == 1
        and isinstance(t.comparators[0], ast.Constant)
        and t.comparators[0].value == "FINANCE"
    )


def _required_id_fields(nodes) -> set[str]:
    fields: set[str] = set()
    for top in nodes:
        for node in ast.walk(top):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "_required_ids":
                continue
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                fields.add(node.args[1].value)
    return fields


def evaluate() -> dict:
    drift = {
        p: {"expected": h, "actual": blob(p)}
        for p, h in EXPECTED.items()
        if blob(p) != h
    }
    if drift:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "pass": False,
            "drift": drift,
        }

    judgment_source = (ROOT / PATHS["judgment"]).read_text(encoding="utf-8")
    semantic_source = (ROOT / PATHS["semantic_ir"]).read_text(encoding="utf-8")
    judgment_tree = ast.parse(judgment_source)
    semantic_tree = ast.parse(semantic_source)

    jdefs = _defs(judgment_tree)
    configured = jdefs["configured_terminal_decision"]
    finance_nodes = []
    for node in ast.walk(configured):
        if isinstance(node, ast.If) and _is_mode_finance(node):
            finance_nodes.extend(node.body)
    finance_required_fields = sorted(_required_id_fields(finance_nodes))

    semantic_defs = _defs(semantic_tree)
    compile_ir = semantic_defs["compile_semantic_ir"]
    compile_args = [a.arg for a in compile_ir.args.args]

    protocol = json.loads((ROOT / PATHS["protocol"]).read_text(encoding="utf-8"))
    substrate = json.loads((ROOT / PATHS["substrate_receipt"]).read_text(encoding="utf-8"))

    finance_acceptance = {
        leaf["id"]: list(leaf["acceptance"])
        for leaf in protocol["leaves"]
    }

    required_protocol_obligations = {
        "ALL_MATERIAL_EXCEPTIONS_AND_ESCALATION_CONDITIONS_PRESERVED",
        "NO_DECISION_RELEVANT_FACT_DROPPED",
        "NO_UNSUPPORTED_DOCUMENT_INTERPRETATION",
    }
    observed_protocol_obligations = {
        item
        for values in finance_acceptance.values()
        for item in values
    }

    declared_only_fields = {
        "rule_evidence_ids",
        "exception_evidence_ids",
        "fact_evidence_ids",
        "cross_reference_evidence_ids",
    }
    source_universe_binding_tokens = {
        "all_material_rule_ids",
        "all_material_exception_ids",
        "escalation_evidence_ids",
        "disclosure_evidence_ids",
        "source_coverage_manifest",
        "document_fact_universe",
        "decision_relevant_fact_universe",
    }
    lower_judgment = judgment_source.lower()
    absent_coverage_tokens = sorted(
        token for token in source_universe_binding_tokens
        if token not in lower_judgment
    )

    semantic_ir_declares_no_raw_inference = (
        "does not infer semantics from raw input" in semantic_source.lower()
        and compile_args == ["contract"]
    )
    substrate_gate_pass = (
        substrate.get("verified", {}).get("general_substrate_test_pass") is True
        and substrate.get("verified", {}).get("source_gate_v2_pass") is True
        and substrate.get("verified", {}).get("clean_direct_case_execution_authority") is True
    )

    mismatch = (
        declared_only_fields.issubset(set(finance_required_fields))
        and required_protocol_obligations.issubset(observed_protocol_obligations)
        and len(absent_coverage_tokens) == len(source_universe_binding_tokens)
        and semantic_ir_declares_no_raw_inference
        and substrate_gate_pass
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNIVERSAL_FINANCE_DIRECT_ROUTE_ADEQUACY_NOT_PROVED__SOURCE_COVERAGE_GAP_LOCALIZED"
            if mismatch else
            "FAIL_CLOSED__EXPECTED_GAP_NOT_ESTABLISHED"
        ),
        "pass": mismatch,
        "finance_required_declared_evidence_fields": finance_required_fields,
        "protocol_load_bearing_completeness_obligations": sorted(required_protocol_obligations),
        "semantic_ir_compile_args": compile_args,
        "semantic_ir_declares_no_raw_semantic_inference": semantic_ir_declares_no_raw_inference,
        "source_coverage_binding_tokens_absent": absent_coverage_tokens,
        "general_substrate_source_gate_already_passed": substrate_gate_pass,
        "two_world_countermodel": {
            "shared_route_observation": "SAME_SOURCE_TEXT_SAME_DECLARED_SEMANTIC_CONTRACT_SAME_DECLARED_EVIDENCE_IDS_SAME_BRAIN_ROUTE_ACCEPT",
            "world_1": "AN_OMITTED_SOURCE_ITEM_IS_NOT_MATERIAL__PROTOCOL_MAY_ACCEPT",
            "world_2": "THE_SAME_OMITTED_SOURCE_ITEM_IS_MATERIAL_OR_DECISION_RELEVANT__PROTOCOL_MUST_REJECT_OR_REQUIRE_IT",
            "route_distinguishes_worlds": False,
            "protocol_truth_differs": True,
        },
        "localized_residual": (
            "PROVE_COMPLETE_LOAD_BEARING_SOURCE_TO_TYPED_SEMANTIC_AND_EVIDENCE_COVERAGE_FOR_THE_SELECTED_FINANCE_CONTEXT"
            "__OR_USE_AN_EQUIVALENT_SCOPE_COMPLETE_END_TO_END_CERTIFICATE"
        ),
        "nonclaims": [
            "NO_CLAIM_THE_JUDGMENT_CONTROL_ENVELOPE_IS_UNSOUND_ON_DECLARED_INPUTS",
            "NO_CLAIM_GENERAL_SUBSTRATE_SOURCE_GATE_FAILED",
            "NO_CLAIM_FINANCE_FAMILY_ACCEPTANCE",
            "NO_TARGET_OR_OPUS_RESULT_ACQUIRED",
        ],
        "incremental_spend_usd": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
