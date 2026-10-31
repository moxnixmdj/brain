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
import difflib
import hashlib
import os
import pathlib
import re
import sys
import zlib
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_DECLARED_INPUT_DERIVATION_V1"
# "from <A> to <B>" -- the two halves are bounded by another role word or the end
# of the clause, so the pair is read off the sentence, never assembled.
_FROM_TO = re.compile(r"\bfrom\s+([^\s,;]+?)\s+(?:in)?to\s+([^\s,;]+)", re.I)
# "<noun> <name>" -- "the function line_total", "the class Cart".  The name is
# read off the sentence and then PROVED against the file's own AST.
# The CREATION grammar, in one place.  "Add a function total_cents(item) to <path>
# that returns price_cents * qty, export it from <path>, and add a test for it in
# <path>" spells every slot it needs: a name, a parameter list, the expression it
# returns, and the three files.  Each is read VERBATIM; a parameter list that is
# not a list of identifiers, or an expression that does not parse, yields no
# value and the binder refuses instead of synthesising something the sentence did
# not say.
_ADDED_FUNCTION = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.I)
_RETURNS_EXPR = re.compile(r"\breturns?\s+(.+?)\s*(?:,|\.\s|$)", re.I)
_EXPORT_FROM = re.compile(r"\bexports?\b[^.\n]{0,40}?\bfrom\s+([^\s,;]+)", re.I)
_CREATED_TEST = re.compile(
    r"\badd(?:s|ing)?\s+(?:a|an|the)?\s*tests?\b[^.\n]{0,50}?\bin\s+([^\s,;]+)", re.I)
# The gate for every rule below that fills a slot for a function the sentence ASKS
# FOR: an ordinary sentence that merely mentions "the function line_total" must
# gain no slot it did not state.  Measured 2026-10-31: without the gate, five
# test-selection rows bound `symbol` on a repair sentence and the selector became
# ambiguous where it selected one relevant capability.
_CREATES_A_FUNCTION = re.compile(
    r"\b(?:add|create|write|implement|define)\w*\b[^.\n]{0,60}?\bfunction\b", re.I)
# "Add a parameter qty with a default value to the function line_total".
_ADDED_PARAM = re.compile(
    r"\b(?:add|insert|give)\w*\b[^.\n]{0,80}?\bparameters?\s+"
    r"(?:named\s+)?[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?", re.I)


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
    "default_expr", "export_in_init", "generate_unit_tests", "synthesize_regression_test",
    "min_coverage_ratio", "min_kill_ratio", "repeats", "tolerance", "algorithm",
    "search_seed", "time_budget_s", "limit",
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
    "remove the unused", "move the function", "move the class", "move symbol",
    "add a parameter", "add parameter", "add a function", "implement a function",
    "implement function", "create a function", "regression test", "caller",
    "circular import", "import cycle", "bisect", "slower", "mutation", "taint", "untrusted",
    "flaky", "intermittently", "deprecated", "sql injection",
    "linearithmic", "unused", "race condition", "are failing",
    "security gate", "type gate", "coverage gate", "mutation gate", "perf gate", "static triage",
    "changed lines", "synthesize",
    # The other half of software work: CREATING.  A request to add a function and
    # test it is software engineering with a stated signature, expression and
    # files, and the derivations below fill those slots from exactly that
    # evidence.  Measured 2026-10-31: without these phrases the feature request
    # was not SWE in scope at all, so the contract was never derived and the
    # capability that exists for it could not be reached.
    "add a function", "export it from", "add a test for", "add a parameter",
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


_ADAPTER_DEFAULTS_CACHE: dict[tuple[str, int, int, str], dict[str, str]] = {}
_PARSED_TREE_CACHE: dict[tuple[str, int, int], ast.Module] = {}


def adapter_defaulted_keys(entry: Mapping[str, Any], root: pathlib.Path) -> dict[str, str]:
    """Keys the adapter itself defaults, proved from its source AST (O(|AST|) + mtime-memoized)."""
    from canonical.runtime import capability_type_surface_v1 as surface

    try:
        adapter = surface.resolve_adapter(entry, root)
    except Exception:
        return {}
    if adapter is None or not adapter.is_file():
        return {}
    try:
        st = adapter.stat()
        root_resolved = pathlib.Path(root).resolve()
        cache_key = (str(adapter), st.st_mtime_ns, st.st_size, str(root_resolved))
    except OSError:
        return {}
    cached = _ADAPTER_DEFAULTS_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    try:
        tree = ast.parse(adapter.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        _ADAPTER_DEFAULTS_CACHE[cache_key] = {}
        return {}

    # Single O(|AST|) prepass collecting nodes guarded by BoolOp(Or) or If.test.
    guarded_nodes: set[int] = set()
    for parent in ast.walk(tree):
        if isinstance(parent, ast.BoolOp) and isinstance(parent.op, ast.Or):
            for v in parent.values:
                guarded_nodes.add(id(v))
        elif isinstance(parent, ast.If):
            for sub in ast.walk(parent.test):
                guarded_nodes.add(id(sub))

    try:
        rel = str(adapter.relative_to(root_resolved))
    except ValueError:
        rel = adapter.name

    found: dict[str, str] = {}
    nodes = list(ast.walk(tree))
    parents = {child: parent for parent in nodes for child in ast.iter_child_nodes(parent)}
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args):
            continue
        owner = node.func.value
        if not (isinstance(owner, ast.Name) and owner.id == "args"):
            continue
        key = node.args[0]
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        guarded = len(node.args) >= 2 or (id(node) in guarded_nodes)
        low = key.value.lower()
        if guarded and key.value in _CONFIGURATION_SLOTS \
                and not any(word in low for word in ("output", "result", "report")):
            found.setdefault(key.value, f"{rel}:{node.lineno}")
    _ADAPTER_DEFAULTS_CACHE[cache_key] = found
    return dict(found)


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
    base = (pathlib.Path(root) / source_rel).parent
    repo = pathlib.Path(root)
    for _ in range(max_up + 1):
        if _holds_tests(base):
            try:
                rel = base.resolve().relative_to(repo.resolve())
            except ValueError:
                return None
            return str(rel) if str(rel) != "." else "."
        if base == repo or repo not in base.parents:
            return None
        base = base.parent
    return None


def _tree_of(root: pathlib.Path, rel: str) -> ast.Module:
    """The parsed module (mtime-memoized), or an empty module when unreadable."""
    try:
        p = (pathlib.Path(root) / rel).resolve()
        st = p.stat()
        key = (str(p), st.st_mtime_ns, st.st_size)
        cached = _PARSED_TREE_CACHE.get(key)
        if cached is not None:
            return cached
        mod = ast.parse(p.read_text(encoding="utf-8"))
        if len(_PARSED_TREE_CACHE) > 512:
            _PARSED_TREE_CACHE.clear()
        _PARSED_TREE_CACHE[key] = mod
        return mod
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


def _read_git_loose_obj(git_dir: pathlib.Path, sha: str) -> tuple[str, bytes] | None:
    if len(sha) != 40:
        return None
    obj_p = git_dir / "objects" / sha[:2] / sha[2:]
    if not obj_p.is_file():
        return None
    try:
        raw = zlib.decompress(obj_p.read_bytes())
        nul = raw.index(b"\x00")
        kind = raw[:nul].decode("ascii", errors="replace").split()[0]
        return kind, raw[nul + 1:]
    except Exception:
        return None


def _git_head_tree_blobs(repo_dir: pathlib.Path, prefix: str = "") -> dict[str, bytes] | None:
    git_dir = repo_dir / ".git"
    if not git_dir.is_dir():
        return None
    try:
        head_raw = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head_raw.startswith("ref:"):
            ref_rel = head_raw.split(":", 1)[1].strip()
            ref_p = git_dir / ref_rel
            if not ref_p.is_file():
                return None
            commit_sha = ref_p.read_text(encoding="utf-8").strip()
        else:
            commit_sha = head_raw
        c_obj = _read_git_loose_obj(git_dir, commit_sha)
        if not c_obj or c_obj[0] != "commit":
            return None
        tree_sha = ""
        for line in c_obj[1].decode("utf-8", errors="replace").splitlines():
            if line.startswith("tree "):
                tree_sha = line.split()[1].strip()
                break
        if not tree_sha:
            return None

        blobs: dict[str, bytes] = {}

        def _walk_tree(t_sha: str, cur_prefix: str) -> bool:
            t_obj = _read_git_loose_obj(git_dir, t_sha)
            if not t_obj or t_obj[0] != "tree":
                return False
            buf = t_obj[1]
            idx = 0
            n = len(buf)
            while idx < n:
                sp = buf.index(b" ", idx)
                mode = buf[idx:sp].decode("ascii", errors="replace")
                nul = buf.index(b"\x00", sp + 1)
                name = buf[sp + 1:nul].decode("utf-8", errors="replace")
                entry_sha = buf[nul + 1:nul + 21].hex()
                idx = nul + 21
                rel_name = f"{cur_prefix}{name}"
                if mode == "40000" or mode == "040000":
                    if not _walk_tree(entry_sha, rel_name + "/"):
                        return False
                else:
                    b_obj = _read_git_loose_obj(git_dir, entry_sha)
                    if not b_obj or b_obj[0] != "blob":
                        return False
                    blobs[rel_name] = b_obj[1]
            return True

        return blobs if _walk_tree(tree_sha, prefix) else None
    except Exception:
        return None


def _materialize_git_diff_for_dir(root: pathlib.Path, rel_dir: str) -> tuple[str | None, list[str]]:
    """Pure-Python working-tree vs HEAD unified diff materializer (zero subprocesses)."""
    repo = pathlib.Path(root).resolve()
    target = (repo / rel_dir).resolve()
    if not target.is_dir() or (target != repo and repo not in target.parents):
        return None, []
    head_blobs = _git_head_tree_blobs(target)
    if head_blobs is None:
        return None, []
    diff_chunks: list[str] = []
    changed_rel: list[str] = []
    disk_files: dict[str, bytes] = {}
    for p in sorted(target.rglob("*")):
        if not p.is_file() or ".git" in p.parts or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        rel_in = p.relative_to(target).as_posix()
        try:
            disk_files[rel_in] = p.read_bytes()
        except OSError:
            continue
    for rel_in in sorted(set(head_blobs) | set(disk_files)):
        old_b = head_blobs.get(rel_in)
        new_b = disk_files.get(rel_in)
        if old_b == new_b:
            continue
        changed_rel.append(f"{rel_dir.rstrip('/')}/{rel_in}")
        old_lines = (old_b.decode("utf-8", errors="replace").splitlines(keepends=True) if old_b is not None else [])
        new_lines = (new_b.decode("utf-8", errors="replace").splitlines(keepends=True) if new_b is not None else [])
        from_hdr = f"a/{rel_in}" if old_b is not None else "/dev/null"
        to_hdr = f"b/{rel_in}" if new_b is not None else "/dev/null"
        ud = list(difflib.unified_diff(old_lines, new_lines, fromfile=from_hdr, tofile=to_hdr))
        if ud:
            diff_chunks.append("".join(ud if ud[-1].endswith("\n") else ud + ["\n"]))
    patch_text = "".join(diff_chunks)
    digest = hashlib.sha256((rel_dir + "\0" + patch_text).encode("utf-8")).hexdigest()[:16]
    spool_rel = f"canonical/astra_runtime/tmp/derived_diff_{digest}.patch"
    spool_abs = repo / spool_rel
    spool_abs.parent.mkdir(parents=True, exist_ok=True)
    spool_abs.write_text(patch_text, encoding="utf-8")
    return spool_rel, changed_rel


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
                        if "__pycache__" not in p.parts and _TEST_NAME_RE.search(p.name):
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
            rule = "PATH_DIR_FROM_STATED_FILE_PARENT"
            # src-layout: ``src/app/calc.py`` whose tests live in ``tests/`` needs the
            # directory that CONTAINS both, or the suite cannot import the package by
            # its top-level name and a correct repair reads as red.  Bounded to three
            # ancestors and only taken when the stated file's own directory holds no
            # tests, so a package layout is untouched.
            widened = _project_root(pathlib.Path(root), sources[0])
            if widened and widened != parent:
                parent, rule = widened, "PATH_DIR_NEAREST_ANCESTOR_THAT_OWNS_THE_TESTS"
            out["source_root"] = {"value": parent, "rule": rule,
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
        out["test_argv"] = {"value": [sys.executable, "-B", tests[0]],
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

    # A stated source file is the module.  No module => no row (fail closed).
    if "module" in keys and len(sources) == 1 and sources[0].endswith(".py"):
        out["module"] = {"value": sources[0], "rule": "MODULE_FROM_STATED_SOURCE_FILE",
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
        elif re.search(r"\bextract\b", str(goal or ""), re.IGNORECASE):
            if "new_name" in keys:
                out["new_name"] = {"value": "_extracted_helper", "rule": "EXTRACT_DEFAULT_HELPER_NAME", "evidence": "extract"}
    if re.search(r"\bextract\b", str(goal or ""), re.IGNORECASE):
        for lkey in ("start_line", "end_line"):
            if lkey in keys and lkey not in out:
                out[lkey] = {"value": 0, "rule": "EXTRACT_AUTO_SLICE_REGION", "evidence": "extract"}

    # A symbol slot is PROVED the same way a qualname is, and for the same reason:
    # "Move the function line_total ..." states the name AFTER the noun, so the
    # qualname grammar above ("the <name> function") reads nothing and the move
    # row refused with BINDING_REFUSED:symbol:not_stated.  Exactly one identifier
    # must follow the noun AND be defined at module scope in the stated file.
    py_named = [f for f in sources if f.endswith(".py")]
    if ({"symbol", "name"} & keys) and py_named:
        nouns = _NAMED_AFTER_NOUN.findall(str(goal or ""))
        candidates = [n for n in dict.fromkeys(nouns) if _NAME_RE.match(n)]
        # A move states TWO files and only one of them DEFINES the name; the
        # proof is "defined at module scope in exactly one stated file", which is
        # strictly stronger than "in the one stated file".
        proved = [(f, _node.name) for f in py_named
                  for _node in (getattr(_tree_of(root, f), "body", []) or [])
                  if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and _node.name in candidates]
        if len(proved) == 1:
            for key in ({"symbol", "name"} & keys):
                out[key] = {"value": proved[0][1], "rule": "SYMBOL_PROVED_FROM_STATED_SOURCE_AST",
                            "evidence": f"{proved[0][0]}:{proved[0][1]}"}
    # A repository operation is STATED by its verb, and only one operation may
    # match.  Measured 2026-10-29: `git.repository.operate.v1` declares an `op`
    # slot because a shell pass-through would be a shell, not a capability -- the
    # sentence chooses WHICH git operation, never the argv.  The rules are ordered
    # most-specific-first so that "Show the last three git commits" binds `log`
    # (commits of a history) rather than `show` (one commit's contents); an
    # ambiguous sentence binds nothing and the binder refuses, which is the whole
    # point of an enumerated operation set.
    if "op" in keys:
        stated = [name for name, pattern in _GIT_OPERATION_GRAMMAR
                  if pattern.search(str(goal or ""))]
        # The one DESTRUCTIVE operation needs repository context, not just a verb.
        # Measured 2026-10-29: "Commit the transaction to the database" matched the
        # commit grammar.  Reading the wrong repository is a wrong answer; creating
        # a commit in it is a wrong change, so the bar is higher: the sentence must
        # say where it is committing (git, staged, changes, working tree, branch,
        # repo) or no operation is derived at all.
        if stated == ["commit"] and not _REPOSITORY_CONTEXT.search(str(goal or "")):
            stated = []
        if len(stated) == 1:
            out["op"] = {"value": stated[0], "rule": "GIT_OPERATION_FROM_STATED_VERB",
                         "evidence": stated[0]}

    # A stated COUNT is the limit the sentence asked for: "the last three git
    # commits" is a request for three rows, and answering it with twenty is a
    # different answer.  Only an explicit number word or digit counts, and only
    # next to the noun it counts, so "three regions" never becomes a limit.
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

    # A commit message is the caller's OWN words, so it is copied, never
    # invented.  Two proofs, both from the sentence:
    #   * an operation other than `commit` has no message at all -- the slot is
    #     declared by the row because ONE operation needs it, so deriving "not
    #     applicable" from the operation is a proof, not a default;
    #   * `commit` takes the quoted literal after "message", or the single quoted
    #     literal of the sentence.
    # Measured on main after the git capability landed: the row declares the slot
    # but the surface only binds what derivation supplies, so without this the
    # operation was refused as BINDING_REFUSED:message:not_stated for EVERY git
    # sentence, including the ones that never commit anything.  The commit
    # sentence in the other direction bound op=commit and then died in the adapter
    # with COMMIT_REQUIRES_A_STATED_MESSAGE -- the operation was unreachable
    # through the door while the grammar said it was bindable.
    if "message" in keys:
        text = str(goal or "")
        op_value = (out.get("op") or {}).get("value")
        if op_value and op_value != "commit":
            out["message"] = {"value": "", "rule": "MESSAGE_NOT_APPLICABLE_TO_THIS_OPERATION",
                              "evidence": op_value}
        else:
            m = re.search(r"\bmessage\b\s*(?:is|of|:|=|saying|say|reads)?\s*"
                          r"[`\"'](.+?)[`\"']", text, re.I | re.S)
            value = m.group(1).strip() if m else None
            if value is None and op_value == "commit":
                quoted = [q.strip() for q in re.findall(r"[`\"'](.+?)[`\"']", text) if q.strip()]
                if len(quoted) == 1:
                    value = quoted[0]
            if value:
                out["message"] = {"value": value, "rule": "MESSAGE_FROM_STATED_QUOTED_TEXT",
                                  "evidence": value[:48]}

    # ---- the creation grammar ------------------------------------------------
    # A function the sentence asks to CREATE has no definition to be proved
    # against -- that is the point of an add.  Its name is read off the one
    # "function name(args)" phrase and must NOT already exist in any stated file:
    # a name that is already defined is a rename or an edit, not an addition.
    if ({"symbol", "new_symbol", "function_name", "new_function"} & keys
            and _CREATES_A_FUNCTION.search(str(goal or ""))):
        fn_phrases = _ADDED_FUNCTION.findall(str(goal or ""))
        if len(fn_phrases) == 1:
            _name = fn_phrases[0][0]
            _existing = set()
            for _f in [f for f in sources if f.endswith(".py")]:
                _ft = _tree_of(root, _f)
                if _ft is None:
                    continue
                _existing |= {n.name for n in ast.walk(_ft)
                              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if _NAME_RE.match(_name) and _name not in _existing:
                for key in ({"symbol", "new_symbol", "function_name", "new_function"} & keys):
                    if key not in out:
                        out[key] = {"value": _name, "rule": "CREATED_FUNCTION_NAME_STATED",
                                    "evidence": _name}
    # DESTINATION GRAMMAR: "Add a function f to <path>" names the one file the
    # addition goes INTO even when the same sentence names other files for other
    # roles ("export it from <path2>", "add a test for it in <path3>").  The role
    # word is the evidence: exactly one STATED source file is the operand of
    # "to".  Without this the row refused BINDING_REFUSED:module:not_stated on the
    # very sentence written for it, because the one-file rule only fires when one
    # file is stated.
    _py_stated = [f for f in sources if f.endswith(".py")]
    if ("module" in keys and "module" not in out and len(_py_stated) > 1
            and _CREATES_A_FUNCTION.search(str(goal or ""))):
        _to_hits = [m.group(1).rstrip(".,;:") for m in
                    re.finditer(r"\bto\s+([^\s,;]+)", str(goal or ""), re.I)]
        _exact = [h for h in _to_hits if h in _py_stated]
        if len(_exact) == 1:
            out["module"] = {"value": _exact[0], "rule": "MODULE_FROM_STATED_TO_TARGET",
                             "evidence": _exact[0]}
    # The export target is the file the sentence says to export FROM, matched
    # against the files it actually states.
    if "export_module" in keys and "export_module" not in out:
        _stated_all = set(stated_existing_files(str(goal or ""), pathlib.Path(root)))
        _exp = [m.group(1).rstrip(".,;:") for m in _EXPORT_FROM.finditer(str(goal or ""))]
        _exp = [h for h in _exp if h in _stated_all]
        if len(_exp) == 1:
            out["export_module"] = {"value": _exp[0], "rule": "EXPORT_TARGET_STATED",
                                    "evidence": _exp[0]}
    # The signature and the returned expression, read off the one "function
    # name(args)" phrase and the one "returns X" phrase, verbatim.
    if (({"params", "parameters"} & keys) or ({"body", "expression", "returns"} & keys)) \
            and _CREATES_A_FUNCTION.search(str(goal or "")):
        _fn_phrases = _ADDED_FUNCTION.findall(str(goal or ""))
        if len(_fn_phrases) == 1:
            _fname, _raw_params = _fn_phrases[0]
            _params = [t.strip() for t in _raw_params.split(",") if t.strip()]
            if all(_NAME_RE.match(t) for t in _params):
                for key in ({"params", "parameters"} & keys):
                    out[key] = {"value": _params, "rule": "PARAMS_FROM_STATED_SIGNATURE",
                                "evidence": "%s(%s)" % (_fname, _raw_params.strip())}
                for key in ({"body", "expression", "returns"} & keys):
                    _rets = [r.strip() for r in _RETURNS_EXPR.findall(str(goal or "")) if r.strip()]
                    if len(_rets) == 1:
                        try:
                            ast.parse("_ = (" + _rets[0] + ")", mode="exec")
                        except SyntaxError:
                            continue
                        out[key] = {"value": _rets[0], "rule": "EXPRESSION_STATED_VERBATIM",
                                    "evidence": _rets[0]}
    # The TEST FILE a feature request is told to create does not exist yet, so it
    # can never be in stated_existing_files -- and the slot is still stated.
    if ({"test_paths", "test_path", "test_file"} & keys):
        _created = [c.rstrip(".,;:") for c in _CREATED_TEST.findall(str(goal or ""))]
        _created = [c for c in _created if c.endswith(".py")]
        if len(set(_created)) == 1:
            for key in ({"test_paths", "test_path", "test_file"} & keys):
                if key not in out:
                    value = [_created[0]] if key == "test_paths" else _created[0]
                    out[key] = {"value": value, "rule": "CREATED_TEST_PATH_STATED",
                                "evidence": _created[0]}
    # A tree to edit, when the sentence names the module the addition goes INTO
    # and other files for other roles: that module's own directory is the root
    # the operation is confined to.
    if ("source_root" in keys and "source_root" not in out and "module" in out
            and str((out.get("module") or {}).get("rule") or "") == "MODULE_FROM_STATED_TO_TARGET"):
        _parent = str(pathlib.PurePosixPath(str(out["module"]["value"])).parent)
        if _parent and (pathlib.Path(root) / _parent).is_dir():
            out["source_root"] = {"value": _parent, "rule": "PATH_DIR_FROM_STATED_MODULE",
                                  "evidence": str(out["module"]["value"])}
    # An ADDED parameter is a name the sentence states and the stated function
    # does NOT already declare, which is what makes it an addition rather than a
    # rename.  Both halves are stated evidence: the name from the one
    # add-parameter phrase, the function from the symbol/qualname proofs above,
    # and the check is the parameter list the file really has.
    if "new_param" in keys and "new_param" not in out:
        _added = [n for n in dict.fromkeys(_ADDED_PARAM.findall(str(goal or "")))
                  if _NAME_RE.match(n)]
        _host = str((out.get("symbol") or out.get("qualname") or {}).get("value") or "")
        if len(_added) == 1 and _host:
            for _f in [f for f in sources if f.endswith(".py")]:
                _tf = _tree_of(root, _f)
                if _tf is None:
                    continue
                for _node in ast.walk(_tf):
                    if not isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if _node.name != _host.split(".")[-1]:
                        continue
                    _declared = [x.arg for x in (list(_node.args.args)
                                                 + list(_node.args.kwonlyargs)
                                                 + list(getattr(_node.args, "posonlyargs", []) or []))]
                    if _added[0] in _declared:
                        break
                    out["new_param"] = {"value": _added[0],
                                        "rule": "ADDED_PARAM_STATED_AND_NOT_DECLARED",
                                        "evidence": "%s:%s" % (_f, _host)}
                    break
                if "new_param" in out:
                    break

    # A qualname is not guessed: it is PROVED by parsing the stated source file.
    # If the request names a parameter/symbol, exactly one function in that file
    # must declare it; if the request names a function, exactly one must match.
    # Anything else (zero or several) yields no value and the binder refuses.
    if "qualname" in keys and len(sources) == 1 and sources[0].endswith(".py"):
        wanted_param = (pairs[0][0] if len(pairs) == 1 else None)
        wanted_fn = None
        fn_match = re.search(r"\b(?:the\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+function\b", str(goal or ""), re.I)
        if fn_match and fn_match.group(1).lower() not in ("the", "a", "an", "python", "target", "helper", "existing", "this", "each", "every"):
            wanted_fn = fn_match.group(1)
        tree = _tree_of(root, sources[0])
        if tree.body:
            method_quals: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
            for top in tree.body:
                if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_quals.append((top.name, top))
                elif isinstance(top, ast.ClassDef):
                    for sub in top.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_quals.append((f"{top.name}.{sub.name}", sub))
            defined_fns = {q for q, _ in method_quals} | {n.name for _, n in method_quals}
            if not wanted_fn:
                dotted_hits = {
                    m.group(1)
                    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\b", str(goal or ""))
                    if m.group(1) in defined_fns
                }
                if len(dotted_hits) == 1:
                    wanted_fn = next(iter(dotted_hits))
            if not wanted_fn:
                preps = {
                    m.group(1)
                    for m in re.finditer(r"\b(?:from|in|of|to|function|method)\s+[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?", str(goal or ""), re.I)
                    if m.group(1) in defined_fns
                }
                if len(preps) == 1:
                    wanted_fn = next(iter(preps))
            matches: list[str] = []
            for qname, node in method_quals:
                arg_names = [a.arg for a in (list(node.args.args) + list(node.args.kwonlyargs))]
                if wanted_fn and (qname == wanted_fn or node.name == wanted_fn):
                    matches.append(qname)
                elif not wanted_fn and wanted_param and wanted_param in arg_names:
                    matches.append(qname)
            if len(set(matches)) == 1:
                out["qualname"] = {"value": matches[0], "rule": "QUALNAME_PROVED_FROM_STATED_SOURCE_AST",
                                   "evidence": f"{sources[0]}:{matches[0]}"}

    goal_str = str(goal or "")
    cid_str = str((args or {}).get("capability_id") or "")

    stated_dirs: list[str] = []
    seen_d: set[str] = set()
    for match in _PATH_RE.finditer(goal_str):
        raw_d = match.group(0).rstrip(".,;:)\"'")
        if raw_d in seen_d:
            continue
        seen_d.add(raw_d)
        try:
            cand_d = (pathlib.Path(root) / raw_d).resolve()
            if cand_d.is_dir() and pathlib.Path(root).resolve() in cand_d.parents:
                stated_dirs.append(raw_d)
        except (OSError, ValueError):
            continue

    # Auto-derive intermediate diff_path / anchor_path / worktree_path / changed_paths from stated git repo dir.
    if ({"diff_path", "changed_paths"} & keys) and len(stated_dirs) == 1:
        git_dir_rel = stated_dirs[0]
        if ((pathlib.Path(root) / git_dir_rel / ".git").is_dir()):
            patch_rel, chg_list = _materialize_git_diff_for_dir(root, git_dir_rel)
            if patch_rel is not None:
                if "diff_path" in keys and "diff_path" not in out:
                    out["diff_path"] = {"value": patch_rel, "rule": "DIFF_PATH_MATERIALIZED_FROM_STATED_GIT_TREE", "evidence": git_dir_rel}
                if "anchor_path" in keys and "anchor_path" not in out:
                    out["anchor_path"] = {"value": git_dir_rel, "rule": "ANCHOR_PATH_FROM_STATED_GIT_TREE", "evidence": git_dir_rel}
                if "worktree_path" in keys and "worktree_path" not in out:
                    out["worktree_path"] = {"value": git_dir_rel, "rule": "WORKTREE_PATH_FROM_STATED_GIT_TREE", "evidence": git_dir_rel}
                if "changed_paths" in keys and "changed_paths" not in out and chg_list:
                    out["changed_paths"] = {"value": chg_list, "rule": "CHANGED_PATHS_FROM_STATED_GIT_TREE", "evidence": git_dir_rel}
                if "source_root" in keys and "source_root" not in out:
                    out["source_root"] = {"value": git_dir_rel, "rule": "SOURCE_ROOT_FROM_STATED_GIT_TREE", "evidence": git_dir_rel}

    # Stated existing directories (scoped strictly to multi-file refactor/choreograph/spec capabilities).
    if ("source_root" in keys and "source_root" not in out
            and any(t in cid_str for t in ("rename_symbol", "move_symbol", "add_parameter", "implement_function_spec", "choreograph"))):
        src_dirs = [d for d in stated_dirs if pathlib.PurePosixPath(d).name not in ("tests", "test")]
        if len(src_dirs) == 1:
            chosen_sr = src_dirs[0]
            if "rename_symbol" in cid_str:
                sr_abs = (pathlib.Path(root) / chosen_sr).resolve()
                while (sr_abs / "__init__.py").is_file() and sr_abs.parent != sr_abs:
                    if pathlib.Path(root).resolve() in sr_abs.parent.parents or sr_abs.parent == pathlib.Path(root).resolve():
                        sr_abs = sr_abs.parent
                    else:
                        break
                chosen_sr = sr_abs.relative_to(pathlib.Path(root).resolve()).as_posix()
                if len(pairs) == 1 and ("module" in keys or "qualname" in keys):
                    old_sym = pairs[0][0]
                    scan_dir = (pathlib.Path(root) / src_dirs[0]).resolve()
                    def_files: list[pathlib.Path] = []
                    for py_f in sorted(scan_dir.rglob("*.py")):
                        if "__pycache__" in py_f.parts:
                            continue
                        pt = _tree_of(root, py_f.relative_to(pathlib.Path(root).resolve()).as_posix())
                        if any(
                            isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and nd.name == old_sym
                            for nd in pt.body
                        ):
                            def_files.append(py_f)
                    if len(def_files) == 1:
                        mod_rel = def_files[0].relative_to(pathlib.Path(root).resolve()).as_posix()
                        if "module" in keys:
                            out["module"] = {"value": mod_rel, "rule": "MODULE_UNIQUE_SYMBOL_DEF_IN_STATED_DIR", "evidence": mod_rel}
                        if "qualname" in keys:
                            out["qualname"] = {"value": old_sym, "rule": "QUALNAME_UNIQUE_SYMBOL_DEF_IN_STATED_DIR", "evidence": f"{mod_rel}:{old_sym}"}
            if "choreograph" not in cid_str or re.search(r"\b(?:regression\s+test|race\s+condition|are\s+failing|circular\s+import|unused)\b", goal_str, re.I):
                out["source_root"] = {"value": chosen_sr, "rule": "PATH_DIR_FROM_STATED_SOURCE_DIR",
                                      "evidence": src_dirs[0]}

    # Regression-test synthesis trigger on crossfile choreograph.
    if "choreograph" in cid_str and re.search(r"\bregression\s+test\b", goal_str, re.I):
        out["synthesize_regression_test"] = {
            "value": True, "rule": "REGRESSION_TEST_REQUESTED", "evidence": "regression test",
        }

    # Move-symbol grammar: "Move [the] (function|class|symbol) SYM from SRC.py to DST.py".
    if {"symbol", "source_module", "target_module"} & keys and "source_module" in keys:
        mv_sym = re.search(
            r"\b(?:move|relocate)\s+(?:the\s+)?(?:function|class|symbol)?\s*"
            r"[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?",
            goal_str, re.I,
        )
        mv_paths = re.search(
            r"\bfrom\s+([A-Za-z0-9_./-]+\.py)\s+to\s+([A-Za-z0-9_./-]+\.py)\b",
            goal_str, re.I,
        )
        if mv_sym and mv_paths:
            sym_v = mv_sym.group(1)
            src_m, dst_m = mv_paths.group(1), mv_paths.group(2)
            if _NAME_RE.match(sym_v) and src_m in files:
                if "symbol" in keys:
                    out["symbol"] = {"value": sym_v, "rule": "MOVE_SYMBOL_STATED", "evidence": sym_v}
                if "source_module" in keys:
                    out["source_module"] = {"value": src_m, "rule": "MOVE_SOURCE_MODULE_STATED", "evidence": src_m}
                if "target_module" in keys:
                    out["target_module"] = {"value": dst_m, "rule": "MOVE_TARGET_MODULE_STATED", "evidence": dst_m}
                if "source_root" in keys and "source_root" not in out:
                    p_dir = str(pathlib.PurePosixPath(src_m).parent)
                    if p_dir and (pathlib.Path(root) / p_dir).is_dir():
                        out["source_root"] = {"value": p_dir, "rule": "MOVE_SOURCE_ROOT_FROM_SOURCE_MODULE", "evidence": src_m}

    # Add-parameter grammar: "Add [a] parameter PARAM [with default ...] to [the] [function|method] QUAL in MOD.py".
    if "param_name" in keys:
        ap_m = re.search(
            r"\badd\s+(?:a\s+|an\s+|optional\s+)*parameter\s+[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?",
            goal_str, re.I,
        )
        if ap_m and _NAME_RE.match(ap_m.group(1)):
            out["param_name"] = {"value": ap_m.group(1), "rule": "ADD_PARAMETER_NAME_STATED", "evidence": ap_m.group(1)}
            def_m = re.search(
                r"\bdefault(?:\s+value)?\s*(?:=|of|is)\s*([0-9]+(?:\.[0-9]+)?|True|False|None|'[^']*'|\"[^\"]*\")",
                goal_str, re.I,
            )
            if "default_expr" in keys:
                d_val = def_m.group(1) if def_m else "None"
                out["default_expr"] = {"value": d_val, "rule": "ADD_PARAMETER_DEFAULT_STATED", "evidence": d_val}

    # Implement-function-spec grammar:
    if {"function_name", "signature", "body_expr", "target_module"} <= keys:
        fn_spec = re.search(
            r"\b(?:add|implement|create|synthesize)\s+(?:a\s+|the\s+)?function\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))\s+"
            r"(?:to|in)\s+([A-Za-z0-9_./-]+\.py)\b",
            goal_str, re.I,
        )
        ret_spec = re.search(
            r"\b(?:that\s+|which\s+)?returns?\s+(.+?)"
            r"(?=\s*(?:,\s*(?:and\s+)?export\b|,\s*(?:and\s+)?add\s+(?:a\s+)?test\b|;\s|\.\s|$))",
            goal_str, re.I,
        )
        if fn_spec and (ret_spec or tests):
            fn_nm, fn_sig, tgt_mod = fn_spec.group(1), fn_spec.group(2), fn_spec.group(3)
            body_e = ret_spec.group(1).strip().rstrip(".,;") if ret_spec else "__SYNTHESIZE_FROM_TESTS__"
            if _NAME_RE.match(fn_nm) and body_e:
                out["function_name"] = {"value": fn_nm, "rule": "SPEC_FUNCTION_NAME_STATED", "evidence": fn_nm}
                out["signature"] = {"value": fn_sig, "rule": "SPEC_SIGNATURE_STATED", "evidence": fn_sig}
                out["target_module"] = {"value": tgt_mod, "rule": "SPEC_TARGET_MODULE_STATED", "evidence": tgt_mod}
                out["body_expr"] = {"value": body_e, "rule": "SPEC_RETURN_EXPR_STATED", "evidence": body_e}
                if "source_root" in keys:
                    p_dir = str(pathlib.PurePosixPath(tgt_mod).parent)
                    if p_dir and (pathlib.Path(root) / p_dir).is_dir():
                        out["source_root"] = {"value": p_dir, "rule": "SPEC_SOURCE_ROOT_FROM_TARGET_MODULE", "evidence": tgt_mod}
                init_m = re.search(r"\b([A-Za-z0-9_./-]+/__init__\.py)\b", goal_str)
                if "init_path" in keys:
                    i_val = init_m.group(1) if init_m else ""
                    out["init_path"] = {"value": i_val, "rule": "SPEC_INIT_PATH_STATED", "evidence": i_val or "default"}
                if (init_m or re.search(r"\bexport\b", goal_str, re.I)) and "export_in_init" in keys:
                    out["export_in_init"] = {"value": True, "rule": "SPEC_EXPORT_REQUESTED", "evidence": "export"}
                tst_m = re.search(r"\b([A-Za-z0-9_./-]+/test_[A-Za-z0-9_]*\.py)\b", goal_str)
                if "test_path" in keys:
                    t_val = tst_m.group(1) if tst_m else ""
                    out["test_path"] = {"value": t_val, "rule": "SPEC_TEST_PATH_STATED", "evidence": t_val or "default"}
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
