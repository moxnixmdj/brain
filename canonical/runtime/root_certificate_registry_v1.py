"""Fail-closed validator for the current R1/R2/R3 root-certificate registry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_COVERAGE_ROOT_CERTIFICATE_REGISTRY_V1"
REGISTRY = "canonical/governance/COVERAGE_ROOT_CERTIFICATE_REGISTRY_20261009_V1.json"
EXPECTED_ROOTS = {
    "R1": ("REALITY_CONTAINMENT", "B_real SUBSETEQ B_plus"),
    "R2": ("MISSION_SOUNDNESS", "G_minus SUBSETEQ G_real"),
    "R3": ("TERMINAL_CLOSURE", "B_plus SUBSETEQ G_minus"),
}
ALLOWED_STATUS = {"PROVED", "FALSIFIED", "UNKNOWN"}


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load(root: Path, relative: str) -> tuple[Mapping[str, Any], str]:
    target = (root / relative).resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("DOCUMENT_NOT_OBJECT:" + relative)
    return doc, _blob(raw)


def validate_repo(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    errors: list[str] = []
    try:
        registry, _ = _load(root, REGISTRY)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["REGISTRY_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc)],
            "proof_closure_ready": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if registry.get("schema") != SCHEMA:
        errors.append("REGISTRY_SCHEMA_INVALID")

    roots = registry.get("roots")
    if not isinstance(roots, Mapping) or set(roots) != set(EXPECTED_ROOTS):
        errors.append("ROOT_SET_NOT_EXACT_R1_R2_R3")
        roots = {}

    for root_id, (expected_id, expected_claim) in EXPECTED_ROOTS.items():
        row = roots.get(root_id)
        if not isinstance(row, Mapping):
            errors.append("ROOT_ROW_MISSING:" + root_id)
            continue
        if row.get("id") != expected_id:
            errors.append("ROOT_ID_MISMATCH:" + root_id)
        if row.get("claim") != expected_claim:
            errors.append("ROOT_CLAIM_MISMATCH:" + root_id)
        status = row.get("status")
        if status not in ALLOWED_STATUS:
            errors.append("ROOT_STATUS_INVALID:" + root_id)
        if status == "UNKNOWN" and row.get("falsified") is not False:
            errors.append("UNKNOWN_ROOT_FALSELY_MARKED_FALSIFIED:" + root_id)

        evidence = row.get("supporting_evidence") or []
        if not isinstance(evidence, list):
            errors.append("SUPPORTING_EVIDENCE_INVALID:" + root_id)
            continue
        for item in evidence:
            if not isinstance(item, Mapping):
                errors.append("EVIDENCE_ROW_INVALID:" + root_id)
                continue
            path = str(item.get("path") or "")
            expected_sha = str(item.get("git_blob_sha") or "")
            try:
                _, observed_sha = _load(root, path)
            except Exception as exc:
                errors.append("EVIDENCE_LOAD_FAILED:" + root_id + ":" + type(exc).__name__)
                continue
            if observed_sha != expected_sha:
                errors.append("EVIDENCE_BLOB_DRIFT:" + root_id + ":" + path)
            if item.get("not_equivalent_to_root_claim") is not True:
                errors.append("EVIDENCE_SCOPE_BOUNDARY_MISSING:" + root_id + ":" + path)

    # Bind mission/theorem/live authority identities.
    for label in ("mission", "root_theorem", "live_binding"):
        binding = registry.get(label)
        if not isinstance(binding, Mapping):
            errors.append("BINDING_MISSING:" + label)
            continue
        path = str(binding.get("path") or "")
        expected_sha = str(binding.get("git_blob_sha") or "")
        try:
            doc, observed_sha = _load(root, path)
        except Exception as exc:
            errors.append("BINDING_LOAD_FAILED:" + label + ":" + type(exc).__name__)
            continue
        if observed_sha != expected_sha:
            errors.append("BINDING_BLOB_DRIFT:" + label)
        if label == "mission" and doc.get("real_objective") != binding.get("real_objective"):
            errors.append("MISSION_OBJECTIVE_MISMATCH")

    # R3's terminal authority evidence is deliberately separate because it is
    # counterevidence to PROVED, not a proof that the set inclusion is false.
    r3 = roots.get("R3") if isinstance(roots, Mapping) else None
    if isinstance(r3, Mapping):
        counter = r3.get("counterevidence_to_proved_status")
        if not isinstance(counter, Mapping):
            errors.append("R3_COUNTEREVIDENCE_BINDING_MISSING")
        else:
            path = str(counter.get("path") or "")
            try:
                terminal, observed_sha = _load(root, path)
            except Exception as exc:
                errors.append("R3_COUNTEREVIDENCE_LOAD_FAILED:" + type(exc).__name__)
            else:
                if observed_sha != counter.get("git_blob_sha"):
                    errors.append("R3_COUNTEREVIDENCE_BLOB_DRIFT")
                live = terminal.get("live_truth") or {}
                if terminal.get("live_truth", {}).get("terminal") is not False and terminal.get("terminal") is not False:
                    errors.append("R3_EXPECTED_TERMINAL_FALSE_NOT_BOUND")
                if live.get("current_U_empty_proved") is not False:
                    errors.append("R3_U_EMPTY_STATE_DRIFT")
                if live.get("independent_open_acceptance_obligations") != 13:
                    errors.append("R3_OPEN_OBLIGATION_COUNT_DRIFT")

    vector = [roots.get(k, {}).get("status") for k in ("R1", "R2", "R3")] if isinstance(roots, Mapping) else []
    if registry.get("root_status_vector") != vector:
        errors.append("ROOT_STATUS_VECTOR_MISMATCH")
    proved_all = vector == ["PROVED", "PROVED", "PROVED"]
    if registry.get("proof_closure_ready") is not proved_all:
        errors.append("PROOF_CLOSURE_READY_MISMATCH")
    if registry.get("registry_complete_for_declared_roots") is not True:
        errors.append("REGISTRY_COMPLETENESS_FLAG_MISSING")

    return {
        "schema": SCHEMA,
        "status": "PASS__ROOT_CERTIFICATE_REGISTRY_BOUND__ROOT_STATUS_PRESERVED" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "root_status_vector": vector,
        "proof_closure_ready": proved_all,
        "registry_complete_for_declared_roots": not errors,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate_repo(Path(__file__).resolve().parents[2]), indent=2, sort_keys=True))
