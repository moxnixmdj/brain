"""Fail-closed application verifier for the synthesis proof-obligation delta."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.proof_obligation_delta_compiler_v1 import compile_delta

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "canonical/governance/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_INPUT_V1.json"
COMPILER = ROOT / "canonical/runtime/proof_obligation_delta_compiler_v1.py"
COMPILER_RECEIPT = ROOT / "canonical/verification/PROOF_OBLIGATION_DELTA_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BINDING_RECEIPT = ROOT / "canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
TARGET_SCOPE_SOURCE = ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
WITNESS_SCOPE_SOURCE = ROOT / "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"

EXPECTED_TARGET = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
EXPECTED_SCOPE = ["population:frozen_matched_synthesis_portfolio"]
EXPECTED_ATOMS = ["metric:matched_quality"]
EXPECTED_METRICS = ["matched_quality_noninferiority", "required_claim_coverage_noninferiority"]


def load(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_VERDICT_V1",
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
    }


def evaluate(
    doc: Mapping[str, Any],
    compiler_receipt: Mapping[str, Any],
    binding_receipt: Mapping[str, Any],
    actual_blobs: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    if doc.get("schema") != "PROJECT_BRAIN_PROOF_OBLIGATION_DELTA_INPUT_V1":
        errors.append("INPUT_SCHEMA_MISMATCH")

    if compiler_receipt.get("status") != (
        "INDEPENDENT_PUBLIC_RUNNER_PASS__HARDENED_CONTENT_ADDRESSED_BINDINGS__"
        "OPAQUE_RECEIPTS_AND_DUPLICATE_TARGET_BINDINGS_REJECTED__ZERO_CREDIT"
    ):
        errors.append("HARDENED_COMPILER_NOT_INDEPENDENT_PASS")
    exact = compiler_receipt.get("exact_brain_blobs", {})
    if not isinstance(exact, Mapping) or exact.get(
        "canonical/runtime/proof_obligation_delta_compiler_v1.py"
    ) != actual_blobs.get("compiler"):
        errors.append("COMPILER_BLOB_NOT_BOUND_TO_INDEPENDENT_RECEIPT")

    if binding_receipt.get("status") != (
        "INDEPENDENT_PUBLIC_RUNNER_PASS__7_SYNTHESIS_TARGET_ATOMS_OPERATIONALLY_BOUND__"
        "MATCHED_METRIC_BOUNDS_OPEN__ZERO_CREDIT"
    ):
        errors.append("SYNTHESIS_BINDING_RECEIPT_NOT_INDEPENDENT_PASS")
    if binding_receipt.get("proved_atom_count") != 7:
        errors.append("SYNTHESIS_BINDING_RECEIPT_ATOM_COUNT_MISMATCH")
    if binding_receipt.get("numeric_metric_bounds_verified") is not False:
        errors.append("SYNTHESIS_BINDING_RECEIPT_NUMERIC_SCOPE_DRIFT")

    target = doc.get("target")
    witness = doc.get("witness")
    if not isinstance(target, Mapping) or not isinstance(witness, Mapping):
        errors.append("TARGET_OR_WITNESS_MISSING")
    else:
        if target.get("id") != EXPECTED_TARGET:
            errors.append("TARGET_ID_MISMATCH")
        ts = target.get("scope_components")
        ws = witness.get("scope_components")
        if not isinstance(ts, list) or len(ts) != 1:
            errors.append("TARGET_SCOPE_COMPONENT_COUNT_MISMATCH")
        else:
            row = ts[0]
            if (
                not isinstance(row, Mapping)
                or row.get("source_path") != "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
                or row.get("source_sha") != actual_blobs.get("target_scope")
            ):
                errors.append("TARGET_SCOPE_PROVENANCE_MISMATCH")
        if not isinstance(ws, list) or len(ws) != 1:
            errors.append("WITNESS_SCOPE_COMPONENT_COUNT_MISMATCH")
        else:
            row = ws[0]
            if (
                not isinstance(row, Mapping)
                or row.get("source_path") != "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
                or row.get("source_sha") != actual_blobs.get("witness_scope")
            ):
                errors.append("WITNESS_SCOPE_PROVENANCE_MISMATCH")

    if doc.get("scope_bindings") != []:
        errors.append("UNVERIFIED_SCOPE_BINDING_FORBIDDEN")
    if doc.get("metric_bindings") != []:
        errors.append("UNVERIFIED_METRIC_BINDING_FORBIDDEN")
    if doc.get("invariant_bindings") != []:
        errors.append("UNVERIFIED_INVARIANT_BINDING_FORBIDDEN")

    atom_bindings = doc.get("atom_bindings")
    if not isinstance(atom_bindings, list) or len(atom_bindings) != 7:
        errors.append("ATOM_BINDING_COUNT_MISMATCH")
    else:
        pairs: set[tuple[str, str]] = set()
        for i, row in enumerate(atom_bindings):
            if not isinstance(row, Mapping):
                errors.append(f"ATOM_BINDING_NOT_OBJECT:{i}")
                continue
            receipt = row.get("receipt")
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("path") != "canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
                or receipt.get("git_blob_sha") != actual_blobs.get("binding_receipt")
            ):
                errors.append(f"ATOM_BINDING_RECEIPT_IDENTITY_MISMATCH:{i}")
            if row.get("verified") is not True or row.get("independent") is not True:
                errors.append(f"ATOM_BINDING_NOT_INDEPENDENTLY_VERIFIED:{i}")
            pair = (str(row.get("witness_atom")), str(row.get("target_atom")))
            if pair in pairs:
                errors.append(f"ATOM_BINDING_DUPLICATE:{i}")
            pairs.add(pair)

    expected = doc.get("expected_residual")
    if not isinstance(expected, Mapping):
        errors.append("EXPECTED_RESIDUAL_MISSING")

    if errors:
        return _fail(*errors)

    delta = compile_delta(doc)
    residual = delta.get("residual")
    if (
        delta.get("status") != "RESIDUAL_DELTA_OPEN"
        or delta.get("pass") is not False
        or delta.get("errors") != []
        or delta.get("scope_relation") is not None
        or not isinstance(residual, Mapping)
    ):
        return _fail("DELTA_COMPILER_DID_NOT_RETURN_EXPECTED_OPEN_FORM")

    canonical_residual = {
        "missing_scope_components": EXPECTED_SCOPE,
        "missing_atoms": EXPECTED_ATOMS,
        "missing_invariants": [],
        "missing_metric_bindings": EXPECTED_METRICS,
        "failing_metric_bounds": [],
    }
    if residual != canonical_residual or dict(expected) != canonical_residual:
        return _fail("EXACT_SYNTHESIS_RESIDUAL_MISMATCH")

    if sorted(delta.get("covered", {}).get("atoms", [])) != sorted(
        x["target_atom"] for x in atom_bindings
    ):
        return _fail("COVERED_ATOM_SET_MISMATCH")

    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_VERDICT_V1",
        "status": (
            "PASS__EXACT_SCOPE_SAFE_SYNTHESIS_DELTA__"
            "ONE_SCOPE_COMPONENT_ONE_ATOM_TWO_METRIC_BINDINGS_OPEN__ZERO_CREDIT"
        ),
        "pass": True,
        "errors": [],
        "target_predicate_id": EXPECTED_TARGET,
        "verified_atom_binding_count": 7,
        "missing_scope_components": EXPECTED_SCOPE,
        "missing_atoms": EXPECTED_ATOMS,
        "missing_metric_bindings": EXPECTED_METRICS,
        "scope_relation": None,
        "acceptance_predicate_closed": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
        "rule": (
            "THIS_PASS_VERIFIES_THE_EXACT_OPEN_RESIDUAL_ONLY__"
            "IT_DOES_NOT_PROVE_SYNTHESIS_ACCEPTANCE_OR_AUTHORIZE_FRESH_REALITY"
        ),
    }


def main() -> int:
    out = evaluate(
        load(INPUT),
        load(COMPILER_RECEIPT),
        load(BINDING_RECEIPT),
        {
            "compiler": blob_sha(COMPILER),
            "binding_receipt": blob_sha(BINDING_RECEIPT),
            "target_scope": blob_sha(TARGET_SCOPE_SOURCE),
            "witness_scope": blob_sha(WITNESS_SCOPE_SOURCE),
        },
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
