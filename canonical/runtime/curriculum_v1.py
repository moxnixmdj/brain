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
    try:
        from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
            recall_and_execute_workflow,
        )
        recalled = recall_and_execute_workflow(gap)
        if recalled is not None and recalled.get("pass") is True:
            return {"closed": True, "status": "PASS__COMPILED_SKILL_RECALL",
                    "from_memory": True, "skill_id": recalled.get("skill_id"),
                    "detail": "executed qualified workflow skill from memory"}
    except Exception:
        pass
    return {"closed": False, "status": out.get("status"),
            "detail": "the goal still fails"}


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
    """Do the thing with this program. Reading is not doing."""
    from canonical.runtime import empirical_cli_probe_v1 as emp
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    suffix = acq._requested_suffix(gap)
    if not suffix:
        return {"closed": False, "status": "NO_OUTPUT_FORMAT_IN_GAP",
                "executable": exe, "detail": "nothing to verify an effect against"}
    observed = emp.probe(exe, gap, suffix=suffix)
    ok = str(observed.get("status") or "").startswith("PASS")
    return {"closed": ok, "status": observed.get("status"), "executable": exe,
            "detail": ("did it with %s" % exe) if ok
                      else ("%s is here but did not do it" % exe)}


def _try_synthesize(gap: str) -> dict[str, Any]:
    """Write a program that does it, and prove it by running it.

    Composing reaches what is registered; this reaches what is merely
    possible. The candidate is executed and its output checked, so a program
    is only accepted once the artifact is really there.
    """
    try:
        from canonical.runtime import program_synthesis_v1 as synth
        out = synth.synthesize_or_recall(gap)
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a lesson
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}
    ok = out.get("pass") is True
    return {"closed": ok, "status": out.get("status"),
            "suffix": out.get("suffix"),
            "from_memory": bool(out.get("from_memory")),
            "detail": ("wrote and verified a program producing %s" % out.get("suffix"))
                      if ok else (out.get("status") or "no candidate worked")}


def _try_explore(gap: str) -> dict[str, Any]:
    """Find out by acting, when nothing else knew the shape of the answer.

    Every other channel needs something given: a registered capability, a
    format in a table, a module the goal named, a source that answered, a
    program that exists. This one needs only a directory it may act in. It
    tries things, watches the directory change, and keeps the shortest
    sequence that reaches the goal -- and the model it built is remembered,
    so the same shape of problem is instant next time.
    """
    from canonical.runtime import computer_env_v1 as cenv
    try:
        return cenv.discover(gap)
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a lesson
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}

def _try_documentation(gap: str) -> dict[str, Any]:
    """Read the manual for it, then really do it.

    The hand-written table only reaches what someone remembered to write
    down. Documentation reaches the whole standard library, which is already
    installed and already paid for, plus semantic HTML form specs when a
    web endpoint URL is named.
    """
    try:
        from canonical.runtime import documentation_mining_v1 as dm
        out = dm.learn_or_recall(gap)
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a lesson
        out = {"pass": False, "status": type(exc).__name__ + ":" + str(exc)[:200]}
    if out.get("pass") is True:
        return {"closed": True, "status": out.get("status"),
                "module": out.get("module"), "suffix": out.get("suffix"),
                "from_memory": bool(out.get("from_memory")),
                "detail": "read %s's documentation and did it" % out.get("module")}
    url_m = re.search(r"https?://[^\s'\"<>]+", str(gap or ""))
    if url_m is not None:
        try:
            from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
            learned = solve_or_learn(gap, allow_tier1_composition=False, record_open_gap=False)
            if learned.get("pass") is True:
                return {"closed": True, "status": learned.get("status"),
                        "from_memory": bool(learned.get("from_memory")),
                        "detail": "inspected semantic web form and compiled HTTP skill"}
        except Exception:
            pass
    return {"closed": False, "status": out.get("status"),
            "module": out.get("module"), "suffix": out.get("suffix"),
            "from_memory": bool(out.get("from_memory")),
            "detail": out.get("status") or "the manual did not say"}


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
    """Learn a program the gap names, verified by running it."""
    from canonical.runtime import live_brain_route_admission_v1 as ra
    exe = ra._named_executable(gap)
    if not exe:
        return {"closed": False, "status": "NO_PROGRAM_NAMED",
                "detail": "the gap names no program that exists here"}
    from canonical.runtime import empirical_cli_probe_v1 as emp
    from canonical.runtime import cli_capability_acquisition_v1 as acq

    suffix = acq._requested_suffix(gap)
    if not suffix:
        return {"closed": False, "status": "NO_OUTPUT_FORMAT_IN_GAP",
                "detail": "nothing to verify an effect against"}
    observed = emp.probe(exe, gap, suffix=suffix)
    ok = str(observed.get("status") or "").startswith("PASS")
    return {"closed": ok, "status": observed.get("status"), "executable": exe,
            "detail": ("learned and verified by running it" if ok
                       else "no observed effect")}


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
        credit_channel(name, bool(outcome.get("closed")))
        if outcome.get("closed"):
            closed_by = name
            break          # cheap before expensive, and stop when it worked

    closed = closed_by is not None
    if gap_id and closed:
        try:
            from canonical.runtime import ignorance_ledger_v1 as led
            led.resolve(gap_id, helped=True, close=True)
        except Exception:
            pass
    elif gap_id:
        try:
            from canonical.runtime import ignorance_ledger_v1 as led
            led.resolve(gap_id, helped=False, close=False)
        except Exception:
            pass

    return {
        "schema": SCHEMA,
        "status": CLOSED if closed else OPEN_UNCLOSED,
        "pass": closed,
        "gap_id": gap_id,
        "gap": what,
        "closed_by": closed_by,
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
