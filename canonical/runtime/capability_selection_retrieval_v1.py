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

import json
import pathlib
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
    """
    short = shortlist(goal, registry, root, max(2, int(k)))
    proposals = list(short.get("proposals") or [])
    base = {"schema": SCHEMA, "goal": goal, "threshold": MARGIN_THRESHOLD,
            "proposals": proposals}
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


def admit(goal: str, cid: str, entry: Mapping[str, Any], root: Any,
          declaration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Typed admission for one proposal: bind the sentence against the declared contract, or refuse.

    Never guesses (the binder is the pinned one), and never confers authority: the caller still
    has to be admitted by the loader for anything to execute.
    """
    declared = declaration or {}
    if not isinstance(entry.get("action_template"), Mapping) or not entry.get("entrypoint"):
        return {"capability_id": cid, "admitted": False, "reason": "EXECUTABLE_ENTRY_INCOMPLETE"}
    # `contract_of` resolves the contract the way every caller must: the declared argument contract
    # (on the entry when the loader composed it there, else in the declaration) and only then the
    # executable template, which for a derived entry carries the zero-input form and no argument names.
    contract = contract_of(entry, declared)
    if not front.is_plain_goal_routable({"action_template": contract}):
        return {"capability_id": cid, "admitted": False, "reason": "NO_DECLARED_INPUT_CONTRACT"}
    conflict = _expectation_compatible(cid, entry, declared)
    if conflict:
        return {"capability_id": cid, "admitted": False, "reason": conflict}
    try:
        inputs = front.bind_all_inputs(goal, {"action_template": contract}, root, cycle=0, spool=set())
    except Exception as exc:  # the binder is the authority on whether the sentence is enough
        detail = str(exc)
        for prefix in ("GOAL_INPUT_BINDING_REQUIRED:", "GOAL_INPUT_BINDING_REQUIRED"):
            if detail.startswith(prefix):
                detail = detail[len(prefix):]
                break
        return {"capability_id": cid, "admitted": False, "reason": "BINDING_REFUSED:" + detail[:160]}
    required = _arg_names(contract)
    missing = [name for name in required if name not in inputs]
    if missing:
        return {"capability_id": cid, "admitted": False,
                "reason": "DECLARED_INPUTS_UNBOUND:" + ",".join(sorted(missing))}
    return {"capability_id": cid, "admitted": True, "inputs": inputs,
            "required_inputs": required, "specific": is_specific(required)}


def select(goal: str, registry: Mapping[str, Mapping[str, Any]], root: Any,
           k: int = DEFAULT_K) -> dict[str, Any]:
    """Propose k, admit them, and select only if exactly one survives.  Ambiguity selects nothing."""
    short = shortlist(goal, registry, root, k)
    declared = declarations(root)
    admits: list[dict[str, Any]] = []
    for proposal in short["proposals"]:
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
    if len(admitted) != 1:
        structural = {row["capability_id"] for row in admits
                      if runs_as_stated(registry, row["capability_id"], root)}
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
