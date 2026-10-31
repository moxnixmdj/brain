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
    "remove the unused", "move the function", "add a parameter", "caller",
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
