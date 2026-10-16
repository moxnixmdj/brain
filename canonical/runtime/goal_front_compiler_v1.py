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


def _is_output_key(key: str, entry: Mapping[str, Any] | None = None) -> bool:
    if entry is not None and isinstance(entry, Mapping):
        pb = entry.get("proposal_bindings")
        if isinstance(pb, Mapping) and key in pb and pb[key].get("type") == "effect_result":
            return False
    return key.startswith("output_") or key.split("_")[0] in _OUTPUT_STEMS


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
    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":" + str(len(matching)) + "_type_compatible_existing_files_named")


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
    pinned_keys = [k for k in keys if k in ("text", "goal", "url") or k.endswith("_path")]
    typed_keys = [k for k in keys if k not in pinned_keys]
    inputs: dict[str, Any] = {}
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
        except GoalCompilationFailure:
            if key.endswith("_path") and not _is_output_key(key, entry):
                is_effect_consumer = (
                    isinstance(entry.get("proposal_bindings"), Mapping)
                    and entry["proposal_bindings"].get(key, {}).get("type") == "effect_result"
                )
                if is_effect_consumer and produced_paths:
                    try:
                        inputs[key] = _bind_produced_artifact(goal, key, root, produced_paths)
                    except GoalCompilationFailure:
                        inputs[key] = _bind_path_by_type(goal, key, root, exclude=produced_paths)
                else:
                    try:
                        inputs[key] = _bind_path_by_type(goal, key, root, exclude=produced_paths)
                    except GoalCompilationFailure as type_failure:
                        if not produced_paths:
                            raise
                        try:
                            inputs[key] = _bind_produced_artifact(goal, key, root, produced_paths)
                        except GoalCompilationFailure:
                            raise type_failure
            elif key.endswith("_path"):
                bound = None
                if produced_paths:
                    try:
                        bound = _bind_produced_artifact(goal, key, root, produced_paths)
                    except GoalCompilationFailure:
                        bound = None
                if bound is None:
                    try:
                        bound = _bind_output_by_future(goal, key, root, exclude=produced_paths)
                    except GoalCompilationFailure:
                        bound = None
                if bound is None:
                    if spool is None or cycle is None:
                        raise
                    bound = _spool_path(key, cycle, spool)
                inputs[key] = bound
            else:
                raise
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

    registry = routable_registry(admissible)
    if len(registry) != len(admissible):
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
                inputs = bind_all_inputs(text, entry, root, cycle=0, spool=spool)
            except GoalCompilationFailure as exc:
                best_error = exc
            else:
                rules.append("F1_BEST_CANDIDATE_BOUND_INSTEAD_OF_FALLTHROUGH")
                if any(str(v).startswith(SPOOL_DIR + "/spool_") for v in inputs.values()):
                    rules.append("F13_INTERMEDIATE_SPOOL_ASSIGNED")
                if any(str(inputs[k]) == str(inputs[j]) for k in inputs if _is_output_key(k, entry) for j in inputs if j != k and j.endswith("_path")):
                    raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", best[2] + ":output_path_equals_an_input_path")
                return _single(best[2], entry, inputs, best[0], best[3], rules)
            # the best candidate cannot bind: accept the pinned selection only if it is itself a
            # prose-scored candidate consistent with the goal's artifact; never a fall-through
            consistent = selected in {c[2] for c in pool}
            if not consistent:
                retrieved = _retrieval_first_selection(text, admissible, root, rules)
                if retrieved is not None:
                    return retrieved
                raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", best[2] + ":" + str(best_error.detail))
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
