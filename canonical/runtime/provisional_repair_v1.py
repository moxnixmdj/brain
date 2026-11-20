"""Targeted refutation of a PROVISIONAL rule in the external store.

A PROVISIONAL applicability rule is the least-demanding survivor consistent
with the evidence used to buy it. It is allowed to be wrong. What it may NOT do
is silently stay wrong: when a real execution disagrees with the stored rule,
the rule must either narrow/weaken by the smallest computed amount or become
OPEN. This module never re-runs the original contrast search and never invents
a fact; it uses one support fact-set recorded with the rule plus the falsifying
state's own facts and exit status.

Authority NONE. Computed mechanism only; zero parameters, zero model calls.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import applicability_v1 as APP
from canonical.runtime import instant_condition_store_v1 as STORE

SCHEMA = "BRAIN_PROVISIONAL_REPAIR_V1"
REFUTED = "OPEN__REFUTED_WITHOUT_SUPPORT"
NO_RULE = "OPEN__NO_RULE_TO_REFUTE"
NARROWED = "REPAIRED__SCOPE_NARROWED"
WEAKENED = "REPAIRED__SCOPE_WEAKENED"
QUARANTINED = "OPEN__NO_COMPUTED_REPAIR"
UNCHANGED = "UNCHANGED__PREDICTION_MATCHED_OUTCOME"


class RepairError(ValueError):
    """Malformed input; ordinary uncertainty returns OPEN, never a guess."""


def attach_support(store: dict[str, Any], argv: Sequence[str],
                   support_facts: Iterable[str], *, source: Mapping[str, Any]) -> dict[str, Any]:
    """Record the fact-set of one genuine positive state alongside the rule."""
    key = STORE.action_key(argv)
    entry = store.get("entries", {}).get(key)
    if not isinstance(entry, Mapping):
        raise RepairError("NO_STORED_RULE_TO_SUPPORT")
    facts = sorted(set(str(item) for item in support_facts))
    if not facts:
        raise RepairError("SUPPORT_FACTS_REQUIRED")
    updated = dict(entry)
    updated["support_facts"] = facts
    updated["support_source"] = dict(source)
    store["entries"][key] = updated
    return updated


def _quarantine(entry: dict[str, Any], *, facts: Sequence[str], outcome: bool,
                reason: str) -> dict[str, Any]:
    updated = dict(entry)
    updated["condition_status"] = REFUTED
    updated["required"] = []
    updated.setdefault("refutations", []).append({
        "facts": sorted(facts), "outcome": outcome, "repair": QUARANTINED,
        "reason": reason,
    })
    return updated


def repair(store: dict[str, Any], argv: Sequence[str], observed_facts: Iterable[str],
           outcome: bool) -> dict[str, Any]:
    """Apply the smallest computed repair after one real disagreement."""
    key = STORE.action_key(argv)
    entry = store.get("entries", {}).get(key)
    if not isinstance(entry, Mapping):
        return {"status": NO_RULE, "repair": QUARANTINED, "changed": False}
    status = str(entry.get("condition_status") or "")
    if status not in {STORE.IDENTIFIED, STORE.PROVISIONAL}:
        return {"status": NO_RULE, "repair": QUARANTINED, "changed": False}

    facts = sorted(set(str(item) for item in observed_facts))
    required = tuple(str(item) for item in (entry.get("required") or ()))
    predicted = APP.admits(required, facts)
    if predicted == bool(outcome):
        return {"status": UNCHANGED, "repair": UNCHANGED, "changed": False,
                "required": list(required)}

    support = entry.get("support_facts")
    if not isinstance(support, list) or not support:
        updated = _quarantine(dict(entry), facts=facts, outcome=outcome,
                              reason="NO_SUPPORT_FACT_SET_RECORDED")
        store["entries"][key] = updated
        return {"status": REFUTED, "repair": QUARANTINED, "changed": True,
                "required": [], "reason": "NO_SUPPORT_FACT_SET_RECORDED"}

    before_status = status
    before_survivors = int((entry.get("source") or {}).get("survivor_count") or 0)
    added = None
    if predicted and not outcome:
        # Over-application: add ONE fact to the existing rule, never replace it.
        # A single counterexample cannot show that an already-required fact is
        # unnecessary; dropping it silently would buy a false sense of progress.
        boundary = APP.learn([(sorted(str(x) for x in support), True), (facts, False)])
        added = None
        for fact in boundary.most_general:
            candidate = tuple(sorted(set(required) | {str(fact)}))
            if (APP.admits(candidate, support) and not APP.admits(candidate, facts)):
                added = str(fact)
                new_required = candidate
                break
        if added is None or boundary.survivor_count <= 0:
            updated = _quarantine(dict(entry), facts=facts, outcome=outcome,
                                  reason="NO_SEPARATING_SURVIVOR")
            store["entries"][key] = updated
            return {"status": REFUTED, "repair": QUARANTINED, "changed": True,
                    "required": [], "reason": "NO_SEPARATING_SURVIVOR"}
        repair_kind = NARROWED
        after_status = STORE.PROVISIONAL
        after_survivors = boundary.survivor_count
    else:
        # Under-application: remove one required fact that this genuine
        # positive state does not have. Removing more than one is not minimal.
        absent = sorted(set(required) - set(facts))
        if not absent:
            updated = _quarantine(dict(entry), facts=facts, outcome=outcome,
                                  reason="NO_REQUIRED_FACT_TO_WEAKEN")
            store["entries"][key] = updated
            return {"status": REFUTED, "repair": QUARANTINED, "changed": True,
                    "required": [], "reason": "NO_REQUIRED_FACT_TO_WEAKEN"}
        new_required = tuple(fact for fact in required if fact != absent[0])
        repair_kind = WEAKENED
        after_status = STORE.PROVISIONAL
        after_survivors = before_survivors

    updated = copy.deepcopy(dict(entry))
    updated["condition_status"] = after_status
    updated["required"] = list(new_required)
    source = dict(updated.get("source") or {})
    source["survivor_count_before"] = before_survivors
    updated["source"] = source
    refutation = {
        "facts": facts, "outcome": bool(outcome), "repair": repair_kind,
        "required_before": list(required), "required_after": list(new_required),
        "status_before": before_status, "status_after": after_status,
    }
    if added is not None:
        # Size of the two-example version space over the observed vocabulary,
        # NOT the original search's evidence-backed survivor count.
        refutation["boundary_survivor_count"] = after_survivors
    updated.setdefault("refutations", []).append(refutation)
    store["entries"][key] = updated
    return {
        "status": after_status, "repair": repair_kind, "changed": True,
        "required": list(new_required),
        "required_before": list(required),
        "added_fact": added,
        "survivor_count_before": before_survivors,
        "survivor_count_after": after_survivors,
    }


def report(store: Mapping[str, Any], argv: Sequence[str]) -> dict[str, Any]:
    """Machine-readable confidence view; PROVISIONAL never looks identified."""
    key = STORE.action_key(argv)
    entry = store.get("entries", {}).get(key)
    if not isinstance(entry, Mapping):
        return {"status": STORE.UNKNOWN, "confidence": "NONE", "required": []}
    status = str(entry.get("condition_status") or "")
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    confidence = (
        "IDENTIFIED" if status == STORE.IDENTIFIED else
        "PROVISIONAL" if status == STORE.PROVISIONAL else "NONE"
    )
    return {
        "status": status,
        "confidence": confidence,
        "required": list(entry.get("required") or ()),
        "survivor_count": source.get("survivor_count"),
        "survivor_count_before": source.get("survivor_count_before"),
        "survivor_count_after": source.get("survivor_count_after"),
        "support_facts": list(entry.get("support_facts") or ()),
        "refutations": list(entry.get("refutations") or ()),
    }
