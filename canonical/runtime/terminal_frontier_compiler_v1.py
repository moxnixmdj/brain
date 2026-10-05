"""Live terminal-frontier compiler for Project Brain.

Derives Root1/Root2/Root3 residuals, active meta-envelope obligations, and
active zero-reality scheduling from canonical truth instead of trusting stale
hand-maintained frontier counts. Zero credit: this module compiles truth; it
does not prove acceptance.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

ROOT_STATE_PATH = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
EVIDENCE_PATH = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
REGISTRY_PATH = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"

ROOT1_ACTIVATION_RE = re.compile(
    r"^ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V(\d+)_ACTIVATION_V1\.json$"
)
ZERO_REALITY_ACTIVATION_RE = re.compile(
    r"^CURRENT_ZERO_REALITY_MINIMUM_CUT_V(\d+)_ACTIVATION_V1\.json$"
)


class FrontierCompileError(RuntimeError):
    pass


def _read_bytes(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise FrontierCompileError(f"MISSING_FILE:{path}")
    return p.read_bytes()


def _load(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        value = json.loads(_read_bytes(path, root))
    except json.JSONDecodeError as exc:
        raise FrontierCompileError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise FrontierCompileError(f"NOT_JSON_OBJECT:{path}")
    return value


def git_blob_sha(path: str, root: Path = ROOT) -> str:
    raw = _read_bytes(path, root)
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _discover_highest_active(
    pattern: re.Pattern[str], root: Path = ROOT
) -> tuple[int, str, dict[str, Any]]:
    gov = root / "canonical/governance"
    rows: list[tuple[int, str, dict[str, Any]]] = []
    for p in gov.glob("*.json"):
        m = pattern.match(p.name)
        if not m:
            continue
        rel = p.relative_to(root).as_posix()
        doc = _load(rel, root)
        if doc.get("scheduling_authority") is not True:
            continue
        rows.append((int(m.group(1)), rel, doc))
    if not rows:
        raise FrontierCompileError(f"NO_ACTIVE_ACTIVATION:{pattern.pattern}")
    rows.sort(key=lambda x: (x[0], x[1]))
    selected = rows[-1]
    status = str(selected[2].get("status") or "").upper()
    if not status.startswith("ACTIVE"):
        raise FrontierCompileError(
            f"HIGHEST_SCHEDULING_AUTHORITY_NONACTIVE:{selected[1]}:{status}"
        )
    return selected


def _verification_passes(
    verification_path: str, verification: Mapping[str, Any]
) -> None:
    status = str(verification.get("status") or "").upper()
    if "PASS" not in status and "SUCCESS" not in status:
        raise FrontierCompileError(
            f"ACTIVATION_VERIFICATION_NOT_PASS:{verification_path}:{status}"
        )
    errors = verification.get("errors")
    if isinstance(errors, list) and errors:
        raise FrontierCompileError(
            f"ACTIVATION_VERIFICATION_ERRORS:{verification_path}:{errors}"
        )
    checks = verification.get("checks")
    if isinstance(checks, Mapping):
        check_errors = checks.get("errors")
        if isinstance(check_errors, list) and check_errors:
            raise FrontierCompileError(
                f"ACTIVATION_VERIFICATION_CHECK_ERRORS:{verification_path}:{check_errors}"
            )


def _validate_activation(
    activation_path: str, activation: Mapping[str, Any], root: Path = ROOT
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    subject = activation.get("subject")
    if not isinstance(subject, Mapping):
        raise FrontierCompileError(f"ACTIVATION_SUBJECT_MISSING:{activation_path}")
    subject_path = str(subject.get("path") or "")
    subject_declared = str(subject.get("git_blob_sha") or "")
    if not subject_path or not subject_declared:
        raise FrontierCompileError(f"ACTIVATION_SUBJECT_INCOMPLETE:{activation_path}")
    subject_actual = git_blob_sha(subject_path, root)
    if subject_declared != subject_actual:
        raise FrontierCompileError(
            f"ACTIVATION_SUBJECT_BLOB_MISMATCH:{activation_path}:"
            f"{subject_declared}:{subject_actual}"
        )
    subject_doc = _load(subject_path, root)

    verification_ref = activation.get("verification")
    if not isinstance(verification_ref, Mapping):
        raise FrontierCompileError(
            f"ACTIVATION_VERIFICATION_BINDING_MISSING:{activation_path}"
        )
    verification_path = str(verification_ref.get("path") or "")
    verification_declared = str(verification_ref.get("git_blob_sha") or "")
    if not verification_path or not verification_declared:
        raise FrontierCompileError(
            f"ACTIVATION_VERIFICATION_BINDING_INCOMPLETE:{activation_path}"
        )
    verification_actual = git_blob_sha(verification_path, root)
    if verification_declared != verification_actual:
        raise FrontierCompileError(
            f"ACTIVATION_VERIFICATION_BLOB_MISMATCH:{activation_path}:"
            f"{verification_declared}:{verification_actual}"
        )
    verification_doc = _load(verification_path, root)
    _verification_passes(verification_path, verification_doc)

    verified_subject = verification_doc.get("subject")
    if isinstance(verified_subject, Mapping):
        if str(verified_subject.get("path") or "") != subject_path:
            raise FrontierCompileError(
                f"VERIFICATION_SUBJECT_PATH_MISMATCH:{activation_path}"
            )
        if str(verified_subject.get("git_blob_sha") or "") != subject_declared:
            raise FrontierCompileError(
                f"VERIFICATION_SUBJECT_BLOB_MISMATCH:{activation_path}"
            )

    return subject_path, subject_doc, verification_path, verification_doc


def root_partition(
    part: Mapping[str, Any],
) -> tuple[set[str], set[str], set[str], set[str]]:
    r1_only = set(part.get("root1_only") or [])
    r2_only = set(part.get("root2_only") or [])
    r3_only = set(part.get("root3_only") or [])
    mixed = set(part.get("root2_and_root3") or [])

    buckets = [r1_only, r2_only, r3_only, mixed]
    for i, left in enumerate(buckets):
        for right in buckets[i + 1 :]:
            if left & right:
                raise FrontierCompileError("ROOT_PARTITION_NOT_DISJOINT")

    all_residual = r1_only | r2_only | r3_only | mixed
    if len(all_residual) != int(part.get("unresolved_total", -1)):
        raise FrontierCompileError("ROOT_PARTITION_COUNT_MISMATCH")

    if len(r1_only) != int(part.get("root1_positive_gap_count", -1)):
        raise FrontierCompileError("ROOT1_COUNT_MISMATCH")
    if len(r2_only) != int(part.get("root2_only_count", -1)):
        raise FrontierCompileError("ROOT2_ONLY_COUNT_MISMATCH")
    if len(r3_only) != int(part.get("root3_only_count", -1)):
        raise FrontierCompileError("ROOT3_ONLY_COUNT_MISMATCH")
    if len(mixed) != int(part.get("root2_and_root3_count", -1)):
        raise FrontierCompileError("ROOT2_ROOT3_MIXED_COUNT_MISMATCH")

    root2 = r2_only | mixed
    root3 = r3_only | mixed
    return r1_only, root2, root3, all_residual


def _is_proved_state(state: object) -> bool:
    s = str(state or "").upper()
    return s.startswith("PROVED") or s.startswith("CLOSED__PROVED")


def acceptance_identity(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    partition_residual: set[str],
) -> tuple[set[str], set[str]]:
    predicates = registry.get("predicates")
    if not isinstance(predicates, list):
        raise FrontierCompileError("REGISTRY_PREDICATES_MISSING")

    registry_ids: list[str] = []
    for row in predicates:
        if not isinstance(row, Mapping) or not row.get("id"):
            raise FrontierCompileError("REGISTRY_PREDICATE_INVALID")
        registry_ids.append(str(row["id"]))
    if len(registry_ids) != len(set(registry_ids)):
        raise FrontierCompileError("REGISTRY_PREDICATE_DUPLICATE")
    registry_set = set(registry_ids)

    claims = evidence.get("claims")
    if not isinstance(claims, list):
        raise FrontierCompileError("EVIDENCE_CLAIMS_MISSING")

    seen_claims: set[str] = set()
    proved: set[str] = set()
    for claim in claims:
        if not isinstance(claim, Mapping) or not claim.get("predicate_id"):
            raise FrontierCompileError("EVIDENCE_CLAIM_INVALID")
        pid = str(claim["predicate_id"])
        if pid in seen_claims:
            raise FrontierCompileError(f"EVIDENCE_DUPLICATE_PREDICATE:{pid}")
        seen_claims.add(pid)
        if pid not in registry_set:
            raise FrontierCompileError(f"EVIDENCE_UNKNOWN_PREDICATE:{pid}")
        if _is_proved_state(claim.get("state")):
            proved.add(pid)

    unresolved = registry_set - proved
    if partition_residual != unresolved:
        missing_from_partition = sorted(unresolved - partition_residual)
        extra_in_partition = sorted(partition_residual - unresolved)
        raise FrontierCompileError(
            "ROOT_PARTITION_IDENTITY_DRIFT:"
            f"missing={missing_from_partition}:extra={extra_in_partition}"
        )

    if len(registry_set) != int(acceptance.get("total_atomic", -1)):
        raise FrontierCompileError("REGISTRY_TOTAL_ATOMIC_DRIFT")
    if len(proved) != int(acceptance.get("proved_atomic", -1)):
        raise FrontierCompileError("PROVED_IDENTITY_COUNT_DRIFT")
    if len(unresolved) != int(acceptance.get("unresolved_atomic", -1)):
        raise FrontierCompileError("UNRESOLVED_IDENTITY_COUNT_DRIFT")

    return proved, unresolved


def _is_open_state(state: object) -> bool:
    s = str(state or "").upper()
    return not (
        s.startswith("CLOSED")
        or s.startswith("PROVED")
        or s.startswith("PASS")
        or s.startswith("RESOLVED")
        or "CLOSED__" in s
    )


def meta_envelope_obligations(meta: Mapping[str, Any]) -> dict[str, Any]:
    mappings: list[str] = []
    for value in meta.get("family_mapping_frontier") or []:
        if isinstance(value, Mapping):
            if _is_open_state(value.get("state")):
                mappings.append(
                    str(value.get("family") or value.get("surface") or "UNNAMED_MAPPING")
                )
        else:
            mappings.append(str(value))

    conditions = [
        str(x.get("condition"))
        for x in (meta.get("cross_cutting_condition_frontier") or [])
        if isinstance(x, Mapping) and _is_open_state(x.get("state"))
    ]

    repair = meta.get("proof_basis_repair")
    repairs: list[str] = []
    if isinstance(repair, Mapping) and _is_open_state(repair.get("state")):
        repairs.append(str(repair.get("surface") or "UNNAMED_PROOF_BASIS_REPAIR"))

    return {
        "family_mappings": mappings,
        "cross_cutting_conditions": conditions,
        "proof_basis_repairs": repairs,
        "open_count": len(mappings) + len(conditions) + len(repairs),
    }


def terminal_finality(
    acceptance: Mapping[str, Any],
    *,
    root1_positive_gap_count: int,
    meta_open_count: int,
) -> bool:
    return (
        int(acceptance.get("accepted_families", -1))
        == int(acceptance.get("total_families", -2))
        and int(acceptance.get("proved_atomic", -1))
        == int(acceptance.get("total_atomic", -2))
        and int(acceptance.get("unresolved_atomic", -1)) == 0
        and root1_positive_gap_count == 0
        and meta_open_count == 0
    )


def frontier_epoch(component_blobs: Mapping[str, str]) -> str:
    if not component_blobs:
        raise FrontierCompileError("EMPTY_FRONTIER_EPOCH")
    lines = []
    for path, sha in sorted(component_blobs.items()):
        if not re.fullmatch(r"[0-9a-f]{40}", str(sha)):
            raise FrontierCompileError(f"INVALID_COMPONENT_SHA:{path}:{sha}")
        lines.append(f"{path}={sha}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def compile_frontier(root: Path = ROOT) -> dict[str, Any]:
    root_state = _load(ROOT_STATE_PATH, root)
    evidence = _load(EVIDENCE_PATH, root)
    registry = _load(REGISTRY_PATH, root)

    acceptance = root_state.get("current_acceptance")
    part = root_state.get("current_residual_root_partition")
    if not isinstance(acceptance, Mapping) or not isinstance(part, Mapping):
        raise FrontierCompileError("CURRENT_ROOT_STATE_INCOMPLETE")

    unresolved_count = int(acceptance.get("unresolved_atomic", -1))
    if unresolved_count != int(part.get("unresolved_total", -2)):
        raise FrontierCompileError("ACCEPTANCE_ROOT_PARTITION_DRIFT")

    root1_only, root2, root3, partition_residual = root_partition(part)
    proved_ids, unresolved_ids = acceptance_identity(
        registry, evidence, acceptance, partition_residual
    )

    saturation = evidence.get("saturation")
    if not isinstance(saturation, Mapping):
        raise FrontierCompileError("EVIDENCE_SATURATION_MISSING")
    if int(saturation.get("proved_predicate_count", -1)) != len(proved_ids):
        raise FrontierCompileError("EVIDENCE_PROVED_COUNT_DRIFT")
    if int(saturation.get("unresolved_predicate_count", -1)) != len(unresolved_ids):
        raise FrontierCompileError("EVIDENCE_UNRESOLVED_COUNT_DRIFT")

    r1ver, r1act_path, r1act = _discover_highest_active(ROOT1_ACTIVATION_RE, root)
    (
        r1subject_path,
        r1meta,
        r1verification_path,
        _,
    ) = _validate_activation(r1act_path, r1act, root)
    meta = meta_envelope_obligations(r1meta)

    zver, zact_path, zact = _discover_highest_active(
        ZERO_REALITY_ACTIVATION_RE, root
    )
    (
        zsubject_path,
        zcut,
        zverification_path,
        _,
    ) = _validate_activation(zact_path, zact, root)

    exact = zcut.get("exact_state")
    if isinstance(exact, Mapping):
        expected_counts = {
            "accepted_families": int(acceptance.get("accepted_families", -999)),
            "open_families": int(acceptance.get("open_families", -999)),
            "proved_atomic": len(proved_ids),
            "unresolved_atomic": len(unresolved_ids),
            "root1_positive_gap_count": len(root1_only),
            "root2_touching_count": len(root2),
            "root3_touching_count": len(root3),
        }
        for key, expected in expected_counts.items():
            if key in exact and int(exact[key]) != expected:
                raise FrontierCompileError(f"ZERO_REALITY_CUT_COUNT_DRIFT:{key}")

    terminal = terminal_finality(
        acceptance,
        root1_positive_gap_count=len(root1_only),
        meta_open_count=int(meta["open_count"]),
    )

    component_paths = [
        ROOT_STATE_PATH,
        EVIDENCE_PATH,
        REGISTRY_PATH,
        r1act_path,
        r1subject_path,
        r1verification_path,
        zact_path,
        zsubject_path,
        zverification_path,
    ]
    blobs = {p: git_blob_sha(p, root) for p in component_paths}

    return {
        "schema": "PROJECT_BRAIN_LIVE_TERMINAL_FRONTIER_V1",
        "status": "TERMINAL_TRUE" if terminal else "TERMINAL_FALSE",
        "acceptance": dict(acceptance),
        "proved_predicates": sorted(proved_ids),
        "unresolved_predicates": sorted(unresolved_ids),
        "root1_positive_predicates": sorted(root1_only),
        "root1_positive_gap_count": len(root1_only),
        "root2_touching": sorted(root2),
        "root2_touching_count": len(root2),
        "root3_touching": sorted(root3),
        "root3_touching_count": len(root3),
        "meta_envelope": {
            "active_version": r1ver,
            "activation_path": r1act_path,
            "subject_path": r1subject_path,
            "verification_path": r1verification_path,
            **meta,
        },
        "zero_reality_cut": {
            "active_version": zver,
            "activation_path": zact_path,
            "subject_path": zsubject_path,
            "verification_path": zverification_path,
        },
        "terminal": terminal,
        "component_blobs": dict(sorted(blobs.items())),
        "frontier_epoch_sha256": frontier_epoch(blobs),
        "accounting": {
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "new_reality_units_consumed": 0,
        },
    }


def main() -> int:
    try:
        print(json.dumps(compile_frontier(), indent=2, sort_keys=True))
        return 0
    except FrontierCompileError as exc:
        print(
            json.dumps(
                {
                    "schema": "PROJECT_BRAIN_LIVE_TERMINAL_FRONTIER_V1",
                    "status": "FAIL_CLOSED__FRONTIER_COMPILE_ERROR",
                    "error": str(exc),
                    "terminal": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
