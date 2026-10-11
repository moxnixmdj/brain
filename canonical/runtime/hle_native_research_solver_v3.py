#!/usr/bin/env python3
"""Brain-native HLE deterministic research solver V3.

Composition:
visible question -> verified question contract -> bounded search/fetch ->
relation-bound candidate extraction -> independent-host aggregation.

No model calls, no gold, no target-score authority.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from collections import defaultdict
from typing import Any, Callable, Mapping

from canonical.runtime.hle_native_question_contract_v1 import compile_question
from canonical.runtime.hle_evidence_candidate_synthesis_v1 import synthesize as synthesize_candidate

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_RESEARCH_SOLVER_V3"
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")


def _sha(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def _host(url: str) -> str:
    try:
        h = (urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:
        return ""
    if h.startswith("www."):
        h = h[4:]
    return h


def _windows(text: str, *, max_windows: int = 220) -> list[str]:
    rows = [" ".join(x.split()) for x in _SENTENCE.split(str(text or "")) if x.strip()]
    out: list[str] = []
    for i, row in enumerate(rows[:max_windows]):
        # Relation and objective anchor can straddle adjacent sentences.
        for a, b in ((i, i + 1), (max(0, i - 1), min(len(rows), i + 2))):
            x = " ".join(rows[a:b]).strip()
            if x and x not in out:
                out.append(x[:2200])
    return out


def propose(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool = False,
    search_fn: Callable[..., Mapping[str, Any]] | None = None,
    fetch_fn: Callable[..., Mapping[str, Any]] | None = None,
    search_limit: int = 12,
    max_fetches: int = 10,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise ValueError("IMAGE_FLAG_MUST_BE_BOOLEAN")

    contract = compile_question(
        task_id=task_id,
        question=question,
        has_nonempty_image_payload=has_nonempty_image_payload,
    )
    base = {
        "schema": SCHEMA,
        "task_id": task_id,
        "question_sha256": _sha(question),
        "contract_status": contract.get("status"),
        "candidate_answer": None,
        "candidate_answer_authority": False,
        "correctness_claimed": False,
        "gold_accessed": False,
        "external_model_calls": 0,
        "external_reasoning_model_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if contract.get("pass") is not True:
        return {**base, "status": "NO_CANDIDATE__QUESTION_CONTRACT_UNRESOLVED"}

    kind = str(contract.get("question_kind") or "")
    if kind == "BARE_OPTION_LETTER":
        return {**base, "status": "NO_CANDIDATE__MCQ_DEFER_TO_MCQ_LANE"}
    if contract.get("polarity") != "POSITIVE":
        return {**base, "status": "NO_CANDIDATE__NEGATIVE_POLARITY_NOT_IN_V3"}
    if has_nonempty_image_payload:
        return {**base, "status": "NO_CANDIDATE__IMAGE_SEMANTICS_REQUIRED_UPSTREAM"}
    if kind in {"SYMBOLIC_OR_NUMBER", "SYMBOLIC_EXPRESSION"}:
        # Symbolic lanes are intentionally earlier in the total orchestrator.
        return {**base, "status": "NO_CANDIDATE__SYMBOLIC_DEFER_TO_SYMBOLIC_LANE"}

    focus = contract.get("research_focus") or {}
    query = str(focus.get("query") or "").strip()
    if not query:
        return {**base, "status": "NO_CANDIDATE__RESEARCH_FOCUS_EMPTY"}
    if " ".join(query.split()).casefold() == " ".join(question.split()).casefold():
        return {**base, "status": "FAIL_CLOSED__RAW_QUESTION_QUERY_FORBIDDEN"}

    focus_terms = [x for x in query.split() if x]
    if not focus_terms:
        return {**base, "status": "NO_CANDIDATE__RESEARCH_FOCUS_EMPTY"}

    if search_fn is None or fetch_fn is None:
        from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools
        search_fn = search_fn or tools.search_web
        fetch_fn = fetch_fn or tools.fetch_web

    try:
        search = dict(search_fn(query, limit=max(1, min(int(search_limit), 20))))
    except Exception as exc:
        search = {"status": "FAILED", "results": [], "error_class": type(exc).__name__}

    urls: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    seen_hosts: set[str] = set()
    for row in search.get("results") or []:
        if not isinstance(row, Mapping):
            continue
        url = str(row.get("url") or "").strip()
        host = _host(url)
        if not url or not host or url in seen_urls or host in seen_hosts:
            continue
        seen_urls.add(url)
        seen_hosts.add(host)
        urls.append((url, host))
        if len(urls) >= max(1, min(int(max_fetches), 12)):
            break

    by_candidate: dict[str, dict[str, Any]] = {}
    fetch_receipts = []
    for url, host in urls:
        try:
            fetched = dict(fetch_fn(url, max_bytes=600_000))
        except Exception as exc:
            fetch_receipts.append({
                "host_sha256": _sha(host),
                "status": "FAILED",
                "error_class": type(exc).__name__,
            })
            continue
        if fetched.get("status") != "PASS":
            fetch_receipts.append({
                "host_sha256": _sha(host),
                "status": str(fetched.get("status") or "FAILED"),
            })
            continue
        final_url = str(fetched.get("final_url") or fetched.get("url") or url)
        final_host = _host(final_url) or host
        body = str(fetched.get("body_excerpt") or "")
        body_sha = str(fetched.get("body_sha256") or _sha(body))
        fetch_receipts.append({
            "host_sha256": _sha(final_host),
            "status": "PASS",
            "body_sha256": body_sha,
        })

        host_best: dict[str, tuple[float, str, str]] = {}
        for window in _windows(body):
            try:
                out = synthesize_candidate(
                    contract=contract["answer_contract"],
                    focus_terms=focus_terms,
                    evidence=window,
                )
            except Exception:
                continue
            if out.get("status") != "ONE_RELATION_BOUND_CANDIDATE":
                continue
            rows = out.get("candidates") or []
            if len(rows) != 1 or rows[0].get("support_authority") is not True:
                continue
            answer = str(rows[0].get("answer") or "").strip()
            if not answer:
                continue
            key = answer.casefold()
            score = float(out.get("focus_coverage") or 0.0)
            prev = host_best.get(key)
            if prev is None or score > prev[0]:
                host_best[key] = (score, answer, str(out.get("relation_class") or ""))

        for key, (coverage, answer, relation) in host_best.items():
            rec = by_candidate.setdefault(key, {
                "answer": answer,
                "hosts": set(),
                "score": 0.0,
                "max_coverage": 0.0,
                "relations": set(),
                "evidence_receipts": [],
            })
            if final_host not in rec["hosts"]:
                rec["hosts"].add(final_host)
                rec["score"] += coverage
            rec["max_coverage"] = max(rec["max_coverage"], coverage)
            if relation:
                rec["relations"].add(relation)
            rec["evidence_receipts"].append({
                "host_sha256": _sha(final_host),
                "body_sha256": body_sha,
                "relation_class": relation,
                "focus_coverage": coverage,
            })

    ranked = sorted(
        by_candidate.values(),
        key=lambda x: (-len(x["hosts"]), -x["score"], -x["max_coverage"], x["answer"].casefold()),
    )
    if not ranked:
        return {
            **base,
            "status": "NO_CANDIDATE__NO_RELATION_BOUND_WEB_EVIDENCE",
            "question_kind": kind,
            "query_sha256": _sha(query),
            "searched_url_count": len(urls),
            "fetch_receipts": fetch_receipts,
        }

    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    best_hosts = len(best["hosts"])
    tied = bool(
        second
        and len(second["hosts"]) == best_hosts
        and abs(float(second["score"]) - float(best["score"])) < 1e-12
    )
    accepted = (
        not tied
        and (
            best_hosts >= 2
            or (best_hosts == 1 and float(best["max_coverage"]) >= 0.95)
        )
    )
    if not accepted:
        return {
            **base,
            "status": "NO_CANDIDATE__INSUFFICIENT_OR_CONFLICTED_RELATION_EVIDENCE",
            "question_kind": kind,
            "query_sha256": _sha(query),
            "searched_url_count": len(urls),
            "candidate_count": len(ranked),
            "top_support_host_count": best_hosts,
            "top_score": best["score"],
            "tied_top": tied,
            "fetch_receipts": fetch_receipts,
        }

    confidence = "HIGH" if best_hosts >= 2 and best["max_coverage"] >= 0.75 else "MEDIUM"
    answer = best["answer"]
    return {
        **base,
        "status": "CANDIDATE_GENERATED__RELATION_BOUND_RESEARCH_V3",
        "question_kind": kind,
        "query_sha256": _sha(query),
        "searched_url_count": len(urls),
        "candidate_answer": answer,
        "candidate_answer_sha256": _sha(answer),
        "confidence_band": confidence,
        "independent_support_host_count": best_hosts,
        "support_score": best["score"],
        "max_focus_coverage": best["max_coverage"],
        "relation_classes": sorted(best["relations"]),
        "evidence_receipts": best["evidence_receipts"],
        "fetch_receipts": fetch_receipts,
        "hard_nonclaim": "RELATION_BOUND_MULTI_SOURCE_PROPOSAL_IS_NOT_A_CORRECTNESS_OR_TARGET_SCORE_PROOF",
    }


if __name__ == "__main__":
    print("IMPORT_OK")
