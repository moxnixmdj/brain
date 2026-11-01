#!/usr/bin/env python3
"""Derive an inspector from the environment's own checker, then try to kill it.

WHY THIS EXISTS
---------------
Every plan that grows coverage by writing inspectors by hand has a throughput of one agent-session
per capability. That is why coverage sat at 43 of 152 while the measurement was argued about. The
asset this tree already has is that the *environment* usually contains a checker -- a test, a
validator, a verifier script -- that states what a correct result looks like. `look_before_v1`
already reads those (`required_by`, `produces`, `satisfies`). This module turns that read into an
inspector, and -- the part that matters -- insists the inspector first be shown able to fail.

THE RULE
--------
A derived inspector is registered only if, on the same corpus:

  * the positive case passes (the real artifact satisfies what the checker demands), and
  * the paired negative control is REFUSED (a decoy that differs in one required respect).

If the derivation is over-permissive it will accept the decoy, and that is exactly the point: an
inspector that cannot reject is decoration, and it must not enter the registry. The negative control
is the gate; no human review step is needed, which is what makes this a flywheel instead of a queue.

This is deliberately narrow. It derives checks that are *lexical facts about the environment's own
checker*, so it can only ever prove "the artifact contains what the environment says it must". It
does not infer semantics, and a capability whose environment has no checker cannot be derived at
all -- it stays refused, which is the correct default rather than a guessed inspector.

Nothing here calls a model. Nothing here spends.
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DERIVED_INSPECTOR_FLYWHEEL_V1"
_PATHY = re.compile(
    r"[\w./-]*/[\w./-]+|\b[\w-]+\.(?:txt|json|log|out|csv|md|lock|ya?ml|toml|png|xlsx|docx|pdf)\b")


class DerivationError(ValueError):
    """The environment does not state enough to derive a check from."""


@dataclass(frozen=True)
class Requirement:
    literal: str
    source: str

    def as_row(self) -> dict[str, Any]:
        return {"literal": self.literal, "source": self.source}


@dataclass
class Derivation:
    capability_id: str
    requirements: list[Requirement]
    checker_paths: list[str]
    refused: bool = False
    reason: str = ""

    @property
    def inspector_name(self) -> str:
        return f"derived_inspector__{self.capability_id}"

    def build(self) -> Callable[[Mapping[str, Any]], tuple[bool, str]]:
        """A real inspector: it re-reads the artifact and compares to the derived literals."""
        wanted = [r.literal for r in self.requirements]
        sources = list(self.checker_paths)

        def inspector(payload: Mapping[str, Any]) -> tuple[bool, str]:
            root = payload.get("root")
            artifact = payload.get("artifact")
            if not isinstance(artifact, str) or not artifact.strip():
                return False, "DERIVED_INSPECTOR_ARTIFACT_NOT_NAMED"
            base = pathlib.Path(root or ".").resolve()
            path = (base / artifact).resolve()
            try:
                path.relative_to(base)
            except ValueError:
                return False, "DERIVED_INSPECTOR_ARTIFACT_OUTSIDE_ROOT"
            if not path.is_file():
                return False, "DERIVED_INSPECTOR_ARTIFACT_ABSENT"
            try:
                text = path.read_text(errors="replace")
            except OSError:
                return False, "DERIVED_INSPECTOR_ARTIFACT_UNREADABLE"
            missing = [w for w in wanted if w not in text]
            if missing:
                return False, "DERIVED_INSPECTOR_REQUIRED_CONTENT_MISSING:" + ",".join(missing[:4])
            # The checker must still be where it was when the requirement was read; a moved or
            # deleted checker means the derivation is stale and must not silently keep passing.
            for src in sources:
                if not (base / src).is_file():
                    return False, "DERIVED_INSPECTOR_CHECKER_MISSING:" + src
            return True, ""

        inspector.__name__ = self.inspector_name
        return inspector

    def as_row(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "inspector": self.inspector_name,
            "requirements": [r.as_row() for r in self.requirements],
            "checker_paths": list(self.checker_paths),
            "refused": self.refused,
            "reason": self.reason,
        }


# Short literals are noise: a checker containing print("ok") would otherwise be "derived" into
# requiring the string "ok" in the artifact. Measured while writing this module's own tests.
MIN_LITERAL = 6
_NOISE = {"true", "false", "none", "utf-8", "text/plain", "application/json"}


def _literals(source: pathlib.Path) -> list[str]:
    """Quoted literals in a checker, preferring content over paths (same rule as look_before)."""
    text = source.read_text(errors="replace")
    out: list[str] = []
    for match in re.finditer(r"""(['"])((?:(?!\1).){2,200}?)\1""", text):
        lit = match.group(2)
        if _PATHY.fullmatch(lit) or len(lit) < MIN_LITERAL or lit.casefold() in _NOISE:
            continue
        out.append(lit)
    return out


def derive(*, capability_id: str, checker_paths: Sequence[str], root: pathlib.Path) -> Derivation:
    """Read the environment's checkers and produce a falsifiable inspector."""
    base = pathlib.Path(root).resolve()
    found: list[Requirement] = []
    usable: list[str] = []
    for rel in checker_paths:
        path = (base / rel).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            continue
        if not path.is_file():
            continue
        usable.append(str(pathlib.PurePosixPath(rel)))
        for lit in _literals(path):
            found.append(Requirement(lit, rel))
    if not usable:
        return Derivation(capability_id, [], [], refused=True, reason="NO_CHECKER_IN_THE_ENVIRONMENT")
    # Deterministic and narrow: longest first, deduplicated, capped. A derivation that hoovers up
    # every literal is not a check, it is a copy of the checker.
    seen: set[str] = set()
    picked: list[Requirement] = []
    for req in sorted(found, key=lambda r: (-len(r.literal), r.literal)):
        if req.literal in seen:
            continue
        seen.add(req.literal)
        picked.append(req)
        if len(picked) >= 8:
            break
    if not picked:
        return Derivation(capability_id, [], usable, refused=True,
                          reason="CHECKER_STATES_NO_CONTENT_REQUIREMENT")
    return Derivation(capability_id, picked, sorted(usable))


@dataclass
class Flight:
    """One derivation, falsified against a paired negative control, then registered or refused."""

    registry: dict[str, Any] = field(default_factory=dict)
    flights: list[dict[str, Any]] = field(default_factory=list)

    def attempt(self, *, derivation: Derivation, positive: Mapping[str, Any],
                negative: Mapping[str, Any]) -> dict[str, Any]:
        if derivation.refused:
            return self._record(derivation.capability_id, "REFUSED__NOTHING_TO_DERIVE",
                                derivation.reason)
        inspector = derivation.build()
        ok_pos, pos_reason = inspector(positive)
        if not ok_pos:
            return self._record(derivation.capability_id, "REFUSED__DERIVATION_DOES_NOT_HOLD_ON_THE_POSITIVE",
                                pos_reason, derivation)
        ok_neg, neg_reason = inspector(negative)
        if ok_neg:
            # The inspector accepted the decoy. It cannot reject, so it is decoration.
            return self._record(derivation.capability_id, "REFUSED__INSPECTOR_ACCEPTED_THE_NEGATIVE_CONTROL",
                                "DERIVED_INSPECTOR_CANNOT_FAIL", derivation)
        self.registry[derivation.capability_id] = {
            "inspector": derivation.inspector_name,
            "requirements": [r.literal for r in derivation.requirements],
            "checker_paths": list(derivation.checker_paths),
            "falsified_by": "negative control refused: " + neg_reason,
        }
        return self._record(derivation.capability_id, "REGISTERED", neg_reason, derivation)

    def _record(self, cid: str, status: str, reason: str,
                derivation: Derivation | None = None) -> dict[str, Any]:
        row = {"capability_id": cid, "status": status, "reason": reason,
               "derivation": derivation.as_row() if derivation else None}
        self.flights.append(row)
        return row

    def metrics(self) -> dict[str, Any]:
        total = len(self.flights)
        registered = sum(1 for f in self.flights if f["status"] == "REGISTERED")
        accepted_negative = sum(
            1 for f in self.flights
            if f["status"] == "REFUSED__INSPECTOR_ACCEPTED_THE_NEGATIVE_CONTROL")
        return {
            "schema": SCHEMA,
            "attempted": total,
            "registered": registered,
            "throughput": round(registered / total, 4) if total else 0.0,
            # The number that must stay zero: a derived inspector that cannot fail.
            "over_permissive_derivations": accepted_negative,
            "refusals_by_status": _tally(self.flights),
        }


def _tally(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status"))
        counts[key] = counts.get(key, 0) + 1
    return counts
