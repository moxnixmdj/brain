"""Verify source-bound P3 v3 synthesis typed-domain countermodels.

This verifier proves only structural facts about the frozen candidate/suite.
It grants no terminal, acceptance, family, capability, or ownership credit.
"""
from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

SPEC = "canonical/governance/SYNTHESIS_P3_TYPED_INPUT_DOMAIN_COUNTERMODEL_PARTITION_20261005_V1.json"
CAND = "canonical/runtime/p3_information_safe_candidate_v3.py"
SUITE = "canonical/runtime/p3_information_safe_proof_suite_v3.py"

def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _audience_priority(source: str) -> dict:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "AUDIENCE_PRIORITY":
                    return ast.literal_eval(node.value)
    raise AssertionError("AUDIENCE_PRIORITY_NOT_FOUND")

def verify(root: Path) -> dict:
    errors = []
    spec = json.loads((root / SPEC).read_text())
    cand_path = root / CAND
    suite_path = root / SUITE
    cand = cand_path.read_text()
    suite = suite_path.read_text()

    if git_blob(cand_path) != spec["authorities"]["p3_candidate"]["git_blob_sha"]:
        errors.append("CANDIDATE_BLOB_DRIFT")
    if git_blob(suite_path) != spec["authorities"]["p3_suite"]["git_blob_sha"]:
        errors.append("SUITE_BLOB_DRIFT")

    try:
        ap = _audience_priority(cand)
        if set(ap) != {"executive", "engineer", "auditor"}:
            errors.append("AUDIENCE_DOMAIN_CHANGED")
    except Exception:
        errors.append("AUDIENCE_PRIORITY_PARSE")

    required_fragments = [
        'claim["relation"]=="at_least"',
        'claim["relation"]=="at_most"',
        'raise ValueError("RELATION")',
        'float(e["value"])',
        'if not votes: continue',
        'AUDIENCE_PRIORITY.get(audience,())',
        '"selected_claims":selected',
        '"uncertainty_claims":sorted(set(uncertainty)&set(selected))',
    ]
    for fragment in required_fragments:
        if fragment not in cand:
            errors.append("CANDIDATE_FACT_DRIFT:" + fragment)

    if '.get("provenance")' in cand or '["provenance"]' in cand:
        errors.append("PROVENANCE_NOW_CONSUMED")
    if '.get("unit")' in cand or '["unit"]' in cand:
        errors.append("UNIT_NOW_CONSUMED")

    if 'n=2 if r.random()>.25 else 3' not in suite:
        errors.append("SUITE_EVIDENCE_CARDINALITY_CHANGED")
    if 'for c in claims:' not in suite or 'for j in range(n):' not in suite:
        errors.append("SUITE_EVERY_CLAIM_EVIDENCE_GENERATION_CHANGED")

    ids = [x["id"] for x in spec["constructive_uncovered_classes"]]
    expected = [
        "SYNTHESIS_SCOPE_R1_OPEN_AUDIENCE_ADAPTATION",
        "SYNTHESIS_SCOPE_R2_NONNUMERIC_OR_STRUCTURED_EVIDENCE",
        "SYNTHESIS_SCOPE_R3_GENERAL_CLAIM_SEMANTICS",
        "SYNTHESIS_SCOPE_R4_GENERAL_OUTPUT_CONSTRAINTS",
        "SYNTHESIS_SCOPE_R5_INSUFFICIENT_EVIDENCE_FOR_REQUIRED_CLAIM",
        "SYNTHESIS_SCOPE_R6_PROVENANCE_AND_UNIT_SENSITIVE_SUPPORT",
        "SYNTHESIS_SCOPE_R7_REALIZED_SYNTHESIS_EXPRESSION",
    ]
    if ids != expected:
        errors.append("RESIDUAL_ID_SET_DRIFT")

    return {
        "schema": "PROJECT_BRAIN_SYNTHESIS_P3_TYPED_INPUT_DOMAIN_COUNTERMODEL_VERDICT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "universal_current_p3_v3_totality_falsified": not errors,
        "constructive_residual_class_count": 7 if not errors else None,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }
