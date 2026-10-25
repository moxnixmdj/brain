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

import fnmatch
import os
import pathlib
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


def _contradicts_the_stated_payload(goal: str, token: str) -> bool:
    """True when the sentence states a TEXT payload and the token offers JSON.

    Measured, and it is not a corner.  "Write the message 'PROJECT BRAIN' into
    the file X" and "Write the string ... to the file X" were both routed to
    json.file.write, which correctly refused the plain text and wrote nothing.
    Neither "json" nor "text" appears in those sentences, so json.file.available
    and text.file.available scored identically on the word "file" -- and the tie
    was then broken ALPHABETICALLY, which always favours the JSON writer.  The
    requests that happened to work did so by luck: "text", "content" and
    "output" are keywords of the text writer, so any sentence using them scored
    it higher, and "into the output file" worked only because of the word
    "output".

    This is the same failure candidate_tokens' own docstring already records --
    a request routed to a JSON writer that refused the plain text with
    CONTENT_NOT_VALID_JSON and wrote neither file -- arriving by a different
    door: there a destination's suffix supplied the word "json", here nothing
    supplied either word and the alphabet decided.

    Scoped as narrowly as the claim allows.  It never promotes anything, only
    demotes, and only a JSON token, and only when the sentence states a payload
    the brain already reads as TEXT -- extract_content is that test, and its own
    patterns require a text role word, so no new vocabulary is introduced here.
    A sentence that says "json" is left alone.  It sits AFTER the score in the
    sort key, so it can only break an exact tie and can never outrank a
    capability the sentence scored higher.
    """
    if not str(token or "").lower().startswith("json."):
        return False
    if extract_content(goal) is None:
        # The sentence states no text payload, so it makes no claim a JSON
        # writer would contradict.  "Copy the file a to b" is untouched.
        return False
    try:
        from canonical.runtime import goal_front_compiler_v1 as _front
        prose = _front.prose_only(goal)
    except Exception:  # noqa: BLE001 - no front compiler, fall back to the goal
        prose = str(goal or "")
    return not re.search(r"\bjson\b", str(prose), re.I)


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
    # The last two terms are the tiebreak, and their ORDER is the fix.  A
    # capability that contradicts the payload the sentence states is demoted
    # below one that does not, but only once the score is equal -- so this can
    # break a tie and can never overturn the words.
    scored.sort(key=lambda pair: (pair[1] not in bound,
                                  -pair[0],
                                  _contradicts_the_stated_payload(goal, pair[1]),
                                  pair[1]))
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
    # A sentence that STATES a command line is not a token-scoring question.
    # `candidate_tokens` scores the registry's keywords against the sentence's
    # prose, so a sentence whose words match no keyword scores nothing at all --
    # measured on caaf2e7: "Make a folder named X" returned
    # OPEN__COMPOSER_NO_REACHABLE_TOKEN with tried=[] (the word "folder" is in
    # no capability's keywords), while extract_argv had ALREADY returned
    # ['mkdir', X].  The same sentence with "directory" in place of "folder"
    # routed fine, because one word happened to be a keyword.  Whether a request
    # the machine can do is served should not depend on that coincidence.
    #
    # Scoped to what the sentence states: extract_argv returns one settled argv
    # or refuses on ambiguity, and the acceptance layer re-derives it and stops
    # any step whose argv the sentence does not contain
    # (STEP_COMMAND_NOT_IN_THE_REQUEST).  Tried AFTER the token loop, so this
    # only adds reach where there was none -- it cannot preempt a route that
    # already worked.
    stated_command = extract_argv(goal)
    if stated_command is not None:
        reg = composer.load_registry()
        for cid, node in g.items():
            entry = reg.get(cid)
            if not isinstance(entry, Mapping):
                continue
            slots = {str(k or "").lower() for k in
                     ((entry.get("action_template") or {}).get("args") or {})}
            # "Declares an argv slot" is NOT "is a command runner", and measuring
            # it that way mis-routed this very sentence: the first match in the
            # graph was auto.apt.zint, a barcode-package installer that happens
            # to take an argv, and route() returned it as a PASS.  A general
            # command runner takes the command line and a place to put the
            # result, and nothing else -- a capability that also wants a package
            # name or a payload is answering a different question.
            if "argv" not in slots or not slots <= {"argv", "output_path"}:
                continue
            for token in [str(t) for t in (node.get("provides") or [])]:
                chain = composer.plan(have, token, g)
                tried.append({"token": token, "reachable": chain is not None,
                              "chain": chain, "stated_command_line": stated_command})
                if chain:
                    return {"schema": SCHEMA, "pass": True, "goal": goal,
                            "token": token, "chain": list(chain), "tried": tried,
                            "status": "PASS__COMPOSER_ROUTE_FOUND",
                            "authority": "TYPE_LEVEL_COMPOSITION_REACHABLE"}
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
# A filename may contain spaces -- "my notes.txt" is an ordinary name -- and
# every rule below is built on tokens that stop at whitespace, so such a name was
# read as two things: the tail `notes.txt`, a file the sentence never named, and
# the head as a directory, `canonical/.../tz/my`.  Measured: "Write the text
# 'hello' to the file <scratch>/my notes.txt" created a file called `my`, left
# both real files untouched, and reported
# PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.  An invented
# destination certified as the work asked for is the same defect as a destructive
# write, so a name with spaces is read whole, from the words that introduce it.
_QUOTED_SPAN = re.compile(r"\"([^\"]+)\"|'([^']+)'")
# A quoted value is a PATH when it holds a separator or ends in a lettered
# extension.  Letters, not digits: '3.5' is a number the sentence asked to be
# written, not a file.
_PATHISH = re.compile(r"/|\.[A-Za-z][A-Za-z0-9]{0,7}$")
_LEAD_STOPWORDS = frozenset({
    "in", "at", "on", "to", "from", "into", "of", "for", "which", "that", "this",
    "these", "those", "containing", "named", "called", "under", "inside", "and",
    "or", "with", "by", "the", "a", "an", "is", "are", "was", "were", "it", "its"})
# "the file my notes.txt" -- the introducer, then as FEW plain words as it takes
# to reach a token that ends in an extension.  Lazy, not greedy: a greedy count
# measured "the file my notes.txt to the file backup.txt" as ONE path stretching
# across both, which is a name no sentence ever stated.
# The same distinction at the layer that fills the slots: a quoted value the
# sentence introduced as a file is an operand, while a quoted value it introduced
# as a pattern is not.
_QUOTED_AS_A_PATH = re.compile(
    r"\b(?:files?|paths?|documents?)\s+(?:\"[^\"]+\"|'[^']+')")
_INTRO_PATH = re.compile(
    r"\b(?:files?|paths?|documents?)\s+"
    r"((?:[^\s,;:'\"()]+[ ]){0,5}?[^\s,;:'\"()]*\.[A-Za-z][A-Za-z0-9_]{0,7})")
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
    found: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        if candidate and candidate not in seen:
            found.append(candidate)
            seen.add(candidate)

    # A quoted name is read whole first, and then removed from the sentence, so
    # its fragments cannot be picked up as separate paths below.  Only a quoted
    # value the sentence INTRODUCED as a file qualifies: shape alone cannot tell
    # them apart, and measuring that way broke a refusal -- in "Replace 'a.b'
    # with 'x' in the file A" the value 'a.b' ends in a lettered extension, so
    # reading it as a path hid it from the unsafe-value check and bound a sed
    # script the sentence was never allowed to produce.  The introducer is the
    # fact that decides it, not the spelling of the value.
    for match in _QUOTED_AS_A_PATH.finditer(str(text or "")):
        quoted = match.group(0).split(None, 1)[1].strip()
        inner = quoted[1:-1] if len(quoted) >= 2 and quoted[0] in "'" + '"' else quoted
        if inner and _PATHISH.search(inner):
            _add(inner)
            body = body.replace(match.group(0), " ")
    # Then a name with spaces, taken from the word that introduces it.  Only a
    # candidate that really holds a space needs this route, and one whose first
    # word is a preposition is not a name at all -- "which files in the
    # directory X" must keep yielding X and not a phrase.
    for match in _INTRO_PATH.finditer(body):
        candidate = match.group(1)
        if " " not in candidate:
            continue
        if candidate.split(" ", 1)[0].lower() in _LEAD_STOPWORDS:
            continue
        _add(candidate)
        body = body.replace(candidate, " ")
    # Not de-duplicated, exactly as before: "Compare the file A and A byte by
    # byte" states two operands that happen to be the same path, and a set here
    # measured that sentence as one operand and refused it for want of arity.
    matches = list(_EXT.finditer(body))
    base = len(found)
    for match in matches:
        found.append(match.group(0))
    seen.update(found)
    # A name with spaces that no word introduces -- "sort <dir>/my notes.txt".
    # Taking any run of words would invent paths out of prose, so the candidate
    # has to be a name in a directory that EXISTS: a fact about the world, not a
    # guess about the sentence.  It replaces its own tail WHERE THAT TAIL SITS,
    # because order is meaning -- `cp` takes the first path as its source and the
    # last as its destination, and appending the longer name at the end measured
    # "copy A to <dir>/my backup.txt" as a copy running backwards.
    root = pathlib.Path(__file__).resolve().parents[2]
    for offset, match in enumerate(matches):
        best = None
        left = match.start()
        for _ in range(4):
            i = left - 1
            while i >= 0 and body[i] == " ":
                i -= 1
            j = i
            while j >= 0 and body[j] not in " \t,;:'\"()":
                j -= 1
            if j >= i:
                break
            extended = body[j + 1:match.end()]
            head = extended.split(" ", 1)[0].lower()
            left = j + 1
            if head in _LEAD_STOPWORDS or " " not in extended:
                continue
            # The sentence has to say which directory to look in.  Without a
            # separator the parent of the candidate is the repository root,
            # which always exists, and the rule measured "Search the file
            # a1.txt" as a file called "Search the file a1.txt" -- the very
            # invention the disk check was here to prevent.
            if "/" not in extended:
                continue
            if ((root / extended).parent).is_dir():
                best = extended
        if best:
            found[base + offset] = best
            seen.add(best)
    # Every path already found is removed before a directory is looked for.  The
    # prefix check below cannot do this job alone, because it compares spellings:
    # for "/home/u/brain/x/a1.txt" the directory token is "home/u/brain/x", which
    # is not a prefix of the found path -- it is missing the leading slash -- so
    # the sentence was read as naming a file AND a folder, `wc` was refused for
    # want of arity, and the request fell through to a chain that reported
    # pass True with no answer and no acceptance at all.  The same happened to
    # "./x/a1.txt".  A path that has been read is not also its own parent.
    for stated in found:
        body = body.replace(str(stated), " ", 1)
    for m in _DIRPATH.finditer(body):
        token = m.group(0)
        if token in seen:
            continue
        # The parent of a path already found is not a second path.  Appending it
        # would move paths[-1] -- which is what PATH_OUTPUT binds -- off the file
        # the sentence named and onto the directory holding it, so a command
        # would be told its output is a folder it was never asked to produce.
        if any(f == token or f.startswith(token + "/") or f.startswith(token + " ")
               for f in found):
            # The last arm is a name with spaces: "canonical/x/my" is the head of
            # "canonical/x/my backup.txt", not a directory holding it.
            continue
        _add(token)
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
# A destination may be DESCRIBED, not only named.  Without this, "to the output
# file X" captured the adjective as the destination and the path was never
# bound:
#
#     "to the output file X"      -> destination "output"
#     "to the target file X"      -> destination "target"
#     "into the same file X"      -> destination "same"
#
# Measured: six of seven ordinary phrasings of a write request lost their
# destination this way, and only the bare "to the file X" worked.
#
# This list is deliberately the same shape and the same words as
# _BETWEEN_PAYLOAD_AND_DEST in raw_goal_trace_acceptance_v1.  The two are not
# shared on purpose -- an inspector that asks the binder what it meant is not an
# inspector -- but they answer the same question about the same sentence, so if
# they drift a request is bound by one and refused by the other.  A test asserts
# they agree across a table of phrasings; that test is the thing that keeps them
# from drifting again.
#
# The truncation defence is untouched: _DEST_AHEAD still requires a path-like
# token to begin the instant the description ends, and a truncated payload is
# followed by the rest of the payload, which is prose and not a path.
_DEST_MODIFIER = r"(?:(?:output|target|destination|same|given|stated|named|following|new|existing)\s+){0,2}"
_DEST_WORDS = (r"\s+(?:to|into|in|at)\s+(?:(?:the|a|an)\s+)?" + _DEST_MODIFIER +
               r"(?:file|path|folder|directory)?\s*")
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


# The units `wc` counts, and the words that say something is being counted.
# Defined once so the three `wc` rules cannot drift apart from each other.
_WC_QTY = r"count|counts|counting|how many|number of|total|tally"
_WC_WORDS = r"words?|word count"
_WC_CHARS = r"bytes?|characters?|char count|byte count"
_WC_LINES = r"lines?|line count"

_PROSE_COMMAND: tuple[tuple[str, str, Any, int], ...] = (
    # Synonyms measured rather than guessed: "duplicate the file a as b" bound
    # nothing at all, so a request the machine can do was refused for want of one
    # word in a table.  Each addition here is a phrasing that was measured to
    # fail, not a synonym thought up in advance.
    # The same filter claim that `rm` must not steal, `cp` must not steal
    # either -- and it is worse here, because `cp` sits first in the table and
    # needs two operands, so "Remove the duplicate lines from the file X"
    # matched `copy|duplicate`, found one path instead of two, and returned
    # None, which ends the search.  The whole table was abandoned on a word that
    # meant "repeated", not "make a second copy".
    (r"\b(?:copy|duplicate)\b(?![^\n]{0,20}?\blines?\b)", "cp", _no_flags, 2),
    (r"\b(?:move|rename)\b", "mv", _no_flags, 2),
    # "Erase the file X" measured to bind nothing.  The negative lookahead is
    # scoped to exactly one claim: removing LINES that are duplicated is a
    # filter over a file that stays, not a deletion of it.  Measured without it,
    # "Remove the duplicate lines from the file X" matched `rm` first -- it is
    # third in this table and the first pattern to match wins -- so teaching
    # `uniq` the word "duplicate" alone would have changed nothing at all.
    (r"\b(?:remove|delete|erase)\b"
     r"(?![^\n]{0,40}?\b(?:duplicate|repeated|unique)\b[^\n]{0,20}?\blines?\b)",
     "rm", _no_flags, 1),
    (r"\b(?:create|make)\b[^.\n]{0,40}?\b(?:directory|folder)\b", "mkdir",
     _no_flags, -1),
    (r"\b(?:create|make|touch)\b[^.\n]{0,40}?\bempty file\b", "touch", _no_flags, 1),
    # Case conversion needs no stdin, and that is the whole reason it is here:
    # `tr` reads standard input, which the adapter never passes, so "convert this
    # file to upper case" looked blocked behind that wall.  It is not blocked --
    # `sed 's/.*/\U&/'` reads the FILE and prints the converted text, so it is a
    # reader like cat, the inspector re-runs it and compares stdout, and the
    # destination is written by the mechanism that already existed.  In place it
    # is also already permitted, because sed is a named transform.
    #
    # The script is fixed by this rule rather than taken from the sentence, so
    # there is no value to escape and no way for the sentence to change what the
    # command means.
    (r"\bcompress(?:es|ed|ing)?\b|\bgzip(?:s|ped|ping)?\b", "gzip", lambda n: [], 1),
(r"\bupper[\s-]*case\b|\buppercase\b", "sed", lambda n: ["-e", "s/.*/\\U&/"], 1),
    (r"\blower[\s-]*case\b|\blowercase\b", "sed", lambda n: ["-e", "s/.*/\\L&/"], 1),
    # The three things `wc` counts, each stated by its own noun.  Order matters
    # only in that all three are narrower than the general read rule below.
    # The unit `wc` counts is named by the sentence, and English puts the noun
    # on either side of the counting word: "count the words", "how many words",
    # "the number of words" and "the word count" all name the same unit.  The
    # three rules below used to require the counting word FIRST, so "Show the
    # word count of the file X" bound no command at all and fell through to
    # capability selection -- which measured as `docx.document.verify.intent_ooxml`,
    # a Word-document verifier, answering a request to count words.  Each rule
    # now matches the unit and the counting word in EITHER order.
    (r"\b(?:%s)\b[^\n]{0,40}?\b(?:%s)\b|\b(?:%s)\b[^\n]{0,20}?\b(?:%s)\b"
     % (_WC_QTY, _WC_WORDS, _WC_WORDS, _WC_QTY), "wc", lambda n: ["-w"], 1),
    (r"\b(?:%s)\b[^\n]{0,40}?\b(?:%s)\b|\b(?:%s)\b[^\n]{0,20}?\b(?:%s)\b"
     % (_WC_QTY, _WC_CHARS, _WC_CHARS, _WC_QTY), "wc", lambda n: ["-c"], 1),
    # "How many lines are in the file X" is at least as ordinary as "count the
    # lines", and measured to bind nothing.
    (r"\b(?:%s)\b[^\n]{0,40}?\b(?:%s)\b|\b(?:%s)\b[^\n]{0,20}?\b(?:%s)\b"
     % (_WC_QTY, _WC_LINES, _WC_LINES, _WC_QTY), "wc", lambda n: ["-l"], 1),
    # `cut` must be tried BEFORE `head`: "Show the first field of the file X"
    # contains both "show" and "first", and the first pattern to match wins.
    # Measured out of order, it bound `head -n 2` and returned two whole lines
    # when the sentence asked for one column.
    (r"\bcut\b|\bfields?\b|\bcolumns?\b", "cut", _cut_flags, 1),
    # "Show me the beginning of the file X" measured to bind `cat`, which returns
    # the whole file.  Not a false answer, but the sentence asked for the
    # beginning and `head` is the command that means it.
    (r"\b(?:show|print|read|display)\b[^.\n]{0,40}?\b(?:first|beginning)\b",
     "head", _head_flags, 1),
    (r"\b(?:show|print|read|display)\b[^.\n]{0,40}?\b(?:last|final|end)\b",
     "tail", _tail_flags, 1),
    # "Put the lines of the file X in order" and "Arrange the lines of the file
    # X in order" both measured to bind nothing: the sentence states the RESULT
    # rather than naming the program.
    (r"\bsort(?:ed|ing)?\b|\bin order\b|\balphabetical(?:ly)?\b", "sort",
     _no_flags, 1),
    # `md5sum` must be tried BEFORE `sha256sum` now that the latter answers to
    # the generic word "hash": "Compute the md5 hash of X" would otherwise bind
    # sha256sum and return the wrong digest for an algorithm the sentence named.
    (r"\bmd5\b", "md5sum", _no_flags, 1),
    # "Compute the hash of the file X" and "Hash the file X" both measured to
    # bind nothing, and both fell through to capability selection -- the first
    # to `source.evidence.extract.objective_grounded.stdlib`, which cannot hash
    # a file at all.  sha256 is the default when the sentence names no algorithm.
    (r"\b(?:checksum|sha256|sha-256|hash|hashes|hashed|digest|fingerprint)\b",
     "sha256sum", _no_flags, 1),
    # --- the rest of the surface the acceptance layer already knows how to
    # judge.  Every program below is in _READ_ONLY_COMMANDS or
    # _MUTATING_POSTCONDITIONS, so each one is verified by machinery that
    # already existed: nothing here adds a way to be trusted, only a way to be
    # asked.  Measured before this block, 11 of those 30 commands were reachable
    # from English and 19 were not.
    # `uniq` alone removes ADJACENT duplicates only, so on a file that was never
    # sorted it answers "the unique lines" with duplicates still in it.  Measured
    # on apple/banana/apple/cherry: the answer held `apple` twice and was
    # certified as an exact semantic acceptance, because acceptance checks
    # reproducibility and `uniq` is perfectly reproducible.  `sort -u` is the
    # distinct set the sentence asked for; `sort` is already in
    # _READ_ONLY_COMMANDS and `-u` is not a side-effecting flag.
    (r"\bunique\b|\b(?:duplicate|duplicates|repeated)\b[^\n]{0,20}?\blines?\b",
     "sort", lambda _n: ["-u"], 1),
    (r"\breverse\b[^\n]{0,40}?\blines?\b|\blines?\b[^\n]{0,40}?\breverse\b",
     "tac", _no_flags, 1),
    # "Add line numbers to the file X" measured to bind nothing: the noun and
    # the counting word are the other way round from "number the lines".
    (r"\bnumbers?\b[^\n]{0,40}?\blines?\b|\blines?\b[^\n]{0,20}?\bnumbers?\b",
     "nl", _no_flags, 1),
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
    (r"\bdiff\b|\bcompare\b|\bdiffer\w*\b", "diff", _no_flags, 2),
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
    # "Output the contents of the file X" measured to bind nothing.  The
    # lookahead is load-bearing: "Write the text 'hello' to the OUTPUT FILE X"
    # also contains "output" followed by "file", and measured without it this
    # rule stole the write -- the sentence was served by `cat` and refused with
    # PROMISED_ARTIFACT_MISSING.  "output" counts only as a verb.
    # "Join the files A and B into the file C" names TWO sources, so it cannot
    # use the single-operand `cat` rule at the end of this table.  It is placed
    # here because the first pattern to match wins, and the generic read rule
    # would otherwise take the sentence and refuse it on arity.
    (r"\b(?:join|concatenate|combine|merge)\b", "cat", _no_flags, 2),
    (r"\b(?:read|show|display|print|cat)\b[^.\n]{0,40}?\bfile\b"
     r"|\boutput\b(?!\s+file\b)[^.\n]{0,40}?\bfile\b", "cat", _no_flags, 1),
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
    # "regular expression" WAS excluded from this trigger, on a measurement: a
    # sentence containing the word "expression" ranked math.numeric_expression.sympy
    # first on that single generic token scoring 11, the calculator then treated
    # the caller's own search text as arithmetic and died at execution with
    # NUMERIC_EXPRESSION_VARIABLE_UNBOUND:plum -- so the phrasing could never
    # reach the command it states.
    #
    # The cause was not the trigger and never was: admission granted a capability
    # whose own declared precondition (`typed.scalar.inputs.available`, supplied
    # by nothing in the registry) the sentence could not meet, because its
    # `variables` slot was silently defaulted to `{}` instead of refused.  That
    # is now refused at admission, on the capability's own contract, and the
    # existing composition fallthrough serves the command.  So the phrasing is a
    # route again -- but it is pinned by a test that fails if the guard is ever
    # removed, because without the guard this row measurably cannot work.
    (r"\bregex\b|\bregular expression\b|\bextended (?:pattern|regex|search)\b"
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


def _sed_print_script(address: str, sentence: str) -> str:
    """The sed script that prints `address`, in the case the sentence states.

    sed composes an ADDRESS with a COMMAND inside one script, so "the third line
    in upper case" is `sed -n '3s/.*/\\U&/p'` -- a single command with no
    pipeline, no shell and no second step.  The composition is ordinary sed and
    was probed directly before this was written.

    Measured without it: the sentence bound `sed -n 3p` and answered 'apple pie'
    in lower case, certified as an exact semantic answer, because the case the
    sentence asked for was dropped and nothing reported the drop.  A pipeline was
    recorded as the reason this could not be answered; it was not -- one program
    already does both halves.
    """
    text = str(sentence or "").lower()
    if re.search(r"\bupper[\s-]*case\b|\buppercase\b", text):
        return "%ss/.*/\\U&/p" % address
    if re.search(r"\blower[\s-]*case\b|\blowercase\b", text):
        return "%ss/.*/\\L&/p" % address
    return "%sp" % address


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


# The words that put a command's result somewhere.  Scoped to the claim the
# sentence makes: a path is only a destination if the sentence introduces it as
# one, so a command that simply takes two files keeps taking two files.
_RESULT_DESTINATION = re.compile(
    r"\b(?:into|to|onto|as|inside)\b[^\n]{0,40}?$"
    r"|\b(?:write|save|put|store|output|send|direct)\b[^\n]{0,40}?$",
    re.IGNORECASE)


def _states_a_destination_for_the_result(sentence: str, dest: Any) -> bool:
    """True when the sentence introduces `dest` as where the result goes."""
    text = str(sentence or "")
    where = text.rfind(str(dest))
    if where <= 0:
        return False
    return bool(_RESULT_DESTINATION.search(text[:where]))


# A substitution states TWO quoted values, and `_quoted_value` refuses on two by
# design -- it cannot know which one the sentence meant.  Here the order is the
# meaning, and only for phrasings whose word order fixes it.  "Substitute 'pear'
# for 'apple'" is deliberately absent: it puts the NEW value first, and guessing
# at a word order would silently rewrite the file the wrong way round.
_PROSE_COMMAND_WITH_TWO_VALUES: tuple[tuple[str, str], ...] = (
    (r"\breplace\b[^\n]{0,60}?\bwith\b", "sed"),
    (r"\bchange\b[^\n]{0,60}?\bto\b", "sed"),
    (r"\bsubstitut(?:e|ing)\b[^\n]{0,60}?\bwith\b", "sed"),
)
# sed treats the left side as a regular expression and `|` is this rule's
# delimiter, so a value carrying either would make the command mean something
# the sentence did not say.  Refuse rather than edit the file wrongly.
# sed treats the left side as a regular expression, and `|` is this rule's
# delimiter, so a value carrying either -- or a newline, which would end the
# expression -- would make the command mean something the sentence did not
# say.  Written with chr() so the set is exactly these five characters and
# cannot be mangled by an escape sequence on the way into the file.
# A character that would make the command mean something the sentence did not
# say.  The dot belongs here on the same grounds as the pipe: in a sed pattern it
# matches ANY character, so "replace 'a.b' with 'x'" would also replace "axb".
# Refusing is the only truthful answer, and until now the refusal this sentence
# got was an accident of a corrupted path reading as two operands.
_SED_UNSAFE = "|" + chr(92) + "&" + chr(10) + chr(13) + "."


def _mask_a_quoted_value(sentence: str, value: str) -> str:
    """Blank out a quoted value without touching anything else in the sentence.

    A blind ``re.sub(value, " ")`` eats the same characters wherever they occur,
    including inside a path: masking the value 'x' turned
    "canonical/.../m3v7x/a1.txt" into "canonical/.../m3v7 /a1.t t" -- a path that
    exists nowhere, and one that then read as TWO operands, which is the only
    reason a sentence replacing 'a.b' was ever refused.  The sentence quoted the
    value, so the quoted span is what gets removed, quotes and all, and nothing
    outside it can be hit.
    """
    body = str(sentence)
    for match in _QUOTED_SPAN.finditer(body):
        inner = str(match.group(1) or match.group(2) or "").strip()
        if inner == str(value):
            return body.replace(match.group(0), " ", 1)
    return body


def _quoted_values(sentence: str) -> list[str]:
    """Every value the sentence delimits, in the order it states them."""
    return [m.group(2) for m in _QUOTED.finditer(str(sentence or ""))]


# Filtering lines OUT of a file is `grep -v`.  Two shapes, and neither is a
# guess about the pattern:
#   * the sentence quotes the text and says the lines must NOT have it;
#   * the sentence says the lines are EMPTY, which is one exact pattern.
# "empty" is not a loose synonym here -- it names `^$` and nothing else, the same
# way an ordinal names a column number.
_NEGATED_LINE = re.compile(
    r"\b(?:do(?:es)?n't|do(?:es)? not|don't|without|excluding|except)\b"
    r"[^\n]{0,40}?\b(?:contain|containing|match|matching|include|including|have)\b"
    r"|\bnot\b[^\n]{0,20}?\b(?:contain|match|include)\b"
    # "the lines WITHOUT 'apple'" -- the same direct introduction, negated.
    # Measured: it satisfied neither arm, because neither `without` nor the
    # value was followed by a verb of containing, so the sentence fell through
    # to `cat` and was certified with the whole file.
    r"|\b(?:without|excluding|except)\b[^\n]{0,20}?['\"]")
# Both word orders.  Measured: "Show the empty lines in the file X" matched and
# "Show the lines in the file X that are empty" did not, so the second fell all
# the way through to `cat` and was certified with the whole file as the answer to
# a question about one line of it.
_BLANK_LINE = re.compile(
    r"\b(?:empty|blank)\b[^\n]{0,40}?\blines?\b"
    r"|\blines?\b[^\n]{0,40}?\b(?:empty|blank)\b")
# The verbs that ask for lines to be TAKEN OUT, as against shown.  `-v` inverts,
# so it belongs to these and not to the others: "remove the empty lines" keeps
# the ones that are not empty, while "show the empty lines" asks for the empty
# ones.  Hard-coding `-v` measured as answering the second with the first.
_REMOVES_THE_LINES = re.compile(r"\b(?:remove|delete|drop|strip)\b")
_MENTIONS_LINES = re.compile(r"\blines?\b")
# The questions a count rule and a line-number rule own.  A sentence that asks
# HOW MANY lines hold a text, or WHICH ones, is not asking for the lines
# themselves, and answering it with the lines would be a certified wrong answer.
_ASKS_A_COUNT_OR_A_NUMBER = re.compile(
    # `which`, `what` and `where` only when the sentence ASKS with them, at its
    # head.  Taken from anywhere in the sentence they exclude a relative pronoun
    # too: "the lines in X WHICH include 'apple'" was measured refused, because
    # the `which` in it introduces the value and asks nothing.
    r"^\s*(?:which|what|where)\b|\b(?:%s)\b|\bnumber\b" % _WC_QTY)
# The introducers that make a quoted value LITERAL text.  `match` is deliberately
# absent: "the lines matching 'ap.le'" is pattern language, and a rule further
# down already answers it with `grep`, while this block sends a quoted value to
# the literal matcher.  Measured, letting this arm claim it: the sentence went
# from `grep` to a refusal, and the two spellings of the same question --
# "Find the lines ... matching" and "Show the lines ... matching" -- were already
# answered by different programs on main, which is a question about matcher
# selection and not one this change should settle by accident.
_STATES_A_LITERAL_VALUE = re.compile(
    r"\bcontain(?:s|ed|ing)?\b|\binclud\w*|\bhold(?:s|ing)?\b|\bhave\b|\bhas\b"
    r"|\bwith\b[^\n]{0,20}?['\"]"
    r"|\b(?:without|excluding|except)\b[^\n]{0,20}?['\"]"
    r"|\b(?:do(?:es)?n't|do(?:es)? not|don't|not)\b[^\n]{0,20}?"
    r"\b(?:contain|includ\w*|have)\b")
# The words that make a quoted value a PATTERN rather than a PAYLOAD.  Shape
# cannot tell them apart -- both are one quoted string -- and neither can the
# word "line", because "Write the line 'PROJECT BRAIN' to the file X" satisfies
# `_FILTER_LINE` and quotes exactly one value.  Measured: taking that sentence
# here bound `grep` over a file the sentence was asking to be WRITTEN, and the
# promised artifact was then correctly reported missing.  The introducer is the
# evidence, and this is the same reason `_quoted_value` reads a payload from its
# role in the sentence rather than from its quotes.
_STATES_CONTAINMENT = re.compile(
    r"\bcontain(?:s|ed|ing)?\b|\bmatch(?:es|ed|ing)?\b|\binclud\w*"
    r"|\bhold(?:s|ing)?\b|\bhave\b|\bhas\b"
    # "the lines WITH 'apple'" introduces the value directly, with no verb of
    # containing at all.  Scoped to a word that runs straight into the quotation,
    # so a "with" anywhere else in the sentence cannot claim the value.
    r"|\bwith\b[^\n]{0,20}?['\"]")
# A SECOND operation stated alongside the filter.  No single command performs
# both halves, so a sentence that states one is refused rather than served with
# the other half silently dropped -- which is the defect, not the fix.
_ANOTHER_OPERATION = re.compile(
    r"\bsort(?:s|ed|ing)?\b|\bunique\b|\bduplicat\w*|\bupper[\s-]*case\b|\buppercase\b"
    r"|\blower[\s-]*case\b|\blowercase\b|\brevers\w*|\bnumbered\b")
_FILTER_LINE = re.compile(
    r"\b(?:remove|delete|drop|strip|write|show|list|print)\b[^\n]{0,40}?\blines?\b")


# A request about a DIRECTORY is not the same request about a file, and the
# difference is a flag the sentence itself states.  "Copy the directory A to the
# directory B" says "directory" twice; `cp` without -r refuses it and the report
# came back COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN -- the worst shape of answer,
# because it claims not to know whether anything happened.
# A sentence that says "append" is making a promise about what SURVIVES: the
# file's current content stays and the new text comes after it.  A plain payload
# write replaces the whole file, so binding one for such a sentence deletes the
# content the sentence promised to keep -- and then reports exact semantic
# acceptance over a file holding five bytes.  Measured: "Append the text 'hello'
# to the file A" turned 'apple\nbanana\n' into 'hello' and passed.  No capability
# in the registry writes in append mode, so the honest outcome is a refusal.
# The verbs that say a sentence wants to be SHOWN something.  A read is not a
# write whatever command serves it: "Show the file X in upper case" asks for the
# upper-cased text, and "Convert the file X to upper case" asks for X to change.
# Both bind the same rewriting sed script, so the script cannot tell them apart
# and only the sentence can.  Measured: the first turned 'apple\nbanana\n' into
# 'APPLE\nBANANA\n' on disk and was certified as an exact semantic answer -- a
# request to be shown something destroyed the file it named, which is the same
# defect `sed -n 3p` had, one layer up, where the script really does rewrite.
_READ_VERBS = re.compile(r"\b(?:show|print|read|display)\b")

_KEEPS_EXISTING_CONTENT = re.compile(
    r"\bappend(?:s|ed|ing)?\b|\bprepend(?:s|ed|ing)?\b|\binsert(?:s|ed|ing)?\b"
    r"|\b(?:to|at)\s+the\s+(?:end|beginning|start|top|bottom)\s+of\b"
    r"|\bwithout\s+(?:losing|deleting|removing|replacing)\b")
# The capabilities that replace a file wholesale with a payload they were given.
_PLAIN_PAYLOAD_WRITES = frozenset({"text.file.write", "json.file.write"})


def keeps_existing_content(sentence: Any) -> bool:
    """True when the sentence promises a file's current content survives."""
    return bool(_KEEPS_EXISTING_CONTENT.search(str(sentence or "").lower()))


_DIRECTORY_REQUEST = re.compile(r"\bdirector(?:y|ies)\b|\bfolders?\b")
_RECURSIVE_REQUEST = re.compile(
    r"\bfiles?\b[^\n]{0,20}?\bin the\b[^\n]{0,20}?\bdirector(?:y|ies)\b"
    r"|\ball the files\b|\bevery file\b|\beach file\b")
_FIND_SUFFIX = re.compile(r"\bend(?:s|ing)?\s+with\s+([^\s,]+)")
_FIND_PREFIX = re.compile(r"\b(?:start|begin)(?:s|ing)?\s+with\s+([^\s,]+)")
# "all the .log files in the directory D" names a SET of files by pattern, which
# no fixed-arity rule can hold: the sentence states one path and a shape.  The
# pattern is expanded here, from the sentence's own words, and the command runs
# on exactly the names it produced.
_EVERY_FILE = re.compile(r"\b(?:all|every|each)\b[^\n]{0,60}?\bfiles?\b")
_ONE_LEVEL_ONLY = re.compile(r"\brecursive(?:ly)?\b|\bsub[- ]?director(?:y|ies)\b|\btree\b")
_FILE_SUFFIX = re.compile(r"\.([A-Za-z0-9]+)\b")
# The words that say a sentence wants the directory LISTED rather than read.
_LISTING_REQUEST = re.compile(r"\b(?:list|names?|what|which)\b")


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
    # The table is matched against the sentence with every path masked out.  A
    # path is a name, not prose, and leaving it in measured two ways: a fixture
    # called `blank.txt` satisfied the blank-line pattern by its own name, and
    # "the lines of the file <path> in reverse order" put forty-plus characters
    # between two words the pattern expected to be neighbours.  Masking first is
    # the same discipline `_prose_ordinal` already applies to numbers.
    for _p in paths:
        text = text.replace(str(_p).lower(), " ")
    for pattern, program, dest_flag in _PROSE_COMMAND_DEST_FLAG:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        if len(paths) != 2:
            return None
        return [program, dest_flag, str(paths[1]), str(paths[0])]
    # "find" alone is NOT enough, and measuring it that way was a regression:
    # "Find the lines in the file X matching 'apple'" is an ordinary search, and
    # the word "find" in it stole the sentence and bound `find X -name 'apple'`.
    # `find` walks a tree, so the sentence has to name one.
    if (re.search(r"\bfind\b", text) and "find" in known
            and _DIRECTORY_REQUEST.search(text)):
        # `find` only reads the tree and prints what is there, so the inspector
        # re-runs it and compares stdout -- no new way to be trusted, only a new
        # way to be asked.  The name pattern is either the value the sentence
        # quoted or the ending it spelled out; "that end with .txt" names `*.txt`
        # and nothing looser.
        values = _quoted_values(sentence)
        masked = str(sentence)
        needle = None
        if len(values) == 1:
            needle = values[0]
            masked = _mask_a_quoted_value(masked, needle)
        else:
            m = _FIND_SUFFIX.search(text) or _FIND_PREFIX.search(text)
            if m:
                # Quotes only.  Stripping the dot too turned ".txt" into the
                # pattern `*txt`, which is looser than the sentence said: it
                # would also select a file called `a-txt` or `notes_txt`.
                token = m.group(1).strip("'\"")
                if not token:
                    return None
                needle = ("*" + token) if _FIND_SUFFIX.search(text) else (token + "*")
                masked = re.sub(re.escape(m.group(1)), " ", masked, flags=re.IGNORECASE)
        operand_paths = extract_paths(masked)
        if len(operand_paths) != 1:
            # No single directory to search, or more than one: refuse rather than
            # pick one and report a search the sentence did not describe.
            return None
        argv = ["find", str(operand_paths[0])]
        if needle:
            argv += ["-name", str(needle)]
        return argv
    # The verb is not what makes a sentence ask for lines.  `_FILTER_LINE`
    # requires one of remove/delete/drop/strip/write/show/list/print before
    # "lines", so the plainest way to ask -- the noun phrase on its own, "the
    # lines in X with 'apple'" -- matched nothing and was refused, while "Show
    # me the lines in X with 'apple'" was answered.  Both ask the same question.
    # The extra arm is scoped to a sentence that mentions lines AND states
    # containment or its negation, and it stays away from the two questions a
    # count and a line-number rule own: "How many lines in X contain 'apple'"
    # must stay a count and "Which lines in X contain 'apple'" must stay a
    # numbered listing.
    _asks_a_filter = _FILTER_LINE.search(text) or (
        _MENTIONS_LINES.search(text)
        and _STATES_A_LITERAL_VALUE.search(text)
        and not _ASKS_A_COUNT_OR_A_NUMBER.search(text))
    if _asks_a_filter and "grep" in known:
        values = _quoted_values(sentence)
        # The blank test runs over the sentence with every path masked out, the
        # way `_prose_ordinal` reads its number from the prose alone.  Measured
        # without this: a file literally named `blank.txt` satisfied the pattern
        # by its own NAME, and the gap "lines in the file <path> that are empty"
        # is longer than the pattern allowed once the path sat in the middle.
        _masked_for_blank = text
        for _p in extract_paths(sentence):
            _masked_for_blank = _masked_for_blank.replace(str(_p).lower(), " ")
        blank = bool(_BLANK_LINE.search(_masked_for_blank))
        _unspanned = _masked_for_blank
        for _span in _QUOTED_SPAN.finditer(str(sentence)):
            _unspanned = _unspanned.replace(str(_span.group(0)).lower(), " ")
        if "'" in _unspanned or '"' in _unspanned:
            # A quote mark the sentence opened and never closed, so what it quoted
            # is not recoverable: "contain 'a'b'" reads as the value `a` followed
            # by a stray fragment.  Measured, taking the recoverable part searched
            # for 'a' -- a guess at a value the sentence never delimited, and one
            # that matches three of four lines.  Refuse instead.
            #
            # Counting quote marks would be wrong here: `'a"b'` is one
            # well-formed value that happens to hold a double quote, and it has
            # three quote marks in it.  What matters is whether any quote is left
            # over once the spans the sentence really delimited are removed.
            return None
        if blank:
            # `^$` is the pattern the sentence itself described -- a regular
            # expression, so it goes to `grep` and not to the literal matcher.
            needle = "^$"
            matcher = "grep"
            invert = bool(_REMOVES_THE_LINES.search(text))
        elif len(values) == 1 and _NEGATED_LINE.search(text):
            needle = values[0]
            matcher = "fgrep"
            invert = True
        elif len(values) == 1 and _STATES_CONTAINMENT.search(text):
            # The POSITIVE half of the same sentence, which was never written:
            # "the lines in X that CONTAIN 'apple'".  `_FILTER_LINE` matched it,
            # one value was quoted, `_NEGATED_LINE` did not fire -- and then the
            # branch ended.  The sentence fell all the way through to `cat` and
            # was certified with the WHOLE FILE as the answer to a question about
            # two of its lines.  Measured: nine such sentences, including one
            # quoting 'apple' itself, every one answered with the whole file.
            # Plain `grep` means it, and grep's exit status is already declared an
            # answer, so a value nothing matches is reported as "nothing matched"
            # rather than refused -- the same distinction the negated form relies
            # on, and pinned from both sides by a test.
            if _ANOTHER_OPERATION.search(text):
                # The sentence also states a second operation -- "the SORTED lines
                # that contain 'apple'" -- and no single command does both.
                # Serving the filter alone would drop the sort and certify it,
                # which is the defect; so this refuses instead of half-serving.
                return None
            # A quoted value is the LITERAL text the sentence delimited, not a
            # regular expression: "contain" is literal language, and this module
            # already sends literal and exact text to `fgrep` for exactly that
            # reason.  Measured with `grep`: "lines that contain 'a*b'" answered
            # 'banana', because `a*b` is a regex that matches it, when no line
            # holds those three characters.
            needle = values[0]
            matcher = "fgrep"
            invert = False
        else:
            # A sentence that quoted nothing and did not say "empty" states no
            # pattern, and an invented pattern is executed.
            needle = None
            matcher = "grep"
            invert = False
        if needle is not None:
            # The QUOTED SPAN is masked, not the bare value: a blind replace eats
            # the same characters wherever they occur, including inside a path.
            operand_paths = extract_paths(
                _mask_a_quoted_value(sentence, needle) if not blank else str(sentence))
            if len(operand_paths) == 2 and _states_a_destination_for_the_result(
                    sentence, operand_paths[-1]):
                operand_paths = operand_paths[:1]
            if len(operand_paths) == 1:
                return [matcher, *(["-v"] if invert else []), str(needle),
                        str(operand_paths[0])]
            return None
    # A sentence that names a SET of files by pattern -- "all the .log files in
    # the directory D" -- states one path and a shape.  The shape is expanded
    # here from the sentence's own words and the command runs on exactly those
    # names: one level of the directory the sentence named, ordinary files only,
    # nothing looser than the ending it spelled out.
    # Engage only on the two things a set of files can be asked to do here.  A
    # sentence that merely says "all the files" -- "list all the files in the
    # directory D" -- is not a set operation and must fall through untouched, so
    # the intent is decided BEFORE any expansion and a non-match is not a
    # refusal of the whole sentence.
    _deleting = bool(re.search(r"\b(?:delet|remov)\w*\b", text)) and "rm" in known
    # A request to COUNT lines, not a mention of the word "line".  `_WC_LINES` is
    # the pattern for the unit -- it is what tells `wc` to count lines instead of
    # words -- and on its own it fires on any sentence that says "line" at all.
    # Measured: "Show the third line of every file in the directory D" set
    # `_counting`, engaged this expansion and returned `wc -l` over the set, so a
    # request for the third line of two files was answered with their line counts
    # -- 4, 2, 6 total -- and certified as an exact semantic answer.  The word
    # that says something is being COUNTED already exists in this module:
    # `_WC_QTY` is what every `wc` row in the table below already requires.
    _counting = (bool(re.search(_WC_LINES, text)) and "wc" in known
                 and bool(re.search(r"\b(?:%s)\b" % _WC_QTY, text)))
    # Reading the CONTENTS of a set of files is the third thing a set can be
    # asked to do.  Without it the sentence falls through to the table, where
    # `(?:list|show) ... directory` binds `ls` and answers with the file NAMES.
    # Measured: "Show the contents of every file in the directory D" returned
    # "one.txt\ntwo.txt" and was certified as exact.
    _reading = bool(re.search(r"\bcontents?\b", text)) and "cat" in known
    if ((_deleting or _counting or _reading) and _EVERY_FILE.search(text)
            and _DIRECTORY_REQUEST.search(text)):
        if _ONE_LEVEL_ONLY.search(text):
            # A deeper sweep than one level, which this expansion cannot do.
            # Falling through would be worse than refusing: the generic
            # single-operand rule sees one path -- the directory -- and binds
            # `rm <the directory>`, deleting the container of the set the
            # sentence described.  So the sentence owns this branch and gets no
            # route rather than a different command.
            return None
        masked = str(sentence)
        for value in _quoted_values(sentence):
            masked = _mask_a_quoted_value(masked, value)
        masked_paths = extract_paths(masked)
        for p in masked_paths:
            masked = re.sub(re.escape(str(p)), " ", masked, flags=re.IGNORECASE)
        suffix = _FILE_SUFFIX.search(masked.lower())
        # Quotes and dots only: the ending must be the one the sentence spelled
        # out, so ".log" selects `*.log` and not the looser `*log`.
        needle = ("*." + suffix.group(1)) if suffix else "*"
        if len(masked_paths) != 1:
            return None
        # The repository root comes from this module's own location, never from
        # the process cwd: a sentence names a path the way the rest of the system
        # does, relative to the root, and binding must not depend on where the
        # caller happened to be standing.
        root = pathlib.Path(__file__).resolve().parents[2]
        base = pathlib.Path(str(masked_paths[0]))
        directory = base if base.is_absolute() else root / base
        if not directory.is_dir():
            return None
        names = sorted(str(base / f) for f in os.listdir(directory)
                       if fnmatch.fnmatch(f, needle) and (directory / f).is_file())
        if not names:
            # Nothing matches.  No program can be asked to delete or count an
            # empty set, so the sentence gets no route rather than a no-op run
            # reported as the work it described.
            return None
        if _deleting:
            return ["rm", *names]
        if _counting:
            return ["wc", "-l", *names]
        if _reading:
            return ["cat", *names]
        return None

    for pattern, program in _PROSE_COMMAND_WITH_TWO_VALUES:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        values = _quoted_values(sentence)
        if len(values) != 2:
            # A substitution the sentence did not fully state.  Refuse; do not
            # invent the half it left out.
            return None
        before, after = values[0], values[1]
        if not before or any(ch in before or ch in after for ch in _SED_UNSAFE):
            return None
        operand_paths = extract_paths(
            str(sentence).replace(before, " ").replace(after, " "))
        if len(operand_paths) != 1:
            return None
        return [program, "-e", "s|%s|%s|g" % (before, after),
                str(operand_paths[0])]
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
        # "Search the files in the directory X for ..." is a search of a tree,
        # and `grep` on a directory without -r is an error, not an answer.
        extra = ["-r"] if _RECURSIVE_REQUEST.search(text) else []
        return [program, *extra, str(value), str(operand_paths[0])]
    # A sentence that asks for ONE line, for a COUNT of the lines holding some
    # text, or for the NUMBER of a line, names a part of the file rather than
    # the file.  Falling through to `cat` or `wc -l` then answers a different
    # question, and the answer is certified all the same, because a whole file
    # is a perfectly reproducible answer to a question nobody asked.  Measured:
    # "Show the third line of X" returned the whole file, and "How many lines in
    # X contain 'apple'" returned 4 -- the number of lines in the file -- when
    # two of them hold the text.
    _asked = _quoted_values(sentence)
    # Not when the sentence is about a TREE.  "Show which files in the directory
    # D contain 'apple'" names a directory and asks which files in it match, and
    # the recursive search rule owns that sentence; taking it here bound
    # `grep -n` over a directory, which is not a search of the tree at all.
    if (len(_asked) == 1 and "grep" in known and not _DIRECTORY_REQUEST.search(text)
            and re.search(r"\bcontain(?:s|ed|ing)?\b|\bmatch(?:es|ed|ing)?\b"
                          r"|\bappear(?:s|ed|ing)?\b", text)):
        _masked = re.sub(re.escape(_asked[0]), " ", sentence, flags=re.IGNORECASE)
        _operands = extract_paths(_masked)
        if len(_operands) == 1:
            if re.search(r"\b(?:%s)\b" % _WC_QTY, text):
                return ["grep", "-c", _asked[0], str(_operands[0])]
            if re.search(r"\b(?:which|what|where)\b|\bnumber\b", text):
                return ["grep", "-n", _asked[0], str(_operands[0])]
            # A yes-or-no question.  Its answer is the exit status, and the
            # acceptance layer already enumerates which codes are answers for
            # grep -- 0 and 1, and never 2, which means trouble.  Nothing new is
            # trusted here: the table, the declaration and the adapter's
            # handling of it all already existed; only the sentence was missing.
            if re.search(r"\b(?:does|did|is|are|whether)\b", text) or text.rstrip().endswith("?"):
                return ["grep", "-q", _asked[0], str(_operands[0])]
    # Singular "line", so "the first 3 lines" stays with `head`, which is the
    # command that means it, and only "the third line" comes here.
    _which = _prose_ordinal(sentence)
    if (_which is not None and "sed" in known
            and re.search(r"\bline\b", text) and not re.search(r"\blines\b", text)
            and re.search(r"\b(?:show|print|read|display)\b", text)):
        _operands = extract_paths(sentence)
        if len(_operands) == 1:
            return ["sed", "-n", _sed_print_script(str(_which), sentence),
                    str(_operands[0])]
    # A part of a file measured in a UNIT the sentence states.  The table below
    # builds every argv as `flags(_prose_count(text))`, and `_head_flags` and
    # `_tail_flags` both answer in LINES, because a line is the only unit the
    # flag callables were ever handed: the NUMBER is read out of the sentence and
    # the unit is thrown away.  Measured, all three certified as exact:
    #   "Show the first 10 bytes of X"       -> `head -n 10`, ten LINES
    #   "Show the first 5 characters of X"   -> `head -n 5`,  five LINES
    #   "Show lines 2 to 4 of X"             -> `cat`, the WHOLE file
    # Ten lines are a perfectly reproducible answer to a question nobody asked,
    # so reproducibility cannot catch this -- only the answer text can.
    #
    # Nothing new is trusted here.  The unit words already live in this module:
    # `_WC_CHARS` is exactly what tells `wc` to count bytes instead of lines, and
    # `head -c` / `tail -c` / `sed -n M,Np` / `tail -n +M` are the four ordinary
    # commands that mean these four questions.  Only the sentence rules were
    # missing -- the same shape as the yes-or-no fix.
    #
    # Digits are read from the PROSE, never from the whole sentence.  That is
    # `_prose_ordinal`'s own measured lesson: a digit inside a directory name
    # (".../tmp/clz1/...") outranked the digit the sentence stated and bound
    # `cut -f 1`.  And a quantity the sentence does not state unambiguously is
    # not guessed -- the rule declines and the sentence falls through unchanged.
    try:
        from canonical.runtime import goal_front_compiler_v1 as _front_unit
        _prose = _front_unit.prose_only(sentence)
    except Exception:  # noqa: BLE001 - no front compiler; decline rather than guess
        _prose = ""
    # The words are matched case-insensitively, the way every other rule in this
    # function matches them against `text`.  Measured without this: `prose_only`
    # keeps the sentence's own case, so "Show the first 10 bytes of X" -- capital
    # S -- failed a lowercase `\bshow\b` test and the whole block was skipped,
    # leaving all three wrong answers exactly as they were.  A block that never
    # runs is indistinguishable from a block that declines, and only the argv
    # shows which one happened.
    _prose = _prose.lower()
    _unit_paths = extract_paths(sentence)
    if (_prose and len(_unit_paths) == 1 and "head" in known
            and not _DIRECTORY_REQUEST.search(_prose)
            and re.search(r"\b(?:show|print|read|display)\b", _prose)):
        _operand = str(_unit_paths[0])
        _digits = re.findall(r"\b(\d+)\b", _prose)
        # Both ends stated: "lines 2 to 4".  Neither `head` nor `tail` can answer
        # this, because each of them fixes one end and leaves the other free.
        _span = re.search(
            r"\blines?\b[^\n]{0,12}?\b(\d+)\s*(?:to|through|thru|until|-)\s*(\d+)\b",
            _prose)
        if _span and len(_digits) == 2 and "sed" in known:
            return ["sed", "-n",
                    _sed_print_script("%s,%s" % (_span.group(1), _span.group(2)), sentence),
                    _operand]
        # Only the START is stated: "from line 3 to the end".  `tail -n +3` is
        # that question exactly.  Measured before this, the sentence bound
        # `tail -n 2` -- the last two lines -- which answered correctly on a
        # four-line fixture and returned `L9\nL10` for "from line 3 to the end"
        # of a ten-line file.  A rule that is right only on the fixture it was
        # measured against is a wrong rule.
        _from_line = re.search(r"\bfrom\s+line\s+(\d+)\b", _prose)
        if (_from_line and len(_digits) == 1 and "tail" in known
                and re.search(r"\b(?:end|bottom|rest)\b", _prose)):
            return ["tail", "-n", "+%s" % _from_line.group(1), _operand]
        # A quantity in BYTES or CHARACTERS, not in lines.  `_WC_QTY` is excluded
        # so "Count the characters in X" stays with `wc -c`, which is the command
        # that answers it.
        if (re.search(r"\b(?:%s)\b" % _WC_CHARS, _prose)
                and not re.search(r"\b(?:%s)\b" % _WC_QTY, _prose)
                and len(_digits) == 1):
            if re.search(r"\b(?:last|end)\b", _prose) and "tail" in known:
                return ["tail", "-c", _digits[0], _operand]
            if re.search(r"\b(?:first|beginning)\b", _prose):
                return ["head", "-c", _digits[0], _operand]
    # "Are the files A and B identical" asks a yes-or-no question about two
    # files.  `cmp -s` answers it with an exit status and prints nothing, and the
    # acceptance layer already treats 0 and 1 as answers for cmp -- 1 meaning
    # "they differ", which is an answer and not a failure.
    if "cmp" in known and re.search(
            r"\bidentical\b|\bthe same\b|\bno differences?\b|\bexactly alike\b", text):
        _operands = extract_paths(sentence)
        if len(_operands) == 2:
            return ["cmp", "-s", str(_operands[0]), str(_operands[1])]
    for pattern, program, flags, arity in _PROSE_COMMAND:
        if program not in known:
            continue
        if not re.search(pattern, text):
            continue
        operands = paths
        if arity < 0:
            # A negative arity means the program takes as many operands as the
            # sentence names, and every one of them has to be stated.  Only
            # `mkdir` uses it: creating a directory the sentence named is
            # harmless, while the same freedom on `rm` would delete a path the
            # sentence happened to mention.
            if not operands:
                return None
        # A read-only command can be asked to put its result somewhere: "write
        # the unique lines of A to the file B", "join A and B into C".  The
        # sentence then names one more path than the program takes as operands,
        # and the extra one is the DESTINATION -- not an operand, and not an
        # invention either, because the adapter writes the command's stdout to
        # `output_path`, which `bind` already fills with the last path in the
        # sentence.  Measured before this, every such sentence was refused on
        # arity: uniq wants one file and the sentence named two.
        #
        # The destination has to be SAID, not assumed.  Requiring the words that
        # introduce it is what keeps "Compare the files A and B" -- two operands,
        # no destination -- binding exactly as it did.
        if (len(paths) == arity + 1
                and _states_a_destination_for_the_result(sentence, paths[-1])):
            operands = paths[:arity]
        if arity >= 0:
            if len(operands) != arity:
                # The sentence did not state enough operands for the program it
                # asked for.  Refuse; do not repeat a path to make the numbers fit.
                return None
        paths = operands
        if program == "cut":
            column = _prose_ordinal(sentence)
            if column is None:
                # No column stated.  Defaulting to 1 would be inventing the
                # answer to the question the sentence actually asked.
                return None
            return [program, "-f", str(column), str(paths[0])]
        if program == "cp" and _DIRECTORY_REQUEST.search(text):
            return [program, "-r", str(paths[0]), str(paths[1])]
        if program == "ls" and _EVERY_FILE.search(text) and not _LISTING_REQUEST.search(text):
            # `ls` answers "what files are here", never "what is IN them".  Its
            # pattern is `(?:list|show) ... directory`, which matches a sentence
            # about the files in a directory just as readily as one about the
            # directory.  Measured: once `_counting` stopped claiming "Show lines
            # 2 to 4 of every file in the directory D", this row took it and
            # answered "one.txt\ntwo.txt" -- the NAMES -- and was certified as an
            # exact semantic answer.  Tightening one keyword match simply handed
            # the sentence to the next loose one, so the loose one is scoped too.
            # A sentence that really asks for a listing says so.
            return None
        _count = _prose_count(text)
        if (program in ("head", "tail") and _COUNT_RE.search(text) is None
                and re.search(r"\bline\b", text) and not re.search(r"\blines\b", text)):
            # "Show me the last LINE" names one line.  The default of two is
            # right for "show me the last lines" and wrong for the singular, and
            # measured as answering the last line of a four-line file with its
            # last two.  Only when no number was stated: a stated count stands.
            _count = 1
        argv = [program, *flags(_count), *paths]
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
    # A value the caller quoted is a VALUE, not a path -- but a search pattern
    # is very often shaped like a filename, and extract_paths cannot tell the
    # difference.  Measured: "Search the file a1.txt for the literal string
    # 'ap.le'" bound output_path to "ap.le", because the pattern was the LAST
    # path in the sentence and PATH_OUTPUT takes the last.  The adapter then
    # failed CLI_EXPECTED_OUTPUT_MISSING over a command whose argv was correct
    # and which ran fine -- the promise was about a file nobody named.  The
    # pattern 'zzzz' bound correctly, because with no dot it is not path-shaped,
    # which is what made this invisible: it only ever fired on a pattern that
    # looks like a file, and 'notes.md' is exactly such a pattern.
    #
    # This is the same masking _prose_argv already applies when it reads
    # operands, at the layer that fills the slots.  A fix that closes one path
    # and leaves its sibling open is not closed.
    _quoted = _quoted_value(goal)
    if _quoted and not _QUOTED_AS_A_PATH.search(str(goal or "")):
        # Still masked when the sentence quoted a PATTERN, which is the case that
        # made the defect above invisible.  Not masked when the sentence
        # introduced the quoted value as a file -- "the file 'my notes.txt'" --
        # because then the quoted value is the only operand the sentence named,
        # and removing it leaves the command with nothing to run on.
        paths = [p for p in paths if p != str(_quoted)]
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
                _declare_a_written_output(args, argv, goal)
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


def _declare_a_written_output(args: dict[str, Any], argv: Sequence[str],
                              sentence: str) -> None:
    """Tell the adapter to write the command's stdout to the declared output.

    `output_path` has always been a promise to CHECK, never a place to write --
    the adapter creates its parent directory and then asks whether it exists.  So
    a sentence that asks for a command's result to be put somewhere had no
    mechanism at all: "Write the unique lines of the file A to the file B"
    compiled, ran `uniq A`, and was then correctly refused with
    PROMISED_ARTIFACT_MISSING because nothing ever wrote B.  The refusal was
    honest and the request was perfectly ordinary.

    Three conditions, each of which is read rather than assumed:
      * the sentence INTRODUCES the last path as where the result goes, which is
        the same test that let the command bind one operand fewer;
      * the command is read-only, so its stdout IS the result and writing it
        changes nothing the sentence did not ask for;
      * the command does not consume its operand -- for `rm A` the bound output
        is the file being deleted, and writing stdout there would resurrect it.
    Anything else leaves the argument unset, so every route that worked before
    this runs byte for byte as it did.
    """
    if not argv:
        return
    program = str(argv[0]).rsplit("/", 1)[-1]
    try:
        from canonical.runtime import raw_goal_trace_acceptance_v1 as _accept
        read_only = program in _accept._READ_ONLY_COMMANDS
        consumes = program in _accept._CONSUMES_AN_OPERAND
    except Exception:  # noqa: BLE001 - no table, no declaration
        return
    if not read_only or consumes:
        return
    named = extract_paths(sentence)
    if not named:
        return
    dest = str(named[-1])
    if dest in {str(x) for x in argv[1:]}:
        # The bound output IS an operand.  For almost every program that means
        # the command is about to remove or replace the file -- which is what
        # _declare_a_consumed_output handles -- and writing stdout there would
        # resurrect it.  A transform is the one exception, and it is safe for a
        # concrete reason: the adapter captures stdout in full and only then
        # writes, so the read is already finished.
        try:
            transforms = _accept._IN_PLACE_TRANSFORMS
        except Exception:  # noqa: BLE001 - no table, no permission
            return
        if program in transforms:
            # Only a script that REWRITES may write over the file it read.
            # `sed -e s|a|b| A` transforms A and putting the result back is the
            # work the sentence asked for.  `sed -n 3p A` is a reader: measured,
            # treating it as a transform left A holding nothing but its third
            # line -- a request to be SHOWN something destroyed the file it
            # named.  The distinction is in the script, not in the program.
            #
            # But the script is not the WHOLE distinction, and saying so was
            # wrong.  `sed -e 's/.*/\U&/'` rewrites, so it passed this test --
            # and "Show the file X in upper case" bound it, wrote the upper-cased
            # text back over X, and was certified.  Measured: X went from
            # 'apple\nbanana\n' to 'APPLE\nBANANA\n' on a request to be SHOWN
            # something.  A rewriting script is necessary for a write-back and
            # not sufficient: the sentence has to have asked for the file to
            # change.  "Convert X to upper case" says so; "Show X in upper case"
            # says the opposite.  Nothing is written for a reading, and the run
            # is still accepted -- the upper-cased text is on stdout, which is
            # where a reading puts its answer.
            if (_READ_VERBS.search(str(sentence or "").lower())
                    or not any(re.match(r"^s[|/#]", str(part).lstrip()) for part in argv[1:])):
                return
            args["write_stdout_to_output"] = "true"
        return
    if _states_a_destination_for_the_result(sentence, dest):
        args["write_stdout_to_output"] = "true"


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
        if str(cid) in _PLAIN_PAYLOAD_WRITES and keeps_existing_content(goal):
            # Refuse BEFORE the adapter runs: this capability truncates the file
            # it is given, so checking afterwards would only report a deletion
            # that has already happened.
            return {"schema": SCHEMA, "pass": False, "goal": goal,
                    "status": "FAIL_CLOSED__WRITE_WOULD_DISCARD_CONTENT_THE_SENTENCE_PROMISED_TO_KEEP",
                    "failed_step": {"index": index, "capability_id": str(cid),
                                    "promise": "existing_content_kept"},
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
