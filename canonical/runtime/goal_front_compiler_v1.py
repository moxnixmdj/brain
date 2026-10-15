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

from canonical.runtime import goal_compiler as gc

SCHEMA = "PROJECT_BRAIN_GOAL_FRONT_COMPILER_V1"
GoalCompilationFailure = gc.GoalCompilationFailure

_QUOTE_OPEN = "\"'\u201c\u2018`"
_QUOTE_CLOSE = "\"'\u201d\u2019`"
_NUM = r"-?\d+(?:\.\d+)?"

# natural aliases for registry input keys (key -> phrases that may name it in a sentence)
_KEY_ALIASES: dict[str, tuple[str, ...]] = {
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
}
_PATH_LIST_KEYS = {"test_paths", "source_paths", "evidence_paths"}
_PATH_DIR_KEYS = {"source_root"}
_PATH_FILE_KEYS = {"path"}
_NUMERIC_KEYS = {"x_value", "y_value", "major", "max_age_s"}
_LIST_NUMERIC_KEYS = {"x_ticks", "y_ticks"}
_BOOL_KEYS = {"authoritative"}
_ARGV_KEYS = {"test_argv"}
_JSON_OR_TEXT_KEYS = {"spec", "objective"}
_KV_KEYS = {"variables"}


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


def routable_registry(admissible: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {cid: entry for cid, entry in admissible.items() if isinstance(entry, Mapping) and is_plain_goal_routable(entry)}


def blocked_zero_input_capabilities(admissible: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return sorted(cid for cid, entry in admissible.items() if isinstance(entry, Mapping) and not is_plain_goal_routable(entry))


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
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":not_stated")
    # quoted values win over bare tokens so an alias inside a quoted value ("Curve A") cannot steal it
    for strict in (True, False):
        for tail in tails:
            value = _parse_typed_value(key, tail, quoted_only=strict)
            if value is not None and value != [] and value != {}:
                return value
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":value_not_parseable")


def _parse_typed_value(key: str, tail: str, quoted_only: bool = False):
    if key in _NUMERIC_KEYS:
        return _number(tail)
    if key in _LIST_NUMERIC_KEYS:
        return _number_list(tail)
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


def _is_output_key(key: str) -> bool:
    return key.startswith("output_") or key.split("_")[0] in _OUTPUT_STEMS


def _bind_path_by_type(goal: str, key: str, root: pathlib.Path, context_paths: list[str] | None = None):
    """F6: bind an input path by file TYPE when the pinned name-stem binder cannot."""
    stem = key[:-5].lower()
    wanted = _STEM_SUFFIXES.get(stem)
    existing = [(raw, p) for raw, p in gc._repo_paths(goal, root) if p.is_file() or raw in (context_paths or [])]
    if wanted:
        matching = [raw for raw, p in existing if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    else:
        matching = [raw for raw, p in existing]
    if len(matching) == 1:
        return matching[0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(matching)) + "_type_compatible_existing_files_named")


def _bind_output_by_future(goal: str, key: str, root: pathlib.Path):
    """F7: an output named in the sentence is a file that does not exist yet."""
    stem = key[:-5].lower().replace("output_", "") if key != "output_path" else "output"
    wanted = _STEM_SUFFIXES.get(stem)
    future = [(raw, p) for raw, p in gc._repo_paths(goal, root) if pathlib.Path(raw).suffix and not p.exists()]
    if wanted:
        future = [(raw, p) for raw, p in future if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    if len(future) == 1:
        return future[0][0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(future)) + "_future_artifacts_named")


def bind_all_inputs(goal: str, entry: Mapping[str, Any], root: pathlib.Path, context_paths=None, future_clauses=None) -> dict[str, Any]:
    """Pinned binder for the keys it supports, typed grammar / type binding for the rest. Never guesses."""
    keys = input_keys(entry)
    pinned_keys = [k for k in keys if k in ("text", "goal", "url") or k.endswith("_path")]
    typed_keys = [k for k in keys if k not in pinned_keys]
    inputs: dict[str, Any] = {}
    for key in pinned_keys:
        shadow = dict(entry)
        shadow["action_template"] = {"args": {key: "${input." + key + "}"}}
        try:
            inputs.update(gc._bind_inputs(goal, root, shadow, context_paths=context_paths, future_clauses=future_clauses))
        except GoalCompilationFailure:
            if key.endswith("_path") and not _is_output_key(key):
                inputs[key] = _bind_path_by_type(goal, key, root, context_paths=context_paths)
            elif key.endswith("_path"):
                inputs[key] = _bind_output_by_future(goal, key, root)
            else:
                raise
    for key in typed_keys:
        inputs[key] = bind_typed_key(goal, key, root)
    repair_output_collisions(goal, inputs, root)
    return inputs


def repair_output_collisions(goal: str, inputs: dict[str, Any], root: pathlib.Path) -> list[str]:
    """F10: an output path is never one of the action's own input files.

    The pinned binder can resolve `output_path` to an existing input named in the sentence; the
    tool then overwrites its input and the promised artifact never appears.  When an output key
    points at a path that is also bound as an input, or at an existing file while the sentence
    names exactly one file that does not exist yet, the future artifact wins.  Ambiguity raises
    (fail closed) instead of guessing.  Returns the keys that were rebound."""
    rebound = []
    input_paths = {str(v) for k, v in inputs.items() if k.endswith("_path") and not _is_output_key(k)}
    for key in [k for k in inputs if k.endswith("_path") and _is_output_key(k)]:
        value = str(inputs[key])
        collides = value in input_paths
        exists = (root / value).exists()
        if collides or (exists and len(_future_artifacts(goal, root)) == 1):
            inputs[key] = _bind_output_by_future(goal, key, root)
            rebound.append(key)
    return rebound


# ----------------------------------------------------------------------------- routing

def prose_only(goal: str) -> str:
    """The sentence without URLs and repository paths (F8)."""
    text = re.sub(r"https?://[^\s)\]}>]+", " ", str(goal or ""))
    return re.sub(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", " ", text)


def ranked_candidates(goal: str, registry: Mapping[str, Mapping[str, Any]]) -> list[tuple[int, int, str, dict[str, Any]]]:
    """Candidates ranked by the pinned scorer on prose tokens only; constraints see the full goal."""
    prose = prose_only(goal)
    out = []
    for cid, entry in sorted(registry.items()):
        if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"), dict):
            continue
        scored_text = prose
        surface_ok, surface_evidence = gc._execution_surface_constraint_match(goal, entry)
        if not surface_ok:
            own = gc._tokens(entry.get("keywords", [])) | gc._tokens(cid) | gc._tokens(entry.get("provides", []))
            surface_word = {"npm_node": "npm", "pypi_python": "pypi", "apt": "apt"}.get(str((surface_evidence or {}).get("required_surface")))
            if not (surface_word and surface_word in own):
                continue
            # the pinned scorer re-applies the surface rule: score without the surface word (F9)
            scored_text = re.sub(r"(?i)\b(?:pypi|npm|node(?:\.js|js)?|apt)\b|python library|javascript library|ubuntu package|debian package", " ", prose)
        if not gc._structured_binary_format_match(goal, entry)[0]:
            continue
        score, specificity, evidence = gc._score(scored_text, cid, entry)
        if score > 0:
            out.append((score, specificity, cid, evidence))
    out.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return out


def _future_artifacts(goal: str, root: pathlib.Path) -> list[str]:
    return [raw for raw, p in gc._repo_paths(goal, root) if pathlib.Path(raw).suffix and not p.exists()]


def _output_keys(entry: Mapping[str, Any]) -> list[str]:
    return [k for k in input_keys(entry) if k.startswith("output_") or k.split("_")[0] in {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}]


def _single(cid: str, entry: Mapping[str, Any], inputs: Mapping[str, Any], score: int, evidence: Mapping[str, Any], rules: list[str]) -> dict[str, Any]:
    return {
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


_LITERAL_MODES = {"DETERMINISTIC_LITERAL_JSON_RECORDS", "DETERMINISTIC_EXACT_LITERAL_RESPONSE"}


def sentence_clauses(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])|\b[Tt]hen\b", " ".join(str(text or "").split()))
    return [part.strip(" .,;") for part in parts if part and part.strip(" .,;")]


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
    accumulated_outputs = []
    for idx, clause in enumerate(clauses):
        future = clauses[idx + 1:]
        sub = compile_goal(clause, admissible, root, context_paths=accumulated_outputs, future_clauses=future)
        parts.append(sub)
        actions.extend(_actions_of(sub, registry))
        effects.extend(e for e in (sub.get("target_effects") or []) if e not in effects)
        for k, v in (sub.get("inputs") or {}).items():
            if k.endswith("_path") and _is_output_key(k) and isinstance(v, str):
                accumulated_outputs.append(v)
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


def compile_goal(
    goal: str, admissible: Mapping[str, Mapping[str, Any]], root: pathlib.Path,
    context_paths=None, future_clauses=None,
) -> dict[str, Any]:
    """Front compile. Returns the pinned compiler's shape plus ``front_compiler`` metadata."""
    rules: list[str] = []
    original = str(goal or "").strip()
    text = normalize_goal(original)
    if text != original:
        rules.append("F2_SENTENCE_FINAL_PERIOD_REMOVED")
    registry = routable_registry(admissible)
    if len(registry) != len(admissible):
        rules.append("F4_ZERO_INPUT_TOOLS_NOT_ROUTABLE")
    ranked = ranked_candidates(text, registry)
    best_cid = ranked[0][2] if ranked else None
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

    selected = (compiled or {}).get("selected_capability") if compiled else None
    single_shape = bool(compiled) and compiled.get("compiler_mode") == "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH" and selected

    if single_shape or compiled is None:
        future = _future_artifacts(text, root)
        # F3: a goal that names a file to be produced is served by a tool that can write a file
        preferred = [c for c in ranked if _output_keys(registry[c[2]])] if future else []
        if future and preferred:
            rules.append("F3_ARTIFACT_WRITERS_PREFERRED")
        pool = preferred or ranked
        best = pool[0] if pool else None
        if best is not None and selected != best[2]:
            entry = registry[best[2]]
            try:
                inputs = bind_all_inputs(text, entry, root, context_paths=context_paths, future_clauses=future_clauses)
            except GoalCompilationFailure as exc:
                best_error = exc
            else:
                rules.append("F1_BEST_CANDIDATE_BOUND_INSTEAD_OF_FALLTHROUGH")
                if any(str(inputs[k]) == str(inputs[j]) for k in inputs if _is_output_key(k) for j in inputs if j != k and j.endswith("_path")):
                    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", best[2] + ":output_path_equals_an_input_path")
                return _single(best[2], entry, inputs, best[0], best[3], rules)
            # the best candidate cannot bind: accept the pinned selection only if it is itself a
            # prose-scored candidate consistent with the goal's artifact; never a fall-through
            consistent = selected in {c[2] for c in pool}
            if not consistent:
                raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", best[2] + ":" + str(best_error.detail))
        if compiled is None:
            raise pinned_failure  # type: ignore[misc]
        if future and not _output_keys(registry[selected]):
            raise GoalCompilationFailure("GOAL_OUTPUT_ARTIFACT_UNSERVED", selected)

    if compiled is None:
        raise pinned_failure  # type: ignore[misc]

    if single_shape and isinstance(compiled.get("inputs"), dict):
        if repair_output_collisions(text, compiled["inputs"], root):
            rules.append("F10_OUTPUT_NEVER_AN_INPUT_FILE")
            for action in compiled.get("actions") or []:
                args = action.get("args") if isinstance(action, dict) else None
                if isinstance(args, dict):
                    for k, v in compiled["inputs"].items():
                        if k in args:
                            args[k] = v
    compiled["front_compiler"] = {"schema": SCHEMA, "rules_applied": rules}
    return compiled
