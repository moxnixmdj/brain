"""Probe the acts the machine has NO capability for -- and see what answers them.

The 22-task reachability probe measures capabilities that exist.  This one measures the
other half of the problem list: the parts of a software engineer's job for which the
registry holds no capability at all, and what the front door does when it is asked for
one anyway.

Three outcomes matter, and only one of them is honest:

  HONEST_REFUSAL   the request fails closed and says it cannot do it;
  SILENTLY_WRONG   some other capability answers, writes a credible artifact, and the
                   door reports PASS -- a hollow pass, which is worse than a refusal
                   because it looks like work;
  WRONG_TOOL       a related but different capability answers and fails, so the user
                   cannot tell a missing capability from a broken one.

Every sentence is ordinary English naming the act, pointed at a scratch repository so a
sentence that reaches `shell.command.run` cannot touch this repository.

    python3 execution_guard/hardcore_se_missing_verb_probe_v1.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORK = ROOT / "canonical/astra_runtime/tmp/missing_verb_probe"


def build_repo() -> Path:
    """A tiny but REAL repository: two commits, a branch, a dirty file, a conflict-free tree."""
    b = WORK / "repo"
    shutil.rmtree(b, ignore_errors=True)
    (b / "pkg").mkdir(parents=True)
    (b / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (b / "README.md").write_text("# demo\n", encoding="utf-8")
    g = lambda *a: subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *a],
                                  cwd=b, capture_output=True, text=True)
    g("init", "-q"); g("add", "-A"); g("commit", "-qm", "first")
    (b / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n",
                                   encoding="utf-8")
    g("add", "-A"); g("commit", "-qm", "second")
    (b / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n",
        encoding="utf-8")
    return b


# (act, sentence).  The sentences name the act the way an engineer names it; none of them
# names a capability, a slot, or a registry word.
ACTS = [
    # ---- version control -------------------------------------------------------
    ("git_status", "Show me the git status of the repository {R} and report it to {O}."),
    ("git_log", "Show the git log of the repository {R} and report it to {O}."),
    ("git_diff", "Show the git diff of the working tree in {R} and report it to {O}."),
    ("git_commit", "Commit the changes in the repository {R} with the message tidy up and report it to {O}."),
    ("git_branch", "Create a branch named feature in the repository {R} and report it to {O}."),
    ("git_checkout", "Check out the previous commit in the repository {R} and report it to {O}."),
    ("git_revert", "Revert the last commit in the repository {R} and report it to {O}."),
    ("git_bisect", "Bisect the history of the repository {R} to find the first bad commit and report it to {O}."),
    ("git_blame", "Blame the lines of {R}/pkg/calc.py and report it to {O}."),
    ("git_stash", "Stash the uncommitted changes in the repository {R} and report it to {O}."),
    ("git_rebase", "Rebase the branch in the repository {R} onto main and report it to {O}."),
    ("merge_conflict", "Resolve the merge conflicts in the repository {R} and report it to {O}."),
    # ---- debugging ------------------------------------------------------------
    ("interactive_debug", "Debug the function add in the repository {R} with breakpoints and report it to {O}."),
    ("crash_repro", "Reproduce the crash in {R}/pkg/calc.py and shrink it to a minimal case, reporting to {O}."),
    # ---- measurement ----------------------------------------------------------
    ("coverage_measure", "Measure the line coverage of the tests in the repository {R} and report it to {O}."),
    ("memory_profile", "Measure the memory usage of the program in the repository {R} and report it to {O}."),
    ("complexity_metric", "Measure the cyclomatic complexity of the python source {R}/pkg and report it to {O}."),
    ("duplication", "Find the duplicated code in the python source {R}/pkg and report it to {O}."),
    ("dead_code", "Find the dead code in the python source {R}/pkg and report it to {O}."),
    # ---- testing --------------------------------------------------------------
    ("fuzz", "Fuzz the function add in {R}/pkg/calc.py and report it to {O}."),
    ("flake_detect", "Find the flaky tests in the repository {R} and report it to {O}."),
    ("differential_test", "Run a differential test of {R}/pkg/calc.py against a reference and report to {O}."),
    # ---- dependencies and supply chain ---------------------------------------
    ("dependency_add", "Add the dependency requests to the project in {R} and report it to {O}."),
    ("vulnerability_audit", "Audit the dependencies in {R} for known vulnerabilities and report it to {O}."),
    ("secret_scan", "Scan the repository {R} for leaked secrets and report it to {O}."),
    ("license_check", "Check the licenses of the dependencies in {R} and report it to {O}."),
    # ---- hygiene and build ----------------------------------------------------
    ("lint", "Lint the python source {R}/pkg and report it to {O}."),
    ("format", "Format the python source {R}/pkg and report it to {O}."),
    ("type_check", "Type check the python source {R}/pkg and report it to {O}."),
    ("build_package", "Build a wheel for the project in {R} and report it to {O}."),
    ("schema_migration", "Write a schema migration for the database in {R} and report it to {O}."),
    ("ci_config", "Write a continuous integration workflow for the repository {R} and report it to {O}."),
    ("changelog", "Write the changelog for the repository {R} and report it to {O}."),
    # ---- runtime quality ------------------------------------------------------
    ("async_audit", "Audit the concurrency in {R}/pkg/calc.py for race conditions and report it to {O}."),
    ("exception_audit", "Audit the exception handling in {R}/pkg/calc.py and report it to {O}."),
    ("resource_leak", "Find the resource leaks in {R}/pkg/calc.py and report it to {O}."),
    ("retry_design", "Make the network calls in {R}/pkg/calc.py retry safely and report it to {O}."),
    ("observability", "Add logging and metrics to {R}/pkg/calc.py and report it to {O}."),
    # ---- refactoring beyond rename/extract ------------------------------------
    ("move_function", "Move the function add from {R}/pkg/calc.py into a new module {R}/pkg/ops.py and report it to {O}."),
    ("inline_function", "Inline the function sub in {R}/pkg/calc.py and report it to {O}."),
    ("change_signature", "Change the signature of the function add in {R}/pkg/calc.py to take a tuple and report it to {O}."),
    # ---- documentation and compatibility -------------------------------------
    ("docstrings", "Write docstrings for the functions in {R}/pkg/calc.py and report it to {O}."),
    ("api_compatibility", "Check whether the change breaks the public api of {R}/pkg and report it to {O}."),
]


def classify(status: str, selected: str, artifact: bool = False) -> str:
    """What the front door did with a request for an act this brain does not have.

    A FAIL with no capability credited and no artifact written is a refusal: the
    machine declined before doing anything, which is honest even when the message
    is vague.  WRONG_TOOL is reserved for the case the word means -- a capability
    was chosen and ran, and it was not the act asked for -- because a vague refusal
    and a wrong tool are different defects and must not be counted as one.
    """
    if status.startswith("PASS"):
        return "SILENTLY_WRONG"
    credited = bool(selected) and selected != "-"
    if status.startswith("FAIL_CLOSED"):
        return "HONEST_REFUSAL"
    if status.startswith("FAIL") and not (credited or artifact):
        return "HONEST_REFUSAL"
    if status.startswith("FAIL"):
        return "WRONG_TOOL"
    return "OTHER"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    ns = ap.parse_args()

    from canonical.runtime import live_brain_route_admission_v1 as adm

    # A previous run's artifacts are not part of this world: a file that already
    # exists changes which path is a "future artifact" and therefore the route.
    shutil.rmtree(WORK, ignore_errors=True)
    repo = build_repo()
    rows = []
    for act, sentence in ACTS:
        if ns.only and act not in ns.only.split(","):
            continue
        out = WORK / "out" / (act + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        goal = sentence.format(R=str(repo), O=str(out))
        try:
            res = adm.solve({"task_id": "MISS_" + act, "goal": goal})
            selected = res.get("capability_id") or res.get("compiled_capability_id") or "-"
            status = str(res.get("status") or "")
            reason = str(res.get("reason") or "")[:160]
        except Exception as exc:  # noqa: BLE001 - a crash is a finding, not an error
            selected, status, reason = "-", "EXC:" + type(exc).__name__, str(exc)[:160]
        wrote = out.is_file()
        verdict = classify(status, selected, wrote)
        # An honest refusal should name the act it cannot perform: "I have no
        # linter" is actionable, "RAW_GOAL_COMPILATION_GAP" is not.
        # Does the refusal name the ACT?  The sentence's first word is the request verb
        # ("Find", "Measure", "Write"), not the act, so it was the wrong question and the
        # answer was always "no" -- the same misreading this probe already had in its
        # ownership check.
        _generic = {"git", "test", "check", "find", "measure", "write", "create", "report",
                    "the", "and", "for", "run", "make", "with"}
        _act_words = [t for t in re.findall(r"[a-z]{4,}", act.lower())
                      if t not in _generic and not t.endswith("ing")]
        named = any(w in (status + " " + reason).lower() for w in _act_words)
        # Does the capability that answered even claim to perform the act?  A
        # refusal that names a substitute is luck, not a refusal: the substitute
        # failed only because it did not produce the promised artifact.
        owns = None
        if selected and selected != "-":
            try:
                from canonical.runtime import live_integrated_brain_v1 as _live
                _entry = _live.load_verified_registry().get(selected) or {}
                # Every keyword is split into the WORDS it is made of.  A capability that
                # declares "type check" names `type` and `check`; comparing whole phrases meant
                # the analyser that answered a type check was reported as not owning it, and a
                # correct answer was counted as a hollow pass -- the third time in this probe
                # that a comparison was made at the wrong granularity.
                _own = (set(re.findall(r"[a-z0-9]+", " ".join(
                            str(x).lower() for x in (_entry.get("keywords") or []))))
                        | set(re.findall(r"[a-z0-9]+", selected.lower()))
                        | set(re.findall(r"[a-z0-9]+", " ".join(_entry.get("provides") or []).lower())))
                # Does the answering capability claim THIS ACT?  The act's own name is the
                # question, not the sentence's first word: measured, this read `head` -- the
                # verb that opens the request ("Show", "Commit") -- against the answering
                # capability's vocabulary, so every act was reported as "does not own the
                # act" no matter who answered it, and the eleven git acts that the registry
                # now owns were counted as hollow passes for being served correctly.
                _tokens = [t for t in re.split(r"[^a-z0-9]+", act.lower()) if t]
                owns = bool(_tokens) and all(
                    any(o == t or o.startswith(t) or t.startswith(o) for o in _own)
                    for t in _tokens)
            except Exception:  # noqa: BLE001 - measurement must not crash the probe
                owns = None
        if verdict == "SILENTLY_WRONG" and owns:
            # The act EXISTS and the capability that answered it is the one that owns it:
            # answering is the correct outcome, not a hollow pass.  The probe was written
            # when no capability performed these acts at all, and its verdict has to say so.
            verdict = "ANSWERED_BY_OWNING_CAPABILITY"
        rows.append({"act": act, "goal": goal, "selected": selected, "status": status[:70],
                     "reason": reason, "verdict": verdict, "artifact": wrote,
                     "refusal_names_the_act": named,
                     "selected_owns_the_act": owns})
        print(f"{act:20s} {verdict:15s} sel={selected[:44]:46s} {status[:44]}", flush=True)

    # A destination that was stated as an ABSOLUTE path can also land inside the
    # repository, mirrored: <root>/home/user/brain/... .  That is the same file
    # written twice, and it is a path-joining defect, so it is reported here
    # rather than cleaned up silently -- a probe that hides its own escapes is
    # the same failure as a gate that can only report PASS.
    escaped = []
    mirrored = ROOT / "home"
    if mirrored.is_dir():
        escaped = sorted(str(p.relative_to(ROOT)) for p in mirrored.rglob("*") if p.is_file())

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    wrongly_accepted = [r["act"] for r in rows if r["verdict"] == "SILENTLY_WRONG"]
    named = sum(1 for r in rows if r["verdict"] == "HONEST_REFUSAL" and r["refusal_names_the_act"])
    refusals = sum(1 for r in rows if r["verdict"] == "HONEST_REFUSAL")
    owned = counts.get("ANSWERED_BY_OWNING_CAPABILITY", 0)
    print("acts now owned by a capability that answers them: %d" % owned)
    print("refusals that name the missing act: %d/%d" % (named, refusals))
    borrowed = [r["act"] for r in rows if r["selected_owns_the_act"] is False]
    print("answered by a capability that does not own the act: %d (%s)"
          % (len(borrowed), ", ".join(borrowed)))
    print("\n" + json.dumps(counts, sort_keys=True))
    print("silently answered (hollow pass):", ", ".join(wrongly_accepted) or "none")
    if escaped:
        print("writes mirrored inside the repository: %d (%s)"
              % (len(escaped), ", ".join(escaped[:3])))
    if ns.json:
        Path(ns.json).write_text(json.dumps({"counts": counts, "escaped_writes": escaped,
                                             "rows": rows}, indent=1),
                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
