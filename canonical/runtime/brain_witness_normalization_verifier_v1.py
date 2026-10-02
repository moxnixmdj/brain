"""Fail-closed verifier for OPUS55 Brain witness normalization v1.

Recomputes the normalized catalog only from content-addressed PROVED claims in
OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2. It grants no semantic,
acceptance, family, or ownership credit.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def normalize_claim(x: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "witness_id": f"WITNESS::{x.get('predicate_id')}",
        "source_predicate_id": x.get("predicate_id"),
        "proof_kind": x.get("proof_kind"),
        "source_path": x.get("source_path"),
        "source_sha": x.get("source_sha"),
        "independent_or_objective": x.get("independent_or_objective") is True,
        "scope_complete": x.get("scope_complete") is True,
        "objective_ceiling": x.get("objective_ceiling") is True,
        "brain_value": x.get("brain_value"),
        "objective_ceiling_value": x.get("objective_ceiling_value"),
        "basis": x.get("basis"),
        "supporting_sources": x.get("supporting_sources") if isinstance(x.get("supporting_sources"), list) else [],
        "normalized_target_atoms": [],
        "semantic_implications": [],
    }

def evaluate(source: Mapping[str, Any], normalized: Mapping[str, Any], source_blob_sha: str) -> dict[str, Any]:
    errors: list[str] = []
    if normalized.get("schema") != "PROJECT_BRAIN_OPUS55_BRAIN_WITNESS_NORMALIZATION_V1":
        errors.append("NORMALIZATION_SCHEMA_MISMATCH")
    auth = normalized.get("authority")
    if not isinstance(auth, Mapping):
        errors.append("AUTHORITY_MISSING")
    else:
        ev = auth.get("evidence_bindings")
        if not isinstance(ev, Mapping) or ev.get("git_blob_sha") != source_blob_sha:
            errors.append("SOURCE_BLOB_AUTHORITY_MISMATCH")

    claims = source.get("claims")
    if not isinstance(claims, list):
        return {"status":"FAIL_CLOSED","pass":False,"errors":["SOURCE_CLAIMS_INVALID"]}

    expected = [normalize_claim(x) for x in claims if isinstance(x, Mapping) and x.get("state") == "PROVED"]
    actual = normalized.get("witnesses")
    if actual != expected:
        errors.append("NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION")
    if normalized.get("witness_count") != len(expected):
        errors.append("WITNESS_COUNT_MISMATCH")

    for i, row in enumerate(actual if isinstance(actual, list) else []):
        if not isinstance(row, Mapping):
            errors.append(f"WITNESS_{i}_INVALID")
            continue
        if row.get("normalized_target_atoms") != []:
            errors.append(f"WITNESS_{i}_TARGET_ATOM_CREDIT_FORBIDDEN")
        if row.get("semantic_implications") != []:
            errors.append(f"WITNESS_{i}_SEMANTIC_IMPLICATION_CREDIT_FORBIDDEN")
        if row.get("independent_or_objective") is not True or row.get("scope_complete") is not True:
            errors.append(f"WITNESS_{i}_SOURCE_PROOF_NOT_ADMISSIBLE")

    return {
        "schema":"PROJECT_BRAIN_OPUS55_BRAIN_WITNESS_NORMALIZATION_VERDICT_V1",
        "status":"PASS__EXACT_CONTENT_ADDRESSED_WITNESS_NORMALIZATION__ZERO_SEMANTIC_CREDIT" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "witness_count":len(expected),
        "semantic_implication_verified":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "new_reality_units_consumed":0,
    }

def main() -> int:
    source=json.loads(SOURCE.read_text())
    normalized=json.loads(NORMALIZED.read_text())
    out=evaluate(source, normalized, git_blob_sha(SOURCE))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
