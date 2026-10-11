"""Current O-row stronger-proof transmutation discovery bridge.

Reuses the already-verified acceptance_proof_transmuter_v1 on the current
objective-acceptance projection. Existing current O proof search only discovers
preassembled V4 claim_spec objects. This bridge additionally discovers stronger
proof evidence already present in canonical JSON, binds it to current O rows
only through explicit predicate context, and reports candidates that are ready
for V4 packaging/current-row verification.

It grants no acceptance, promotion, capability, ownership, or terminal credit.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from canonical.runtime.acceptance_proof_transmuter_v1 import _base, _mode_pass

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O_REUSE_TRANSMUTATION_BRIDGE_V1"
CUT_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1"
CUT_PATH = Path("canonical/governance/CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1.json")
ROOTS = ("canonical/governance", "canonical/evidence", "canonical/verification", "canonical/action_intents")
MAX_BYTES = 8_000_000

_CONTEXT_KEYS = ("predicate_id", "target_predicate", "obligation_id")
_REQUIRED_EVIDENCE_KEYS = (
    "mode",
    "verified",
    "independent",
    "contamination_clean",
    "binds_frozen_protocol",
    "closes_entire_protocol",
    "scope_relation",
    "result",
)

def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _canon(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def _sha(x: Mapping[str, Any]) -> str:
    return sha256(_canon(x)).hexdigest()

def _load_json(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc

def _active_o_ids(cut: Mapping[str, Any]) -> set[str]:
    if cut.get("schema") != CUT_SCHEMA:
        raise ValueError("CURRENT_CUT_SCHEMA_INVALID")
    part = cut.get("current_partition")
    if not isinstance(part, Mapping):
        raise ValueError("CURRENT_PARTITION_INVALID")
    ids = part.get("active_o_obligation_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("CURRENT_O_IDS_INVALID")
    if len(ids) != len(set(ids)):
        raise ValueError("CURRENT_O_IDS_DUPLICATE")
    expected = part.get("active_o_rows")
    if expected != len(ids):
        raise ValueError("CURRENT_O_COUNT_MISMATCH")
    return set(ids)

def _local_context(obj: Mapping[str, Any], active: set[str]) -> set[str]:
    out: set[str] = set()
    for key in _CONTEXT_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value in active:
            out.add(value)
    values = obj.get("predicate_ids")
    if isinstance(values, list):
        out.update(v for v in values if isinstance(v, str) and v in active)
    return out

def _walk(obj: Any, active: set[str], inherited: frozenset[str] = frozenset()):
    if isinstance(obj, Mapping):
        local = _local_context(obj, active)
        context = frozenset(local) if local else inherited
        yield obj, context
        for value in obj.values():
            yield from _walk(value, active, context)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value, active, inherited)

def _looks_like_transmutation_evidence(obj: Mapping[str, Any]) -> bool:
    return all(key in obj for key in _REQUIRED_EVIDENCE_KEYS)

def analyze_documents(cut: Mapping[str, Any], documents: Iterable[tuple[str, str, Any]]) -> dict[str, Any]:
    active = _active_o_ids(cut)
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for source_path, source_blob, doc in documents:
        if not isinstance(source_path, str) or not source_path:
            continue
        if not isinstance(source_blob, str) or len(source_blob) != 40:
            continue
        for obj, context in _walk(doc, active):
            if not context or not _looks_like_transmutation_evidence(obj):
                continue
            digest = _sha(obj)
            for pid in sorted(context):
                key = (pid, source_blob, digest)
                if key in seen:
                    continue
                seen.add(key)
                base_ok, base_reasons = _base(obj)
                if not base_ok:
                    rejected.append({
                        "obligation_id": pid,
                        "source_path": source_path,
                        "source_git_blob_sha": source_blob,
                        "evidence_sha256": digest,
                        "reasons": list(base_reasons),
                    })
                    continue
                mode_ok, mode_reason = _mode_pass(obj)
                if not mode_ok:
                    rejected.append({
                        "obligation_id": pid,
                        "source_path": source_path,
                        "source_git_blob_sha": source_blob,
                        "evidence_sha256": digest,
                        "mode": obj.get("mode"),
                        "reasons": [mode_reason],
                    })
                    continue
                rows.append({
                    "obligation_id": pid,
                    "source_path": source_path,
                    "source_git_blob_sha": source_blob,
                    "evidence_sha256": digest,
                    "mode": obj.get("mode"),
                    "transmuter_reason": mode_reason,
                    "v4_packaging_required": True,
                    "current_row_independent_verification_required": True,
                })

    rows.sort(key=lambda r: (r["obligation_id"], r["source_path"], r["evidence_sha256"]))
    rejected.sort(key=lambda r: (r["obligation_id"], r["source_path"], r["evidence_sha256"]))

    ready_ids = sorted({r["obligation_id"] for r in rows})
    missing_ids = sorted(active - set(ready_ids))
    by_source: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        by_source.setdefault((row["source_path"], row["source_git_blob_sha"]), set()).add(row["obligation_id"])
    multi = [
        {"source_path": p, "source_git_blob_sha": b, "obligation_ids": sorted(ids), "row_count": len(ids)}
        for (p, b), ids in by_source.items() if len(ids) > 1
    ]
    multi.sort(key=lambda r: (-r["row_count"], r["source_path"]))

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_O_REUSE_TRANSMUTATION_DISCOVERY",
        "pass": True,
        "active_o_count": len(active),
        "transmutation_candidate_count": len(rows),
        "candidate_obligation_ids": ready_ids,
        "candidate_obligation_count": len(ready_ids),
        "missing_obligation_ids": missing_ids,
        "missing_obligation_count": len(missing_ids),
        "multi_row_sources": multi,
        "candidates": rows,
        "rejections": rejected[:128],
        "acceptance_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": "TRANSMUTER_PASS_IS_DISCOVERY_ONLY__CANDIDATE_MUST_BE_PACKAGED_INTO_CURRENT_V4_CLAIM_AND_INDEPENDENTLY_VERIFIED_BEFORE_CANONICAL_ROW_CREDIT",
    }

def scan(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True) if repo_root is not None else Path(__file__).resolve().parents[2]
    cut = _load_json(root / CUT_PATH)
    documents: list[tuple[str, str, Any]] = []
    parse_failures: list[dict[str, str]] = []
    scanned = 0
    scanned_bytes = 0

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
            scanned += 1
            scanned_bytes += len(raw)
            try:
                doc = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                parse_failures.append({"path": path.relative_to(root).as_posix(), "reason": type(exc).__name__})
                continue
            documents.append((path.relative_to(root).as_posix(), _blob(raw), doc))

    out = analyze_documents(cut, documents)
    out.update({
        "scanned_json_file_count": scanned,
        "scanned_json_bytes": scanned_bytes,
        "parse_failure_count": len(parse_failures),
        "parse_failures": parse_failures[:32],
    })
    return out

def run(args=None, root=None):
    return scan(repo_root=root)

if __name__ == "__main__":
    print(json.dumps(scan(), indent=2, sort_keys=True))
