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
    (("caller", "who calls", "call site", "call graph", "find every call"),
     ("caller", "call graph", "who calls"), "symbol"),
)
_FAMILY_SWE_PREFIXES = ("python.", "code.", "software.", "test.", "orchestration.verify.")


def _family_terms(goal: str) -> tuple[tuple[str, ...], str] | None:
    low = str(goal or "").lower()
    for triggers, terms, token in _FAMILIES:
        if any(t in low for t in triggers):
            return terms, token
    return None


def is_swe_request(goal: str) -> bool:
    """An explicit software-engineering request: the base verb list OR a stated
    SWE effect family (caller-finding etc.).  Broadening is confined to the typed
    RETRY path; the pinned lexical compiler and the ``executed`` guard are
    untouched.  Verified: the three pinned front-door refusals stay non-SWE."""
    if derivation.is_swe_request(goal):
        return True
    return _family_terms(goal) is not None


def _execution_template(entry: Mapping[str, Any], removed: set[str]) -> dict[str, Any]:
    """Copy the adapter's declared template, dropping ONLY adapter-defaulted
    ``${input.*}`` placeholders.  Slots with a bound value (including derived
    ones) are kept so the adapter still receives them at run time."""
    template = dict(entry.get("action_template") or {})
    args = dict(template.get("args") or {})
    for key in list(args):
        value = args[key]
        if key in removed and isinstance(value, str) and "${input." in value:
            args.pop(key, None)
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
    imperative = re.search(
        r"(?:^|[.;\n]|\bthen\b|\band\b)\s*"
        r"(?:(?:please|first|next)\s+|(?:can|could|would)\s+you\s+(?:please\s+)?)?"
        r"(?:implement\b|develop\b|build\b|"
        r"add\s+(?:(?:a|an|the|new)\s+)*[\w -]{0,60}"
        r"\b(?:function|method|feature|endpoint|class|api)\b)", prose)
    software = re.search(r"\b(?:python|software|code|function|method|feature|endpoint|class|api)\b", prose)
    if imperative and not software:
        from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES
        software = any(path.suffix.lower() in SOURCE_SUFFIXES
                       for _raw, path in goal_compiler._repo_paths(goal, live_brain.ROOT))
    # These are actual registry effect namespaces, not keyword relevance or id
    # substrings such as 'patch' (which could mean a report-only patch search).
    material = ('.source.write.', '.refactor.', '.edit.', '.issue_to_pr.')
    if imperative and software:
        for cid in capability_ids:
            entry = registry.get(str(cid)) or {}
            if any(any(part in str(effect) for part in material)
                   for effect in entry.get('provides', [])):
                return None
        return 'R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED'

    if "?" in str(goal or ""):
        return None
    repo_paths = list(goal_compiler._repo_paths(goal, live_brain.ROOT))
    if any(pathlib.Path(raw).suffix and not path.exists() for raw, path in repo_paths):
        return None
    has_py_target = any(
        (path.is_file() and path.suffix.lower() == ".py")
        or (path.is_dir() and any(path.rglob("*.py")))
        for _raw, path in repo_paths
    )
    if not has_py_target:
        return None
    in_place_edit = re.search(
        r"(?:^|[.;\n]|\bthen\b|\band\b)\s*(?:(?:please|first|next)\s+)?"
        r"(?:"
        r"extract\s+(?:the\s+)?[\w -]{1,50}\bfrom\b|"
        r"inline\s+(?:the\s+)?|"
        r"move\s+(?:the\s+)?(?:function|method|class|symbol|helper)\b|"
        r"remove\s+(?:the\s+)?(?:sql\s+injection|unused\s+(?:function|import|code)|dead\s+code)\b|"
        r"break\s+(?:the\s+)?(?:circular\s+import|import\s+cycle|cycle)\b|"
        r"resolve\s+(?:the\s+)?merge\s+conflict\b|"
        r"make\s+\S+\s+(?:linear|linearithmic|constant|faster|subquadratic|thread[- ]safe)\b"
        r")",
        prose,
    )
    if not in_place_edit:
        return None
    edit_tokens = ("refactor", "repair", "edit", "choreograph", "resolve", "format", "migrate")
    edit_effects = (".source.write.", ".refactor.", ".edit.", ".repair.", ".choreograph.", ".merge_conflict.")
    for cid in capability_ids:
        cid_s = str(cid).lower()
        entry = registry.get(str(cid)) or {}
        if any(tok in cid_s for tok in edit_tokens):
            return None
        if any(any(part in str(effect) for part in edit_effects)
               for effect in entry.get("provides", [])):
            return None
    return "R11_READ_ONLY_CAPABILITY_FOR_SOURCE_EDIT"


def _effect_consistent(goal: str, cid: str) -> bool:
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
    for verbs, effects in selection._EFFECT_WORDS:
        if any(verb in text for verb in verbs):
            stated.extend(effects)
    if not stated:
        return True
    low = str(cid or "").lower()
    return any(effect in low for effect in set(stated))


def _resolve_family(goal: str, root: pathlib.Path, registry: dict,
                    declared: dict) -> tuple[str, dict] | None:
    """Enumerate hidden capabilities matching the goal's SWE effect (by the
    registry's OWN keywords), and let ``admit()`` -- the existing typed-contract
    binder -- be the oracle.  DECISIVE only when EXACTLY ONE candidate is
    admitted+specific AND its name states the effect.  Ambiguity or zero =>
    None (fail closed).  This never fabricates a capability: every candidate is
    a real registry row that must bind every declared input from the sentence.

    Measured 2026-10-28: "Find every caller of the function add in X" enumerates
    {symbol.index.ast, change_impact.testselect}; only symbol.index.ast admits
    (specific) and names the effect -> decisive, and its artifact is a REAL
    callers_of map.  test-gen/lint/typecheck/extract enumerate to zero-or-many
    admitted and therefore stay honestly fail-closed (no false PASS).
    """
    fam = _family_terms(goal)
    if fam is None:
        return None
    terms, token = fam
    candidates: list[str] = []
    for cid, entry in sorted(registry.items()):
        if not cid.startswith(_FAMILY_SWE_PREFIXES):
            continue
        surface = " ".join(map(str, (entry.get("keywords") or []) +
                               (entry.get("provides") or []))) + " " + cid
        low = surface.lower()
        if any(term in low for term in terms):
            candidates.append(cid)
    if not candidates:
        return None
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


def build_plan(goal: str, root: Any) -> tuple[dict, dict, dict] | None:
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
        registry = dict(live_brain.load_verified_registry())
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
            if (decision.get("status") == "SELECTED" and decision.get("selected_capability")
                    and _effect_consistent(goal, str(decision.get("selected_capability")))):
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
        exec_entry["action_template"] = _execution_template(entry, removed)
        admissible[cid] = exec_entry

        # Prefer the real compiled shape when the lexical compiler can produce
        # one (it carries target_effects / finish_summary / match_evidence the
        # lossless raw-task contract reads); fall back to a synthetic single-
        # capability plan when the compiler raised (the short-sentence case).
        try:
            _, _, real = live_brain.compile_against_live_registry(goal, root)
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
        compiled.setdefault("target_effects", list(entry.get("provides") or []) or [cid])
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
