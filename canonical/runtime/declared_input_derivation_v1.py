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
import hashlib
import json
import os
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
    # MEASUREMENT requests are software-engineering requests too.  Measured 2026-10-29:
    # "Measure the test coverage of <file>." contains no verb from this list, so derivation
    # never ran, `anchor_path` was never derived, and the coverage gate -- a capability that
    # exists and works -- was unreachable from the sentence that describes it.
    "coverage", "mutation", "mutant", "benchmark", "performance", "audit", "security",
    "vulnerab", "static analysis", "typecheck", "check the",
    # IMPACT ANALYSIS.  "Which tests do I need to run after changing <f>?" is an explicit
    # software-engineering question and contains none of the verbs above, so derivation never
    # ran and the impact row was refused on ``changed_paths`` -- the file the sentence names.
    "which tests", "affected by", "impact of", "after changing",
    # EXTRACTION AND INLINING ARE CODE TRANSFORMS, AND THE PLAIN VERB IS TOO GENERIC:
    # "extract the text from a PDF" is not this.  The phrases below only fire when the sentence
    # states an extraction INTO CODE, which is exactly the shape ``python.refactor.extract_function``
    # declares -- and without them the derivation never ran for the extract family at all, so the
    # row could not bind a coordinate it can now compute (measured 2026-10-30).
    "into a new function", "into a function", "extract the statement", "extract the statements",
    "extract the expression", "extract the block", "inline the function", "refactor the",
    # The verbs the job is made of that were missing.  Measured: "Inline the
    # single-use helper ...", "Remove the SQL injection ..." and "Resolve the merge
    # conflict ..." are ordinary software-engineering sentences, and every one of
    # them was refused the derivation path -- so a row that exists could never be
    # reached by the sentence that names it.  This list is only a GATE (does this
    # request belong on the typed SWE path at all); a listed verb still binds
    # nothing by itself, and ambiguity still yields no value.
    "inline", "single-use", "single use", "merge conflict", "conflict", "unmerged",
    "injection", "parameterize", "parameterized", "sql", "dead code", "unused import",
    "remove the unused", "move the function", "add a parameter", "caller",
    "circular import", "import cycle", "bisect", "slower", "mutation", "taint", "untrusted",
    "flaky", "intermittently", "deprecated", "sql injection",
    "linearithmic", "unused", "race condition", "are failing",
    # The other half of software work: CREATING.  A request to add a function and
    # test it is software engineering with a stated signature, expression and
    # files, and the derivations below fill those slots from exactly that
    # evidence.  Measured 2026-10-31: without these phrases the feature request
    # was not SWE in scope at all, so the contract was never derived.
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
# PEOPLE QUOTE IDENTIFIERS.  ``Rename the symbol `mul` to `multiply`` is the same request as
# "rename the function mul to multiply", and the bare-word pattern refused it: the backtick stopped
# the name match, so no plan was decisive and a read-only symbol index stayed the answer.  Measured
# 2026-10-30.  One optional quote character on either side -- backtick, single, double -- is
# accepted; nothing else about the sentence is relaxed.
_QUOTE = r"[`\'\"]?"
_RENAME_OLD_NEW = re.compile(
    r"\brename\b[^.?!]*?\b(?:parameter|symbol|function|argument|variable)?\s*"
    + _QUOTE + r"([A-Za-z_][A-Za-z0-9_]*)" + _QUOTE + r"\s+(?:to|as|into)\s+"
    + _QUOTE + r"([A-Za-z_][A-Za-z0-9_]*)" + _QUOTE + r"\b",
    re.IGNORECASE,
)
_NAMED_NEW = re.compile(
    r"\b(?:new\s+(?:function|parameter|symbol|name)\s+named|named)\s+" + _QUOTE +
    r"([A-Za-z_][A-Za-z0-9_]*)" + _QUOTE + r"\b", re.IGNORECASE,
)

# "from <A> to <B>" -- the two halves are bounded by another role word or the end of the clause,
# so the pair is read off the sentence, never assembled.  Read by the MOVE grammar: two stated
# paths with roles are a sender and a receiver, and the sentence says which is which.
_FROM_TO = re.compile(r"\bfrom\s+([^\s,;]+?)\s+(?:in)?to\s+([^\s,;]+)", re.I)
# "<noun> <name>" -- "the function line_total", "the class Cart".  The name is read off the
# sentence and then PROVED against the file's own AST.
# The CREATION grammar, in one place.  "Add a function total_cents(item) to <path>
# that returns price_cents * qty, export it from <path>, and add a test for it in
# <path>" spells every slot it needs.  Each is read VERBATIM; a parameter list that
# is not identifiers, or an expression that does not parse, yields no value and the
# binder refuses instead of inventing something the sentence did not say.
_ADDED_FUNCTION = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.I)
_RETURNS_EXPR = re.compile(r"\breturns?\s+(.+?)\s*(?:,|\.\s|$)", re.I)
_EXPORT_FROM = re.compile(r"\bexports?\b[^.\n]{0,40}?\bfrom\s+([^\s,;]+)", re.I)
_CREATED_TEST = re.compile(
    r"\badd(?:s|ing)?\s+(?:a|an|the)?\s*tests?\b[^.\n]{0,50}?\bin\s+([^\s,;]+)", re.I)
# The gate for every rule below: a sentence that merely mentions "the function
# line_total" must gain no slot it did not state.  Measured 2026-10-31: without
# the gate, five test-selection rows bound `symbol` on a repair sentence.
_CREATES_A_FUNCTION = re.compile(
    r"\b(?:add|create|write|implement|define)\w*\b[^.\n]{0,60}?\bfunction\b", re.I)
# "Add a parameter qty with a default value to the function line_total".
_ADDED_PARAM = re.compile(
    r"\b(?:add|insert|give)\w*\b[^.\n]{0,80}?\bparameters?\s+"
    r"(?:named\s+)?[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?", re.I)


_NAMED_AFTER_NOUN = re.compile(r"\b(?:function|method|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


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



# ---------------------------------------------------------------------------------------------
# A CROSS-FILE EDIT PLAN IS A VALUE THE SENTENCE AND THE TREE TOGETHER PROVE.
#
# `python.source.crossfile_edit.choreograph.v1` is the one capability that answers "what does
# renaming this symbol really touch" -- the question grep gets wrong and the step every engineer
# takes before a rename.  It declares `edits_path`, `source_root` and `output_path`, and nothing in
# the pipeline ever produced an `edits_path`, so measured 2026-10-30 the three ordinary sentences
# for it all refused:
#
#   "Which files must change to rename the symbol `mul` to `multiply` in <dir>?"
#        -> software.repair.choreograph.crossfile.v1 (a MUTATOR), refused as a writer answering
#           a read-only question
#   "Plan the rename of the symbol `mul` to `multiply` across <dir>."
#        -> python.source.symbols.index.ast, refused PROMISED_SOURCE_CHANGE_NOT_APPLIED
#
# The op is not invented.  Every field is proved: the two names are STATED (the same rename
# grammar the refactor rows already use), the source root is a STATED directory, and the MODULE is
# the one file under it that really defines the symbol -- parsed, never guessed.  Zero matches or
# several matches yield no value, so the slot stays unbound and the capability keeps failing
# closed.  The file is written into the machine's own scratch, content-addressed like every other
# derived value, so the same sentence always produces the same bytes.
# ---------------------------------------------------------------------------------------------
_EDITS_DIR = "canonical/astra_runtime/tmp/derived"
_MAX_SCAN_FILES = 4000


def _stated_directories(goal: str, root: pathlib.Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for match in _PATH_RE.finditer(str(goal or "")):
        raw = match.group(0).rstrip(".,;:)\"'")
        if raw in seen:
            continue
        seen.add(raw)
        try:
            candidate = (pathlib.Path(root) / raw).resolve()
            base = pathlib.Path(root).resolve()
        except (OSError, ValueError):
            continue
        if candidate.is_dir() and (candidate == base or base in candidate.parents):
            out.append(raw)
    return out


def _defining_module(source_root: str, symbol: str, root: pathlib.Path) -> str | None:
    """The ONE module under source_root that defines `symbol` at module scope, or None."""
    base = pathlib.Path(root) / source_root
    found: list[str] = []
    scanned = 0
    for path in sorted(base.rglob("*.py")):
        if any(part in ("__pycache__", ".git") for part in path.parts):
            continue
        scanned += 1
        if scanned > _MAX_SCAN_FILES:
            return None
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and node.name == symbol:
                found.append(path.relative_to(base).as_posix())
                break
        if len(found) > 1:
            return None
    return found[0] if len(found) == 1 else None


def _derive_edits(goal: str, keys: set[str], root: pathlib.Path) -> dict[str, Any] | None:
    """`edits_path` (and the `source_root` it is relative to) for a stated rename."""
    if "edits_path" not in keys:
        return None
    pairs = _RENAME_OLD_NEW.findall(str(goal or ""))
    if len(pairs) != 1:
        return None
    old, new = pairs[0]
    if not (_NAME_RE.match(old) and _NAME_RE.match(new)) or old == new:
        return None
    directories = _stated_directories(goal, root)
    if len(directories) != 1:
        return None
    source_root = directories[0]
    inner = _defining_module(source_root, old, root)
    if inner is None:
        return None
    # The op's ``module`` is the file's REPOSITORY-relative path, not its path under source_root: the
    # consumer compares it against the symbol index's own ``path`` column, and that index is built
    # with ``source_root`` as a subdirectory of the repository (measured: rows read
    # ``canonical/astra_runtime/tmp/xf/pkg/calc.py``).  Emitting the inner path produced
    # ``MODULE_NOT_IN_INDEX:pkg/calc.py`` and a plan that refused its only op.
    module = source_root.rstrip("/") + "/" + inner if source_root.strip("./") else inner
    body = json.dumps([{"op": "rename_symbol", "module": module, "name": old,
                        "new_name": new}], indent=1, sort_keys=True) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    rel_out = f"{_EDITS_DIR}/edits_{digest}.json"
    target = pathlib.Path(root) / rel_out
    try:
        if not (target.is_file() and target.read_text(encoding="utf-8") == body):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
    except OSError:
        return None
    derived: dict[str, Any] = {
        "edits_path": {"value": rel_out, "rule": "EDITS_FROM_STATED_RENAME_AND_PROVED_MODULE",
                       "evidence": f"{module}:{old}->{new}"}}
    if "source_root" in keys:
        derived["source_root"] = {"value": source_root,
                                  "rule": "SOURCE_ROOT_FROM_STATED_DIRECTORY",
                                  "evidence": source_root}
    return derived

def _tree_of(root: pathlib.Path, rel: str):
    """The parsed module, or an empty module when it cannot be read.

    An unreadable stated file proves nothing, so the proof below simply yields no candidate --
    the same fail-closed reading the qualname rule uses.
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

# git's own subcommand vocabulary (`git help -a`, main porcelain commands, git 2.39.5).
# It is here only to answer "is this leading word an OPERATION?"; a word that is not in
# it is a verb of the request's own ("find", "explain", "rename") and changes nothing.
_GIT_SUBCOMMANDS = frozenset("""
add am archive bisect blame branch bundle checkout cherry-pick citool clean clone commit
describe diff fetch format-patch gc grep gui init log maintenance merge mv notes pull push
range-diff rebase reset restore revert rm shortlog show sparse-checkout stash status
submodule switch tag worktree
""".split())


# THE VERB IS THE OPERATION.  A NOUN PHRASE IN THE SENTENCE IS NOT A SUBSTITUTE FOR IT.
#
# Measured 2026-10-31 on `main` 4b1baa2, through ``live_brain_route_admission_v1.solve``:
#
#     "Reset the working tree to HEAD~1"        -> PASS, op=status
#     "Stash the working tree changes"          -> PASS, op=status
#     "Push the current branch to origin"       -> PASS, op=branch
#
# Every one of the three asks for a repository operation the row's own ``limitations``
# declare it does not have -- *"Reads plus one write (commit --no-verify).  No push,
# rebase, merge, reset or history rewrite."* -- and every one of them passed, because
# the binder matched the words *"working tree"* / *"branch"* to the status and branch
# grammars while the sentence's own verb named an operation that has no implementation
# here.  The row ALREADY refuses an operation it does not declare, by name
# (``OP_NOT_DECLARED:<op>:declared=...``); the binder pre-empted that refusal by binding
# a different operation, and the door certified a read as a change.
#
# So the stated verb is bound even when the row cannot perform it.  A read verb
# ("show", "list", "print") still leaves the grammar free to read the object phrase --
# *"Show the last three git commits"* states `show` and means `log` -- while a verb that
# CHANGES the repository is never re-read as a question about it.
#
# The operations the grammar already reads, derived from it so the two cannot drift.
_GIT_GRAMMAR_OPS = frozenset(name for name, _pattern in _GIT_OPERATION_GRAMMAR)
_GIT_WRITE_SUBCOMMANDS = frozenset("""
add am apply checkout cherry-pick clean clone commit fetch gc init merge mv pull push
rebase reset restore revert rm stash switch tag worktree
""".split())

# Openers that carry no verb of their own.  Bounded and exact: the sentence's first
# remaining word is the imperative, or nothing is read.
_LEADING_OPENER = re.compile(
    r"^\s*(?:please|kindly|now|then|also|and|so|ok|okay|could\s+you|can\s+you|would\s+you"
    r"|will\s+you|i\s+want\s+you\s+to|i\s+need\s+you\s+to|go\s+ahead\s+and|let'?s)\b[\s,]*",
    re.I,
)


def stated_git_operation(goal: str) -> str | None:
    """The repository operation the sentence's own IMPERATIVE names, if it names one.

    ``None`` when the leading word is not a git subcommand at all -- a question
    ("Which commit broke the tests"), a read ("Find every caller ..."), or a goal whose
    first word is a path.  The vocabulary is git's, not this file's: ``git help -a``,
    main porcelain commands.  Whether the chosen row can perform the operation is a
    separate question, answered by the row's own ``OPS`` tuple at execution time.
    """
    text = str(goal or "")
    for _ in range(4):
        stripped = _LEADING_OPENER.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    match = re.match(r"([A-Za-z][A-Za-z-]*)", text)
    if match is None:
        return None
    verb = match.group(1).lower()
    return verb if verb in _GIT_SUBCOMMANDS else None


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

    # THE SENTENCE NAMES THE TESTS BY NAMING THEIR DIRECTORY.
    #
    # "The tests in <b>/tests are failing. Fix the code so they pass" names no file, so
    # `tests` stayed empty, no test slot could be derived, and the directory rule below
    # bound `source_root` to the TEST directory itself.  Measured 2026-10-31 on that
    # sentence: the repair engine searched `<b>/tests`, found only the test file, spent
    # 46 s and reported NO VERIFIED REPAIR -- the same engine repairs the same fixture in
    # 2.4 s once it is handed the tree that owns the tests.  What a directory holds is a
    # fact about the tree, so a directory the sentence names that contains test modules
    # states exactly those modules.  Bounded to the stated directories, capped, and two
    # stated directories that both hold tests are still ambiguity: no value is invented.
    if not tests:
        _stated = _stated_directories(goal, root)
        if len(_stated) <= 1:
            _found_tests: list[str] = []
            for _d in _stated:
                try:
                    _dir_abs = (pathlib.Path(root) / _d).resolve()
                    _files = sorted(_dir_abs.rglob("*.py"))
                except (OSError, ValueError):
                    continue
                for _f in _files[:400]:
                    if "__pycache__" in _f.parts or not _TEST_NAME_RE.search(_f.name):
                        continue
                    try:
                        _found_tests.append(_f.relative_to(pathlib.Path(root).resolve()).as_posix())
                    except ValueError:
                        continue
            if _found_tests:
                tests = _found_tests
                discovered_tests = True

    # A directory slot is satisfied by the parent of the ONE stated source file.
    #
    # ``anchor_path`` is the review gates' name for the SAME thing: the directory the tests run
    # from (pytest rootdir).  The coverage/perf/mutation gates all declare it and none of them
    # could be bound, so "measure the test coverage of <file>" had no route at all.  One rule,
    # reused: the sentence states a file, the file states its directory, and the directory must
    # exist.
    # ... UNLESS THE ROW ITSELF SAYS IT TAKES THE FILE.  ``proposal_bindings`` is where a capability
    # declares the shape of a slot, and six analysis rows declare ``source_root`` as
    # ``path_file_or_dir``: for them the stated FILE is the subject and its parent is a WIDER
    # question.  Measured 2026-10-31 on the capability matrix: "Count the functions in <pkg>/calc.py"
    # reached ``python.source.definition_count.v1`` with ``source_root`` widened to <pkg>, which
    # carries 8 files, and the row answered 12 definitions for a question about 2 -- PASS on a wrong
    # answer, the FALSE class the matrix exists to catch.  A row that only says ``source_root`` (a
    # repair loop, a test runner) still gets the parent, because it cannot read one file.
    _bindings = entry.get("proposal_bindings") if isinstance(entry, Mapping) else None
    for _dir_slot in ("source_root", "anchor_path"):
        if _dir_slot in keys and len(sources) == 1 and _dir_slot not in out:
            _declared = _bindings.get(_dir_slot) if isinstance(_bindings, Mapping) else None
            if isinstance(_declared, Mapping) and str(_declared.get("type") or "") == "path_file_or_dir":
                continue
            parent = str(pathlib.PurePosixPath(sources[0]).parent)
            if parent and (pathlib.Path(root) / parent).is_dir():
                out[_dir_slot] = {"value": parent, "rule": "PATH_DIR_FROM_STATED_FILE_PARENT",
                                  "evidence": sources[0]}
    # THE SAME RULE FOR SEVERAL STATED FILES, BUT ONLY WHEN THE SENTENCE GAVE THEM ROLES
    # ("from A to B"): the directory that holds both ends of a stated move is determined, and it
    # is the only directory that is.  Without it the sibling move row refused with
    # source_root:0_existing_directories_named.  A sentence that merely LISTS two files derives
    # nothing -- that is a pinned law (test_two_source_files_are_ambiguous_and_derive_nothing).
    if "source_root" in keys and "source_root" not in out and len(sources) > 1 \
            and _FROM_TO.search(str(goal or "")):
        _parents = [str(pathlib.PurePosixPath(f).parent) for f in sources]
        _common = _parents[0] if len(set(_parents)) == 1 else None
        if _common is None:
            try:
                _common = str(pathlib.PurePosixPath(os.path.commonpath(_parents)))
            except ValueError:
                _common = None
        if _common and (pathlib.Path(root) / _common).is_dir():
            out["source_root"] = {"value": _common, "rule": "PATH_DIR_COMMON_TO_STATED_FILES",
                                  "evidence": ",".join(sources)}
    # A ROOT THAT HOLDS ONLY TESTS IS NOT THE ROOT OF THE CODE UNDER TEST.
    #
    # Declaration-driven, exactly like the `path_file_or_dir` rule above: this fires only
    # for a row that consumes `source_root`, only when the sentence named tests and NO
    # source file, and only when the tests sit in a directory.  Then the evidence chain is
    # the sentence's own -- the sentence names the tests, the tests live in a directory,
    # and the nearest ancestor of that directory holding a module that is not a test is
    # where the code under test lives.  A sentence that names a source file is untouched:
    # its root is already determined by the file.  Measured 2026-10-31: without this the
    # same sentence bound `source_root` to `<b>/tests` and every repair row (route, apply,
    # test-guided search) searched the test folder for a defect in `app/`.
    if "source_root" in keys and tests and not sources:
        _owners = {str(pathlib.PurePosixPath(t).parent) for t in tests}
        if len(_owners) == 1:
            _owner = next(iter(_owners))
            _walk = pathlib.PurePosixPath(_owner).parent
            for _ in range(3):
                if not _walk.name:
                    break
                _walk_abs = pathlib.Path(root) / str(_walk)
                if _walk_abs.is_dir():
                    _code = False
                    scanned = 0
                    try:
                        for _f in _walk_abs.rglob("*.py"):
                            scanned += 1
                            if scanned > 400:
                                break
                            if "__pycache__" in _f.parts or _TEST_NAME_RE.search(_f.name):
                                continue
                            _code = True
                            break
                    except OSError:
                        _code = False
                    if _code:
                        out["source_root"] = {
                            "value": str(_walk), "rule": "PATH_DIR_OWNING_STATED_TESTS",
                            "evidence": _owner,
                        }
                        break
                _walk = _walk.parent

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
    # THE REFACTORS VERIFY BY RUNNING THE TESTS THEY ARE GIVEN, AND REFUSE TO CERTIFY WITHOUT THEM.
    #
    # ``run_tests`` is a pytest argument list executed with cwd=source_root; with none, the rename
    # adapters set ``gate: PASS_BLIND`` and ``verified: false`` -- the edit lands and the door then
    # refuses, i.e. a refused request that already edited the files, which is the worst of both.
    # The evidence is the same one the repair path already uses: the ONE test file beside the stated
    # source (discovered under exactly the rule below).  Paths are relative to the directory pytest
    # runs in, which is the style the adapters' own receipts use.
    if "run_tests" in keys and tests:
        # The root the paths are relative to is the directory the capability will RUN in: the
        # refactors chdir to ``source_root``; the review gates chdir to ``anchor_path`` (the copied
        # anchor world).  Measured 2026-10-30: without this the mutation gate was handed
        # ``canonical/astra_runtime/tmp/m1/cov/test_calc.py`` while running inside a scratch copy of
        # that same directory, pytest collected nothing, and the honest-looking verdict was
        # ``BASE_WORLD_RED:no tests ran``.
        _root = str(out.get("source_root", {}).get("value")
                    or out.get("anchor_path", {}).get("value") or "").rstrip("/")
        if not _root and sources:
            _root = str(pathlib.PurePosixPath(sources[0]).parent).rstrip("/")
        # A TEST THAT DOES NOT IMPORT THE MODULE CANNOT VERIFY A CHANGE IN IT.
        #
        # ``run_tests`` makes the refactor adapters run those tests AFTER the edit and demand
        # green.  Handing them every test beside the source is not evidence of anything: measured
        # 2026-10-30, "Rename the parameter old_price to price in <pkg/util.py>" was given
        # ``test_calc.py`` -- a test of a DIFFERENT module that is red in that fixture for its own
        # reasons -- so a correct rename was rolled back and reported as a red test.  The relation
        # is read from the test file itself (it must mention the module's stem), which is the same
        # kind of evidence the index already uses for imports.
        _stem = pathlib.PurePosixPath(sources[0]).stem if sources else ""
        _related = []
        for _t in tests:
            try:
                _text = (pathlib.Path(root) / _t).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _stem and (_stem in _text):
                _related.append(_t)
        _rel_tests = []
        for _t in _related:
            _rel_tests.append(_t[len(_root) + 1:] if _root and _t.startswith(_root + "/") else _t)
        if _rel_tests:
            out["run_tests"] = {
                "value": [x for x in _rel_tests if "/" not in x] or _rel_tests,
                "rule": ("PYTEST_ARGV_FROM_RELATED_DISCOVERED_TEST_FILE" if discovered_tests
                         else "PYTEST_ARGV_FROM_RELATED_STATED_TEST_FILE"),
                "evidence": ",".join(_related),
            }
    if "test_paths" in keys and tests:
        out["test_paths"] = {"value": list(tests),
                             "rule": ("PATH_LIST_FROM_DISCOVERED_TEST_FILES" if discovered_tests
                                      else "PATH_LIST_FROM_STATED_TEST_FILES"),
                             "evidence": ",".join(tests)}
    if "source_paths" in keys and sources:
        out["source_paths"] = {"value": list(sources), "rule": "PATH_LIST_FROM_STATED_SOURCE_FILES",
                               "evidence": ",".join(sources)}
    # WHICH TESTS A CHANGE BREAKS needs the CHANGE.  ``changed_paths`` is the impact rows' name for
    # the file the sentence says it changed ("after changing <f>"), and the sentence already states
    # it -- the same evidence as ``source_paths``.  Measured 2026-10-30: the declaration shortlist
    # reached python.source.change_impact.testselect.v1 (the row that provides change_impact and
    # test selection) and admission refused it on ``changed_paths:no_matching_existing_files_named``,
    # so the route layer answered R3_WEAK_EVIDENCE while a repository MEASUREMENT had previously
    # PASSED the same sentence.
    # SCOPED TO THE SENTENCE THAT STATES A CHANGE.  A stated .py file is not itself a statement
    # that anything changed: "the add function in <f> is broken, fix it" names a file and states no
    # change set, and binding ``changed_paths`` for it made ``python.repo.diff_apply_full_testgate``
    # bind as well as the repair row -- two admitted candidates, so five tests of the decisive
    # typed plan (and the repair route itself) went from SELECTED to ambiguous.  The evidence for
    # this slot is the CHANGE, and it is only there when the sentence says so.
    _CHANGE_WORDS = re.compile(r"\b(?:after changing|changed|changes?|diff|affected by|impact of|"
                               r"which tests)\b", re.IGNORECASE)
    stated_change = [f for f in files if f.endswith(".py")] if _CHANGE_WORDS.search(goal) else []
    if "changed_paths" in keys and stated_change:
        out["changed_paths"] = {"value": list(stated_change),
                                "rule": "PATH_LIST_FROM_STATED_CHANGED_FILES",
                                "evidence": ",".join(stated_change)}
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

    # EXTRACT FUNCTION: THE SENTENCE NAMES THE REGION AND THE NEW NAME; THE AST NAMES THE REST.
    #
    # ``python.refactor.extract_function.v1`` has existed since the refactor round and was NEVER
    # reachable: it wants (source_root, module, qualname, new_name, start_line, end_line) and no rule
    # produced the coordinate, so "extract ... into a new function named sum2 in <f>" fell through the
    # lexical matcher to ``math.numeric_expression.sympy``.  Measured 2026-10-30.  Everything the row
    # needs is evidence already in hand: the sentence states the file (=> source_root, module), the
    # quoted region (=> the statement span) and the new name; the AST supplies the enclosing function.
    #
    # THE REGION MUST BE A STATEMENT.  The adapter lifts *statement blocks* into a function; binding a
    # sub-expression ("the expression `a + b`") to the statement that contains it would perform a
    # different edit than the one asked for, so that case is left unbound on purpose: no value is
    # invented, and the refusal is honest.
    if {"start_line", "end_line", "new_name", "module"} <= keys and len(sources) == 1:
        _quoted = re.search(r"[`\x27\"]([^`\x27\"]{1,200})[`\x27\"]", goal)
        _named = _NAMED_NEW.search(goal)
        if _quoted and _named:
            _wanted = " ".join(_quoted.group(1).split())
            try:
                _text = (pathlib.Path(root) / sources[0]).read_text(encoding="utf-8", errors="replace")
                _tree = ast.parse(_text)
            except (OSError, SyntaxError):
                _tree = None
            _hits: list[tuple[str, int, int]] = []
            if _tree is not None:
                for _fn in ast.walk(_tree):
                    if not isinstance(_fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for _stmt in ast.walk(_fn):
                        if not isinstance(_stmt, ast.stmt) or _stmt is _fn:
                            continue
                        try:
                            _seg = ast.get_source_segment(_text, _stmt)
                        except Exception:  # noqa: BLE001 - an unsegmentable node is not evidence
                            _seg = None
                        if _seg and " ".join(_seg.split()) == _wanted:
                            _hits.append((_fn.name, _stmt.lineno, _stmt.end_lineno))
            if len(_hits) == 1:
                _fn_name, _start, _end = _hits[0]
                out["qualname"] = {"value": _fn_name, "rule": "QUALNAME_FROM_ENCLOSING_FUNCTION",
                                   "evidence": sources[0]}
                out["start_line"] = {"value": _start, "rule": "SPAN_FROM_STATED_STATEMENT",
                                     "evidence": _wanted[:80]}
                out["end_line"] = {"value": _end, "rule": "SPAN_FROM_STATED_STATEMENT",
                                   "evidence": _wanted[:80]}
                out["new_name"] = {"value": _named.group(1), "rule": "NAME_FROM_STATED_NEW_NAME",
                                   "evidence": goal[:120]}
                out["module"] = {"value": pathlib.PurePosixPath(sources[0]).name,
                                 "rule": "MODULE_IS_THE_STATED_FILE", "evidence": sources[0]}
    # EXTRACT: A DESCRIBED REGION IS A BLOCK, AND DATA FLOW PICKS IT.
    #
    # The rule above needs the sentence to QUOTE the region and NAME the new function.  A real
    # request does neither: "Extract the discount arithmetic from apply_discount in <path> into
    # a new function" describes the block and leaves the name to the adapter.  Without this the
    # only value ever bound to start_line/end_line was the 0/0 sentinel, which the adapter
    # correctly refused with REGION_INVALID -- one capability, never reachable from the sentence
    # that describes it, and a sentinel is not evidence.
    #
    # The decider is data flow, which is a fact about the parsed function, not a guess about
    # prose: among the contiguous runs of the function's own top-level statements, the region is
    # the SMALLEST run that is SELF-CONTAINED -- every name it reads is a parameter of the
    # function or is assigned inside the run -- and that performs a computation.  A run that
    # reads a local defined outside it cannot be lifted without carrying that local, and the
    # smallest self-contained computation is exactly what "the arithmetic" names.  Ties yield no
    # value: two equally small self-contained computations are two different requests.
    if ("start_line" in keys and "end_line" in keys
            and "start_line" not in out and len(sources) == 1 and sources[0].endswith(".py")):
        try:
            _src_text = (pathlib.Path(root) / sources[0]).read_text(encoding="utf-8", errors="replace")
            _src_tree = ast.parse(_src_text)
        except (OSError, SyntaxError):
            _src_tree = None
        if _src_tree is not None:
            _defined = {n.name for n in ast.walk(_src_tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            _phrases = [m.group(1) for m in re.finditer(
                r"\b(?:from|in|of)\s+([A-Za-z_][A-Za-z0-9_]*)", str(goal or ""), re.I)]
            _hosts = [n for n in dict.fromkeys(_phrases) if n in _defined]
            _host = _hosts[0] if len(_hosts) == 1 else ""
            _fn = None
            for _node in ast.walk(_src_tree):
                if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _node.name == _host:
                    _fn = _node
                    break
            if _fn is not None:
                _params = {a.arg for a in list(_fn.args.args) + list(_fn.args.kwonlyargs)
                           + list(getattr(_fn.args, "posonlyargs", []))}
                _module_names = {t.id for n in _src_tree.body if isinstance(n, ast.Assign)
                                 for t in n.targets if isinstance(t, ast.Name)}
                _body = [st for st in _fn.body if isinstance(st, ast.stmt)]
                _blocked = (ast.Return, ast.Raise, ast.Break, ast.Continue, ast.Yield,
                            ast.Global, ast.Nonlocal, ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)
                _winners: list[tuple[int, int, int]] = []
                for _i in range(len(_body)):
                    for _j in range(_i, len(_body)):
                        _run = _body[_i:_j + 1]
                        if any(isinstance(x, _blocked) for st in _run for x in ast.walk(st)):
                            continue
                        _assigns = {t.id for st in _run for x in ast.walk(st)
                                    if isinstance(x, (ast.Assign, ast.AnnAssign))
                                    for t in ([x.target] if isinstance(x, ast.AnnAssign) else x.targets)
                                    if isinstance(t, ast.Name)}
                        _reads = {x.id for st in _run for x in ast.walk(st)
                                  if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
                        _free = _reads - _assigns
                        if not _free <= (_params | _module_names):
                            continue
                        _computes = any(isinstance(x, (ast.BinOp, ast.Call))
                                        for st in _run for x in ast.walk(st))
                        if not _assigns or not _computes:
                            continue
                        _winners.append((len(_run), _i, _j))
                if _winners:
                    _winners.sort()
                    _smallest = [w for w in _winners if w[0] == _winners[0][0]]
                    if len(_smallest) == 1:
                        _, _i, _j = _smallest[0]
                        out["qualname"] = {"value": _host, "rule": "QUALNAME_FROM_ENCLOSING_FUNCTION",
                                           "evidence": sources[0]}
                        out["start_line"] = {"value": _body[_i].lineno,
                                             "rule": "SPAN_FROM_SELF_CONTAINED_BLOCK",
                                             "evidence": "%s:%d-%d" % (_host, _body[_i].lineno,
                                                                       _body[_j].end_lineno)}
                        out["end_line"] = {"value": _body[_j].end_lineno,
                                           "rule": "SPAN_FROM_SELF_CONTAINED_BLOCK",
                                           "evidence": _host}
                        if "module" in keys and "module" not in out:
                            out["module"] = {"value": pathlib.PurePosixPath(sources[0]).name,
                                             "rule": "MODULE_IS_THE_STATED_FILE",
                                             "evidence": sources[0]}
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
    # MOVE GRAMMAR: two stated source files with the roles "from A to B" name a SENDER and a
    # RECEIVER, and the sentence says which is which.  Measured: "Move the function line_total
    # from <b>/app/models.py to <b>/app/service.py" shortlisted python.refactor.move_function.v1
    # and then refused it with BINDING_REFUSED:module:not_stated, because the one-file rule above
    # only fires when exactly ONE source file is stated -- so the capability that exists for this
    # sentence could never be reached by it.  The roles are read from the sentence's own
    # "from ... to ..." pair, matched against the paths it actually states; anything else (no
    # pair, no path, both orders) yields no value and the binder still fails closed.
    _py_sources = [f for f in sources if f.endswith(".py")]
    # ``source_module`` is the same fact under the name a different row chose for it
    # (``python.refactor.move_symbol.v1`` declares source_module/target_module where
    # ``python.refactor.move_function.v1`` declares module/to_module).  Measured 2026-10-31: with
    # only ``module`` recognised, the symbol mover bound nothing, refused
    # ``source_module:not_stated``, and the sentence fell through to a repair choreographer --
    # a mover that exists and cannot be reached by the sentence written for it.
    # The alias is offered only to the sentence that names a SYMBOL: "Move the function
    # line_total ..." states a function and is answered by python.refactor.move_function.v1,
    # while "Move the symbol `mul` ..." states the other noun and is answered by
    # python.refactor.move_symbol.v1.  Measured 2026-10-31: with the alias unconditional both
    # rows bound and the symbol mover outranked the function mover for a FUNCTION sentence.
    _source_module_keys = ({"module"} | ({"source_module"} if "symbol" in str(goal or "").lower() else set())) & keys
    if len(_py_sources) == 2 and _source_module_keys and ({"to_module", "target_module"} & keys):
        _pair = _FROM_TO.search(str(goal or ""))
        if _pair is not None:
            def _stated_near(near: str) -> str | None:
                hits = [f for f in _py_sources if f in near or f.split("/")[-1] in near]
                return hits[0] if len(hits) == 1 else None
            _src_hit, _dst_hit = _stated_near(_pair.group(1)), _stated_near(_pair.group(2))
            if _src_hit and _dst_hit and _src_hit != _dst_hit:
                for _key in _source_module_keys:
                    out[_key] = {"value": _src_hit, "rule": "MODULE_FROM_STATED_FROM_PATH",
                                 "evidence": _src_hit}
                for _key in ({"to_module", "target_module"} & keys):
                    out[_key] = {"value": _dst_hit, "rule": "TARGET_MODULE_FROM_STATED_TO_PATH",
                                 "evidence": _dst_hit}
    # A SYMBOL SLOT IS PROVED THE SAME WAY A QUALNAME IS, AND FOR THE SAME REASON: "Move the
    # function line_total ..." states the name AFTER the noun, so a "<name> function" grammar reads
    # nothing and the move row refused with BINDING_REFUSED:symbol:not_stated.  Exactly one
    # identifier must follow the noun AND be defined at module scope in a stated file -- which for
    # a move is strictly stronger than "in the one stated file", since a move states two.
    if ({"symbol", "name"} & keys) and _py_sources:
        _nouns = _NAMED_AFTER_NOUN.findall(str(goal or ""))
        _candidates = [n for n in dict.fromkeys(_nouns) if _NAME_RE.match(n)]
        _proved = [(f, _node.name) for f in _py_sources
                   for _node in (getattr(_tree_of(root, f), "body", []) or [])
                   if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                   and _node.name in _candidates]
        if len(_proved) == 1:
            for _key in ({"symbol", "name"} & keys):
                out[_key] = {"value": _proved[0][1], "rule": "SYMBOL_PROVED_FROM_STATED_SOURCE_AST",
                             "evidence": "%s:%s" % (_proved[0][0], _proved[0][1])}
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
        # The sentence's own verb decides what operation it asks for; the noun phrases
        # only get to choose WHEN the verb is a read.  "Reset the working tree to HEAD~1"
        # states `reset`, not `status` -- binding `status` because the words "working
        # tree" appear is how a read gets certified as a change (measured 2026-10-31;
        # see the table above).  Only an operation the grammar does NOT already read may
        # override it, so an operation that works today keeps its reading byte for byte.
        _stated_verb = stated_git_operation(goal)
        if _stated_verb in _GIT_WRITE_SUBCOMMANDS and _stated_verb not in _GIT_GRAMMAR_OPS:
            stated = [_stated_verb]
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

    # ---- the creation grammar ------------------------------------------------
    # A function the sentence asks to CREATE has no definition to be proved
    # against.  Its name is read off the one "function name(args)" phrase and must
    # NOT already exist in any stated file: a name that is already defined is a
    # rename or an edit, not an addition.
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
    # roles.  The role word is the evidence.
    _py_stated = [f for f in sources if f.endswith(".py")]
    if ("module" in keys and "module" not in out and len(_py_stated) > 1
            and _CREATES_A_FUNCTION.search(str(goal or ""))):
        _to_hits = [m.group(1).rstrip(".,;:") for m in
                    re.finditer(r"\bto\s+([^\s,;]+)", str(goal or ""), re.I)]
        _exact = [h for h in _to_hits if h in _py_stated]
        if len(_exact) == 1:
            out["module"] = {"value": _exact[0], "rule": "MODULE_FROM_STATED_TO_TARGET",
                             "evidence": _exact[0]}
    if "export_module" in keys and "export_module" not in out:
        _stated_all = set(stated_existing_files(str(goal or ""), pathlib.Path(root)))
        _exp = [m.group(1).rstrip(".,;:") for m in _EXPORT_FROM.finditer(str(goal or ""))]
        _exp = [h for h in _exp if h in _stated_all]
        if len(_exp) == 1:
            out["export_module"] = {"value": _exp[0], "rule": "EXPORT_TARGET_STATED",
                                    "evidence": _exp[0]}
    if (({"params", "parameters"} & keys) or ({"body", "expression", "returns"} & keys)) \
            and _CREATES_A_FUNCTION.search(str(goal or "")):
        _fn_phrases = _ADDED_FUNCTION.findall(str(goal or ""))
        if len(_fn_phrases) == 1:
            _fname, _raw_params = _fn_phrases[0]
            _params = [p.strip() for p in _raw_params.split(",") if p.strip()]
            if all(_NAME_RE.match(p) for p in _params):
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
    if ("source_root" in keys and "source_root" not in out and "module" in out
            and str((out.get("module") or {}).get("rule") or "") == "MODULE_FROM_STATED_TO_TARGET"):
        _parent = str(pathlib.PurePosixPath(str(out["module"]["value"])).parent)
        if _parent and (pathlib.Path(root) / _parent).is_dir():
            out["source_root"] = {"value": _parent, "rule": "PATH_DIR_FROM_STATED_MODULE",
                                  "evidence": str(out["module"]["value"])}
    # An ADDED parameter is a name the sentence states and the stated function does
    # NOT already declare, which is what makes it an addition rather than a rename.
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
                    for m in re.finditer(r"\b(?:from|in|of|function|method)\s+[`\"']?([A-Za-z_][A-Za-z0-9_]*)[`\"']?", str(goal or ""), re.I)
                    if m.group(1) in defined_fns
                }
                if len(preps) == 1:
                    wanted_fn = next(iter(preps))
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
    # The cross-file edit plan: last, so every value above keeps its own precedence.
    edits = _derive_edits(goal, keys, root)
    if edits:
        for key, value in edits.items():
            out.setdefault(key, value)
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
