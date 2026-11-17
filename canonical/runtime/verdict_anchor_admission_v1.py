#!/usr/bin/env python3
"""Admit a self-judged verdict only if its judge cannot read the anchor it is graded against.

Rank 2 of the merged ranked plan (``ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.json``,
``ranked_next_with_pass_fail``): *anchor every self-judged verdict to data the
judging loop cannot read (suite/locked corpus)* -- pass: always-pass collapse is
detected at admission; kill: the anchor is readable by the thing it judges.

Why this exists
---------------
Who-Verifies the Verifier (arXiv 2610.11464) measured the failure this gate
refuses: strip the anchor guards and the verifier collapses to always-pass
while downstream skill training scores exactly as well.  A loop that passes
everything is indistinguishable from a loop that verified everything, so the
collapse is invisible from inside.  This tree measured the same asymmetry from
the other side -- ungated replay of recorded plans was 53.5% stale and 31.1%
silently corrupt across 228 real compositions
(``PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json``), and the first-case
instrument chose the wrong observation on 81% of cases
(``THE_INSTRUMENT_NOT_THE_EXPERIENCE_20261117_V1.md``).

What admission checks
---------------------
``admission_errors(judge, anchor_cases, judge_history)`` returns a sorted list
of refusal reasons; an empty list admits the judge.  Refusals, in order:

* ``JUDGE_NOT_CALLABLE`` / ``ANCHOR_SOURCE_UNREADABLE`` -- fail closed: a
  judge that cannot be called or whose source cannot be read cannot be shown
  to be separated from the anchor.
* ``ANCHOR_EMPTY`` / ``ANCHOR_CASE_INVALID:<id>`` / ``ANCHOR_DUPLICATE_CASE_ID``
  -- the anchor must be a well-formed list of ``{case_id, content,
  expected_verdict}`` records with ``expected_verdict`` in ``{PASS, FAIL}``.
* ``ANCHOR_WITHOUT_NEGATIVE_CASE`` / ``ANCHOR_WITHOUT_POSITIVE_CASE`` -- an
  anchor holding only one polarity cannot detect a constant judge: always-pass
  needs known-false canaries to be caught, always-fail needs known-true ones.
* ``ANCHOR_READABLE_BY_JUDGE:<token>`` -- the kill condition of the ranked
  plan, made executable: the judge's own source must not mention a label token
  (``expected_verdict``, ``replay_equals_live``, or a replay ``status`` name).
  The judge is invoked on redacted ``content`` only; a source that names the
  label domain is treated as reading it, comments included.
* ``JUDGE_OUTPUT_INVALID:<id>`` / ``JUDGE_ERROR:<id>`` -- the judge must
  return exactly ``PASS`` or ``FAIL`` for every anchor case, without raising.
* ``ALWAYS_PASS_COLLAPSE`` -- the judge passes EVERY known-false canary: the
  documented Who-Verifies collapse, reproduced at admission.
* ``ENDORSES_KNOWN_FALSE:<id>`` -- the judge passes some (not all) known-false
  canaries: one endorsement of a known-false claim is already a refusal; the
  index stores verdicts permanently (measured: 31.1% silent corruption when
  ungated), so a false pass is the expensive direction.  False *rejections*
  of known-true cases are deliberately not refusals: they cost capability,
  which the capability metrics already charge, and never poison permanence.
* ``ALWAYS_FAIL_COLLAPSE`` -- the judge fails every anchor case: a constant
  function carries no information either.
* ``NEVER_FAILS_HISTORY`` -- three or more recorded prior verdicts and not one
  failure: the Who-Verifies production signature (a verifier that never vetoes
  anything while downstream scores look fine).

Real anchor corpus
------------------
``anchor_from_replay_records`` adapts the 228 measured replay pairs of
``canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json`` -- real
execution feedback from this repository's own corpus at a pinned commit -- into
anchor cases: ground truth is the RUNNER's outcome (the recorded plan still
holds when replayed, or not), never a judge's opinion.  The content redacted to
the judge carries only site coordinates; the label fields stay with admission.

Standard library only; no model, no network, no weights.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_VERDICT_ANCHOR_ADMISSION_V1"

#: Judge-source tokens whose appearance means the judge names the label domain.
#: Comments count: source is source, and a judge that discusses the labels is
#: treated as able to reach them.
LABEL_TOKENS: tuple[str, ...] = (
    "expected_verdict",
    "replay_equals_live",
    "REPLAY_MATCHES_LIVE",
    "REPLAY_DIFFERS_BUT_HOLDS",
    "REPLAY_DOES_NOT_PARSE",
    "SILENT_CORRUPTION",
)

#: Runner outcomes in which the recorded plan still works when replayed.
HOLDING_STATUSES: frozenset[str] = frozenset(
    {"REPLAY_MATCHES_LIVE", "REPLAY_DIFFERS_BUT_HOLDS"}
)
NON_HOLDING_STATUSES: frozenset[str] = frozenset(
    {"REPLAY_DOES_NOT_PARSE", "SILENT_CORRUPTION"}
)

#: Prior verdicts required before a never-fails history means anything.
NEVER_FAILS_MIN_HISTORY = 3

_VERDICTS = frozenset({"PASS", "FAIL"})


class AnchorError(ValueError):
    """Malformed anchor input (raised only by the adapter, never by admission)."""


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().upper()


def anchor_from_replay_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Redact real replay records into anchor cases.

    ``content`` keeps only what an instrument may read (site coordinates);
    ``expected_verdict`` is the runner's own outcome, held by admission.
    """
    cases: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        status = rec.get("status")
        if status not in HOLDING_STATUSES | NON_HOLDING_STATUSES:
            raise AnchorError("ANCHOR_RECORD_STATUS_UNKNOWN:" + str(i))
        if "path" not in rec or "planned_line" not in rec or "live_line" not in rec:
            raise AnchorError("ANCHOR_RECORD_SITE_MISSING:" + str(i))
        cases.append(
            {
                "case_id": "replay#%d:%s#%s" % (i, rec.get("path"), rec.get("sample")),
                "content": {
                    "path": rec.get("path"),
                    "planned_line": rec.get("planned_line"),
                    "live_line": rec.get("live_line"),
                    "drift": rec.get("drift"),
                },
                "expected_verdict": "PASS" if status in HOLDING_STATUSES else "FAIL",
            }
        )
    return cases


def admission_errors(
    judge: Callable[[Mapping[str, Any]], str],
    anchor_cases: Sequence[Mapping[str, Any]],
    judge_history: Iterable[str] = (),
) -> list[str]:
    """Refuse a self-judged verdict loop unless it is anchored and discriminates."""
    errors: list[str] = []

    if not callable(judge):
        return ["JUDGE_NOT_CALLABLE"]

    if not anchor_cases:
        return ["ANCHOR_EMPTY"]

    seen_ids: set[str] = set()
    negatives = 0
    positives = 0
    for i, case in enumerate(anchor_cases):
        if not isinstance(case, Mapping):
            errors.append("ANCHOR_CASE_INVALID:%d" % i)
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append("ANCHOR_CASE_INVALID:%d" % i)
            continue
        if case_id in seen_ids:
            errors.append("ANCHOR_DUPLICATE_CASE_ID:" + case_id)
        seen_ids.add(case_id)
        if not isinstance(case.get("content"), Mapping):
            errors.append("ANCHOR_CASE_INVALID:" + case_id)
            continue
        verdict = _normalize(case.get("expected_verdict"))
        if verdict not in _VERDICTS:
            errors.append("ANCHOR_CASE_INVALID:" + case_id)
            continue
        if verdict == "FAIL":
            negatives += 1
        else:
            positives += 1

    if negatives == 0:
        errors.append("ANCHOR_WITHOUT_NEGATIVE_CASE")
    if positives == 0:
        errors.append("ANCHOR_WITHOUT_POSITIVE_CASE")
    if errors:
        return sorted(set(errors))

    try:
        source = inspect.getsource(judge)
    except (OSError, TypeError):
        return sorted(set(errors + ["ANCHOR_SOURCE_UNREADABLE"]))
    for token in LABEL_TOKENS:
        if token in source:
            # One token is already the kill condition; stop at the first.
            errors.append("ANCHOR_READABLE_BY_JUDGE:" + token)
            break

    judged: list[tuple[Mapping[str, Any], str]] = []
    for case in anchor_cases:
        case_id = case["case_id"]
        try:
            raw = judge(case["content"])
        except Exception:  # noqa: BLE001 - any crash is a refusal, fail closed
            errors.append("JUDGE_ERROR:" + case_id)
            continue
        verdict = _normalize(raw)
        if verdict not in _VERDICTS:
            errors.append("JUDGE_OUTPUT_INVALID:" + case_id)
            continue
        judged.append((case, verdict))

    if judged:
        false_passes = sorted(
            case["case_id"]
            for case, verdict in judged
            if verdict == "PASS" and case["expected_verdict"] == "FAIL"
        )
        known_fails = sum(1 for case, _ in judged if case["expected_verdict"] == "FAIL")
        if false_passes and len(false_passes) == known_fails:
            errors.append("ALWAYS_PASS_COLLAPSE")
        elif false_passes:
            errors.append("ENDORSES_KNOWN_FALSE:" + false_passes[0])
        all_verdicts = {verdict for _, verdict in judged}
        if all_verdicts == {"FAIL"} and len(judged) == len(anchor_cases):
            errors.append("ALWAYS_FAIL_COLLAPSE")

    history = [_normalize(v) for v in judge_history]
    if any(v not in _VERDICTS for v in history):
        errors.append("JUDGE_HISTORY_INVALID")
    elif len(history) >= NEVER_FAILS_MIN_HISTORY and not any(v == "FAIL" for v in history):
        errors.append("NEVER_FAILS_HISTORY")

    return sorted(set(errors))
