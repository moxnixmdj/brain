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
    "knowledge": {"cost": 1.0, "note": "go and get the data"},
    "acquire":   {"cost": 1.8, "note": "learn to run a program"},
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
    ok = out.get("pass") is True
    return {"closed": ok, "status": out.get("status"),
            "detail": "the goal executed and passed" if ok else "the goal still fails"}


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


def _try_knowledge(gap: str, min_sources: int) -> dict[str, Any]:
    from canonical.runtime import jit_knowledge_v1 as jit
    # try the phrasing that searches well, not only the one that was written
    queries = [gap, query_for(gap)]
    seen: set[str] = set()
    best: dict[str, Any] = {}
    for query in queries:
        if not query or query in seen:
            continue
        seen.add(query)
        out = jit.resolve(query, min_sources=min_sources)
        if out.get("pass") is True:
            return {"closed": True, "status": out.get("status"), "query": query,
                    "documents": out.get("document_count", 0),
                    "sources": out.get("sources_answered") or [],
                    "detail": "independent sources answered"}
        if not best or out.get("document_count", 0) > best.get("documents", 0):
            best = {"closed": False, "status": out.get("status"), "query": query,
                    "documents": out.get("document_count", 0),
                    "sources": out.get("sources_answered") or [],
                    "detail": (out.get("gap") or "sources did not answer")}
    return best


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
            elif name == "knowledge":
                outcome = _try_knowledge(what, min_sources)
            elif name == "acquire":
                outcome = _try_acquire(what)
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
        channels: Sequence[str] | None = None,
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
        result = study(gap, min_sources=min_sources, channels=channels)
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
