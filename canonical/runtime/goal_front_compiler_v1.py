"""One mouth for every bound capability: a front layer on the byte-pinned goal compiler.

Measured on 2026-10-15 (canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json)
the pinned compiler has measured defects and compound-flow gaps that this layer corrects WITHOUT editing a pinned byte:

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

10. Multi-step goals need an execution graph, not a flat action list. Here: each explicit clause is
    compiled with prior produced paths in context, lowered through ``capability_planner.plan_actions``,
    and connected by declared effect/result edges. Returned artifact paths flow through ``$result``
    bindings when the producer declares the field; otherwise the explicit path stays static and the
    dependency edge still orders execution. The live controller enforces the resulting composition
    capsule, and final outputs are reopened and checked for non-empty bytes.

It also binds the 33 registry inputs the pinned binder cannot (``path``, ``jq_filter``,
``expression``, ``x_value``, ``test_paths`` ...) from an explicit typed grammar:
``<key words> <quoted string | number | path | list | key=value pairs>``.  Inputs are never
guessed: a goal that does not state an input fails closed with GOAL_INPUT_BINDING_REQUIRED.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shlex
from typing import Any, Mapping

from canonical.runtime import capability_planner
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


def _bind_path_by_type(goal: str, key: str, root: pathlib.Path):
    """F6: bind an input path by file TYPE when the pinned name-stem binder cannot."""
    stem = key[:-5].lower()
    wanted = _STEM_SUFFIXES.get(stem)
    existing = [(raw, p) for raw, p in gc._repo_paths(goal, root) if p.is_file()]
    if wanted:
        matching = [raw for raw, p in existing if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    else:
        matching = [raw for raw, p in existing]
    if len(matching) == 1:
        return matching[0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(matching)) + "_type_compatible_existing_files_named")


def _context_path_for_input(key: str, context_paths) -> str | None:
    """Return the most recent compatible artifact forwarded from an earlier clause."""
    if not key.endswith("_path") or _is_output_key(key):
        return None
    paths = [str(path) for path in context_paths or [] if isinstance(path, (str, pathlib.Path))]
    if not paths:
        return None
    stem = key[:-5].lower()
    wanted = _STEM_SUFFIXES.get(stem)
    if wanted:
        for raw in reversed(paths):
            path = pathlib.Path(raw)
            if "".join(path.suffixes[-2:]).lower() in wanted or path.suffix.lower() in wanted:
                return raw
        return None
    # Match the pinned compiler's typed context lookup for generic input/source
    # paths, but do not use output paths as inputs.
    return gc._context_path_for_key(key, paths)


def _bind_output_by_future(goal: str, key: str, root: pathlib.Path, context_paths=None):
    """F7: an output named in the sentence is a file that does not exist yet."""
    stem = key[:-5].lower().replace("output_", "") if key != "output_path" else "output"
    wanted = _STEM_SUFFIXES.get(stem)
    context = {str(path) for path in context_paths or []}
    future = [
        (raw, p) for raw, p in gc._repo_paths(goal, root)
        if pathlib.Path(raw).suffix and not p.exists() and raw not in context
    ]
    if wanted:
        future = [(raw, p) for raw, p in future if "".join(p.suffixes[-2:]).lower() in wanted or p.suffix.lower() in wanted]
    if len(future) == 1:
        return future[0][0]
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(future)) + "_future_artifacts_named")


def bind_all_inputs(goal: str, entry: Mapping[str, Any], root: pathlib.Path, context_paths=None, future_clauses=None) -> dict[str, Any]:
    """Bind explicit inputs, forwarding produced context artifacts before stale disk matches."""
    keys = input_keys(entry)
    pinned_keys = [k for k in keys if k in ("text", "goal", "url") or k.endswith("_path")]
    typed_keys = [k for k in keys if k not in pinned_keys]
    inputs: dict[str, Any] = {}
    for key in pinned_keys:
        if key.endswith("_path") and not _is_output_key(key):
            forwarded = _context_path_for_input(key, context_paths)
            if forwarded is not None:
                inputs[key] = forwarded
                continue
        shadow = dict(entry)
        shadow["action_template"] = {"args": {key: "${input." + key + "}"}}
        try:
            inputs.update(gc._bind_inputs(goal, root, shadow, context_paths=context_paths, future_clauses=future_clauses))
        except GoalCompilationFailure:
            if key.endswith("_path") and not _is_output_key(key):
                inputs[key] = _bind_path_by_type(goal, key, root)
            elif key.endswith("_path"):
                inputs[key] = _bind_output_by_future(goal, key, root, context_paths=context_paths)
            else:
                raise
    for key in typed_keys:
        inputs[key] = bind_typed_key(goal, key, root)
    repair_output_collisions(goal, inputs, root, context_paths=context_paths)
    return inputs


def repair_output_collisions(goal: str, inputs: dict[str, Any], root: pathlib.Path, context_paths=None) -> list[str]:
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
        if collides or (exists and len(_future_artifacts(goal, root, context_paths)) == 1):
            inputs[key] = _bind_output_by_future(goal, key, root, context_paths=context_paths)
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


def _future_artifacts(goal: str, root: pathlib.Path, context_paths=None) -> list[str]:
    excluded = {str(path) for path in context_paths or []}
    return list(dict.fromkeys(
        raw for raw, p in gc._repo_paths(goal, root)
        if pathlib.Path(raw).suffix and not p.exists() and raw not in excluded
    ))


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
    """Use the compiler's conservative sentence/action connector grammar."""
    clauses = []
    for part in gc.decompose_goal(text):
        clause = str(part).strip(" .,;")
        clause = re.sub(r"(?i)\s+\b(?:and|then)\s*$", "", clause).strip(" .,;")
        clause = re.sub(r"(?i)^(?:and|then)\s+", "", clause).strip(" .,;")
        if clause and clause.lower() not in {"and", "then"}:
            clauses.append(clause)
    return clauses


def _actions_of(compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    actions = compiled.get("controller_actions")
    if isinstance(actions, list):
        return [dict(a) for a in actions if isinstance(a, Mapping) and a.get("type") != "finish"]
    cid = str(compiled.get("selected_capability") or "")
    if cid not in registry or not isinstance(compiled.get("inputs"), Mapping):
        raise GoalCompilationFailure("GOAL_COMPILATION_CLAUSE_NOT_EXECUTABLE", cid)
    return [gc._render_template(registry[cid]["action_template"], dict(compiled["inputs"]))]


def _walk_result_refs(value):
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise GoalCompilationFailure("COMPOUND_RESULT_REFERENCE_INVALID")
            try:
                cycle = int(spec.get("cycle", -1))
            except (TypeError, ValueError) as exc:
                raise GoalCompilationFailure("COMPOUND_RESULT_REFERENCE_INVALID") from exc
            field = str(spec.get("field") or "").strip()
            if cycle < 0 or not field:
                raise GoalCompilationFailure("COMPOUND_RESULT_REFERENCE_INVALID")
            return [{"cycle": cycle, "field": field}]
        return [ref for item in value.values() for ref in _walk_result_refs(item)]
    if isinstance(value, list):
        return [ref for item in value for ref in _walk_result_refs(item)]
    return []


def _offset_result_refs(value, cycle_offset: int):
    if isinstance(value, Mapping):
        if set(value) == {"$result"} and isinstance(value["$result"], Mapping):
            spec = dict(value["$result"])
            spec["cycle"] = int(spec.get("cycle", -1)) + cycle_offset
            return {"$result": spec}
        return {key: _offset_result_refs(item, cycle_offset) for key, item in value.items()}
    if isinstance(value, list):
        return [_offset_result_refs(item, cycle_offset) for item in value]
    return value


def _action_capability_id(action: Mapping[str, Any], compiled: Mapping[str, Any], registry) -> str | None:
    args = action.get("args") if isinstance(action.get("args"), Mapping) else {}
    argument_id = str(args.get("capability_id") or "").strip()
    if argument_id:
        return argument_id
    action_id = str(action.get("capability_id") or "").strip()
    if action_id:
        if action_id in registry:
            return action_id
        if not action_id.startswith("front.compound."):
            return action_id
    selected = str(compiled.get("selected_capability") or "").strip()
    return selected or None


def _action_output_bindings(action: Mapping[str, Any], result_fields) -> list[tuple[str, str | None]]:
    args = action.get("args") if isinstance(action.get("args"), Mapping) else {}
    declared = set(result_fields or [])
    out = []
    for key, value in args.items():
        if isinstance(key, str) and key.endswith("_path") and _is_output_key(key) and isinstance(value, str) and value:
            out.append((value, key if key in declared else None))
    return out


def _input_path_values(action: Mapping[str, Any], inputs=None) -> set[str]:
    values = set()
    for key, value in (inputs or {}).items():
        if isinstance(key, str) and key.endswith("_path") and not _is_output_key(key):
            if isinstance(value, str) and value:
                values.add(value)
            elif isinstance(value, list):
                values.update(str(item) for item in value if isinstance(item, str) and item)
    args = action.get("args") if isinstance(action.get("args"), Mapping) else {}
    for key, value in args.items():
        if isinstance(key, str) and (key == "path" or key.endswith("_path") or key.endswith("_paths")) and not _is_output_key(key):
            if isinstance(value, str) and value:
                values.add(value)
            elif isinstance(value, list):
                values.update(str(item) for item in value if isinstance(item, str) and item)
    return values


def _replace_context_artifact_refs(value, producers, requirements, output_key=False):
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            is_output = isinstance(key, str) and key.endswith("_path") and _is_output_key(key)
            out[key] = _replace_context_artifact_refs(item, producers, requirements, output_key=is_output)
        return out
    if isinstance(value, list):
        return [_replace_context_artifact_refs(item, producers, requirements, output_key=output_key) for item in value]
    if isinstance(value, str) and not output_key and value in producers:
        producer = producers[value]
        requirements.add(producer["effect"])
        field = producer.get("result_field")
        if field:
            return {"$effect_result": {"effect": producer["effect"], "field": field}}
    return value


COMPOUND_NATIVE_RESULT_FIELDS = {
    "write_json_records": {"output_path", "record_count", "fields", "output_sha256", "output_bytes"},
    "assert_file_exists": {"path", "exists", "verified", "sha256"},
    "read_file": {"path", "content", "truncated"},
    "list_tree": {"items", "truncated"},
    "search_text": {"query", "hits", "truncated"},
    "assert_text_contains_json_keys": {"verified", "expected_key_count", "expected_keys", "missing_keys", "json_path", "normalization"},
}
COMPOUND_NATIVE_ACTION_TYPES = frozenset({
    "read_file", "list_tree", "search_text", "http_get",
    "extract_labeled_fields_from_rendered_source", "assert_labeled_fields_against_fresh_source",
    "resolve_authority_identity", "assert_authority_identity", "discover_authoritative_web_source",
    "assert_authoritative_source_discovery", "fetch_json_knowledge", "assess_knowledge_consistency",
    "materialize_supported_knowledge", "assert_knowledge_status", "assert_json_knowledge",
    "write_json_records", "invoke_verified_bound_capability_adapter", "invoke_capability",
    "invoke_capability_by_runtime_value", "invoke_capability_fanout", "invoke_capability_fallback",
    "invoke_capability_until", "verify_with_independent_pypi_codec", "verify_with_independent_npm_codec",
    "project_browser_result_json", "join_runtime_json_arrays", "assert_runtime_json_join",
    "aggregate_runtime_json_arrays", "assert_runtime_json_aggregate", "derive_grouped_records",
    "assert_grouped_derived_records", "select_ranked_record", "assert_ranked_record",
    "assert_hex_prefix_bucket", "assert_collection_length_bucket", "assert_runtime_selected_code_decodes",
    "assert_text_contains_json_keys", "assert_file_exists", "assert_json_fields_equal",
    "assert_runtime_fanout_decodes", "assert_runtime_fanout_artifacts_decode",
    "assert_runtime_per_item_fallback_decodes", "assert_runtime_fallback_decision",
    "assert_runtime_bounded_loop_trace", "assert_workflow_audit_supported_by_source",
    "assert_python_source_audit_supported_by_source", "assert_python_test_audit_zero",
    "assert_python_test_audit_supported_by_fresh_execution",
})


def _native_result_fields(action: Mapping[str, Any], referenced_fields) -> list[str]:
    typ = str(action.get("type") or "")
    fields = set(COMPOUND_NATIVE_RESULT_FIELDS.get(typ, set()))
    fields.update(str(field) for field in referenced_fields if str(field))
    return sorted(fields)


def _context_inputs_from(compiled: Mapping[str, Any]) -> dict[str, Any]:
    inputs = compiled.get("inputs")
    return dict(inputs) if isinstance(inputs, Mapping) else {}


def _build_execution_dag(
    step_specs: list[dict[str, Any]],
    registry: Mapping[str, Mapping[str, Any]],
    root: pathlib.Path,
    original_goal: str,
    initial_context_paths=None,
    *,
    clauses=None,
    compiled_parts=None,
    rules=None,
    compiler_mode="FRONT_COMPOUND_EXECUTION_DAG",
    target_effects=None,
):
    """Lower the front compiler's explicit action sequence into a validated planner DAG."""
    if not step_specs:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_EXECUTABLE_CLAUSE")
    if len(step_specs) > 62:
        raise GoalCompilationFailure("COMPOUND_ACTION_LIMIT_EXCEEDED", str(len(step_specs)))

    producers: dict[str, dict[str, Any]] = {}
    prepared: list[dict[str, Any]] = []
    step_effects = [f"compound.step.{i}.completed" for i in range(len(step_specs))]
    referenced_fields: dict[int, set[str]] = {i: set() for i in range(len(step_specs))}

    # Existing result references in specialized compiled plans use action-cycle indexes.
    # Rebase clause-local references and prove that they only point backward.
    for index, spec in enumerate(step_specs):
        action = _offset_result_refs(dict(spec["action"]), int(spec.get("cycle_offset", 0)))
        for ref in _walk_result_refs(action):
            if ref["cycle"] >= index:
                raise GoalCompilationFailure("COMPOUND_RESULT_REFERENCE_NOT_BACKWARD", f"{index}:{ref['cycle']}")
            referenced_fields[ref["cycle"]].add(ref["field"])
        prepared.append({**spec, "action": action})

    raw_capabilities = []
    user_outputs: list[str] = []
    for index, spec in enumerate(prepared):
        action = dict(spec["action"])
        source_cid = spec.get("source_capability_id")
        entry = registry.get(source_cid) if source_cid else None
        if isinstance(entry, Mapping):
            # Registry-declared fields remain authoritative. Older verified entries
            # may omit a result_fields list; any compiler-authored cross-step read is
            # then made an explicit runtime-checked field contract in the capsule.
            result_fields = sorted(
                {str(x) for x in (entry.get("result_fields") or []) if isinstance(x, str) and x.strip()}
                | referenced_fields[index]
            )
            native = False
        else:
            result_fields = _native_result_fields(action, referenced_fields[index])
            native = True
        action_id = f"front.compound.action.{index}"
        step_effect = step_effects[index]
        requires = set()
        if index:
            requires.add(step_effects[index - 1])
        for ref in _walk_result_refs(action):
            requires.add(step_effects[ref["cycle"]])

        # Context paths are provenance edges. When a producer reports its output path,
        # consumers read that returned path via capability_planner's typed result binding.
        inputs = _input_path_values(action, spec.get("inputs"))
        for path in sorted(inputs):
            provider = producers.get(path)
            if provider is not None:
                requires.add(provider["effect"])
        action = _replace_context_artifact_refs(action, producers, requires)

        provides = [step_effect]
        output_bindings = _action_output_bindings(action, result_fields)
        input_paths = _input_path_values(action, spec.get("inputs"))
        collisions = sorted(input_paths & {path for path, _field in output_bindings})
        if collisions:
            raise GoalCompilationFailure("COMPOUND_OUTPUT_EQUALS_INPUT_PATH", collisions[0])
        for path, result_field in output_bindings:
            if path in producers:
                raise GoalCompilationFailure("COMPOUND_ARTIFACT_MULTIPLE_PRODUCERS", path)
            artifact_effect = "compound.artifact." + hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
            provides.append(artifact_effect)
            producers[path] = {"effect": artifact_effect, "result_field": result_field, "producer_index": index}
            user_outputs.append(path)
        raw_capabilities.append({
            "id": action_id,
            "requires": sorted(requires),
            "provides": provides,
            "cost": float(spec.get("cost", 1.0)),
            "action": action,
            "result_fields": result_fields,
            "source_capability_id": source_cid,
            "goal_clause": spec.get("goal_clause"),
            "context_paths": list(spec.get("context_paths") or []),
            "native_action": native,
            "step_index": spec.get("step_index", index),
            "action_index": index,
            "role": spec.get("role", "COMPOUND_ACTION"),
        })

    # Anything named as a not-yet-existing artifact must have an actual producer in the DAG.
    expected_future = [
        path for path in _future_artifacts(original_goal, root, initial_context_paths)
        if path not in {str(x) for x in initial_context_paths or []}
    ]
    unserved = sorted(set(expected_future) - set(user_outputs))
    if unserved:
        raise GoalCompilationFailure("GOAL_OUTPUT_ARTIFACT_UNSERVED", ",".join(unserved))

    # Independently reopen each produced artifact at the end of the plan. The live route
    # also checks non-empty bytes after execution, so existence alone cannot produce PASS.
    final_paths = list(dict.fromkeys(user_outputs))
    final_verifier_ids = []
    previous_final_effect = step_effects[-1]
    for offset, path in enumerate(final_paths):
        verifier_index = len(raw_capabilities)
        verifier_id = f"front.compound.verify.{offset}"
        step_effect = f"compound.verification.{offset}.complete"
        requirements = {previous_final_effect}
        provider = producers.get(path)
        if provider is not None:
            requirements.add(provider["effect"])
        verify_action = {
            "type": "assert_file_exists",
            "args": {"path": path},
            "expect": {"type": "field_equals", "field": "verified", "value": True},
            "why": "Independently reopen and verify a produced compound-goal deliverable.",
        }
        verify_action = _replace_context_artifact_refs(verify_action, producers, requirements)
        raw_capabilities.append({
            "id": verifier_id,
            "requires": sorted(requirements),
            "provides": [step_effect],
            "cost": 1.0,
            "action": verify_action,
            "result_fields": ["exists", "path", "sha256", "verified"],
            "source_capability_id": None,
            "goal_clause": None,
            "context_paths": [path],
            "native_action": True,
            "step_index": None,
            "action_index": verifier_index,
            "role": "FINAL_DELIVERABLE_VERIFICATION",
            "verified_path": path,
        })
        final_verifier_ids.append(verifier_id)
        previous_final_effect = step_effect

    if len(raw_capabilities) + 1 > 64:
        raise GoalCompilationFailure("COMPOUND_ACTION_LIMIT_EXCEEDED", str(len(raw_capabilities) + 1))
    if final_verifier_ids:
        targets = [f"compound.verification.{i}.complete" for i in range(len(final_verifier_ids))]
    else:
        targets = [step_effects[-1]]
    problem = {
        "initial_facts": [],
        "target_effects": targets,
        "finish_summary": "COMPOUND_GOAL_COMPLETE_AND_DELIVERABLES_VERIFIED",
        "capabilities": raw_capabilities,
    }
    try:
        planned = capability_planner.plan_actions(problem)
    except capability_planner.PlanningFailure as exc:
        raise GoalCompilationFailure("COMPOUND_DAG_PLANNING_FAILED", f"{exc.code}:{exc.detail}") from exc

    output_rules = list(rules or [])
    output_rules.extend([
        "F5_COMPOUND_SENTENCES_COMPILED_SEPARATELY",
        "F11_CONTEXT_PATHS_FORWARDED_BETWEEN_CLAUSES",
        "F12_CAPABILITY_PLANNER_EXECUTION_DAG",
    ])
    if final_paths:
        output_rules.append("F13_FINAL_DELIVERABLES_INDEPENDENTLY_REOPENED")
    result = {
        "schema": "PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode": compiler_mode,
        "controller_actions": planned["actions"],
        "compiled_parts": list(compiled_parts or []),
        "target_effects": list(target_effects or targets),
        "clauses": list(clauses or []),
        "capability_problem": problem,
        "capability_plan": planned["planning"],
        "execution_dag": planned["execution_dag"],
        "composition_contract": planned["composition_contract"],
        "composition_initial_facts": planned["planning"].get("initial_facts", []),
        "final_deliverable_verification": {
            "status": "PLANNED",
            "paths": final_paths,
            "verification_capability_ids": final_verifier_ids,
            "verification_kind": "FILE_REOPEN_EXISTS_AND_POSTRUN_NONEMPTY",
        },
        "front_compiler": {"schema": SCHEMA, "rules_applied": list(dict.fromkeys(output_rules))},
    }
    return result


def _plan_existing_compound(
    compiled: Mapping[str, Any],
    admissible: Mapping[str, Mapping[str, Any]],
    root: pathlib.Path,
    original_goal: str,
    rules: list[str],
    initial_context_paths=None,
) -> dict[str, Any]:
    """Add planner DAG/capsule contracts around a specialized pinned compound plan."""
    registry = routable_registry(admissible)
    raw_actions = compiled.get("controller_actions")
    if not isinstance(raw_actions, list):
        raise GoalCompilationFailure("COMPOUND_CONTROLLER_ACTIONS_REQUIRED")
    actions = [dict(action) for action in raw_actions if isinstance(action, Mapping) and action.get("type") != "finish"]
    if not actions:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_EXECUTABLE_CLAUSE")
    specs = []
    clauses = list(compiled.get("clauses") or sentence_clauses(original_goal))
    parts = list(compiled.get("compiled_parts") or [])
    context_paths = [str(path) for path in initial_context_paths or []]
    for index, action in enumerate(actions):
        source_cid = _action_capability_id(action, compiled, registry)
        if source_cid and source_cid not in registry:
            raise GoalCompilationFailure("COMPOUND_ACTION_SOURCE_NOT_ADMISSIBLE", source_cid)
        if source_cid is None and action.get("type") not in COMPOUND_NATIVE_ACTION_TYPES:
            raise GoalCompilationFailure("COMPOUND_ACTION_SOURCE_UNDECLARED", str(action.get("type")))
        entry = registry.get(source_cid) if source_cid else None
        result_fields = (entry.get("result_fields") or []) if isinstance(entry, Mapping) else _native_result_fields(action, [])
        specs.append({
            "action": action,
            "source_capability_id": source_cid,
            # Specialized pinned compound compilers perform their own literal/structured
            # grammar checks; the generic token-overlap guard is applied to front-split
            # capability clauses, not to their internal action lowering.
            "goal_clause": None,
            "inputs": {},
            "context_paths": list(context_paths),
            "cycle_offset": 0,
            "step_index": index,
            "role": "PINNED_COMPOUND_ACTION",
        })
        for output_path, _field in _action_output_bindings(action, result_fields):
            if output_path not in context_paths:
                context_paths.append(output_path)
    result = _build_execution_dag(
        specs,
        registry,
        root,
        original_goal,
        initial_context_paths=initial_context_paths,
        clauses=clauses,
        compiled_parts=parts,
        rules=rules,
        compiler_mode="FRONT_COMPOUND_EXECUTION_DAG",
    )
    result["source_compiler_mode"] = compiled.get("compiler_mode")
    result["source_target_effects"] = list(compiled.get("target_effects") or [])
    output_rules = list((result.get("front_compiler") or {}).get("rules_applied") or [])
    output_rules.append("F14_PINNED_COMPOUND_PLAN_ROUTED_THROUGH_LIVE_DAG")
    result["front_compiler"] = {"schema": SCHEMA, "rules_applied": list(dict.fromkeys(output_rules))}
    return result


def _compile_clauses(
    clauses: list[str],
    admissible: Mapping[str, Mapping[str, Any]],
    root: pathlib.Path,
    rules: list[str],
    *,
    original_goal=None,
    initial_context_paths=None,
) -> dict[str, Any]:
    registry = routable_registry(admissible)
    parts: list[dict[str, Any]] = []
    step_specs: list[dict[str, Any]] = []
    context_paths = [str(path) for path in initial_context_paths or []]
    for clause_index, clause in enumerate(clauses):
        sub = compile_goal(
            clause,
            admissible,
            root,
            context_paths=context_paths,
            future_clauses=clauses[clause_index + 1:],
        )
        actions = _actions_of(sub, registry)
        if not actions:
            raise GoalCompilationFailure("GOAL_COMPILATION_NO_EXECUTABLE_CLAUSE", str(clause_index))
        base_cycle = len(step_specs)
        inputs = _context_inputs_from(sub)
        part = {
            "index": clause_index,
            "subgoal": clause,
            "mode": sub.get("compiler_mode"),
            "selected_capability": sub.get("selected_capability"),
            "inputs": inputs,
            "output_paths": [],
            "planner_capability_ids": [],
        }
        for local_index, action in enumerate(actions):
            source_cid = _action_capability_id(action, sub, registry)
            if source_cid and source_cid not in registry:
                raise GoalCompilationFailure("COMPOUND_ACTION_SOURCE_NOT_ADMISSIBLE", source_cid)
            source_entry = registry.get(source_cid) if source_cid else None
            declared_fields = list(source_entry.get("result_fields") or []) if isinstance(source_entry, Mapping) else []
            if not source_cid and action.get("type") not in COMPOUND_NATIVE_ACTION_TYPES:
                raise GoalCompilationFailure("COMPOUND_ACTION_SOURCE_UNDECLARED", str(action.get("type")))
            spec = {
                "action": action,
                "source_capability_id": source_cid,
                "goal_clause": clause,
                "inputs": inputs,
                "context_paths": list(context_paths),
                "cycle_offset": base_cycle,
                "step_index": clause_index,
            }
            step_specs.append(spec)
            part["planner_capability_ids"].append(f"front.compound.action.{len(step_specs) - 1}")
            for output_path, _field in _action_output_bindings(action, declared_fields):
                if output_path not in part["output_paths"]:
                    part["output_paths"].append(output_path)
                if output_path not in context_paths:
                    context_paths.append(output_path)
        parts.append(part)
    full_goal = str(original_goal if original_goal is not None else " ".join(clauses))
    planned = _build_execution_dag(
        step_specs,
        registry,
        root,
        full_goal,
        initial_context_paths=initial_context_paths,
        clauses=clauses,
        compiled_parts=parts,
        rules=rules,
        compiler_mode="FRONT_COMPOUND_EXECUTION_DAG",
        target_effects=None,
    )
    return planned


def compile_goal(
    goal: str,
    admissible: Mapping[str, Mapping[str, Any]],
    root: pathlib.Path,
    *,
    context_paths=None,
    future_clauses=None,
) -> dict[str, Any]:
    """Front compile, optionally forwarding artifacts produced by earlier clauses."""
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

    clauses = sentence_clauses(text)
    # F5: a literal route captured several clauses; compile every clause and preserve
    # the producer paths instead of allowing a sentence-final literal to swallow them.
    if compiled is not None and compiled.get("compiler_mode") in _LITERAL_MODES and len(clauses) >= 2:
        return _compile_clauses(
            clauses, admissible, root, rules,
            original_goal=text,
            initial_context_paths=context_paths,
        )

    selected = (compiled or {}).get("selected_capability") if compiled else None
    single_shape = bool(compiled) and compiled.get("compiler_mode") == "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH" and selected

    # Any ordinary compound/plain route is decomposed before a whole-goal token match
    # can hide or swallow later actions. Purpose-built controller plans emitted by the
    # pinned compiler retain their specialized lowering below.
    if len(clauses) >= 2 and (compiled is None or single_shape or compiled.get("compiler_mode") in _LITERAL_MODES):
        return _compile_clauses(
            clauses, admissible, root, rules,
            original_goal=text,
            initial_context_paths=context_paths,
        )
    if (
        compiled is not None
        and len(clauses) >= 2
        and isinstance(compiled.get("controller_actions"), list)
        and compiled.get("compiler_mode") != "FRONT_COMPOUND_EXECUTION_DAG"
    ):
        return _plan_existing_compound(compiled, admissible, root, text, rules, context_paths)

    if single_shape or compiled is None:
        future = _future_artifacts(text, root, context_paths)
        # F3: a goal that names a file to be produced is served by a tool that can write a file
        preferred = [c for c in ranked if _output_keys(registry[c[2]])] if future else []
        if future and preferred:
            rules.append("F3_ARTIFACT_WRITERS_PREFERRED")
        pool = preferred or ranked
        best = pool[0] if pool else None
        if best is not None and selected != best[2]:
            entry = registry[best[2]]
            try:
                inputs = bind_all_inputs(
                    text, entry, root,
                    context_paths=context_paths,
                    future_clauses=future_clauses,
                )
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
        if context_paths:
            for key in input_keys(registry[selected]):
                forwarded = _context_path_for_input(key, context_paths)
                if forwarded is not None:
                    compiled["inputs"][key] = forwarded
        if repair_output_collisions(text, compiled["inputs"], root, context_paths=context_paths):
            rules.append("F10_OUTPUT_NEVER_AN_INPUT_FILE")
            for action in compiled.get("actions") or []:
                args = action.get("args") if isinstance(action, dict) else None
                if isinstance(args, dict):
                    for k, v in compiled["inputs"].items():
                        if k in args:
                            args[k] = v
    compiled["front_compiler"] = {"schema": SCHEMA, "rules_applied": rules}
    return compiled
