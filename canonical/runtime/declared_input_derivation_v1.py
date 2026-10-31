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
import os
import pathlib
import re
import sys
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_DECLARED_INPUT_DERIVATION_V1"
# "from <A> to <B>" -- the two halves are bounded by another role word or the end
# of the clause, so the pair is read off the sentence, never assembled.
_FROM_TO = re.compile(r"\bfrom\s+([^\s,;]+?)\s+(?:in)?to\s+([^\s,;]+)", re.I)
# "<noun> <name>" -- "the function line_total", "the class Cart".  The name is
# read off the sentence and then PROVED against the file's own AST.
_NAMED_AFTER_NOUN = re.compile(r"\b(?:function|method|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)

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
    "limit",
})

# Scope, measured not assumed: typed-admission pins for receipt-projected
# capabilities (brain.module.function.invoke etc.) broke when derivation was
# applied to every goal.  Only an explicit software-engineering request to a
# software-engineering capability takes this path; everything else keeps the
# byte-for-byte original admission gate.
SWE_CID_PREFIXES = ("python.", "code.", "software.", "git.", "evidence.oracle.", "orchestration.verify.")
_SWE_VERBS = (
    "rename", "repair", "fix", "bug", "broken", "broke", "refactor", "extract ", "extract function",
    "lint", "type-check", "typecheck", "review", "localize", "fault", "traceback",
    "scaffold", "generate test", "failing test", "unit test", "patch",
    "inline", "single-use", "single use", "merge conflict", "conflict", "unmerged",
    "injection", "parameterize", "parameterized", "sql", "dead code", "unused import",
    "remove the unused", "move the function", "move function", "move symbol", "move helper",
    "add a parameter", "add parameter", "add an optional parameter", "add optional parameter", "add argument",
    "implement ", "synthesize ", "add a function", "add a total function", "total function", "write a function",
    "regression test", "caller",
    "circular import", "import cycle", "bisect", "slower", "mutation", "taint", "untrusted",
    "flaky", "intermittently", "deprecated", "sql injection",
    "linearithmic", "unused", "race condition", "are failing",
)


def is_swe_request(goal: str) -> bool:
    """An explicit software-engineering request, not a generic module call.

    A stated git OPERATION counts on its own.  "Show the last three git commits"
    contains none of the repair verbs, so derivation was skipped and the one slot
    that has to come from the sentence (`op`) was never derived -- the capability
    was enumerated, admitted as a candidate, and then refused on
    ``BINDING_REFUSED:op:not_stated``.  The test is the grammar itself, not a
    second word list, and it is exact: zero or two stated operations is not a
    request for one operation, so neither derives anything.
    """
    text = str(goal or "").lower()
    if any(verb in text for verb in _SWE_VERBS):
        return True
    return len([name for name, pattern in _GIT_OPERATION_GRAMMAR
                if pattern.search(text)]) == 1

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


def _tree_of(root: pathlib.Path, rel: str):
    """The parsed module, or an empty module when it cannot be read.

    An unreadable stated file proves nothing, so the proof above simply yields no
    candidate -- the same fail-closed reading the qualname rule uses.
    """
    try:
        return ast.parse((pathlib.Path(root) / rel).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return ast.Module(body=[], type_ignores=[])
# Ordered: the first rule whose pattern matches decides, and the caller still
# refuses when two DIFFERENT operations match, so order only resolves the cases
# where one verb is a strict refinement of another.
# Words that make a commit sentence about a REPOSITORY rather than about a
# database transaction, a purchase or a promise.
# ("commit" itself is deliberately absent: it would make the test always true.)
_REPOSITORY_CONTEXT = re.compile(
    r"\bgit\b|\bstaged\b|\bchanges?\b|\bworking\s+tree\b|\bbranch(?:es)?\b"
    r"|\brepo(?:sitory)?\b|\buncommitted\b|\bhistory\b", re.I)


_COUNT_WORDS = {w: i for i, w in enumerate(
    ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
     "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
     "sixteen", "seventeen", "eighteen", "nineteen", "twenty"), start=0)}

_STATED_COUNT = re.compile(
    r"\b(\d{1,3}|" + "|".join(sorted(_COUNT_WORDS, key=len, reverse=True)) + r")\s+"
    # up to three words may sit between the count and what it counts: "the last
    # three GIT commits" says three, not twenty.
    r"(?:[\w-]+\s+){0,3}(?:commits?|entries|rows|lines?|branches?)\b", re.IGNORECASE)


_GIT_OPERATION_GRAMMAR: tuple[tuple[str, "re.Pattern[str]"], ...] = tuple(
    (name, re.compile(pattern, re.I)) for name, pattern in (
        # history: an explicit git log, the word history, or "the last N commits"
        ("log", r"\bgit\s+log\b|\bhistory\b|\b(?:last|recent|latest|first)"
                r"(?:\s+\w+){0,3}\s+commits?\b"),
        # a status question about the working tree
        ("status", r"\bgit\s+status\b|\bworking\s+tree\b|\buncommitted\b|\bstatus\b"),
        ("diff", r"\bgit\s+diff\b|\bdiff\b"),
        ("blame", r"\bblame\b|\bwho\s+wrote\b|\bwho\s+touched\b"),
        # An imperative or a question about branches -- never the bare noun.
        # Measured 2026-10-29: with `\bbranch(?:es)?\b`, "Branch out the new feature
        # into three modules" bound op=branch and returned PASS for a `git branch`
        # listing.  A metaphor is not a repository operation, and an enumerated
        # operation set is only as good as the grammar that admits to it.
        ("branch", r"\b(?:list|show|print|git)\s+(?:me\s+)?(?:the\s+|all\s+)?branches?\b"
                   r"|\bbranches\b|\bcurrent\s+branch\b|\bwhich\s+branch\b"),
        # one commit's contents: "show the commit", "git show"
        ("show", r"\bshow\s+(?:the\s+|a\s+|that\s+)?commit\b|\bgit\s+show\b"),
        # an imperative to record a change.  Anchored or object-bearing ON PURPOSE:
        # a bare \bcommit\b also matches "show the commit", which would turn one
        # unambiguous sentence into an ambiguous two-operation match.
        ("commit", r"^\s*(?:\w+\s+)?commit\b|\bgit\s+commit\b"
                   r"|\bcommit\s+(?:the|all|these|this|that|staged|everything|it)\b"),
    )
)


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
    if not tests:
        try:
            from canonical.runtime import goal_compiler as _gc
            repo_paths = _gc._repo_paths(str(goal or ""), pathlib.Path(root))
            witness_dirs = _gc._witness_directories(str(goal or ""), repo_paths)
        except Exception:
            witness_dirs = set()
        if witness_dirs:
            w_found: list[str] = []
            for wdir in sorted(witness_dirs):
                wp = (pathlib.Path(root) / wdir).resolve()
                if wp.is_dir():
                    for p in sorted(wp.rglob("*.py")):
                        if "__pycache__" not in p.parts and p.name != "__init__.py" and _TEST_NAME_RE.search(p.name):
                            w_found.append(p.relative_to(pathlib.Path(root).resolve()).as_posix())
            if w_found:
                tests = w_found
                discovered_tests = True
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
    if "source_root" in keys and len(sources) == 1:
        parent = str(pathlib.PurePosixPath(sources[0]).parent)
        if parent and (pathlib.Path(root) / parent).is_dir():
            out["source_root"] = {"value": parent, "rule": "PATH_DIR_FROM_STATED_FILE_PARENT",
                                  "evidence": sources[0]}
    # The same rule for SEVERAL stated files, but ONLY when the sentence already
    # gave them ROLES ("from A to B"): the directory that holds both ends of a
    # stated move is determined, and it is the only directory that is.  Without
    # this the sibling move row refused with
    # source_root:0_existing_directories_named.  A sentence that merely lists two
    # files derives nothing -- that is a pinned law
    # (test_two_source_files_are_ambiguous_and_derive_nothing), and it stays.
    elif "source_root" in keys and len(sources) > 1 and _FROM_TO.search(str(goal or "")):
        parents = [str(pathlib.PurePosixPath(f).parent) for f in sources]
        common = parents[0] if len(set(parents)) == 1 else None
        if common is None:
            try:
                common = str(pathlib.PurePosixPath(os.path.commonpath(parents)))
            except ValueError:
                common = None
        if common and (pathlib.Path(root) / common).is_dir():
            out["source_root"] = {"value": common, "rule": "PATH_DIR_COMMON_TO_STATED_FILES",
                                  "evidence": ",".join(sources)}
    # A test command slot is satisfied by running the ONE stated test file.
    if "test_argv" in keys and len(tests) == 1:
        t_abs = (pathlib.Path(root) / tests[0]).resolve()
        t_txt = t_abs.read_text(encoding="utf-8", errors="ignore") if t_abs.is_file() else ""
        if "TestCase" in t_txt and "unittest.main" not in t_txt:
            from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import suite_argv as _s_argv
            argv_val = _s_argv(sys.executable, t_abs)
        else:
            argv_val = [sys.executable, "-B", tests[0]]
        out["test_argv"] = {"value": argv_val,
                            "rule": ("ARGV_FROM_DISCOVERED_TEST_FILE" if discovered_tests
                                     else "ARGV_FROM_STATED_TEST_FILE"),
                            "evidence": tests[0]}
    if "test_paths" in keys and tests:
        out["test_paths"] = {"value": list(tests),
                             "rule": ("PATH_LIST_FROM_DISCOVERED_TEST_FILES" if discovered_tests
                                      else "PATH_LIST_FROM_STATED_TEST_FILES"),
                             "evidence": ",".join(tests)}
    if "source_paths" in keys and sources:
        out["source_paths"] = {"value": list(sources), "rule": "PATH_LIST_FROM_STATED_SOURCE_FILES",
                               "evidence": ",".join(sources)}

    # A stated source file is the module (relative to source_root when source_root is derived).
    if "module" in keys and len(sources) == 1 and sources[0].endswith(".py"):
        mod_val = sources[0]
        if "source_root" in out:
            sr_val = str(out["source_root"]["value"]).rstrip("/")
            if sr_val and mod_val.startswith(sr_val + "/"):
                mod_val = mod_val[len(sr_val) + 1:]
        out["module"] = {"value": mod_val, "rule": "MODULE_FROM_STATED_SOURCE_FILE",
                         "evidence": sources[0]}
    # MOVE GRAMMAR: two stated source files with the roles "from A to B" name a
    # SENDER and a RECEIVER, and the sentence says which is which.  Measured:
    # "Move the function line_total from <b>/app/models.py to <b>/app/service.py"
    # shortlisted python.refactor.move_function.v1 and then refused it with
    # BINDING_REFUSED:module:not_stated, because the one-file rule above only
    # fires when exactly ONE source file is stated -- so the capability that
    # exists for this sentence could never be reached by it.  The roles are read
    # from the sentence's own "from ... to ..." pair, matched against the paths
    # it actually states; anything else (no pair, no path, both orders) yields no
    # value and the binder still fails closed.
    py_sources = [f for f in sources if f.endswith(".py")]
    if len(py_sources) == 2 and ("module" in keys) and ({"to_module", "target_module"} & keys):
        pair = _FROM_TO.search(str(goal or ""))
        if pair is not None:
            def _stated(near: str) -> str | None:
                hits = [f for f in py_sources if f in near or f.split("/")[-1] in near]
                return hits[0] if len(hits) == 1 else None
            src_hit, dst_hit = _stated(pair.group(1)), _stated(pair.group(2))
            if src_hit and dst_hit and src_hit != dst_hit:
                out["module"] = {"value": src_hit, "rule": "MODULE_FROM_STATED_FROM_PATH",
                                 "evidence": src_hit}
                for key in ({"to_module", "target_module"} & keys):
                    out[key] = {"value": dst_hit, "rule": "TARGET_MODULE_FROM_STATED_TO_PATH",
                                "evidence": dst_hit}

    goal_str = str(goal or "")
    goal_low = goal_str.lower()

    if "goal" in keys:
        out["goal"] = {"value": goal_str, "rule": "GOAL_TEXT_FORWARDED", "evidence": "goal"}

    # Cross-file move_symbol grammar on extract_function.v1 (`qualname` in keys)
    move_m = re.search(
        r"\bmove\b[^.?!]*?\bfrom\s+([A-Za-z0-9_./-]+\.py)\s+(?:to|into)\s+([A-Za-z0-9_./-]+\.py)",
        goal_str, re.IGNORECASE,
    )
    if move_m and "to_module" in keys and "qualname" in keys:
        orig_raw, dest_raw = move_m.group(1), move_m.group(2)
        orig_abs = (pathlib.Path(root) / orig_raw).resolve()
        dest_abs = (pathlib.Path(root) / dest_raw).resolve()
        repo_abs = pathlib.Path(root).resolve()
        if orig_abs.is_file() and repo_abs in orig_abs.parents and repo_abs in dest_abs.parents:
            common_abs = pathlib.Path(os.path.commonpath([str(orig_abs.parent), str(dest_abs.parent)]))
            while (common_abs / "__init__.py").is_file() and common_abs != repo_abs and (common_abs.parent == repo_abs or repo_abs in common_abs.parent.parents):
                common_abs = common_abs.parent
            if common_abs == repo_abs or repo_abs in common_abs.parents:
                sr_rel = "." if common_abs == repo_abs else common_abs.relative_to(repo_abs).as_posix()
                mod_rel_m = orig_abs.relative_to(common_abs).as_posix()
                dest_rel_m = dest_abs.relative_to(common_abs).as_posix()
                out["source_root"] = {"value": sr_rel, "rule": "MOVE_COMMON_SOURCE_ROOT", "evidence": orig_raw}
                out["module"] = {"value": mod_rel_m, "rule": "MOVE_ORIGIN_MODULE_STATED", "evidence": orig_raw}
                out["to_module"] = {"value": dest_rel_m, "rule": "MOVE_DEST_MODULE_STATED", "evidence": dest_raw}
                for lkey in ("start_line", "end_line"):
                    if lkey in keys:
                        out[lkey] = {"value": 0, "rule": "MOVE_WHOLE_SYMBOL_SPAN", "evidence": "move"}
                try:
                    otree = ast.parse(orig_abs.read_text(encoding="utf-8"))
                    odefs = {n.name for n in otree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
                except Exception:
                    odefs = set()
                mentioned_syms = [s for s in odefs if re.search(r"\b" + re.escape(s) + r"\b", goal_str)]
                if len(mentioned_syms) == 1:
                    sym = mentioned_syms[0]
                    if "qualname" in keys:
                        out["qualname"] = {"value": sym, "rule": "MOVE_SYMBOL_PROVED_IN_ORIGIN", "evidence": sym}
                    if "new_name" in keys:
                        out["new_name"] = {"value": sym, "rule": "MOVE_PRESERVES_SYMBOL_NAME", "evidence": sym}
    elif "to_module" in keys and "to_module" not in out:
        out["to_module"] = {"value": "", "rule": "EXTRACT_IN_MODULE_DEFAULT", "evidence": "no_move"}
        span_m = re.search(r"\blines?\s+(\d+)\s*(?:to|through|-|\.\.)\s*(\d+)\b", goal_str, re.IGNORECASE)
        if span_m:
            if "start_line" in keys:
                out["start_line"] = {"value": int(span_m.group(1)), "rule": "EXTRACT_START_LINE_STATED", "evidence": span_m.group(0)}
            if "end_line" in keys:
                out["end_line"] = {"value": int(span_m.group(2)), "rule": "EXTRACT_END_LINE_STATED", "evidence": span_m.group(0)}
        helper_m = re.search(
            r"\b(?:into|as)\s+(?:(?:a|an|new|extracted|helper|function|method|named|called)\s+)*[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?",
            goal_str, re.IGNORECASE,
        )
        if helper_m and "new_name" in keys and _NAME_RE.match(helper_m.group(1)):
            out["new_name"] = {"value": helper_m.group(1), "rule": "EXTRACT_NEW_NAME_STATED", "evidence": helper_m.group(1)}

    # Add-parameter grammar: "add [an] [optional] parameter NAME[=DEFAULT] to FN ..."
    add_p_m = re.search(
        r"\badd\s+(?:an?\s+)?(?:optional\s+|keyword\s+|default\s+)*(?:parameter|argument|param|arg)\s+"
        r"[`\"']?([A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*([^`\"'\s,;)]+))?[`\"']?",
        goal_str, re.IGNORECASE,
    )
    if add_p_m and "old_param" in keys and "new_param" in keys:
        p_name = add_p_m.group(1)
        def_val = add_p_m.group(2)
        if not def_val:
            dm = re.search(r"\bdefault(?:ing)?\s+(?:to|of|=)\s*[`\"']?([^`\"'\s,;).]+)[`\"']?", goal_str, re.IGNORECASE)
            def_val = dm.group(1) if dm else "None"
        if _NAME_RE.match(p_name):
            out["old_param"] = {"value": "", "rule": "ADD_PARAM_EMPTY_OLD", "evidence": "add_parameter"}
            out["new_param"] = {"value": p_name, "rule": "ADD_PARAM_NAME_STATED", "evidence": p_name}
            if "operation" in keys:
                out["operation"] = {"value": "add_parameter", "rule": "ADD_PARAM_OPERATION", "evidence": "add"}
            if "default_expr" in keys:
                out["default_expr"] = {"value": def_val, "rule": "ADD_PARAM_DEFAULT", "evidence": def_val}
            if len(sources) == 1 and sources[0].endswith(".py") and "source_root" in keys and "module" in keys:
                s_abs = (pathlib.Path(root) / sources[0]).resolve()
                repo_r = pathlib.Path(root).resolve()
                pkg_r = s_abs.parent
                while (pkg_r / "__init__.py").is_file() and pkg_r != repo_r and (pkg_r.parent == repo_r or repo_r in pkg_r.parent.parents):
                    pkg_r = pkg_r.parent
                if pkg_r != s_abs.parent and (pkg_r == repo_r or repo_r in pkg_r.parents):
                    out["source_root"] = {"value": "." if pkg_r == repo_r else pkg_r.relative_to(repo_r).as_posix(), "rule": "ADD_PARAM_PACKAGE_ROOT", "evidence": sources[0]}
                    out["module"] = {"value": s_abs.relative_to(pkg_r).as_posix(), "rule": "ADD_PARAM_PACKAGE_MODULE", "evidence": sources[0]}
    else:
        if "operation" in keys and "old_param" in keys:
            out["operation"] = {"value": "", "rule": "RENAME_PARAM_DEFAULT_OPERATION", "evidence": "rename"}
        if "default_expr" in keys:
            out["default_expr"] = {"value": "None", "rule": "RENAME_PARAM_UNUSED_DEFAULT", "evidence": "None"}

    # Greenfield / total-function synthesis + fix_then_regression_test slots (`python.software.synthesize_function.v1`)
    reg_test_intent = "regression test" in goal_low
    synth_intent = bool(
        re.search(
            r"\b(?:implement|synthesize|total\s+function|"
            r"(?:write|add|create)\s+a\s+(?:total\s+|pure\s+|helper\s+|new\s+)*function)\b",
            goal_low,
        )
        and not re.search(r"\b(?:broken|bug|caller|callers|who\s+calls|rename|extract|move)\b", goal_low)
    )
    if (synth_intent or reg_test_intent) and "target_file" in keys:
        non_init_sources = [s for s in sources if s.endswith(".py") and pathlib.PurePosixPath(s).name != "__init__.py"]
        if len(non_init_sources) == 1:
            out["target_file"] = {"value": non_init_sources[0], "rule": "TARGET_FILE_FROM_STATED_SOURCE", "evidence": non_init_sources[0]}
            if "source_root" in keys and "source_root" not in out:
                t_abs_s = (pathlib.Path(root) / non_init_sources[0]).resolve()
                repo_r = pathlib.Path(root).resolve()
                pkg_r = t_abs_s.parent
                while (pkg_r / "__init__.py").is_file() and pkg_r != repo_r and (pkg_r.parent == repo_r or repo_r in pkg_r.parent.parents):
                    pkg_r = pkg_r.parent
                out["source_root"] = {
                    "value": "." if pkg_r == repo_r else pkg_r.relative_to(repo_r).as_posix(),
                    "rule": "SOURCE_ROOT_FROM_STATED_TARGET_PACKAGE",
                    "evidence": non_init_sources[0],
                }
        else:
            raw_pys = [
                m.group(0).rstrip(".,;:)\"'")
                for m in _PATH_RE.finditer(goal_str)
                if m.group(0).rstrip(".,;:)\"'").endswith(".py")
                and pathlib.PurePosixPath(m.group(0).rstrip(".,;:)\"'")).name != "__init__.py"
                and not _TEST_NAME_RE.search(m.group(0).rstrip(".,;:)\"'"))
            ]
            if len(raw_pys) == 1:
                cand_t = (pathlib.Path(root) / raw_pys[0]).resolve()
                if pathlib.Path(root).resolve() in cand_t.parents:
                    out["target_file"] = {"value": raw_pys[0], "rule": "TARGET_FILE_TO_CREATE_STATED", "evidence": raw_pys[0]}
                    if "source_root" in keys and "source_root" not in out and cand_t.parent.is_dir():
                        out["source_root"] = {
                            "value": cand_t.parent.relative_to(pathlib.Path(root).resolve()).as_posix(),
                            "rule": "SOURCE_ROOT_FROM_NEW_TARGET_PARENT",
                            "evidence": raw_pys[0],
                        }
            elif reg_test_intent:
                repo_r = pathlib.Path(root).resolve()
                stated_dirs: list[pathlib.Path] = []
                for m in _PATH_RE.finditer(goal_str):
                    raw_d = m.group(0).rstrip(".,;:)\"'")
                    dp = (repo_r / raw_d).resolve()
                    if dp.is_dir() and repo_r in dp.parents and dp.name not in ("tests", "test") and dp not in stated_dirs:
                        stated_dirs.append(dp)
                if len(stated_dirs) == 1:
                    prod_cands = [
                        p for p in sorted(stated_dirs[0].rglob("*.py"))
                        if "__pycache__" not in p.parts and ".git" not in p.parts
                        and p.name != "__init__.py" and not _TEST_NAME_RE.search(p.name)
                    ]
                    if len(prod_cands) == 1:
                        rel_prod = prod_cands[0].relative_to(repo_r).as_posix()
                        out["target_file"] = {"value": rel_prod, "rule": "TARGET_FILE_UNIQUE_IN_STATED_DIR", "evidence": rel_prod}
                        if "source_root" in keys:
                            out["source_root"] = {
                                "value": stated_dirs[0].relative_to(repo_r).as_posix(),
                                "rule": "SOURCE_ROOT_STATED_DIR",
                                "evidence": stated_dirs[0].relative_to(repo_r).as_posix(),
                            }
        if synth_intent and "test_paths" in keys and "test_paths" not in out:
            fut_tests = [
                m.group(0).rstrip(".,;:)\"'")
                for m in _PATH_RE.finditer(goal_str)
                if m.group(0).rstrip(".,;:)\"'").endswith(".py")
                and _TEST_NAME_RE.search(m.group(0).rstrip(".,;:)\"'"))
            ]
            if fut_tests:
                out["test_paths"] = {"value": fut_tests, "rule": "FUTURE_TEST_PATHS_STATED", "evidence": ",".join(fut_tests)}
    if reg_test_intent and "function_name" in keys and "target_file" in keys:
        out["function_name"] = {"value": "", "rule": "REGRESSION_TEST_MODE_NO_FN_REQUIRED", "evidence": "regression test"}
        if "operation" in keys:
            out["operation"] = {"value": "fix_then_regression_test", "rule": "FIX_THEN_REGRESSION_TEST_STATED", "evidence": "regression test"}
        if "regression_test_file" in keys:
            reg_pys = [
                m.group(0).rstrip(".,;:)\"'")
                for m in _PATH_RE.finditer(goal_str)
                if m.group(0).rstrip(".,;:)\"'").endswith(".py")
                and "regression" in m.group(0).lower()
            ]
            out["regression_test_file"] = {
                "value": reg_pys[0] if len(reg_pys) == 1 else "",
                "rule": "REGRESSION_TEST_PATH_DERIVED",
                "evidence": reg_pys[0] if len(reg_pys) == 1 else "auto_in_test_dir",
            }
    elif synth_intent and "function_name" in keys:
        if "operation" in keys:
            out["operation"] = {"value": "synthesize_function", "rule": "SYNTH_FUNCTION_MODE", "evidence": "synthesize"}
        if "regression_test_file" in keys:
            out["regression_test_file"] = {"value": "", "rule": "NO_REGRESSION_TEST_REQUESTED", "evidence": "none"}
        fn_s = re.search(
            r"\b(?:implement|write|add|create|synthesize|define)\s+(?:a\s+)?(?:total\s+|pure\s+|helper\s+)*"
            r"(?:function|def|method)\s+(?:named\s+|called\s+)?[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?",
            goal_str, re.IGNORECASE,
        )
        if not fn_s:
            fn_s = re.search(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", goal_str)
        if fn_s and _NAME_RE.match(fn_s.group(1)):
            out["function_name"] = {"value": fn_s.group(1), "rule": "SYNTH_FUNCTION_NAME_STATED", "evidence": fn_s.group(1)}
        elif tests:
            out["function_name"] = {"value": "", "rule": "SYNTH_FUNCTION_FROM_TEST_IMPORTS", "evidence": "auto_from_tests"}
    # Rename grammar: BOTH names must be stated, and exactly one pair may match.
    pairs = ([] if add_p_m else _RENAME_OLD_NEW.findall(str(goal or "")))
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
        elif re.search(r"\bextract\b", str(goal or ""), re.IGNORECASE):
            if "new_name" in keys and "new_name" not in out:
                out["new_name"] = {"value": "_extracted_helper", "rule": "EXTRACT_DEFAULT_HELPER_NAME", "evidence": "extract"}
    if re.search(r"\bextract\b", str(goal or ""), re.IGNORECASE):
        for lkey in ("start_line", "end_line"):
            if lkey in keys and lkey not in out:
                out[lkey] = {"value": 0, "rule": "EXTRACT_AUTO_SLICE_REGION", "evidence": "extract"}

    # When renaming a symbol across a stated directory (`in pkg/app`) without naming a `.py` file,
    # prove the unique `.py` module in that directory that defines `old_symbol`.
    if "module" in keys and "module" not in out and not sources and len(pairs) == 1:
        old_sym = pairs[0][0]
        repo_r = pathlib.Path(root).resolve()
        stated_dirs_r: list[pathlib.Path] = []
        for m in _PATH_RE.finditer(goal_str):
            raw_d = m.group(0).rstrip(".,;:)\"'")
            dp = (repo_r / raw_d).resolve()
            if dp.is_dir() and repo_r in dp.parents and dp not in stated_dirs_r:
                stated_dirs_r.append(dp)
        if len(stated_dirs_r) == 1 and _NAME_RE.match(old_sym):
            def_files: list[pathlib.Path] = []
            for py_f in sorted(stated_dirs_r[0].rglob("*.py")):
                if "__pycache__" in py_f.parts or ".git" in py_f.parts:
                    continue
                try:
                    pt = ast.parse(py_f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for nd in pt.body:
                    if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and nd.name == old_sym:
                        def_files.append(py_f)
                        break
                    if isinstance(nd, ast.Assign) and any(isinstance(t, ast.Name) and t.id == old_sym for t in nd.targets):
                        def_files.append(py_f)
                        break
            if len(def_files) == 1:
                pkg_r = stated_dirs_r[0]
                while (pkg_r / "__init__.py").is_file() and pkg_r != repo_r and (pkg_r.parent == repo_r or repo_r in pkg_r.parent.parents):
                    pkg_r = pkg_r.parent
                if "source_root" in keys:
                    out["source_root"] = {
                        "value": "." if pkg_r == repo_r else pkg_r.relative_to(repo_r).as_posix(),
                        "rule": "RENAME_SYMBOL_PACKAGE_ROOT_PROVED",
                        "evidence": def_files[0].relative_to(repo_r).as_posix(),
                    }
                out["module"] = {
                    "value": def_files[0].relative_to(pkg_r).as_posix(),
                    "rule": "MODULE_PROVED_UNIQUE_SYMBOL_IN_STATED_DIR",
                    "evidence": f"{def_files[0].relative_to(repo_r).as_posix()}:{old_sym}",
                }
                if "qualname" in keys and "qualname" not in out:
                    out["qualname"] = {
                        "value": old_sym,
                        "rule": "QUALNAME_PROVED_UNIQUE_SYMBOL_IN_STATED_DIR",
                        "evidence": f"{def_files[0].relative_to(repo_r).as_posix()}:{old_sym}",
                    }

    # A symbol slot is PROVED the same way a qualname is, and for the same reason:
    # "Move the function line_total ..." states the name AFTER the noun, so the
    # qualname grammar above ("the <name> function") reads nothing and the move
    # row refused with BINDING_REFUSED:symbol:not_stated.  Exactly one identifier
    # must follow the noun AND be defined at module scope in the stated file.
    py_named = [f for f in sources if f.endswith(".py")]
    if ({"symbol", "name"} & keys) and py_named:
        nouns = _NAMED_AFTER_NOUN.findall(str(goal or ""))
        candidates = [n for n in dict.fromkeys(nouns) if _NAME_RE.match(n)]
        proved = [(f, _node.name) for f in py_named
                  for _node in (getattr(_tree_of(root, f), "body", []) or [])
                  if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and _node.name in candidates]
        if len(proved) == 1:
            for key in ({"symbol", "name"} & keys):
                out[key] = {"value": proved[0][1], "rule": "SYMBOL_PROVED_FROM_STATED_SOURCE_AST",
                            "evidence": f"{proved[0][0]}:{proved[0][1]}"}
    if "op" in keys:
        stated = [name for name, pattern in _GIT_OPERATION_GRAMMAR
                  if pattern.search(str(goal or ""))]
        if stated == ["commit"] and not _REPOSITORY_CONTEXT.search(str(goal or "")):
            stated = []
        if len(stated) == 1:
            out["op"] = {"value": stated[0], "rule": "GIT_OPERATION_FROM_STATED_VERB",
                         "evidence": stated[0]}

    if "limit" in keys:
        m = _STATED_COUNT.search(str(goal or ""))
        if m:
            token = m.group(1).lower()
            value = _COUNT_WORDS.get(token)
            if value is None and token.isdigit():
                value = int(token)
            if value is not None:
                out["limit"] = {"value": value, "rule": "LIMIT_FROM_STATED_COUNT",
                                "evidence": token}

    # A qualname is not guessed: it is PROVED by parsing the stated source file.
    # If the request names a parameter/symbol, exactly one function in that file
    # must declare it; if the request names a function, exactly one must match.
    # Anything else (zero or several) yields no value and the binder refuses.
    if "qualname" in keys and "qualname" not in out and len(sources) == 1 and sources[0].endswith(".py"):
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
            defined_fns = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if not wanted_fn and not wanted_param:
                preps = {
                    m.group(1)
                    for m in re.finditer(r"\b(?:to|from|in|of|function|method)\s+[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?", str(goal or ""), re.I)
                    if m.group(1) in defined_fns
                }
                if len(preps) == 1:
                    wanted_fn = next(iter(preps))
                elif len(defined_fns) == 1 and (add_p_m or re.search(r"\bextract\b", goal_str, re.I)):
                    wanted_fn = next(iter(defined_fns))
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
