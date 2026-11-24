"""The witness is the object the action produced, checked against what the goal named.

Three defects were measured in `A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_
20261203_V1.md`: a page's cited flag is (1) never run, (2) vacuous on 281 of 370 pages, and
(3) unable to say WHICH object the action touched -- 8 of 8 probes accepted a decoy the
action never touched. Adding a blacklist of destroying flags fixes (1) for one machine and
fixes none of (2) or (3); the round's own conclusion was to *fill the citation from the room*.

This module is that wire, and it is deliberately not a new check. A check stays whatever
read-only program the environment already had. What changes is what the check is allowed to
witness:

    a check result is credited ONLY for a path whose BYTES this action changed.

Computed from the room, never from prose:

  * `delta_of` compares every file's content digest before and after the action. A kind map
    is blind to an overwrite (`shred -v` keeps a file of the same kind); bytes are not.
  * `targets_of` reads back the paths the checks were ACTUALLY run on, separating the object
    asserted about from a source a comparison merely reads (`bytes_equal`'s `left`).
  * `witness` binds held checks to delta. A held check on an untouched object is an
    INVARIANT (e.g. "src must stay a directory"), not evidence, and never a witness. A held
    check with no bound object is a FALSE DONE: the goal was already true before the action.
    A same-kind decoy the action also changed makes the witness AMBIGUOUS.

The two error directions the frontier measures are both represented here: a check that
accepts everything cannot credit an untouched decoy, and a check that rejects everything
cannot be helped -- it simply never witnesses. Nothing here invents a program name, stores a
fact, calls a model, or touches the network. The rule is a mechanism, so it lives in code and
not in the external knowledge store.

Authority: NONE__PRODUCER_RUN_SANDBOX. No capability credit, no benchmark result.
"""

from __future__ import annotations

import hashlib
import pathlib
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_ROOM_WITNESS_V1"

# These are fields of the check RECEIPT, not names of programs. They say where the check
# looked, which is exactly the value a page's prose cannot supply.
_TARGET_KEYS = ("path", "right", "archive")
_SOURCE_KEYS = ("left",)


def digest(root: pathlib.Path) -> dict[str, str]:
    """Every regular file in the room, by content. A kind map is blind to an overwrite."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(root).as_posix()
            try:
                out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                out[rel] = "<unreadable>"
    return out


def delta_of(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, Any]:
    """The action's effect, derived from bytes rather than from a page's sentence."""
    changed = sorted(p for p in set(before) | set(after)
                     if before.get(p) != after.get(p))
    return {
        "changed": changed,
        "created": [p for p in changed if p not in before],
        "removed": [p for p in changed if p not in after],
        "overwritten": [p for p in changed if p in before and p in after],
        # "produced" includes an overwrite: the object the step made may have had a name before.
        "produced": [p for p in changed if p in after],
        "consumed": [p for p in changed if p in before],
    }


def targets_of(checks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Which path each check was actually run on, and which path it only read as a source.

    `archive_contains` records every archive it tried in `tried`; those are targets too. A
    check that names no object cannot witness anything, and is reported as such rather than
    being silently skipped.
    """
    rows: list[dict[str, Any]] = []
    for check in checks:
        targets: list[str] = []
        sources: list[str] = []
        for key in _TARGET_KEYS:
            value = check.get(key)
            if isinstance(value, str) and value:
                targets.append(value)
        for key in _SOURCE_KEYS:
            value = check.get(key)
            if isinstance(value, str) and value:
                sources.append(value)
        tried = check.get("tried")
        if isinstance(tried, Iterable):
            for row in tried:
                if isinstance(row, Mapping):
                    value = row.get("archive")
                    if isinstance(value, str) and value and value not in targets:
                        targets.append(value)
        rows.append({"check": check.get("check", "<unnamed>"),
                     "held": bool(check.get("held")),
                     "targets": sorted(set(targets)),
                     "sources": sorted(set(sources))})
    return rows


def witness(before: Mapping[str, str], after: Mapping[str, str],
            checks: Sequence[Mapping[str, Any]], *,
            decoys: Iterable[str] = (),
            argv: Sequence[str] = (),
            reread: Callable[[str], str] | None = None) -> dict[str, Any]:
    """Bind held checks to the bytes this action changed, or refuse.

    `reread`, when supplied, re-reads each bound object at verification time. A digest that
    moved between `after` and the check is state drift, and the verdict is refused instead of
    being reported on stale bytes.
    """
    delta = delta_of(before, after)
    changed = set(delta["changed"])
    decoys = sorted(set(decoys))
    rows: list[dict[str, Any]] = []
    for row in targets_of(checks):
        touched = [p for p in row["targets"] if p in changed]
        if not row["held"]:
            kind = "NOT_HELD"
        elif touched:
            kind = "WITNESSED"
        elif row["targets"]:
            kind = "INVARIANT"          # held on an object this action never touched
        else:
            kind = "REFUSED__CHECK_NAMES_NO_OBJECT"
        rows.append({**row, "touched": touched, "kind": kind})

    bound = sorted({p for row in rows if row["kind"] == "WITNESSED"
                    for p in row["touched"]})
    decoys_in_delta = sorted(set(decoys) & changed)
    drift: list[str] = []
    if reread is not None:
        for path in bound:
            if path in after:
                # A produced or overwritten object must still hold the bytes the action left.
                try:
                    if reread(path) != after[path]:
                        drift.append(path)
                except OSError:
                    drift.append(path)
            else:
                # A REMOVED object is a legitimate witness (N10/N11: "so the old name is
                # gone"). Its expected state is ABSENCE, not a digest. Treating absence as a
                # digest mismatch was the false drift that refused both removal needs.
                try:
                    reread(path)
                    drift.append(path)          # it came back
                except OSError:
                    pass                         # still absent, as the action left it

    if any(row["kind"] == "REFUSED__CHECK_NAMES_NO_OBJECT" for row in rows):
        status, reason = ("REFUSED__CHECK_NAMES_NO_OBJECT",
                          "a held check names no object, so it cannot be bound to the action")
    elif not bound and not any(row["kind"] == "INVARIANT" for row in rows):
        # An all-reject verifier is a different defect from a false done, and the frontier
        # measures them separately (VerifierBench: false rejections concentrate in all-reject
        # verifiers). Reporting both as "the goal was already true" would hide that.
        status, reason = ("REFUSED__NO_HELD_CHECK",
                          "no check held; an all-reject check cannot witness a valid action")
    elif not bound:
        status, reason = ("REFUSED__GOAL_HELD_BEFORE_THE_ACTION",
                          "no held check is bound to a byte the action changed; a pre-existing "
                          "object or a no-op cannot be claimed as this action's success")
    elif decoys_in_delta:
        status, reason = ("REFUSED__AMBIGUOUS_WITNESS",
                          "the action also changed a same-kind decoy, so the goal's object is "
                          "not identified among the objects produced")
    elif drift:
        status, reason = ("REFUSED__STATE_DRIFT",
                          "a bound object's bytes changed between the action and the check")
    else:
        status, reason = ("WITNESSED",
                          "a held check was executed on an object whose bytes this action changed")

    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "held": status == "WITNESSED",
        "bound": bound,
        "argv": list(argv),
        "delta": delta,
        "decoys": decoys,
        "decoys_in_delta": decoys_in_delta,
        "drift": drift,
        "rows": rows,
        "witnessed": sum(1 for row in rows if row["kind"] == "WITNESSED"),
        "invariants": sum(1 for row in rows if row["kind"] == "INVARIANT"),
        "not_held": sum(1 for row in rows if row["kind"] == "NOT_HELD"),
    }


def status_of(before: Mapping[str, str], after: Mapping[str, str],
              accepted: bool) -> dict[str, Any]:
    """The status the operator reads, derived from bytes.

    The shipped round compared *kinds* and reported 7 of 8 accepted destroyers as
    `ACCEPTED_INERT` -- "succeeded and changed nothing" -- for a file whose bytes were gone.
    A run is CHANGED exactly when a content digest moved, whatever the object's name or kind.
    """
    delta = delta_of(before, after)
    status = ("REFUSED" if not accepted else
              "ACCEPTED_CHANGED" if delta["changed"] else "ACCEPTED_INERT")
    return {"status": status, "reason": ("a content digest moved" if delta["changed"]
                                         else "no content digest moved"),
            "changed": delta["changed"]}
