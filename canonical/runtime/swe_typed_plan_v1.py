"""Scoped typed-SWE execution plan for the live front door (hidden-tool wiring).

Measured 2026-10-27.  ``capability_selection_retrieval_v1.select`` already
shortlists, admits and (for a stated effect) disambiguates a software-engineering
capability from a human sentence, and ``declared_input_derivation_v1`` already
proves the missing declared inputs from stated evidence.  But ``select()`` is a
*proposal* surface: the live door ``live_brain_route_admission_v1.solve`` still
routes primarily through the pinned lexical compiler, which sends ordinary SWE
sentences to PDF/document converters.  This module is the missing wire: it turns
a DECISIVE typed selection into a fully-bound, executable ``compiled`` plan that
re-enters the SAME ``solve`` gate chain (route admission, execution, tool truth,
promised artifact, source change, observed effect).  Nothing runs here directly.

Route order (why this is REUSE/ADAPT, not a new primitive): the selector, the
derivation, the type surface, the binder and the whole observation gate chain
already exist.  This module only composes them and fixes two shape mismatches the
probes measured:

  * the derived/ adapter-defaulted slots must be removed from the EXECUTABLE
    template (else ``_render_template`` raises GOAL_INPUT_BINDING_REQUIRED on a
    slot the adapter defaults), but DERIVED slots must KEEP their bound values
    (else the adapter gets TEST_PATHS_REQUIRED).  ``binding_view``'s shadow is
    built for BINDING; this builds a second, execution-only template.
  * an ``output_path`` bound onto a stated SOURCE file would be overwritten by a
    report, corrupting the module.  It is moved to a fresh, deterministic report
    path in the stated source directory.  A stated report path is never touched.

Authority: NONE. Credit: 0. Model dependency: 0. Incremental spend: $0.
"""
from __future__ import annotations

import pathlib
import re
from typing import Any, Mapping

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime import goal_compiler
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_integrated_brain_v1 as live_brain

SCHEMA = "PROJECT_BRAIN_SWE_TYPED_PLAN_V1"

# Hidden-tool wiring, measured 2026-10-28.  Human SWE sentences name an EFFECT
# ("find every caller", "extract the function", "lint", "type-check").  The
# capabilities that serve those effects already exist in the registry and bind
# and execute honestly (e.g. python.source.symbols.index.ast produces a real
# ``callers_of`` map), but the lexical BM25 shortlist buries them under path-
# named and wrong-domain rows, and the narrow SWE verb list never lets the typed
# retry fire for them.  §9 of COMPOSITION_LEVERAGE: when a relation can't be
# derived from names, ENUMERATE the candidate space and let execution/admission
# be the oracle.  Candidates are derived from the registry's OWN declared
# keywords (data-driven, not a hardcoded id table); ``admit()`` stays the oracle;
# EXACTLY ONE admitted+specific candidate is decisive; ambiguity => fail closed.

_FAMILIES: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    # (goal triggers, registry-keyword terms to enumerate candidates, required effect token in cid)
    (("move the function", "move the class", "move symbol", "relocate function", "relocate class"),
     ("move_symbol", "relocate symbol"), "move_symbol"),
    (("add a parameter", "add parameter", "new parameter"),
     ("add_parameter", "signature evolution"), "source.add_parameter"),
    (("add a function", "implement a function", "implement function", "create a function"),
     ("implement_function_spec", "function specification"), "implement_function_spec"),
    (("regression test that would have caught", "add a regression test"),
     ("python.tests.regression.synthesized",), "choreograph"),
    (("caller", "who calls", "call site", "call graph", "find every call"),
     ("caller", "call graph", "who calls"), "symbol"),
    # Measured 2026-10-29: "Show the last three git commits" is the plainest thing a
    # software engineer asks, and the machine had no git capability at all -- it
    # returned PASS through an inventory row (see live_brain_route_admission_v1.
    # inventory_source_path).  The capability now exists (git.repository.operate.v1);
    # this entry is what lets a stated git OPERATION reach it, by the same
    # enumerate-and-let-admission-be-the-oracle route the caller family uses.
    # Triggers are deliberately narrow.  Measured 2026-10-29: with a bare "branch"
    # trigger, "Branch out the new feature into three modules" bound op=branch and
    # returned PASS for a `git branch` listing -- a false PASS of exactly the class
    # this file exists to remove.  A metaphor is not a repository operation, so the
    # trigger is the PLURAL noun or the explicit command, never the bare verb.
    (("git", "commit the", "last commit", "commits", "blame", "branches",
      "who wrote", "working tree", "staged changes"),
     ("git", "commit", "history", "repository"), "git"),
)
_FAMILY_SWE_PREFIXES = ("python.", "code.", "software.", "test.", "orchestration.verify.",
                        "git.")


GIT_FAMILY_TOKEN = "git"


def stated_family_token(goal: str) -> str | None:
    """The effect token of the family this sentence STATES, or ``None``.

    Cheap enough for the front door: one pass over ``_FAMILIES`` triggers and no
    registry read.  The door uses it to decide whether a typed plan is
    AUTHORITATIVE for this sentence or merely a retry candidate.
    """
    fam = _family_terms(goal)
    return fam[1] if fam else None


# A coordinating junction starts a NEW clause, and a family trigger inside a
# subordinate clause is not what the sentence asked for.  Measured 2026-10-31:
# "Add a parameter qty with a default value to the function line_total in X and
# update every caller so behaviour is unchanged" contains "caller", so the caller
# family claimed AUTHORITY over an add-a-parameter request, its single admitted
# candidate was the symbol index, and R10 then rejected the plan because a
# caller inventory does not deliver a signature change -- 4 of 28 tasks that a
# lower-bound reading of the same registry does serve.  The triggering noun is
# in the second clause: the sentence's own governing clause decides its effect.
_CLAUSE_BREAK = re.compile(r"(?:[.;!?]|,\s*$|\s+(?:and|then|so|but)\s+)", re.I)


def _governing_clause(text: str) -> str:
    """The clause that carries the sentence's request (its first clause)."""
    parts = [p for p in _CLAUSE_BREAK.split(str(text or "")) if p and p.strip()]
    return parts[0] if parts else ""


def _family_hits(goal: str) -> tuple[tuple[str, ...], tuple[str, ...], str] | None:
    """(the trigger phrases the sentence states, candidate terms, effect token)."""
    # Paths and quoted values are task data, not evidence of an effect family.
    prose = front.prose_only(str(goal or ""))
    head = _governing_clause(prose.lower())
    for triggers, terms, token in _FAMILIES:
        # A guard that names "update every caller" and "rename " by hand is a
        # curated condition on the sentences this file must generalise over; the
        # governing clause decides it for every family and every sentence:
        # "Add a parameter qty ... and update every caller" states a signature
        # change, "Rename the function f to g" states a rename, and in both the
        # family noun sits in a clause that is not the request.
        hits = tuple(t for t in triggers if t in head)
        if hits:
            return hits, terms, token
    return None


def _family_terms(goal: str) -> tuple[tuple[str, ...], str] | None:
    hit = _family_hits(goal)
    return (hit[1], hit[2]) if hit else None


def is_swe_request(goal: str) -> bool:
    """An explicit software-engineering request: the base verb list OR a stated
    SWE effect family (caller-finding etc.).  Broadening is confined to the typed
    RETRY path; the pinned lexical compiler and the ``executed`` guard are
    untouched.  Verified: the three pinned front-door refusals stay non-SWE."""
    if derivation.is_swe_request(goal):
        return True
    return _family_terms(goal) is not None


def _execution_template(entry: Mapping[str, Any], removed: set[str],
                        extra_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Copy the adapter's declared template, dropping ONLY adapter-defaulted
    ``${input.*}`` placeholders.  Slots with a bound value (including derived
    ones) are kept so the adapter still receives them at run time."""
    template = dict(entry.get("action_template") or {})
    args = dict(template.get("args") or {})
    for key in list(args):
        value = args[key]
        if key in removed and isinstance(value, str) and "${input." in value:
            args.pop(key, None)
    if extra_inputs and extra_inputs.get("synthesize_regression_test") is True:
        args["synthesize_regression_test"] = True
    template["args"] = args
    return template


def _fresh_output_path(goal: str, root: pathlib.Path, inputs: Mapping[str, Any]) -> str | None:
    """If ``output_path`` was bound onto a stated source file, relocate it to a
    fresh report path in the stated source directory.  Never overwrite a source.

    Evidence: the stated source directory (or the parent of the single stated
    source file).  Deterministic name; the promised-artifact gate independently
    checks that the file is non-empty, so inventing a passing path proves nothing.
    """
    stated = set(derivation.stated_existing_files(goal, root))
    current = inputs.get("output_path")
    if not isinstance(current, str) or current not in stated:
        return None
    # Only a file the sentence treats as code is a dangerous output target.
    if not current.endswith((".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".rb")):
        return None
    source_root = inputs.get("source_root")
    if isinstance(source_root, str) and source_root and (root / source_root).is_dir():
        parent = source_root
    else:
        parent = str(pathlib.PurePosixPath(current).parent)
    if not parent or not (root / parent).is_dir():
        return None
    return str(pathlib.PurePosixPath(parent) / "typed_swe_report.json")


def implementation_effect_error(goal: str, capability_ids, registry: Mapping[str, Any]) -> str | None:
    """A necessary effect check, NOT proof an implementation is correct.

    Scope: explicit implementation imperatives in software requests. Paths and
    quoted literals are values, not imperative verbs. Report/index/test-selection
    effects cannot discharge this request even when every input binds. Reuse the
    front compiler's value stripping and the registry's declared effect contracts.
    Unknown implementation contracts fail closed; existing acceptance checks must
    still judge any source-writing route that passes this preflight.
    """
    from canonical.runtime import goal_front_compiler_v1 as front
    prose = front.prose_only(goal).lower()
    if re.search(r"\b(?:find\s+every\s+caller|who\s+calls)\b", prose):
        if not any("symbol" in str(c).lower() for c in capability_ids):
            return "R10_CALLER_QUERY_EFFECT_UNSERVED"
    if re.search(r"\badd\s+(?:a\s+)?regression\s+test\b", prose) and re.search(r"\b(?:fix|repair)\b", prose):
        has_reg_cap = any(
            (((registry.get(str(c)) or {}).get("action_template") or {}).get("args") or {}).get("synthesize_regression_test") is True
            for c in capability_ids
        )
        if not has_reg_cap:
            return "R10_REGRESSION_TEST_EFFECT_UNSERVED"
    imperative = re.search(
        r"(?:^|[.;\n]|\bthen\b|\band\b)\s*"
        r"(?:(?:please|first|next)\s+|(?:can|could|would)\s+you\s+(?:please\s+)?)?"
        r"(?:implement\b|develop\b|build\b|"
        r"add\s+(?:(?:a|an|the|new)\s+)*[\w -]{0,60}"
        r"\b(?:function|method|feature|endpoint|class|api)\b)", prose)
    software = re.search(r"\b(?:python|software|code|function|method|feature|endpoint|class|api)\b", prose)
    if not imperative:
        return None
    if not software:
        from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES
        software = any(path.suffix.lower() in SOURCE_SUFFIXES
                       for _raw, path in goal_compiler._repo_paths(goal, live_brain.ROOT))
    if not software:
        return None
    # These are actual registry effect namespaces, not keyword relevance or id
    # substrings such as 'patch' (which could mean a report-only patch search).
    material = ('.source.write.', '.refactor.', '.edit.', '.issue_to_pr.', '.feature.implement.')
    for cid in capability_ids:
        entry = registry.get(str(cid)) or {}
        if any(any(part in str(effect) for part in material)
               for effect in entry.get('provides', [])):
            return None
    return 'R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED'


def _effect_consistent(goal: str, cid: str, entry: Mapping[str, Any] | None = None) -> bool:
    """Reuse the selector's OWN E30 effect vocabulary as an admission gate.

    Measured 2026-10-27: ``select`` admits by DECLARED-INPUT CONTRACT, not by
    effect.  With a single bindable proposal (F17) the E30 effect disambiguator
    never runs, so "Type-check the file X" bound to a repair choreographer
    (``software.repair.choreograph.crossfile.v1``) that no-op'd to a false PASS
    with the source unchanged.  An effect-inconsistent plan must be refused so
    the caller keeps its fail-closed verdict.  A goal that states NO effect word
    imposes no constraint (its decisive typed admission is the evidence).
    """
    text = str(goal or "").lower()
    stated: list[str] = []
    phrases: list[str] = []
    for verbs, effects in selection._EFFECT_WORDS:
        hit = [verb for verb in verbs if verb in text]
        if hit:
            stated.extend(effects)
            phrases.extend(hit)
    if not stated:
        return True
    low = _row_surface(cid, entry)
    if any(effect in low for effect in set(stated)):
        return True
    # ... or the row DECLARES the stated phrase itself.  `_EFFECT_WORDS` is a
    # curated verb->effect table, and a curated table is exactly what goes stale:
    # "merge conflict" is mapped to {choreograph}, so the dedicated
    # python.vcs.merge_conflict.resolve.v1 row -- whose own keywords say
    # "merge conflict", "keep both changes", "unmerged" -- was judged
    # effect-INCONSISTENT with the sentence it exists for, and a 28-task census
    # lost the merge-conflict request that the front compiler had ALREADY
    # selected correctly.  A row's declared keywords/provides are the row's own
    # statement of the effect it serves; matching the sentence there is stronger
    # evidence than membership in a hand-maintained synonym table.
    return any(len(phrase) > 3 and phrase in low for phrase in set(phrases))


def _row_surface(cid: str, entry: Mapping[str, Any] | None = None) -> str:
    """What the row itself says it does: its id plus its declared surface."""
    parts = [str(cid or "").lower()]
    if isinstance(entry, Mapping):
        parts.extend(map(str, (entry.get("keywords") or [])))
        parts.extend(map(str, (entry.get("provides") or [])))
    return " ".join(parts).lower()


def _phrase_rivals(goal: str, triggers, token: str,
                   registry: Mapping[str, Any]) -> set[str]:
    """Rows that DECLARE a multi-word phrase of the sentence holding a trigger.

    Pure data: every phrase comes from a registry row's own keywords/provides,
    and the trigger words come from ``_FAMILIES`` -- no per-capability table.
    Excludes rows whose id carries the family's effect token (those are the
    family's own candidates, judged by the admission oracle).
    """
    prose = front.prose_only(str(goal or "")).lower()
    rivals: set[str] = set()
    for cid, entry in registry.items():
        if token in str(cid).lower():
            continue
        for phrase in list(entry.get("keywords") or []) + list(entry.get("provides") or []):
            words = str(phrase).lower().split()
            if len(words) < 2:
                continue
            joined = " ".join(words)
            if not any(t in joined for t in triggers):
                continue
            if joined in prose:
                rivals.add(str(cid))
                break
    return rivals


def _resolve_family(goal: str, root: pathlib.Path, registry: dict,
                    declared: dict) -> tuple[str, dict] | None:
    """Enumerate hidden capabilities matching the goal's SWE effect (by the
    registry's OWN keywords), and let ``admit()`` -- the existing typed-contract
    binder -- be the oracle.  DECISIVE only when EXACTLY ONE candidate is
    admitted+specific AND its name states the effect.  Ambiguity or zero =>
    None (fail closed).  This never fabricates a capability: every candidate is
    a real registry row that must bind every declared input from the sentence.

    Measured 2026-10-28: "Find every caller of the function add in X" enumerates
    {symbol.index.ast, change_impact.testselect}; symbol.index.ast names the
    requested effect and its artifact is a REAL callers_of map. Later input
    derivation also made testselect/an inliner bindable, so effect eligibility
    must precede ambiguity counting, not rely on unrelated tools failing to
    bind. Multiple effect-eligible admissions still refuse.
    """
    fam = _family_hits(goal)
    if fam is None:
        return None
    triggers, terms, token = fam
    candidates: list[str] = []
    for cid, entry in sorted(registry.items()):
        if not cid.startswith(_FAMILY_SWE_PREFIXES):
            continue
        # Apply the existing family-effect constraint BEFORE admission and
        # ambiguity counting. Shared keywords and bindable inputs do not make
        # an inliner/test selector an answer to a caller-index request. Filtering
        # only after len(admitted) rejected the real index when those unrelated
        # tools became bindable, and wasted their contract-binding work.
        if token not in cid.lower():
            continue
        surface = " ".join(map(str, (entry.get("keywords") or []) +
                               (entry.get("provides") or []))) + " " + cid
        low = surface.lower()
        if any(term in low for term in terms):
            candidates.append(cid)
    if not candidates:
        return None
    # A family trigger that sits INSIDE a longer phrase another row declares is
    # not the sentence's effect; it is that phrase's object.  "Inline the
    # single-use helper _price_with_tax in X into its only caller" contains
    # "caller", so the caller family claimed authority and executed the symbol
    # index -- a report -- for a refactor, which then failed the promised-source-
    # change gate.  The inliner's own keyword "only caller" states what the
    # sentence asks for.  Enumerate that DECLARED-phrase evidence first, admit it
    # with the same oracle, and only an unambiguous admission wins.
    rivals = _phrase_rivals(goal, triggers, token, registry)
    if rivals:
        rival_hits: list[tuple[str, dict]] = []
        for cid in sorted(rivals):
            try:
                decision = selection.admit(goal, cid, registry[cid], root, declared.get(cid))
            except Exception:
                continue
            if decision.get("admitted") and decision.get("specific"):
                rival_hits.append((cid, dict(decision.get("inputs") or {})))
        if len(rival_hits) == 1:
            return rival_hits[0]
        if len(rival_hits) > 1:
            return None  # two declared phrases could be the request -> refuse
        return None      # the declared phrase is the subject but cannot bind
    admitted: list[tuple[str, dict]] = []
    for cid in candidates:
        try:
            decision = selection.admit(goal, cid, registry[cid], root, declared.get(cid))
        except Exception:
            continue
        if decision.get("admitted") and decision.get("specific"):
            admitted.append((cid, dict(decision.get("inputs") or {})))
    if len(admitted) != 1:
        return None  # ambiguous / none -> fail closed
    cid, inputs = admitted[0]
    if token not in cid.lower():
        return None  # effect-inconsistent -> no false PASS
    return cid, inputs


def build_plan(goal: str, root: Any, *, compiled_context=None) -> tuple[dict, dict, dict] | None:
    """Return ``(registry, admissible, compiled)`` for a DECISIVE typed SWE
    selection, or ``None``.  ``None`` means: not a SWE request, ambiguous, no
    bindable proposal, effect-inconsistent, or any fault — the caller keeps its
    original fail-closed verdict.  Ambiguity is never silently resolved.

    Two decisive routes, both reusing hidden in-repo machinery:
      * select(): the typed shortlist+admit+E30 path (repair/rename/review).
      * _resolve_family(): enumerate-and-let-admission-be-oracle (§9), for SWE
        effect families the lexical shortlist buries (caller-finding, etc.).
    """
    root = pathlib.Path(root)
    if not is_swe_request(goal):
        return None
    try:
        registry = (dict(compiled_context[0]) if compiled_context is not None
                    else dict(live_brain.load_verified_registry()))
        declared = selection.declarations(root)
        cid = ""
        inputs: dict = {}

        fam_terms = _family_terms(goal)
        if fam_terms is not None:
            # A stated SWE effect family is AUTHORITATIVE: the effect-keyed
            # enumerate-and-admit resolver decides (§9).  Measured: letting the
            # lexical select() run first on these goals is nondeterministic —
            # with other tree state it returned an unrelated testselect
            # capability instead of the symbol index.  Family resolver only:
            # decisive single admission, or fail closed.  No second guess.
            fam = _resolve_family(goal, root, registry, declared)
            if fam is None:
                return None
            cid, inputs = fam
        else:
            # Route 1: the existing decisive typed selection (repair/rename/etc).
            decision = selection.select(goal, registry, root, 8)
            chosen = str(decision.get("selected_capability") or "")
            if (decision.get("status") == "SELECTED" and chosen
                    and _effect_consistent(goal, chosen, registry.get(chosen))):
                cid = str(decision.get("selected_capability"))
                inputs = dict(decision.get("inputs") or {})
            else:
                return None  # ambiguity / effect-inconsistent -> refuse

        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        entry = dict(admissible.get(cid) or registry.get(cid) or {})
        if not entry:
            return None
        shadow, values, report = derivation.binding_view(goal, entry, root)
        inputs = {**inputs, **values}
        removed = set((report.get("adapter_defaulted") or {}).keys())

        # Destination identity comes from the stated ROLE, not file existence.
        # F7/F13 can spool an occupied report elsewhere; then repair preflight
        # checks that spool instead of the user's destination, making the verdict
        # depend on previous requests. Reuse the front compiler's role detector
        # (including its aliases and repeated-mention handling). This grants no
        # overwrite authority: the existing adapter/preflight still judges the
        # actual destination. Multiple stated destinations are ambiguous.
        destinations = (front._named_output_destinations(goal, entry, ("output_path",), root)
                        if "output_path" in inputs else set())
        if len(destinations) > 1:
            return None
        if destinations:
            inputs["output_path"] = next(iter(destinations))
        else:
            # Only relocate an incidental source binding. Never move a report
            # the sentence explicitly directs onto an existing source file;
            # preserve that path so the write/repair guards can refuse it.
            relocated = _fresh_output_path(goal, root, inputs)
            if relocated:
                inputs["output_path"] = relocated

        # The three refactor adapters (rename_parameter / rename_symbol /
        # extract_function) resolve ``module`` RELATIVE to ``source_root``:
        # ``_safe_path(src_abs, module_rel)``.  The derivation emits the full
        # repo-relative path, which doubles the prefix -> PATH_MISSING.  Measured:
        # with ``module`` relative to ``source_root`` the rename adapter returns
        # gate=PASS, edit_count=2, complete=true.  Only strip the prefix when the
        # stated source_root is a real directory and genuinely prefixes module.
        sr = inputs.get("source_root")
        mod = inputs.get("module")
        if (isinstance(sr, str) and sr and isinstance(mod, str)
                and mod.startswith(sr.rstrip("/") + "/")
                and (root / sr).is_dir()):
            inputs["module"] = mod[len(sr.rstrip("/")) + 1:]

        exec_entry = dict(entry)
        exec_entry["action_template"] = _execution_template(entry, removed, inputs)
        admissible[cid] = exec_entry

        # Prefer the real compiled shape when the lexical compiler can produce
        # one (it carries target_effects / finish_summary / match_evidence the
        # lossless raw-task contract reads); fall back to a synthetic single-
        # capability plan when the compiler raised (the short-sentence case).
        try:
            if compiled_context is None:
                _, _, real = live_brain.compile_against_live_registry(goal, root)
            else:
                real = compiled_context[2]
            compiled = dict(real)
        except Exception:
            compiled = {
                "schema": SCHEMA, "capabilities": [cid], "compiled_parts": [],
                "score": 0, "match_evidence": {}, "initial_facts": {},
                "finish_summary": "RAW_GOAL_COMPLETE",
            }
        compiled["selected_capability"] = cid
        compiled["inputs"] = inputs
        compiled["compiler_mode"] = "SWE_TYPED_PLAN_V1"
        # The original lexical plan may describe a DIFFERENT capability. Its
        # effects and evidence cannot follow a corrected typed selection.
        compiled["target_effects"] = list(entry.get("provides") or []) or [cid]
        compiled["initial_facts"] = list(entry.get("requires") or [])
        compiled["compiled_parts"] = []
        compiled["capabilities"] = [cid]
        score, _, evidence = goal_compiler._score(goal, cid, entry)
        compiled["score"] = score
        compiled["match_evidence"] = evidence
        compiled.pop("capability_dag", None)
        compiled.pop("controller_actions", None)
        return (registry, admissible, compiled)
    except Exception:
        return None


def plan_report(goal: str, root: Any) -> dict[str, Any]:
    """Measurement surface: what a decisive typed plan would select, without
    executing anything.  Independent of any claim of success."""
    plan = build_plan(goal, root)
    if plan is None:
        return {"schema": SCHEMA, "status": "NO_DECISIVE_TYPED_PLAN"}
    _, _, compiled = plan
    return {
        "schema": SCHEMA, "status": "DECISIVE_TYPED_PLAN",
        "selected_capability": compiled.get("selected_capability"),
        "inputs": {k: (v if isinstance(v, (str, int, float, bool, list, dict)) else str(v))
                   for k, v in (compiled.get("inputs") or {}).items()},
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
