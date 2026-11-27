"""Attribute a task to one of a repository's standing law violations.

The oracle reports the repository's *debt*: several things it promised and does not deliver. A task
names one of them, and in the blind setting the only thing naming it is the issue text — the one
channel that is neither the fix nor a model call.

The signal is lexical and structural, deliberately: identifiers the issue mentions (`unregister()`,
`list_plugin_distinfo`), file paths it points at, and the vocabulary of the law that fired. No
embeddings, no paraphrase matching — a paraphrase model would be a runtime model call, and a
bag-of-tokens is honest about what it can and cannot separate.

The known limit is measured, not hidden: two defects that live in the *same function* cannot be
separated by identifier overlap, because the issue names the function and both defects sit there.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

__all__ = ["issue_signals", "score_violation", "rank_violations", "Attribution"]

_CODE_SPAN = re.compile(r"`([^`]+)`")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_CALL = re.compile(r"([A-Za-z_][A-Za-z0-9_]{2,})\s*\(")
_PATHISH = re.compile(r"\b[\w./-]+\.(?:py|c|h|js|ts|rst|md)\b")
_CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")

# Words that carry no attribution signal in any repository.
_STOP = frozenset(
    """
    the and for with that this from when what which while would should could have has had
    was were are not but you your our their they them then than there here into onto over
    under about after before because been being does did doing done also just only more most
    some such very can will may might must shall one two three fix fixes fixed issue report
    proposed proposal behavior behaviour change changes instead silently returns return
    """.split()
)


def issue_signals(text: str) -> dict[str, float]:
    """Weighted identifier signals from an issue, without reading anything but its own words.

    Code spans outrank plain words (an issue that writes `unregister()` means that function), and a
    file path outranks both (it narrows the search to one module).
    """
    signals: dict[str, float] = {}
    if not text:
        return signals
    for span in _CODE_SPAN.findall(text):
        for name in _IDENT.findall(span) + [span.strip()]:
            if len(name) >= 3 and name.lower() not in _STOP:
                signals[name] = max(signals.get(name, 0.0), 3.0)
    for path in _PATHISH.findall(text):
        signals[path] = max(signals.get(path, 0.0), 4.0)
    for call in _CALL.findall(text):
        if call.lower() not in _STOP:
            signals[call] = max(signals.get(call, 0.0), 2.5)
    for camel in _CAMEL.findall(text):
        signals[camel] = max(signals.get(camel, 0.0), 1.5)
    for word in _IDENT.findall(text):
        low = word.lower()
        if low in _STOP or len(word) < 4:
            continue
        signals.setdefault(word, 1.0)
    return signals


def _names_of(violation: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("where", "getter", "method", "file", "rel_path"):
        value = violation.get(key)
        if not isinstance(value, str):
            continue
        for part in re.split(r"[.\s]+", value):
            if part:
                names.add(part)
        names.add(value)
    return names


def score_violation(violation: Mapping[str, Any], signals: Mapping[str, float]) -> float:
    """Sum of the weights of the issue signals that the violation's own names carry."""
    names = _names_of(violation)
    scored = 0.0
    for name, weight in signals.items():
        if name in names:
            scored += weight
            continue
        # `list_plugin_distinfo()` in the issue vs `list_plugin_distinfo` on the violation, or the
        # other way round: compare the identifier without a call suffix.
        bare = name.split("(")[0].strip("`")
        if bare and (bare in names or any(bare == n.split(".")[-1] for n in names)):
            scored += weight * 0.8
    if violation.get("law"):
        law = str(violation["law"])
        signals_law = signals.get(law, 0.0)
        # An issue that says "assert" or "trailing whitespace" is naming a law, not a symbol; the
        # law's own words are evidence, at half weight because word matches are weaker than names.
        for word in law.split("_"):
            if len(word) >= 4 and word in {k.lower() for k in signals}:
                signals_law += 0.5
        scored += signals_law * 0.5
    return round(scored, 2)


class Attribution(dict):
    """One ranked violation, with the evidence that ranked it."""

    @property
    def where(self) -> str:
        return str(self.get("where") or "")

    @property
    def score(self) -> float:
        return float(self.get("score") or 0.0)


def rank_violations(
    violations: Sequence[Mapping[str, Any]],
    issue_text: str,
) -> list[Attribution]:
    """Rank standing violations by how much of the issue's vocabulary they carry.

    Ties are broken by the violation's own order (law order is stable), never by recency or file
    order: a tie means the issue does not separate them, and inventing a separator would be a guess.
    """
    signals = issue_signals(issue_text)
    scored: list[Attribution] = []
    for index, violation in enumerate(violations):
        item = Attribution(violation)
        item["score"] = score_violation(violation, signals)
        item["order"] = index
        matched = sorted(
            name for name in signals
            if name.split("(")[0].strip("`") in _names_of(violation)
            or any(name.split("(")[0].strip("`") == n.split(".")[-1] for n in _names_of(violation))
        )
        item["evidence"] = matched[:6]
        scored.append(item)
    scored.sort(key=lambda v: (-v.score, v["order"]))
    return scored


def attributable(violations: Sequence[Mapping[str, Any]], issue_text: str) -> bool:
    """True when at least one violation shares any signal with the issue."""
    return any(score_violation(v, issue_signals(issue_text)) > 0 for v in violations)


def summarise(ranked: Iterable[Mapping[str, Any]], top: int = 3) -> list[str]:
    return [f"{v.get('where')} :: {v.get('score')} :: {v.get('evidence')}" for v in list(ranked)[:top]]


def self_check() -> dict[str, Any]:
    """Verify violation attribution ranks matching issue symbols and abstains on unrelated text."""
    violations = [
        {"law": "remove_argument_vanishes", "cls": "Cache", "method": "remove_item", "target": "Cache.remove_item"},
        {"law": "round_trip", "cls": "Codec", "method": "encode", "target": "Codec.encode"},
    ]
    ranked = rank_violations(violations, "Cache.remove_item leaves stale entries after remove_item() is called")
    unrelated = attributable(violations, "What is the weather in Paris tomorrow?")
    top_ok = bool(ranked) and "remove_item" in str(ranked[0]) and ranked[0].score > 0.0
    ok = top_ok and (unrelated is False)
    return {
        "verdict": "SELF_CHECK_PASS" if ok else "SELF_CHECK_FAIL",
        "top_ranked_ok": top_ok,
        "unrelated_abstained": unrelated is False,
    }
