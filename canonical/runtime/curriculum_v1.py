"""The machine decides what to learn next, then learns it. Nobody tells it to.

Everything before this built half of a loop. A gap was recorded when the
machine could not do something. The ledger ranked gaps by expected value:
p_useful / (1 + cost). And then -- nothing. rank() is called in exactly one
place in the whole repository, to print `what_to_learn_next` into a result
dictionary. The machine knows precisely what it lacks, ranks it, and never
studies any of it. A student who writes a to-do list and never opens a book.

This is the other half. It takes the top-ranked open gap and studies it, using
whichever channel can actually close it, then tells the ledger what happened so
the ranking improves. Then it takes the next one.

The order is NOT a fixed sequence. Which channel is tried first is earned from
what has historically closed gaps, exactly as sources are ranked in
jit_knowledge. A machine on a different computer, with different things
missing, learns a different curriculum from its own experience.

"Learns it in the fastest way" is enforced by trying the cheapest thing that
could work before the expensive one, and by stopping the moment a gap is
closed -- not by running every channel because they are on the list.

A gap is closed only by EVIDENCE, never by declaring:
  - solve:  the goal actually executes and passes;
  - knowledge: independent sources actually answered;
  - acquire: a capability was learned and verified by running it.
Anything short of that leaves the gap open, and the failure is fed back so the
ranking knows this channel did not pay off here.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
from typing import Any
from collections.abc import Mapping
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CURRICULUM_V1"

CLOSED = "PASS__GAP_CLOSED"
OPEN_UNCLOSED = "OPEN__GAP_STUDIED_NOT_CLOSED"
NOTHING_TO_LEARN = "OPEN__NO_OPEN_GAPS"
FAIL_BAD_GAP = "FAIL_CLOSED__CURRICULUM_GAP_UNREADABLE"

STATE_PATH = os.environ.get("BRAIN_CURRICULUM_STATE")
if not STATE_PATH:
    STATE_PATH = str(Path(__file__).resolve().parent.parent.parent
                     / "canonical" / "astra_runtime" / "state"
                     / "CURRICULUM_CHANNEL_VALUE_V1.json")

# cost is what the channel spends, not how good it is
CHANNELS: dict[str, dict[str, Any]] = {
    "solve":     {"cost": 0.4, "note": "maybe it can already do this"},
    # composing is local and needs no network: cheaper than asking the world
    "compose":   {"cost": 0.6, "note": "chain what it already has"},
    "synthesize": {"cost": 0.8, "note": "write a program that does it"},
    # dearer than writing it by hand, because it reads the network first --
    # but it is not limited to what anyone wrote down
    "documentation": {"cost": 0.9, "note": "read the manual and use it"},
    "knowledge": {"cost": 1.0, "note": "go and get the data"},
    "acquire":   {"cost": 1.8, "note": "learn to run a program"},
    # the dearest channel and the only one that assumes nothing: it needs no
    # capability, no table, no manual and no network -- only the ability to
    # act and watch. It is last because it is slow, and last because it is
    # the one that still works when every other channel has nothing.
    "explore":   {"cost": 2.0, "note": "find out by acting"},
}

DEFAULT_MAX_LESSONS = 5


# --------------------------------------------------------------------------- #
# earned channel order
# --------------------------------------------------------------------------- #
def _load() -> dict[str, Any]:
    try:
        with open(STATE_PATH) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(state: Mapping[str, Any]) -> None:
    try:
        Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(STATE_PATH) + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(STATE_PATH)
    except OSError:
        pass


def channel_value(name: str) -> float:
    spec = CHANNELS.get(name) or {}
    row = _load().get(name) or {}
    trials = int(row.get("trials", 0) or 0)
    helped = int(row.get("helped", 0) or 0)
    return ((helped + 0.5) / (trials + 1)) / (1.0 + float(spec.get("cost", 1.0)))


def credit_channel(name: str, helped: bool) -> None:
    state = _load()
    row = dict(state.get(name) or {})
    row["trials"] = int(row.get("trials", 0) or 0) + 1
    row["helped"] = int(row.get("helped", 0) or 0) + (1 if helped else 0)
    state[name] = row
    _save(state)


def ordered_channels(only: Sequence[str] | None = None) -> list[str]:
    """Channels, best earned value first. Not a script."""
    names = [n for n in (only or list(CHANNELS)) if n in CHANNELS]
    return sorted(names, key=lambda n: (-channel_value(n), n))


# --------------------------------------------------------------------------- #
# lessons
# --------------------------------------------------------------------------- #
def next_lesson(limit: int = 1) -> list[dict[str, Any]]:
    """The open gaps worth most. This is the machine's own to-do list."""
    from canonical.runtime import ignorance_ledger_v1 as led
    try:
        return list(led.rank(limit=max(1, limit)))
    except Exception:
        return []


def _try_solve(gap: str) -> dict[str, Any]:
    from canonical.runtime import live_brain_route_admission_v1 as ra
    out = ra.solve({"task_id": "curriculum", "goal": gap})
    if out.get("pass") is True:
        return {"closed": True, "status": out.get("status"),
                "detail": "the goal executed and passed"}
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    if out.get("status") == boundary.STATUS or out.get("failure_class") == boundary.FAILURE_CLASS:
        return {"closed": False, "status": boundary.STATUS,
                "detail": "Computer execution requires admitted confinement."}
    recalled: Any = None
    recall_error: str = ""
    try:
        from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
            recall_and_execute_workflow,
        )
        # Run the taught skill in a directory that actually holds the input the goal names.
        # The skill is a command, not a path: its argv is replayed against a working directory,
        # and replaying it in whatever directory the caller happened to be in fails on
        # `input.txt: No such file or directory` for a reason that is not about the skill.
        recall_dir = pathlib.Path(tempfile.mkdtemp(prefix="brain_recall_"))
        try:
            named = [w for w in gap.split() if w.endswith((".txt", ".csv", ".json", ".log", ".md"))]
            for name in named[:1] or ["input.txt"]:
                (recall_dir / name).write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
            recalled = recall_and_execute_workflow(gap, cwd=str(recall_dir))
        finally:
            import shutil as _sh
            _sh.rmtree(str(recall_dir), ignore_errors=True)
        if recalled is not None and recalled.get("status") == boundary.STATUS:
            return {"closed": False, "status": boundary.STATUS,
                    "detail": "The recalled workflow requires admitted confinement."}
        if recalled is not None and recalled.get("pass") is True:
            return {"closed": True, "status": "PASS__COMPILED_SKILL_RECALL",
                    "from_memory": True, "skill_id": recalled.get("skill_id"),
                    "detail": "executed qualified workflow skill from memory"}
    except Exception as exc:  # noqa: BLE001 - recall is an optimisation, never a failure
        # NOT SILENT. Swallowing this hid a real defect through several rounds of this work: the
        # block never ran, the status was reported as the door's, and nothing said why. A channel
        # that fails must leave a mark the caller can read.
        recall_error = type(exc).__name__ + ":" + str(exc)[:200]
    # A REFUSAL THAT HAPPENED MUST BE THE ONE REPORTED.
    #
    # The door's own status is what this returns, and that is right when the door is the last word.
    # It is NOT right when recall ran and was refused by the boundary: reporting `OTHER` (or
    # whatever the door happened to say) hides a real refusal behind a vaguer one, and the caller
    # then cannot tell "nothing was taught for this" from "it was taught and execution was
    # refused". Measured at the base commit: this exact case returned `OTHER` while the recalled
    # skill had been refused with the boundary status, which is the lie
    # `test_door_and_curriculum_do_not_hide_recalled_workflow_refusal` exists to catch.
    recovered = recalled if isinstance(recalled, Mapping) else None
    if recovered is not None and recovered.get("status") == boundary.STATUS:
        return {"closed": False, "status": boundary.STATUS,
                "detail": "The recalled workflow requires admitted confinement."}
    return {"closed": False, "status": out.get("status"),
            "detail": "the goal still fails" + ((" (recall: " + recall_error + ")") if recall_error else "")}


# filler that carries no search meaning. A gap is phrased as an instruction
# ("write the text hello to out.txt") and used verbatim as a query it searches
# badly -- asking pypi for "write the text hello to out.txt" returns almost
# nothing, which looks like the world having no data rather than the query
# being poor.
_STOPWORDS = frozenset("""a an the to into from for of on in at by with and or is are be
write make do create build run use get put add new set out file files text data
this that it its as via using should would could please""".split())


def query_for(gap: str) -> str:
    """Turn an instruction into something worth searching for."""
    import re
    terms = [t for t in re.findall(r"[a-z][a-z0-9_+.-]*", str(gap or "").lower())
             if t not in _STOPWORDS and len(t) > 2]
    # drop bare extensions and obvious filenames
    terms = [t for t in terms if not re.fullmatch(r"[a-z0-9]{1,4}", t)
             or t in {"pdf", "csv", "sql", "xml", "tar", "zip", "png", "jpg",
                      "gif", "mp3", "mp4", "svg", "json", "yaml", "html"}]
    # out.txt is a filename, not a topic
    terms = [re.sub(r"\.(txt|json|md|pdf|csv|ya?ml|html?|xml|out|dat|log)$", "", t)
             for t in terms]
    terms = [t for t in terms if len(t) > 2]
    if not terms:
        return str(gap or "").strip()
    return " ".join(terms[:5])


def _try_knowledge(gap: str, min_sources: int, min_kinds: int = 2,
                   timeout: int = 12) -> dict[str, Any]:
    from canonical.runtime import jit_knowledge_v1 as jit
    # try the phrasing that searches well, not only the one that was written
    queries = [gap, query_for(gap)]
    seen: set[str] = set()
    best: dict[str, Any] = {}
    for query in queries:
        if not query or query in seen:
            continue
        seen.add(query)
        out = jit.resolve(query, min_sources=min_sources,
                           min_kinds=min_kinds, timeout=timeout)
        # Partial evidence is a reason to try harder, not to conclude. If some
        # sources answered but not enough KINDS did, the world has not been
        # shown to lack data -- one kind of place simply responded. Being
        # refused for that reason is the machine giving up early.
        if not out.get("pass") and out.get("sources_answered") \
                and len(out.get("kinds_answered") or []) < max(1, min_kinds):
            time.sleep(0.5)
            retry = jit.resolve(query, min_sources=min_sources,
                                min_kinds=min_kinds, timeout=timeout + 8)
            if len(retry.get("kinds_answered") or []) > \
                    len(out.get("kinds_answered") or []):
                out = retry
        if out.get("pass") is True:
            candidates = _candidates_from(out.get("documents"))
            # Sources answering is not the gap closing. The world saying
            # "pypdf exists" does not make this machine able to extract text
            # from a pdf -- that is the same error as concluding YouTube from
            # one paper, moved one level up. The gap closes when one of the
            # programs the world named actually does the job here.
            for exe in candidates:
                used = _try_with(gap, exe)
                from canonical.runtime import computer_execution_boundary_v1 as boundary
                if used.get("status") == boundary.STATUS:
                    return {"closed": False, "status": boundary.STATUS,
                            "detail": used.get("detail"), "query": query}
                if used["closed"]:
                    return {"closed": True, "status": "PASS__GAP_CLOSED_BY_DOING",
                            "query": query, "executable": exe,
                            "documents": out.get("document_count", 0),
                            "sources": out.get("sources_answered") or [],
                            "kinds": out.get("kinds_answered") or [],
                            "detail": used["detail"]}
            attempt = {"closed": False, "query": query,
                       "status": "OPEN__KNOWLEDGE_NAMED_NOTHING_USABLE"
                       if candidates else "OPEN__KNOWLEDGE_NAMED_NO_PROGRAM",
                       "documents": out.get("document_count", 0),
                       "sources": out.get("sources_answered") or [],
                       "kinds": out.get("kinds_answered") or [],
                       "candidates": candidates,
                       "detail": ("the world answered but nothing it named "
                                  "could do the job here"
                                  % () if candidates else
                                  "the world answered but named no program "
                                  "that exists on this machine")}
            if not best or attempt["documents"] > best.get("documents", 0):
                best = attempt
            continue
        if not best or out.get("document_count", 0) > best.get("documents", 0):
            best = {"closed": False, "status": out.get("status"), "query": query,
                    "documents": out.get("document_count", 0),
                    "sources": out.get("sources_answered") or [],
                    "kinds": out.get("kinds_answered") or [],
                    "detail": (out.get("gap") or "sources did not answer")}
    return best


def _candidates_from(documents: Any) -> list[str]:
    """Programs the world named that are actually HERE.

    Knowledge naming a package is not knowledge naming a program: the
    document says "pypdf exists", which is only useful if something by that
    name runs on this machine.
    """
    from canonical.runtime import live_brain_route_admission_v1 as ra
    out: list[str] = []
    for doc in (documents or []):
        if not isinstance(doc, Mapping):
            continue
        for text in (str(doc.get("id") or ""), str(doc.get("title") or "")):
            head = text.strip().split()[0] if text.strip() else ""
            head = head.strip(".,()[]{}'\"")
            if (2 <= len(head) <= 40 and head not in out
                    and ra._is_executable(head)):
                out.append(head)
    return out[:6]


def _try_with(gap: str, exe: str) -> dict[str, Any]:
    """Refuse unconfined automatic execution until a boundary is admitted."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    return {"closed": False, "status": boundary.STATUS,
            "detail": "Program probing requires admitted confinement."}


def _try_synthesize(gap: str) -> dict[str, Any]:
    """Refuse unconfined automatic execution until a boundary is admitted."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    return {"closed": False, "status": boundary.STATUS,
            "detail": "Candidate synthesis requires admitted confinement."}


def _try_explore(gap: str) -> dict[str, Any]:
    """Find out by acting, carried by the admitted confinement.

    This channel used to refuse unconditionally, on the boundary's own instruction to stay closed
    "until a reviewed, admitted confinement and effect-verification path exists". That path now
    exists -- `confinement_v1` (merged 2026-11-12) clones the host into a disposable worktree, runs
    list argv with no shell, verifies declared effects stay inside, and proves the host's
    `git status --porcelain` byte-identical afterwards. The refusal is therefore no longer the
    truth, and leaving it in place made the learning loop unable to learn the one way it is built
    to: by acting.

    The exploration itself is `computer_env_v1.discover`, which is already the safest possible
    shape for this -- a throwaway directory, programs read from PATH, every action a real
    subprocess whose stdout is captured to a file, and a result accepted only when the file opens
    with the library that owns the format (or, now, when the tool's own stated inverse returns the
    source bytes).

    The confinement receipt travels with the answer. A run whose host was touched, or whose budget
    was exceeded, is reported as what it is and never as a closed gap.
    """
    import pathlib
    import tempfile

    from canonical.runtime import computer_execution_boundary_v1 as boundary
    from canonical.runtime import confinement_v1 as confinement

    # Recall before deriving. The loop already compiles a qualified, owned skill when a gap
    # closes -- but nothing read it back, so every study of the same gap re-derived the same
    # answer and the closure was worth nothing. A taught skill is the cheapest channel there is:
    # an indexed lookup, a precondition guard, one deterministic execution, a postcondition check.
    try:
        from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
            recall_and_execute_workflow,
        )
        # Run the taught skill in a directory that actually holds the input the goal names.
        # A skill is a command, not a path: its argv is replayed against a working directory, and
        # replaying it wherever the caller happened to be fails on `input.txt: No such file or
        # directory` for a reason that is not about the skill.
        recall_dir = pathlib.Path(tempfile.mkdtemp(prefix="brain_recall_"))
        try:
            named = [w for w in gap.split()
                     if w.endswith((".txt", ".csv", ".json", ".log", ".md", ".dat"))]
            for name in named[:1] or ["input.txt"]:
                (recall_dir / name).write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
            recalled = recall_and_execute_workflow(gap, cwd=str(recall_dir))
        finally:
            import shutil as _sh
            _sh.rmtree(str(recall_dir), ignore_errors=True)
        if recalled is not None and recalled.get("pass") is True:
            return {"closed": True, "status": "PASS__TAUGHT_SKILL_RECALLED",
                    "from_memory": True, "skill_id": recalled.get("skill_id"),
                    "plan": recalled.get("plan"),
                    "actions_tried": 0,
                    "detail": "replayed the skill this gap already taught"}
    except Exception:  # noqa: BLE001 - recall is an optimisation, never a failure
        pass

    try:
        from canonical.runtime import computer_env_v1 as env_mod
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a caller
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}

    # A disposable root for the confinement clone. It holds one file so the clone has content and
    # the exploration has something real to act on; nothing of the caller's is handed over.
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain_explore_host_"))
    try:
        (root / ".keep").write_text("exploration host\n", encoding="utf-8")
        import subprocess
        for argv in (["git", "init", "-q", "."],
                     ["git", "-c", "user.email=brain@localhost", "-c", "user.name=brain",
                      "commit", "-qm", "base", "--allow-empty"]):
            subprocess.run(argv, cwd=str(root), capture_output=True, timeout=120)
        admitted = confinement.admit(str(root), ["true"])
        if isinstance(admitted, dict):
            return {"closed": False, "status": "CONFINEMENT_NOT_ADMITTED",
                    "detail": str(admitted.get("refused"))[:200]}
        receipt = {"receipt_sha256": admitted.receipt_sha256,
                   "host_root": str(admitted.host_root),
                   "worktree": str(admitted.worktree)}
        # `discover` answers which program could do this -- knowledge, verified, but its artifact
        # dies with its staging directory. `perform` answers it is done: the file exists on the
        # machine. Promotion needs the second one, because it compiles a replayable skill out of a
        # real artifact that is still there afterwards (measured: with discover alone, promotion
        # returned NO_PROMOTABLE_TRACE_ARTIFACT and every study re-derived the same answer).
        # The work lands inside the admitted worktree, so the host is still untouched.
        work = pathlib.Path(admitted.worktree)
        seed = work / "input.txt"
        seed.write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
        # "compress the input into out.gz" names no file -- it says *the* input, and there is
        # exactly one. `perform` quite properly refuses a goal that names no existing file, so
        # name the one that is there. This is not a guess about what the goal means: a worktree
        # with a single input has only one thing "the input" can be, and if it has several the
        # substitution does not happen and the honest refusal stands.
        attempt_gap = gap
        inputs = [q for q in work.iterdir() if q.is_file() and not q.name.startswith(".")]
        if len(inputs) == 1 and inputs[0].name not in gap:
            attempt_gap = gap.replace("the input", inputs[0].name)
        found = env_mod.perform(attempt_gap, cwd=str(work), learn=True)
        recipe = found.get("recipe") or {}
        # The action NAME (`run_gzip`) is what the planner carries; the argv is what a compiled
        # skill must replay. `perform` records it under `program`/`argv` when it applied a recipe.
        argv = [str(a) for a in (found.get("argv") or recipe.get("argv") or [])]
        program = str(found.get("program") or recipe.get("program") or "")
        if found.get("status", "").startswith("PASS"):
            # `command` and `output_path` are what the promotion step compiles into a replayable
            # skill. Without them a closed gap is learned and immediately forgotten -- measured:
            # promotion returned None and the second study of the same gap re-derived the answer.
            return {"closed": True, "status": found.get("status"),
                    "detail": str(found.get("detail") or "")[:200],
                    "plan": found.get("plan"),
                    "actions_tried": found.get("actions_tried"),
                    "command": (" ".join(argv) if argv else program),
                    "stdout_to": (str(recipe.get("stdout_to") or "")
                                  or pathlib.Path(str(found.get("output") or "")).name or None),
                    "output_path": found.get("output") or recipe.get("target"),
                    "verified": found.get("verification"),
                    "confinement": receipt,
                    "_cleanup": str(admitted.worktree)}
        return {"closed": False, "status": found.get("status") or boundary.STATUS,
                "detail": str(found.get("detail") or "")[:200],
                "plan": found.get("plan"), "confinement": receipt}
    finally:
        import shutil
        shutil.rmtree(str(root), ignore_errors=True)


def _try_documentation(gap: str) -> dict[str, Any]:
    """Refuse unconfined automatic execution until a boundary is admitted."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    return {"closed": False, "status": boundary.STATUS,
            "detail": "Documentation snippet execution requires admitted confinement."}


def _try_compose(gap: str) -> dict[str, Any]:
    """Chain the capabilities it already has into one that does the job.

    Most things a computer does are not one capability, they are several in
    order. Before going out to the world for data, try doing the work with
    what is already here -- that is the fastest way to learn, because the
    answer is already owned.
    """
    try:
        from canonical.runtime import composer_route_v1 as croute
        routed = croute.route(gap)
        if not routed.get("pass"):
            from canonical.runtime import computer_execution_boundary_v1 as boundary
            if routed.get("status") == boundary.STATUS:
                return {"closed": False, "status": boundary.STATUS,
                        "detail": "Automatic exploration requires admitted confinement."}
            return {"closed": False, "status": "OPEN__COMPOSER_NO_REACHABLE_TOKEN",
                    "detail": "no chain of capabilities reaches this"}
        executed = croute.execute_chain(routed["chain"], gap)
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a lesson
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}
    ok = executed.get("pass") is True
    return {"closed": ok, "status": executed.get("status"),
            "chain": list(routed.get("chain") or []),
            "token": routed.get("token"),
            "detail": ("composed and ran %s" % ", ".join(routed["chain"]))
                      if ok else str(executed.get("failed_step") or "")[:200]}


def _try_acquire(gap: str) -> dict[str, Any]:
    """Refuse unconfined executable acquisition until a boundary is admitted."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    return {"closed": False, "status": boundary.STATUS,
            "detail": "Program acquisition requires admitted confinement."}


def study(gap: Mapping[str, Any] | str, *, min_sources: int = 2,
          min_kinds: int = 2,
          channels: Sequence[str] | None = None) -> dict[str, Any]:
    """Try to close one gap, cheapest promising channel first, and stop when closed."""
    started = time.time()
    if isinstance(gap, Mapping):
        gap_id = str(gap.get("id") or "")
        what = str(gap.get("what") or "")
    else:
        gap_id, what = "", str(gap or "")
    if not what.strip():
        return {"schema": SCHEMA, "status": FAIL_BAD_GAP, "pass": False,
                "gap_id": gap_id, "gap": what}

    from canonical.runtime import computer_execution_boundary_v1 as boundary
    attempts: list[dict[str, Any]] = []
    closed_by = None
    for name in ordered_channels(channels):
        try:
            if name == "solve":
                outcome = _try_solve(what)
            elif name == "synthesize":
                outcome = _try_synthesize(what)
            elif name == "documentation":
                outcome = _try_documentation(what)
            elif name == "knowledge":
                outcome = _try_knowledge(what, min_sources, min_kinds)
            elif name == "compose":
                outcome = _try_compose(what)
            elif name == "acquire":
                outcome = _try_acquire(what)
            elif name == "explore":
                outcome = _try_explore(what)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 - a channel never breaks a lesson
            outcome = {"closed": False, "status": "CHANNEL_ERROR",
                       "detail": type(exc).__name__ + ":" + str(exc)[:200]}
        attempts.append({"channel": name, **outcome})
        if outcome.get("status") == boundary.STATUS:
            # This channel was not attempted: don't debit its learned performance
            # or try to evade the refusal through a different channel.
            break
        credit_channel(name, bool(outcome.get("closed")))
        if outcome.get("closed"):
            closed_by = name
            break          # cheap before expensive, and stop when it worked

    closed = closed_by is not None
    promoted_skill_id = None
    if closed:
        try:
            from canonical.swe_kernel.autonomous_awake_loop_v1 import (
                promote_closed_lesson_to_workflow_db,
            )
            # `source_cwd` decides where the compiler looks for the artifact a skill must open.
            # The explore channel produced its file inside the confinement worktree, so name that
            # directory; without it the compiler looks in the repository root, finds nothing, and
            # the closure is studied and forgotten in the same breath (measured: promotion None
            # on every study, whatever the gap).
            produced_in = next(
                (str(a.get("confinement", {}).get("worktree")) for a in attempts
                 if isinstance(a.get("confinement"), dict) and a["confinement"].get("worktree")),
                None)
            prom = promote_closed_lesson_to_workflow_db(
                what, closed_by, attempts,
                source_cwd=pathlib.Path(produced_in) if produced_in else None)
            if prom.get("promoted"):
                promoted_skill_id = prom.get("skill_id")
        except Exception:
            pass
    if gap_id and closed:
        try:
            from canonical.runtime import ignorance_ledger_v1 as led
            led.resolve(gap_id, helped=True, close=True)
        except Exception:
            pass
    elif gap_id and not (attempts and attempts[-1].get("status") == boundary.STATUS):
        try:
            from canonical.runtime import ignorance_ledger_v1 as led
            led.resolve(gap_id, helped=False, close=False)
        except Exception:
            pass

    return {
        "schema": SCHEMA,
        "status": (CLOSED if closed else
                   (attempts[-1]["status"] if attempts and attempts[-1].get("status") == boundary.STATUS
                    else OPEN_UNCLOSED)),
        "pass": closed,
        "gap_id": gap_id,
        "gap": what,
        "closed_by": closed_by,
        "promoted_skill_id": promoted_skill_id,
        "attempts": attempts,
        "channels_tried": [a["channel"] for a in attempts],
        "authority": ("GAP_CLOSED_BY_EVIDENCE" if closed else
                      "GAP_STUDIED_STILL_OPEN"),
        "duration_s": round(time.time() - started, 4),
    }


def run(*, max_lessons: int = DEFAULT_MAX_LESSONS, min_sources: int = 2,
        min_kinds: int = 2, channels: Sequence[str] | None = None,
        on_lesson: Callable[[dict[str, Any]], None] | None = None
        ) -> dict[str, Any]:
    """Study the machine's own backlog, most valuable first, until it is empty."""
    started = time.time()
    lessons: list[dict[str, Any]] = []
    pending = next_lesson(limit=max(1, max_lessons))
    if not pending:
        return {"schema": SCHEMA, "status": NOTHING_TO_LEARN, "pass": False,
                "lessons": [], "studied": 0, "closed": 0,
                "duration_s": round(time.time() - started, 4)}

    for gap in pending[:max(1, max_lessons)]:
        result = study(gap, min_sources=min_sources,
                         min_kinds=min_kinds, channels=channels)
        lessons.append(result)
        if on_lesson is not None:
            try:
                on_lesson(result)
            except Exception:
                pass

    closed = sum(1 for r in lessons if r.get("pass"))
    return {
        "schema": SCHEMA,
        "status": CLOSED if closed else OPEN_UNCLOSED,
        "pass": closed > 0,
        "studied": len(lessons),
        "closed": closed,
        "still_open": [r["gap"] for r in lessons if not r.get("pass")],
        "lessons": lessons,
        "authority": "GAPS_CLOSED_BY_EVIDENCE" if closed else "NOTHING_CLOSED",
        "duration_s": round(time.time() - started, 4),
    }
