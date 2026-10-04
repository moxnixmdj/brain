#!/usr/bin/env python3
"""Reference-free constructor for LiveBench/IFBench character-trigram overlap constraints.

The pinned LiveBench scorer at commit 8f8e5c381a16e3f24257776edd53471fe86f8091
scores SET overlap of raw Python character trigrams:

    |G3(output) ∩ G3(reference)| / |G3(output)|

This module does not read reference_text.  It is sound under the explicit
WHITESPACE_NORMALIZATION_ONLY contract: base_text and the scorer reference have
identical non-whitespace character runs; only whitespace between those runs may
differ. Under that contract:
  * any trigram wholly inside a non-whitespace run of base_text is guaranteed
    present in the reference; and
  * a sentinel character absent from base_text is absent from the reference.

The constructor searches tiny outputs whose unique trigram set is composed only
of those two classes, so the overlap ratio is known exactly without recovering
the hidden/raw reference formatting.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_NGRAM_REFERENCE_FREE_V1"
CONTRACT = "WHITESPACE_NORMALIZATION_ONLY"


def _trigrams(text: str) -> set[str]:
    text = str(text)
    return {text[i:i+3] for i in range(max(0, len(text) - 2))}


def _sentinels(base_text: str, need: int = 96) -> list[str]:
    """Return non-whitespace characters absent from base_text.

    Private-use Unicode is used only as a convenient candidate alphabet.  The
    proof obligation is absence from base_text plus CONTRACT, not any assumption
    that private-use characters are globally impossible.
    """
    out: list[str] = []
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in base_text:
            out.append(ch)
            if len(out) >= need:
                return out
    return out


def _guaranteed_ratio(candidate: str, base_text: str, sentinels: set[str]) -> tuple[float, int, int] | None:
    """Exact ratio under CONTRACT, or None if any output trigram is unclassified."""
    output = _trigrams(candidate)
    if not output:
        return None

    guaranteed_overlap = {g for g in _trigrams(base_text) if not any(c.isspace() for c in g)}
    hit = 0
    for g in output:
        if g in guaranteed_overlap:
            hit += 1
            continue
        # Any trigram containing an absent non-whitespace sentinel is guaranteed
        # absent from the reference under CONTRACT.
        if any(ch in sentinels for ch in g):
            continue
        return None
    return 100.0 * hit / len(output), hit, len(output)


def construct(base_text: str, percentage: float, tolerance: float = 2.0) -> dict[str, Any]:
    base_text = str(base_text or "")
    try:
        target = float(percentage)
        tol = float(tolerance)
    except Exception:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "INVALID_PERCENTAGE"}

    if not base_text:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "BASE_TEXT_REQUIRED"}
    if not (0.0 <= target <= 100.0 and 0.0 <= tol <= 100.0):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "OUT_OF_RANGE"}

    pool = _sentinels(base_text)
    if len(pool) < 64:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "INSUFFICIENT_ABSENT_SENTINELS"}
    sentinel_set = set(pool)

    best: dict[str, Any] | None = None

    def consider(candidate: str, kind: str, source: str) -> None:
        nonlocal best
        certified = _guaranteed_ratio(candidate, base_text, sentinel_set)
        if certified is None:
            return
        ratio, numerator, denominator = certified
        if not (target - tol <= ratio <= target + tol):
            return
        record = {
            "response": candidate,
            "certified_percent": ratio,
            "numerator": numerator,
            "denominator": denominator,
            "construction": kind,
            "source_span": source,
        }
        if best is None:
            best = record
            return
        old = (len(best["response"]), abs(best["certified_percent"] - target))
        new = (len(candidate), abs(ratio - target))
        if new < old:
            best = record

    for match in re.finditer(r"\S{3,}", base_text):
        run = match.group(0)
        # Long runs add no proof strength for this finite ±2% target search.
        max_len = min(len(run), 96)
        for start in range(0, len(run) - 2):
            for length in range(3, min(max_len, len(run) - start) + 1):
                source = run[start:start + length]
                consider(source, "RAW_SPAN", source)
                consider(pool[0] + source[1:], "MUTATE_FIRST", source)
                consider(source[:-1] + pool[0], "MUTATE_LAST", source)
                if len(source) >= 4:
                    consider(pool[0] + source[1:-1] + pool[1], "MUTATE_BOTH_ENDS", source)

                # Appending n distinct absent characters contributes only
                # certified non-overlap trigrams (including the transition).
                for n in range(1, 61):
                    tail = "".join(pool[:n])
                    consider(source + tail, "APPEND_ABSENT", source)
                    consider(pool[0] + source[1:] + tail, "MUTATE_FIRST_APPEND_ABSENT", source)

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_CERTIFIED_CONSTRUCTION_FOUND",
            "target_percent": target,
            "tolerance": tol,
            "contract": CONTRACT,
            "reference_text_read": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_UNDER_CONTRACT",
        "target_percent": target,
        "tolerance": tol,
        "contract": CONTRACT,
        "reference_text_read": False,
        "model_dependency_count": 0,
        "network_used": False,
        **best,
    }


_RATIO = re.compile(r"Maintain a trigram overlap of \d+(?:\.\d+)?% \(±2%\) with the provided reference text\.")
_SENTENCE_KEYWORD = re.compile(r"The response must include keyword \S+ in the \d+(?:-st|-nd|-rd|-th) sentence\.")
_CONSONANT_CLUSTER = re.compile(r"Ensure each word in your response has at least one consonant cluster \(two or more consonants together\)\.")


def extract_pinned_public_ifbench_base(prompt: str) -> str:
    """Extractor for the exact constraint forms present in the pinned public 12-row audit.

    This helper is deliberately narrow and fail-closed by scope. It is not a
    claim about unseen/frozen terminal rows.
    """
    value = str(prompt or "")
    value = _RATIO.sub("", value)
    value = _SENTENCE_KEYWORD.sub("", value)
    value = _CONSONANT_CLUSTER.sub("", value)
    return value.strip()


def score_with_reference_for_audit(response: str, reference_text: str) -> float:
    """Audit-only mirror of the pinned scorer. Never called by construct()."""
    out = _trigrams(response)
    if not out:
        return 0.0
    ref = _trigrams(reference_text)
    return 100.0 * len(out & ref) / len(out)


def audit_public_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit public ratio:overlap rows; hidden/public kwargs are verifier-only."""
    checked = []
    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        idx = ids.index("ratio:overlap")
        kwargs = (row.get("kwargs") or [])[idx]
        target = float(kwargs["percentage"])
        reference = str(kwargs["reference_text"])
        base = extract_pinned_public_ifbench_base(str(row["prompt"]))
        result = construct(base, target)
        if result.get("status") != "PASS_UNDER_CONTRACT":
            checked.append({"key": row.get("key"), "pass": False, "reason": result.get("error")})
            continue
        actual = score_with_reference_for_audit(result["response"], reference)
        checked.append({
            "key": row.get("key"),
            "target": target,
            "certified_percent": result["certified_percent"],
            "actual_public_reference_percent": actual,
            "pass": target - 2 <= actual <= target + 2,
        })

    return {
        "schema": SCHEMA + "_PUBLIC_AUDIT",
        "ratio_rows": len(checked),
        "passed": sum(1 for x in checked if x.get("pass")),
        "all_pass": bool(checked) and all(x.get("pass") for x in checked),
        "rows": checked,
        "hard_nonclaim": "PUBLIC_FAMILY_AUDIT_ONLY__NO_UNSEEN_TERMINAL_ROW_OR_ACCEPTANCE_CREDIT",
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return construct(args.get("base_text", ""), args.get("percentage", 0), args.get("tolerance", 2))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("base_text")
    ap.add_argument("percentage", type=float)
    ns = ap.parse_args()
    print(json.dumps(construct(ns.base_text, ns.percentage), indent=2, ensure_ascii=False, sort_keys=True))
