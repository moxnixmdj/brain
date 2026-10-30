#!/usr/bin/env python3
"""Declared input derivation -- bind human sentences to typed capability contracts.

Why this exists
---------------
Measured on 2026-10-27 (see SWE_HIDDEN_WIRING_MEASUREMENT_20261027_V1.md): the
typed selector ``capability_selection_retrieval_v1.select`` shortlists the RIGHT
software-engineering capability for an ordinary request, then refuses it with
``BINDING_REFUSED:<slot>:not_stated``.  Two whole classes of slot are missing,
and both are already solved machinery in this repository:

1. ADAPTER-DEFAULTED slots.  ``python_refactor_rename_parameter.py:247-249`` reads
   ``args.get("python_executable") or sys.executable`` -- the adapter owns the
   default -- yet the registry declares ``python_executable`` as a required
   ``${input.python_executable}``.  PR #6272 removed three such slots by hand for
   two capabilities and measured the fix.  This module does it mechanically for
   every adapter, by reading the adapter's own AST.  A slot is dropped only when
   the adapter itself proves it supplies a fallback; the default is never
   invented here.

2. EVIDENCE-DERIVED slots.  A human says "fix calc.py", which states a FILE; the
   repair loop declares ``source_root`` (a DIRECTORY).  The only directory the
   sentence determines is that file's parent.  Likewise a stated test file
   determines the test command, and "rename old_price to price" states both the
   old and the new name.  Each derivation below is a function of bytes the
   sentence actually states; an ambiguous statement yields NO value and the
   binder still fails closed.  Nothing is guessed, nothing is generated.

This module is a REUSE/ADAPT of three existing hidden mechanisms:
  * ``capability_type_surface_v1`` (ARGV / PATH_DIR slot types and KEY_ALIASES);
  * ``goal_front_compiler_v1`` (the pinned binder, left byte-for-byte unchanged);
  * ``capability_selection_retrieval_v1.admit`` (typed admission, the caller).

Zero model, zero network, zero spend.  It changes no registry row and no kernel.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_DECLARED_INPUT_DERIVATION_V1"

# ONLY configuration knobs may be defaulted away.  A path/root/argv/dir/file
# slot is SEMANTIC: even when the adapter has a fallback, dropping it let the
# binder bind an output path onto the user's source file (measured by the
# mutation test in test_declared_input_derivation_v1.py).  Those slots must be
# stated by the sentence or derived from stated evidence -- never defaulted.
_CONFIGURATION_SLOTS = frozenset({
    "python_executable", "timeout_s", "run_tests", "max_rounds", "max_files",
    "max_candidates", "max_total_candidates", "max_candidates_per_file",
    "max_edits", "max_pair_candidates", "max_symbols_per_file",
    "mutations_per_file", "pattern", "budget", "top_k", "seed", "verbose", "strict",
})

# Scope, measured not assumed: typed-admission pins for receipt-projected
# capabilities (brain.module.function.invoke etc.) broke when derivation was
# applied to every goal.  Only an explicit software-engineering request to a
# software-engineering capability takes this path; everything else keeps the
# byte-for-byte original admission gate.
SWE_CID_PREFIXES = ("python.", "code.", "software.", "evidence.oracle.", "orchestration.verify.")
_SWE_VERBS = (
    "rename", "repair", "fix", "bug", "broken", "refactor", "extract function",
    "lint", "type-check", "typecheck", "review", "localize", "traceback",
    "scaffold", "generate test", "failing test", "unit test", "patch",
)


def is_swe_request(goal: str) -> bool:
    """An explicit software-engineering request, not a generic module call."""
    text = str(goal or "").lower()
    return any(verb in text for verb in _SWE_VERBS)

_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+")
_TEST_NAME_RE = re.compile(r"(^|/)(test_[^/]*|[^/]*_test)\.(py|js|ts|go|rs)$")
_SOURCE_SUFFIXES = (".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".rb")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# "rename [the] [parameter|symbol|function] OLD to NEW" / "into a new function named NEW".
_RENAME_OLD_NEW = re.compile(
    r"\brename\b[^.?!]*?\b(?:parameter|symbol|function|argument|variable)?\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s+(?:to|as|into)\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    re.IGNORECASE,
)
_NAMED_NEW = re.compile(
    r"\b(?:new\s+(?:function|parameter|symbol|name)\s+named|named)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE,
)


def stated_existing_files(goal: str, root: pathlib.Path) -> list[str]:
    """Paths the sentence states that really exist as files, in first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for match in _PATH_RE.finditer(str(goal or "")):
        raw = match.group(0).rstrip(".,;:)\"'")
        if raw in seen:
            continue
        seen.add(raw)
        try:
            candidate = (pathlib.Path(root) / raw).resolve()
            if candidate.is_file() and pathlib.Path(root).resolve() in candidate.parents:
                out.append(raw)
        except (OSError, ValueError):
            continue
    return out


def adapter_defaulted_keys(entry: Mapping[str, Any], root: pathlib.Path) -> dict[str, str]:
    """Keys the adapter itself defaults, proved from its source AST.

    A key qualifies only when the adapter reads it with ``args.get(<key>)`` AND
    that read is guarded by an ``or <fallback>`` or a positional default.  The
    evidence string is ``<relative path>:<line>`` so a reviewer can re-check it.
    """
    from canonical.runtime import capability_type_surface_v1 as surface

    try:
        adapter = surface.resolve_adapter(entry, root)
    except Exception:  # an unresolvable adapter declares no defaults we can prove
        return {}
    if adapter is None or not adapter.is_file():
        return {}
    try:
        tree = ast.parse(adapter.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return {}
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args):
            continue
        owner = node.func.value
        if not (isinstance(owner, ast.Name) and owner.id == "args"):
            continue
        key = node.args[0]
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        # A default is proved by: a second positional arg, an `or` fallback on
        # this very call, or an `if args.get(key)` guard (presence-optional).
        guarded = len(node.args) >= 2
        for parent in ast.walk(tree):
            if isinstance(parent, ast.BoolOp) and isinstance(parent.op, ast.Or) and node in parent.values:
                guarded = True
                break
            if isinstance(parent, ast.If) and node in ast.walk(parent.test):
                guarded = True
                break
        # Scope is declaration-driven: only a proven configuration knob, never
        # an output (the stated destination is the acceptance promise) and never
        # a semantic path/root/argv slot.
        low = key.value.lower()
        if guarded and key.value in _CONFIGURATION_SLOTS \
                and not any(word in low for word in ("output", "result", "report")):
            try:
                rel = str(adapter.relative_to(pathlib.Path(root).resolve()))
            except ValueError:
                rel = adapter.name
            found.setdefault(key.value, f"{rel}:{node.lineno}")
    return found


def _holds_tests(directory: pathlib.Path) -> bool:
    """True when ``directory`` itself contains test files, or a ``tests``/``test`` child does.

    Streams and stops at the first hit, so the check costs one ``readdir`` on a real
    project and nothing more.  It is a fact about the tree, not an inference.
    """
    try:
        for child in directory.iterdir():
            if child.is_file() and _TEST_NAME_RE.search(child.name):
                return True
            if child.is_dir() and child.name in {"tests", "test"}:
                for inner in child.iterdir():
                    if inner.is_file() and _TEST_NAME_RE.search(inner.name):
                        return True
    except OSError:
        return False
    return False


def _project_root(root: pathlib.Path, source_rel: str, max_up: int = 3) -> str | None:
    """The nearest ancestor of a stated source file that also owns its tests.

    A repository's tests are not always beside the code: ``src/app/calc.py`` with
    ``tests/test_calc.py`` needs the directory that CONTAINS both, because the
    tools that run the suite require the tests to live under the source root and
    the tests import the package by its top-level name.  Measured 2026-10-29:
    with ``source_root`` pinned to the source file's parent, that layout refused
    with NO_TEST_FILES_UNDER_SOURCE_ROOT and the identical bug repaired in the
    flat layout.

    The walk is bounded (3 levels), starts at the file's parent, stops at the
    first ancestor that holds tests, and never leaves the repository.  If the
    file's own directory already holds tests -- the common case -- this returns
    that directory and nothing changes.
    """
    base = (root / source_rel).parent
    base_abs = base if base.is_absolute() else (root / base)
    repo = pathlib.Path(root)
    for _ in range(max_up + 1):
        if _holds_tests(base_abs):
            try:
                rel = base_abs.resolve().relative_to(repo.resolve())
            except ValueError:
                return None
            return str(rel) if str(rel) != "." else "."
        if base_abs == repo or repo not in base_abs.parents:
            return None
        base_abs = base_abs.parent
    return None


def derive(goal: str, entry: Mapping[str, Any], root: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Evidence-backed values for declared slots.  Ambiguity => no row at all."""
    args = ((entry.get("action_template") or {}).get("args") or {})
    keys = {str(k) for k in args} - {"capability_id"}
    files = stated_existing_files(goal, root)
    sources = [f for f in files if f.endswith(_SOURCE_SUFFIXES) and not _TEST_NAME_RE.search(f)]
    tests = [f for f in files if _TEST_NAME_RE.search(f)]
    out: dict[str, dict[str, Any]] = {}
    # DATA-GAP ACQUISITION.  "fix it so its tests pass" states no test path, but
    # it DOES state the source file, and that file's directory is the narrowly
    # determined place its tests live.  Discovering them there is not a guess:
    # the directory is stated evidence, the scan is bounded to that directory,
    # and more than one candidate is still ambiguous (no value is invented).
    discovered_tests = False
    project_root = _project_root(root, sources[0]) if len(sources) == 1 else None
    if not tests and len(sources) == 1:
        # Scan the directory that owns the code AND its tests.  When the file's
        # own directory holds them (the flat layout) project_root is that
        # directory and this is the same scan as before; in a src/ layout it is
        # the directory above both, which is the only place the suite can be.
        scope = [pathlib.Path(root) / project_root] if project_root else []
        scope.append((pathlib.Path(root) / sources[0]).parent)
        found = []
        for parent in scope:
            if not parent.is_dir():
                continue
            try:
                found = sorted(p for p in parent.iterdir()
                               if p.is_file() and _TEST_NAME_RE.search(p.name))
            except OSError:
                found = []
            if found:
                break
            tests_dir = parent / "tests"
            if tests_dir.is_dir():
                try:
                    inner = sorted(p for p in tests_dir.iterdir()
                                   if p.is_file() and _TEST_NAME_RE.search(p.name))
                except OSError:
                    inner = []
                if len(inner) == 1:
                    found = inner
                    break
        if len(found) == 1:
            tests = [str(found[0].relative_to(pathlib.Path(root)))]
            discovered_tests = True

    # A directory slot is satisfied by the parent of the ONE stated source file.
    # When the stated tests live ABOVE that parent (src/ + tests/), the slot is
    # satisfied by the nearest ancestor that owns both, because that is the only
    # directory under which the stated test command can run and be verified.
    if "source_root" in keys and len(sources) == 1:
        parent = str(pathlib.PurePosixPath(sources[0]).parent)
        # Widen ONLY for a contract that consumes tests as well as a source root:
        # that is the contract in which the tests must live under the root (the
        # repair appliers run and verify the stated command from it).  A contract
        # that declares a source root and nothing about tests -- the symbol index,
        # the refactorers -- names the CODE, and widening it would make the index
        # sweep the whole project instead of the package.  Measured: widening
        # unconditionally turned "find every caller" from PASS to fail in the
        # src/ layout while repairing nothing.
        needs_tests_under_root = bool({"test_paths", "test_argv"} & keys) and bool(tests)
        outside = not any(str(pathlib.PurePosixPath(x).parent).startswith(parent) for x in tests)
        widened = project_root if (needs_tests_under_root and outside) else None
        value = widened or parent
        if value and (pathlib.Path(root) / value).is_dir():
            out["source_root"] = {
                "value": value,
                "rule": ("PATH_DIR_FROM_SOURCE_AND_TEST_COMMON_ANCESTOR"
                         if widened else "PATH_DIR_FROM_STATED_FILE_PARENT"),
                "evidence": (",".join([sources[0]] + list(tests)) if widened else sources[0]),
            }
    # A test command slot is satisfied by running the ONE stated test file.
    if "test_argv" in keys and tests:
        # The command must COLLECT the suite, not execute the file.  A test file
        # without an ``if __name__ == "__main__"`` guard runs nothing when it is
        # executed and exits 0, which every repair loop in this repository reads
        # as BASELINE_ALREADY_PASSES -- a false "already passes" for a program
        # that fails its own test (the shared module measures 695 of 2019 such
        # files, 34%).  ``suite_argv`` is the loader form the repair family
        # already uses; this reuses it instead of hand-writing an argv that the
        # runner cannot see into.  Targets stay repo-relative, exactly as before.
        from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import (
            suite_argv,
        )
        out["test_argv"] = {"value": [str(x) for x in suite_argv(sys.executable, *tests)],
                            "rule": ("ARGV_LOADER_FROM_DISCOVERED_TEST_FILES" if discovered_tests
                                     else "ARGV_LOADER_FROM_STATED_TEST_FILES"),
                            "evidence": ",".join(tests)}
    if "test_paths" in keys and tests:
        out["test_paths"] = {"value": list(tests),
                             "rule": ("PATH_LIST_FROM_DISCOVERED_TEST_FILES" if discovered_tests
                                      else "PATH_LIST_FROM_STATED_TEST_FILES"),
                             "evidence": ",".join(tests)}
    if "source_paths" in keys and sources:
        out["source_paths"] = {"value": list(sources), "rule": "PATH_LIST_FROM_STATED_SOURCE_FILES",
                               "evidence": ",".join(sources)}

    # A stated source file is the module.  No module => no row (fail closed).
    if "module" in keys and len(sources) == 1 and sources[0].endswith(".py"):
        out["module"] = {"value": sources[0], "rule": "MODULE_FROM_STATED_SOURCE_FILE",
                         "evidence": sources[0]}
    # Rename grammar: BOTH names must be stated, and exactly one pair may match.
    pairs = _RENAME_OLD_NEW.findall(str(goal or ""))
    if len(pairs) == 1:
        old, new = pairs[0]
        if _NAME_RE.match(old) and _NAME_RE.match(new):
            if "old_param" in keys:
                out["old_param"] = {"value": old, "rule": "RENAME_OLD_NAME_STATED", "evidence": old}
            if "old_symbol" in keys:
                out["old_symbol"] = {"value": old, "rule": "RENAME_OLD_NAME_STATED", "evidence": old}
            for key in ("new_param", "new_symbol", "new_name"):
                if key in keys:
                    out[key] = {"value": new, "rule": "RENAME_NEW_NAME_STATED", "evidence": new}
    else:
        named = _NAMED_NEW.findall(str(goal or ""))
        if len(named) == 1 and _NAME_RE.match(named[0]):
            for key in ("new_param", "new_symbol", "new_name"):
                if key in keys:
                    out[key] = {"value": named[0], "rule": "NEW_NAME_STATED", "evidence": named[0]}

    # A qualname is not guessed: it is PROVED by parsing the stated source file.
    # If the request names a parameter/symbol, exactly one function in that file
    # must declare it; if the request names a function, exactly one must match.
    # Anything else (zero or several) yields no value and the binder refuses.
    if "qualname" in keys and len(sources) == 1 and sources[0].endswith(".py"):
        wanted_param = (pairs[0][0] if len(pairs) == 1 else None)
        wanted_fn = None
        fn_match = re.search(r"\b(?:the\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+function\b", str(goal or ""), re.I)
        if fn_match:
            wanted_fn = fn_match.group(1)
        try:
            tree = ast.parse((pathlib.Path(root) / sources[0]).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            tree = None
        if tree is not None:
            matches: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    arg_names = [a.arg for a in (list(node.args.args) + list(node.args.kwonlyargs))]
                    if wanted_param and wanted_param in arg_names:
                        matches.append(node.name)
                    elif wanted_fn and node.name == wanted_fn:
                        matches.append(node.name)
            if len(set(matches)) == 1:
                out["qualname"] = {"value": matches[0], "rule": "QUALNAME_PROVED_FROM_STATED_SOURCE_AST",
                                   "evidence": f"{sources[0]}:{matches[0]}"}
    return out


def binding_view(goal: str, entry: Mapping[str, Any], root: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return (shadow_entry, derived_values, report) for typed admission.

    The shadow entry removes slots the ADAPTER defaults or the SENTENCE derives,
    so the pinned binder is only asked for values the sentence must still state.
    The derived values are merged back by the caller, with their evidence.
    """
    derived = derive(goal, entry, root)
    defaults = adapter_defaulted_keys(entry, root)
    shadow = dict(entry)
    template = dict(entry.get("action_template") or {})
    args = dict(template.get("args") or {})
    removed = {k: v for k, v in defaults.items() if k in args and k not in derived}
    for key in list(derived) + list(removed):
        args.pop(key, None)
    template["args"] = args
    shadow["action_template"] = template
    values = {k: v["value"] for k, v in derived.items()}
    report = {"schema": SCHEMA, "derived": derived, "adapter_defaulted": removed,
              "derived_count": len(derived), "adapter_defaulted_count": len(removed)}
    return shadow, values, report
