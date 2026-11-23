"""Learn an undocumented program's interface by asking it, one refusal at a time.

THE PROBLEM, AND WHY IT IS THE RIGHT ONE TO SOLVE NEXT. Everything in §A90-A97 assumes the program
documents itself. Agent-Diff (arXiv 2602.11224, Feb 2026) benchmarks the other case -- "no-docs", where the
agent gets only a service name and must discover the interface by exploration -- and reports the frontier's
failure there is not silence but **hallucinated task completion**: given null responses, models "attempt
Collections API, receives null responses, and hallucinate task completion." The same paper finds a novel
interface (introduced after training cutoffs) scores 54.1 against 73.1 for familiar ones, which says the
with-docs score is partly memory.

This repository has never had that failure mode, because it refuses instead of guessing. It also has never
been able to act without documents at all. Both statements are true and the second is the problem.

THE IDEA, IN ONE SENTENCE. **A program is its own documentation if you can ask it questions** -- every
undocumented interface still answers, and its answers distinguish "that is not a thing I do" from "that is
a thing I do, and you left something out".

That distinction is the whole mechanism, and it needs no model and no vocabulary:

    probe 'add'        -> NAME_REQUIRED            the VERB IS RIGHT, an argument is missing
    probe 'add x'      -> exit 0, state changed    the ARITY IS TWO, and it worked
    probe 'bogus'      -> UNKNOWN_VERB:bogus       the verb is NOT in the program's closed set

`NAME_REQUIRED` is a membership test that came back POSITIVE. `UNKNOWN_VERB` is one that came back
NEGATIVE. Nothing here interprets English; it reads whether the program accepted the shape it was offered.
Where a program says nothing at all -- exit 0 with no output on every input -- this reports
`NO_DISCRIMINATION` rather than inventing a model of it.

WHAT IT LEARNS, AND WHAT IT DELIBERATELY DOES NOT. It learns VERBS (which first words the program accepts),
ARITY (how many positional arguments a verb wants before it stops refusing), and EFFECT (whether a verb
changes the world). It does not learn semantics -- it cannot know that `add` means "insert a record" rather
than "count something". That is a real limit and this module states it instead of hiding it: the learned
interface is enough to ACT, not enough to CHOOSE. Choosing is what the goal supplies.

THE SAFETY RULE THAT MAKES PROBING POSSIBLE. Probing a mutating program is dangerous, so the probe runs in
a COPY of the world and only the interface it learned is carried back. `probe_world` takes a source
directory and copies it; nothing here ever touches the caller's tree. This is the same discipline
`knowledge_repair_v1` already uses for its repair loop.

Authority NONE. Zero model calls. Every learned fact is an observation of an exit code or an output string
that the program itself printed.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_UNDOCUMENTED_V1"

#: A refusal that says a REQUIRED ARGUMENT is missing. The verb it was asked about is therefore one the
#: program HAS -- this is a positive membership result, which is why it is worth reading carefully.
_WANTS_MORE = re.compile(
    r"\b(?:[A-Z][A-Z0-9_]{2,}_(?:REQUIRED|MISSING|EXPECTED)"
    r"|(?:MISSING|REQUIRED|EXPECTED)_[A-Z][A-Z0-9_]{2,})\b"
    r"|\b(?:usage|usage:)\b.*\b(?:requires?|needs?|missing)\b"
    r"|\b(?:requires?|missing)\b.*\b(?:argument|parameter|option|operand)\b", re.I)

#: A refusal that says the VERB is not one the program has. A negative membership result.
_NO_SUCH_VERB = re.compile(
    r"\b(?:UNKNOWN|INVALID|UNRECOGNISED|UNRECOGNIZED|BAD|NO_SUCH)_?(?:VERB|COMMAND|SUBCOMMAND|ROUTE|ACTION)"
    r"\b\s*:?\s*([\w./-]*)", re.I)

#: Words that are structure rather than verbs. Used only to avoid probing them for ever, never to decide
#: what a verb means.
_FLAGLIKE = re.compile(r"^-")


def _run(program: str, argv: Sequence[str], cwd: pathlib.Path, env: Mapping[str, str],
         timeout: int) -> dict[str, Any]:
    try:
        done = subprocess.run([program] + [str(a) for a in argv], cwd=str(cwd),
                              capture_output=True, text=True, timeout=timeout, env=dict(env))
    except subprocess.TimeoutExpired:
        return {"exit": None, "out": "", "err": "", "timed_out": True}
    except OSError as exc:
        return {"exit": None, "out": "", "err": "%s: %s" % (type(exc).__name__, exc), "timed_out": False}
    return {"exit": done.returncode, "out": (done.stdout or "")[-4000:],
            "err": (done.stderr or "")[-4000:], "timed_out": False}


def _says_wants_more(answer: Mapping[str, Any]) -> str | None:
    """The missing-argument code, if the program said it wants more. A POSITIVE verb result."""
    text = "%s %s" % (answer.get("err") or "", answer.get("out") or "")
    match = _WANTS_MORE.search(text)
    if not match:
        return None
    return match.group(0)[:60]


def _says_no_such_verb(answer: Mapping[str, Any]) -> str | None:
    text = "%s %s" % (answer.get("err") or "", answer.get("out") or "")
    match = _NO_SUCH_VERB.search(text)
    return (match.group(0) or "")[:80] if match else None


def unknown_verb_signature(program: str, *, world: pathlib.Path, env: Mapping[str, str],
                           timeout: int = 20) -> dict[str, Any]:
    """Learn what THIS program says when a verb cannot possibly exist.

    THE DENOMINATOR, AND WHY IT IS THE WHOLE TRICK. Reading refusal vocabulary is fragile -- measured
    2026-11-23, a second program refused with `MISSING_ARGUMENT` where the first said `NAME_REQUIRED`, and
    a pattern matching one missed the other, so a real verb was reported unreadable. Any pattern list is a
    list of the programs I happened to see.

    A program, though, is consistent about its own rejection. `ticketer` answers `INVALID_COMMAND`;
    `mystery` answers `UNKNOWN_VERB:<name>`. So the program's own answer to a nonsense verb is a
    calibrating measurement rather than a guess: whatever it says to `qzx_probe_nonsense` is what "this
    verb does not exist" SOUNDS LIKE HERE. A verb whose refusal differs from that signature is a verb the
    program HAS, and the search for its arity can continue.

    The nonsense name is chosen to be one no program would define, and it is probed rather than assumed.
    """
    name = "qzxvbnmprobe"
    answer = _run(program, [name], world, env, timeout)
    return {"probe": name, "exit": answer.get("exit"), "out": answer.get("out") or "",
            "err": answer.get("err") or ""}


def _resembles(answer: Mapping[str, Any], signature: Mapping[str, Any]) -> bool:
    """Does this refusal look like the program's own no-such-verb answer?

    Compared on the part that identifies the objection: the stderr text with any echoed verb name removed,
    and the exit code. `UNKNOWN_VERB:add` and `UNKNOWN_VERB:qzxvbnmprobe` are the SAME objection with a
    different subject, so the subject is stripped before comparing -- otherwise every unknown verb would
    look novel.
    """
    if answer.get("exit") != signature.get("exit"):
        return False

    def shape(resp: Mapping[str, Any]) -> str:
        text = "%s %s" % (resp.get("err") or "", resp.get("out") or "")
        text = text.replace(str(signature.get("probe") or ""), "<verb>")
        return re.sub(r"[\w./-]{6,}", "<w>", text.strip())[:200]

    return bool(shape(answer)) and shape(answer) == shape(signature)


def probe_verb(program: str, verb: str, *, world: pathlib.Path, env: Mapping[str, str],
               signature: Mapping[str, Any] | None = None,
               timeout: int = 20) -> dict[str, Any]:
    """Ask the program whether `verb` is one of its verbs, and how many arguments it wants.

    The arity search is bounded and stops at the first acceptance. Each argument is a placeholder the
    program has never seen -- the point is not to produce a valid command but to find the SHAPE at which
    the program stops refusing.
    """
    said_more: list[str] = []
    last: dict[str, Any] = {}
    for count in range(0, 4):
        argv = [verb] + ["probe%d" % index for index in range(count)]
        last = _run(program, argv, world, env, timeout)
        if last.get("timed_out"):
            return {"verb": verb, "known": False, "why": "TIMED_OUT", "arity": None}
        if last.get("exit") == 0:
            return {"verb": verb, "known": True, "arity": count,
                    "evidence": "ACCEPTED_AT_ARITY_%d" % count,
                    "out": (last.get("out") or "")[:160],
                    "missing_codes": said_more}
        missing = _says_wants_more(last)
        no_such = _says_no_such_verb(last)
        if no_such:
            # the program has told us the verb is not its own -- a negative result, and the search stops
            return {"verb": verb, "known": False, "why": "THE_PROGRAM_REPORTED_THIS_VERB_AS_UNKNOWN",
                    "evidence": no_such, "arity": None, "missing_codes": said_more}
        if missing:
            said_more.append(missing)
            continue
        # THE DIFFERENTIAL READING: the program refused, and said something that is NOT its own
        # no-such-verb answer. That is a refusal of the SHAPE, which means the VERB exists.
        if signature is not None and not _resembles(last, signature):
            said_more.append("REFUSED_THE_SHAPE_NOT_THE_VERB")
            continue
        # a refusal that names neither: the verb may be right, but the shape is wrong in a way this
        # module cannot read. Record what was said and stop guessing.
        return {"verb": verb, "known": None, "why": "REFUSAL_DID_NOT_LOCATE_ITS_SUBJECT",
                "evidence": ("%s %s" % (last.get("err") or "", last.get("out") or ""))[:160],
                "arity": None, "missing_codes": said_more}
    return {"verb": verb, "known": None, "why": "ARITY_NOT_FOUND_WITHIN_BOUND",
            "missing_codes": said_more, "arity": None}


def probe_world(program: str, source: str | pathlib.Path, *,
                candidates: Sequence[str] = (), env_key: str | None = None,
                timeout: int = 20) -> dict[str, Any]:
    """Probe a program in a COPY of a world, and report the interface it states.

    Nothing here touches `source`. A probe of a mutating program WILL mutate whatever it runs against,
    which is why the copy is not optional and why it is made before the first probe rather than after the
    first surprise.
    """
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain_probe_"))
    world = work / "world"
    source_path = pathlib.Path(source).resolve()
    shutil.copytree(source, world, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))

    # THE COPY MUST CONTAIN THE PROGRAM, AND THE PROBE MUST RUN THAT ONE.
    # Measured 2026-11-23: the program was resolved from the ORIGINAL tree, so probing executed the real
    # binary and every write landed in the world I had promised not to touch -- `.tix.json` appeared in
    # the caller's directory while the copy stayed clean. A copy that is never executed is not a sandbox;
    # it is a decoration that makes the code READ safe while it is not.
    #: the program as the CALLER named it -- the copy exists only for the duration of the probe, so
    #: recording the copy's path would hand back an interface pointing at a deleted file. Measured
    #: 2026-11-23: act_hint was `/tmp/brain_probe_.../world/bin/ticketer`, which no longer existed by the
    #: time the interface was used.
    reported_program = str(pathlib.Path(program).resolve())
    program_path = pathlib.Path(program).resolve()
    try:
        inside = program_path.relative_to(source_path)
    except ValueError:
        inside = None
    if inside is not None:
        copied = world / inside
        program = str(copied)
        try:
            copied.chmod(copied.stat().st_mode | 0o111)
        except OSError:
            pass

    env: dict[str, str] = {}
    if env_key:
        # the state file lives INSIDE the copy, so nothing it writes can reach the caller
        env[env_key] = str(world / "state.json")

    def state() -> str:
        """THE WHOLE COPY, not one file I guessed the name of.

        Measured 2026-11-23: `ticketer` writes a dotfile beside itself and takes no environment variable,
        so watching a single expected path reported `mutating: []` for a program that had plainly mutated.
        A program's effect appears SOMEWHERE in the world it was given, so the fingerprint is every file's
        relative path, size, and mtime -- which is enough to see a change and cheap enough to take between
        probes.
        """
        parts: list[str] = []
        if env_key:
            try:
                parts.append("ENV:" + pathlib.Path(env[env_key]).read_text())
            except OSError:
                pass
        for found in sorted(world.rglob("*")):
            if found.is_file() and "__pycache__" not in str(found):
                try:
                    stat = found.stat()
                    parts.append("%s:%d:%d" % (found.relative_to(world), stat.st_size,
                                               int(stat.st_mtime_ns)))
                except OSError:
                    continue
        return "|".join(parts)

    signature = unknown_verb_signature(program, world=world, env=env, timeout=timeout)
    before = state()
    results: list[dict[str, Any]] = []
    for verb in candidates:
        if _FLAGLIKE.match(str(verb)):
            continue
        learned = probe_verb(program, str(verb), world=world, env=env, signature=signature,
                             timeout=timeout)
        learned["changed_the_world"] = state() != before
        before = state()
        results.append(learned)
    known = [r for r in results if r.get("known") is True]
    return {"schema": SCHEMA, "program": reported_program, "probed": results,
            "no_such_verb_signature": {"exit": signature.get("exit"),
                                       "said": ((signature.get("err") or signature.get("out")) or "")
                                               .strip()[:80]},
            "verbs_learned": [r["verb"] for r in known],
            "arity": {r["verb"]: r.get("arity") for r in known},
            "mutating": [r["verb"] for r in known if r.get("changed_the_world")],
            "unknown": [r["verb"] for r in results if r.get("known") is False],
            "unreadable": [r["verb"] for r in results if r.get("known") is None],
            "world_was_copied_to": str(world)}


def learn_interface(program: str, source: str | pathlib.Path, *,
                    candidates: Sequence[str] = (), env_key: str | None = None,
                    timeout: int = 20, read_source: bool = True) -> dict[str, Any]:
    """Probe, then say whether the result is enough to ACT with -- and if not, why not.

    `enough_to_act` is deliberately narrow: a learned mutating verb with a known arity is enough to build a
    command. It is NOT enough to know why anyone would want to run it, and this module says so rather than
    letting a caller read `verbs_learned` as understanding.
    """
    if not candidates and read_source:
        # the caller supplied nothing, so ask the program's own bytes for hypotheses instead of asking the
        # caller to guess. A rejected candidate costs one probe and is reported `unknown`.
        found = candidates_from_source(program)
        candidates = found.get("candidates") or []
        origin = found
    else:
        origin = {"schema": SCHEMA, "candidates": list(candidates),
                  "why": "THE_CALLER_STATED_THESE"}
    result = probe_world(program, source, candidates=candidates, env_key=env_key, timeout=timeout)
    result["candidates_from"] = origin.get("why")
    mutating = [v for v in result["mutating"] if result["arity"].get(v) is not None]
    if mutating:
        result["enough_to_act"] = True
        result["act_hint"] = "%s %s<arg>" % (result["program"], mutating[0])
        result["not_learnt"] = "what the verb MEANS, or whether it is the verb the goal wants"
    elif result["verbs_learned"]:
        result["enough_to_act"] = False
        result["why"] = "VERBS_LEARNED_NONE_CHANGED_THE_WORLD"
    else:
        result["enough_to_act"] = False
        result["why"] = "NO_DISCRIMINATION" if result["unreadable"] else "NO_VERB_ACCEPTED"
    return result


def candidates_from_source(program: str) -> dict[str, Any]:
    """Read a program's own bytes for the words it compares against -- hypotheses, never truth.

    THE PROBLEM THIS SOLVES: probing needs a list of verbs to try, and a caller should not have to supply
    one. `ticketer` refuses `help`, `--help` and `commands`, so it will never enumerate itself; a program
    that does not document itself will not volunteer its vocabulary either.

    But the program is not silent -- it is RIGHT THERE. A dispatch compares the first argument against the
    words it accepts, and those comparisons are in its source. Measured 2026-11-23 on `ticketer`: the string
    literals it compares against are exactly `open`, `show`, `shutdown` -- its three verbs, no noise.

    THIS IS NOT "READ THE DOCUMENTATION". The documentation describes; the source DISPATCHES, and a
    comparison is a statement the program makes about itself. Still, a literal in a comparison is only a
    claim: `--fix` appears in a condition too. So everything here is a HYPOTHESIS and `probe_world` decides
    which are real. A candidate the program rejects costs one probe and is reported `unknown`.

    Refuses rather than guesses when the source is not parseable as Python -- in that case the caller must
    supply candidates, and a probe with no candidates learns nothing and says so.
    """
    try:
        source = pathlib.Path(program).read_text(errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError, ValueError) as exc:
        return {"schema": SCHEMA, "candidates": [], "why": "THE_SOURCE_IS_NOT_READABLE_PYTHON",
                "detail": "%s: %s" % (type(exc).__name__, exc)}

    compared: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for operand in [node.left] + list(node.comparators):
                if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                    compared.add(operand.value)
    #: a verb is a bare lowercase word; flags (`--fix`), paths and messages are not, and are cheap to skip
    candidates = sorted(v for v in compared if re.fullmatch(r"[a-z][a-z0-9_-]{1,20}", v))
    return {"schema": SCHEMA, "candidates": candidates,
            "why": "THE_PROGRAM_STATES_THESE_IN_ITS_OWN_DISPATCH",
            "note": "hypotheses; probe_world decides which are real",
            "all_compared_literals": sorted(compared)[:60]}


def act_for_goal(goal: str, learned: Mapping[str, Any], *,
                 root: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Build a command for a goal, using ONLY an interface that was measured from the program.

    THE JOIN, AND THE LINE IT DOES NOT CROSS. The learned interface says which verbs exist and how many
    arguments each wants. The goal says what it wants and supplies the values. A command follows when the
    goal NAMES a verb the program has: the values between quotes are the arguments, in the order stated.

    When the goal names no such verb, this refuses -- `THE_PROGRAM_STATES_NO_SUCH_VERB` -- and does not try
    to pick the "closest" one. Measured 2026-11-23: `open a ticket "T-1" describing "printer jammed"` names
    `open` and joins cleanly; `create a ticket titled "T-9" with body "wifi down"` names nothing the
    program has, and NO amount of syntax makes `create` mean `open`. Synonymy is knowledge about English,
    not about the program, and this module has none -- so it says so instead of guessing. That is the
    difference between a join and a lookup table of synonyms I would have to invent.

    Values are taken from the goal in quoted spans, in order, which is the request's own statement of what
    the arguments are. Nothing is invented; a goal that quotes fewer values than the arity is refused with
    the count, because a positional argument cannot be filled from nothing.
    """
    verbs = list(learned.get("verbs_learned") or [])
    arity = dict(learned.get("arity") or {})
    words = set(re.findall(r"[a-z]+", str(goal).lower()))
    named = [v for v in verbs if str(v).lower() in words]
    if not named:
        # a verb named by a longer form of the goal's word: `open` for `opened`. Bounded to a prefix of at
        # least four characters so `a` or `to` cannot match by accident.
        named = [v for v in verbs
                 if any(w.startswith(str(v).lower()) and len(w) >= 4 for w in words)]
    if len(named) != 1:
        return {"schema": SCHEMA, "act": None,
                "why": "THE_PROGRAM_STATES_NO_SUCH_VERB" if not named else "THE_GOAL_NAMES_SEVERAL_VERBS",
                "the_program_has": verbs, "goal": str(goal)[:200],
                "detail": "synonymy is knowledge about English, which this module does not have"
                if not named else "the goal names more than one of the program's verbs"}
    verb = named[0]
    want = arity.get(verb)
    values = [v for v in re.findall(r'"([^"]*)"|\u201c([^\u201d]*)\u201d', str(goal)) for v in v if v]
    if want is None:
        return {"schema": SCHEMA, "act": None, "why": "THE_LEARNED_ARITY_IS_UNKNOWN",
                "verb": verb, "the_program_has": verbs}
    if len(values) < want:
        return {"schema": SCHEMA, "act": None, "why": "THE_GOAL_STATES_TOO_FEW_VALUES",
                "verb": verb, "wanted": want, "stated": values}
    program = str(learned.get("program") or "")
    return {"schema": SCHEMA, "act": [program, verb] + list(values[:want]),
            "verb": verb, "arity": want, "values_from_the_goal": list(values[:want]),
            "why": "JOINED_FROM_THE_MEASURED_INTERFACE"}


def main(argv: Sequence[str] | None = None) -> int:
    import sys
    arguments = list(argv if argv is not None else sys.argv[1:])
    if len(arguments) < 2:
        print(json.dumps({"schema": SCHEMA,
                          "usage": "python -m canonical.runtime.undocumented_v1 "
                                   "<program> <world-dir> [verb ...]"}, indent=1))
        return 0
    program, source = arguments[0], arguments[1]
    verbs = arguments[2:]
    print(json.dumps(learn_interface(program, source, candidates=verbs), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
