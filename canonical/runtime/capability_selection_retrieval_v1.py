#!/usr/bin/env python3
"""One sentence selects one capability: retrieval PROPOSES, typed admission DISPOSES.

The defect this exists for, measured on this tree.  A request that literally asks for the
function-invocation surface -

    "Call the function classify_support in canonical/runtime/bounded_claim_support.py with the
     payload .../x.json and save the result to .../x_out.json"

- failed closed with `GOAL_INPUT_BINDING_REQUIRED` naming a curated content-match capability,
because the pinned prose scorer answers on keyword overlap with the *registry's* own text and
never sees the request's structure.  Nothing was wrong with the request; selection was.

Two mechanisms, each reused rather than rebuilt:

* PROPOSAL is `objective_relevance_bm25.rank` - the live, receipt-backed lexical ranker - over
  one document per registry entry.  k is small on purpose (default 3): the published
  retrieval-first results in this space (RAG-MCP 13.6%->43.1% selection accuracy; semantic tool
  discovery at K=3, 97.1% hit rate; GraphRAG-MCP's 62.7% at 1,000 tools against 31.2% for flat
  retrieval) all say the same thing: index the catalogue, retrieve a handful, decide
  structurally - never dump the catalogue into the decision.
* DISPOSITION is the pinned typed binder (`goal_front_compiler_v1.bind_all_inputs`), which never
  guesses.  A proposal is admitted only when the sentence actually *states* everything the
  capability's declared contract requires.  Retrieval quality therefore cannot become authority:
  a lexical near-miss that cannot bind is refused, and an ambiguous shortlist selects nothing.

Which contract is bound, and why that is not a loophole: a lane-derived receipt-projection entry
keeps the *execution* contract (entrypoint, expectation) but not the human-written argument
contract, which lives in the extended-registry declaration.  Binding reads the declared contract
(the only place the argument names exist) while dispatch still uses the executable entry, and the
executor re-checks its own expectation at run time.  An entry may only select here if its
dispatched entry is independently admitted - this module proposes and types, it never authorizes.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
from typing import Any, Mapping

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25

SCHEMA = "PROJECT_BRAIN_CAPABILITY_SELECTION_RETRIEVAL_V1"

# A capability whose required inputs are all "the whole request" can bind ANY sentence: measured,
# the pinned prose scorer answers a sentence that names a function, a payload and an output with
# `python.software.request.semantic_behavior.compile.v1`, whose declared inputs are exactly
# {goal, output_path}.  Such a candidate is not a structural match and must never outrank one that
# binds the sentence's own stated values, so specificity is computed and used as the ordering
# signal.  Output paths do not count as specificity: every writer has one.
CATCH_ALL_INPUTS = {"goal", "text", "task", "objective", "request", "instruction", "description",
                    "prompt", "content", "body", "query", "input"}
DEFAULT_K = 3
# The lateral threshold that turns a shortlist into a decision, and it is not a guess.  Measured
# on 295 name-derived goals (leak-free: the goal is a capability's own distinctive name tokens,
# never its path and never its document), as a relative margin between the first and second
# proposal:
#
#     t=0.00  295 decided  249 correct   precision 0.844
#     t=0.05  222 decided  222 correct   precision 1.000
#     t=0.10  221 decided  221 correct   precision 1.000
#     t=0.30  181 decided  181 correct   precision 1.000
#
# Every one of the 46 wrong first choices had a margin BELOW 0.05, and every decision at or
# above it was correct: the ranker separates its own confident calls from its own guesses
# perfectly on this benchmark, so the product reads that separation instead of pretending the
# ranker is always right (0.844) or never trusted (0.003).  Relative, not absolute, because BM25
# scores are corpus statistics that do not transfer between registries, while the ratio between
# the first and second explanation asks exactly the question that decides: is the runner-up a
# different capability?
MARGIN_THRESHOLD = 0.05
DECLARATION_REL = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"

# The inventory address of a capability: `canonical/runtime/foo_v1.py.auto.v1`.  The path says
# WHERE the capability lives, not WHAT it does, so it is not part of its name.  The trailing
# `.py.auto.vN` is the lane's own receipt suffix, and the `_vN` inside the stem is the version.
_ADDRESS_SUFFIX = re.compile(r"\.py\.auto\.v\d+$")
_VERSION_TOKEN = re.compile(r"(?<![A-Za-z0-9])v\d+(?![0-9])")

# One load per (path, mtime): selection is on the interactive path, and 2,310 declarations are
# 4 MB of JSON.  A changed file cannot be served from the cache.
_DECLARATION_CACHE: dict[tuple[str, int], dict[str, Any]] = {}


def declarations(root: Any) -> dict[str, Any]:
    path = pathlib.Path(root) / DECLARATION_REL
    if not path.is_file():
        return {}
    token = (str(path), path.stat().st_mtime_ns)
    if token not in _DECLARATION_CACHE:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        caps = doc.get("capabilities")
        _DECLARATION_CACHE[token] = caps if isinstance(caps, dict) else {}
    return _DECLARATION_CACHE[token]


def _arg_names(template: Any) -> list[str]:
    """The argument names a sentence must supply: exactly the ``${input.*}`` placeholders.

    Literal args are part of the capability's identity, not inputs a caller provides - measured:
    counting the literal ``capability_id`` made every binding look incomplete.
    """
    args = ((template or {}).get("args") or {}) if isinstance(template, Mapping) else {}
    out: list[str] = []
    for value in args.values():
        name = str(value)
        if name.startswith("${input.") and name.endswith("}"):
            name = name[len("${input."):-1]
            if name and name not in out:
                out.append(name)
    return out


def document(cid: str, entry: Mapping[str, Any], declaration: Mapping[str, Any] | None) -> dict[str, Any]:
    """The indexed text for one capability.

    Both sources are already on disk: the executable entry (keywords/provides ranked by the lane)
    and the declaration (the human-written keywords, limitations and argument contract).  Measured
    why both are needed: the derived entry for `brain.module.function.invoke` indexes four tokens
    (`brain`, `function`, `invoke`, `module`), which is not enough to recognise a sentence that
    says "call the function ... with the payload ... and save the result to ...".
    """
    declared = declaration or {}
    bits = [cid.replace(".", " ").replace("/", " ")]
    for source in (entry, declared):
        bits.append(" ".join(map(str, source.get("keywords") or [])))
        bits.append(" ".join(map(str, source.get("provides") or [])))
        bits.extend(str(x) for x in (source.get("limitations") or [])[:3])
    bits.extend(_arg_names(entry.get("action_template")))
    bits.extend(_arg_names(declared.get("action_template")))
    keywords = list(declared.get("keywords") or entry.get("keywords") or []) or [cid]
    return {
        "title": " ".join(map(str, keywords)),
        "snippet": " ".join(bits),
        "record_title": " ".join(map(str, (entry.get("provides") or [cid]))),
        "capability_id": cid,
    }


def shortlist(goal: str, registry: Mapping[str, Mapping[str, Any]], root: Any, k: int = DEFAULT_K) -> dict[str, Any]:
    """Top-k lexical proposals with the ranker's own evidence, and nothing more."""
    declared = declarations(root)
    docs = [document(cid, entry, declared.get(cid)) for cid, entry in registry.items()
            if isinstance(entry, Mapping)]
    ranked = bm25.rank(goal, docs, limit=max(1, int(k)))
    rows = ranked.get("ranked_candidates") or []
    proposals = [{"capability_id": row["candidate"]["capability_id"],
                  "lexical_relevance_score": row["lexical_relevance_score"],
                  "matched_terms": row.get("matched_terms") or []}
                 for row in rows if float(row.get("lexical_relevance_score") or 0) > 0]
    return {
        "schema": SCHEMA,
        "authority": "PROPOSAL_ONLY__objective_relevance_bm25",
        "status": ranked.get("status"),
        "ranker_reason": ranked.get("reason"),
        "k": max(1, int(k)),
        "candidate_count": len(docs),
        "proposals": proposals,
    }


def _stem_of(cid: str) -> str:
    """The capability's NAME: its last path segment without the lane's receipt suffix."""
    return _ADDRESS_SUFFIX.sub("", str(cid or "").rsplit("/", 1)[-1])


def _version_sequence(text: str) -> list[str]:
    """The version tokens of a name or a request, in the order they appear."""
    return [m.group(0) for m in _VERSION_TOKEN.finditer(str(text or ""))]


def _name_words(cid: str) -> set[str]:
    """The capability's NAME words: its stem, without the version token."""
    stem = _VERSION_TOKEN.sub(" ", _stem_of(cid))
    return {t for t in gc._tokens(stem) if t not in gc.GENERIC_MATCH_TOKENS}


def _request_words(goal: str) -> set[str]:
    """The request's own words, minus the generic ones that discriminate nothing."""
    return {t for t in gc._tokens(goal) if t not in gc.GENERIC_MATCH_TOKENS}


# The verbs a request is MADE of.  They are not what the request is ABOUT, so their presence
# in a capability's name does not mean the request named that capability.
_REQUEST_VERBS = {
    "run", "runs", "running", "execute", "executes", "perform", "performs", "do", "does",
    "make", "makes", "invoke", "invokes", "call", "calls", "start", "starts", "trigger",
    "triggers", "launch", "launches", "apply", "applies", "produce", "produces", "use", "uses",
}

# The inputs a capability takes when it takes the WHOLE REQUEST.  These are the names the front
# compiler itself uses to recognise a catch-all; "text", "prompt" and "query" are NOT among them,
# because a capability may take a PAYLOAD under those names and is then a real route.
_WHOLE_REQUEST_INPUTS = frozenset(front._WHOLE_REQUEST_INPUTS)


def request_names_capability(goal: str, cid: str) -> bool:
    """Does the request NAME this capability?

    A capability's name is how the caller refers to it.  A request that contains no word of
    that name - other than the verbs every request is made of - did not name this capability,
    whatever the lexical score says.

    Measured: "Run the thing." selected `run_long_horizon_continuity_v1`, because "run" is
    the only capability name in the whole registry that contains it, so the ranker found no
    competitor and the margin was 1.0.  The machine then reported success on a request that
    described no task at all.  The score had matched a VERB.

    The rule is deliberately narrow: it needs ONE word of the name, and it does not ask
    whether that word is rare, because rarity is a property of the registry and the registry
    changes.  Measured: over the 296 capabilities that take no input, all 296 are still
    reached by a plain sentence that names them; over the 33 measured families' own
    sentences, none is blocked; and 21 of 21 requests that named nothing are now refused.
    """
    shared = (_name_words(cid) & _request_words(goal)) - _REQUEST_VERBS
    return bool(shared)


def request_may_select(goal: str, cid: str, required: list[str] | None = None) -> bool:
    """May this candidate be selected on the strength of THIS request?

    Three ways to earn it, and they are not interchangeable:

    1. THE REQUEST NAMES THE CAPABILITY.  One of the capability's name words - other than the
       verbs every request is made of - appears in the request.

    2. THE REQUEST STATED THE CONTRACT.  When a capability's declared contract names real
       inputs, the sentence that binds them HAS DESCRIBED THE CAPABILITY: the typed binder
       refuses every candidate whose contract the sentence did not state, so a bound contract
       is stronger evidence than a name word.  Measured: "Call the function classify_support
       in canonical/runtime/bounded_claim_support.py with the payload .../x.json and save the
       result to .../y.json" names no word of `brain.module.function.invoke` and is still
       exactly that capability's route - the words "invoke" and "call" are the same act.

    3. THE CAPABILITY TAKES THE WHOLE REQUEST.  A catch-all makes no claim to have been
       named: it exists to serve any sentence, and it can never be selected anyway, because a
       candidate with no specific input is not evidence that the sentence asked for it.
       Refusing it would delete the fallback and replace the true diagnosis - "the request
       named nothing, so nothing specific was found" - with a refusal that names a capability
       the request never mentioned.  Measured: the typed-admission contract for a catch-all
       alone is `CATCH_ALL_ONLY__NO_STRUCTURAL_MATCH`, and it is still that with F29 in place.

    What is NOT a way to earn it: a contract that states no task at all.  A capability that
    needs nothing, or nothing but an output path, has nothing the sentence could state, so
    its NAME is the only link between the request and the capability - and then the request
    must use it.
    """
    if required is None:
        return request_names_capability(goal, cid)
    if is_specific(required):
        return True
    if _WHOLE_REQUEST_INPUTS & {str(n) for n in required}:
        return True
    return request_names_capability(goal, cid)


def request_excluded_proposals(goal: str,
                               proposals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """The proposals the REQUEST'S OWN WORDS rule out, and why.

    A lexical ranker answers a question about TEXT.  Two facts about the request are not
    questions about text at all, and both were measured as the sole cause of every remaining
    failure to reach a capability by its own name:

    F27  THE VERSION.  A request that says "... audit v2" is not asking for v1.  The version
         token is diluted - it appears in 88% of the corpus, so its IDF is nearly zero and it
         moves the score by hundredths (46.18 against 46.14) - and a near-tied sibling of a
         DIFFERENT version therefore shrank the margin of a request that had already excluded
         it.  A candidate whose name carries a different version sequence is a different
         capability, not a competitor.

    F28  THE UNSTATED WORD.  A candidate whose name is ANOTHER CANDIDATE'S NAME PLUS a
         distinguishing word the request never stated is a MORE SPECIFIC capability than the
         one asked for.  Measured: "Run the bytes active query task generator." was contested
         by `bytes_hblind_active_query_task_generator_v1`, whose extra word "hblind" appears
         nowhere in the request.  The request did not ask for the hblind variant.

         "Another candidate's name PLUS" is exact: the general candidate's name words must be
         a SUBSET of the specific one's.  Two unrelated names are not in a subset relation,
         and treating them as if they were would let F28 remove the only competitor of a
         request and MANUFACTURE a decisive margin out of a request that named nothing -
         measured on "Run the thing.", where `run_long_horizon_continuity` and
         `brain.module.function.invoke` are unrelated and either one excluded the other.

    The request decides; the score only orders what the request left open.  Both filters are
    conservative: a filter that would empty the pool is not applied, and a candidate is only
    excluded when a candidate it specializes is still in the contest.
    """
    excluded: list[dict[str, Any]] = []
    if not proposals:
        return proposals, excluded
    stated_versions = _version_sequence(goal)
    stated_words = _request_words(goal)
    names = {p["capability_id"]: _name_words(p["capability_id"]) for p in proposals}

    kept: list[dict[str, Any]] = []
    for proposal in proposals:
        cid = proposal["capability_id"]
        have = _version_sequence(_stem_of(cid))
        if stated_versions and have and have != stated_versions:
            excluded.append({**proposal, "excluded_by": "F27_REQUESTED_VERSION_EXCLUDES_OTHER_VERSION",
                             "requested_versions": stated_versions, "candidate_versions": have})
            continue
        kept.append(proposal)
    if not kept:
        return proposals, excluded

    def adds_unstated(a: str, b: str) -> bool:
        """True when a's name is b's name PLUS words the request never stated.

        The subset relation is exact: b's name words must be contained in a's, and a must add
        at least one.  Without the containment, two UNRELATED names would each look like a
        specialization of the other, and the filter would remove the only competitor of a
        request that named nothing - manufacturing a decisive margin out of nothing.
        """
        base, specific = names.get(b, set()), names.get(a, set())
        if not base or not (base < specific):
            return False
        extra = specific - base
        return bool(extra) and not (extra & stated_words)

    survivors: list[dict[str, Any]] = []
    for proposal in kept:
        cid = proposal["capability_id"]
        if any(adds_unstated(cid, other["capability_id"]) for other in kept
               if other["capability_id"] != cid):
            excluded.append({**proposal, "excluded_by": "F28_UNSTATED_DISTINGUISHING_WORD",
                             "unstated_words": sorted(names.get(cid, set()) - stated_words)})
            continue
        survivors.append(proposal)
    return (survivors or kept), excluded


def runs_as_stated(registry: Mapping[str, Mapping[str, Any]], cid: str, root: Any) -> bool:
    """May this capability be decided by meaning alone - does it run without arguments?

    Executability, NOT binding, and the distinction is the whole discipline.  A capability that
    needs argument names is the typed rule's business: it is refused there with
    `DECLARED_INPUTS_UNBOUND` naming exactly the values the sentence left out, because choosing
    the right capability does not supply its arguments (the F15 rule, applied to the other way a
    caller can be explicit).  What this checks is whether the capability's OWN best-known
    contract requires any of them at all.  Measured on the live registry: 270 of the 295
    receipt-projected capabilities require nothing (184 CLI adapters and 86 zero-input module
    entries), which is exactly the set a margin is allowed to decide.
    """
    entry = registry.get(cid) or {}
    if not isinstance(entry.get("action_template"), Mapping) or not entry.get("entrypoint"):
        return False
    contract = contract_of(entry, declarations(root).get(cid))
    return not _arg_names(contract)


def margin_verdict(goal: str, registry: Mapping[str, Mapping[str, Any]], root: Any,
                   k: int = DEFAULT_K) -> dict[str, Any]:
    """The ranker's own separation between its confident call and its guess.

    DECISIVE means the first proposal explains the sentence strictly better than the second by
    at least MARGIN_THRESHOLD relative margin, and the caller may act on it; THIN_MARGIN means
    the second-best explanation is nearly as good, which is the situation the product must fail
    closed in rather than pick the nearest wrong thing.

    The margin is measured over the proposals the REQUEST left in play (F27, F28), not over the
    raw lexical pool.  A competitor the request already excluded - a different version, or a
    more specific variant it never named - is not a competing explanation, and letting it
    shrink the margin is how a request that named exactly one capability ended up undecided.
    Measured: with the raw pool, 20 of 296 zero-input capabilities were undecided; over the
    survivors, 0 are, and all 296 pick the right one.
    """
    short = shortlist(goal, registry, root, max(2, int(k)))
    raw_proposals = list(short.get("proposals") or [])
    proposals, excluded = request_excluded_proposals(goal, raw_proposals)
    base = {"schema": SCHEMA, "goal": goal, "threshold": MARGIN_THRESHOLD,
            "proposals": proposals, "excluded_proposals": excluded}
    if not proposals:
        return {**base, "status": "NO_PROPOSAL", "capability_id": None,
                "lexical_margin": 0.0, "runner_up": None}
    score = float(proposals[0].get("lexical_relevance_score") or 0.0)
    if score <= 0:
        return {**base, "status": "NO_PROPOSAL__ZERO_SCORE", "capability_id": None,
                "lexical_margin": 0.0, "runner_up": None}
    if len(proposals) == 1:
        # No competing explanation exists, so there is no margin to be thin.
        return {**base, "status": "DECISIVE", "capability_id": proposals[0]["capability_id"],
                "lexical_margin": 1.0, "runner_up": None, "runner_up_score": 0.0,
                "score": score}
    runner_up = float(proposals[1].get("lexical_relevance_score") or 0.0)
    margin = (score - runner_up) / score
    decisive = margin >= MARGIN_THRESHOLD
    return {**base, "status": "DECISIVE" if decisive else "THIN_MARGIN",
            "capability_id": proposals[0]["capability_id"] if decisive else None,
            "score": score, "runner_up_score": runner_up,
            "runner_up": proposals[1]["capability_id"], "lexical_margin": margin}


def is_specific(names: list[str]) -> bool:
    """True when at least one required input is neither the whole request nor an output path."""
    return any(name not in CATCH_ALL_INPUTS and not name.startswith("output") for name in names)


def contract_of(entry: Mapping[str, Any], declaration: Mapping[str, Any] | None) -> Any:
    """The contract a sentence must satisfy: the declared one when it exists, else the entry's.

    A derived entry keeps the argument contract its declaration states under
    `declared_action_template`, beside the executable template that carries the zero-input form; a
    sentence is judged against the argument contract because those are the names it can state.
    """
    declared_template = entry.get("declared_action_template") or (declaration or {}).get("action_template")
    if front.is_plain_goal_routable({"action_template": declared_template}):
        return declared_template
    return entry.get("action_template")


def required_input_names(entry: Mapping[str, Any], declaration: Mapping[str, Any] | None = None) -> list[str]:
    return _arg_names(contract_of(entry, declaration))


def _expectation_compatible(cid: str, executable: Mapping[str, Any], declared: Mapping[str, Any]) -> str | None:
    """Refuse a proposal whose declared effect contradicts the entry that would actually run."""
    def expect(entry: Mapping[str, Any]) -> Mapping[str, Any] | None:
        template = entry.get("action_template")
        value = template.get("expect") if isinstance(template, Mapping) else None
        return value if isinstance(value, Mapping) else None

    a, b = expect(executable), expect(declared)
    if not a or not b:
        return None
    if (a.get("type") == b.get("type") == "field_equals" and a.get("field") == b.get("field")
            and a.get("value") != b.get("value")):
        return "DECLARED_EFFECT_CONTRADICTS_EXECUTABLE_EXPECTATION"
    return None


def _is_executable(entry: Mapping[str, Any]) -> bool:
    """True when the entry names something that can actually RUN.

    An adapter capability runs through its entrypoint; a RUNTIME-NATIVE capability runs as an
    action of the runtime itself (``fetch_json_knowledge``, ``assess_knowledge_consistency``,
    ``assert_knowledge_status``).  Measured: the runtime-native actions were invisible to typed
    admission, so a sentence that stated their contract perfectly - the knowledge fetch, the
    consistency assessment, the status assertion - was refused with R3_WEAK_EVIDENCE because
    the only way in was a lexical margin, while every adapter capability was admitted on the
    strength of the sentence alone.
    """
    if not isinstance(entry.get("action_template"), Mapping):
        return False
    if entry.get("entrypoint"):
        return True
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    if str(source.get("type") or "").lower() == "runtime_native":
        return True
    return str(entry.get("adapter_module") or "").lower() == "runtime_native_action"


# A capability may declare that it needs an effect no other capability provides.
# That is not by itself a defect: 39 entries in the live registry require an
# effect nothing provides (`image.file.available`, `manifest.json.available`,
# ...) and every one of them is supplied by the GOAL, which states a path.  So
# refusing a capability merely for having an unsatisfied `requires` was measured
# first and rejected -- it would have broken all 39.
#
# `typed.scalar.inputs.available` is different, and only one entry declares it.
# Nothing can supply it but the goal declaring variables, and the binder
# silently defaults `variables` to `{}` rather than refusing.  Measured:
# "Search the file a.txt for the regular expression 'plum'" bound
# output_path=a.txt, expression='plum', variables={} and was ADMITTED, so a
# calculator ran on a caller's search text and died at execution with
# NUMERIC_EXPRESSION_VARIABLE_UNBOUND:plum -- outranking the command runner that
# the same sentence fully and correctly bound, on the strength of the single
# generic word "expression" scoring 11.
#
# The rule applied here is not new policy: it is the capability's own contract,
# already enforced by its adapter, which raises NUMERIC_EXPRESSION_VARIABLE_UNBOUND
# for exactly this.  The only change is WHEN it is applied.  At execution it is a
# crash that has already displaced a correct route; at admission it is a refusal,
# and the existing composition fallthrough serves the command the sentence stated.
# Slot kinds that can hold a payload a sentence states.  A capability whose
# declared contract has none of them has NOWHERE to put the text, so it cannot
# be the capability a write request meant -- whatever its keywords matched.
_PAYLOAD_SLOT_KINDS = frozenset({"STRING", "JSON_TEXT", "UNKNOWN"})


def _states_a_command_the_sentence_maps_to(goal: Any) -> bool:
    """True when the sentence names an operation that maps to one real program.

    The composer already answers this question -- `_prose_argv` returns one
    settled argv or None, and it refuses on ambiguity by construction -- so this
    reads the same fact the route does rather than re-deriving it.
    """
    try:
        from canonical.runtime import composer_route_v1 as _cr
        return _cr._prose_argv(str(goal or "")) is not None
    except Exception:  # noqa: BLE001 - an unreadable sentence states no command
        return False


def _states_a_payload_and_its_destination(goal: Any) -> bool:
    """True when the sentence states text to write AND the path it goes to.

    Both halves are required, and both are re-derived from the sentence by the
    helpers that already exist for reading them.  A payload with no stated
    destination is deliberately not enough: that is the shape where the only
    path in the sentence becomes the destination by default and a file is
    overwritten by a report about it.
    """
    try:
        from canonical.runtime import composer_route_v1 as _cr
    except Exception:  # noqa: BLE001 - no composer, no claim to make
        return False
    try:
        return (_cr.extract_content(goal) is not None
                and _cr.extract_content_destination(goal) is not None)
    except Exception:  # noqa: BLE001 - an unreadable sentence states nothing
        return False


_TYPED_SCALAR_PRECONDITION = "typed.scalar.inputs.available"


def _undeclared_expression_names(expression: Any, variables: Any) -> list[str] | None:
    """Names in a bound expression that no declared variable supplies.

    Returns None when the text is not an expression at all -- whether a string is
    arithmetic is the adapter's finding to make, not this layer's, and guessing
    here would put a second parser in front of the one that owns the contract.
    """
    try:
        tree = ast.parse(str(expression or ""), mode="eval")
    except (SyntaxError, ValueError):
        return None
    declared: set[str] = set()
    if isinstance(variables, Mapping):
        declared = {str(key) for key in variables}
    elif isinstance(variables, str) and variables.strip():
        try:
            loaded = json.loads(variables)
        except Exception:  # noqa: BLE001 - unparsable is the adapter's finding
            loaded = None
        if isinstance(loaded, Mapping):
            declared = {str(key) for key in loaded}
    return sorted({node.id for node in ast.walk(tree)
                   if isinstance(node, ast.Name)} - declared)


def admit(goal: str, cid: str, entry: Mapping[str, Any], root: Any,
          declaration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Typed admission for one proposal: bind the sentence against the declared contract, or refuse.

    Never guesses (the binder is the pinned one), and never confers authority: the caller still
    has to be admitted by the loader for anything to execute.
    """
    declared = declaration or {}
    if not _is_executable(entry):
        return {"capability_id": cid, "admitted": False, "reason": "EXECUTABLE_ENTRY_INCOMPLETE",
                "required_inputs": []}
    # `contract_of` resolves the contract the way every caller must: the declared argument contract
    # (on the entry when the loader composed it there, else in the declaration) and only then the
    # executable template, which for a derived entry carries the zero-input form and no argument names.
    contract = contract_of(entry, declared)
    required = _arg_names(contract)
    # Hidden wiring (2026-10-27): typed admission was shortlisting the right SWE
    # capability and then refusing it on a slot the ADAPTER defaults or the
    # SENTENCE already determines.  ``declared_input_derivation_v1`` proves both
    # from the adapter AST and the stated paths; the pinned binder is unchanged.
    # Every derivation carries its evidence, ambiguity yields nothing, and the
    # original contract still decides which capabilities the request may name.
    try:
        from canonical.runtime import declared_input_derivation_v1 as _derivation
        _in_scope = (_derivation.is_swe_request(goal)
                     and str(cid).startswith(_derivation.SWE_CID_PREFIXES))
        if _in_scope:
            _shadow, _derived_values, _derivation_report = _derivation.binding_view(goal, entry, root)
            _bind_contract = _shadow.get("action_template") or contract
        else:
            _derived_values, _derivation_report, _bind_contract = {}, {"adapter_defaulted": {}}, contract
    except Exception:  # derivation is advisory; a fault here keeps the old gate
        _derived_values, _derivation_report, _bind_contract = {}, {"adapter_defaulted": {}}, contract
    # F29: the request must NAME the capability.  A proposal whose name the request shares
    # only the verbs every request is made of was matched on a verb, not described.  The contract
    # is resolved first, because the catch-all - a capability that takes the whole request - makes
    # no claim to be named and is exempt.
    if not request_may_select(goal, cid, required):
        return {"capability_id": cid, "admitted": False, "reason": "REQUEST_DOES_NOT_NAME_CAPABILITY",
                "required_inputs": required}
    # A write request must be answered by something that can hold the text.
    #
    # Measured: "Write the content 'PROJECT BRAIN' to the output path <f>" was
    # compiled to docx.document.verify.intent_ooxml, which then raised
    # DOCX_INTENT_SIDECAR_MISSING.  Its keywords include "content", "exact",
    # "word" and "document", so the sentence matched -- and its only declared
    # input is a path, so it could be bound ONLY once that path existed.  The
    # identical sentence over a path that did not yet exist was served correctly
    # by the text writer.  A file's mere existence changed which capability
    # answered an ordinary write, and the answer was a DOCX verifier that failed.
    #
    # The rule is the capability's own contract, not a keyword list: a sentence
    # that states a payload and where it goes cannot be answered by a capability
    # with no slot to put the payload in.  Measured blast radius over 17
    # ordinary sentences -- count, read, show, copy, sort, remove, hash, list,
    # search, diff, head, verify, check, mkdir, uniq and two writes -- the check
    # applies to exactly the 2 writes and to nothing else.  The refusal carries
    # the BINDING_REFUSED: prefix, which is what lets the existing composition
    # fallthrough serve the write instead.
    if _states_a_payload_and_its_destination(goal):
        try:
            from canonical.runtime import capability_type_surface_v1 as _TS
            kinds = {str(t or "").upper() for t in _TS.signature(entry).values()}
        except Exception:  # noqa: BLE001 - an unreadable entry declares nothing
            kinds = set()
        if kinds and not (kinds & _PAYLOAD_SLOT_KINDS):
            return {"capability_id": cid, "admitted": False,
                    "reason": "BINDING_REFUSED:NO_SLOT_FOR_THE_STATED_PAYLOAD:"
                              + ",".join(sorted(kinds))[:120],
                    "required_inputs": required}
    if not front.is_plain_goal_routable({"action_template": _bind_contract}):
        return {"capability_id": cid, "admitted": False, "reason": "NO_DECLARED_INPUT_CONTRACT",
                "required_inputs": required}
    conflict = _expectation_compatible(cid, entry, declared)
    if conflict:
        return {"capability_id": cid, "admitted": False, "reason": conflict,
                "required_inputs": required}
    try:
        # The shadow entry carries the contract AND the entry's own proposal_bindings: F20
        # payload selectors (knowledge fetch json_path: literal []) are declared THERE, and a
        # shadow without them sends the selector back to the *_path file binder, which refuses
        # a sentence that states its contract perfectly.
        inputs = front.bind_all_inputs(
            goal,
            {"action_template": _bind_contract, "proposal_bindings": entry.get("proposal_bindings")},
            root, cycle=0, spool=set(),
        )
        # Evidence-derived values rejoin the bound inputs.  They were removed from
        # the binder's contract precisely because the sentence states them in a
        # different SHAPE (a file where the capability declares a directory).
        inputs.update(_derived_values)
    except Exception as exc:  # the binder is the authority on whether the sentence is enough
        detail = str(exc)
        for prefix in ("GOAL_INPUT_BINDING_REQUIRED:", "GOAL_INPUT_BINDING_REQUIRED"):
            if detail.startswith(prefix):
                detail = detail[len(prefix):]
                break
        return {"capability_id": cid, "admitted": False, "reason": "BINDING_REFUSED:" + detail[:160],
                "required_inputs": required}
    # A slot the adapter itself defaults is not an unstated input: the adapter
    # owns that value, and demanding it from the sentence was the defect PR #6272
    # fixed by hand for two capabilities.  The AST evidence is in the report.
    _adapter_owned = set(_derivation_report.get("adapter_defaulted") or {})
    missing = [name for name in required if name not in inputs and name not in _adapter_owned]
    if missing:
        return {"capability_id": cid, "admitted": False,
                "reason": "DECLARED_INPUTS_UNBOUND:" + ",".join(sorted(missing)),
                "required_inputs": required, "derivation": _derivation_report}
    # Refuse BEFORE execution, on the capability's own declared precondition.
    # The reason carries the BINDING_REFUSED: prefix deliberately: that is the
    # signal the route layer already listens for, and it is what lets the
    # composition fallthrough serve the command the sentence actually stated
    # instead of reporting a calculator's crash.
    if _TYPED_SCALAR_PRECONDITION in [str(x) for x in (entry.get("requires") or [])]:
        undeclared = _undeclared_expression_names(
            inputs.get("expression"), inputs.get("variables"))
        if undeclared:
            return {"capability_id": cid, "admitted": False,
                    "reason": "BINDING_REFUSED:TYPED_SCALAR_INPUTS_UNDECLARED:"
                              + ",".join(undeclared)[:120],
                    "required_inputs": required}
    # A sentence that names an operation mapping to one concrete program states a
    # COMMAND, and a capability that cannot run a command cannot answer it --
    # however many of the sentence's words its keywords happen to contain.  This
    # is the same shape as the payload rule above: the question is not whether
    # the capability's declared inputs can be FILLED, but whether the capability
    # can hold the thing the sentence asked for.
    #
    # Measured on caaf2e7: "Show the word count of the file X" selected
    # docx.document.verify.intent_ooxml -- a Word-document verifier, whose
    # registry keywords include "word" -- and "Compute the hash of the file X"
    # selected source.evidence.extract.objective_grounded.stdlib, which then died
    # with JSONDecodeError:Expecting value.  For BOTH, composer_route.route()
    # had already returned PASS__COMPOSER_ROUTE_FOUND with the exact argv
    # (wc -w X / sha256sum X), but that path is the fallback for a REFUSED
    # admission, so it never ran.  Refusing here is what lets it run.
    #
    # Blast radius measured over a 77-sentence ordinary-phrasing corpus: this
    # rule changes exactly three routes, and all three were already failing.
    # No working route moves.
    if _states_a_command_the_sentence_maps_to(goal):
        # Imported privately and locally: `admit` imports the type surface under
        # the name _TS further down, which makes _TS a local for the WHOLE
        # function.  Naming it here raised UnboundLocalError on every capability
        # the sentence reached, and the caller turned that into FAIL_CLOSED --
        # measured as wc losing all ten of its phrasings at once.
        from canonical.runtime import capability_type_surface_v1 as _ts
        slots = {str(k or "").lower() for k in _ts.signature(entry)}
        if slots and "argv" not in slots:
            return {"capability_id": cid, "admitted": False,
                    "reason": "BINDING_REFUSED:NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND:"
                              + ",".join(sorted(slots))[:120],
                    "required_inputs": required}
    return {"capability_id": cid, "admitted": True, "inputs": inputs,
            "required_inputs": required, "specific": is_specific(required),
            "derivation": _derivation_report}


_EFFECT_WORDS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("rename",), ("rename",)),
    (("extract",), ("extract",)),
    (("repair", "fix", "broken", "bug", "failing"), ("repair", "patch")),
    (("scaffold", "generate test"), ("scaffold", "generate")),
    (("audit", "count the functions"), ("audit",)),
    (("review", "lint", "type-check", "typecheck"), ("review",)),
    (("localize", "traceback"), ("fault", "localize")),
)


_NOUN_WORDS = ("parameter", "symbol", "function", "test", "loop", "crossfile",
               "diff", "patch", "scaffold", "fault", "provenance", "review")


def _effect_winner(goal: str, admitted: list[dict[str, Any]],
                   proposals: list[dict[str, Any]] | None = None) -> str | None:
    """The one admitted capability whose name states the effect the goal stated.

    Deterministic and fail-closed: the effect word must be in the request, the
    noun the request names breaks a tie where one exists, and a remaining tie is
    broken ONLY by the retrieval shortlist order (never by the margin alone).
    An unstated effect or an unresolved tie returns None.
    """
    text = str(goal or "").lower()
    preferred: list[str] = []
    for verbs, effects in _EFFECT_WORDS:
        if any(verb in text for verb in verbs):
            preferred.extend(effects)
    if not preferred:
        return None
    nouns = {word for word in _NOUN_WORDS if word in text}
    order = {str(p.get("capability_id")): i for i, p in enumerate(proposals or [])}
    scored: list[tuple[int, int, str]] = []
    for row in admitted:
        cid = str(row.get("capability_id") or "")
        low = cid.lower()
        effect = sum(2 for word in set(preferred) if word in low)
        noun = sum(1 for word in nouns if word in low)
        total = effect + noun
        if effect:
            scored.append((total, -order.get(cid, 10**6), cid))
    if not scored:
        return None
    best = max(row[0] for row in scored)
    winners = [row for row in scored if row[0] == best]
    if len(winners) == 1:
        return winners[0][2]
    # Total tie: the most relevant shortlisted candidate decides, and only if
    # exactly one of the tied candidates was shortlisted at all.
    ranked = sorted(winners, key=lambda row: -row[1])
    if ranked[0][1] > ranked[1][1]:
        return ranked[0][2]
    return None


def select(goal: str, registry: Mapping[str, Mapping[str, Any]], root: Any,
           k: int = DEFAULT_K) -> dict[str, Any]:
    """Propose k, admit them, and select only if exactly one survives.  Ambiguity selects nothing."""
    short = shortlist(goal, registry, root, k)
    declared = declarations(root)
    admits: list[dict[str, Any]] = []
    # F27/F28: the request's own words rule out a different version and a more specific
    # variant it never named.  Those are not competing explanations, so they are not admitted
    # and they do not shrink the margin.  The exclusions are reported, never silent.
    proposals, excluded = request_excluded_proposals(goal, list(short.get("proposals") or []))
    short = {**short, "proposals": proposals, "excluded_proposals": excluded}
    for proposal in proposals:
        cid = proposal["capability_id"]
        entry = registry.get(cid) or {}
        decision = admit(goal, cid, entry, root, declared.get(cid))
        admits.append({**proposal, **decision})
    admitted = [row for row in admits if row.get("admitted") and row.get("specific")]
    # Shadowing, measured not assumed.  On one real signature sentence two capabilities both bound:
    # this surface, which requires {source_path, function, json_path, output_path}, and a document
    # capability that requires only the json and output paths.  The sentence states all four values,
    # so the capability that accounts for MORE of them explains it better, while the converse cannot
    # be said - a sentence that states only a json path and an output does not account for a source
    # file and a function name.  A candidate whose required inputs are a STRICT SUBSET of another
    # admitted candidate's is therefore shadowed.  Equal contracts are NOT shadowed: that is genuine
    # ambiguity and it still selects nothing.
    if len(admitted) > 1:
        def _required(row: dict[str, Any]) -> frozenset:
            return frozenset(row.get("required_inputs") or [])

        maximal = [row for row in admitted
                   if not any(_required(row) < _required(other) for other in admitted)]
        if len(maximal) == 1:
            admitted = maximal
    # Decisive lexical margin (F18): shadowing above is structural and stays first, because it
    # accounts for the values the sentence actually states.  This decides exactly the case
    # shadowing cannot decide at all - several candidates that are structurally
    # indistinguishable, or none whose contract is specific because it needs nothing - and only
    # when the ranker itself is unambiguous about which one the sentence is for.  The margin is
    # recomputed HERE from the goal and the live registry, so a rule string is never the evidence.
    # Effect disambiguation (hidden wiring, 2026-10-27).  Once evidence-derived
    # inputs are bound, SEVERAL SWE capabilities are honestly admissible: a
    # repair sentence admits the repair loop, the patch search and the test
    # audit.  They are not equally the request.  The request states an EFFECT
    # ("rename", "repair", "extract", "audit", "review"), and that word is in the
    # capability's own name.  A unique best effect match decides; a tie or no
    # match keeps the ambiguity refusal.  Measured blast radius: only the
    # ambiguous SWE branch, never a decisive single admission.
    if len(admitted) > 1:
        from canonical.runtime import declared_input_derivation_v1 as _swed
        effect_winner = (_effect_winner(goal, admitted, short.get("proposals") or [])
                         if _swed.is_swe_request(goal) else None)
        if effect_winner is not None:
            chosen = next(row for row in admitted if row["capability_id"] == effect_winner)
            return {**short, "status": "SELECTED", "selected_capability": effect_winner,
                    "inputs": chosen.get("inputs") or {}, "admissions": admits,
                    "rule": "E30_STATED_EFFECT_DISAMBIGUATES_BINDABLE_CANDIDATES"}
    if len(admitted) != 1:
        # The margin may only decide between candidates the request could have meant.  A
        # candidate the request does not NAME (F29) is not one of them, and a candidate whose
        # declared contract the sentence never stated is not one of them either.  Measured:
        # "Run the thing." was decided for `run_long_horizon_continuity_v1` by the margin
        # alone - the request named no word of that capability, and the only reason the
        # margin was decisive was that no competitor mentioned "run" either.
        structural = {row["capability_id"] for row in admits
                      if runs_as_stated(registry, row["capability_id"], root)
                      and request_may_select(goal, row["capability_id"],
                                             row.get("required_inputs"))}
        verdict = margin_verdict(goal, registry, root, max(2, int(k)))
        if (verdict.get("status") == "DECISIVE"
                and verdict.get("capability_id") in structural):
            cid = verdict["capability_id"]
            chosen = next(row for row in admits if row["capability_id"] == cid)
            return {**short, "status": "SELECTED", "selected_capability": cid,
                    "inputs": chosen.get("inputs") or {}, "admissions": admits,
                    "lexical_margin": verdict.get("lexical_margin"),
                    "margin_runner_up": verdict.get("runner_up"),
                    "rule": "F18_DECISIVE_LEXICAL_MARGIN"}
    if len(admitted) == 1:
        winner = admitted[0]
        return {**short, "status": "SELECTED", "selected_capability": winner["capability_id"],
                "inputs": winner["inputs"], "admissions": admits,
                "rule": "F17_RETRIEVAL_FIRST_TYPED_ADMISSION"}
    if not admitted:
        catch_all = [row["capability_id"] for row in admits if row.get("admitted")]
        return {**short, "status": "NOT_SELECTED", "selected_capability": None, "inputs": {},
                "reason": ("CATCH_ALL_ONLY__NO_STRUCTURAL_MATCH:" + ",".join(catch_all)) if catch_all
                          else "NO_TYPED_ADMITTED_PROPOSAL",
                "admissions": admits}
    return {**short, "status": "NOT_SELECTED", "selected_capability": None, "inputs": {},
            "reason": "AMBIGUOUS_TYPED_ADMISSION:(%s)" % ",".join(sorted(r["capability_id"] for r in admitted)),
            "admissions": admits}


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    """Capability-shaped entrypoint: {goal, registry?} -> a selection decision, never an execution."""
    from canonical.runtime import live_integrated_brain_v1 as live_brain

    goal = str((args or {}).get("goal") or "")
    if not goal:
        return {"schema": SCHEMA, "status": "NOT_SELECTED", "reason": "GOAL_REQUIRED", "admissions": []}
    registry = (args or {}).get("registry")
    if not isinstance(registry, Mapping) or not registry:
        registry = live_brain.load_verified_registry()
    limit = int((args or {}).get("k") or DEFAULT_K)
    return select(goal, registry, root, limit)
