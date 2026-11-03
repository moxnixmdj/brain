#!/usr/bin/env python3
"""Derive a safe retained-learning scope from what a project already declares.

Why this exists
---------------
`python.software.repair.apply.verified.v1` contains the whole learning chain --
propose, recall, verify, teach, crystallize, carry the operator generalization --
and it is **switched off by default** (`retained_learning: {"enabled": False}`).
Only a benchmark tool ever turns it on, so production repairs search cold every time.

Measured 2026-11-02 with `canonical/tools/live_scoped_transfer_benchmark_v1.py`,
same constructed boundary lesson, three arms:

    arm             solved   retained hits   search invocations
    cold             7/7          0                 6
    statement        7/7          1                 5
    generalized      7/7          6                 0

Fully switched on, **every** repair becomes a recalled plan: search 6 -> 0. It does not
move the solve rate, and that is the honest reading -- learning is a COST technology
here, not a capability technology.

Why it was off
--------------
Recall needs a caller-declared `contract` with a `scope_id`. Deriving the right scope
looks like the unresolved hypothesis-space problem, so the default stayed off.

That framing was wrong, and seeing why is the whole point of this module:

    The scope is a COST FILTER, not a SAFETY FILTER.

`recall_and_apply_verified` takes a mandatory verifier, and `RetainedRepairSession`
wires it to `ProjectTestOracle` -- the project's real test suite -- which runs on
**every** recall before any candidate is proposed. So:

  * a scope derived too WIDE costs one failed oracle call and a fallback to search;
    it cannot yield a patch the suite would have rejected;
  * a scope derived too NARROW costs the search we already pay today.

Neither outcome can produce a wrong patch. The cheap, sufficient question is therefore
not "is this the correct hypothesis space" but "is this key stable and specific enough
that a second repair of the same kind lands on it". This module answers exactly that.

What the scope is
-----------------
The **test corpus the repair is verified against**, hashed. Two repairs are in scope
together when the same tests judge them. That is deliberately conservative: it makes
learning *within a project* instant (the measured 32->1, 64->1, 16->1 result) and does
not attempt cross-project carry, which needs the hypothesis-space work and is therefore
out of scope by construction rather than by omission.

`allow_operator_generalization` is enabled only where the store itself permits it
(TEST_SUITE + scope_id + python). That flag is what took retained hits from 1 to 6.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RETAINED_SCOPE_DERIVATION_V1"

# Where a derived store lives, relative to the repository root. Contained, visible and
# reported in the output rather than hidden: the session refuses any path outside the
# repository, and a learner whose memory location is not stated is a learner you cannot
# audit.
DEFAULT_DB_RELPATH = ".brain/retained_repair_skills.sqlite"

DERIVED = "DERIVED_FROM_TEST_CORPUS"


def _non_test_python_files(source_root: Path) -> list[Path]:
    from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import is_test_file_name

    found: list[Path] = []
    for path in sorted(source_root.rglob("*.py")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or any(p == ".git" for p in path.parts):
            continue
        if is_test_file_name(path.name):
            continue
        found.append(path)
    return found


def derive_scope_id(repo: Path, test_paths: Sequence[Path]) -> str:
    """A stable key from the test corpus that judges the repair.

    Repository-relative paths, sorted, so the same corpus gives the same key on a
    different checkout of the same project and a different corpus never collides.
    """
    rel = sorted(
        str(p.resolve().relative_to(repo.resolve()).as_posix()) if p.resolve().is_relative_to(repo.resolve())
        else p.name
        for p in test_paths
    )
    digest = hashlib.sha256("\n".join(rel).encode("utf-8")).hexdigest()[:16]
    return f"python/tests/{digest}/v1"


def derive_retained_config(
    *,
    repo: Path,
    source_root: Path,
    test_paths: Sequence[Path],
    explicit: Any = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return (config, report). A config of None means declined, with the reason named.

    `explicit` is whatever the caller passed. A caller that states a configuration
    keeps it verbatim -- this function never overrides an explicit decision, it only
    supplies one where the caller supplied none.

    Fails closed by declining, never by guessing: every decline names its cause and
    leaves the solver on the path it already took.
    """
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source": None,
        "scope_id": None,
        "db_path": None,
        "allow_operator_generalization": None,
        "declined_reason": None,
        "scope_is_cost_filter_not_safety_filter": True,
        "verifier_runs_on_every_recall": True,
    }

    if explicit is not None:
        report["source"] = "CALLER_STATED"
        report["declined_reason"] = None
        return explicit, report

    repo = repo.resolve()
    source_root = source_root.resolve()
    if not source_root.is_dir():
        report["declined_reason"] = "DECLINED:SOURCE_ROOT_NOT_A_DIRECTORY"
        return None, report

    if not test_paths:
        report["declined_reason"] = "DECLINED:NO_TEST_CORPUS_TO_SCOPE_AGAINST"
        return None, report

    # A retained session proposes a rewrite for exactly ONE target file. Deriving a
    # target is honest only when the tree has exactly one non-test module; with more,
    # "which file does this repair concern" is not a fact the tree states, and picking
    # one would be a guess dressed as a derivation.
    sources = _non_test_python_files(source_root)
    if len(sources) == 0:
        report["declined_reason"] = "DECLINED:NO_NON_TEST_SOURCE_FILE_TO_TARGET"
        return None, report
    if len(sources) > 1:
        report["declined_reason"] = "DECLINED:MULTIPLE_SOURCE_FILES_TARGET_AMBIGUOUS"
        report["non_test_source_count"] = len(sources)
        return None, report

    target = sources[0]
    try:
        target_rel = target.relative_to(repo).as_posix()
    except ValueError:
        report["declined_reason"] = "DECLINED:TARGET_OUTSIDE_REPOSITORY"
        return None, report

    scope_id = derive_scope_id(repo, test_paths)
    config = {
        "enabled": True,
        "db_path": DEFAULT_DB_RELPATH,
        "target_path": target_rel,
        # Empty dependence/precondition maps are the honest statement "this lesson is
        # scoped by its test corpus and by nothing else". They are not omitted, because
        # `applicable()` requires both to be present and to match exactly.
        "contract": {
            "schema_version": 1,
            "scope_id": scope_id,
            "verification_kind": "TEST_SUITE",
            "dependencies": {},
            "preconditions": {},
        },
        "context": {"dependencies": {}, "preconditions": {}},
        # TEST_SUITE + scope_id + python is exactly the store's own precondition for
        # this flag, and it is what raised retained hits from 1 to 6.
        "allow_operator_generalization": True,
    }
    report.update(
        source=DERIVED,
        scope_id=scope_id,
        db_path=DEFAULT_DB_RELPATH,
        target_path=target_rel,
        allow_operator_generalization=True,
        test_corpus_size=len(test_paths),
    )
    return config, report


def explain(report: Mapping[str, Any]) -> str:
    """One line a human can read in a report."""
    if report.get("declined_reason"):
        return f"retained learning DECLINED: {report['declined_reason']}"
    return ("retained learning ON: scope %s, target %s, memory %s%s"
            % (report.get("scope_id"), report.get("target_path"), report.get("db_path"),
               ", operator generalization on" if report.get("allow_operator_generalization") else ""))
