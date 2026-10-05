"""Live terminal-frontier compiler for Project Brain.

Derives Root2, Root3, Root1 meta-envelope, and active zero-reality scheduling
from canonical truth instead of trusting stale hand-maintained frontier counts.
Zero credit: this module compiles truth; it does not prove acceptance.
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
        if doc.get("scheduling_authority") is True:
            rows.append((int(m.group(1)), rel, doc))
    if not rows:
        raise FrontierCompileError(f"NO_ACTIVE_ACTIVATION:{pattern.pattern}")
    rows.sort(key=lambda x: (x[0], x[1]))
    return rows[-1]


def _validate_subject(
    activation_path: str, activation: Mapping[str, Any], root: Path = ROOT
) -> tuple[str, dict[str, Any]]:
    subject = activation.get("subject")
    if not isinstance(subject, Mapping):
        raise FrontierCompileError(f"ACTIVATION_SUBJECT_MISSING:{activation_path}")
    path = str(subject.get("path") or "")
    declared = str(subject.get("git_blob_sha") or "")
    if not path or not declared:
        raise FrontierCompileError(f"ACTIVATION_SUBJECT_INCOMPLETE:{activation_path}")
    actual = git_blob_sha(path, root)
    if declared != actual:
        raise FrontierCompileError(
            f"ACTIVATION_SUBJECT_BLOB_MISMATCH:{activation_path}:{declared}:{actual}"
        )
    return path, _load(path, root)


def root_partition(part: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    r2_only = set(part.get("root2_only") or [])
    r3_only = set(part.get("root3_only") or [])
    mixed = set(part.get("root2_and_root3") or [])
    if (r2_only & r3_only) or (r2_only & mixed) or (r3_only & mixed):
        raise FrontierCompileError("ROOT_PARTITION_NOT_DISJOINT")
    r2 = r2_only | mixed
    r3 = r3_only | mixed
    expected_unresolved = len(r2_only) + len(r3_only) + len(mixed)
    if expected_unresolved != int(part.get("unresolved_total", -1)):
        raise FrontierCompileError("ROOT_PARTITION_COUNT_MISMATCH")
    if len(r2) != int(part.get("root2_only_count", -1)) + int(
        part.get("root2_and_root3_count", -1)
    ):
        raise FrontierCompileError("ROOT2_COUNT_MISMATCH")
    if len(r3) != int(part.get("root3_only_count", -1)) + int(
        part.get("root2_and_root3_count", -1)
    ):
        raise FrontierCompileError("ROOT3_COUNT_MISMATCH")
    return r2, r3


def _is_open_state(state: object) -> bool:
    s = str(state or "").upper()
    return not (
        s.startswith("CLOSED")
        or s.startswith("PROVED")
        or s.startswith("PASS")
        or "CLOSED__" in s
    )


def meta_envelope_obligations(meta: Mapping[str, Any]) -> dict[str, Any]:
    mappings = list(meta.get("family_mapping_frontier") or [])
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

    acceptance = root_state.get("current_acceptance")
    part = root_state.get("current_residual_root_partition")
    if not isinstance(acceptance, Mapping) or not isinstance(part, Mapping):
        raise FrontierCompileError("CURRENT_ROOT_STATE_INCOMPLETE")

    unresolved = int(acceptance.get("unresolved_atomic", -1))
    if unresolved != int(part.get("unresolved_total", -2)):
        raise FrontierCompileError("ACCEPTANCE_ROOT_PARTITION_DRIFT")

    saturation = evidence.get("saturation")
    if not isinstance(saturation, Mapping):
        raise FrontierCompileError("EVIDENCE_SATURATION_MISSING")
    if int(saturation.get("proved_predicate_count", -1)) != int(
        acceptance.get("proved_atomic", -2)
    ):
        raise FrontierCompileError("EVIDENCE_PROVED_COUNT_DRIFT")
    if int(saturation.get("unresolved_predicate_count", -1)) != unresolved:
        raise FrontierCompileError("EVIDENCE_UNRESOLVED_COUNT_DRIFT")

    root2, root3 = root_partition(part)

    r1ver, r1act_path, r1act = _discover_highest_active(ROOT1_ACTIVATION_RE, root)
    r1subject_path, r1meta = _validate_subject(r1act_path, r1act, root)
    meta = meta_envelope_obligations(r1meta)

    zver, zact_path, zact = _discover_highest_active(
        ZERO_REALITY_ACTIVATION_RE, root
    )
    zsubject_path, zcut = _validate_subject(zact_path, zact, root)

    exact = zcut.get("exact_state")
    if isinstance(exact, Mapping):
        for key in ("accepted_families", "open_families", "proved_atomic", "unresolved_atomic"):
            if key in exact and int(exact[key]) != int(acceptance.get(key, -999)):
                raise FrontierCompileError(f"ZERO_REALITY_CUT_COUNT_DRIFT:{key}")

    root1_positive = int(part.get("root1_positive_gap_count", -1))
    terminal = terminal_finality(
        acceptance,
        root1_positive_gap_count=root1_positive,
        meta_open_count=int(meta["open_count"]),
    )

    component_paths = [
        ROOT_STATE_PATH,
        EVIDENCE_PATH,
        r1act_path,
        r1subject_path,
        zact_path,
        zsubject_path,
    ]
    blobs = {p: git_blob_sha(p, root) for p in component_paths}

    return {
        "schema": "PROJECT_BRAIN_LIVE_TERMINAL_FRONTIER_V1",
        "status": "TERMINAL_TRUE" if terminal else "TERMINAL_FALSE",
        "acceptance": dict(acceptance),
        "root1_positive_gap_count": root1_positive,
        "root2_touching": sorted(root2),
        "root2_touching_count": len(root2),
        "root3_touching": sorted(root3),
        "root3_touching_count": len(root3),
        "meta_envelope": {
            "active_version": r1ver,
            "activation_path": r1act_path,
            "subject_path": r1subject_path,
            **meta,
        },
        "zero_reality_cut": {
            "active_version": zver,
            "activation_path": zact_path,
            "subject_path": zsubject_path,
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
