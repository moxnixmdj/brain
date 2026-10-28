"""Twelve git acts, asked in ordinary English, executed against a real repository.

The inventory ranked version control as the #1 missing area: the machine could not run
`git status` on its own tree, and `git blame`, `git stash`, `git bisect` and `git rebase`
appeared in **zero** files of this repository.  Eleven registry entries now exist
(`vcs.git.*`), so this instrument measures the only thing that matters about them: a
sentence an engineer would actually write, through the live door, with the artifact and the
repository state checked afterwards.

What is measured per row:

  hit      the capability the sentence selected is the one that performs the act
  pass     the door reported PASS
  artifact the JSON artifact exists and carries the fields the act promises
  effect   the REPOSITORY actually changed (mutating verbs only) -- a commit that did not
           move HEAD, or a stash that left the tree dirty, is the hollow pass this
           repository keeps finding, and it is not visible from a status string

Each row gets its own fresh world, because a mutating verb that shares a repository with the
next test measures the fixture, not the capability.

    python3 execution_guard/hardcore_se_git_surface_v1.py [--json OUT] [--only tags]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORK = ROOT / "canonical/astra_runtime/tmp/git_surface"

# (tag, capability, sentence, expected artifact fields, effect check name)
PROBES = [
    ("status", "vcs.git.status.v1",
     "Show me the git status of the repository {R} and write it to {O}.",
     ["branch", "entries", "change_count", "clean"], "status_reports_the_change"),
    ("log", "vcs.git.log.v1",
     "Show the git log of the repository {R} and write it to {O}.",
     ["commits", "commit_count"], "log_reads_both_commits"),
    ("diff", "vcs.git.diff.v1",
     "Show the git diff of the repository {R} against HEAD and write it to {O}.",
     ["files", "patch", "stat"], "diff_shows_the_edit"),
    ("blame", "vcs.git.blame.v1",
     "Blame the lines of the file {R}/pkg/calc.py in the repository {R} and write it to {O}.",
     ["lines", "line_count", "authors"], "blame_attributes_every_line"),
    ("branch_list", "vcs.git.branch_list.v1",
     "List the branches of the repository {R} and write it to {O}.",
     ["branches", "branch_count"], "branches_include_main_and_feature"),
    ("branch_create", "vcs.git.branch_create.v1",
     "Create a branch called trial in the repository {R} and write it to {O}.",
     ["branch_name", "created"], "branch_now_exists"),
    ("checkout", "vcs.git.checkout.v1",
     "Check out the branch feature in the repository {R} and write it to {O}.",
     ["target", "before", "after", "switched"], "head_is_on_the_feature_branch"),
    ("commit", "vcs.git.commit.v1",
     "Commit the changes of the repository {R} with the message \"add subtract\" and write it to {O}.",
     ["committed", "sha", "paths"], "head_moved"),
    ("stash", "vcs.git.stash.v1",
     "Stash the uncommitted changes in the repository {R} and write it to {O}.",
     ["stashed", "stash_ref", "entry_count"], "tree_is_clean"),
    ("revert", "vcs.git.revert.v1",
     "Revert the last commit in the repository {R} and write it to {O}.",
     ["reverted_subject", "sha", "previous_sha"], "head_moved"),
    # The two acts that were missing from this repository entirely.  Both are HISTORIES, not
    # files: a bisect names the commit a predicate first fails at, and a rebase replays a
    # branch -- neither can be checked by looking at the artifact alone.
    ("bisect", "vcs.git.bisect.v1",
     'Bisect the repository {R} from the ref HEAD~2 using the command '
     '"{PY} -m pytest -q {R}/pkg/test_calc.py" and write it to {O}.',
     ["good_ref", "bad_ref", "command", "first_bad_sha", "first_bad_subject", "found"],
     "bisect_names_the_commit_that_broke_the_test", "bisect"),
    ("rebase", "vcs.git.rebase.v1",
     "Rebase the branch in the repository {R} onto main and write it to {O}.",
     ["onto", "branch", "previous_sha", "sha", "commits_replayed"], "branch_replayed_onto_main",
     "rebase"),
]


def _git(repo: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.email=brain@localhost", "-c", "user.name=brain", *argv],
                          cwd=str(repo), capture_output=True, text=True)


def build_bisect_world(tag: str) -> Path:
    """Three commits: the test passes, the test still passes, then it fails.

    A bisect is only meaningful when a PREDICATE flips, so the fixture carries the predicate
    from the first commit: a repository whose test file appears only later would make every
    earlier commit "bad" for having no tests at all, and the act would be graded against the
    fixture rather than against git.
    """
    repo = WORK / tag / "repo"
    shutil.rmtree(repo.parent, ignore_errors=True)
    (repo / "pkg").mkdir(parents=True)
    test = "from pkg.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    (repo / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "pkg/test_calc.py").write_text(test, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first: addition with its test")
    (repo / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n",
        encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "second: add subtract")
    (repo / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a - b\n\n\ndef sub(a, b):\n    return a - b\n",
        encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "third: break addition")
    return repo


def build_rebase_world(tag: str) -> Path:
    """`main` and a `feature` branch that has both moved: a rebase has work to replay."""
    repo = WORK / tag / "repo"
    shutil.rmtree(repo.parent, ignore_errors=True)
    (repo / "pkg").mkdir(parents=True)
    calc = repo / "pkg/calc.py"
    calc.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first")
    _git(repo, "checkout", "-q", "-b", "feature")
    calc.write_text(calc.read_text(encoding="utf-8") + "\n\ndef sub(a, b):\n    return a - b\n",
                    encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "feature: subtract")
    calc.write_text(calc.read_text(encoding="utf-8") + "\n\ndef mul(a, b):\n    return a * b\n",
                    encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "feature: multiply")
    _git(repo, "checkout", "-q", "main")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "main moves on")
    _git(repo, "checkout", "-q", "feature")
    return repo


def build_world(tag: str, setup: str = "") -> Path:
    """Two commits on `main`, one extra branch, and a dirty working tree."""
    if setup == "bisect":
        return build_bisect_world(tag)
    if setup == "rebase":
        return build_rebase_world(tag)
    repo = WORK / tag / "repo"
    shutil.rmtree(repo.parent, ignore_errors=True)
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "first")
    (repo / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "second: add subtract")
    _git(repo, "branch", "feature")
    (repo / "pkg/calc.py").write_text(
        (repo / "pkg/calc.py").read_text(encoding="utf-8")
        + "\n\ndef mul(a, b):\n    return a * b\n", encoding="utf-8")
    return repo


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _branch(repo: Path) -> str:
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _dirty(repo: Path) -> list[str]:
    return [l for l in _git(repo, "status", "--porcelain=v1").stdout.splitlines() if l.strip()]


EFFECTS = {
    "status_reports_the_change": lambda repo, before, body: body.get("change_count", 0) >= 1
        and body.get("clean") is False,
    "log_reads_both_commits": lambda repo, before, body: body.get("commit_count", 0) == 2,
    "diff_shows_the_edit": lambda repo, before, body: "mul" in (body.get("patch") or ""),
    # Every line of the file attributed, and as many lines as the file has -- not a
    # hardcoded count, which would silently pass a truncated report or fail a longer file.
    "blame_attributes_every_line": lambda repo, before, body: (
        bool(body.get("lines"))
        and all(str(x.get("sha") or "") for x in body["lines"])
        and body.get("line_count") == len((repo / "pkg" / "calc.py").read_text().splitlines())),
    "branches_include_main_and_feature": lambda repo, before, body:
        {b["name"] for b in body.get("branches") or []} >= {"main", "feature"},
    "branch_now_exists": lambda repo, before, body:
        _git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/trial").returncode == 0,
    "head_is_on_the_feature_branch": lambda repo, before, body: _branch(repo) == "feature",
    "head_moved": lambda repo, before, body: _head(repo) != before,
    "tree_is_clean": lambda repo, before, body: not _dirty(repo),
    # A bisect is right when the commit it names is the commit that broke the test -- HEAD in
    # this fixture -- and wrong when it names a neighbour that merely happens to be nearby.
    "bisect_names_the_commit_that_broke_the_test": lambda repo, before, body: (
        body.get("found") is True
        and str(body.get("first_bad_sha") or "") == _head(repo)
        and "break" in str(body.get("first_bad_subject") or "")),
    # A rebase is right when the branch now CONTAINS what it was rebased onto and its own work
    # was replayed onto it -- a rebase that reported success while leaving main outside the
    # branch's history is the hollow pass this check exists for.
    "branch_replayed_onto_main": lambda repo, before, body: (
        int(body.get("commits_replayed") or 0) >= 2
        and _git(repo, "merge-base", "--is-ancestor", "main", "HEAD").returncode == 0
        and _branch(repo) == "feature"),
}


# --------------------------------------------------------------------------- refusals
#
# The ten rows above prove the surface can ACT.  A git surface that acts on a request it
# cannot honour is worse than one that cannot act at all: `git checkout` on a dirty tree
# throws the engineer's work away, `git revert` under a conflict leaves a tree nobody asked
# for, and `git commit` on a clean tree is a report about a commit that never happened.
# Each row below states a sentence the verb must REFUSE, and records which named refusal
# reached the front door and whether the repository was left exactly as it was found.

NOT_A_REPO_DIR = WORK / "not_a_repository"


def _world_untouched(repo: Path):
    """Snapshot of everything a refused verb must leave alone."""
    return ({"head": _head(repo), "branch": _branch(repo), "dirty": _dirty(repo),
             "branches": sorted(l.strip() for l in
                                _git(repo, "branch", "--format=%(refname:short)").stdout.splitlines() if l.strip())}
            if (repo / ".git").exists() else {"head": "", "branch": "", "dirty": [], "branches": []})


# (tag, sentence, world setup, expected refusal codes)
REFUSALS = [
    ("not_a_repository", "Show me the git status of the repository {R} and write it to {O}.",
     "plain_directory", ("NOT_A_REPOSITORY",)),
    ("repository_not_stated", "Show me the git status of the repository and write it to {O}.",
     "plain_directory", ("REPOSITORY_NOT_STATED", "REPOSITORY_NOT_A_DIRECTORY",
                         "DECLARED_INPUTS_UNBOUND", "BINDING_REFUSED", "FAIL_CLOSED")),
    ("working_tree_dirty", "Check out the branch feature in the repository {R} and write it to {O}.",
     "dirty", ("WORKING_TREE_DIRTY",)),
    ("ref_not_found", "Check out the branch nosuchbranch in the repository {R} and write it to {O}.",
     "clean", ("REF_NOT_FOUND",)),
    ("nothing_to_commit",
     'Commit the changes of the repository {R} with the message "no change at all" and write it to {O}.',
     "clean", ("NOTHING_TO_COMMIT", "COMMIT_DID_NOT_MOVE_HEAD")),
    ("branch_already_exists",
     "Create a branch called main in the repository {R} and write it to {O}.",
     "clean", ("BRANCH_ALREADY_EXISTS",)),
    ("revert_conflict",
     "Revert the commit {SHA} of the repository {R} and write it to {O}.",
     "revert_conflict", ("REVERT_CONFLICT",)),
    ("path_not_in_repository",
     "Blame the lines of the file {OUTSIDE} in the repository {R} and write it to {O}.",
     "clean", ("PATH_NOT_IN_REPOSITORY", "BINDING_REFUSED", "FAIL_CLOSED")),
    # A bisect with no predicate and a rebase onto a revision that is not there.  Both are acts
    # whose WRONG version damages history, so both must refuse by name.
    ("bisect_without_a_command",
     "Bisect the repository {R} from the ref HEAD~2 and write it to {O}.",
     "bisect", ("argv:not_stated", "BISECT_COMMAND_NOT_STATED", "BINDING_REFUSED",
                "STATED_ACT_INPUTS_UNBOUND", "FAIL_CLOSED")),
    ("rebase_onto_a_missing_ref",
     "Rebase the branch in the repository {R} onto nosuchbranch and write it to {O}.",
     "rebase", ("REF_NOT_FOUND",)),
]


def _refusal_world(tag: str, setup: str) -> tuple[Path, str, dict]:
    """Build the world a refusal needs. Returns (repo, an outside file, values the sentence names)."""
    if setup == "plain_directory":
        shutil.rmtree(NOT_A_REPO_DIR, ignore_errors=True)
        NOT_A_REPO_DIR.mkdir(parents=True)
        (NOT_A_REPO_DIR / "README.md").write_text("# not a repository\n", encoding="utf-8")
        return NOT_A_REPO_DIR, "", {}
    if setup in ("bisect", "rebase"):
        # These two verbs need a history that has something to find (a predicate that flips) or
        # something to replay (a branch that has moved), so they build their own world.
        repo = build_world("refuse_" + tag, setup)
        outside = WORK / "outside" / ("outside_%s.py" % tag)
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("value = 1\n", encoding="utf-8")
        return repo, str(outside.relative_to(ROOT)), {}
    repo = build_world("refuse_" + tag)
    if setup == "clean":
        # A clean tree, because these rows test the REFUSAL and not the dirty-tree guard.
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "third: add multiply")
    elif setup == "revert_conflict":
        # `git revert` conflicts when a LATER commit touches the same lines as the reverted
        # one, so the second commit's change is undone first and committed back.
        calc = repo / "pkg/calc.py"
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "third: add multiply")
        calc.write_text(calc.read_text(encoding="utf-8").replace(
            "    return a - b\n", "    return a - b  # later edit\n"), encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "fourth: edit the subtract line")
        # The commit whose own lines are gone: reverting it re-applies a line that a later
        # commit rewrote, which is the conflict -- and the sha is read from the repository
        # rather than written into the sentence, exactly as an engineer would copy it.
        target = _git(repo, "rev-parse", "HEAD~3").stdout.strip()
    outside = WORK / "outside" / ("outside_%s.py" % tag)
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("value = 1\n", encoding="utf-8")
    return repo, str(outside.relative_to(ROOT)), {"SHA": locals().get("target", "")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    # Re-run against the world the previous run left behind.  A capability whose answer
    # changes once its own artifact exists is not the same capability, and the only way to
    # see that is to run the same sentence twice without wiping the world between runs.
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--refusals", action="store_true",
                    help="measure the refusals instead of the acts")
    ns = ap.parse_args()

    from canonical.runtime import live_brain_route_admission_v1 as adm

    if not ns.reuse:
        shutil.rmtree(WORK, ignore_errors=True)
    if ns.refusals:
        return _measure_refusals(adm, ns)
    rows = []
    for row_def in PROBES:
        tag, cid, sentence, fields, effect = row_def[:5]
        setup = row_def[5] if len(row_def) > 5 else ""
        if ns.only and tag not in ns.only.split(","):
            continue
        fresh = not (ns.reuse and (WORK / tag / "repo" / ".git").exists())
        repo = build_world(tag, setup) if fresh else (WORK / tag / "repo")
        if fresh and tag in ("revert", "checkout"):
            # `git revert` and `git checkout` both refuse a dirty tree -- that refusal IS the
            # contract -- so the fixture commits first rather than the check being weakened.
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "third: add multiply")
        out = repo.parent / "out" / (tag + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        goal = sentence.format(R=str(repo), O=str(out), PY=sys.executable)
        before = _head(repo)
        try:
            res = adm.solve({"task_id": "GIT_" + tag, "goal": goal})
            selected = str(res.get("capability_id") or res.get("compiled_capability_id") or "-")
            status = str(res.get("status") or "")
            reason = str(res.get("reason") or "")[:80]
        except Exception as exc:  # noqa: BLE001 - a crash is a finding, not an error
            selected, status, reason = "-", "EXC:" + type(exc).__name__, str(exc)[:80]
        body = {}
        if out.is_file():
            try:
                body = json.loads(out.read_text(encoding="utf-8"))
            except ValueError:
                body = {}
        missing = [f for f in fields if f not in body]
        try:
            effected = bool(EFFECTS[effect](repo, before, body))
        except Exception:  # noqa: BLE001
            effected = False
        row = {"tag": tag, "expected": cid, "selected": selected, "hit": selected == cid,
               "pass": status.startswith("PASS"), "artifact": bool(body),
               "missing_fields": missing, "effect": effected, "status": status[:70],
               "reason": reason}
        rows.append(row)
        print("%-13s hit=%-3s pass=%-3s art=%-3s effect=%-3s %s"
              % (tag, "Y" if row["hit"] else "N", "Y" if row["pass"] else "N",
                 "Y" if row["artifact"] else "N", "Y" if effected else "N", status[:40]), flush=True)

    hits = sum(1 for r in rows if r["hit"])
    passes = sum(1 for r in rows if r["pass"])
    arts = sum(1 for r in rows if r["artifact"] and not r["missing_fields"])
    effs = sum(1 for r in rows if r["effect"])
    print("\nselected %d/%d  pass %d/%d  artifact %d/%d  repository actually changed %d/%d"
          % (hits, len(rows), passes, len(rows), arts, len(rows), effs, len(rows)))
    if ns.json:
        Path(ns.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


def _measure_refusals(adm, ns) -> int:
    """State one sentence per refusal and check it closed AND that nothing moved."""
    rows = []
    for tag, sentence, setup, codes in REFUSALS:
        if ns.only and tag not in ns.only.split(","):
            continue
        repo, outside, values = _refusal_world(tag, setup)
        out = (WORK / tag / "out" / ("refusal_" + tag + ".json")) if (repo / ".git").exists() \
            else (repo.parent / "out" / ("refusal_" + tag + ".json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        goal = sentence.format(R=repo.relative_to(ROOT), O=out.relative_to(ROOT),
                              OUTSIDE=outside, **values)
        before = _world_untouched(repo)
        try:
            res = adm.solve({"task_id": "GIT_REFUSE_" + tag, "goal": goal})
            status = str(res.get("status") or "")
            reason = str(res.get("reason") or "")
        except Exception as exc:  # noqa: BLE001 - a crash is a finding, not an error
            status, reason = "EXC:" + type(exc).__name__, str(exc)
        body = {}
        if out.is_file():
            try:
                body = json.loads(out.read_text(encoding="utf-8"))
            except ValueError:
                body = {}
        # A refusal is only a refusal if it NAMES the contract it declined, either in the
        # door's reason or in the artifact it wrote, and if the repository is untouched.
        spoken = " ".join(str(x) for x in (reason, body.get("reason"), body.get("gate")))
        named = next((c for c in codes if c in spoken), "")
        untouched = _world_untouched(repo) == before
        acted = status.startswith("PASS")
        row = {"tag": tag, "expected_codes": list(codes), "named": named,
               "status": status[:70], "reason": reason[:100],
               "refused": bool(named) and not acted, "untouched": untouched,
               "outcome": ("REFUSED_AND_NAMED" if (named and not acted and untouched)
                           # A PASS is never a refusal, whatever the artifact says: the door
                           # read a gate and reported success for an act it did not perform.
                           else ("REPORTED_A_PASS" if acted
                                 else ("UNTOUCHED_BUT_UNNAMED" if untouched
                                       else "CHANGED_WITHOUT_NAMING")))}
        rows.append(row)
        print("%-22s %-20s %-22s %s"
              % (tag, row["outcome"], named or "<none>", status[:34]), flush=True)
    good = sum(1 for r in rows if r["outcome"] == "REFUSED_AND_NAMED")
    print("\nrefused and named %d/%d   (untouched %d/%d)"
          % (good, len(rows), sum(1 for r in rows if r["untouched"]), len(rows)))
    if ns.json:
        Path(ns.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
