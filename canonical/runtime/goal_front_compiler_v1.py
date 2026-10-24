"""One mouth for every bound capability: a front layer on the byte-pinned goal compiler.

Measured on 2026-10-15 (canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json)
the pinned compiler had four defects that this layer corrects WITHOUT editing a pinned byte:

1. Silent candidate fall-through: when the best-scoring tool cannot bind its inputs the pinned
   ``_compile_single_goal`` skips it (``except Exception: continue``) and runs the next scored
   candidate - frequently a zero-input catch-all that always reports success.
   Here: if the best-scoring candidate is not the one selected, this layer tries to bind the best
   candidate itself and otherwise FAILS CLOSED naming the unbound inputs.
2. A sentence-final period is absorbed into the last literal value (``"1."`` instead of ``1``).
   Here: one sentence-final period is removed before compilation; the original text is kept for
   the lossless raw contract.
3. Verb synonyms ("build ... and write it to") route to a VERIFIER instead of the creator.
   Here: when the goal names a future artifact and the selected tool has no output key, the best
   scoring candidate that can write that artifact is selected instead.
4. Zero-input tools (``terminal.kstar.root.assess.stdlib`` ...) are reachable from plain goals
   through generic keywords.  Here: tools without inputs are never routable from a plain goal.
5. The literal routes swallow the following sentences: "...: alpha 1. Then create Y ...: beta 2."
   compiles to ONE record whose value is "1. Then create Y ...".  Here: when a literal route
   captured a goal of several sentences, each sentence is compiled on its own and the controller
   actions are concatenated; every sentence must compile or the whole goal fails closed.

6. Input files bind only when the file NAME contains the input's stem (``archive_path`` needs a
   file called ``*archive*``), so "verify the archive canonical/x/bundle.tar.gz" cannot bind.
   Here: when the pinned binder fails for an input path, the single existing named file whose
   TYPE matches the stem (archive -> .tar.gz/.tgz/.zip, json -> .json, pdf -> .pdf ...) binds.

7. An output path binds by suffix over ALL named paths, so "read a.json and save it to b.json"
   is ambiguous to the pinned binder.  Here: an output that failed to bind takes the single
   named file that does not exist yet (and matches the key's type when the key has one).

8. Path components count as routing evidence (``.../live_solver_e2e/x.pdf`` makes "live" a
   match for a provenance tool).  Here: candidates are ranked on PROSE tokens only (paths and
   URLs removed); the surface/format constraints still see the full sentence.

9. ``pypi.provenance.audit_live_artifact`` declares the keyword ``pypi`` but the pinned surface
   rule rejects any tool without a pypi source when the sentence says "pypi" - the tool cannot
   be reached by its own keyword.  Here: a surface word that is one of the tool's OWN tokens
   (keywords, identity, provides) does not reject it.

10. The caller's own choice is discarded.  Candidates are ranked on PROSE tokens and paths are
   removed (defect 8), so a goal whose content IS a capability id collapses to its verbs and is
   absorbed by a generic candidate - measured: ``run <zero-input capability id>`` selected
   ``python.software.request.semantic_behavior.compile.v1`` for 217 of 294 receipt-backed
   capabilities and reported success.  Here: an id that appears verbatim in the goal selects
   that capability and nothing else (F15).  Naming is not guessing - it is the caller choosing -
   and composition is never stolen: a sentence that keeps asking for more still routes normally.

11. (F18) The npm/pypi/apt ecosystem surface rule read the HOST of a URL as an ecosystem claim:
   ``Fetch ... from https://pypi.org/pypi/requests/json ...`` rejected every generic fetch tool
   (including the knowledge fetcher whose own keywords score 29 on that prose), leaving the
   sentence to a catch-all.  Here: surface claims are evaluated on prose only; a URL is a value
   being fetched, while the words of the sentence keep the rule.

12. (F20) ``json_path`` is a selector INSIDE the fetched payload (a list of key/index parts,
   declared in proposal_bindings as the literal []), but the ``*_path`` file binder bound a
   real ``*.json`` file to it and the runtime failed closed with KNOWLEDGE_JSON_PATH_INVALID.
   Here: payload selectors bind from an explicit bracket list ("[]", "["info"]", "["urls", 0]")
   or default to the declared identity [] exactly like the empty key/value mapping; anything
   else still fails closed.

13. (F21/F22) Two natural sentences could not reach tools that score them: chart tick
   observations are (pixel, value) PAIRS which the flat list grammar could never express, so
   axis calibration through a sentence was impossible; and a same-score tie
   (``Fetch ... https://pypi.org/...`` scores 29 for both http.json.fetch_from_state and
   knowledge.json.fetch.external) resolved to whichever sorted first - and failed closed on
   its unstated inputs even though the sibling was bindable.  Here: pairs state as
    ``[[80, 0], [233, 1], [400, 2]]``, and a same-score tier is disposed by typed admission in
    rank order (first tied candidate whose inputs the sentence states wins); a lower-score tier
    is still never silently entered.

14. (F23) Two input files of the SAME type could never be bound together: the pinned binder
    refuses a key whose stem matches more than one named file, and the type fallback refuses it
    too, so a sentence naming a live metadata document AND a selection record could not reach the
    capability that consumes both (``metadata_path:2_type_compatible_existing_files_named``).
    Here the SENTENCE decides: the role word that introduces a path ("with selection <file>")
    claims that file for the key whose stem is that role, and a file left with exactly one
    unclaimed key is bound by elimination.  Every binding is stated by the sentence or forced by
    the only remaining assignment; anything else still fails closed.

15. (F24) The lexical score is a hint; the words of the request are the decision.  A candidate
    whose DECLARED input the sentence never stated was never what was asked - it is skipped and
    the walk continues down the ranked pool - while a candidate the sentence states AMBIGUOUSLY
    keeps the request open and the request fails closed.  Measured: ``Collect the external
    knowledge JSON document <url> with json path [] as authoritative true and store it in <out>``
    scores 25 for a DOCX creator (the words "json" and "document" are in its very name) against
    23 for the knowledge fetcher, and the DOCX creator needs a JSON FILE the sentence never
    states - so the request failed closed on a sentence that states the knowledge fetcher's whole
    contract.  A capability that can serve ANY sentence (it takes the whole request and writes
    an artifact) is never the decision: it binds every sentence, so it is the fall-through F1
    exists to stop.

16. (F25) A URL, a path and a quoted literal are all VALUES the request carries, and none of
    them says what the task IS.  F8 removed the first two from the ranking; here the third is
    removed too, because a value's own words were being read as the task's words.  Measured:
    ``Apply the jq filter "[.items[].v] | add"`` scored the SA-CCR credit add-on capability
    above the jq capability (the word "add" lives inside the FILTER), and ``with jq filter
    ".record.tag"`` scored a DOCX creator above jq (the word "record" lives inside the filter).
    Both sentences ask for jq; both were answered by something else.

17. (F26) A multi-step request is ONE graph, and the artifact an earlier step writes is part
    of the pool a later step's input may bind from.  Measured: ``Fetch ... and save it to
    <fetched>. Then audit ... on <fetched> with selection <sel> and save the report to <rep>``
    was not planned as a DAG at all - the consumer bound the selection record (it was the only
    file on disk), the producer's artifact was claimed as the consumer's OUTPUT, and the
    request silently dropped a step.  An OUTPUT is a new artifact and never claims an earlier
    step's; and the earlier step's artifact is what the sentence points at.

It also binds the 33 registry inputs the pinned binder cannot (``path``, ``jq_filter``,
``expression``, ``x_value``, ``test_paths`` ...) from an explicit typed grammar:
``<key words> <quoted string | number | path | list | key=value pairs>``.  Inputs are never
guessed: a goal that does not state an input fails closed with GOAL_INPUT_BINDING_REQUIRED.
"""
from __future__ import annotations

import json
import pathlib
import re
import shlex
from typing import Any, Mapping

from canonical.runtime import capability_planner
from canonical.runtime import goal_compiler as gc

SCHEMA = "PROJECT_BRAIN_GOAL_FRONT_COMPILER_V1"
GoalCompilationFailure = gc.GoalCompilationFailure
# F11: a multi-step sentence is compiled into one capability_planner problem and executed as an
# autonomous DAG.  The compiled shape below is what the live admission entry executes.
DAG_SCHEMA = "PROJECT_BRAIN_CAPABILITY_DAG_V1"
DAG_MODE = "FRONT_CAPABILITY_DAG_PLANNED"
DAG_FINISH_SUMMARY = "CAPABILITY_DAG_COMPLETE"

_QUOTE_OPEN = "\"'\u201c\u2018`"
_QUOTE_CLOSE = "\"'\u201d\u2019`"
_NUM = r"-?\d+(?:\.\d+)?"
# A quoted literal: the VALUE the request carries (F25).  Its words are not the task's words.
_QUOTED_LITERAL = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'|“[^”\n]*”|‘[^’\n]*’")

# natural aliases for registry input keys (key -> phrases that may name it in a sentence)
_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    # An output has no type of its own, so its role can only come from the sentence.
    "output_path": ("result to", "results to", "save to", "save it to", "write to",
                    "output to", "store to", "report to"),
    "output_file": ("result to", "results to", "save to", "save it to", "write to",
                    "output to", "store to", "report to"),
    "jq_filter": ("jq filter", "jq_filter", "jq expression", "filter"),
    "expression": ("expression", "formula"),
    "variables": ("variables", "with variables", "where"),
    "x_value": ("x value", "x_value", "x =", "x=", "at x"),
    "y_value": ("y value", "y_value", "y =", "y=", "at y"),
    "x_ticks": ("x ticks", "x_ticks", "x axis ticks"),
    "y_ticks": ("y ticks", "y_ticks", "y axis ticks"),
    "label": ("label", "curve", "series", "legend entry"),
    "prompt": ("prompt", "question"),
    "pattern": ("pattern", "test pattern", "file pattern"),
    "test_argv": ("test argv", "test_argv", "test command", "command"),
    "objective": ("objective", "claim"),
    "spec": ("spec", "specification", "relation spec"),
    "product": ("product",),
    "major": ("major version", "major"),
    "version_field": ("version field", "version_field"),
    "field_name": ("field name", "field_name", "field"),
    "expected_status": ("expected status", "expected_status", "status"),
    "url_key": ("url key", "url_key", "state key"),
    "authoritative": ("authoritative",),
    "max_age_s": ("max age seconds", "max age", "max_age_s", "maximum age"),
    # F23: the ROLE words that may introduce a path in a sentence (see ``_role_phrases``).
    "metadata_path": ("metadata", "live metadata"),
    "selection_path": ("selection", "selected", "selection record"),
    "assessment_path": ("assessment", "assessed", "assessment record"),
    "result_path": ("result", "claim", "release claim"),
    "report_path": ("report",),
    "source_json_path": ("source json", "state json"),
}
_PATH_LIST_KEYS = {"test_paths", "source_paths", "evidence_paths"}
_PATH_DIR_KEYS = {"source_root"}
_PATH_FILE_KEYS = {"path"}
# F20: ``json_path`` is a SELECTOR INSIDE the fetched JSON payload (a list of key/index parts,
# declared in the registry's own proposal_bindings as the literal []), never a file on disk.
# The pinned ``*_path`` file binder would otherwise bind an existing ``*.json`` file to it and
# the runtime fails closed with KNOWLEDGE_JSON_PATH_INVALID because the string is not a list.
# The routing is DECLARATION-DRIVEN, per entry: jq's ``json_path`` carries no literal-list
# declaration and keeps the file binder.
_PAYLOAD_SELECTOR_KEYS = {"json_path"}


def _declared_literal_selector_keys(entry: Mapping[str, Any]) -> set[str]:
    """Keys of this entry that the registry itself declares as literal LIST values (F20)."""
    bindings = entry.get("proposal_bindings") if isinstance(entry, Mapping) else None
    if not isinstance(bindings, Mapping):
        return set()
    return {
        key for key, binding in bindings.items()
        if isinstance(binding, Mapping) and binding.get("type") == "literal"
        and isinstance(binding.get("value"), list) and str(key).endswith("_path")
    }
_NUMERIC_KEYS = {"x_value", "y_value", "major", "max_age_s"}
_LIST_NUMERIC_KEYS = {"x_ticks", "y_ticks"}
_BOOL_KEYS = {"authoritative"}
_ARGV_KEYS = {"test_argv"}
_JSON_OR_TEXT_KEYS = {"spec", "objective"}
_KV_KEYS = {"variables"}
# The keys that ASK for a version, so a bare version token is their value and not a name
# fragment.  Measured over the live registry: 55 distinct input keys, and exactly one of
# them denotes a version - `version_field` on `web.release.verify.independent_http`.
_VERSION_KEYS = {"version_field", "version"}


def normalize_goal(goal: str) -> str:
    """Remove exactly one sentence-final period (defect 2). Everything else is untouched."""
    text = str(goal or "").strip()
    if text.endswith(".") and not text.endswith("..") and len(text) > 1:
        return text[:-1].rstrip()
    return text


def input_keys(entry: Mapping[str, Any]) -> list[str]:
    return sorted(gc._placeholders((entry or {}).get("action_template") or {}))


def is_plain_goal_routable(entry: Mapping[str, Any]) -> bool:
    """Defect 4: a tool that takes no input cannot be what a sentence asked for."""
    template = (entry or {}).get("action_template")
    return isinstance(template, dict) and bool(gc._placeholders(template))


def _named_receipt_projection(text: str, admissible: Mapping[str, Mapping[str, Any]],
                              selected: str | None, names=None) -> str | None:
    """A receipt-projected capability the sentence NAMES but the scorer cannot see.

    The pinned scorer skips anything whose status is not VERIFIED_BOUND_CAPABILITY,
    so a receipt projection is structurally invisible to it -- that is the whole
    reason F17 exists.  But F17 was only ever consulted when the pinned path had
    FAILED, so a sentence that named a receipt projection outright still lost to
    whatever bound capability the scorer happened to rank first.  Measured:
    "Run the bytes active query task generator." selected
    python.task.acceptance.measured.objective.v1 while naming
    bytes_active_query_task_generator_v1 and binding nothing of its contract.

    Scoped exactly as F17 is: receipt projections only.  The trigger is new, the
    authority is not.
    """
    matches = []
    for cid, entry in (admissible or {}).items():
        if cid == selected or not isinstance(entry, Mapping):
            continue
        if entry.get("capability_source") != "receipt_projection":
            continue
        if (names or request_names_capability_id)(text, cid):
            matches.append(cid)
    if not matches:
        return None
    # The MOST SPECIFIC name stated, not the first one found.  A shorter name can
    # be a subsequence of a longer one: "Run the bytes characteristic active query
    # task generator v10." states the whole of bytes_active_query_task_generator_v1
    # as well, because "characteristic" is only an extra word in the middle, so
    # iteration order picked the less specific sibling and 3 of 13 still misrouted.
    # A caller who says the longer name means the longer name.
    def _specificity(cid: str) -> tuple:
        stem = str(cid).rsplit("/", 1)[-1].split(".py")[0]
        words = [w for w in re.split(r"[_\s]+", stem) if len(w) > 1]
        return (len(words), len(stem))
    return max(matches, key=_specificity)


ROOT_FOR_NAMING = pathlib.Path(__file__).resolve().parents[2]

# A token carrying an underscore, a slash, or an INTERNAL dot is an identifier, not
# a word the caller wrote out: "classify_support" and "canonical/runtime/x.py" go,
# while "v1", "generator" and "candidate" stay.  The dot has to be internal -- the
# first version of this matched any token containing a dot, so the sentence-final
# period turned the LAST WORD OF EVERY GOAL into an "identifier" and deleted it:
# "Run the bytes active query task generator." lost "generator", "... v6
# candidate." lost "candidate", and "... audit v1." lost the version itself, which
# is why a v1 sentence matched a v2 capability.
_IDENTIFIER_TOKEN_RE = re.compile(r"\S*(?:_|/|\.\S)\S*")


def _prose_of(text: str) -> str:
    """The caller's own words: no repository paths, no identifiers.

    Measured: judging a name against the raw sentence let a PATH do the naming.
    "Call the function classify_support in canonical/runtime/bounded_claim_support.py
    with the payload ... and save the result to ..." was read as naming SIXTEEN
    receipt projections, because bounded_, support, claim and selected_ all occur
    inside repository paths -- and the shared predicate tokenises, so the identifier
    "classify_support" alone contributed "support" and named nine more.
    """
    prose = str(text or "")
    for raw, _resolved in gc._repo_paths(prose, ROOT_FOR_NAMING):
        for spelling in {raw, str(raw).lstrip("/"), str(_resolved)}:
            if spelling:
                prose = prose.replace(spelling, " ")
    return _IDENTIFIER_TOKEN_RE.sub(" ", prose)


_NAME_VERSION_RE = re.compile(r"^v\d+$", re.IGNORECASE)
_NAME_STOPWORDS = frozenset({"run", "call", "the", "a", "an", "and", "with", "of",
                             "for", "to", "in", "on", "that", "it", "by"})


def request_states_the_capability_name(text: str, cid: str) -> bool:
    """True only when the caller wrote the capability's WHOLE name, in order.

    Refusing a request is a fail-closed act, so one word of a name is enough
    evidence for it -- that is what request_names_capability is documented to do.
    TAKING OVER a route that already bound is the opposite kind of act and needs
    far stronger evidence.  Measured with the one-word rule: "Audit the python
    source file ... with an AST parser ..." read as naming 15 receipt projections
    and "Repair the python source ... so that the test ... passes" read as naming
    8, on the strength of a single shared word each.  Admitting the first of those
    displaced real bound capabilities and broke 4 tests in
    test_live_brain_route_admission_v1.py.

    The whole name, in order, is the evidence a caller actually gives when they mean
    a specific capability, and it is exactly what the wave 7 generator produces:
    "Run the bytes active query task generator." A trailing version token is
    optional, because prose drops it and the retrieval path separates version
    siblings only when the request states the version.
    """
    try:
        stem = str(cid or "").rsplit("/", 1)[-1].split(".py")[0]
        if not stem or stem == cid:
            return False
        all_words = [w.lower() for w in re.split(r"[_\s]+", stem) if len(w) > 1]
        # A version token can sit ANYWHERE in the name, not only at the end:
        # terminal_frontier_factorizer_v6_candidate and
        # current_terminal_authority_v3_k6_v4_verifier both carry one mid-name.
        # Reading only the trailing word rejected the right capability outright and
        # handed the route to a sibling.
        stem_versions = [w for w in all_words if _NAME_VERSION_RE.match(w)]
        words = [w for w in all_words if not _NAME_VERSION_RE.match(w)]
        words = [w for w in words if w not in _NAME_STOPWORDS]
        if not words:
            return False
        prose = _prose_of(text)
        # A version the caller STATES must match; one they omit is left open.  The
        # trailing token is dropped from the word list so that prose without a
        # version still names the capability, but dropping it silently made
        # siblings indistinguishable: "Run the composition cross step no bypass
        # audit v2." matched _v1 and _v2 identically, both tie-break on the same
        # word count and the same stem length, and iteration order picked _v1.
        # Measured across all 294 path-style receipt-backed capabilities, 24 of the
        # 294 misrouted and every one of them was a version sibling.  The harness
        # generator documents this rule for the retrieval path: "the version is
        # part of the name, because the retrieval path separates a capability's
        # version siblings only when the request states the version."
        stated = re.findall(r"\bv(\d+)\b", prose, re.IGNORECASE)
        if stated and sorted("v" + x for x in stated) != sorted(stem_versions):
            return False
        last = -1
        for w in words:
            m = re.search(r"\b" + re.escape(w) + r"s?\b", prose, re.IGNORECASE)
            if m is None or m.start() < last:
                return False
            last = m.end()
        return True
    except Exception:  # noqa: BLE001 - naming is evidence, never a reason to raise
        return False


def request_names_capability_id(text: str, cid: str) -> bool:
    """Does the sentence name this capability, judging by its module name?

    F29 already answers this for a module name; a capability id such as
    ``canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1`` carries
    that name as the stem before ``.py``.  Reusing the existing predicate rather
    than writing a second notion of "named" is the point: one rule, one meaning.
    """
    try:
        from canonical.runtime import capability_selection_retrieval_v1 as _sel
        stem = str(cid or "").rsplit("/", 1)[-1].split(".py")[0]
        if not stem or stem == cid:
            # A dotted capability id is not a module name; judging it as one would
            # match on ordinary English words inside the id.
            return False
        # A NAME has to appear in the PROSE.  Judged against the raw sentence, a
        # path does the naming instead: "Call the function classify_support in
        # canonical/runtime/bounded_claim_support.py with the payload ... and save
        # the result to ..." was measured to "name" SIXTEEN different receipt
        # projections, because bounded_, support, claim and selected_ all occur
        # inside repository paths and ordinary words.  That is what made admitting
        # the named entry directly break 7 tests in
        # test_live_brain_route_admission_v1.py -- the hook fired on a candidate the
        # sentence never mentioned.  Removing the path spans first leaves only the
        # words the caller actually wrote.
        prose = text
        for raw, _resolved in gc._repo_paths(text, ROOT_FOR_NAMING):
            for spelling in {raw, str(raw).lstrip("/"), str(_resolved)}:
                if spelling:
                    prose = prose.replace(spelling, " ")
        # And an IDENTIFIER is not prose either.  The shared predicate tokenises,
        # so "classify_support" contributes the word "support" -- which on its own
        # measured as naming nine different capabilities ending in _support, after
        # the paths were already stripped.  A caller writes a capability's name in
        # words; a token with an underscore, a dot or a slash in it is a path, a
        # function or a field, and none of those is the caller naming a capability.
        prose = _IDENTIFIER_TOKEN_RE.sub(" ", prose)
        return bool(_sel.request_names_capability(prose, stem))
    except Exception:  # noqa: BLE001 - naming is evidence, never a reason to raise
        return False


def routable_registry(admissible: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {cid: entry for cid, entry in admissible.items() if isinstance(entry, Mapping) and is_plain_goal_routable(entry)}


def blocked_zero_input_capabilities(admissible: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return sorted(cid for cid, entry in admissible.items() if isinstance(entry, Mapping) and not is_plain_goal_routable(entry))


# ------------------------------------------------------------------------- F15: naming as choosing

_IDENTITY_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/")
_COMPOSITION_MARKERS = (" and ", " then ", " also ", " plus ", " after ", " before ", ",", ";", "\n")
_MAX_NAMING_WORDS = 4
_EXPLICIT_NAME_SCORE = 10 ** 6
_CAPABILITY_ID_SHAPE = re.compile(r"[A-Za-z0-9_./-]+\.py\.auto\.v1")


def explicitly_named_capabilities(goal: str, admissible: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Every capability whose id appears verbatim in ``goal``, on identifier boundaries.

    ``.`` is deliberately NOT an identity character: ids end in ``.v1``, so a sentence-final
    period must not stop an id from being recognised, while ``.../a_v1.py.auto.v1x`` still is
    a different identifier and does not match.
    """
    text = str(goal or "")
    hits: list[str] = []
    for cid in admissible:
        idx = text.find(cid)
        while idx != -1:
            end = idx + len(cid)
            before = text[idx - 1] if idx else ""
            after = text[end] if end < len(text) else ""
            if before not in _IDENTITY_CHARS and after not in _IDENTITY_CHARS:
                hits.append(cid)
                break
            idx = text.find(cid, idx + 1)
    return sorted(set(hits))


def capability_id_shaped_tokens(goal: str) -> list[str]:
    """Tokens in the goal that have the shape of a receipt-backed capability identity.

    Measured: a goal naming a capability was previously bound as an *output artifact* - the id
    handed to a generic candidate as ``output_path`` - which then reported
    ``output_verified: true`` by writing a file at the capability's own id path.  224 of 294
    naming goals "succeeded" that way.  An id-shaped token is an identity, never an artifact.
    """
    return sorted(set(_CAPABILITY_ID_SHAPE.findall(str(goal or ""))))


def naming_is_the_whole_request(goal: str, cid: str) -> bool:
    """Defect 10: a goal that only names ``cid`` is the caller choosing it, not an input to guess.

    Composition is never stolen: a second clause, a continuation, or more than a naming phrase
    leaves the decision to the normal machinery.  A named capability is also where its own
    verdict is written, so a sentence that says nothing but the id is read as naming the
    capability; routing never becomes success authority either way - the raw goal keeps its
    acceptance obligations ("receipts still required") until they are met by evidence.
    """
    rest = str(goal or "").replace(cid, " ").lower()
    if any(marker in rest for marker in _COMPOSITION_MARKERS):
        return False
    return len([w for w in re.split(r"[^0-9a-z]+", rest) if w]) <= _MAX_NAMING_WORDS


# ----------------------------------------------------------------------------- typed grammar

def _alias_regex(key: str) -> str:
    phrases = list(_KEY_ALIASES.get(key, ())) + [key, key.replace("_", " ")]
    phrases = sorted(set(phrases), key=len, reverse=True)
    return "(?:" + "|".join(re.escape(p) for p in phrases) + ")"


def _after_key(goal: str, key: str) -> list[str]:
    """Every text tail following '<key words>' plus optional '=', ':', 'of', 'is' (all aliases, overlapping)."""
    phrases = sorted(set(list(_KEY_ALIASES.get(key, ())) + [key, key.replace("_", " ")]), key=len, reverse=True)
    tails: list[str] = []
    for phrase in phrases:
        pattern = re.compile(r"(?i)\b" + re.escape(phrase) + r"\s*(?:=|:|\bof\b|\bis\b)?\s*")
        tails.extend(goal[m.end():] for m in pattern.finditer(goal))
    return tails


def _quoted(text: str) -> str | None:
    m = re.match(r"\s*([" + _QUOTE_OPEN + r"])(.*?)([" + _QUOTE_CLOSE + r"])", text, re.S)
    return m.group(2) if m else None


def _number(text: str):
    m = re.match(r"\s*(" + _NUM + r")\b", text)
    if not m:
        return None
    raw = m.group(1)
    return float(raw) if "." in raw else int(raw)


def _number_list(text: str) -> list[float] | None:
    m = re.match(r"\s*\[?\s*(" + _NUM + r"(?:\s*,\s*" + _NUM + r")*)\s*\]?", text)
    if not m:
        return None
    return [float(x) if "." in x else int(x) for x in re.split(r"\s*,\s*", m.group(1))]


def _pair_list(text: str) -> list[list[float]] | None:
    """F21: ``[[pixel, value], ...]`` - the tick-observation pairs ``calibrate_axis`` consumes.

    The flat numeric list grammar could never express them, so axis calibration through a
    sentence was impossible: every chart reader received bare values, crashed the unpack, and
    reported AXIS_TICKS_INSUFFICIENT (the documented "compound goal grammar pending" gap).
    """
    m = re.match(
        r"\s*\[\s*((?:\[\s*" + _NUM + r"\s*,\s*" + _NUM + r"\s*\]\s*,?\s*)+)\]",
        text,
    )
    if not m:
        return None
    pairs = re.findall(r"\[\s*(" + _NUM + r")\s*,\s*(" + _NUM + r")\s*\]", m.group(1))
    if not pairs:
        return None
    return [[float(a) if "." in a else int(a), float(b) if "." in b else int(b)] for a, b in pairs]


def _kv_pairs(text: str) -> dict[str, float] | None:
    m = re.match(r"\s*((?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*" + _NUM + r"\s*(?:,|and|\s)?\s*)+)", text)
    if not m:
        return None
    out: dict[str, float] = {}
    for name, value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(" + _NUM + ")", m.group(1)):
        out[name] = float(value) if "." in value else int(value)
    return out or None


def bind_typed_key(goal: str, key: str, root: pathlib.Path):
    """Bind one input key the pinned binder cannot. Raises GoalCompilationFailure when absent."""
    paths = gc._repo_paths(goal, root)
    if key in _PATH_FILE_KEYS:
        files = [raw for raw, p in paths if p.is_file()]
        if len(files) == 1:
            return files[0]
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(files)) + "_existing_files_named")
    if key in _PATH_DIR_KEYS:
        dirs = [raw for raw, p in paths if p.is_dir()]
        if len(dirs) == 1:
            return dirs[0]
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(dirs)) + "_existing_directories_named")
    if key in _PATH_LIST_KEYS:
        files = [raw for raw, p in paths if p.is_file()]
        if key == "test_paths":
            chosen = [raw for raw in files if re.search(r"(^|/)(test_[^/]*|[^/]*_test)\.py$", raw) or "/tests/" in raw]
        elif key == "source_paths":
            chosen = [raw for raw in files if raw.endswith(".py") and not re.search(r"(^|/)(test_[^/]*|[^/]*_test)\.py$", raw)]
        else:
            chosen = files
        if chosen:
            return chosen
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":no_matching_existing_files_named")
    tails = _after_key(goal, key)
    if not tails:
        if key in _KV_KEYS:
            # No bindings were stated. An empty mapping is the identity element for a
            # key/value input, not a guess: the capability that owns the semantics still
            # fails closed on any symbol it cannot resolve (the sympy adapter raises
            # NUMERIC_EXPRESSION_VARIABLE_UNBOUND), so this only lets an expression that
            # needs no bindings through instead of rejecting it at compile time.
            return {}
        if key in _PAYLOAD_SELECTOR_KEYS:
            # F20: [] is the declared identity selector (the registry's own proposal_bindings
            # carry the literal []): select the whole payload.  The capability that owns the
            # semantics still fails closed on any selector it cannot navigate
            # (KNOWLEDGE_JSON_PATH_NOT_FOUND), so nothing is guessed here.
            return []
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":not_stated")
    # quoted values win over bare tokens so an alias inside a quoted value ("Curve A") cannot steal it
    for strict in (True, False):
        for tail in tails:
            value = _parse_typed_value(key, tail, quoted_only=strict)
            if value is None:
                continue
            if value == [] or value == {}:
                # An empty parse is "nothing matched" for every key EXCEPT the keys whose
                # stated value legitimately IS the empty collection (F20 json_path "[]").
                if value == [] and key in _PAYLOAD_SELECTOR_KEYS:
                    return []
                continue
            return value
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":value_not_parseable")


# A bare version token - "v1", "v2", "v10" - is a NAME fragment, not a stated value.
#
# Measured: "Run the p3 binary decision grounded expression v1." bound the capability's
# `expression` input to the string "v1", so the request for a capability NAMED
# `p3_binary_decision_grounded_expression_v1` was served by `math.numeric_expression.sympy`
# with the expression "v1" - a number, not an expression.  The words "expression" and "v1"
# are how the request NAMES the capability; neither is a value the caller supplied.  This is
# the same discipline as F25 (a quoted literal's words are not the task's words) applied to
# the inventory's own naming convention.
#
# The rule is narrow on purpose: it applies to a BARE token only.  A quoted value is the
# caller stating it, and a key that denotes a version (`version_field`) is asking for one.
_VERSION_FRAGMENT = re.compile(r"^v\d+$")


def _parse_typed_value(key: str, tail: str, quoted_only: bool = False):
    if key in _NUMERIC_KEYS:
        return _number(tail)
    if key in _LIST_NUMERIC_KEYS:
        # F21: tick observations may be stated as pairs ("[[80, 0], [233, 1], [400, 2]]",
        # the (pixel, value) form calibrate_axis consumes) or as the original flat list.
        return _pair_list(tail) if _pair_list(tail) is not None else _number_list(tail)
    if key in _PAYLOAD_SELECTOR_KEYS:
        # F20: a JSON bracket list of key/index parts ("[]", "[\"info\"]", "[\"urls\", 0]").
        # Anything else fails closed: the selector's semantics belong to the capability.
        m = re.match(r"\s*(\[[^\]]*\])", tail)
        if m:
            try:
                value = json.loads(m.group(1))
            except ValueError:
                return None
            if isinstance(value, list) and all(isinstance(p, (str, int)) for p in value):
                return value
        return None
    if key in _BOOL_KEYS:
        m = re.match(r"\s*(true|false|yes|no)\b", tail, re.I)
        return (m.group(1).lower() in ("true", "yes")) if m else None
    if key in _KV_KEYS:
        return _kv_pairs(tail)
    if key in _ARGV_KEYS:
        q = _quoted(tail)
        return shlex.split(q) if q else None
    if key in _JSON_OR_TEXT_KEYS:
        q = _quoted(tail)
        if q is None:
            return None
        try:
            return json.loads(q)
        except ValueError:
            return q
    value = _quoted(tail)
    if value is None and not quoted_only:
        m = re.match(r"\s*([A-Za-z0-9_.:/-]+)", tail)
        value = m.group(1) if m else None
        # a bare version token names a capability; it is not a value the caller stated
        if value is not None and _VERSION_FRAGMENT.match(value) and key not in _VERSION_KEYS:
            return None
    return value


_STEM_SUFFIXES: dict[str, set[str]] = {
    "archive": {".gz", ".tgz", ".tar", ".zip"}, "tar": {".gz", ".tgz", ".tar"}, "zip": {".zip"},
    "json": {".json"}, "records": {".json"}, "manifest": {".json"}, "spec": {".json"}, "config": {".json", ".yaml", ".yml", ".toml"},
    "pdf": {".pdf"}, "markdown": {".md", ".markdown"}, "md": {".md"}, "docx": {".docx"}, "xlsx": {".xlsx"}, "spreadsheet": {".xlsx"},
    "sqlite": {".sqlite", ".db", ".sqlite3"}, "database": {".sqlite", ".db", ".sqlite3"}, "yaml": {".yaml", ".yml"}, "csv": {".csv"},
    "html": {".html", ".htm"}, "image": {".png", ".jpg", ".jpeg", ".webp"}, "png": {".png"}, "screenshot": {".png", ".jpg", ".jpeg"},
    "text": {".txt", ".md"}, "source": {".py"}, "python": {".py"}, "test": {".py"},
}
_OUTPUT_STEMS = {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}

# Past this many candidates the set is ambiguous whatever it contains, so the
# walk stops. Chosen so hashing them all stays cheap while still covering the
# realistic case of a directory holding a few copies of one input.
_SCAN_CANDIDATE_CAP = 8


def _is_output_key(key: str, entry: Mapping[str, Any] | None = None) -> bool:
    if entry is not None and isinstance(entry, Mapping):
        pb = entry.get("proposal_bindings")
        if isinstance(pb, Mapping) and key in pb and pb[key].get("type") == "effect_result":
            return False
    return key.startswith("output_") or key.split("_")[0] in _OUTPUT_STEMS


def _excluded(produced_paths, taken) -> set[str]:
    """The paths a fallback binder may not use: earlier steps' artifacts and claimed files."""
    skip = {str(x) for x in (produced_paths or []) if isinstance(x, str) and x}
    skip |= {str(x) for x in (taken or []) if isinstance(x, str) and x}
    return skip


def _interchangeable(cands, root: pathlib.Path) -> bool:
    """True when every candidate is byte-identical, so the choice cannot matter.

    Delegates the judgement to semantic_ambiguity_control_v1, which already
    implements the exact rule -- surviving interpretations that share a
    terminal signature are terminally equivalent and need no disambiguation.
    Two copies of the same file are the same input; refusing to pick between
    them is not rigour, it is a refusal with no reason behind it.
    """
    import hashlib

    try:
        from canonical.runtime import semantic_ambiguity_control_v1 as SA
    except Exception:
        return False
    digests = []
    for rel in cands:
        p = root / rel
        try:
            digests.append(hashlib.sha256(p.read_bytes()).hexdigest())
        except OSError:
            return False
    worlds = [
        {"world_id": rel, "terminal_signature_complete": True,
         "terminal_signature": {"sha256": d}}
        for rel, d in zip(cands, digests)
    ]
    verdict = SA.decide({
        "ambiguity_owner": "EXTERNAL_WORLD",
        "hypothesis_set_complete": True,
        "worlds": worlds,
        "observations": [],
    })
    return verdict.get("status") == "PASS__AMBIGUITY_TERMINALLY_IRRELEVANT"


def _scan_root_by_type(wanted, root: pathlib.Path, skip) -> list[str]:
    """Files in the working directory whose type fits the slot.

    Collects up to _SCAN_CANDIDATE_CAP candidates and stops: past that the set
    is ambiguous whatever it contains, and walking 14k more paths to confirm it
    buys nothing. `.git`, `node_modules`, `__pycache__` and `.venv` are pruned
    because none is where a user's input file lives and all are large enough to
    dominate the walk.
    """
    pruned = {".git", "node_modules", "__pycache__", ".venv"}
    out: list[str] = []
    stack = [pathlib.Path(root)]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            name = p.name
            try:
                if p.is_dir():
                    if name not in pruned:
                        stack.append(p)
                    continue
                if not p.is_file():
                    continue
            except OSError:
                continue
            rel = p.relative_to(root).as_posix()
            if rel in skip:
                continue
            if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted:
                out.append(rel)
                if len(out) > _SCAN_CANDIDATE_CAP:
                    return out
    return out


def _bind_path_by_type(goal: str, key: str, root: pathlib.Path, exclude=None):
    """F6: bind an input path by file TYPE when the pinned name-stem binder cannot."""
    stem = key[:-5].lower()
    wanted = _STEM_SUFFIXES.get(stem)
    skip = {str(x) for x in (exclude or [])}
    existing = [(raw, p) for raw, p in gc._repo_paths(goal, root) if p.is_file() and raw not in skip]
    if wanted:
        matching = [raw for raw, p in existing if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    else:
        matching = [raw for raw, p in existing]
    if len(matching) == 1:
        return matching[0]
    if not matching and wanted:
        # The goal named no usable file, so ask the working directory. This
        # binder keeps the two properties world_binding_v1._world_path_for
        # lacks: it honours the exclusion set, and it binds on exactly one
        # candidate while refusing on two. Measured, that other path returns
        # the alphabetically first match, which bound AGENTS.md as the
        # markdown to convert and a stray tool.py as the evidence to rank.
        scanned = _scan_root_by_type(wanted, root, skip)
        if len(scanned) == 1:
            return scanned[0]
        if 1 < len(scanned) <= _SCAN_CANDIDATE_CAP and _interchangeable(scanned, root):
            # Byte-identical, so the choice is terminal-irrelevant. Sorted for
            # determinism: the same world always yields the same path.
            return sorted(scanned)[0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(matching)) + "_type_compatible_existing_files_named")


def _named_output_destinations(
    goal: str, entry: Mapping[str, Any], keys: Any, root: pathlib.Path
) -> set[str]:
    """The paths this sentence explicitly introduces as a DESTINATION of this capability.

    F7 binds an output only when the named file does not exist yet, on the sound rule that a
    file already on disk may belong to somebody else.  But when the named destination DOES
    exist - a re-run of the same request, or an artifact an earlier test left in a shared
    scratch directory - F7 declines it, the step spools elsewhere, and the sentence's own
    destination is left unclaimed.  The input binder then finds it: a named, type-compatible,
    existing file that nothing has taken.  Measured, that is a phantom second candidate, and
    it turns an explicitly stated input into a refusal:

        BINDING_REFUSED:json_path:2_type_compatible_existing_files_named
        matching = ['.../x.json', '.../x_out.json']

    for the sentence "read x.json and save the result to x_out.json", where x_out.json exists.
    The sentence never offered x_out.json as a source; it named it as the destination.

    Identification is by ROLE, not by type.  A generic output_path carries no type of its own,
    so filtering by suffix swept in every named path including the real input - measured, that
    broke the binding outright.  The sentence states the role in the words immediately before
    the path ("save the result to <file>"), and _role_anchored already reads exactly that for
    input roles; outputs simply had no phrases in the alias table, so _role_phrases returned
    [] and no destination could ever be recognised.  When no path is role-anchored this
    returns nothing and every binder behaves exactly as before.

    This only ever REMOVES candidates from input binding.  The one case it can newly refuse is
    a sentence that names the same path as both the source and the destination, which is a
    self-overwrite and should be refused.
    """
    named: set[str] = set()
    for key in (keys or []):
        key = str(key)
        if not key.endswith("_path") or not _is_output_key(key, entry):
            continue
        phrases = _role_phrases(key)
        if not phrases:
            continue
        for raw, _path in gc._repo_paths(goal, root):
            # Every mention, not just the first.  _role_anchored judges the text before the
            # occurrence it finds, so a path the sentence mentions twice - once as the source
            # and once as the destination - would be judged only at its first mention and the
            # destination role would be missed entirely.
            index = str(goal or "").find(raw)
            while index >= 0:
                if _role_anchored(goal, raw, phrases, index=index):
                    named.add(raw)
                    break
                index = str(goal or "").find(raw, index + 1)
    return named


def _bind_output_by_future(goal: str, key: str, root: pathlib.Path, exclude=None):
    """F7: an output named in the sentence is a file that does not exist yet.

    ``exclude`` drops the artifacts earlier steps of the same request produce (F12): a path another
    step is going to write is not a file THIS step is being asked to create.
    """
    skip = {str(x) for x in (exclude or [])}
    stem = key[:-5].lower().replace("output_", "") if key != "output_path" else "output"
    wanted = _STEM_SUFFIXES.get(stem)
    future = [(raw, p) for raw, p in gc._repo_paths(goal, root) if pathlib.Path(raw).suffix and not p.exists() and raw not in skip]
    if wanted:
        future = [(raw, p) for raw, p in future if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    if len(future) == 1:
        return future[0][0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(future)) + "_future_artifacts_named")


SPOOL_DIR = "canonical/astra_runtime/tmp"
SPOOL_DEFAULT_SUFFIX = ".json"


def _spool_suffix(key: str) -> str:
    """The extension a synthesized intermediate artifact must carry.

    Taken from the typed-stem table when the key names a type (``json_path`` -> ``.json``); a
    generic ``output_path`` carries no type of its own, so the documented default applies.
    """
    stem = key[:-5].lower() if key.endswith("_path") else key.lower()
    wanted = _STEM_SUFFIXES.get(stem.replace("output_", ""))
    return sorted(wanted)[0] if wanted else SPOOL_DEFAULT_SUFFIX


def _spool_path(key: str, cycle: int, taken: set[str]) -> str:
    """F13: a deterministic intermediate artifact for a step whose sentence names none.

    The DAG planner assigns it, so a producer and its consumer agree on the path without the
    request having to spell it out.  The path is a pure function of (cycle, key stem, index) and
    is de-duplicated against ``taken``, so it is never a guess about what the requester meant:
    the same request always spools to the same place, and two steps never collide.
    """
    stem = (key[:-5].lower() if key.endswith("_path") else key.lower()).replace("output_", "") or "artifact"
    suffix = _spool_suffix(key)
    index = 0
    while True:
        name = f"spool_{cycle}_{stem}{suffix}" if not index else f"spool_{cycle}_{stem}_{index}{suffix}"
        rel = f"{SPOOL_DIR}/{name}"
        if rel not in taken:
            taken.add(rel)
            return rel
        index += 1


def _bind_produced_artifact(goal: str, key: str, root: pathlib.Path, produced_paths):
    """F12: an input that an EARLIER step of the same request produces binds to that artifact.

    Only called with the exact set of paths the earlier planned steps will write, so a step never
    consumes a path nobody in the request produces.  Ambiguity fails closed.
    """
    produced = [str(x) for x in (produced_paths or []) if isinstance(x, str) and x]
    named = [raw for raw, _p in gc._repo_paths(goal, root)]
    candidates = [raw for raw in named if raw in produced]
    if len(candidates) == 1:
        return candidates[0]
    stem = key[:-5].lower() if key.endswith("_path") else key.lower()
    wanted = _STEM_SUFFIXES.get(stem.replace("output_", ""))
    if wanted:
        typed = [p for p in candidates if pathlib.PurePosixPath(p).suffix.lower() in wanted or "".join(pathlib.PurePosixPath(p).suffixes[-2:]).lower() in wanted]
        if len(typed) == 1:
            return typed[0]
        typed_all = [p for p in produced if pathlib.PurePosixPath(p).suffix.lower() in wanted or "".join(pathlib.PurePosixPath(p).suffixes[-2:]).lower() in wanted]
        if len(typed_all) == 1:
            return typed_all[0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(candidates)) + "_cross_step_artifacts_named")


# ------------------------------------------------------------------- F23: role-anchored input binding

# Words that may sit between a role word and the path it introduces ("the selection file X").
_ROLE_FILLERS = ("the", "a", "an", "file", "document", "record", "records", "input", "artifact")
# Words of a key stem that never name a role ("source_path" -> "source" alone says nothing).
_GENERIC_ROLE_WORDS = {"path", "file", "input", "output", "the", "of", "src", "dst", "and", "with", "a", "an"}


def _role_phrases(key: str) -> list[str]:
    """The phrases that may name this key's ROLE immediately before a path in a sentence.

    The key's own stem is the primary role ("selection_path" -> "selection"); the alias table
    adds the natural words a person actually uses for that role ("with selection <file>").
    """
    stem = key[:-5].lower() if key.endswith("_path") else key.lower()
    words = [w for w in re.split(r"[^a-z0-9]+", stem) if w and w not in _GENERIC_ROLE_WORDS]
    phrases: list[str] = []
    if words:
        phrases.append(" ".join(words))
    for alias in _KEY_ALIASES.get(key, ()):
        alias = str(alias).lower().strip()
        if alias and alias not in phrases:
            phrases.append(alias)
    return phrases


def _role_anchored(goal: str, raw: str, phrases, index: int | None = None) -> bool:
    """True when the sentence introduces this path with one of ``phrases`` right before it.

    ``index`` pins WHICH mention to judge.  Without it the first occurrence decides, which is
    right for a path named once and wrong for a path named twice: in "read x.json and save
    the result to x.json" the first mention carries the source role and the second carries
    the destination role, so a caller asking about the destination must be able to point at
    the second.  Default None keeps every existing caller's behaviour exactly.
    """
    text = str(goal or "")
    if index is None:
        index = text.find(raw)
    if index < 0:
        return False
    before = text[:index]
    filler = r"(?:\s+(?:" + "|".join(_ROLE_FILLERS) + r"))?"
    for phrase in phrases:
        words = [w for w in re.split(r"[^a-z0-9]+", str(phrase).lower()) if w]
        if not words:
            continue
        pattern = r"(?<![a-z0-9])" + r"[^a-z0-9]+".join(re.escape(w) for w in words) + r"(?![a-z0-9])"
        if re.search(pattern + filler + r"\s*$", before, flags=re.IGNORECASE):
            return True
    return False


def _named_existing_paths(goal: str, root: pathlib.Path) -> list[str]:
    """Existing files the sentence names, in order of appearance."""
    text = str(goal or "")
    found: list[str] = []
    for raw, path in gc._repo_paths(goal, root):
        if path.is_file() and raw not in found:
            found.append(raw)
    found.sort(key=lambda raw: (text.find(raw) if text.find(raw) >= 0 else len(text), raw))
    return found


# Two paths belong to ONE conjunction group when only a conjunction separates them
# ("the manifest a.json and b.json").  A role word in front of such a group governs ALL of
# its members, so the role alone cannot say which one the capability must read.
_CONJUNCTION_ONLY = re.compile(r"^[\s,]*(?:(?:and|plus|as well as)\b[\s,]*)?$", re.IGNORECASE)


def _path_groups(goal: str) -> dict[str, list[str]]:
    """Map every path the sentence names to the paths it names in the SAME conjunction."""
    text = str(goal or "")
    matches: list[tuple[str, int, int]] = []
    for match in re.finditer(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", text):
        raw = match.group(0).rstrip(".,;:!?)]}")
        if raw:
            matches.append((raw, match.start(), match.end()))
    groups: dict[str, list[str]] = {}
    for index, (raw, _start, end) in enumerate(matches):
        group = [raw]
        cursor = end
        for _raw, next_start, next_end in matches[index + 1:]:
            if not _CONJUNCTION_ONLY.match(text[cursor:next_start]):
                break
            group.append(_raw)
            cursor = next_end
        groups.setdefault(raw, group)
    return groups


def _joint_role_binding(goal: str, pending: list[str], root: pathlib.Path, taken,
                        produced_paths=None) -> dict[str, str]:
    """F23: bind several same-type input files by the roles the sentence gives them.

    The pinned binder refuses a key whose stem matches more than one named file, and the
    type fallback refuses it as well - so a sentence naming two JSON documents (a live
    metadata file and a selection record) could never reach the capability that consumes
    both, even though the sentence says which is which.  Here the SENTENCE decides: the
    role word that introduces a path ("with selection <file>") claims that file for the key
    whose stem is that role, and a file left with exactly one unclaimed key is bound by
    elimination.  Nothing is guessed - every binding is either stated by the sentence or
    forced by the only remaining assignment; anything else fails closed.

    F26: the pool also holds the artifacts an EARLIER step of the same request writes, when
    the sentence names them.  That is the whole point of a multi-step request ("fetch it,
    then audit what you fetched"): the consumer's input IS the producer's artifact, and the
    role the sentence gives it is the only thing that says so.  Measured before F26: the
    consumer bound the selection record instead (it was the only file on disk), the producer's
    artifact was claimed as the consumer's OUTPUT, and the request silently dropped a step.
    """
    skip = set(taken or [])
    pool = [raw for raw in _named_existing_paths(goal, root) if raw not in skip]
    named = [raw for raw, _p in gc._repo_paths(goal, root)]
    for produced in (produced_paths or []):
        produced = str(produced)
        if produced in named and produced not in skip and produced not in pool:
            pool.append(produced)
    if not pending or not pool:
        return {}
    remaining_keys = list(pending)
    remaining_files = list(pool)
    assignment: dict[str, str] = {}
    claims: dict[str, tuple[int, str]] = {}
    groups = _path_groups(goal)
    existing = set(pool)
    for key in remaining_keys:
        phrases = _role_phrases(key)
        best: tuple[int, str] | None = None
        ambiguous = False
        for raw in remaining_files:
            for phrase in phrases:
                words = [w for w in re.split(r"[^a-z0-9]+", str(phrase).lower()) if w]
                if not words:
                    continue
                if not _role_anchored(goal, raw, [phrase]):
                    continue
                spec = len(words)
                if best is None or spec > best[0]:
                    best, ambiguous = (spec, raw), False
                elif spec == best[0] and raw != best[1]:
                    ambiguous = True
        if best is not None:
            # a role in front of a CONJUNCTION ("the manifest a.json and b.json") governs every
            # member of the group: the sentence does not say which one to read, so it stays open.
            group = [p for p in (groups.get(best[1]) or [best[1]]) if p in existing]
            if len(group) > 1:
                ambiguous = True
        if best is not None and not ambiguous:
            claims[key] = best
    # a file two roles claim equally is not decided by the sentence
    for key, (spec, raw) in list(claims.items()):
        if any(other != key and other_spec >= spec and other_raw == raw
               for other, (other_spec, other_raw) in claims.items()):
            claims.pop(key)
    for key, (_spec, raw) in claims.items():
        if raw in remaining_files:
            assignment[key] = raw
            remaining_files.remove(raw)
            remaining_keys.remove(key)
    if len(remaining_keys) == 1 and len(remaining_files) == 1:
        assignment[remaining_keys[0]] = remaining_files[0]
    return assignment


def bind_all_inputs(goal: str, entry: Mapping[str, Any], root: pathlib.Path, context_paths=None, future_clauses=None,
                    produced_paths=None, cycle=None, spool=None) -> dict[str, Any]:
    """Pinned binder for the keys it supports, typed grammar / type binding for the rest. Never guesses.

    ``produced_paths`` (F12) is the set of artifacts earlier steps of the same multi-step request
    will write; it is the only additional source an input path may bind from.

    ``cycle``/``spool`` (F13) enable intermediate spooling: when an OUTPUT path is not named by the
    sentence and no earlier step produces it, a deterministic spool path is assigned instead of
    failing closed.  Passing ``spool=None`` keeps the original fail-closed behaviour, which is what
    every caller outside the DAG planner does.
    """
    keys = input_keys(entry)
    # F20: a ``*_path`` key whose OWN registry entry declares it a literal list value is a
    # payload selector (knowledge fetch json_path: literal []), not a file; every other
    # ``*_path`` key (jq json_path ...) keeps the pinned file binder.
    declared_selectors = _declared_literal_selector_keys(entry)
    pinned_keys = [k for k in keys if k not in declared_selectors and (k in ("text", "goal", "url") or k.endswith("_path"))]
    typed_keys = [k for k in keys if k not in pinned_keys]
    inputs: dict[str, Any] = {}
    taken: set[str] = set()
    pending_input_paths: list[str] = []
    for key in pinned_keys:
        shadow = dict(entry)
        shadow["action_template"] = {"args": {key: "${input." + key + "}"}}
        try:
            bound_val = gc._bind_inputs(goal, root, shadow, context_paths=context_paths, future_clauses=future_clauses)
            val = bound_val.get(key)
            if key.endswith("_path") and not _is_output_key(key, entry) and val:
                stem = key[:-5].lower()
                wanted = _STEM_SUFFIXES.get(stem)
                if wanted and pathlib.PurePosixPath(val).suffix.lower() not in wanted:
                    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", "type_mismatch:" + key)
            inputs.update(bound_val)
            if isinstance(val, str) and val:
                taken.add(val)
        except GoalCompilationFailure:
            if key.endswith("_path") and not _is_output_key(key, entry):
                # F23: a key the pinned binder could not decide is decided with its SIBLINGS,
                # because the roles the sentence gives the files are only meaningful together.
                pending_input_paths.append(key)
                continue
            if key.endswith("_path"):
                # F26: an OUTPUT is a new artifact.  It never claims an artifact an earlier
                # step already writes (that would overwrite the producer's output), so the
                # produced-artifact binder is not offered here - only the future artifacts the
                # sentence still names, and then the deterministic spool.
                bound = None
                try:
                    bound = _bind_output_by_future(goal, key, root, exclude=produced_paths)
                except GoalCompilationFailure:
                    bound = None
                if bound is None:
                    if spool is None or cycle is None:
                        raise
                    bound = _spool_path(key, cycle, spool)
                inputs[key] = bound
                if isinstance(bound, str) and bound:
                    taken.add(bound)
                continue
            raise
    # F23: the roles the sentence states decide the keys the pinned binder left open.
    if pending_input_paths:
        joint = _joint_role_binding(goal, pending_input_paths, root, taken, produced_paths=produced_paths)
        for key in pending_input_paths:
            if key in joint:
                inputs[key] = joint[key]
                taken.add(joint[key])
    for key in pending_input_paths:
        if key in inputs:
            continue
        is_effect_consumer = (
            isinstance(entry.get("proposal_bindings"), Mapping)
            and entry["proposal_bindings"].get(key, {}).get("type") == "effect_result"
        )
        if is_effect_consumer and produced_paths:
            try:
                inputs[key] = _bind_produced_artifact(goal, key, root, produced_paths)
            except GoalCompilationFailure:
                inputs[key] = _bind_path_by_type(goal, key, root, exclude=_excluded(produced_paths, taken) | _named_output_destinations(goal, entry, keys, root))
        else:
            try:
                inputs[key] = _bind_path_by_type(goal, key, root, exclude=_excluded(produced_paths, taken) | _named_output_destinations(goal, entry, keys, root))
            except GoalCompilationFailure as type_failure:
                if not produced_paths:
                    raise
                try:
                    inputs[key] = _bind_produced_artifact(goal, key, root, produced_paths)
                except GoalCompilationFailure:
                    raise type_failure
        if isinstance(inputs.get(key), str) and inputs[key]:
            taken.add(inputs[key])
    for key in typed_keys:
        inputs[key] = bind_typed_key(goal, key, root)
    repair_output_collisions(goal, inputs, root, exclude=produced_paths, entry=entry,
                             cycle=cycle, spool=spool)
    return inputs


def repair_output_collisions(goal: str, inputs: dict[str, Any], root: pathlib.Path, exclude=None, entry: Mapping[str, Any] | None = None,
                             cycle=None, spool=None) -> list[str]:
    """F10: an output path is never one of the action's own input files.

    The pinned binder can resolve `output_path` to an existing input named in the sentence; the
    tool then overwrites its input and the promised artifact never appears.  When an output key
    points at a path that is also bound as an input, or at an existing file while the sentence
    names exactly one file that does not exist yet, the future artifact wins.  Ambiguity raises
    (fail closed) instead of guessing.  Returns the keys that were rebound.

    F13: when the sentence names no output artifact at all, a deterministic spool path replaces
    the colliding one.  A sentence that names an artifact - one or several - still binds or fails
    closed on it, so this never overrides a stated intent.
    """
    rebound = []
    # The repository root arrives as a string from some callers (the retrieval path passes
    # whatever the caller gave it) and as a Path from others.  Measured: a request naming
    # "p3 binary decision grounded expression v1" reached this function with a str root and
    # died on `root / value` with `unsupported operand type(s) for /: 'str' and 'str'` - a
    # crash in the compiler, not a refusal.  A compiler that crashes is not a compiler that
    # fails closed, so the type is settled here rather than at each call site.
    root = pathlib.Path(root)
    input_paths = {str(v) for k, v in inputs.items() if k.endswith("_path") and not _is_output_key(k, entry)}
    for key in [k for k in inputs if k.endswith("_path") and _is_output_key(k, entry)]:
        value = str(inputs[key])
        collides = value in input_paths
        exists = (root / value).exists()
        if collides or (exists and len([p for p in _future_artifacts(goal, root) if p not in {str(x) for x in (exclude or [])}]) == 1):
            try:
                inputs[key] = _bind_output_by_future(goal, key, root, exclude=exclude)
            except GoalCompilationFailure:
                if spool is None or cycle is None or _future_artifacts(goal, root):
                    raise
                inputs[key] = _spool_path(key, cycle, spool)
            rebound.append(key)
    return rebound


# ----------------------------------------------------------------------------- routing

def prose_only(goal: str) -> str:
    """The sentence without URLs, repository paths and quoted literals (F8, F25).

    A URL, a path and a quoted literal are all VALUES the request carries: the address it
    reads, the file it touches, the text it encodes.  None of them says what the task IS.
    F8 already removed the first two; F25 removes the third, because a value's own words were
    being read as the task's words.  Measured: ``Apply the jq filter "[.items[].v] | add"``
    scored the SA-CCR credit add-on capability above the jq capability (the word "add" lives
    inside the FILTER, not in the request), and ``with jq filter ".record.tag"`` scored a DOCX
    creator above jq (the word "record" lives inside the filter too).  The task was right in
    both sentences; the value was mistaken for the task.
    """
    text = re.sub(r"https?://[^\s)\]}>]+", " ", str(goal or ""))
    text = _QUOTED_LITERAL.sub(" ", text)
    return re.sub(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", " ", text)


_ECOSYSTEM_WORD = re.compile(r"(?i)\b(?:pypi|npm|node(?:\.js|js)?|apt)\b|python library|javascript library|ubuntu package|debian package")
_SURFACE_WORD = {"npm_node": "npm", "pypi_python": "pypi", "apt": "apt"}


def score_capability(goal: str, cid: str, entry: Mapping[str, Any]) -> tuple[int, int, dict[str, Any]]:
    """The score of ONE capability for this sentence, on the same basis the ranker uses.

    F18: the ecosystem surface rule (npm/pypi/apt) is evaluated on PROSE, never on a URL or a
    path, and an ecosystem word that is one of the capability's OWN tokens is not a claim about
    which executor may run - the sentence says "pypi" because the capability IS about pypi.
    Measured: ``Fetch the external knowledge JSON from https://pypi.org/pypi/requests/json ...``
    rejected every generic fetch tool because the pypi HOST inside the URL was read as an
    ecosystem claim, leaving zero candidates for a sentence whose own keywords match at score
    29.  A URL is an input VALUE being fetched (K1 knowledge), not a statement about which
    ecosystem the executor must come from; the claim words live in the prose, and prose still
    carries the rule: a sentence that says "pypi package" in words keeps the pypi requirement.

    The route admission re-derives a DAG step's evidence HERE, so a step is judged the way the
    planner chose it: a pypi step scored 0 under the raw pinned rule and the whole multi-step
    request was refused with DAG_STEP_WEAK_EVIDENCE.
    """
    prose = prose_only(goal)
    scored_text = prose
    surface_ok, surface_evidence = gc._execution_surface_constraint_match(prose, entry)
    if not surface_ok:
        own = gc._tokens(entry.get("keywords", [])) | gc._tokens(cid) | gc._tokens(entry.get("provides", []))
        surface_word = _SURFACE_WORD.get(str((surface_evidence or {}).get("required_surface")))
        if not (surface_word and surface_word in own):
            return gc._score(prose, cid, entry)
        scored_text = _ECOSYSTEM_WORD.sub(" ", prose)
    return gc._score(scored_text, cid, entry)


def ranked_candidates(goal: str, registry: Mapping[str, Mapping[str, Any]]) -> list[tuple[int, int, str, dict[str, Any]]]:
    """Candidates ranked by the pinned scorer on prose tokens only; constraints see the full goal."""
    out = []
    for cid, entry in sorted(registry.items()):
        if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"), dict):
            continue
        prose = prose_only(goal)
        surface_ok, surface_evidence = gc._execution_surface_constraint_match(prose, entry)
        if not surface_ok:
            own = gc._tokens(entry.get("keywords", [])) | gc._tokens(cid) | gc._tokens(entry.get("provides", []))
            surface_word = _SURFACE_WORD.get(str((surface_evidence or {}).get("required_surface")))
            if not (surface_word and surface_word in own):
                continue
        if not gc._structured_binary_format_match(goal, entry)[0]:
            continue
        score, specificity, evidence = score_capability(goal, cid, entry)
        if score > 0:
            out.append((score, specificity, cid, evidence))
    out.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return out


def _future_artifacts(goal: str, root: pathlib.Path) -> list[str]:
    return [raw for raw, p in gc._repo_paths(goal, root) if pathlib.Path(raw).suffix and not p.exists()]


def _output_keys(entry: Mapping[str, Any]) -> list[str]:
    return [k for k in input_keys(entry) if k.startswith("output_") or k.split("_")[0] in {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}]


_WHOLE_REQUEST_INPUTS = {"goal", "task", "objective", "request", "instruction", "description",
                         "content", "body"}
# "text", "prompt" and "query" are NOT whole-request markers: a capability may take a PAYLOAD
# under those names (the content a QR code encodes, the question a chart reader answers), and
# such a capability is a real route, not an answer-anything fallback.


def _is_catch_all(entry: Mapping[str, Any]) -> bool:
    """True for a capability that can serve ANY sentence.

    It takes the whole request as its input (or nothing at all) and writes an artifact: such a
    capability binds every sentence, so it can never be the DECISION - it is only ever the
    last resort the pinned compiler falls through to, which is the defect F1 exists to stop.
    """
    names = input_keys(entry)
    if not names:
        return True
    for name in names:
        if name in _WHOLE_REQUEST_INPUTS:
            continue
        if _is_output_key(name, entry):
            continue
        return False
    return True


def _score_tiers(pool: list[tuple[int, int, str, dict[str, Any]]]) -> list[list[tuple[int, int, str, dict[str, Any]]]]:
    """The ranked pool split into equal-score tiers (a tie is one tier, F22)."""
    tiers: list[list[tuple[int, int, str, dict[str, Any]]]] = []
    for cand in pool:
        if tiers and tiers[-1][0][0] == cand[0]:
            tiers[-1].append(cand)
        else:
            tiers.append([cand])
    return tiers


# A binding failure that names ZERO candidates means the sentence never stated that input;
# a failure that names TWO or more means the sentence stated it ambiguously.  The difference
# decides whether the route may continue (F24) or must fail closed.
_UNSTATED_DETAIL = re.compile(r"(?:^|:)(?:not_stated|value_not_parseable|no_matching_existing_files_named)$")


def _failure_is_unstated(exc: BaseException) -> bool:
    """True when the sentence gave the candidate NOTHING for one of its declared inputs."""
    if getattr(exc, "code", "") != "GOAL_INPUT_BINDING_REQUIRED":
        return False
    detail = str(getattr(exc, "detail", "") or "")
    counted = re.search(r":(\d+)_", detail)
    if counted:
        return int(counted.group(1)) == 0
    return bool(_UNSTATED_DETAIL.search(detail))


def _single(cid: str, entry: Mapping[str, Any], inputs: Mapping[str, Any], score: int, evidence: Mapping[str, Any], rules: list[str]) -> dict[str, Any]:    return {
        "schema": "PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode": "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH",
        "selected_capability": cid,
        "score": score,
        "match_evidence": dict(evidence),
        "inputs": dict(inputs),
        "initial_facts": list(entry.get("requires") or []),
        "target_effects": list(entry.get("provides") or []),
        "capabilities": [],
        "finish_summary": "PLAIN_GOAL_COMPLETE",
        "front_compiler": {"schema": SCHEMA, "rules_applied": list(rules)},
    }


def _retrieval_first_selection(goal: str, admissible: Mapping[str, Mapping[str, Any]],
                               root: pathlib.Path, rules: list[str]) -> dict[str, Any] | None:
    """F17: retrieval proposes k=3, typed admission disposes.  Returns None to keep the failure.

    Called ONLY after the pinned prose scorer has failed to deliver a bound single capability, so
    it can turn a failure into a selection and can never override a selection that already bound
    (that discipline is what keeps every earlier rule's evidence intact).  Selection quality is
    therefore bounded by admission, not by the ranker: a lexical near-miss whose declared inputs
    the sentence does not state is refused, and an ambiguous shortlist selects nothing at all.
    """
    from canonical.runtime import capability_selection_retrieval_v1 as selection

    decision = selection.select(goal, admissible, root, selection.DEFAULT_K)
    if decision.get("status") != "SELECTED":
        return None
    cid = decision["selected_capability"]
    entry = admissible.get(cid) or {}
    if not entry:
        return None
    # SCOPED, and this is the whole reason F17 exists: a receipt-backed capability is invisible to
    # the pinned scorer (it skips anything whose status is not VERIFIED_BOUND_CAPABILITY), so no
    # earlier rule can ever select one from a sentence.  Everything the pinned scorer CAN see stays
    # its decision: measured, an unscoped version of this hook displaced `grounding.stdlib` from its
    # own signature sentence in favour of a specific sibling, which is a misroute, not a fix.  So a
    # retrieved selection is accepted only when it is DERIVED EVIDENCE - a capability the pinned
    # path structurally cannot propose.
    if entry.get("capability_source") != "receipt_projection":
        return None
    proposals = decision.get("proposals") or []
    score = int(round(float((proposals[0] if proposals else {}).get("lexical_relevance_score") or 0)))
    rules.append("F17_RETRIEVAL_FIRST_TYPED_ADMISSION")
    return _single(cid, entry, decision["inputs"], score, {
        "rule": "F17_RETRIEVAL_FIRST_TYPED_ADMISSION",
        "retrieval": decision.get("authority"),
        "k": decision.get("k"),
        "proposals": [p["capability_id"] for p in proposals],
        "admissions": [{k: v for k, v in row.items() if k in ("capability_id", "admitted", "reason")}
                       for row in decision.get("admissions") or []],
    }, rules)


_LITERAL_MODES = {"DETERMINISTIC_LITERAL_JSON_RECORDS", "DETERMINISTIC_EXACT_LITERAL_RESPONSE"}


def sentence_clauses(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])|\b[Tt]hen\b", " ".join(str(text or "").split()))
    return [part.strip(" .,;") for part in parts if part and part.strip(" .,;")]


# ----------------------------------------------------------------------------- capability DAG (F11)

def _whole_value_placeholder(template: Any, key: str) -> bool:
    """True when every ``${input.<key>}`` occurrence in the template is a whole string value.

    Only then can the bound value be replaced by a cross-step reference; a placeholder embedded in
    a longer string could not carry one, so the caller fails closed instead of rendering it.
    """
    marker = "${input." + key + "}"
    slots: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and marker in value:
            slots.append(value)

    walk(template)
    return bool(slots) and all(slot == marker for slot in slots)


def _claiming_earlier_artifact(inputs: Mapping[str, Any], produced_paths, entry: Mapping[str, Any] | None = None) -> bool:
    produced = {str(x) for x in (produced_paths or [])}
    return any(_is_output_key(key, entry) and isinstance(value, str) and value in produced for key, value in inputs.items())


def bind_dag_clause(clause: str, admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path, produced_paths=None,
                    cycle=None, spool=None):
    """Bind ONE step of a multi-step request to a bound capability (F11).

    Candidates are ranked on the clause's prose tokens (F8); the best one that can bind every
    declared input wins, where the artifacts earlier steps will write are the only extra source an
    input path may bind from (F12).  A candidate that would claim an artifact an earlier step
    already produces, or name the same path for two of its own inputs, is rejected.  Returns
    ``None`` when no bound capability serves the clause - never a weaker guess.
    """
    registry = routable_registry(admissible)
    for score, specificity, cid, evidence in ranked_candidates(clause, registry):
        entry = registry[cid]
        try:
            inputs = bind_all_inputs(clause, entry, root, produced_paths=produced_paths,
                                     cycle=cycle, spool=spool)
        except GoalCompilationFailure:
            continue
        if _claiming_earlier_artifact(inputs, produced_paths, entry):
            continue
        if any(str(inputs[k]) == str(inputs[j]) for k in inputs if _is_output_key(k, entry) for j in inputs if j != k and j.endswith("_path")):
            continue
        return {"capability_id": cid, "inputs": inputs, "score": score, "specificity": specificity, "match_evidence": dict(evidence)}
    return None


def _dag_steps(clauses: list[str], admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path):
    registry = routable_registry(admissible)
    steps: list[dict[str, Any]] = []
    produced: list[str] = []
    spool: set[str] = set()
    for cycle, clause in enumerate(clauses):
        bound = bind_dag_clause(clause, admissible, root, produced_paths=produced,
                                cycle=cycle, spool=spool)
        if bound is None:
            return None
        entry = registry[bound["capability_id"]]
        outputs = [(key, str(value)) for key, value in bound["inputs"].items()
                   if _is_output_key(key, entry) and isinstance(value, str) and value]
        steps.append({**bound, "clause": clause, "entry": entry, "outputs": outputs, "forwarded": {}})
        produced.extend(path for _key, path in outputs)
    return steps


def _dag_artifact_edges(steps: list[dict[str, Any]], root: pathlib.Path) -> list[dict[str, Any]]:
    """Every input bound to an artifact an EARLIER step writes, as an explicit forwarding edge."""
    claimed: dict[str, int] = {}
    for index, step in enumerate(steps):
        for _key, path in step["outputs"]:
            if path in claimed:
                raise GoalCompilationFailure(
                    "CAPABILITY_DAG_ARTIFACT_CONFLICT",
                    path + ":steps:" + str(claimed[path]) + "," + str(index),
                )
            claimed[path] = index
    edges: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        forwarded: dict[str, Any] = {}
        for key, value in step["inputs"].items():
            if _is_output_key(key, step.get("entry")) or not isinstance(value, str) or not value or not key.endswith("_path"):
                continue
            producer, field = None, None
            for earlier in range(index):
                match = [k for k, path in steps[earlier]["outputs"] if path == value]
                if match:
                    producer, field = earlier, match[0]
                    break
            if producer is None:
                if any(path == value for _k, path in step["outputs"]):
                    raise GoalCompilationFailure("CAPABILITY_DAG_SELF_ARTIFACT_REFERENCE", step["capability_id"] + ":" + key + ":" + value)
                if any(path == value for later in range(index + 1, len(steps)) for _k, path in steps[later]["outputs"]):
                    raise GoalCompilationFailure("CAPABILITY_DAG_REVERSE_ARTIFACT_REFERENCE", step["capability_id"] + ":" + key + ":" + value)
                if pathlib.PurePosixPath(value).suffix and not (root / value).exists():
                    raise GoalCompilationFailure("CAPABILITY_DAG_ARTIFACT_UNPRODUCED", step["capability_id"] + ":" + key + ":" + value)
                continue
            if not _whole_value_placeholder(step["entry"].get("action_template") or {}, key):
                raise GoalCompilationFailure("CAPABILITY_DAG_FORWARD_BINDING_UNSUPPORTED", step["capability_id"] + ":" + key)
            effect = "artifact:" + value
            forwarded[key] = {"$effect_result": {"effect": effect, "field": field}}
            edges.append({
                "consumer_cycle": index, "consumer_capability_id": step["capability_id"], "input_key": key,
                "producer_cycle": producer, "producer_capability_id": steps[producer]["capability_id"],
                "produced_path": value, "result_field": field, "effect": effect,
            })
        step["forwarded"] = forwarded
    return edges


def _dag_problem(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """The capability_planner problem for one multi-step request.

    Facts are explicit: ``env:<declared precondition>`` (verified by the binder at compile time),
    ``order:<i>`` (the sentence order the request states) and ``artifact:<path>`` (a file a step
    writes).  A step declares the artifact an earlier step writes among its requirements, so the
    planner is the authority that the consumer never runs before its producer, and ``plan_actions``
    turns that requirement into a ``$result`` reference the executor resolves.
    """
    initial = {"order:0"}
    capabilities: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        entry = step["entry"]
        bound = dict(step["inputs"])
        bound.update(step["forwarded"])
        try:
            action = dict(gc._render_template(entry.get("action_template") or {}, bound))
        except GoalCompilationFailure as exc:
            raise GoalCompilationFailure("CAPABILITY_DAG_ACTION_RENDER_FAILED", step["capability_id"] + ":" + str(exc.detail)) from exc
        declared = [str(e) for e in (entry.get("requires") or [])]
        requires = {"env:" + effect for effect in declared}
        requires.update(value["$effect_result"]["effect"] for value in step["forwarded"].values())
        if index:
            requires.add("order:" + str(index))
        provides = {"step:" + str(index) + ":executed"}
        if index < len(steps) - 1:
            provides.add("order:" + str(index + 1))
        provides.update("artifact:" + path for _key, path in step["outputs"])
        initial.update("env:" + effect for effect in declared)
        result_fields = {str(x) for x in (entry.get("result_fields") or [])} | {key for key, _path in step["outputs"]}
        capabilities.append({
            "id": "step:" + str(index) + ":" + str(step["capability_id"]),
            "source_capability_id": step["capability_id"],
            "requires": sorted(requires),
            "provides": sorted(provides),
            "cost": float(entry.get("cost", 1) or 0),
            "action": action,
            "result_fields": sorted(result_fields),
        })
    targets = sorted({fact for cap in capabilities for fact in cap["provides"]})
    return {
        "initial_facts": sorted(initial),
        "target_effects": targets,
        "capabilities": capabilities,
        "finish_summary": DAG_FINISH_SUMMARY,
        "max_expansions": 5000,
    }


def plan_capability_dag(goal: str, admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path):
    """F11: compile a multi-step request into ONE capability DAG and plan it with capability_planner.

    Returns the compiled shape (``compiler_mode`` = ``FRONT_CAPABILITY_DAG_PLANNED``) or ``None``
    when the request is not a multi-step request whose every step is a bound capability.  A step
    that cannot be served, an artifact two steps would both claim, a consumer of an artifact no
    earlier step writes, or a contradiction the planner cannot satisfy all fail closed.
    """
    clauses = sentence_clauses(goal)
    if len(clauses) < 2:
        return None
    steps = _dag_steps(clauses, admissible, root)
    if steps is None or len(steps) < 2:
        return None
    rules = ["F11_MULTI_STEP_CAPABILITY_DAG_PLANNED"]
    edges = _dag_artifact_edges(steps, root)
    if edges:
        rules.append("F12_CROSS_STEP_ARTIFACT_BOUND")
    if any(str(v).startswith(SPOOL_DIR + "/spool_") for step in steps for v in step["inputs"].values()):
        rules.append("F13_INTERMEDIATE_SPOOL_ASSIGNED")
    problem = _dag_problem(steps)
    try:
        planned = capability_planner.plan_actions(problem)
    except capability_planner.PlanningFailure as exc:
        code = "CAPABILITY_DAG_UNREACHABLE_STEP" if exc.code == "UNREACHABLE_TARGET_EFFECTS" else "CAPABILITY_DAG_PLANNING_FAILED"
        raise GoalCompilationFailure(code, (str(exc.detail) if exc.detail else str(exc.code))[:300]) from exc
    expected = ["step:" + str(index) + ":" + str(step["capability_id"]) for index, step in enumerate(steps)]
    emitted = [str(a.get("capability_id")) for a in planned["actions"] if isinstance(a, Mapping) and a.get("type") != "finish"]
    if emitted != expected:
        raise GoalCompilationFailure("CAPABILITY_DAG_PLAN_ORDER_INVALID", ",".join(emitted)[:300])
    dag_steps = []
    for index, step in enumerate(steps):
        action = dict(planned["actions"][index])
        dag_steps.append({
            "cycle": index,
            "capability_id": step["capability_id"],
            "clause": step["clause"],
            "action": action,
            "expect": action.get("expect"),
            "requires": list(problem["capabilities"][index]["requires"]),
            "provides": list(problem["capabilities"][index]["provides"]),
            "result_fields": list(problem["capabilities"][index]["result_fields"]),
            "artifacts_produced": sorted(path for _key, path in step["outputs"]),
            "artifacts_consumed": [dict(edge) for edge in edges if edge["consumer_cycle"] == index],
        })
    return {
        "schema": "PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode": DAG_MODE,
        "selected_capability": None,
        "controller_actions": [dict(a) for a in planned["actions"]],
        "compiled_parts": [{
            "clause": step["clause"], "selected_capability": step["capability_id"], "inputs": dict(step["inputs"]),
            "score": step["score"], "match_evidence": dict(step["match_evidence"]),
            "target_effects": [str(e) for e in (step["entry"].get("provides") or [])],
        } for step in steps],
        "target_effects": sorted({str(e) for step in steps for e in (step["entry"].get("provides") or [])}),
        "clauses": [step["clause"] for step in steps],
        "capability_dag": {
            "schema": DAG_SCHEMA,
            "compiler_mode": DAG_MODE,
            "finish_summary": DAG_FINISH_SUMMARY,
            "steps": dag_steps,
            "artifact_edges": [dict(edge) for edge in edges],
            "planning": dict(planned["planning"]),
            "composition_contract": [dict(row) for row in planned["composition_contract"]],
            "problem": problem,
            "front_compiler": {"schema": SCHEMA, "rules_applied": list(rules)},
        },
        "front_compiler": {"schema": SCHEMA, "rules_applied": list(rules)},
    }


def _actions_of(compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    actions = compiled.get("controller_actions")
    if isinstance(actions, list):
        return [dict(a) for a in actions if isinstance(a, Mapping) and a.get("type") != "finish"]
    cid = str(compiled.get("selected_capability") or "")
    if cid not in registry or not isinstance(compiled.get("inputs"), Mapping):
        raise GoalCompilationFailure("GOAL_COMPILATION_CLAUSE_NOT_EXECUTABLE", cid)
    return [gc._render_template(registry[cid]["action_template"], dict(compiled["inputs"]))]


def _compile_clauses(clauses: list[str], admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path, rules: list[str]) -> dict[str, Any]:
    registry = routable_registry(admissible)
    parts, actions, effects = [], [], []
    for clause in clauses:
        sub = compile_goal(clause, admissible, root)
        parts.append(sub)
        actions.extend(_actions_of(sub, registry))
        effects.extend(e for e in (sub.get("target_effects") or []) if e not in effects)
    if not actions:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_EXECUTABLE_CLAUSE")
    rules.append("F5_COMPOUND_SENTENCES_COMPILED_SEPARATELY")
    return {
        "schema": "PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode": "FRONT_COMPOUND_SENTENCES",
        "controller_actions": actions + [{"type": "finish", "args": {"summary": "COMPOUND_GOAL_COMPLETE"}}],
        "compiled_parts": parts,
        "target_effects": effects,
        "clauses": list(clauses),
        "front_compiler": {"schema": SCHEMA, "rules_applied": list(rules)},
    }


def compile_goal(goal: str, admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path) -> dict[str, Any]:
    """Front compile. Returns the pinned compiler's shape plus ``front_compiler`` metadata."""
    rules: list[str] = []
    original = str(goal or "").strip()
    text = normalize_goal(original)
    if text != original:
        rules.append("F2_SENTENCE_FINAL_PERIOD_REMOVED")

    # F15: an id that appears verbatim in the goal is the caller choosing that capability.
    # Defect 10 - without this, the id is stripped as a path and the goal is absorbed by a
    # generic candidate that reports success for work it was never asked to do.
    named = explicitly_named_capabilities(text, admissible)
    if len(named) == 1 and naming_is_the_whole_request(text, named[0]):
        cid = named[0]
        entry = admissible[cid]
        inputs = (
            bind_all_inputs(text, entry, root, cycle=0, spool=set())
            if is_plain_goal_routable(entry)
            else {}
        )
        rules.append("F15_EXPLICIT_CAPABILITY_ID_NAMED")
        return _single(
            cid,
            entry,
            inputs,
            _EXPLICIT_NAME_SCORE,
            {
                "rule": "F15_EXPLICIT_CAPABILITY_ID_NAMED",
                "explicit_capability_id": cid,
                "named_route": "EXACT_CAPABILITY_ID_IN_GOAL",
            },
            rules,
        )

    # F16: an id-shaped token is an identity.  A registered one inside a longer request is a
    # composition this layer does not claim; an unregistered one is not a capability at all
    # and must not become an artifact some other capability can "satisfy" by writing a file.
    #
    # Identity is derived from the registry, not from a spelling: the shape regex below only
    # knows the `*.py.auto.v1` inventory ids, so a registered capability named any other way
    # (e.g. `brain.module.function.invoke`) used to fall through this rule and reach the
    # ranker, which answers GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH for a compound
    # request that names a real capability.  `named` is already computed above and is by
    # construction a subset of the registry, so this adds identity without adding a lookup.
    shaped = capability_id_shaped_tokens(text)
    identities = sorted(set(shaped) | set(named))
    if identities:
        unknown = [t for t in identities if t not in admissible]
        if unknown:
            raise GoalCompilationFailure("GOAL_NAMES_UNKNOWN_CAPABILITY", ",".join(unknown[:3]))
        raise GoalCompilationFailure("GOAL_NAMES_CAPABILITY_IN_COMPOUND_REQUEST", ",".join(identities[:3]))

    # A ZERO-INPUT TOOL MAY COMPETE; IT MAY NEVER DECIDE.
    #
    # `routable_registry` deletes the capabilities that take no input, because a
    # capability that binds every sentence can never be the answer to one.  That
    # is exactly what `_is_catch_all`'s own docstring says: "it can never be the
    # DECISION".  Deleting them from the RANKING, though, does more than refuse
    # them -- it changes what the pinned compiler can bind at all, and that was
    # measured to flip a selection.
    #
    # "Fetch a JSON document and assess its internal consistency." binds nothing
    # grounded once `terminal.kstar.root.assess.stdlib` is gone, so the pinned
    # compiler falls through to WORLD binding and returns
    # `docx.document.create_from_json_record` at score 25 with `json_path`
    # inferred to canonical/CANONICAL_POINTER.json; with it present the grounded
    # pass is non-empty, the world fallback never runs, and the chained pass's
    # `knowledge.consistency.assess` (score 8, every slot grounded) wins.  The
    # docx pick then fails at execution with JSON_DOCX_SPEC_UNRESOLVED, because
    # the spec that producer needs was never stated.
    #
    # So the full admissible view is what gets RANKED and what the pinned
    # compiler binds against, while the routable projection is what may be
    # DECIDED.  `_is_catch_all` still refuses a catch-all inside the walk and F17
    # still displaces one the pinned scorer returned, so nothing that F4 was
    # protecting becomes selectable -- the weak candidate is back as a
    # competitor, which is the only role it ever needed.
    registry = dict(admissible)
    decidable = set(routable_registry(admissible))
    if len(decidable) != len(admissible):
        rules.append("F4_ZERO_INPUT_TOOLS_NOT_ROUTABLE")
    ranked = ranked_candidates(text, registry)
    best_cid = ranked[0][2] if ranked else None
    spool: set[str] = set()
    try:
        compiled = dict(gc.compile_goal(text, registry, root))
        pinned_failure = None
    except GoalCompilationFailure as exc:
        compiled, pinned_failure = None, exc

    # F5: a literal route captured several sentences -> compile sentence by sentence
    if compiled is not None and compiled.get("compiler_mode") in _LITERAL_MODES:
        clauses = sentence_clauses(text)
        if len(clauses) >= 2:
            return _compile_clauses(clauses, admissible, root, rules)

    # F11: a multi-step request whose every step is a bound capability is planned as one DAG.
    # The planner (capability_planner) plans it, resolves each cross-step artifact into a
    # $result reference and emits the composition contract the live entry executes.
    planned_dag = plan_capability_dag(text, admissible, root)
    if planned_dag is not None:
        rules.extend(planned_dag["front_compiler"]["rules_applied"])
        planned_dag["front_compiler"] = {"schema": SCHEMA, "rules_applied": list(rules)}
        planned_dag["capability_dag"]["front_compiler"] = {"schema": SCHEMA, "rules_applied": list(rules)}
        return planned_dag

    selected = (compiled or {}).get("selected_capability") if compiled else None
    single_shape = bool(compiled) and compiled.get("compiler_mode") == "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH" and selected

    # An explicit name outranks a scorer that could not see the thing named.
    if single_shape:
        _named = _named_receipt_projection(text, admissible, selected,
                                            request_states_the_capability_name)
        if _named is not None:
            rules.append("F29_NAMED_RECEIPT_PROJECTION_CONSULTED")
            retrieved = _retrieval_first_selection(text, admissible, root, rules)
            if retrieved is not None and retrieved.get("selected_capability") == _named:
                return retrieved
            # F17 retrieves k=3 and disposes by typed admission, so among lexical
            # SIBLINGS it cannot tell which one was asked for: the registry holds
            # bytes_active_query_task_generator_v1 alongside bytes_characteristic_,
            # bytes_discrete_sequence_, bytes_domain_free_, bytes_hblind_,
            # bytes_microkernel_v3_ and bytes_scalar_exact_ variants, and 7 of the
            # first 13 receipt-backed prose goals lost to
            # python.task.acceptance.measured.objective.v1 because the shortlist was
            # ambiguous and F17 selects nothing when it is.  An explicit name IS the
            # disambiguation the ranker lacks.  This was attempted before and broke 7
            # tests in test_live_brain_route_admission_v1.py -- because the naming
            # test counted a repository PATH and an identifier as naming a
            # capability, so it fired on 16 candidates for one ordinary sentence.
            # The predicate now needs the name in the caller's own words, and that
            # sentence names none.  Admission still goes through the typed binder,
            # which is what bounds selection quality.
            named_entry = admissible.get(_named) or {}
            try:
                named_inputs = bind_all_inputs(text, named_entry, root, cycle=0, spool=None)
            except GoalCompilationFailure:
                named_inputs = None
            if named_inputs is not None:
                rules.append("F29_NAMED_RECEIPT_PROJECTION_ADMITTED_BY_CONTRACT")
                return _single(_named, named_entry, named_inputs, 0, {
                    "rule": "F29_NAMED_RECEIPT_PROJECTION_ADMITTED_BY_CONTRACT",
                    "named": _named,
                    "retrieval_was_ambiguous": retrieved is None,
                }, rules)

    if single_shape or compiled is None:
        future = _future_artifacts(text, root)
        # The pool a DECISION may come from.  A catch-all stays in `ranked` as a
        # competitor and in `registry` as a bindable entry, but it is never a
        # candidate this walk may return - that is the whole of F4, applied where
        # the decision is made instead of where the ranking is built.
        # F29 earns back what F4 withholds.  A zero-input tool declares no task,
        # so no part of the sentence can evidence it -- unless the sentence NAMES
        # it, which is precisely the one link F29 accepts for that shape of
        # contract.  Measured: "Run the bytes active query task generator." names
        # bytes_active_query_task_generator_v1 and still lost its route to
        # python.task.acceptance.measured.objective.v1, because F4 had already
        # taken the named capability out of the decidable set.  The converse is
        # the same rule and it is what keeps "Run the thing." refused: a VERB is
        # not a name, so a zero-input tool that is not named stays undecidable.
        selectable = [
            c for c in ranked
            if c[2] in decidable or request_names_capability_id(text, c[2])
        ]
        # F3: a goal that names a file to be produced is served by a tool that can write a file
        preferred = [c for c in selectable if _output_keys(registry[c[2]])] if future else []
        if future and preferred:
            rules.append("F3_ARTIFACT_WRITERS_PREFERRED")
        pool = preferred or selectable
        best = pool[0] if pool else None
        if best is not None and selected != best[2]:
            # F1 binds the best candidate; F22 disposes a same-score TIE by typed admission:
            # candidates tied with the best are one tier (a genuine ambiguity, not a rank gap),
            # tried in rank order, and the first whose inputs the sentence actually states wins.
            #
            # F24: the route must be EXECUTABLE on the sentence as stated.  A candidate whose
            # declared input the sentence never stated was never what was asked - the lexical
            # score is a hint, the words of the request are the decision - so it is skipped and
            # the walk continues down the ranked pool.  A candidate the sentence states
            # AMBIGUOUSLY keeps the request open: the walk stops there and the request fails
            # closed, because two files for one slot is a question, not a choice.  F22's
            # same-score tier stays a tier: within it a sibling may still bind.
            bound: tuple[tuple[int, int, str, dict[str, Any]], dict[str, Any], dict[str, Any]] | None = None
            best_error: GoalCompilationFailure | None = None
            for tier_index, tier in enumerate(_score_tiers(pool)):
                tier_error: GoalCompilationFailure | None = None
                for rank, cand in enumerate(tier):
                    cand_entry = registry[cand[2]]
                    if _is_catch_all(cand_entry):
                        # a capability that binds every sentence is never the decision
                        continue
                    try:
                        cand_inputs = bind_all_inputs(text, cand_entry, root, cycle=0, spool=spool)
                    except GoalCompilationFailure as exc:
                        if _failure_is_unstated(exc):
                            if best_error is None:
                                best_error = exc
                            continue
                        if tier_error is None:
                            tier_error = exc
                        if best_error is None:
                            best_error = exc
                        continue
                    bound = (cand, cand_entry, cand_inputs)
                    if rank == 0 and tier_index == 0:
                        rules.append("F1_BEST_CANDIDATE_BOUND_INSTEAD_OF_FALLTHROUGH")
                    elif tier_index == 0:
                        rules.append("F22_SAME_SCORE_TIE_ADMISSION")
                    else:
                        rules.append("F24_UNSTATED_CANDIDATE_SKIPPED")
                    break
                if bound is not None:
                    break
                if tier_error is not None:
                    # an ambiguous statement keeps the request open: no lower tier may answer it
                    break
            if bound is not None:
                cand, entry, inputs = bound
                if any(str(v).startswith(SPOOL_DIR + "/spool_") for v in inputs.values()):
                    rules.append("F13_INTERMEDIATE_SPOOL_ASSIGNED")
                if any(str(inputs[k]) == str(inputs[j]) for k in inputs if _is_output_key(k, entry) for j in inputs if j != k and j.endswith("_path")):
                    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", cand[2] + ":output_path_equals_an_input_path")
                return _single(cand[2], entry, inputs, cand[0], cand[3], rules)
            # no tied candidate can bind: accept the pinned selection only if it is itself a
            # prose-scored candidate consistent with the goal's artifact; never a fall-through
            consistent = selected in {c[2] for c in pool}
            if not consistent:
                retrieved = _retrieval_first_selection(text, admissible, root, rules)
                if retrieved is not None:
                    return retrieved
                detail = str(getattr(best_error, "detail", "")) if best_error is not None else "no_candidate_binds"
                # F29: when the sentence stated NO contract anywhere and named no
                # capability, the honest diagnosis is that nothing was named -- not
                # the name of whatever candidate happened to rank first.  Measured:
                # "Run the thing." was refused as
                # GOAL_INPUT_BINDING_REQUIRED:shell.command.run:argv:not_stated,
                # which blames a capability the request never mentioned.  A bound
                # contract stays stronger evidence than a name, so this fires only
                # when every candidate failed for want of a stated input.
                if best_error is not None and _failure_is_unstated(best_error) \
                        and not any(request_names_capability_id(text, cid) for cid in admissible):
                    rules.append("F29_REQUEST_NAMED_NOTHING")
                    raise GoalCompilationFailure("GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH",
                                                 best[2] + ":" + detail)
                raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", best[2] + ":" + detail)
        if compiled is None:
            retrieved = _retrieval_first_selection(text, admissible, root, rules)
            if retrieved is not None:
                return retrieved
            raise pinned_failure  # type: ignore[misc]
        if future and not _output_keys(registry[selected]):
            raise GoalCompilationFailure("GOAL_OUTPUT_ARTIFACT_UNSERVED", selected)

    if compiled is None:
        retrieved = _retrieval_first_selection(text, admissible, root, rules)
        if retrieved is not None:
            return retrieved
        raise pinned_failure  # type: ignore[misc]

    # F17 (pinned catch-all): the pinned scorer answers a STRUCTURED sentence with a capability
    # whose only declared inputs are {goal, output_path} - it binds any sentence at all, which is
    # measured, not hypothetical.  When the pinned winner is such a catch-all and a structurally
    # SPECIFIC typed admission exists, the specific one is the answer.  This sits after F1 has had
    # its chance to re-bind a ranked candidate (that is what keeps the reachability results that
    # depended on F1 intact) and it never fires when admission is ambiguous, so an unclear sentence
    # still fails closed instead of being guessed.
    if single_shape and selected:
        from canonical.runtime import capability_selection_retrieval_v1 as _sel

        _declared = _sel.declarations(root).get(selected)
        _names = _sel.required_input_names(admissible.get(selected) or {}, _declared)
        if _names and not _sel.is_specific(_names):
            displaced = _retrieval_first_selection(text, admissible, root, rules)
            if displaced is not None:
                displaced["match_evidence"]["displaced_pinned_selection"] = selected
                displaced["match_evidence"]["displaced_catch_all_inputs"] = _names
                return displaced

    if single_shape and isinstance(compiled.get("inputs"), dict):
        if repair_output_collisions(text, compiled["inputs"], root, entry=registry.get(selected),
                                    cycle=0, spool=spool):
            rules.append("F10_OUTPUT_NEVER_AN_INPUT_FILE")
            if any(str(v).startswith(SPOOL_DIR + "/spool_") for v in compiled["inputs"].values()):
                rules.append("F13_INTERMEDIATE_SPOOL_ASSIGNED")
            for action in compiled.get("actions") or []:
                args = action.get("args") if isinstance(action, dict) else None
                if isinstance(args, dict):
                    for k, v in compiled["inputs"].items():
                        if k in args:
                            args[k] = v
    compiled["front_compiler"] = {"schema": SCHEMA, "rules_applied": rules}
    return compiled
