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


# Keys the composer adds to a capability's arguments to tell the ADAPTER how to
# report a fact.  They are not declared inputs -- the capability never asks for
# them -- so they must not be counted when deciding whether a contract is full.
_ADAPTER_DIRECTIVES = frozenset({"output_may_be_consumed",
                                 "exit_status_is_the_answer"})


def _fully_bound_contract_tokens(goal: str, g: Mapping[str, Any],
                                 reg: Mapping[str, Any]) -> frozenset[str]:
    """Tokens provided by a capability every declared input of which the goal fills.

    Nothing is mapped by hand from sentence to capability.  The question asked is
    the one PR #6135 already asks: can this capability's own signature be filled
    from what the sentence states?  A capability that declares an ARGV slot is
    chosen for a sentence that states a command line because that sentence
    *fills the slot*, not because somebody wrote down which capability "copy"
    means.  A sentence that states no command binds nothing, and this returns an
    empty set, so the ranking falls back to the words alone.
    """
    try:
        from canonical.runtime import capability_type_surface_v1 as TS
    except Exception:  # noqa: BLE001 - no type surface, no contract to test
        return frozenset()
    if not extract_argv(goal):
        # The sentence states no command line, so there is no contract for this
        # rule to read.  Returning early is what keeps the rule from flooding:
        # measured without it, "audit the python unit tests and count passes"
        # promoted every capability whose STRING slot extract_content could
        # fill, the real auditor fell out of the top of the ranking, and the
        # unified model's own execution audit went 33/33 -> 32/33.
        return frozenset()
    filled: set[str] = set()
    for cid, node in g.items():
        entry = reg.get(cid)
        if not isinstance(entry, Mapping):
            continue
        try:
            sig = TS.signature(entry)
        except Exception:  # noqa: BLE001 - an unreadable entry declares nothing
            continue
        if not any(str(typ or "").upper() == "ARGV" for typ in sig.values()):
            # Only a capability that DECLARES a command-line slot can be the one
            # a stated command line fills.  That is the whole of the claim: the
            # sentence supplied a command, this capability is built to take one.
            continue
        try:
            args = bind(sig, goal)
        except Exception:  # noqa: BLE001 - binding is best effort here
            continue
        if not args or (set(args) - _ADAPTER_DIRECTIVES) != set(sig):
            # Every declared input, or none.  A half-filled contract is not
            # evidence that this is the capability the sentence meant.
            #
            # The adapter directives are excluded from the comparison because
            # they are not declared inputs at all: they are instructions the
            # composer gives the adapter about how to REPORT a fact, added after
            # the contract is filled.  Counting them as unbound inputs made every
            # consuming or answer-reporting command look half-filled -- measured,
            # "Diff the file a against b" lost the tie to json.file.available on
            # the word "file" and the request reached a JSON writer.
            continue
        for tok in (node.get("provides") or []):
            filled.add(str(tok))
    return frozenset(filled)


def candidate_tokens(goal: str, g: Mapping[str, Any] | None = None) -> list[str]:
    """Tokens the goal might be asking for, best guess first.

    Scored on the request's PROSE, never on the values it carries -- the same rule the
    front compiler already applies as F8/F25, and for the same measured reason.  A URL,
    a path and a quoted payload are values: the address it reads, the file it touches,
    the text it encodes.  None of them says what the task IS.

    Measured without this, on "Write the text 'hello patch' to the file <t>/out.txt and
    save the report to <t>/report.json": words() returns the path's own components as
    task words -- json, txt, out, canonical, astra, runtime, tmp -- and `json`, taken
    from the FILENAME report.json, ranked json.file.available above text.file.available.
    The request was then routed to a JSON writer, which correctly refused the plain text
    with CONTENT_NOT_VALID_JSON, and neither file was written.  A destination's suffix
    decided the task.  On prose the same sentence yields file, report, save, text,
    write -- the words the request is actually made of.
    """
    from canonical.runtime import capability_composer_v1 as composer
    from canonical.runtime import goal_front_compiler_v1 as front

    g = g if g is not None else composer.graph()
    # Scored on the request's PROSE, never on the values it carries -- the rule
    # the front compiler already applies as F8/F25.  An earlier revision also
    # subtracted the payload returned by ``extract_content``, on the theory that
    # an unquoted payload could still vote.  Measured, it changed nothing: for
    # "Write the text the archive manifest listing to out.txt" the writer is
    # chosen either way, because the archiver's own name matches no word of the
    # prose.  So the subtraction was removed rather than kept as a guess.
    gw = words(front.prose_only(goal))
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
    # RANK ON THE WORDS, THEN ON WHETHER THE SENTENCE FILLS THE CONTRACT.
    #
    # An earlier revision of this function demoted any capability whose matches
    # were all generic, on the theory that a shared word is not evidence.  That
    # is wrong on its own terms, and measurably so: for "Write the text 'hello
    # patch' to out.txt and save the report to r.json", text.file.available
    # matched four of the sentence's five words and scored 2.3094 -- the highest
    # in the registry -- while document.convert.markdown_pdf matched one word,
    # "report", and scored 0.5000.  The rule handed the request to the archiver.
    # A capability that matches almost the whole sentence is not a weak
    # candidate; it is the candidate.
    #
    # What actually separates "Copy the file a to b" from "Write the text ...",
    # where a JSON writer and a text writer tie on the word "file", is not which
    # words are distinctive.  It is that the first sentence fills an ARGV slot
    # and the second fills none.  That is the contract test below, and it is the
    # same test PR #6135 established as DECLARED_CONTRACT_FULLY_BOUND.
    scored = [(score(gw, tok, extra), tok) for tok in provided]
    scored = [(s0, t) for s0, t in scored if s0 > 0]
    bound = _fully_bound_contract_tokens(goal, g, reg)
    scored.sort(key=lambda pair: (pair[1] not in bound,
                                  -pair[0], pair[1]))
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


# The destination a stated payload runs to: the path the sentence puts immediately
# after the content.  Built from the same _DEST_WORDS and path lookahead the
# payload patterns already use, so a sentence is parsed by one grammar rather than
# two that can disagree.
_CONTENT_DEST = [
    re.compile(r"\b(?:text|content|string|message|word|line)\s+.+?" + _DEST_WORDS + r"(\S+)", re.I),
    re.compile(r"\bwrite\s+.+?" + _DEST_WORDS + r"(\S+)", re.I),
]


def extract_content_destination(text: str) -> str | None:
    """The path the sentence puts immediately after the text it states.

    Returns None when the sentence states no content, or states it with no
    destination following -- "create the file X containing the text Y" names its
    destination BEFORE the payload, and "compress notes.txt into notes.txt.gz"
    states no payload at all.  Both must keep binding the way they always did, so
    this answers only the one question it can answer precisely.
    """
    body = str(text or "")
    for pattern in _CONTENT_DEST:
        match = pattern.search(body)
        if match:
            token = str(match.group(1) or "").strip().strip(".,;:!?\"'")
            if token:
                return token
    return None


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
    # No command line was QUOTED.  The request may still state one in ordinary
    # English -- "Copy the file a to b" -- and that is the shape almost every
    # real request takes.  This is a fallthrough, not a replacement: a quoted
    # command line always wins, because it is the stronger statement.
    return _prose_argv(sentence)


# --------------------------------------------------------------------------- #
# a command the sentence asks for in words, rather than states as a line
# --------------------------------------------------------------------------- #
# ``_ARGV`` reads a command line the sentence QUOTES -- "Run the shell command
# cp a b".  Nobody writes it that way twice.  The ordinary request is "Copy the
# file a to b", and before this table it produced no argv at all, so
# shell.command.run -- a VERIFIED_BOUND_CAPABILITY with an independently
# verified output -- was unreachable for every sentence phrased as English.
#
# Nothing here is invented.  Each pattern names one program, and every program
# below is drawn from the acceptance layer's own tables
# (``_READ_ONLY_COMMANDS`` and ``_MUTATING_POSTCONDITIONS``), which is the set of
# commands the verifier already knows how to judge AFTER the fact.  A prose
# request is only ever routed to a command the verifier can check.  The import
# assertion at the bottom of this block makes that a fact rather than a comment.
#
# Each row is (pattern, program, flag-builder, operand-arity).  The arity is the
# half that keeps this from guessing: a pattern that wants two paths and finds
# one returns None, so an incomplete request is refused instead of being
# completed with an invented operand -- the same rule PR #6119 set for a text
# slot and PR #6120 set for a command line.

def _no_flags(_n: int) -> list[str]:
    return []


# Which column the sentence asked for.  An ordinal word is a number the sentence
# states just as much as a digit is, so it is read rather than defaulted; a
# sentence that states neither is refused by the arity rule below rather than
# given column 1, because an invented column is an invented answer.
_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
             "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}


def _cut_flags(n: int) -> list[str]:
    return ["-f", str(n)]


def _head_flags(n: int) -> list[str]:
    return ["-n", str(n)]


def _tail_flags(n: int) -> list[str]:
    return ["-n", str(n)]


_PROSE_COMMAND: tuple[tuple[str, str, Any, int], ...] = (
    (r"\bcopy\b", "cp", _no_flags, 2),
    (r"\b(?:move|rename)\b", "mv", _no_flags, 2),
    (r"\b(?:remove|delete)\b", "rm", _no_flags, 1),
    (r"\b(?:create|make)\b[^.\n]{0,40}?\bdirectory\b", "mkdir", _no_flags, 1),
    (r"\b(?:create|make|touch)\b[^.\n]{0,40}?\bempty file\b", "touch", _no_flags, 1),
    # The three things `wc` counts, each stated by its own noun.  Order matters
    # only in that all three are narrower than the general read rule below.
    (r"\bcount\b[^.\n]{0,40}?\b(?:words?|word count)\b", "wc", lambda n: ["-w"], 1),
    (r"\bcount\b[^.\n]{0,40}?\b(?:bytes?|characters?|char count)\b",
     "wc", lambda n: ["-c"], 1),
    (r"\bcount\b[^.\n]{0,40}?\blines?\b", "wc", lambda n: ["-l"], 1),
    # `cut` must be tried BEFORE `head`: "Show the first field of the file X"
    # contains both "show" and "first", and the first pattern to match wins.
    # Measured out of order, it bound `head -n 2` and returned two whole lines
    # when the sentence asked for one column.
    (r"\bcut\b|\bfields?\b|\bcolumns?\b", "cut", _cut_flags, 1),
    (r"\b(?:show|print|read|display)\b[^.\n]{0,40}?\bfirst\b",
     "head", _head_flags, 1),
    (r"\b(?:show|print|read|display)\b[^.\n]{0,40}?\blast\b",
     "tail", _tail_flags, 1),
    (r"\bsort\b", "sort", _no_flags, 1),
    (r"\b(?:checksum|sha256)\b", "sha256sum", _no_flags, 1),
    # --- the rest of the surface the acceptance layer already knows how to
    # judge.  Every program below is in _READ_ONLY_COMMANDS or
    # _MUTATING_POSTCONDITIONS, so each one is verified by machinery that
    # already existed: nothing here adds a way to be trusted, only a way to be
    # asked.  Measured before this block, 11 of those 30 commands were reachable
    # from English and 19 were not.
    (r"\bmd5\b", "md5sum", _no_flags, 1),
    (r"\bunique\b", "uniq", _no_flags, 1),
    (r"\breverse\b[^\n]{0,40}?\blines?\b", "tac", _no_flags, 1),
    (r"\bnumber\b[^\n]{0,40}?\blines?\b", "nl", _no_flags, 1),
    # Order matters: the first pattern to match wins, so the narrower claims
    # about a path come before the general one about a directory.  Measured out
    # of order, "Show the directory name of X" matched (show ... directory) and
    # bound `ls` on a file.
    (r"\bbase ?name\b", "basename", _no_flags, 1),
    (r"\b(?:directory name|parent directory)\b", "dirname", _no_flags, 1),
    (r"\b(?:list|show)\b[^\n]{0,40}?\bdirectory\b", "ls", _no_flags, 1),
    (r"\b(?:real|absolute|full) path\b", "realpath", _no_flags, 1),
    (r"\b(?:octal|byte) dump\b", "od", _no_flags, 1),
    # The pattern is deliberately narrow.  The PROGRAM is called `file`, and the
    # word "file" is in almost every sentence this module ever sees, so a loose
    # pattern here would steal routes the way a bare task verb on the command
    # runner's keywords once stole the model's own audit.  Only an explicit ask
    # about a file's TYPE reaches it.
    (r"\bfile type\b|\btype of the file\b|\bwhat type\b", "file", _no_flags, 1),
    # Two operands, both stated.  `cmp` is kept distinct from `diff` because it
    # answers a different question -- equal or not, rather than how they differ.
    # Both report their answer as an exit status, which the adapter is now told
    # about by _declare_an_exit_status_answer and the verifier re-derives by
    # re-running the command and comparing the code.
    # `cmp` asks a question `diff` does not answer: equal or not, with no
    # account of how they differ.  It is reachable only from a sentence that
    # SAYS byte-for-byte, never from the word "compare" alone -- "compare a and
    # b" is asking how they differ, which is diff's answer, and the first
    # pattern to match wins.
    #
    # This row was previously withheld on the stated ground that reaching `cmp`
    # would need "compare" and "bytes" added to the command runner's registry
    # keywords, the move that measurably took the unified model's verifier from
    # 33/33 to 32/33 on the word "count".  That ground was a claim, not a
    # measurement, and it is false: a prose pattern adds no registry keyword at
    # all.  `diff` reaches the same capability through the composer path with
    # none of its own words on the keywords list, and so does `cmp`.  The
    # registry keywords were not touched, and verify still reports 33/33.
    (r"\bcmp\b|\bbyte[ -]for[ -]byte\b|\bbyte[ -]by[ -]byte\b|\bidentical bytes\b|\bthe same bytes\b",
     "cmp", _no_flags, 2),
    (r"\bdiff\b|\bcompare\b", "diff", _no_flags, 2),
    # `stat` is deliberately ABSENT, and it was measured
    # rather than assumed:
    #
    #   stat  -> COMMAND_OUTPUT_NOT_REPRODUCED.  It prints access and modify
    #            times, so running it twice cannot give the same bytes and the
    #            re-inspection that makes a read-only command trustworthy is
    #            unavailable.  The verifier's refusal is the truthful answer.
    #
    # Binding them would produce a command that runs and then reports failure
    # over work that succeeded -- the exact shape PR #6126 closed.  A request
    # for one of them is refused instead, which is honest: nothing here can
    # verify the answer, and an unverifiable act should not be performed.
    (r"\b(?:read|show|display|print|cat)\b[^.\n]{0,40}?\bfile\b", "cat", _no_flags, 1),
)

# A command whose first operand is NOT a path but a value the sentence states.
# `grep` needs a pattern, and a pattern is exactly what a quoted value is: the
# binder already has extract_content for it, and the acceptance layer already
# re-derives the whole argv from the sentence.  Requiring BOTH a quoted pattern
# and exactly one path is what keeps this from guessing -- a search that states
# no pattern binds nothing, because an invented pattern is an invented answer.
_PROSE_COMMAND_WITH_VALUE: tuple[tuple[str, str], ...] = (
    # fgrep is tried first: a sentence that asks for literal or exact text is
    # asking for a FIXED STRING, and handing that to `grep` would let a dot or a
    # bracket in the caller's own text be read as a pattern it never wrote.
    # Which program answers is decided by what the sentence says about the text,
    # not by guessing at the text itself.
    (r"\b(?:exact|literal|fixed)\b[^\n]{0,40}?\b(?:text|string)\b", "fgrep"),
    # `egrep` is the same rule from the other side: a sentence that calls the
    # text a regular expression or a pattern is asking for a PATTERN, and
    # handing it to `fgrep` would make an alternation or a class literal.  As
    # with `fgrep`, which program answers is decided by what the sentence says
    # about the text, never by inspecting the caller's own value.
    #
    # The word "expression" is deliberately NOT a trigger, and that was measured
    # rather than assumed.  A sentence containing it ranks a NUMERIC EXPRESSION
    # capability first, which then tries to evaluate the caller's own search
    # text as an arithmetic expression and dies:
    #
    #   "…for the regular expression 'plum|grape'"  -> NUMERIC_EXPRESSION_AST_NODE_REJECTED:BinOp
    #   "…for the regular expression 'plum'"        -> NUMERIC_EXPRESSION_VARIABLE_UNBOUND:plum
    #
    # Both arrived as FAIL__LIVE_CONTROLLER_EXECUTION, never reaching the
    # command.  "regex", "extended pattern" and "extended search" bind and
    # verify exactly.  A phrasing that measurably cannot reach the command it
    # states is not a route; it is left to `grep`, which fails truthfully rather
    # than pretending.  The hijack itself is a separate, named gap: the binder
    # ranks a capability whose expression slot is unbound above a command line
    # that is fully bound.
    (r"\bregex\b|\bextended (?:pattern|regex|search)\b"
     r"|\bpattern\b[^\n]{0,30}?\b(?:match|search)\b", "egrep"),
    (r"\b(?:grep|search|find)\b", "grep"),
)

_COUNT_RE = re.compile(r"\bfirst\s+(\d+)\b|\b(\d+)\s+lines?\b")


_QUOTED = re.compile(r"""(['"])(.+?)\1""", re.S)


def _quoted_value(sentence: str) -> str | None:
    """The value a sentence delimits, when it delimits one and nothing else.

    ``extract_content`` reads a stated payload from its ROLE in the sentence --
    "the text ... to the file ...".  A search pattern has no role phrase: it is
    simply quoted.  Reading the quotes is not a guess, it is the caller having
    marked the boundary, which is the same evidence the ARGV rule already trusts
    when it splits a quoted command line.  Ambiguity refuses: two different
    quoted values in one sentence state two candidates and neither is the one.
    """
    found = [m.group(2) for m in _QUOTED.finditer(str(sentence or ""))]
    if len(found) != 1 or not found[0].strip():
        return None
    return found[0]


def _prose_count(sentence: str) -> int:
    """How many lines the sentence asked for, or 2 as the documented default."""
    m = _COUNT_RE.search(sentence)
    if m:
        return int(m.group(1) or m.group(2))
    return 2


def _prose_ordinal(sentence: str) -> int | None:
    """Which one of a series the sentence named, as a digit or as a word.

    Returns None rather than 1 when the sentence states neither.  ``head`` may
    default, because "show the first lines" is a real request with a real
    conventional answer; ``cut`` may not, because there is no conventional
    column and choosing one would be choosing the answer.
    """
    text = str(sentence or "").lower()
    # From the PROSE, never from the whole sentence.  Measured without this,
    # "Show the second column of the file canonical/astra_runtime/tmp/z1/a.txt"
    # bound `cut -f 1`: extract_number found the 1 in the directory name z1, a
    # number the sentence never stated, and it outranked the word "second".
    try:
        from canonical.runtime import goal_front_compiler_v1 as _front
        number = extract_number(_front.prose_only(sentence))
    except Exception:  # noqa: BLE001 - no front compiler, fall back to the word
        number = None
    if number is not None and float(number).is_integer() and int(number) >= 1:
        return int(number)
    for word, value in _ORDINALS.items():
        if re.search(r"\b%s\b" % word, text):
            return value
    return None


# The one shape where the destination is NOT the last operand.  "Sort the file A
# into B" states two paths in source-then-destination order, but `sort` writes
# its destination through -o, so the argv is `sort -o B A`.  The knowledge is not
# invented here either: raw_goal_trace_acceptance_v1 already records that "sort -o
# FILE" writes FILE, in _SIDE_EFFECTING_FLAGS, and refuses to treat it as a
# reader.  This routes it; _post_sort judges it.
_PROSE_COMMAND_DEST_FLAG: tuple[tuple[str, str, str], ...] = (
    # [^\n] and not [^.\n]: the text between the verb and "into" is a PATH, and
    # a path is full of dots.  Measured with [^.\n] this pattern never matched.
    (r"\bsort\b[^\n]{0,80}?\binto\b", "sort", "-o"),
)


def _prose_argv(sentence: str) -> list[str] | None:
    """The command a sentence asks for in ordinary English, or None.

    Returns None whenever the sentence does not supply the operands the program
    needs.  An arity mismatch is a refusal, never a guess: ``cp`` with one path
    would be an invented destination, and an invented operand is executed.
    """
    from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept

    known = set(_accept._READ_ONLY_COMMANDS) | set(_accept._MUTATING_POSTCONDITIONS)
    text = str(sentence or "").lower()
    paths = extract_paths(sentence)
    if not paths:
        return None
    for pattern, program, dest_flag in _PROSE_COMMAND_DEST_FLAG:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        if len(paths) != 2:
            return None
        return [program, dest_flag, str(paths[1]), str(paths[0])]
    for pattern, program in _PROSE_COMMAND_WITH_VALUE:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        value = extract_content(sentence) or _quoted_value(sentence)
        # A search pattern is frequently shaped like a filename -- 'a.c',
        # 'notes.md' -- and extract_paths cannot tell the difference, so it
        # counted the caller's own quoted text as a second operand and the
        # request was refused for want of arity.  The value is masked out
        # before the paths are read: it is a value because the caller quoted
        # it, which is the same evidence that made it the pattern.
        operand_paths = paths
        if value:
            operand_paths = extract_paths(str(sentence).replace(str(value), " "))
        if not value or len(operand_paths) != 1:
            # A pattern the sentence did not state, or more than one file to
            # search in: refuse rather than complete the command by guessing.
            return None
        return [program, str(value), str(operand_paths[0])]
    for pattern, program, flags, arity in _PROSE_COMMAND:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        if len(paths) != arity:
            # The sentence did not state enough operands for the program it
            # asked for.  Refuse; do not repeat a path to make the numbers fit.
            return None
        if program == "cut":
            column = _prose_ordinal(sentence)
            if column is None:
                # No column stated.  Defaulting to 1 would be inventing the
                # answer to the question the sentence actually asked.
                return None
            return [program, "-f", str(column), str(paths[0])]
        argv = [program, *flags(_prose_count(text)), *paths]
        return [str(part) for part in argv if str(part)]
    return None


try:  # pragma: no cover - import-time consistency check
    from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept

    _VERIFIABLE = set(_accept._READ_ONLY_COMMANDS) | set(
        _accept._MUTATING_POSTCONDITIONS)
    assert {p for _p, p, _f, _a in _PROSE_COMMAND} <= _VERIFIABLE, (
        "a prose pattern names a program the acceptance layer cannot verify")
except Exception:  # noqa: BLE001 - the layer may be absent; routing still works
    pass


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
            #
            # Unless the sentence states content and says where THAT goes.  A
            # request can name two destinations with two different roles:
            #
            #   "Write the text 'hello patch' to the file out.txt
            #    and save the report to report.json."
            #
            # paths[-1] is report.json, so the stated text was written into the
            # report and out.txt -- the file the sentence actually asked for --
            # was never created.  Measured on e00d2d5: the chain ran one step,
            # wrote report.json, and the artifact gate correctly refused with
            # PROMISED_ARTIFACT_MISSING:out.txt.  The gate was right; the binding
            # was wrong.
            #
            # The destination the content runs to is the path the sentence puts
            # immediately after the payload, which is the same notion
            # _payload_runs_to_the_destination already verifies on the acceptance
            # side -- and it is only consulted when content was actually stated,
            # so a sentence with no payload keeps binding exactly as before.
            destination = extract_content_destination(goal)
            if destination and destination in paths:
                args[slot] = destination
            elif paths:
                args[slot] = paths[-1]
        elif t == "ARGV":
            argv = extract_argv(goal)
            if argv:
                args[slot] = argv
                _declare_a_consumed_output(args, argv)
                _declare_an_exit_status_answer(args, argv)
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


def _declare_an_exit_status_answer(args: dict[str, Any], argv: Sequence[str]) -> None:
    """Tell the adapter when the command's exit status IS its answer.

    Written on the shape of ``_declare_a_consumed_output`` directly above, and
    for the same reason: the adapter is the producer and must not decide whether
    a fact is a failure.  The knowledge is read from the acceptance layer's own
    table rather than written here, so a program is only ever declared an
    answer-reporter when a verifier exists to judge the answer -- and the codes
    are enumerated there, so `diff` exiting 2 for "trouble" still fails.
    """
    if not argv:
        return
    program = str(argv[0]).rsplit("/", 1)[-1]
    try:
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept
        codes = _accept._ANSWER_IS_THE_EXIT_STATUS.get(program)
    except Exception:  # noqa: BLE001 - no table, no declaration
        codes = None
    if codes:
        args["exit_status_is_the_answer"] = ",".join(
            str(code) for code in sorted(codes))


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
