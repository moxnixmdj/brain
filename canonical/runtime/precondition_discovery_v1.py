#!/usr/bin/env python3
"""Discover an observable that separates worlds the current facts call identical.

THE MEASURED WALL. Two real directories with IDENTICAL sensed facts produced opposite real outcomes:
one chain succeeded, one failed `DOCX_INTENT_SIDECAR_MISSING`. The cause -- a `.docx.intent.json`
sidecar next to the document -- has no fact in `world_probe_v1`'s vocabulary. To the learner those
two worlds are one point; to the executor they are different worlds. `applicability_v1` correctly
answers INCONSISTENT, and `vocabulary_gap` now returns the witness pair. This module aims a repair
at that witness.

WHY NOT LEARN IT FROM MORE RUNS. No number of runs helps: every run reports the same fact vector, so
the evidence stays contradictory forever. The missing thing is an OBSERVABLE, not an observation.
That is the same lesson `vocabulary_induction_v1` records for numeric families -- recover vocabulary
from evidence that FITS, and report NO_EVIDENCE rather than guess -- applied to file predicates.

WHAT MAKES A CANDIDATE LEGITIMATE. A candidate here is a FILE-NAME SUFFIX predicate: "some file under
the root ends with S". Three properties are required before it is reported, and all three are checked
against real directories, never asserted:

  1. SEPARATION   -- true in every supplied success world, false in every supplied failure world.
  2. GENERALITY   -- the SHORTEST separating suffix is preferred, so the predicate is the least
                     demanding one that fits. Setting the whole filename as the "predicate" would
                     separate perfectly and generalise to nothing: it is a fingerprint of one world.
  3. RENAME STABILITY -- the caller may supply held-out worlds whose files are named differently.
                     A candidate that only works for the name it was discovered on is rejected.

WHAT THIS REFUSES TO DO. It does not register a fact, edit the sensor, or change any admission
decision. Adopting a new observable into `world_probe_v1` is a governance act with its own evidence
bar; this returns verified candidates and the worlds they were verified on. It never invents a
predicate that no file exhibits, and it reports NO_CANDIDATE rather than guessing when the worlds
differ by nothing observable.

Authority NONE. Reads directory listings only. Writes nothing, executes nothing. $0, no model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_PRECONDITION_DISCOVERY_V1"

NO_WORLDS = "NO_WORLDS_SUPPLIED"
NO_DIFFERENCE = "NO_OBSERVABLE_DIFFERENCE_BETWEEN_THE_WORLDS"
NO_CANDIDATE = "NO_SUFFIX_SEPARATES_EVERY_SUPPLIED_WORLD"
DISCOVERED = "DISCOVERED__A_VERIFIED_SUFFIX_SEPARATES_THE_WORLDS"

_SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", ".next", ".cache", ".arena", ".tox", ".nox", "target", "out",
})
_MAX_FILES = 200_000
#: A suffix must keep at least this many characters of extension to be a kind rather than a
#: fragment of a name. ".json" qualifies; "n" does not.
_MIN_SUFFIX_PARTS = 2


def _files(root) -> tuple[str, ...]:
    root = Path(root)
    out: list[str] = []
    stack = [str(root)]
    while stack and len(out) < _MAX_FILES:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    if entry.name in _SKIP_DIRS:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        out.append(entry.name.lower())
        except OSError:
            continue
    return tuple(sorted(set(out)))


def _suffixes(name: str) -> tuple[str, ...]:
    """Candidate kind suffixes of a file name, shortest first.

    `report.docx.intent.json` -> `.json`, `.intent.json`, `.docx.intent.json`, ...
    The whole bare name is never offered: matching one exact file name is a fingerprint, not a kind.
    """
    parts = name.split(".")
    out = []
    for count in range(1, len(parts)):
        if count < _MIN_SUFFIX_PARTS:
            continue
        out.append("." + ".".join(parts[-count:]))
    return tuple(out)


def holds(root, suffix: str) -> bool:
    """The candidate observable, evaluated against a real directory."""
    suffix = str(suffix).lower()
    return any(name.endswith(suffix) for name in _files(root))


@dataclass(frozen=True)
class Discovery:
    schema: str
    status: str
    suffix: str | None
    #: Suffixes that separated the discovery worlds, shortest first.
    separating: tuple[str, ...]
    #: Per-world evaluation of the returned suffix, including any held-out worlds.
    verified_on: tuple[dict[str, Any], ...]
    reason: str

    @property
    def found(self) -> bool:
        return self.status == DISCOVERED

    def as_row(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "suffix": self.suffix,
            "separating": list(self.separating),
            "verified_on": [dict(v) for v in self.verified_on],
            "reason": self.reason,
        }


def discover(
    success_roots: Sequence[Any],
    failure_roots: Sequence[Any],
    *,
    held_out_success: Sequence[Any] = (),
    held_out_failure: Sequence[Any] = (),
) -> Discovery:
    """Find the least demanding file suffix true in every success world and false in every failure.

    Held-out worlds are checked but never used to CHOOSE the suffix, so passing them is a real
    falsification rather than a fit. A suffix that separates the discovery worlds and then fails a
    held-out world is discarded, not quietly kept.
    """
    def _stop(status: str, reason: str, separating=()) -> Discovery:
        return Discovery(SCHEMA, status, None, tuple(separating), (), reason)

    if not success_roots or not failure_roots:
        return _stop(NO_WORLDS, "BOTH_A_SUCCESS_AND_A_FAILURE_WORLD_ARE_REQUIRED")

    yes = [_files(r) for r in success_roots]
    no = [_files(r) for r in failure_roots]
    # Only suffixes exhibited by a success world can possibly be required there.
    pool: set[str] = set()
    for names in yes:
        for name in names:
            pool.update(_suffixes(name))
    if not pool:
        return _stop(NO_DIFFERENCE, "NO_FILE_SUFFIXES_IN_THE_SUCCESS_WORLDS")

    def _separates(suffix: str) -> bool:
        return (all(any(n.endswith(suffix) for n in names) for names in yes)
                and not any(any(n.endswith(suffix) for n in names) for names in no))

    separating = sorted({s for s in pool if _separates(s)}, key=lambda s: (s.count("."), len(s), s))
    if not separating:
        return _stop(NO_CANDIDATE, "EVERY_CANDIDATE_IS_TRUE_IN_A_FAILURE_WORLD_OR_FALSE_IN_A_SUCCESS")

    checks = []
    for suffix in separating:
        rows = []
        ok = True
        for label, roots, expected in (
            ("success", success_roots, True),
            ("failure", failure_roots, False),
            ("held_out_success", held_out_success, True),
            ("held_out_failure", held_out_failure, False),
        ):
            for root in roots:
                value = holds(root, suffix)
                rows.append({"class": label, "root": Path(root).name,
                             "holds": bool(value), "expected": expected,
                             "correct": bool(value) == expected})
                if bool(value) != expected:
                    ok = False
        if ok:
            return Discovery(SCHEMA, DISCOVERED, suffix, tuple(separating), tuple(rows),
                             "SHORTEST_SUFFIX_THAT_SEPARATES_EVERY_SUPPLIED_WORLD")
        checks.extend(rows)

    return Discovery(SCHEMA, NO_CANDIDATE, None, tuple(separating), tuple(checks),
                     "EVERY_SEPARATING_SUFFIX_FAILED_A_HELD_OUT_WORLD")
