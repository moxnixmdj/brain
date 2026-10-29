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
    # Review-gate thresholds.  Measured 2026-10-29: every gate reads its ratio with
    # ``float(args.get(k) if args.get(k) is not None else <default>)`` -- absence IS the
    # default -- yet the binder demanded the number be spoken in the sentence, so
    # "measure the test coverage of <file>" could not bind a gate that defaults it.
    "min_coverage_ratio", "min_kill_ratio", "max_mutants", "repeats", "tolerance",
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
    # MEASUREMENT requests are software-engineering requests too.  Measured 2026-10-29:
    # "Measure the test coverage of <file>." contains no verb from this list, so derivation
    # never ran, `anchor_path` was never derived, and the coverage gate -- a capability that
    # exists and works -- was unreachable from the sentence that describes it.
    "coverage", "mutation", "mutant", "benchmark", "performance", "audit", "security",
    "vulnerab", "static analysis", "typecheck", "check the",
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
            # ``float(args.get(k) if args.get(k) is not None else 1.0)``: the read sits in a
            # conditional EXPRESSION whose branch is the fallback.  Absence-provided default,
            # proved from source, same as an ``or`` fallback.
            if isinstance(parent, ast.IfExp) and node in ast.walk(parent.test) \
                    and isinstance(parent.test, ast.Compare) \
                    and any(isinstance(op, ast.IsNot) for op in parent.test.ops):
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


# --------------------------------------------------------------------------- #
# a stated FILE reviewed as a CHANGE SET
# --------------------------------------------------------------------------- #
# Measured 2026-10-29, one door call each on a fresh tree::
#
#   "Lint <...>/pkg/calc.py"       FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
#   "Type-check <...>/pkg/calc.py" FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
#   "Run a security audit on <pkg>" FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
#
# with ``BINDING_REFUSED:diff_path:0_type_compatible_existing_files_named`` underneath.  The
# review gates (``python.review.diff_static_triage.v1``, ``..._type_gate``, ``..._security_gate``,
# ``..._coverage_gate``, ``..._mutation_gate``) all declare ``diff_path`` + ``worktree_path``:
# they review the CHANGED LINES of a change set.  Nothing in the registry produces a change set
# from a sentence (census over all 419 rows: the only producer is
# ``python.software.repair.apply.verified.v1``), so 9 capabilities that work are unreachable.
#
# A request to review a FILE is a request to review all of it.  The honest change set for it is
# every line as an ADDITION against an empty baseline -- which is exactly what
# ``git diff --no-index /dev/null <file>`` writes, and what the gate's own parser already treats
# as "the whole file is in scope" (``created`` -> ``[(1, 10**9)]``).  Nothing is invented: the
# content is the file's bytes, the baseline is empty, and the artifact is content-addressed, so
# the same request always produces the same diff and a second run rewrites nothing.
_DERIVED_DIR = "canonical/astra_runtime/tmp/derived"
_MAX_DIFF_BYTES = 1 << 20  # 1 MiB per stated file; beyond that no row (honest refusal)


def _stated_change_set(files: list[str], root: pathlib.Path,
                       base: str | None = None) -> dict[str, Any] | None:
    """A unified diff in which every line of every stated file is new.  Pure in the bytes.

    ``base`` is the directory the diff's paths are relative to, and it must be the SAME directory
    the consuming gate treats as its anchor/worktree.  Measured 2026-10-29: the repository-relative
    paths below were handed to ``python.review.diff_coverage_gate.v1`` with an anchor of the
    package directory, so ``git apply`` planted ``canonical/.../calc.py`` INSIDE a copy of that
    package and the suite (which imports ``calc``) never imported it.  The gate then found the
    changed file absent from the coverage report, counted zero executable changed lines, and
    reported ``gate: PASS`` with ``diff_covered_ratio: 1.0`` -- a passing coverage measurement
    that measured nothing.  Paths and anchor are one decision, not two.
    """
    root = pathlib.Path(root)
    chunks: list[str] = []
    for rel in files:
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            return None
        if len(raw) > _MAX_DIFF_BYTES:
            return None
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
        lines = text.splitlines()
        shown = rel
        if base:
            try:
                shown = str(pathlib.PurePosixPath(rel).relative_to(str(base).strip("./") or "."))
            except ValueError:
                return None
        # THE FILE IS WHAT IT IS, SO THE CHANGE SET REWRITES IT IN PLACE.
        #
        # "Every line is new" was written as a NEW-file diff (``--- /dev/null``).  A gate that
        # APPLIES the change set to a copy of the tree then refuses it: the file it claims to
        # create already exists there.
        #
        #   DIFF_DOES_NOT_APPLY:error: .../_cov_tree_.../calc.py: already exists in working directory
        #
        # (measured 2026-10-29, python.review.diff_coverage_gate.v1).  A whole-file rewrite -- the
        # file's own lines removed and re-added -- states the same thing (the entire file is in
        # scope, every line is the new side) and applies to a tree that already holds it, because
        # the removed lines are its exact content.  Nothing is invented: same bytes, both sides.
        chunks.append("--- a/" + shown)
        chunks.append("+++ b/" + shown)
        chunks.append("@@ -1,%d +1,%d @@" % (max(len(lines), 1), max(len(lines), 1)))
        chunks.extend("-" + line for line in lines)
        if text and not text.endswith("\n"):
            chunks.append("\\ No newline at end of file")
        chunks.extend("+" + line for line in lines)
        if text and not text.endswith("\n"):
            chunks.append("\\ No newline at end of file")
    if not chunks:
        return None
    body = "\n".join(chunks) + "\n"
    import hashlib
    rel_out = "%s/stated_%s.diff" % (_DERIVED_DIR, hashlib.sha256(body.encode("utf-8")).hexdigest()[:16])
    target = root / rel_out
    try:
        if not (target.is_file() and target.read_text(encoding="utf-8") == body):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
    except OSError:
        return None
    return {"value": rel_out, "rule": "DIFF_FROM_STATED_FILES_EVERY_LINE_IS_NEW",
            "evidence": ",".join(files)}


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
    if not tests and len(sources) == 1:
        parent = (pathlib.Path(root) / sources[0]).parent
        try:
            found = sorted(p for p in parent.iterdir()
                           if p.is_file() and _TEST_NAME_RE.search(p.name))
        except OSError:
            found = []
        if len(found) == 1:
            tests = [str(found[0].relative_to(pathlib.Path(root)))]
            discovered_tests = True

    # A directory slot is satisfied by the parent of the ONE stated source file.
    #
    # ``anchor_path`` is the review gates' name for the SAME thing: the directory the tests run
    # from (pytest rootdir).  The coverage/perf/mutation gates all declare it and none of them
    # could be bound, so "measure the test coverage of <file>" had no route at all.  One rule,
    # reused: the sentence states a file, the file states its directory, and the directory must
    # exist.
    for _dir_slot in ("source_root", "anchor_path"):
        if _dir_slot in keys and len(sources) == 1 and _dir_slot not in out:
            parent = str(pathlib.PurePosixPath(sources[0]).parent)
            if parent and (pathlib.Path(root) / parent).is_dir():
                out[_dir_slot] = {"value": parent, "rule": "PATH_DIR_FROM_STATED_FILE_PARENT",
                                  "evidence": sources[0]}
    # A test command slot is satisfied by running the ONE stated test file -- through
    # the repository's OWN suite runner, never by executing the file as a script.
    #
    # Measured 2026-10-29 on `e2d7981`: `[python, "-B", test_file]` exits 0 having run
    # NOTHING when the file carries no `__main__` guard (the same trap
    # `python_test_guided_patch_search_v1.suite_argv` was written for: 695 of 2019
    # unittest files in this repository have no guard).  A repair loop reads that 0 as
    # "the stated test already passes", so "the add function in X is broken, fix it so
    # its tests pass" returned PASS with X byte-identical and its own test red.  The
    # same adapter, given the loader command line, repaired X in place and verified it
    # (applied=True, pre_rc=1, post_rc=0).  One rule, one place: the runner the
    # capability itself uses.
    if "test_argv" in keys and len(tests) == 1:
        from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import (
            suite_argv as _suite_argv,
        )
        runner = _suite_argv(sys.executable, *tests)
        out["test_argv"] = {"value": [sys.executable, "-B"] + [str(x) for x in runner[1:]],
                            "rule": ("ARGV_FROM_DISCOVERED_TEST_FILE_SUITE_RUNNER" if discovered_tests
                                     else "ARGV_FROM_STATED_TEST_FILE_SUITE_RUNNER"),
                            "evidence": tests[0]}
    if "test_paths" in keys and tests:
        out["test_paths"] = {"value": list(tests),
                             "rule": ("PATH_LIST_FROM_DISCOVERED_TEST_FILES" if discovered_tests
                                      else "PATH_LIST_FROM_STATED_TEST_FILES"),
                             "evidence": ",".join(tests)}
    if "source_paths" in keys and sources:
        out["source_paths"] = {"value": list(sources), "rule": "PATH_LIST_FROM_STATED_SOURCE_FILES",
                               "evidence": ",".join(sources)}
    # A review gate reviews a CHANGE SET; a sentence names FILES.  Every stated .py (a test file
    # is a legitimate review target too) becomes one change set in which all of it is new, and the
    # worktree the gate reads the new-side bytes from is the tree the sentence named.
    stated_python = [f for f in files if f.endswith(".py")]
    # ONE decision for three slots: where the change set is rooted, which tree holds the NEW-side
    # bytes, and which directory the tests run from.  They are the parent of the stated file when
    # every stated .py shares one, and the repository root otherwise -- the same value for all
    # three, because a diff whose paths are rooted somewhere other than the gate's anchor is a
    # change set that silently applies to the wrong tree (see _stated_change_set).
    base = "."
    parents = {str(pathlib.PurePosixPath(f).parent) for f in stated_python}
    if len(parents) == 1:
        candidate = parents.pop().strip("./") or "."
        if candidate != "" and (pathlib.Path(root) / candidate).is_dir():
            base = candidate
    if "diff_path" in keys and stated_python:
        change_set = _stated_change_set(stated_python, root, base)
        if change_set is not None:
            out["diff_path"] = change_set
            if "worktree_path" in keys:
                out["worktree_path"] = {"value": base, "rule": "WORKTREE_IS_THE_TREE_THE_SENTENCE_NAMES",
                                        "evidence": ",".join(stated_python)}
            if "anchor_path" in keys:
                out["anchor_path"] = {"value": base, "rule": "ANCHOR_IS_THE_TREES_ROOT_WHOSE_TESTS_RUN",
                                      "evidence": ",".join(stated_python)}

    # A BENCHMARK IS A FILE THAT DEFINES ``bench()``, AND THE STATEMENT NAMES THE MODULE.
    #
    # ``python.review.diff_perf_gate.v1`` declares ``bench_path``: "a repo file defining
    # ``def bench(): ...``".  A sentence says "run a performance review of <module>", never the
    # benchmark's path, so the slot was unbound and one more working capability stayed
    # unreachable.  Discovery is bounded to the directory the sentence states and is by the
    # gate's OWN declared contract (a top-level ``def bench``), not by a name heuristic; two
    # candidates stay ambiguous and yield no row.
    if "bench_path" in keys and (sources or tests):
        parent = (pathlib.Path(root) / (sources or tests)[0]).parent
        found: list[str] = []
        try:
            for candidate in sorted(parent.iterdir()):
                if not (candidate.is_file() and candidate.suffix == ".py"):
                    continue
                try:
                    tree = ast.parse(candidate.read_text(encoding="utf-8", errors="replace"))
                except (OSError, SyntaxError, ValueError):
                    continue
                if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and node.name == "bench" for node in tree.body):
                    found.append(str(candidate.relative_to(pathlib.Path(root))))
        except OSError:
            found = []
        if len(found) == 1:
            # The gate copies ``anchor_path`` and looks for ``bench_path`` INSIDE that copy, so the
            # value must be relative to the same base as the change set -- the same one decision
            # as above.  Measured 2026-10-29: an anchor-relative bench landed as a repo-relative
            # value and the gate refused BENCH_FILE_MISSING on a file that was right there.
            shown = found[0]
            try:
                shown = str(pathlib.PurePosixPath(found[0]).relative_to(str(base).strip("./") or "."))
            except ValueError:
                shown = found[0]
            out["bench_path"] = {"value": shown, "rule": "BENCH_FILE_DEFINING_BENCH_IN_STATED_DIR",
                                 "evidence": found[0] + ":def bench"}
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
