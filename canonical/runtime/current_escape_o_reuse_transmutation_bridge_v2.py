"""Current O-row reuse discovery bridge V2.

V1 discovers only fully normalized transmutation evidence. V2 preserves that
strict lane unchanged and adds a separate fail-closed legacy adaptation lane
for explicitly row-targeted canonical artifacts that can be normalized or
specialized before requesting new external reality.

Legacy adaptation inputs grant no acceptance, promotion, capability, ownership,
or terminal credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from canonical.runtime import current_escape_o_reuse_transmutation_bridge_v1 as v1

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O_REUSE_TRANSMUTATION_BRIDGE_V2"
CUT_SCHEMA = v1.CUT_SCHEMA
CUT_PATH = v1.CUT_PATH
ROOTS = ("canonical/governance", "canonical/evidence", "canonical/verification")
MAX_BYTES = v1.MAX_BYTES

_LEGACY_CONTEXT_KEYS = ("predicate_id", "target_predicate", "obligation_id", "frozen_predicate_id")
_EXACT_STRUCTURED_ALIASES = {
    ("target_surface", "HUMANITYS_LAST_EXAM"): "HLE_TOOLS_GE_67_7",
    ("scope", "CURRENT_GDPVAL_AA_V2_1_PUBLIC_FIXED_BAR_ACCEPTANCE_ROUTE_ONLY"): "PROWORK_GDPVAL_GE_1846",
}
_PREFIX_STRUCTURED_ALIASES = (
    ("problem", "MYSTERYMECHANISM_V2_", "MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER"),
)


def _legacy_targets(doc: Mapping[str, Any], active: set[str]) -> set[str]:
    out: set[str] = set()
    for key in _LEGACY_CONTEXT_KEYS:
        value = doc.get(key)
        if isinstance(value, str) and value in active:
            out.add(value)
    values = doc.get("predicate_ids")
    if isinstance(values, list):
        out.update(v for v in values if isinstance(v, str) and v in active)
    for (key, expected), pid in _EXACT_STRUCTURED_ALIASES.items():
        if pid in active and doc.get(key) == expected:
            out.add(pid)
    for key, prefix, pid in _PREFIX_STRUCTURED_ALIASES:
        value = doc.get(key)
        if pid in active and isinstance(value, str) and value.startswith(prefix):
            out.add(pid)
    return out


def _append_strings(dst: list[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        dst.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                dst.append(item.strip())


def _remaining_delta(doc: Mapping[str, Any]) -> list[str]:
    raw: list[str] = []
    _append_strings(raw, doc.get("remaining_route_blocker"))
    _append_strings(raw, doc.get("next"))

    frontier = doc.get("frontier_effect")
    if isinstance(frontier, Mapping):
        _append_strings(raw, frontier.get("new_single_primary_burden"))
        _append_strings(raw, frontier.get("preserve"))

    causal = doc.get("causal_reduction")
    if isinstance(causal, Mapping):
        _append_strings(raw, causal.get("still_open"))

    _append_strings(raw, doc.get("preserve"))
    mystery = doc.get("mysterymechanism_use")
    if isinstance(mystery, Mapping):
        _append_strings(raw, mystery.get("remaining_bridge"))

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if item not in seen:
            seen.add(item)
            out.append(item)
        if len(out) >= 12:
            break
    return out


def _has_adaptation_signal(doc: Mapping[str, Any]) -> bool:
    return any(
        key in doc
        for key in (
            "status",
            "new_primitive_required",
            "remaining_route_blocker",
            "next",
            "frontier_effect",
            "causal_reduction",
            "preserve",
            "hard_nonclaims",
        )
    )


def analyze_documents(cut: Mapping[str, Any], documents: Iterable[tuple[str, str, Any]]) -> dict[str, Any]:
    docs = list(documents)
    strict = v1.analyze_documents(cut, docs)
    active = v1._active_o_ids(cut)

    strict_keys = {
        (row["obligation_id"], row["source_path"], row["source_git_blob_sha"])
        for row in strict.get("candidates", [])
    }

    adaptation: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for source_path, source_blob, doc in docs:
        if not isinstance(source_path, str) or not source_path.startswith(ROOTS):
            continue
        if not isinstance(source_blob, str) or len(source_blob) != 40:
            continue
        if not isinstance(doc, Mapping) or not _has_adaptation_signal(doc):
            continue

        targets = _legacy_targets(doc, active)
        if not targets:
            continue

        for pid in sorted(targets):
            key = (pid, source_path, source_blob)
            if key in seen or key in strict_keys:
                continue
            seen.add(key)
            hard_nonclaims = doc.get("hard_nonclaims")
            if not isinstance(hard_nonclaims, list):
                hard_nonclaims = doc.get("nonclaims")
            if not isinstance(hard_nonclaims, list):
                hard_nonclaims = []
            adaptation.append(
                {
                    "obligation_id": pid,
                    "source_path": source_path,
                    "source_git_blob_sha": source_blob,
                    "source_status": doc.get("status"),
                    "new_primitive_required": doc.get("new_primitive_required"),
                    "remaining_delta": _remaining_delta(doc),
                    "hard_nonclaims": [x for x in hard_nonclaims if isinstance(x, str)][:16],
                    "normalization_required": True,
                    "v4_packaging_required": True,
                    "current_row_independent_verification_required": True,
                    "acceptance_authority": False,
                }
            )

    adaptation.sort(key=lambda r: (r["obligation_id"], r["source_path"], r["source_git_blob_sha"]))
    strict_ids = sorted(set(strict.get("candidate_obligation_ids", [])))
    adaptation_ids = sorted({row["obligation_id"] for row in adaptation})
    reuse_covered = set(strict_ids) | set(adaptation_ids)

    return {
        "schema": SCHEMA,
        "status": "PASS__STRICT_TRANSMUTATION_PLUS_LEGACY_ADAPTATION_DISCOVERY__ZERO_CREDIT",
        "pass": True,
        "active_o_count": len(active),
        "strict_candidate_obligation_ids": strict_ids,
        "strict_candidate_obligation_count": len(strict_ids),
        "strict_candidates": strict.get("candidates", []),
        "strict_rejections": strict.get("rejections", []),
        "adaptation_candidate_obligation_ids": adaptation_ids,
        "adaptation_candidate_obligation_count": len(adaptation_ids),
        "legacy_adaptation_inputs": adaptation,
        "reuse_covered_obligation_ids": sorted(reuse_covered),
        "reuse_covered_obligation_count": len(reuse_covered),
        "reuse_uncovered_obligation_ids": sorted(active - reuse_covered),
        "reuse_uncovered_obligation_count": len(active - reuse_covered),
        "acceptance_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": "LEGACY_ADAPTATION_INPUT_IS_NOT_A_PROOF__NORMALIZE_PACKAGE_AND_INDEPENDENTLY_VERIFY_BEFORE_ANY_ROW_CREDIT",
    }


def _load_json(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


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
            documents.append((path.relative_to(root).as_posix(), v1._blob(raw), doc))

    out = analyze_documents(cut, documents)
    out.update(
        {
            "scanned_json_file_count": scanned,
            "scanned_json_bytes": scanned_bytes,
            "parse_failure_count": len(parse_failures),
            "parse_failures": parse_failures[:32],
        }
    )
    return out


def run(args=None, root=None):
    return scan(repo_root=root)


if __name__ == "__main__":
    print(json.dumps(scan(), indent=2, sort_keys=True))
