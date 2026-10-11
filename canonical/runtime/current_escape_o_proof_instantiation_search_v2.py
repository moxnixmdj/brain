"""Fail-closed discovery of existing proof instantiations for current active O rows.

Successor to current_escape_o11_proof_instantiation_search_v1. Membership follows
current_escape_o_objective_acceptance_law_gate_v2, so current O/Q/parked
reclassification is reflected without historical O11/Q2 leakage.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import current_escape_o_objective_acceptance_law_gate_v2 as gate

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O_PROOF_INSTANTIATION_SEARCH_V2"
ROOTS = ("canonical/governance", "canonical/evidence", "canonical/verification", "canonical/action_intents")
MAX_BYTES = 8_000_000


def _canon(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _sha(x: Mapping[str, Any]) -> str:
    return sha256(_canon(x)).hexdigest()


def _walk(x: Any):
    if isinstance(x, Mapping):
        yield x
        for value in x.values():
            yield from _walk(value)
    elif isinstance(x, list):
        for value in x:
            yield from _walk(value)


def _claims(doc: Any):
    seen: set[str] = set()
    for obj in _walk(doc):
        rows = []
        if isinstance(obj.get("claim_spec"), Mapping):
            rows.append(obj["claim_spec"])
        if all(isinstance(obj.get(k), Mapping) for k in ("policy", "evidence", "current_identity")):
            rows.append(obj)
        for row in rows:
            digest = _sha(row)
            if digest not in seen:
                seen.add(digest)
                yield row


def scan(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True) if repo_root is not None else Path(__file__).resolve().parents[2]
    o, q, parked, cut = gate._current_projection(root)
    found = []
    parse_failures = []
    nfiles = 0
    nbytes = 0
    for relroot in ROOTS:
        base = (root / relroot).resolve()
        try:
            base.relative_to(root)
        except ValueError:
            continue
        if not base.is_dir() or base.is_symlink():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                path = path.resolve(strict=True)
                path.relative_to(root)
            except (FileNotFoundError, ValueError):
                continue
            if not path.is_file() or path.is_symlink():
                continue
            raw = path.read_bytes()
            if len(raw) > MAX_BYTES:
                continue
            nfiles += 1
            nbytes += len(raw)
            try:
                doc = json.loads(raw.decode())
            except Exception as exc:
                parse_failures.append({"path": path.relative_to(root).as_posix(), "reason": type(exc).__name__})
                continue
            for claim in _claims(doc):
                policy = claim.get("policy")
                pid = str(policy.get("predicate_id") or "") if isinstance(policy, Mapping) else ""
                if pid not in o:
                    continue
                verdict = gate.evaluate({"obligation_id": pid, "claim_spec": claim}, repo_root=root)
                found.append({
                    "obligation_id": pid,
                    "source_path": path.relative_to(root).as_posix(),
                    "source_git_blob_sha": _blob(raw),
                    "claim_spec_sha256": _sha(claim),
                    "gate_pass": verdict.get("pass") is True,
                    "gate_status": verdict.get("status"),
                    "gate_reason": verdict.get("reason"),
                    "proof_mode": verdict.get("proof_mode"),
                })

    unique = {}
    for row in found:
        unique[(row["obligation_id"], row["source_git_blob_sha"], row["claim_spec_sha256"])] = row
    found = sorted(unique.values(), key=lambda r: (not r["gate_pass"], r["obligation_id"], r["source_path"]))
    proved = sorted({r["obligation_id"] for r in found if r["gate_pass"]})
    missing = sorted(o - set(proved))
    by_source: dict[str, set[str]] = {}
    for row in found:
        if row["gate_pass"]:
            by_source.setdefault(row["source_path"], set()).add(row["obligation_id"])
    multi = sorted(
        (
            {"source_path": path, "proved_obligation_ids": sorted(ids), "proved_row_count": len(ids)}
            for path, ids in by_source.items() if len(ids) > 1
        ),
        key=lambda r: (-r["proved_row_count"], r["source_path"]),
    )
    near = {
        pid: [
            {k: row.get(k) for k in ("source_path", "source_git_blob_sha", "claim_spec_sha256", "gate_status", "gate_reason", "proof_mode")}
            for row in found if row["obligation_id"] == pid and not row["gate_pass"]
        ][:16]
        for pid in missing
    }
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_O_PROOF_INSTANTIATION_SEARCH_COMPLETE",
        "pass": True,
        "current_cut_status": cut.get("status"),
        "current_o_count": len(o),
        "current_q_count": len(q),
        "current_parked_count": len(parked),
        "scanned_json_file_count": nfiles,
        "scanned_json_bytes": nbytes,
        "parse_failure_count": len(parse_failures),
        "parse_failures": parse_failures[:32],
        "candidate_count": len(found),
        "proved_candidate_count": sum(row["gate_pass"] for row in found),
        "proved_obligation_ids": proved,
        "proved_obligation_count": len(proved),
        "missing_obligation_ids": missing,
        "missing_obligation_count": len(missing),
        "multi_row_proof_sources": multi,
        "candidates": found,
        "near_misses": near,
        "all_o_rows_have_proved_candidate": not missing,
        "acceptance_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def run(args=None, root=None):
    return scan(repo_root=root)


if __name__ == "__main__":
    print(json.dumps(scan(), indent=2, sort_keys=True))
