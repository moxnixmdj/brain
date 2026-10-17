"""Plain sentence in. Nothing else supplied by a human.

Every capability before this took a hand-filled field: want_tokens=["out",
"report", "raw"]. That is a human translating the goal into machine terms,
and it is exactly what "by itself" forbids. The original objective was a
plain goal string going in the front with no fields filled by hand.

So: derive what is wanted FROM THE SENTENCE.

Then run the whole chain -- discover, guard against undoers, chain
dependencies, rank by observed effect -- and finally check whether the goal
was actually met, rather than assuming it was because something ran.

Verification is deliberately separate from scoring. Scoring chooses between
actions; verification asks whether the job is done. Conflating them is how
a system reports success it never achieved.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_V1"

_STOP = {
    "a", "an", "the", "this", "that", "these", "those", "to", "from", "into",
    "in", "on", "at", "by", "for", "of", "with", "and", "or", "but", "is",
    "are", "was", "were", "be", "been", "it", "its", "using", "use", "make",
    "build", "create", "generate", "produce", "please", "then", "so", "we",
    "i", "you", "should", "can", "could", "would", "do", "does", "did",
    "have", "has", "had", "get", "got", "put", "set", "up", "out",
    # Instruction verbs and filler. "run the formatter" should be about the
    # formatter, not about running: the cobra run produced
    # ['run','formatter','over','source','code'], where three of five tokens
    # were scaffolding. Every noise token dilutes matching and, worse, can
    # match an unrelated artifact that happens to contain the word "code".
    "run", "runs", "running", "execute", "exec", "invoke", "call", "start",
    "over", "under", "onto", "into", "via", "per", "all", "any", "some",
    "more", "most", "want", "need", "like", "just", "also", "now", "new",
    "then", "than", "that", "which", "what", "when", "where", "how",
    "make", "do", "done", "thing", "stuff",
    # NOT "file" and NOT "data" -- both were added here and both were wrong.
    # "produce a report from the data" then tokenised to just ['report'],
    # losing the word that matches data/raw.json. They are content words,
    # not scaffolding. Stripping them trades real signal for tidiness.
}


def goal_tokens(goal: str) -> list[str]:
    """What the sentence is about, with the verbs and filler removed.

    Deliberately NOT a model. A plain, inspectable rule: content words that
    are not stopwords. If it guesses wrong a human can see exactly why.
    """
    words = re.findall(r"[a-z0-9_./]+", (goal or "").lower())
    return [w for w in words if w not in _STOP and len(w) > 1][:12]


_VALIDATOR_WORDS = ("test", "tests", "check", "checks", "verify", "validate",
                    "lint", "audit", "schema", "spec")


# Commands that cannot fail. An oracle's whole job is to be capable of
# saying no, so a command hardwired to succeed is not an oracle no matter
# what it is called -- and counting one lets anything pass by declaring a
# check that always agrees.
# Failures that are facts about the machine, not verdicts on the work.
_ENVIRONMENTAL_FAILURE_CLASSES = frozenset({
    "missing_binary", "missing_python_module", "missing_node_module",
})

_NEVER_FAILS = (
    re.compile(r"^\s*(?::|true)\s*$"),
    re.compile(r"^\s*(echo\b[^&|;]*)?(\s*(?:&&|;)\s*)?exit\s+0\s*$"),
    re.compile(r"^\s*echo\b[^&|;]*$"),
)


def _ground(root: str, paths: list) -> dict:
    """Re-read the artifacts a verdict rests on, and say whether they hold.

    A verdict is a claim about the machine, and a claim that is not
    re-checked is a claim the machine has not confirmed. The snapshot was
    taken when the work happened; between then and the verdict, a destroyer
    task may have removed the file, or a later step may have overwritten
    it. Reading again at the moment of judgement is what catches that --
    and it costs one stat per path.
    """
    try:
        import grounding_v1 as G
    except Exception:
        return {"verdict": "UNVERIFIABLE", "detail": "grounding unavailable",
                "total": 0, "grounded": 0, "unverifiable": 0}
    claims = []
    for path in paths or []:
        rel = os.path.relpath(path, root) if os.path.isabs(str(path)) else str(path)
        claims.append({"path": rel, "exists": True})
    res = G.check_all(claims, root)
    return {"verdict": res["verdict"], "grounded": res["grounded"],
            "unverifiable": res["unverifiable"], "total": res["total"],
            "all_grounded": res["all_grounded"]}


def _can_fail(command: str) -> bool:
    """Could this command ever report failure? If not it is not a check."""
    c = (command or "").strip()
    if not c:
        return False
    return not any(p.match(c) for p in _NEVER_FAILS)


def find_validators(tasks: list[dict]) -> list[dict]:
    """Tasks this environment ships as its own oracle.

    Matching the words is not enough. env_toolchain's package.json declares
    a "test" script -- `echo no tests here && exit 0` -- which matches every
    validator word and can never fail. Treating it as the environment's
    oracle meant the decoy was the judge of its own work.
    """
    out = []
    for t in tasks or []:
        name = (t.get("name") or "").lower()
        command = t.get("command") or ""
        label = "%s %s" % (name, command.lower())
        if not any(w in label for w in _VALIDATOR_WORDS):
            continue
        if not _can_fail(command):
            continue
        out.append(t)
    return out


def verify(goal: str, root: str, before: dict, after: dict,
           produces: dict | None = None,
           validators: dict | None = None) -> dict:
    """Did the goal actually get met? Ask separately from scoring.

    Two routes to an answer:

    LEXICAL  the artifact's own name contains a goal word. Fails when the
             environment names things differently -- a report saved as
             summary.txt matches nothing.

    EVIDENCE the environment declares its own vocabulary. If a task is
             named after the goal, whatever that task demonstrably PRODUCED
             is the goal artifact, whatever the file is called. The link is
             observed, not guessed from a synonym list.

    The second is the fix for lexical brittleness, and it needs no model and
    no hardcoded vocabulary -- it reads the connection out of the place
    itself. Bringing a synonym list would only work for words I thought of.
    """
    tokens = goal_tokens(goal)
    new = sorted(set(after) - set(before))
    # In-place edits count as work. A formatter creates nothing.
    changed = sorted(p for p in set(before) & set(after)
                     if before[p] != after[p])
    touched = new + changed
    if not tokens:
        return {"verified": False, "reason": "NO_GOAL_TOKENS",
                "new_paths": new, "modified_paths": changed}
    if not touched:
        return {"verified": False, "reason": "NOTHING_PRODUCED",
                "new_paths": [], "modified_paths": []}

    # Route ZERO, and it runs FIRST: ASK THE ENVIRONMENT TO JUDGE.
    #
    # Whether an artifact is a valid report is semantic, and this system has
    # no semantics. But projects routinely ship their own oracle: tests,
    # linters, schema checks. If the environment declares a check and that
    # check passes, the artifact is valid BY THE ENVIRONMENT'S OWN STANDARD
    # -- better than any judgement made from outside, because it is the
    # standard that actually governs here.
    #
    # This does not decide correctness. It finds who already did.
    if validators:
        failures = sorted(v for v, ok in validators.items() if not ok)
        if not failures:
            return {"verified": True,
                    "reason": "ENVIRONMENT_VALIDATOR_PASSED",
                    "route": "environment_validator",
                    "validators_run": sorted(validators),
                    "new_paths": new[:10],
                    "modified_paths": changed[:10],
                    "goal_tokens": tokens}
        return {"verified": False,
                "reason": "ENVIRONMENT_VALIDATOR_FAILED",
                "route": "environment_validator",
                "failed": failures,
                "validators_run": sorted(validators),
                "new_paths": new[:10],
                "modified_paths": changed[:10],
                "goal_tokens": tokens}

    hits = [p for p in touched if any(t in p.lower() for t in tokens)]
    if hits:
        grounded = _ground(root, hits[:10])
        if not grounded.get("all_grounded"):
            # It was there a moment ago and is not now. That is not a
            # completed goal; it is work that was undone.
            return {"verified": False, "reason": "ARTIFACT_NOT_GROUNDED",
                    "route": "lexical", "matching": hits[:10],
                    "grounding": grounded,
                    "new_paths": new[:10], "modified_paths": changed[:10],
                    "goal_tokens": tokens}
        return {"verified": True, "reason": "GOAL_ARTIFACT_FOUND",
                "route": "lexical", "matching": hits[:10],
                "grounding": grounded,
                "new_paths": new[:10], "modified_paths": changed[:10],
                "goal_tokens": tokens}

    # Route two: a task named after the goal tells us what it produced.
    bridged, via = [], None
    for cmd, paths in (produces or {}).items():
        key = " ".join(cmd).lower() if isinstance(cmd, (list, tuple)) \
            else str(cmd).lower()
        if any(t in key for t in tokens):
            for path in paths:
                if path in touched:
                    bridged.append(path)
                    via = key
    if bridged:
        matched = sorted(set(bridged))[:10]
        grounded = _ground(root, matched)
        if not grounded.get("all_grounded"):
            return {"verified": False, "reason": "ARTIFACT_NOT_GROUNDED",
                    "route": "environment_evidence", "via_command": via,
                    "matching": matched, "grounding": grounded,
                    "new_paths": new[:10], "goal_tokens": tokens}
        return {"verified": True, "reason": "GOAL_ARTIFACT_FOUND",
                "route": "environment_evidence", "via_command": via,
                "matching": matched, "grounding": grounded,
                "new_paths": new[:10], "goal_tokens": tokens}

    return {"verified": False, "reason": "NO_MATCHING_ARTIFACT",
            "route": None, "matching": [], "new_paths": new[:10],
            "modified_paths": changed[:10],
            "goal_tokens": tokens}


def _ground(root: str, paths: list) -> dict:
    """Re-read the artifacts a verdict rests on, and say whether they hold.

    A verdict is a claim about the machine, and a claim that is not
    re-checked is a claim the machine has not confirmed. The snapshot was
    taken when the work happened; between then and the verdict, a destroyer
    task may have removed the file, or a later step may have overwritten
    it. Reading again at the moment of judgement is what catches that --
    and it costs one stat per path.
    """
    try:
        import grounding_v1 as G
    except Exception:
        return {"verdict": "UNVERIFIABLE", "detail": "grounding unavailable",
                "total": 0, "grounded": 0, "unverifiable": 0}
    claims = []
    for path in paths or []:
        rel = os.path.relpath(path, root) if os.path.isabs(str(path)) else str(path)
        claims.append({"path": rel, "exists": True})
    res = G.check_all(claims, root)
    return {"verdict": res["verdict"], "grounded": res["grounded"],
            "unverifiable": res["unverifiable"], "total": res["total"],
            "all_grounded": res["all_grounded"]}




def _snapshot(root: str) -> dict:
    """Path -> mtime, so IN-PLACE changes are visible.

    The first version recorded only path names, so a tool that rewrites
    existing files -- a formatter, a linter with --fix, any sort of code
    modification -- looked like it had done nothing at all. Running cobra's
    `make fmt` returned NOTHING_PRODUCED, which was simply false: the work
    of a formatter is entirely in-place.
    """
    rootp = Path(root)
    out = {}
    for fp in rootp.rglob("*"):
        if fp.is_file():
            try:
                out[str(fp.relative_to(rootp))] = fp.stat().st_mtime_ns
            except OSError:
                pass
    return out


def _urls_mentioned(root: str, limit: int = 40) -> str:
    """Text of a project's own small files, so a URL written in a README or
    a task file counts as part of the task. Binary and huge files skipped."""
    import re as _re
    out, n = [], 0
    names = ("README", "readme", "TASK", "task", "GOAL", "goal", "NOTES", "notes")
    for path in sorted(Path(root).rglob("*")):
        if n >= limit or not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".rst", ".html", ".json", ".py", ""}:
            continue
        if path.stat().st_size > 200_000:
            continue
        try:
            t = path.read_text(errors="ignore")
        except Exception:
            continue
        if any(k in path.name for k in names) or ".md" == path.suffix.lower():
            out.append(t[:20000]); n += 1
    return "\n".join(out)


def run(goal: str, root: str, binary_limit: int = 0,
        iterations: int = 16) -> dict:
    """Plain sentence in, work out, verified outcome out."""
    import explore_v1 as X
    tokens = goal_tokens(goal)
    before = _snapshot(root)

    # THE BROWSER, chosen by the goal rather than named by a human.
    # If the task is about a page, no amount of reading the filesystem will
    # find the answer, because the answer is not on the filesystem. So look
    # for URLs the goal mentions -- and, if it names none, URLs the project
    # itself mentions -- and load them in a real browser before deciding
    # anything. What matters on a page is often written by script after
    # load, which only a real browser sees.
    #
    # This is not a fallback and it is not a pipe. It is one more sense the
    # loop consults, alongside the directory and the validator.
    browser: dict = {}
    try:
        import browser_v1 as B
        wanted = B.urls_in(goal)
        if not wanted:
            wanted = B.urls_in(_urls_mentioned(root))
        wanted = wanted[:3]
        if wanted:
            ok, why = B.available()
            if not ok:
                browser = {"urls": wanted, "unavailable": why}
            else:
                pages = []
                for u in wanted:
                    try:
                        r = B.state(u)
                    except Exception as exc:
                        pages.append({"url": u, "error": f"{type(exc).__name__}: {exc}"})
                        continue
                    if r.get("ok") and r.get("data"):
                        d = r["data"]
                        hay = ((d.get("text") or "") + " " + (d.get("title") or "")).lower()
                        d["goal_words_on_page"] = sorted({t for t in tokens if t in hay})
                        pages.append(d)
                browser = {"urls": wanted, "pages": pages,
                           "loaded": sum(1 for p in pages if p.get("chars"))}
    except Exception as exc:
        browser = {"error": f"{type(exc).__name__}: {exc}"}

    # LOOK BEFORE ACTING.
    # env_monster2 made acting first unrecoverable. The environment's own
    # check and the scripts themselves are plain text sitting in the
    # directory; reading them says which command produces what the check
    # demands. Commands whose source satisfies the oracle are run first;
    # ones we could read and that contradict it go last. Unreadable ones
    # keep their place -- unread is not the same as wrong.
    look: dict = {}
    try:
        import taskfile_read_v1 as TF
        import look_before_v1 as LB
        tasks = TF.read_tasks(root)
        vsrc = LB.scripts_named(["check.py"], Path(root))
        if not vsrc:
            for t in LB.__dict__.get("find_validators", lambda x: []) (tasks):
                pass
        # validator sources: any local script a validator command names
        for t in find_validators(tasks):
            vsrc += LB.scripts_named(t.get("command", "").split(), Path(root))
        cmds0 = [["sh", "-c", t["command"]] for t in tasks if t.get("command")]
        if vsrc and cmds0:
            look = LB.choose(cmds0, root, list(dict.fromkeys(vsrc)))
    except Exception:
        look = {}
    # Act on what reading revealed: do not run what the sources contradict.
    # Only exclude RIVALS -- demoted commands writing where a preferred one
    # writes. Excluding all demoted commands dropped fetch.py in
    # env_monster, which transform.py depends on, breaking a chain the
    # system already knew how to build. A prerequisite is not a rival.
    exclude = {" ".join(c) for c in (look.get("rivals") or [])}
    if exclude:
        look = dict(look, excluded=[ " ".join(c) for c in (look.get("rivals") or [])])
    # FIT THE ENVIRONMENT TO THE MACHINE.
    #
    # Every command this project declares may be impossible here -- pytest
    # is not installed, and a project that only ever says "pytest -q" gives
    # nothing runnable. Rather than run the declared commands and report
    # failure, work out what would actually test it, prove it by running it,
    # and if the environment's own oracle names a file to write, put the
    # evidence there.
    #
    # The command chosen is often one no file in the project mentions. Its
    # warrant is not a template but evidence: the tests import unittest, so
    # unittest discover collects them -- and then it ran, and three tests ran.
    fit_info: dict = {}
    try:
        import subprocess as _sp
        import taskfile_read_v1 as _TF
        import look_before_v1 as _LB
        import environment_fit_v1 as EF
        # The file to write is named by the oracle itself, in its own source.
        # look_before's requirements are the strings a command must produce,
        # which is a different thing and told the wrong story here: check.py
        # mentions "All tests passed" only in the branch that FAILS, so
        # preferring a command that emits it preferred the decoy. The path
        # literal is unambiguous -- the oracle names the file it will read.
        vsrc2 = _LB.scripts_named(["check.py"], Path(root))
        for _t in find_validators(_TF.read_tasks(root)):
            vsrc2 += _LB.scripts_named(_t.get("command", "").split(), Path(root))
        reqs = []
        for _src in vsrc2:
            try:
                # literals() reads the file itself, so it takes the path.
                # Converting to text first (done once, wrongly) made every
                # call fail with 'str' object has no attribute read_text and
                # silently yielded no requirements at all -- the kind of
                # breakage that reports a clean empty result rather than an
                # error, which is why it survived a full run unnoticed.
                _lits = _LB.literals(_src)
            except Exception:
                continue
            for _lit in _lits:
                if ("/" in _lit and ".." not in _lit and len(_lit) < 80
                        and _lit.endswith((".txt", ".json", ".xml", ".log"))):
                    if _lit not in reqs:
                        reqs.append(_lit)
        cmd, src, why = EF.best_test_command(root)
        if cmd and reqs:
            # VERIFY BEFORE COMMITTING. The fit was previously run and its
            # output written to the artifact, and only afterwards checked --
            # plan, execute, verify in the wrong order. The repair is now
            # offered as a proposal to the universal solver, whose verifier
            # is immutable, and the file is written only once that verifier
            # has accepted it. A rejected proposal leaves nothing behind.
            # The universal solver imports itself as canonical.runtime.*, so
            # the repo root has to be importable, not just this directory.
            import sys as _sys
            _pkg_root = str(Path(__file__).resolve().parents[2])
            if _pkg_root not in _sys.path:
                _sys.path.insert(0, _pkg_root)
            from canonical.runtime import repair_proposal_v1 as RP
            prop = RP.propose(cmd, root, min_tests=1, timeout=300)
            verdict = prop.get("solver") or {}
            fit_info = {"command": prop.get("repaired_command") or cmd,
                        "source": src, "why": why,
                        "observed": prop.get("observed"),
                        "solver": verdict.get("status"),
                        "verified": bool(verdict.get("pass"))}
            if not verdict.get("pass"):
                fit_info["note"] = "solver did not verify; nothing written"
                raise RuntimeError("SOLVER_DID_NOT_VERIFY")
            out = prop.get("output") or ""
            for req in reqs:
                target = Path(root) / req
                if target.parent.is_dir():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(out)
                    fit_info["wrote"] = req
                    # A report we just proved correct can still be clobbered:
                    # the decoy also writes out/report.txt, and running it
                    # afterwards replaced real evidence with "All tests
                    # passed". Producing the right thing and then letting
                    # something overwrite it is the same as never producing it.
                    try:
                        for _t2 in _TF.read_tasks(root):
                            _cmd2 = (_t2.get("command") or "").strip()
                            if not _cmd2 or _cmd2 == cmd:
                                continue
                            if req in (_LB.output_paths(["sh", "-c", _cmd2], root) or []):
                                exclude.add("sh -c " + _cmd2)
                                fit_info.setdefault("excluded", []).append(_cmd2)
                    except Exception:
                        pass
                    break
    except Exception as exc:
        fit_info = {"error": f"{type(exc).__name__}: {exc}"}

    result = X.explore_here(root, want_tokens=tokens,
                            binary_limit=binary_limit,
                            iterations=iterations,
                            interaction_aware=True,
                            compose_aware=True, exclude=exclude)
    # NOTHING YET? GIVE THE DECLARED TASKS THE SAME REPAIR.
    #
    # A command that fails because the directory it writes into does not
    # exist produces no files at all, and a loop that only asks whether
    # files appeared cannot tell that apart from a command that genuinely
    # did nothing. Before concluding the goal was not met, the tasks this
    # environment declares are run through the same repair path the
    # validators already get. If they still produce nothing, "nothing was
    # produced" is a fact rather than a guess.
    try:
        _now = _snapshot(root)
        _touched = bool(set(_now) - set(before)) or any(
            before[p] != _now[p] for p in set(before) & set(_now))
        if not _touched:
            import repair_v1 as _RP
            for _t in (tasks or []):
                _c = _t.get("command")
                if _c:
                    _RP.attempt(_c, root, timeout=180)
    except Exception:
        pass
    after = _snapshot(root)
    produces = {}
    try:
        import interaction_v1 as IA
        import discover_v1 as DISCOVER
        cmds = DISCOVER.candidates(root, binary_limit=binary_limit)
        produces = IA.analyze(root, cmds).get("produces") or {}
    except Exception:
        produces = {}
    # Route three: run the environment's own checks and let them judge.
    validators: dict = {}
    unevaluable: list = []
    try:
        import subprocess as _sp
        import taskfile_read_v1 as TF
        for t in find_validators(TF.read_tasks(root)):
            cmd = t.get("command")
            if not cmd:
                continue
            # Use the runner the project would use, not the raw text.
            # npm scripts need node_modules/.bin on PATH, which only
            # `npm run` provides -- executing "mocha ..." directly fails
            # with command-not-found and makes a working project look
            # broken. Same rationale as taskfile_read_v1.task_commands.
            origin = (t.get("origin") or "").lower()
            if origin.endswith("package.json") and t.get("name"):
                argv = ["npm", "run", "--silent", t["name"]]
            else:
                argv = ["sh", "-c", cmd]
            try:
                if argv[:1] == ["npm"]:
                    rc = _sp.run(argv, cwd=root,
                                 capture_output=True, timeout=180).returncode
                    validators[cmd] = (rc == 0)
                else:
                    # A validator that fails because a tool is absent here
                    # is a fact about this machine, not evidence about the
                    # work. Give the oracle the same adaptation everything
                    # else gets: only a failure that survives repair is a
                    # real failure. `pytest -q` in env_toolchain is the
                    # environment's declared check and pytest does not
                    # exist -- repaired to unittest, it runs and passes.
                    import repair_v1 as _RP
                    res = _RP.attempt(cmd, root, timeout=180)
                    if res.get("ok"):
                        validators[cmd] = True
                    else:
                        # A check that cannot be RUN is not a check that
                        # failed. pytest_run.py imports pytest and pytest
                        # cannot be obtained here; that is a fact about
                        # this machine, not evidence about the work. Counting
                        # it as a failure would report our missing tool as
                        # somebody else's broken build.
                        classes = {a.get("class") for a in res.get("attempts", [])}
                        if classes and classes <= _ENVIRONMENTAL_FAILURE_CLASSES:
                            if cmd not in unevaluable:
                                unevaluable.append(cmd)
                        else:
                            validators[cmd] = False
            except Exception:
                validators[cmd] = False
    except Exception:
        validators = {}

    check = verify(goal, root, before, after, produces=produces,
                   validators=validators)
    return {"schema": SCHEMA,
            "goal": goal,
            "goal_tokens": tokens,
            "discovered": result.get("commands_discovered"),
            "excluded_as_undoer": result.get("excluded_as_undoer") or [],
            "retried": (result.get("chained") or {}).get("retried") or [],
            "best": result.get("best"),
            "browser": browser,
            "environment_fit": fit_info,
            # Reported, not dropped: a check we could not run is part of the
            # honest answer, and hiding it would make the pass look cleaner
            # than it is.
            "unevaluable_validators": unevaluable,
            "look_before": {"requirements": look.get("requirements", []),
                            "excluded": look.get("excluded", []),
                            "preferred": [" ".join(c) for c in look.get("preferred", [])],
                            "demoted": [" ".join(c) for c in look.get("demoted", [])]},
            "verification": check,
            "model_dependency_count": 0}


if __name__ == "__main__":
    import json
    g = sys.argv[1] if len(sys.argv) > 1 else "produce a report from the data"
    r = sys.argv[2] if len(sys.argv) > 2 else str(ROOT)
    print(json.dumps(run(g, r), indent=2)[:1200])
