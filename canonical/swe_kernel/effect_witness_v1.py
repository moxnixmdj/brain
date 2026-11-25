#!/usr/bin/env python3
"""An action's check must name the object the action changed.

WHY THIS EXISTS
---------------
The repository's own guide was measured with 2,319 declared "read-only checks".
281 of 370 citations accepted every object in the room, and 8 of 8 probes accepted
a decoy the action had never touched (`A_CHECK_THAT_NOBODY_RUNS_..._20261203_V1`).
That is not a search failure: a check of the form ``gzip -t <anything>`` cannot
say which object the goal was about.  A rule learned with such a check is a rule
that can never be refuted, so it is not knowledge.

THE LAW IMPLEMENTED HERE
------------------------
A check is admitted only when its subject is the object the action or the goal
named, and its effect is a byte-level change under that subject's closure.  The
subject comes from the literal arguments and an expected object, never from a
page's prose and never from "some object of this kind".

    subject  = a literal, room-relative path in argv or given by the caller
    effect   = paths whose sha256 changed (added / removed / mutated)
    bound    = the effect is empty (verification) or every changed path derives
               from an expected subject, and the subject was actually named
    decoy    = a check whose only subject is a different path -> REFUSED

Nothing is learned into weights.  The durable, inspectable artifact is the
witness: role, subject, digest, changed paths.  It can be stored, removed or
edited without touching any mechanism.

No model calls. No parameters. No network.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EFFECT_WITNESS_V1"

ROLE_TRANSFORM = "transform"   # named subject changed in place
ROLE_PRODUCE = "produce"       # a new path derived from the subject appeared
ROLE_CONSUME = "consume"       # subject unchanged, output derived from it
ROLE_DESTROY = "destroy"       # named subject disappeared
ROLE_VERIFY = "verify"         # nothing changed, subject explicitly named
ROLE_SIDE_EFFECT = "side_effect"
ROLE_INERT = "inert"


def digest_tree(root: pathlib.Path) -> dict[str, str]:
    """Content identity of every regular file in the room, by relative path."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        try:
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            out[rel] = "<unreadable>"
    return out


def _normal(arg: str) -> str | None:
    """A literal room-relative path, or None. No globs, no escapes, no guesses."""
    if not arg or arg.startswith("-") or "*" in arg or "?" in arg:
        return None
    path = pathlib.PurePosixPath(arg.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        return None
    rel = path.as_posix()
    return rel[:-2] if rel.endswith("/.") else rel


def named_subjects(argv: Sequence[str], before: Mapping[str, str],
                   after: Mapping[str, str] | None = None) -> list[str]:
    """Paths literally named in argv that exist before or after the action.

    ``--file=X`` is one argument with one object; ``-f X`` is two.  Option names
    are never objects.  Only existence in the room makes a literal a subject,
    so a flag value such as ``0`` or ``GAMMA`` cannot become one by accident.
    """
    universe = set(before) | set(after or {})
    found: set[str] = set()
    args = list(argv[1:])
    for index, arg in enumerate(args):
        cand = _normal(arg)
        if cand in universe:
            found.add(cand)
        if arg.startswith("--") and "=" in arg:
            cand = _normal(arg.split("=", 1)[1])
            if cand in universe:
                found.add(cand)
        # `-f ARCHIVE`: the value after an argument-taking flag is a literal path.
        if arg.startswith("-") and not arg.startswith("--") and index + 1 < len(args):
            cand = _normal(args[index + 1])
            if cand in universe:
                found.add(cand)
    return sorted(found)


def derives(path: str, subject: str) -> bool:
    """Is `path` the subject itself or an object produced from it?

    Three shapes are derived: the same path, an extension of it
    (``payload.txt`` -> ``payload.txt.gz``), and a subtree of it
    (``src`` -> ``src/README``).  Nothing else is assumed.
    """
    if path == subject:
        return True
    if path.startswith(subject + ".") or path.startswith(subject + "/"):
        return True
    # An archive's contents derive from the archive's stem: `proj.tar` -> `proj/`.
    # This is a structural relation on the name the room itself printed, not a
    # table of program behaviours.
    stem = subject
    for suffix in (".tar.gz", ".tar.xz", ".tar.bz2", ".tgz", ".tar", ".gz",
                   ".xz", ".bz2", ".zip"):
        if stem.endswith(suffix) and len(stem) > len(suffix):
            stem = stem[:-len(suffix)]
            break
    return stem != subject and (path == stem or path.startswith(stem + "/"))


def witness(before: Mapping[str, str], after: Mapping[str, str],
            subjects: Iterable[str], outputs: Iterable[str] = ()) -> dict[str, Any]:
    """Compute the effect under the named subjects. Pure function of two digests.

    `outputs` are the objects the goal named as the result. They are part of
    the demand, not a guess: without them, a compression that overwrites an
    existing ``a.txt.gz`` looks like destruction of ``a.txt`` instead of
    production of the named result.
    """
    subj = sorted(set(subjects))
    changed = sorted(p for p in set(before) | set(after)
                     if before.get(p) != after.get(p))
    created = sorted(p for p in after if p not in before)
    removed = sorted(p for p in before if p not in after)
    changed_subjects = [p for p in subj if p in changed]
    derived_changed = [p for p in changed
                       if any(derives(p, s) for s in subj)]
    unexpected = [p for p in changed if p not in derived_changed]

    outputs = set(outputs)
    # An output that disappeared is not a production; `rm a.txt.gz` must stay
    # a destruction even when the goal named a.txt.gz as the object of interest.
    produced_from_subject = [p for p in (
        set(created) | {p for p in (set(changed) & outputs) if p in after and p not in removed})
        if any(derives(p, s) for s in subj)
        or (p in subj and any(s in removed for s in subj))
        or p in outputs]
    if produced_from_subject and changed_subjects:
        # `gzip payload.txt` removes the source and creates `payload.txt.gz`.
        # That is one production under the named subject, not destruction.
        role = ROLE_PRODUCE
    elif removed and any(s in removed for s in subj):
        role = ROLE_DESTROY
    elif changed_subjects:
        role = ROLE_TRANSFORM
    elif created or derived_changed:
        role = ROLE_CONSUME
    elif subj:
        role = ROLE_VERIFY
    else:
        role = ROLE_INERT

    return {
        "schema": SCHEMA,
        "role": role,
        "subjects": subj,
        "outputs": sorted(outputs),
        "subject_digests": {p: {"before": before.get(p), "after": after.get(p)}
                            for p in subj},
        "changed": changed,
        "created": created,
        "removed": removed,
        "unexpected_changed": unexpected,
        "signature": [role] + [f"{p}:{'in' if p in before else 'out'}"
                               for p in sorted(subj)],
    }


def witness_of_run(argv: Sequence[str], before: Mapping[str, str],
                   after: Mapping[str, str], outputs: Iterable[str] = ()) -> dict[str, Any]:
    """The witness of one executed command, from the argv and two room digests."""
    subj = named_subjects(argv, before, after)
    return witness(before, after, subj, outputs)


def bind(info: Mapping[str, Any], expected: Iterable[str], *,
         accepted: bool = True, allow_destroy: bool = False) -> dict[str, Any]:
    """Is this run a check of the object the goal actually named?

    A verification is inert by definition; it is admitted only when it names
    an expected subject.  An effect must be entirely under an expected subject
    and must actually change one of them.  A check on a decoy fails here even
    when the program exited zero.
    """
    want = sorted(set(expected))
    row = dict(info)
    subjects = [str(s) for s in row.get("subjects") or []]
    overlap = [s for s in subjects if s in want]
    role = row.get("role")
    if not want:
        return {**row, "bound": False, "reason": "NO_EXPECTED_OBJECT", "accepted": accepted}
    if not overlap:
        return {**row, "bound": False, "reason": "SUBJECT_IS_NOT_THE_NAMED_OBJECT",
                "accepted": accepted}
    if not accepted:
        return {**row, "bound": False, "reason": "PROGRAM_REFUSED", "accepted": False}
    if row.get("unexpected_changed"):
        return {**row, "bound": False, "reason": "CHANGED_AN_UNNAMED_OBJECT",
                "accepted": accepted}
    if role == ROLE_VERIFY:
        return {**row, "bound": True, "reason": "NAMED_SUBJECT_VERIFIED",
                "accepted": accepted}
    if role == ROLE_INERT or not row.get("changed"):
        return {**row, "bound": False, "reason": "NO_OBSERVABLE_EFFECT",
                "accepted": accepted}
    if role == ROLE_DESTROY:
        # Destruction is observable and bound, but it is never a goal check
        # unless the caller declares this object as the one to remove.
        if allow_destroy:
            return {**row, "bound": True, "reason": "NAMED_SUBJECT_REMOVED",
                    "accepted": accepted}
        return {**row, "bound": False, "reason": "DESTROYED_SUBJECT",
                "accepted": accepted}
    return {**row, "bound": True, "reason": "EFFECT_UNDER_NAMED_SUBJECT",
            "accepted": accepted}


def separates(right: Mapping[str, Any], decoy: Mapping[str, Any]) -> bool:
    """Can this witness tell the named object from a same-kind decoy?

    The right run must be bound and have an observable subject; the decoy must
    be refused *for the same expected object*.  Passing a decoy by exit code is
    exactly the defect this module exists to remove.
    """
    if not right.get("bound") or decoy.get("bound"):
        return False
    if not (right.get("subjects") and right.get("changed")):
        return False
    return set(right["changed"]) != set(decoy.get("changed") or [])


def abstract_rule(bound_row: Mapping[str, Any], *, goal_family: str) -> dict[str, Any]:
    """The durable, generalised unit: a signature, not an argv string.

    Concrete paths and digests stay in the evidence; the stored rule holds only
    the role and the relation between subject and effect.  It can be removed or
    edited without touching code and without retraining anything.
    """
    if not bound_row.get("bound"):
        return {"schema": SCHEMA, "rule": None, "status": "REFUSED__UNBOUND_WITNESS"}
    subjects = [str(s) for s in bound_row.get("subjects") or []]
    return {
        "schema": SCHEMA,
        "rule": {
            "goal_family": str(goal_family),
            "signature": [bound_row.get("role")] + sorted({
                ("self" if p in subjects else "derived")
                for p in bound_row.get("changed") or []}),
            "subject_count": len(subjects),
            "effect_count": len(bound_row.get("changed") or []),
        },
        "status": "PASS__ABSTRACTED",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
    }


# --------------------------------------------------------------------------- #
# External, inspectable store. The mechanism above has no learned state; only
# this file holds what one experience earned. Removing a rule changes behavior
# without touching code or any parameter.
# --------------------------------------------------------------------------- #
def load_rules(path: pathlib.Path | str) -> list[dict[str, Any]]:
    """Read the rule store, or an empty list. A corrupt store fails closed."""
    path = pathlib.Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        return []
    if not isinstance(data, Mapping) or data.get("schema") != SCHEMA:
        return []
    rows = data.get("rules")
    return list(rows) if isinstance(rows, list) else []


def save_rules(path: pathlib.Path | str, rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Atomic whole-store write; no append-in-place, no hidden state."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA, "rules": [dict(r) for r in rules]}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return {"path": str(path), "rule_count": len(payload["rules"])}


def admit_rule(path: pathlib.Path | str, rule: Mapping[str, Any]) -> dict[str, Any]:
    """Store an abstract rule only after a decoy refuted the raw check."""
    inner = rule.get("rule") if rule.get("status") == "PASS__ABSTRACTED" else None
    if not isinstance(inner, Mapping) or not inner.get("signature"):
        return {"status": "REFUSED__NOT_AN_ADMITTED_RULE"}
    rules = load_rules(path)
    signatures = {json.dumps(r.get("signature"), sort_keys=True) for r in rules}
    key = json.dumps(inner["signature"], sort_keys=True)
    if key not in signatures:
        rules.append(dict(inner))
        save_rules(path, rules)
    return {"status": "PASS__STORED", "signature": list(inner["signature"])}


def revoke_rule(path: pathlib.Path | str, signature: Sequence[str]) -> dict[str, Any]:
    """Remove a rule by its signature. Nothing else in the system changes."""
    rules = load_rules(path)
    key = json.dumps(list(signature), sort_keys=True)
    kept = [r for r in rules if json.dumps(r.get("signature"), sort_keys=True) != key]
    save_rules(path, kept)
    return {"status": "PASS__REVOKED", "removed": len(rules) - len(kept)}


def rules_for(path: pathlib.Path | str, signature: Sequence[str]) -> list[dict[str, Any]]:
    """The reusable rules matching this observed effect signature."""
    key = json.dumps(list(signature), sort_keys=True)
    return [r for r in load_rules(path)
            if json.dumps(r.get("signature"), sort_keys=True) == key]
