#!/usr/bin/env python3
"""Onboard a capability: demonstrate once, prove it generalises, inspect it, register it.

WHY THIS EXISTS
---------------
Everything built so far judges work that already happened. The number that actually limits what
this system can do is the denominator: how many capabilities have a demonstration, a held-out
instance and an inspector. Measured 2026-11-01 that was 43 of 152, and uninspected capabilities now
rank first in the hard slice, which means the sample feeding every self-measurement is dominated by
failures nobody can interpret.

So the work is a pipeline, not another gate:

    demonstrate once -> replay on a DIFFERENT instance -> independent inspection -> register

THE RULES, EACH ONE A REFUSAL
-----------------------------
  * no held-out instance, or one that binds the same parameters  -> FAIL_CLOSED__NO_HELDOUT /
    FAIL_CLOSED__HELDOUT_IDENTICAL_TO_THE_DEMONSTRATION. One instance cannot separate a procedure
    from a memorised instance, which is the oldest defect in this tree.
  * no inspector                                                 -> FAIL_CLOSED__NO_INSPECTOR.
    Registering a capability nobody can check is how 109 of them came to be uninspected.
  * the inspector passing on the demonstration but failing on the held-out instance ->
    FAIL_CLOSED__HELDOUT_UNVERIFIED. That is the exact shape of an overfit skill.

WHAT IT REPORTS
---------------
`throughput` (onboarded / attempted) and `heldout_survival` (onboarded / onboarded+failed). Two
numbers, because a factory that onboards a lot of skills that do not generalise is worse than a slow
one, and only reporting both keeps that visible.

This module wires the parts; it does not reimplement them. Nothing here calls a model or spends.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CAPABILITY_ONBOARDING_FACTORY_V1"

Demonstrate = Callable[[str], Mapping[str, Any]]
Register = Callable[[Mapping[str, Any]], None]
Inspector = Callable[[Mapping[str, Any]], tuple[bool, str]]


@dataclass
class Attempt:
    capability_id: str
    status: str
    reason: str = ""
    heldout_used: bool = False
    inspector: str = ""

    @property
    def onboarded(self) -> bool:
        return self.status == "ONBOARDED"

    @property
    def failed(self) -> bool:
        return not self.onboarded

    def as_row(self) -> dict[str, Any]:
        return {"capability_id": self.capability_id, "status": self.status,
                "reason": self.reason, "heldout_used": self.heldout_used,
                "inspector": self.inspector}


@dataclass
class Factory:
    """One pipeline, injected dependencies, every stage a refusal."""

    inspector_for: Callable[[str], Inspector | None]
    register: Register
    attempts: list[Attempt] = field(default_factory=list)

    def onboard(self, *, capability_id: str, demonstration: Mapping[str, Any],
                heldout: Mapping[str, Any] | None, demonstrate: Demonstrate | None = None
                ) -> Attempt:
        cid = str(capability_id or "").strip()
        if not cid:
            return self._record(Attempt("", "FAIL_CLOSED__CAPABILITY_ID_REQUIRED"))

        if not isinstance(demonstration, Mapping) or demonstration.get("ok") is not True:
            return self._record(Attempt(cid, "FAIL_CLOSED__DEMONSTRATION_DID_NOT_SUCCEED",
                                        str(demonstration.get("reason") if isinstance(
                                            demonstration, Mapping) else "")))

        if heldout is None:
            return self._record(Attempt(cid, "FAIL_CLOSED__NO_HELDOUT_INSTANCE",
                                        "HELDOUT_GOAL_REQUIRED_TO_QUALIFY_TRANSFER"))
        if heldout.get("binds") == demonstration.get("binds"):
            # Same parameters under another name: replay, not transfer.
            return self._record(Attempt(cid, "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_THE_DEMONSTRATION",
                                        "HELDOUT_BINDINGS_EQUAL_DEMONSTRATION_BINDINGS",
                                        heldout_used=True))

        inspector = self.inspector_for(cid)
        if inspector is None:
            return self._record(Attempt(cid, "FAIL_CLOSED__NO_INSPECTOR",
                                        "REGISTERING_AN_UNCHECKABLE_CAPABILITY_IS_THE_DEFECT",
                                        heldout_used=True))
        name = getattr(inspector, "__name__", "inspector")

        if demonstrate is not None:
            replayed = demonstrate(cid)
            if not isinstance(replayed, Mapping) or replayed.get("ok") is not True:
                return self._record(Attempt(cid, "FAIL_CLOSED__DEMONSTRATION_DID_NOT_REPLAY",
                                            str(replayed.get("reason") if isinstance(
                                                replayed, Mapping) else ""),
                                            heldout_used=True))

        ok, reason = inspector(demonstration)
        if not ok:
            return self._record(Attempt(cid, "FAIL_CLOSED__DEMONSTRATION_UNVERIFIED",
                                        str(reason), heldout_used=True, inspector=name))
        ok, reason = inspector(heldout)
        if not ok:
            # The skill replays the instance it was shown and fails a different one.
            return self._record(Attempt(cid, "FAIL_CLOSED__HELDOUT_UNVERIFIED",
                                        str(reason), heldout_used=True, inspector=name))

        self.register({
            "capability_id": cid,
            "heldout_bindings": heldout.get("binds"),
            "inspector": name,
            "heldout_verified": True,
        })
        return self._record(Attempt(cid, "ONBOARDED", "", heldout_used=True, inspector=name))

    def _record(self, attempt: Attempt) -> Attempt:
        self.attempts.append(attempt)
        return attempt

    def metrics(self) -> dict[str, Any]:
        total = len(self.attempts)
        onboarded = sum(1 for a in self.attempts if a.onboarded)
        failures = total - onboarded
        return {
            "schema": SCHEMA,
            "attempted": total,
            "onboarded": onboarded,
            "throughput": round(onboarded / total, 4) if total else 0.0,
            "heldout_survival": (round(onboarded / (onboarded + self._heldout_failures()), 4)
                                 if (onboarded + self._heldout_failures()) else 0.0),
            "refusals_by_status": self._by_status(),
        }

    def _heldout_failures(self) -> int:
        return sum(1 for a in self.attempts
                   if a.status.startswith("FAIL_CLOSED__HELDOUT"))

    def _by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for attempt in self.attempts:
            counts[attempt.status] = counts.get(attempt.status, 0) + 1
        return counts
