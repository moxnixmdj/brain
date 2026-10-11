from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_AUTHORITY_CONVENTION_SWEEP_V1"
REVIEW_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_AUTHORITY_CONVENTION_REVIEW_V1"

CLASS_PATTERNS = {
    "AUTHORITY_OVERRIDE": re.compile(r"\b(override|overrides|supersede|supersedes|takes precedence|current instruction|latest instruction|pinned|effective immediately)\b", re.I),
    "STANDARD_POLICY": re.compile(r"\b(standard|policy|must|shall|required|do not|never|always|guideline|template|house style|firm style)\b", re.I),
    "ASSUMPTION_CONTROL": re.compile(r"\b(assumption|assumptions|fx|exchange rate|currency|unit|units|source vintage|data vintage|as of|latest available)\b", re.I),
    "PROFESSIONAL_CONVENTION": re.compile(r"\b(format|formatting|legend|colour|color|spelling|tone|recommendation|citation|source note|source notes|vintage|currency|units?)\b", re.I),
    "SCENARIO_STRUCTURE": re.compile(r"\b(scenario|scenarios|base case|upside|downside|bull|bear|transition case|sensitivity|sensitivities)\b", re.I),
    "RECONCILIATION_STRUCTURE": re.compile(r"\b(reconcile|reconciliation|top[- ]down|bottom[- ]up|cross[- ]check|crosscheck|bridge)\b", re.I),
}
HIGH_SIGNAL = {"AUTHORITY_OVERRIDE", "STANDARD_POLICY"}


class AuthoritySweepError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda x: str(x)):
            yield from _walk_strings(value[key], path + "." + str(key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _walk_strings(item, path + f"[{i}]")
    elif isinstance(value, str):
        text = value.strip()
        if text:
            yield path, text


def discover_candidates(parse_manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(parse_manifest, Mapping):
        raise AuthoritySweepError("PARSE_MANIFEST_INVALID")
    if parse_manifest.get("status") != "PASS__ALL_DECLARED_SOURCES_PARSED":
        raise AuthoritySweepError("ALL_DECLARED_SOURCES_NOT_PARSED")
    receipts = parse_manifest.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise AuthoritySweepError("PARSE_RECEIPTS_REQUIRED")

    rows = []
    seen = set()
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise AuthoritySweepError("PARSE_RECEIPT_INVALID")
        source_path = receipt.get("source_path")
        source_sha = receipt.get("source_sha256")
        parsed = receipt.get("parsed")
        if not isinstance(source_path, str) or not source_path:
            raise AuthoritySweepError("SOURCE_PATH_INVALID")
        if not isinstance(source_sha, str) or len(source_sha) != 64:
            raise AuthoritySweepError("SOURCE_SHA_INVALID:" + source_path)
        if not isinstance(parsed, Mapping):
            raise AuthoritySweepError("PARSED_REPRESENTATION_INVALID:" + source_path)

        for fragment_path, text in _walk_strings(parsed):
            classes = sorted(name for name, pat in CLASS_PATTERNS.items() if pat.search(text))
            if not classes:
                continue
            material = {
                "source_path": source_path,
                "source_sha256": source_sha,
                "fragment_path": fragment_path,
                "text": text,
                "classes": classes,
            }
            candidate_id = "AAC:" + _sha(_canon(material))
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append({
                "candidate_id": candidate_id,
                **material,
                "high_signal": bool(set(classes) & HIGH_SIGNAL),
            })

    rows.sort(key=lambda x: (x["source_path"], x["fragment_path"], x["candidate_id"]))
    material = {
        "schema": SCHEMA,
        "status": "AUTHORITY_CONVENTION_CANDIDATES_DISCOVERED",
        "parse_manifest_sha256": parse_manifest.get("parse_manifest_sha256"),
        "candidate_count": len(rows),
        "high_signal_count": sum(1 for x in rows if x["high_signal"]),
        "candidates": rows,
        "semantic_completeness_claimed": False,
        "negative_relevance_claimed": False,
        "hidden_rubric_information_used": False,
        "terminal_authority": False,
    }
    return {**material, "sweep_sha256": _sha(_canon(material))}


def verify_review(sweep: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(sweep, Mapping) or sweep.get("schema") != SCHEMA:
        raise AuthoritySweepError("SWEEP_INVALID")
    if not isinstance(review, Mapping) or review.get("schema") != REVIEW_SCHEMA:
        raise AuthoritySweepError("REVIEW_INVALID")
    if review.get("sweep_sha256") != sweep.get("sweep_sha256"):
        raise AuthoritySweepError("SWEEP_BINDING_MISMATCH")

    candidates = sweep.get("candidates")
    rows = review.get("rows")
    if not isinstance(candidates, list) or not isinstance(rows, list):
        raise AuthoritySweepError("CANDIDATES_OR_REVIEW_ROWS_INVALID")

    by_id = {x["candidate_id"]: x for x in candidates}
    if len(by_id) != len(candidates):
        raise AuthoritySweepError("CANDIDATE_ID_DUPLICATE")
    seen = set()
    errors = []
    resolved = []
    allowed_actions = {
        "AUTHORITY",
        "CONVENTION",
        "DIMENSION",
        "SCENARIO_STRUCTURE",
        "RECONCILIATION_STRUCTURE",
        "DATA_INPUT",
        "CONTEXT_ONLY",
    }

    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"REVIEW_ROW_NOT_OBJECT:{i}")
            continue
        cid = row.get("candidate_id")
        action = row.get("action")
        if not isinstance(cid, str) or cid not in by_id:
            errors.append(f"REVIEW_CANDIDATE_UNKNOWN:{i}")
            continue
        if cid in seen:
            errors.append("REVIEW_CANDIDATE_DUPLICATE:" + cid)
            continue
        seen.add(cid)
        if action not in allowed_actions:
            errors.append("REVIEW_ACTION_INVALID:" + cid)
            continue
        cand = by_id[cid]
        if cand.get("high_signal") and action in {"DATA_INPUT", "CONTEXT_ONLY"}:
            errors.append("HIGH_SIGNAL_AUTHORITY_NOT_BOUND:" + cid)
        if action == "CONTEXT_ONLY":
            receipt = row.get("context_only_justification_receipt")
            if not isinstance(receipt, str) or not receipt.strip():
                errors.append("CONTEXT_ONLY_JUSTIFICATION_MISSING:" + cid)
        if action in {"AUTHORITY", "CONVENTION", "DIMENSION", "SCENARIO_STRUCTURE", "RECONCILIATION_STRUCTURE"}:
            target_ids = row.get("target_ids")
            if not isinstance(target_ids, list) or not target_ids or any(not isinstance(x, str) or not x.strip() for x in target_ids):
                errors.append("BOUND_TARGET_IDS_MISSING:" + cid)
        resolved.append({"candidate_id": cid, "action": action})

    missing = sorted(set(by_id) - seen)
    errors.extend("UNREVIEWED_CANDIDATE:" + cid for cid in missing)

    passed = not errors
    material = {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_AUTHORITY_CONVENTION_REVIEW_VERDICT_V1",
        "status": "PASS__ALL_DISCOVERED_CANDIDATES_REVIEWED" if passed else "FAIL_CLOSED",
        "pass": passed,
        "errors": sorted(set(errors)),
        "sweep_sha256": sweep.get("sweep_sha256"),
        "candidate_count": len(candidates),
        "reviewed_count": len(seen),
        "high_signal_count": int(sweep.get("high_signal_count") or 0),
        "semantic_completeness_claimed": False,
        "negative_relevance_self_certified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**material, "review_verdict_sha256": _sha(_canon(material))}
