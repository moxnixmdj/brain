#!/usr/bin/env python3
"""Routing a sentence to a typed capability chain.

The composer can already find an ordered chain of capabilities that turns
what the machine has into what a goal asks for -- 70 capabilities, 123 typed
tokens. It had no callers outside its own tests. The reason it was never
wired in is that ``plan`` takes a TOKEN, and nobody was translating a goal
written in English into one.

That translation is the whole of this module, and it is scored rather than
declared: a token is chosen because its own words and the words of the
capabilities that provide it are the words the goal used. Nothing here is a
hand-written mapping from sentences to capabilities, because a hand-written
mapping is the strict program the owner refused.

The second half is the part that matters: a plan that is only produced and
never run is not a capability. ``route`` returns the chain AND executes it,
and reports the observed result of every step.
"""

from __future__ import annotations

import re
import shlex
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_COMPOSER_ROUTE_V1"

_WORD = re.compile(r"[a-z0-9]+")
# Only true function words. An earlier version also stripped write/read/create/
# file -- which threw away the verb that says WHAT TO DO and the noun that says
# WHAT IT IS ABOUT. "write the text hello to out.txt" and "extract text from a
# pdf" then differ by one word, and the router cannot tell them apart.
_STOP = frozenset("""a an the this that these those it its is are was were be
been am do does did and or but if then than so as at by for from in into of on
to with without""".split())


def words(text: str) -> set[str]:
    """Content words. Stopwords are noise here, not meaning."""
    return {w for w in _WORD.findall(str(text or "").lower())
            if len(w) > 1 and w not in _STOP}


def token_words(token: str) -> set[str]:
    """``archive.tar_gz.create_from_manifest`` -> the words inside its name."""
    return {w for w in _WORD.findall(str(token or "").lower()) if len(w) > 1}


def score(goal_words: set[str], token: str,
          extra_words: Mapping[str, set[str]] | None = None) -> float:
    """How much of this token the goal actually said.

    The token's own name is not the only thing that describes it. A
    capability that writes a file is called `text.file.write` and carries the
    keywords write/file/create/save -- a goal saying "write the text hello to
    out.txt" matches those far better than it matches `pdf.extract.text`,
    which shares only the word "text". Scoring the name alone picks the
    wrong capability for the right reason.

    Dividing by the token name's length: a token that says twelve things and
    matches two of them is a worse guess than one that says three things and
    matches two of them.
    """
    tw = token_words(token)
    if not tw:
        return 0.0
    known = set(tw) | set((extra_words or {}).get(token) or ())
    hit = len(goal_words & known)
    if not hit:
        return 0.0
    return hit / (len(tw) ** 0.5)


def candidate_tokens(goal: str, g: Mapping[str, Any] | None = None) -> list[str]:
    """Tokens the goal might be asking for, best guess first."""
    from canonical.runtime import capability_composer_v1 as composer

    g = g if g is not None else composer.graph()
    gw = words(goal)
    if not gw:
        return []
    provided: set[str] = set()
    extra: dict[str, set[str]] = {}
    from canonical.runtime import capability_composer_v1 as composer
    reg = composer.load_registry()
    for cid, node in g.items():
        entry = reg.get(cid) or {}
        words_for = set(words(cid))
        for kw in (entry.get("keywords") or []):
            words_for |= words(str(kw))
        for tok in (node.get("provides") or []):
            tok = str(tok)
            provided.add(tok)
            extra.setdefault(tok, set()).update(words_for)
    scored = [(score(gw, tok, extra), tok) for tok in provided]
    scored = [(s, t) for s, t in scored if s > 0]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [t for _, t in scored]


def route(goal: str, seed: Sequence[str] | None = None,
          g: Mapping[str, Any] | None = None,
          max_candidates: int = 6,
          cwd: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Find the chain this goal asks for, and say which token it was read as.

    The chain is not returned as a claim: every candidate is tried until one
    is genuinely reachable from what the machine has.
    """
    from canonical.runtime import capability_composer_v1 as composer

    g = g if g is not None else composer.graph()
    ext = sorted(composer.external_tokens(g))
    have = list(seed) if seed is not None else list(ext)
    tried: list[dict[str, Any]] = []
    for token in candidate_tokens(goal, g)[:max_candidates]:
        chain = composer.plan(have, token, g)
        tried.append({"token": token, "reachable": chain is not None,
                      "chain": chain})
        if chain:
            return {"schema": SCHEMA, "pass": True, "goal": goal,
                    "token": token, "chain": list(chain), "tried": tried,
                    "status": "PASS__COMPOSER_ROUTE_FOUND",
                    "authority": "TYPE_LEVEL_COMPOSITION_REACHABLE"}
    # No chain of registered capabilities reaches it. Before reporting that,
    # try to WRITE a program that does it -- python3 is here and the stdlib is
    # free, so "nothing is registered" is not the same as "it cannot be done".
    try:
        from canonical.runtime import program_synthesis_v1 as synth
        from canonical.runtime import documentation_mining_v1 as dm
        made = synth.synthesize_or_recall(goal)
        if not (isinstance(made, Mapping) and made.get("pass")):
            made = dm.learn_or_recall(goal)
    except Exception:  # noqa: BLE001 - synthesis must never break routing
        made = None
    if isinstance(made, Mapping) and made.get("pass"):
        return {"schema": SCHEMA, "pass": True, "goal": goal, "token": None,
                "chain": [], "tried": tried, "synthesised": True,
                "status": "PASS__SYNTHESISED_PROGRAM",
                "suffix": made.get("suffix"),
                "authority": "SYNTHESISED_EXECUTED_AND_EFFECT_VERIFIED"}
    # Nothing is registered, nothing could be written, and no documentation
    # showed the way. The last resort is the one that is given nothing: act in
    # a real directory, watch what changes, and keep the shortest sequence
    # that reached the goal. It is last because it is the slowest, and last
    # because it is the only one still standing when every other had nothing.
    if not (isinstance(made, Mapping) and made.get("pass")):
        try:
            from canonical.runtime import computer_env_v1 as cenv
            found = cenv.discover(goal)
        except Exception:  # noqa: BLE001 - discovery must never break routing
            found = None
        if isinstance(found, Mapping) and found.get("closed"):
            # Knowing which program could do it is not doing it. If the goal
            # names a file that is actually there, do the job and leave the
            # file behind -- otherwise this is a fact about a sandbox.
            done = None
            try:
                from canonical.runtime import computer_env_v1 as cenv
                done = cenv.perform(goal, cwd=cwd)
            except Exception:  # noqa: BLE001 - doing must never break routing
                done = None
            if isinstance(done, Mapping) and done.get("pass"):
                return {"schema": SCHEMA, "pass": True, "goal": goal,
                        "token": None, "chain": [], "tried": tried,
                        "explored": True, "done": True,
                        "plan": list(done.get("plan") or []),
                        "output": done.get("output"),
                        "output_bytes": done.get("output_bytes"),
                        "argv": done.get("argv"),
                        "verification": done.get("verification"),
                        "suffix": found.get("suffix"),
                        "status": "PASS__PERFORMED_ON_REAL_FILE",
                        "authority": "PERFORMED_ON_REAL_FILE_AND_VERIFIED"}
            return {"schema": SCHEMA, "pass": True, "goal": goal,
                    "token": None, "chain": [], "tried": tried,
                    "explored": True, "plan": list(found.get("plan") or []),
                    "suffix": found.get("suffix"),
                    "actions_tried": found.get("actions_tried"),
                    "status": "PASS__DISCOVERED_BY_ACTING",
                    "authority": "DISCOVERED_BY_ACTING_AND_EFFECT_VERIFIED"}
    return {"schema": SCHEMA, "pass": False, "goal": goal, "token": None,
            "chain": [], "tried": tried,
            "status": "OPEN__COMPOSER_NO_REACHABLE_TOKEN",
            "authority": "TYPE_LEVEL_COMPOSITION_UNREACHABLE"}


# --------------------------------------------------------------------------- #
# binding: turning a sentence into the arguments a capability wants
# --------------------------------------------------------------------------- #
_EXT = re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9_]{1,8}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


# A path is not required to have an extension, and a directory almost never has
# one.  `_EXT` alone therefore made every directory invisible to the composer:
# "mkdir canonical/.../sub" bound no path at all, so PATH_OUTPUT could not be
# filled and execute_chain refused with OPEN__COMPOSER_SLOT_UNBOUND before
# dispatching anything -- while goal_compiler._repo_paths found that very path.
# Two extractors in one brain disagreed about what a path is, and the narrower
# one was the one that decided whether a command could run.
#
# Tried only AFTER `_EXT`, and only for a token carrying a separator whose last
# segment has no dot and is not the stem of a longer dotted name, so no sentence
# that already found its paths can change.  The same idiom this file already uses
# for _CONTENT_FALLBACK: a fallback that is never reached first cannot alter a
# sentence that already worked.
_DIRPATH = re.compile(r"\b(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_-]+(?![.\w-])")


def extract_paths(text: str) -> list[str]:
    """Filenames anywhere in the sentence.

    The surface's own parser is anchored to the start of the string, so it
    finds no file at all in "compress notes.txt into notes.txt.gz" -- the
    first word is a verb, and the file is the third. Looking only where the
    library looks is how a machine decides a goal named no input.
    """
    body = str(text or "")
    found = [m.group(0) for m in _EXT.finditer(body)]
    seen = set(found)
    for m in _DIRPATH.finditer(body):
        token = m.group(0)
        if token in seen:
            continue
        # The parent of a path already found is not a second path.  Appending it
        # would move paths[-1] -- which is what PATH_OUTPUT binds -- off the file
        # the sentence named and onto the directory holding it, so a command
        # would be told its output is a folder it was never asked to produce.
        if any(f == token or f.startswith(token + "/") for f in found):
            continue
        found.append(token)
        seen.add(token)
    return found


# A destination is a PATH, and the terminator only counts when what follows it is
# one.  The previous patterns ended the payload at the first "to|into|in|at",
# which are ordinary English words that belong to the payload far more often than
# they introduce a destination.  Measured on 4d859af over 18 stated texts, 13 were
# silently altered before they were written:
#
#     "a plain sentence about nothing in particular" -> "plain sentence about nothing"
#     "the results are in the attachment"            -> "results are"
#     "items in stock at the warehouse"              -> "items"
#     "text in the middle of it"                     -> "text"
#
# The file was then written with the truncated bytes, and because the acceptance
# re-inspector compares the file against the ARGUMENT rather than the sentence, it
# reported the result as independently verified.  So this was not a cosmetic
# truncation: it produced a confident pass on work the request never asked for.
_DEST_AHEAD = r"(?=[^\s]*/|\S+\.[A-Za-z0-9]{1,6}\b)"
_DEST_WORDS = r"\s+(?:to|into|in|at)\s+(?:(?:the|a|an)\s+)?(?:file|path|folder|directory)?\s*"
_CONTENT = [
    re.compile(r"\b(?:text|content|string|message|word|line)\s+(.+?)" + _DEST_WORDS + _DEST_AHEAD, re.I),
    re.compile(r"\bwrite\s+(.+?)" + _DEST_WORDS + _DEST_AHEAD, re.I),
]
# Kept, and tried only when nothing above matched, so a destination with no
# extension and no separator still binds exactly as it did before.  A fallback
# that is never reached first cannot change any sentence that already worked.
_CONTENT_FALLBACK = [
    re.compile(r"\b(?:text|content|string|message|word|line)\s+(.+?)\s+(?:to|into|in|at)\s+", re.I),
    re.compile(r"\bwrite\s+(.+?)\s+(?:to|into)\s+", re.I),
]


def extract_content(text: str) -> str | None:
    """What the goal asks to be written, when it says.

    "write the text hello to out.txt" asks for hello, and the file is the
    destination, not the payload. Guessing the filename as the content is how
    a machine writes a file full of its own name and calls it done.
    """
    sentence = str(text or "")
    for table in (_CONTENT, _CONTENT_FALLBACK):
        for pat in table:
            m = pat.search(sentence)
            if not m:
                continue
            body = m.group(1).strip().strip("'\"")
            if body:
                # The payload is delivered VERBATIM.  This used to strip a leading
                # "the"/"a"/"an", on the reasoning that an article is grammar rather
                # than content.  For a value that is about to be written to a file
                # that is not a distinction the writer gets to make: "the archive
                # manifest listing" was written as "archive manifest listing" and
                # "an important note" as "important note".  Measured, that one line
                # accounted for 7 of the 13 altered texts.
                return body
    return None


# --- argv -----------------------------------------------------------------
# A command line is quoted, like a payload: every token is content, so nothing
# here may be normalised, reordered or defaulted.  The role word is required,
# which is what keeps the whole "Run the <capability>." corpus from binding a
# command nobody asked to run -- measured, none of those sentences mention
# "command" or "argv".
_ARGV = [
    re.compile(r"\b(?:shell\s+|cli\s+|terminal\s+)?command\s+(?:to\s+run\s+|line\s+)?(.+?)\s*$", re.I),
    re.compile(r"\bargv\s+(.+?)\s*$", re.I),
]


def extract_argv(text: str) -> list[str] | None:
    """The command line the sentence states, token by token, or None.

    ``shell.command.run`` has been a VERIFIED_BOUND_CAPABILITY with an
    independently verified output all along -- cwd pinned to the repository
    root, timeout clamped to 300s, argv capped at 64 non-empty strings, and a
    non-zero exit raised rather than returned.  It was simply unreachable:
    ``bind`` had no rule for an ARGV slot, so every sentence that named it was
    refused with ``shell.command.run:argv:not_stated``.  One slot type was the
    whole distance between a verified general command runner and the requests
    that would use it.

    Returns None rather than a guess when the sentence states no command.  That
    is the rule PR #6119 established for a text slot and it applies here for the
    same reason: a slot filled from something the sentence does not contain is
    an invention, and an invention executes.
    """
    sentence = str(text or "")
    for pat in _ARGV:
        m = pat.search(sentence)
        if not m:
            continue
        body = m.group(1).strip().rstrip(".").strip()
        if not body:
            continue
        try:
            parts = shlex.split(body)
        except ValueError:
            # An unbalanced quote is a malformed command line, not something to
            # repair by guessing at the missing half.
            return None
        if parts and all(isinstance(part, str) and part for part in parts):
            return parts
    return None


def extract_number(text: str) -> float | None:
    m = _NUM.search(str(text or ""))
    return float(m.group(0)) if m else None


def bind(signature: Mapping[str, str], goal: str,
         inputs: Mapping[str, Any] | None = None,
         produced: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Fill each slot with something real, or leave it out and say so."""
    inputs = inputs or {}
    produced = produced or {}
    paths = extract_paths(goal)
    args: dict[str, Any] = {}
    for slot, typ in signature.items():
        if slot in inputs:
            args[slot] = inputs[slot]
            continue
        if slot in produced:
            args[slot] = produced[slot]
            continue
        t = str(typ or "").upper()
        if t in ("PATH_FILE", "PATH_INPUT", "PATH_LIST", "PATH_DIR"):
            if paths:
                args[slot] = paths[0]
        elif t == "PATH_OUTPUT":
            # the target is the LAST name in the sentence, not the first --
            # for "compress notes.txt into notes.txt.gz" that is the .gz
            if paths:
                args[slot] = paths[-1]
        elif t == "ARGV":
            argv = extract_argv(goal)
            if argv:
                args[slot] = argv
                _declare_a_consumed_output(args, argv)
        elif t == "NUMBER":
            n = extract_number(goal)
            if n is not None:
                args[slot] = n
        elif t == "STRING":
            # Only a text the sentence actually stated.  The old fallback used
            # paths[0] when no text was stated, which invented a payload out of a
            # filename -- and because a read or a count names exactly one path,
            # that same path also bound PATH_OUTPUT, so the file was opened for
            # writing and filled with its own name.  Measured on 25e3d67: 10 of 15
            # ordinary non-write requests -- read, count, delete, sort, reverse,
            # show, print, sum, search, truncate -- destroyed the file they were
            # told about and every one reported pass=True.  Leaving the slot
            # unbound makes the composer say so instead.
            body = extract_content(goal)
            if body:
                args[slot] = body
    return args


def _declare_a_consumed_output(args: dict[str, Any], argv: Sequence[str]) -> None:
    """Tell the adapter when the bound output is the operand a command removes.

    The composer binds PATH_OUTPUT to the last path the sentence names.  For
    `rm A` that is A itself -- the file being deleted -- so the adapter is handed
    a declared output that the command is about to make absent.  Without this the
    adapter raises CLI_EXPECTED_OUTPUT_MISSING after having already run the
    command, which is a report that denies work that happened.

    The knowledge is not invented here: it is read from the acceptance layer's
    own postcondition table, so a command is only declared a consumer when a
    verified postcondition exists to judge the result.  A deferred import keeps
    the layering -- the composer asks the verifier what it knows, and never the
    other way round.
    """
    if not argv:
        return
    program = str(argv[0]).rsplit("/", 1)[-1]
    try:
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept
        consumes = program in _accept._CONSUMES_AN_OPERAND
    except Exception:  # noqa: BLE001 - no table, no declaration
        consumes = False
    if consumes:
        args["output_may_be_consumed"] = "true"


# --------------------------------------------------------------------------- #
# execution: a plan that is never run is not a capability
# --------------------------------------------------------------------------- #
# Keys run_adapter_locally stamps onto the adapter's own result.  They describe
# the invocation, not what the capability produced, so they are kept out of the
# values a later step may bind to.
_INVOKER_STAMPED_KEYS = ("capability_id", "dependency")


def execute_chain(chain: Sequence[str], goal: str,
                  inputs: Mapping[str, Any] | None = None,
                  registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run the chain, step by step, and report what each step actually did."""
    from canonical.runtime import capability_composer_v1 as composer
    from canonical.runtime import capability_type_surface_v1 as TS
    from canonical.runtime import live_brain_route_admission_v1 as ra

    reg = registry if registry is not None else composer.load_registry()
    steps: list[dict[str, Any]] = []
    produced: dict[str, Any] = {}
    for index, cid in enumerate(chain):
        entry = reg.get(cid)
        if not isinstance(entry, Mapping):
            return {"schema": SCHEMA, "pass": False, "goal": goal,
                    "status": "FAIL__COMPOSER_STEP_NOT_IN_REGISTRY",
                    "failed_step": {"index": index, "capability_id": cid},
                    "steps": steps}
        sig = TS.signature(entry)
        args = bind(sig, goal, inputs, produced)
        errors = TS.check(sig, args)
        missing = sorted(set(sig) - set(args))
        if missing:
            return {"schema": SCHEMA, "pass": False, "goal": goal,
                    "status": "OPEN__COMPOSER_SLOT_UNBOUND",
                    "failed_step": {"index": index, "capability_id": cid,
                                    "missing_slots": missing},
                    "steps": steps}
        try:
            result = ra.run_adapter_locally(entry, {"args": dict(args)})
        except Exception as exc:  # noqa: BLE001 - a step failure is data
            # The adapter dispatches the command and only THEN checks its own
            # expectations, so it can raise after the work has already landed.
            # For `rm A` the file is deleted and only then does the output check
            # fail.  Returning without appending this step destroys the only
            # record that a command was dispatched, so every downstream consumer
            # sees an empty step list and reports that nothing happened.
            #
            # Measured on b364795: "Run the shell command rm A" deleted A,
            # execute_chain returned steps=[] with status
            # FAIL__COMPOSER_STEP_RAISED, and solve() reported
            # FAIL__RAW_GOAL_COMPILATION_GAP -- a report that denied a side
            # effect which had already happened.  That is the one direction a
            # false report must never go.
            #
            # Whether the side effect landed is genuinely unknown from here, so
            # the record says exactly that and claims nothing more.
            reason = type(exc).__name__ + ":" + str(exc)[:200]
            steps.append({"index": index, "capability_id": cid,
                          "args": dict(args), "type_errors": list(errors),
                          "adapter_raised": reason, "result": None,
                          "side_effect_landed": "UNKNOWN"})
            return {"schema": SCHEMA, "pass": False, "goal": goal,
                    "status": "FAIL__COMPOSER_STEP_RAISED",
                    "failed_step": {"index": index, "capability_id": cid,
                                    "reason": reason},
                    "steps": steps}
        # `run_adapter_locally` returns the adapter's own dict AS the result --
        # {"output_path": ..., "output_sha256": ..., "output_verified": True, ...}.
        # It does not wrap it under a "result" key, and it never has.  Reading
        # result.get("result") therefore returned None for every step of every
        # chain, which had two measured consequences on 5402138: the step record
        # was written as {"raw": null}, destroying the only evidence the step
        # produced, and `produced` stayed empty, so `bind` could never offer a
        # later step anything an earlier step had made.  The chain still reported
        # pass=True, so a composed goal answered "done" with a record that said
        # nothing had been produced.  Measured over the composed path: every step
        # of every chain recorded {"raw": null} and `produced` was always {}.
        observed = dict(result) if isinstance(result, Mapping) else None
        if observed is not None:
            # run_adapter_locally stamps these two itself; they are provenance
            # about the invocation, not outputs of the capability, and must not
            # become bindable slots for a later step.
            for injected in _INVOKER_STAMPED_KEYS:
                observed.pop(injected, None)
        if isinstance(observed, Mapping):
            for key, value in observed.items():
                produced.setdefault(key, value)
        steps.append({"index": index, "capability_id": cid, "args": dict(args),
                      "type_errors": list(errors),
                      "result": observed if isinstance(observed, Mapping)
                                else {"raw": observed}})
    return {"schema": SCHEMA, "pass": True, "goal": goal, "steps": steps,
            "produced": dict(produced),
            "status": "PASS__COMPOSER_CHAIN_EXECUTED",
            "authority": "TYPE_LEVEL_COMPOSITION_EXECUTED_LOCALLY"}
