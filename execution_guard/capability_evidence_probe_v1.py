#!/usr/bin/env python3
"""Give every capability that claims VERIFIED_BOUND_CAPABILITY the evidence the claim implies.

WHY THIS EXISTS (measured on arena/4ca3a720-brain)
--------------------------------------------------
`canonical/tests/test_live_brain_route_admission_v1.py::test_no_registry_entry_is_left_without_proof`
asserts that no registry entry carries a missing or empty `verification` block. Measured: 16 of
154 entries do -- every capability added after the receipt-projection lane was built but through
the adapter lanes (`quality_v1`, `toolchain_v1`, `vcs_git_v1`). They are the ones that answer the
hardcore-software sentences (lint, type check, coverage, duplication, resource leak, api
compatibility, bisect, rebase), so the hole sits exactly where the work is.

The generic lane could not close it. `capability_receipt_lane_v1.discover()` fills every
`${input.*}` with a content-addressed SINK path, so an adapter whose declared input is a real
source tree fails closed on a path that does not exist, the probe swallows the SystemExit, and the
entry gets no receipt: measured, 0 of 16 issued. A generic probe cannot evidence an adapter whose
input is the world. It needs a TASK-SHAPED input.

WHAT THIS PROBE DOES
--------------------
Builds, outside the repository, small fixtures that are shaped like the work:

* a python package that duplicates a block, leaks a file handle, carries no licence, and has a
  test that fails -- the input every analysis verb needs;
* a git repository with a known-good commit, a known-bad commit, and one failing command -- the
  input bisect needs (the command is the predicate, and here it is stated, not guessed);
* a branch and an upstream -- the input rebase needs.

Then it runs each capability ONCE on that fixture through its own `run(args, root)`, records the
observed effect and the artifact digest, runs it a SECOND time, and reports whether the two agree.
A receipt is written only when the capability actually ran and the second run reproduced the
first: an unreproduced receipt would be a claim, and the whole point is that this file issues none.

Nothing is promoted. `producer_independent` is false and stays false: this is one identity running
its own work. The receipt is evidence, and promotion remains governed elsewhere.

    python3 execution_guard/capability_evidence_probe_v1.py            # measure + write receipts
    python3 execution_guard/capability_evidence_probe_v1.py --check    # measure only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
EVIDENCE = ROOT / "canonical/astra_runtime/evidence"

# The analysis verbs all read a source tree and write one artifact.  The fixture is written to
# contain exactly one instance of each finding they look for, so "found 1" is a fact the probe
# can compare against the file it wrote rather than against an expectation.
LEAKY_SOURCE = '''import os


def read_config(path):
    handle = open(path)
    return handle.read()


def duplicate_a(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
        else:
            total -= item
    return total


def duplicate_b(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
        else:
            total -= item
    return total


def branchy(kind, value):
    # deliberately above the default C901 threshold of 10, so the complexity verb has something
    # it is REQUIRED to report rather than merely nothing to complain about
    if kind == 1:
        return value + 1
    elif kind == 2:
        return value - 1
    elif kind == 3:
        return value * 2
    elif kind == 4:
        return value // 2
    elif kind == 5:
        return value % 3
    elif kind == 6:
        return value ** 2
    elif kind == 7:
        return -value
    elif kind == 8:
        return abs(value)
    elif kind == 9:
        return value or 1
    elif kind == 10:
        return value and 2
    elif kind == 11:
        return 0 if value else 1
    return value
'''

CALC_SOURCE = '''def add(a, b):
    return a + b


def divide(a, b):
    return a / b
'''

TEST_SOURCE = '''from pkg.calc import divide


def test_divide_by_zero_is_refused():
    assert divide(1, 0) == 0
'''


def _sink(root: Path, name: str) -> Path:
    out = root / "out" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *argv], cwd=str(repo), capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "p", "GIT_AUTHOR_EMAIL": "p@e",
                               "GIT_COMMITTER_NAME": "p", "GIT_COMMITTER_EMAIL": "p@e"})


def build_source_fixture(work: Path) -> Path:
    """A small python project with one of each finding the analysis verbs look for."""
    root = work / "source"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "io_leak.py").write_text(LEAKY_SOURCE, encoding="utf-8")
    (root / "pkg" / "calc.py").write_text(CALC_SOURCE, encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(TEST_SOURCE, encoding="utf-8")
    # Two of the analysis verbs read HISTORY, not a tree (`changelog` and `api_compatibility`
    # both read the committed revision through `git show`).  A plain directory makes them
    # refuse NOT_A_REPOSITORY / NOT_A_GIT_WORKTREE, which is a fact about the fixture, not
    # about the capability.  So the fixture is a repository with a committed baseline.
    _git(root, ["init", "-q", "-b", "main"])
    _git(root, ["add", "-A"])
    _git(root, ["commit", "-qm", "baseline"])
    return root


def build_git_fixture(work: Path) -> Path:
    """A repository with a known-good commit, a known-bad one, and an upstream branch."""
    repo = work / "repo"
    repo.mkdir(parents=True)
    _git(repo, ["init", "-q", "-b", "main"])
    (repo / "value.txt").write_text("1\n", encoding="utf-8")
    _git(repo, ["add", "-A"])
    _git(repo, ["commit", "-qm", "good"])
    good = _git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    (repo / "value.txt").write_text("2\n", encoding="utf-8")
    _git(repo, ["add", "-A"])
    _git(repo, ["commit", "-qm", "bad"])
    bad = _git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    # An upstream to rebase onto: a branch that main has not seen.
    _git(repo, ["checkout", "-q", "-b", "upstream", good])
    (repo / "upstream.txt").write_text("u\n", encoding="utf-8")
    _git(repo, ["add", "-A"])
    _git(repo, ["commit", "-qm", "upstream work"])
    upstream = _git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    _git(repo, ["checkout", "-q", "-b", "feature", bad])
    return repo, good, upstream  # type: ignore[return-value]


# capability -> the VALUES its declared slots are filled with.  Nothing here decides what a
# capability means: the declared invocation already says that.  This only supplies the world the
# declaration assumes -- a source tree that has the findings, a repository with a known good and a
# known bad commit -- where the generic lane supplied a sink path that does not exist.
def _inputs(cid: str, source: Path, repo, good: str, upstream: str, out: Path) -> dict[str, Any]:
    if cid == "vcs.git.bisect.v1":
        # The predicate is STATED, and it is a command the fixture's own history makes true at
        # the good commit and false after it.  A bisect with an invented predicate would name a
        # commit that has nothing to do with anything.
        return {"argv": ["python3", "-c",
                         "import sys,pathlib;"
                         "sys.exit(pathlib.Path('value.txt').read_text().strip() != '1')"],
                "ref": good, "worktree_path": str(repo),
                "output_path": str(out / "bisect.json")}
    if cid == "vcs.git.rebase.v1":
        return {"ref": upstream, "worktree_path": str(repo),
                "output_path": str(out / "rebase.json")}
    return {"source_root": str(source),
            "source_paths": [str(source / "pkg" / "calc.py")],
            "output_path": str(out / (cid.rsplit(".", 2)[-2] + ".json"))}


def _declared_args(entry: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any] | None:
    """The capability's OWN template, with every `${input.x}` filled from `values`."""
    template = (entry.get("action_template") or {}).get("args") or {}
    args: dict[str, Any] = {}
    for key, value in template.items():
        if isinstance(value, str) and value.startswith("${input.") and value.endswith("}"):
            name = value[len("${input."):-1]
            if name not in values:
                return None  # a slot this fixture cannot fill: the task shape is unknown
            args[key] = values[name]
        else:
            args[key] = value
    return args


# The artifact records where it was written and what it was pointed at, so two runs at different
# paths can never have the same sha256 even when they found exactly the same things.  Reproduction
# therefore compares the FINDINGS: every key whose value is a path, a digest or a clock reading is
# dropped, and the rest must be equal.
_VOLATILE_KEYS = ("target", "artifact_path", "artifact_sha256", "output_path", "elapsed",
                  # A commit id identifies WHEN the replay happened, not what it found: two
                  # identical rebases mint different shas because the committer clock differs.
                  "sha", "previous_sha", "head", "onto", "good_ref", "bad_ref", "first_bad_sha",
                  "elapsed_ms", "elapsed_ns", "generated_at", "timestamp", "duration_ms",
                  "started_at", "finished_at", "cwd", "repo", "worktree_path",
                  # A process TRANSCRIPT is not a finding: pytest's own tail carries its
                  # runtime ("1 failed in 0.42s"), so two identical analyses never match on it.
                  # The verdict, the counts and the finding list all stay in the comparison.
                  "test_output_tail", "stdout", "stderr", "log", "log_tail")
_VOLATILE_PARTS = ("elapsed", "duration", "timestamp", "_at", "_ms", "_ns", "sha256", "path")


def finding_projection(value: Any, key: str = "") -> Any:
    """The result with everything that is about THIS run removed."""
    if isinstance(value, Mapping):
        return {k: finding_projection(v, str(k)) for k, v in value.items()
                if str(k) not in _VOLATILE_KEYS
                and not any(part in str(k).lower() for part in _VOLATILE_PARTS)}
    if isinstance(value, (list, tuple)):
        return [finding_projection(v, key) for v in value]
    if isinstance(value, str) and value.startswith("/"):
        return "<path>"
    return value


def _findings_sha(result: Any) -> str:
    return hashlib.sha256(json.dumps(finding_projection(result), sort_keys=True,
                                     default=str).encode("utf-8")).hexdigest()


# WHAT THE FIXTURE GUARANTEES, AND WHAT EACH VERB MUST THEREFORE FIND.
# Running is not finding.  A resource-leak analyser that reports "0 leaks" on a file with an
# unclosed `open()` has executed successfully and told a lie, and a receipt recording only "it
# ran, gate=PASS" would carry that lie forward as evidence.  Each predicate below is true only
# if the planted defect came back.
ORACLE = {
    "python.quality.resource_leak.v1": (
        "the unclosed open() in pkg/io_leak.py",
        lambda r: int(r.get("leaks_found") or 0) >= 1),
    "python.quality.duplication.v1": (
        "the block duplicated between duplicate_a and duplicate_b",
        lambda r: int(r.get("clone_group_count") or 0) >= 1),
    "python.quality.coverage.v1": (
        "the failing test in tests/test_calc.py",
        lambda r: r.get("tests_passed") is False
        and isinstance(r.get("percent_covered"), (int, float))),
    "python.quality.license_scan.v1": ("the package's undeclared licence",
                                       lambda r: bool(r.get("licenses"))),
    "python.quality.changelog.v1": ("the committed baseline",
                                    lambda r: int(r.get("commit_count") or 0) >= 1),
    "python.quality.api_compatibility.v1": (
        "the committed revision it must diff against",
        lambda r: bool(r.get("complete")) and int(r.get("files_compared") or 0) >= 1),
    "python.toolchain.bandit_security.v1": ("the assert in the test module (B101)",
                                            lambda r: bool(r.get("issues"))),
    "python.toolchain.ruff_lint.v1": (
        "the unclosed file (SIM115) and the unused import (F401)",
        lambda r: len(r.get("issues") or []) >= 2),
    "python.toolchain.ruff_dead_code.v1": ("the unused `import os`",
                                           lambda r: int(r.get("unused_count") or 0) >= 1),
    "python.toolchain.ruff_complexity.v1": (
        "the twelve-branch function `branchy`, which is above the default threshold",
        lambda r: int(r.get("over_threshold_count") or 0) >= 1
        and isinstance(r.get("max_complexity"), int) and r["max_complexity"] > 10),
    "python.toolchain.mypy_typecheck.v1": ("the functions it must at least parse",
                                           lambda r: isinstance(r.get("error_count"), int)),
    "vcs.git.bisect.v1": ("the first bad commit, whose subject is 'bad'",
                          lambda r: bool(r.get("found")) and r.get("first_bad_subject") == "bad"),
    "vcs.git.rebase.v1": ("the one commit replayed onto the upstream branch",
                          lambda r: int(r.get("commits_replayed") or 0) >= 1),
}


def _run_once(cid: str, module_path: str, entrypoint: str, args: Mapping[str, Any]) -> dict | None:
    """Load the adapter exactly as the kernel does and call it once."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pb_evidence_" + cid.replace(".", "_"),
                                                  str(ROOT / module_path))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        fn = getattr(module, entrypoint, None)
        if not callable(fn):
            return None
        return fn(dict(args), str(ROOT))
    except BaseException as exc:  # noqa: BLE001 - a probe that dies is a measurement, not a crash
        return {"probe_error": type(exc).__name__, "detail": str(exc)[:200]}


def _module_path(cid: str, entry: Mapping[str, Any]) -> str | None:
    from canonical.runtime import capability_receipt_lane_v1 as lane
    return lane._bound_module_path(str(ROOT), entry)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="measure without writing receipts")
    ap.add_argument("--only", default="", help="comma separated capability ids")
    ns = ap.parse_args(argv)

    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    wanted = [c for c, e in sorted(caps.items())
              if not isinstance(e.get("verification"), dict) or not e.get("verification")]
    if ns.only:
        keep = {c.strip() for c in ns.only.split(",") if c.strip()}
        wanted = [c for c in wanted if c in keep]

    work = Path(tempfile.mkdtemp(prefix="brain_evidence_"))
    receipts: dict[str, dict] = {}
    rows = []
    try:
        source = build_source_fixture(work)
        repo, good, upstream = build_git_fixture(work)
        for cid in wanted:
            entry = caps[cid]
            module_path = _module_path(cid, entry)
            if module_path is None:
                rows.append({"capability_id": cid, "outcome": "NO_MODULE"})
                continue
            shape = __import__("canonical.runtime.capability_receipt_lane_v1",
                               fromlist=["contract_shape"]).contract_shape(
                str(ROOT / module_path))
            entrypoint = shape[0] if shape else "run"
            base_args = _declared_args(entry, _inputs(cid, source, repo, good, upstream,
                                                      work / "out"))
            if base_args is None:
                rows.append({"capability_id": cid, "outcome": "NO_TASK_SHAPE"})
                continue
            # A fresh output path per run so the second run cannot "reproduce" by finding the
            # first run's artifact already there.
            first = _run_once(cid, module_path, entrypoint, base_args)
            first_sha = _sha256(Path(base_args["output_path"]))
            # Same STARTING WORLD, second time -- a COPY of the template, so the tree and the
            # git history are byte-identical rather than merely equivalent.  Some of these verbs
            # mutate what they are pointed at (`rebase` replays commits, `ruff_format` rewrites
            # the source), so a second run against the world the first one left behind measures
            # idempotence, not reproduction; and rebuilding mints new commit shas, which the
            # findings legitimately quote.
            second_world = work / "second"
            shutil.rmtree(second_world, ignore_errors=True)
            shutil.copytree(source, second_world / "source")
            shutil.copytree(repo, second_world / "repo")
            second_args = _declared_args(entry, _inputs(cid, second_world / "source",
                                                        second_world / "repo", good, upstream,
                                                        second_world / "out"))
            second = _run_once(cid, module_path, entrypoint, second_args)
            ran = isinstance(first, Mapping) and not first.get("probe_error")
            reproduced = bool(ran and _findings_sha(first) == _findings_sha(second))
            row = {
                "capability_id": cid,
                "module_path": module_path,
                "entrypoint": entrypoint,
                "outcome": "EXECUTED" if ran else "DID_NOT_RUN",
                "observed": ({k: first.get(k) for k in ("status", "pass", "gate",
                                                        "output_verified")
                              if k in first} if ran else {}),
                "artifact_sha256": first_sha,
                "reproduced": reproduced,
                "gate": (first or {}).get("gate") if ran else None,
                "probe_error": (first or {}).get("probe_error") if isinstance(first, Mapping) else None,
            }
            planted = ORACLE.get(cid)
            if planted is not None and ran:
                label, predicate = planted
                try:
                    row["found"] = bool(predicate(first))
                except Exception:  # noqa: BLE001 - a result the oracle cannot read is a MISS
                    row["found"] = False
                row["planted"] = label
            rows.append(row)
            if ran and reproduced and not ns.check:
                receipt_path = ("canonical/astra_runtime/evidence/"
                                "CAPABILITY__" + cid.replace("/", "_") + "__RECEIPT.json")
                receipt = {
                    "schema": "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1",
                    "capability_id": cid,
                    "kind": "contract",
                    "module_path": module_path,
                    "module_sha256": hashlib.sha256((ROOT / module_path).read_bytes()).hexdigest(),
                    "entrypoint": entrypoint,
                    "invoked_args": {k: v for k, v in base_args.items() if k != "capability_id"},
                    "outcome": "EXECUTED",
                    "observed": row["observed"],
                    "artifact_sha256": first_sha,
                    "reproduced_on_second_run": True,
                "planted_defect": row.get("planted"),
                "planted_defect_found": row.get("found"),
                    "elapsed_ms": None,
                    "executor": "execution_guard/capability_evidence_probe_v1.py",
                    "probe_input": "task-shaped fixture (source tree / git repository), not a sink path",
                    "model_dependency_count": 0,
                    "incremental_spend_usd": 0,
                    "ran_by": "local-session",
                    "independent_verifier": None,
                    "producer_independent": False,
                    "receipt_path": receipt_path,
                }
                EVIDENCE.mkdir(parents=True, exist_ok=True)
                (ROOT / receipt_path).write_text(json.dumps(receipt, indent=1, sort_keys=True),
                                                 encoding="utf-8")
                receipts[cid] = receipt
    finally:
        shutil.rmtree(work, ignore_errors=True)

    executed = sum(1 for r in rows if r.get("outcome") == "EXECUTED")
    reproduced = sum(1 for r in rows if r.get("reproduced"))
    for row in rows:
        print("%-46s %-12s gate=%-5s reproduced=%-5s found=%s" % (
            row["capability_id"], row["outcome"], str(row.get("gate")), row.get("reproduced"),
            {True: "YES", False: "MISSED", None: "-"}.get(row.get("found"), "-")))
    missed = [r for r in rows if r.get("found") is False]
    if missed:
        print("\nplanted defects the claiming capability did NOT find (a capability defect):")
        for row in missed:
            print("  - %s: %s" % (row["capability_id"], row.get("planted")))
    print("\nentries without evidence: %d | executed: %d | reproduced: %d | receipts written: %d"
          % (len(wanted), executed, reproduced, len(receipts)))
    if not ns.check:
        print("receipts: " + (", ".join(sorted(receipts)) or "none"))
    return 0 if reproduced == len(wanted) else 1


if __name__ == "__main__":
    raise SystemExit(main())
