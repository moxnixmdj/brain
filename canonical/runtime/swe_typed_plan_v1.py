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
from canonical.runtime import goal_front_compiler_v1 as front
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

_FAMILIES = (
 (('off-by-one bug',
   'not null constraint',
   'second method',
   'add a method',
   'exported function',
   'development dependency',
   'dev dependency',
   'create a pyproject',
   'pin the dependency',
   'vendor the',
   'failing ci job',
   'ci workflow',
   'set up ci',
   'setup ci',
   'caching of pip',
   'quarantine the flaky'),
  ('polyglot', 'pyproject', 'makefile', 'workflow', 'quarantine'),
  'polyglot.transform_and_verify'),
 (('profile ',
   'hot spot',
   'fuzz the function',
   'tell me which tests fail',
   'find the root cause',
   'explain why',
   'api design',
   'known vulnerabilities',
   'design the api',
   'write an adr',
   'plan the migration',
   'design document for splitting',
   'changelog entry'),
  ('diagnose', 'hotspot', 'api_design', 'adr_and_migration', 'vulnerability_audit', 'blame_and_changelog', 'runner_verdict'),
  'diagnose_and_architect'),
 (('optimise the function',
   'optimize the function',
   'add memoisation',
   'add memoization',
   'thread pool',
   'release the gil',
   'property-based test',
   'write a unit test',
   'one module per function',
   'deprecated function',
   'add type hints',
   'extract the magic',
   'extract constant',
   'cherry-pick',
   'create a branch',
   'from docstrings',
   'cli flag',
   'add logging',
   'add retry',
   'add retries'),
  ('swe_transform', 'egraph', 'concurrency', 'structural.module', 'format.ast_verified', 'branch.operate'),
  'swe.transform_and_synthesize'),
 (('move the function', 'move the class', 'move symbol', 'relocate function', 'relocate class'),
  ('move_symbol', 'relocate symbol'),
  'move_symbol'),
 (('add a parameter', 'add parameter', 'new parameter'),
  ('add_parameter', 'signature evolution'),
  'source.add_parameter'),
 (('add a function', 'implement a function', 'implement function', 'create a function'),
  ('implement_function_spec', 'function specification', 'polyglot'),
  'function'),
 (('regression test that would have caught', 'add a regression test'),
  ('python.tests.regression.synthesized', 'swe_transform'),
  'regression'),
 (('caller', 'who calls', 'call site', 'call graph', 'find every call'),
  ('caller', 'call graph', 'who calls'),
  'symbol'),
 (('git',
   'commit the',
   'last commit',
   'commits',
   'blame',
   'branches',
   'who wrote',
   'who last changed',
   'who changed',
   'who touched',
   'working tree',
   'staged changes'),
  ('git', 'commit', 'history', 'repository'),
  'git'),
 (('type-check', 'type check', 'typecheck', 'type checks', 'mypy'),
  ('type_gate', 'typecheck', 'type check', 'type-check', 'mypy'),
  'type'),
 (('lint ', 'ruff check', 'static triage'),
  ('diff_static_triage',),
  'diff_static_triage'),
 (('merge conflict', 'conflict markers'),
  ('merge_conflict',),
  'merge_conflict'),
 (('untrusted input', 'taint flow', 'sql injection', 'command injection'),
  ('taint_flow',),
  'taint_flow'),
 (('crosshair', 'postcondition', 'precondition'),
  ('crosshair',),
  'crosshair'),
 (('bug:',
   'bug report',
   'bug in',
   'broken',
   'failing test',
   'test fails',
   'tests fail',
   'returns the wrong',
   'wrong value',
   'does not pass',
   "doesn't pass"),
  ('apply the repair', 'repair.apply', 'verified_repair_applied', 'write the fix'),
  'repair'),
 (('into a new function', 'pull out into', 'extract the loop'), ('extract', 'refactor'), 'extract'),
 (('which files must change',
   'what has to change',
   'what must change',
   'files must change',
   'sites must change',
   'cross-file',
   'crossfile',
   'plan the rename'),
  ('cross-file', 'choreograph', 'plan'),
  'crossfile_edit'),
 (('test coverage', 'coverage'), ('coverage',), 'coverage'),
 (('security issue',
   'security review',
   'security audit',
   'security scan',
   'vulnerab',
   'check for security'),
  ('security', 'vulnerab', 'bandit'),
  'security'),
 (('mutation score', 'mutation test', 'mutants', 'mutation coverage'),
  ('mutation', 'mutant'),
  'mutation'),
 (('performance regression', 'performance review', 'benchmark', 'slower than', 'timing regression'),
  ('performance', 'perf', 'benchmark'),
  'perf'))
_FAMILY_SWE_PREFIXES = ("python.", "code.", "software.", "test.", "orchestration.verify.",
                        "git.")


_ANALYSIS_ONLY_TRIGGERS = ("explain", "describe", "summarise", "summarize",
                           "diagnose", "why is", "why does", "how does", "review the")

GIT_FAMILY_TOKEN = "git"


def stated_family_token(goal: str) -> str | None:
    """The effect token of the family this sentence STATES, or ``None``.

    Cheap enough for the front door: one pass over ``_FAMILIES`` triggers and no
    registry read.  The door uses it to decide whether a typed plan is
    AUTHORITATIVE for this sentence or merely a retry candidate.
    """
    fam = _family_terms(goal)
    return fam[1] if fam else None


# A coordinating junction starts a NEW clause, and a family trigger inside a
# subordinate clause is not what the sentence asked for.  Measured 2026-10-31:
# "Add a parameter qty with a default value to the function line_total in X and
# update every caller so behaviour is unchanged" contains "caller", so the caller
# family claimed AUTHORITY over an add-a-parameter request and the symbol index
# was executed for a signature change.  The sentence's own governing clause
# decides its effect.
_CLAUSE_BREAK = re.compile(r"(?:\.(?=\s|$)|[;!?]|,\s*$|\s+(?:and|then|so|but)\s+)", re.I)


def _governing_clause(text: str) -> str:
    """The clause that carries the sentence's request (its first clause)."""
    parts = [p for p in _CLAUSE_BREAK.split(str(text or "")) if p and p.strip()]
    return parts[0] if parts else ""


_ASKED_RE = re.compile(
    r"\?|(?:^|[.;]\s*)(?:which|what|where|who|whom|whose|how|why|is|are|does|do)\b"
    r"|\bwhether\b|\btell me\b|\bcheck (?:if|whether)\b", re.IGNORECASE)


def _family_hits(goal: str) -> tuple[tuple[str, ...], tuple[str, ...], str] | None:
    """(the trigger phrases the sentence states, candidate terms, effect token)."""
    # Commit messages are payload, not authorization for source synthesis.
    # Reuse the existing repository grammar/scope validator before kernel dispatch.
    if derivation.stated_git_operation_verb(goal) == "commit":
        return derivation.stated_git_operations(goal), ("git", "repository"), GIT_FAMILY_TOKEN
    raw_low = str(goal or "").lower()
    if any(p in raw_low for p in (
        "ast patch search", "patch search", "repair loop", "coupled ", "strict progress", "provenance guided"
    )):
        return None
    if "find the root cause" in raw_low and "answer.json" not in raw_low:
        return ("find the root cause",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if (
        re.search(r"\bgit\s+bisect\b|\bbisect\s+the\s+regression\b|\b(?:which|find\s+the)\s+commit\b[^\n]{0,200}?\bbroke\b", raw_low)
        or ("performance regression" in raw_low and "commit" in raw_low)
    ):
        return ("bisect",), ("bisect_regression", "perf_attribution"), "bisect_regression"
    if (
        any(w in raw_low for w in ("postcondition", "symbolic execution", "crosshair"))
        or ("counterexample" in raw_low and ".py" in raw_low)
    ):
        return ("contract_check",), ("contract.verdict", "crosshair"), "crosshair"
    if "changelog" in raw_low and "commits" in raw_low:
        return ("git_changelog",), ("diagnose", "blame_and_changelog"), "diagnose_and_architect"
    if "benchmark" in raw_low and "head~1" in raw_low and ".py" in raw_low:
        return ("benchmark_git_ref",), ("diagnose", "hotspot"), "diagnose_and_architect"
    if "regression test" in raw_low and "reproduces" in raw_low and "fix" not in raw_low and ".py" in raw_low:
        return ("write_regression_test",), ("swe_transform",), "swe.transform_and_synthesize"
    if "find the race condition" in raw_low:
        _root_p = pathlib.Path(__file__).resolve().parents[2]
        _rfiles = [p for p in re.findall(r"[A-Za-z0-9_./-]+\.py\b", str(goal or "")) if (_root_p / p).is_file()]
        if _rfiles and any(w in (_root_p / _rfiles[0]).read_text(encoding="utf-8", errors="replace") for w in ("threading", "Thread", "asyncio")):
            return ("find the race condition",), ("diagnose",), "diagnose_and_architect"
    if "cause of the exception" in raw_low and "log" in raw_low:
        return ("log exception",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if "profile " in raw_low and ("hot spot" in raw_low or "where the time goes" in raw_low):
        return ("profile",), ("diagnose", "hotspot"), "diagnose_and_architect"
    if ("why does " in raw_low and " fail" in raw_low) or ("is red" in raw_low and "find out why" in raw_low) or ("debugger" in raw_low and "frame" in raw_low):
        return ("diagnose_suite",), ("diagnose", "runner_verdict"), "diagnose_and_architect"
    if "trace how data flows" in raw_low or "trace why " in raw_low:
        return ("trace",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if "which files must change to rename" in raw_low:
        return ("rename_plan",), ("diagnose",), "diagnose_and_architect"
    if re.search(r"^\s*find\s+(?:the\s+)?dead\s+code\b", raw_low):
        return ("find_dead_code",), ("diagnose", "dead"), "diagnose_and_architect"
    if "audit " in raw_low and "dependenc" in raw_low and "vulnerabilit" in raw_low:
        return ("audit",), ("vulnerability_audit", "diagnose"), "diagnose_and_architect"
    if "validate " in raw_low and "json schema" in raw_low:
        return ("json_schema",), ("diagnose", "schema"), "diagnose_and_architect"
    if "review the pull request" in raw_low:
        return ("pr_review",), ("diagnose", "pull request"), "diagnose_and_architect"
    if "committed secrets" in raw_low or "hardcoded secret" in raw_low:
        return ("secret_scan",), ("secret_scan", "secret"), "secret"
    if "explain the bug" in raw_low:
        return ("explain the bug",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if "explain what " in raw_low and ".py" in raw_low:
        return ("explain what",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if "lint" in raw_low and "javascript" in raw_low:
        return ("lint javascript",), ("diagnose", "static_triage"), "diagnose_and_architect"
    if "run" in raw_low and "javascript" in raw_low and "test" in raw_low:
        return ("run javascript test",), ("diagnose", "runner_verdict"), "diagnose_and_architect"
    if (
        re.search(r"\b(?:show|print|display|find|get)\s+(?:me\s+)?(?:the\s+)?(?:definition|signature|implementation)\s+of\b", raw_low)
        or re.search(r"\bwhere\s+is\s+\S+(?:\s+\S+){0,2}\s+defined\b", raw_low)
    ):
        return ("show_definition",), ("diagnose", "definition"), "diagnose_and_architect"
    if re.search(r"\b(?:which|what)\s+(?:modules?|files?)\s+import\b|\bwho\s+imports\b|\bimporters\s+of\b", raw_low):
        return ("which_modules_import",), ("diagnose", "importers"), "diagnose_and_architect"
    if ("import cycle" in raw_low or "circular import" in raw_low or "cyclic import" in raw_low) and not any(
        w in raw_low for w in ("fix ", "break ", "remove ", "resolve ")
    ):
        return ("import_cycles",), ("diagnose", "import_cycles"), "diagnose_and_architect"
    if "class hierarchy" in raw_low or "subclasses of" in raw_low or "inheritance hierarchy" in raw_low or "mro of" in raw_low:
        return ("class_hierarchy",), ("diagnose", "class_hierarchy"), "diagnose_and_architect"
    if (
        re.search(r"^\s*(?:please\s+)?run\s+(?:the\s+)?(?:unit\s+)?tests?\s+(?:in|for|from)\s+\S*test\S*\.py\b", raw_low)
        and "write the" not in raw_low
        and "save " not in raw_low
        and "tell me" not in raw_low
    ):
        return ("run_single_test",), ("diagnose", "runner_verdict"), "diagnose_and_architect"
    if "trace the value of" in raw_low and ".py" in raw_low:
        return ("trace_value_provenance",), ("diagnose", "root_cause"), "diagnose_and_architect"
    if (
        "flaky" in raw_low
        and any(w in raw_low for w in ("find", "detect", "tell me if", "whether", "rerun"))
        and "quarantine" not in raw_low
        and "answer.json" not in raw_low
    ):
        return ("find_flaky_tests",), ("diagnose", "flaky"), "diagnose_and_architect"
    if "design the api" in raw_low and "adr" in raw_low:
        return ("design the api",), ("diagnose", "adr_and_migration"), "diagnose_and_architect"
    if "design document" in raw_low and "splitting" in raw_low:
        return ("design document",), ("diagnose", "adr_and_migration"), "diagnose_and_architect"
    if "increase the mutation score" in raw_low:
        return ("increase the mutation score",), ("swe_transform",), "swe.transform_and_synthesize"
    if (
        re.search(r"\boptimis[ez]?\w*|\boptimiz\w*", raw_low)
        or ("faster" in raw_low and "without changing" in raw_low)
    ) and ".py" in raw_low and "linear" not in raw_low:
        return ("optimize",), ("swe_transform",), "swe.transform_and_synthesize"
    if ("asynchronous" in raw_low or re.search(r"\bmake\b.*\basync\b", raw_low)) and ".py" in raw_low:
        return ("make_async",), ("swe_transform",), "swe.transform_and_synthesize"
    if "parallel" in raw_low and ("test suite" in raw_low or "tests" in raw_low):
        return ("parallel_tests",), ("swe_transform",), "swe.transform_and_synthesize"
    if "benchmark" in raw_low and "baseline" in raw_low and ".py" in raw_low:
        return ("add_benchmark",), ("swe_transform",), "swe.transform_and_synthesize"
    if "coverage" in raw_low and ("raise" in raw_low or "increase" in raw_low) and ".py" in raw_low:
        return ("raise_coverage",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"\bproperty[- ]based\s+tests?\b|\bhypothesis\b", raw_low) and ".py" in raw_low:
        return ("write_property_test",), ("swe_transform",), "swe.transform_and_synthesize"
    if "docstring" in raw_low and "test" in raw_low and ".py" in raw_low:
        return ("tests_from_docstrings",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"^\s*(?:please\s+)?(?:write|add|create|generate|synthesize|author)\s+(?:a\s+|missing\s+)?unit\s+tests?\b", raw_low) and ".py" in raw_low:
        return ("write_unit_test",), ("swe_transform",), "swe.transform_and_synthesize"
    if "add a test for the case" in raw_low:
        return ("add a test for the case",), ("swe_transform",), "swe.transform_and_synthesize"
    if "implement this issue" in raw_low:
        return ("implement this issue",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"\b(?:add|implement)\s+(?:a\s+|an\s+)?[a-z_]\w*\s+function\b", raw_low) and (
        "use it in" in raw_low or ("with tests" in raw_low and "update " in raw_low)
    ):
        return ("crossfile_feature",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(
        r"\b(?:add\s+(?:structured\s+|debug\s+|info\s+)?logging|add\s+retr(?:y|ies)|retry\s+logic|with\s+backoff|"
        r"add\s+error\s+handling|sqlalchemy\s+model|fastapi\s+endpoint|write\s+a\s+client|path\s+traversal|counter\s+metric)\b",
        raw_low,
    ):
        return ("swe_feature",), ("swe_transform",), "swe.transform_and_synthesize"
    if (
        "move the module " in raw_low
        or ("magic number" in raw_low)
        or ("shared helper" in raw_low and "refactor " in raw_low)
        or ("split " in raw_low and ("one module per" in raw_low or "into two modules" in raw_low))
        or ("add type hints" in raw_low)
        or ("lint " in raw_low and "fix what it reports" in raw_low)
    ):
        return ("swe_refactor",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"\b(?:remove|delete|drop)\s+(?:the\s+|all\s+)?dead\s+code\b", raw_low):
        return ("remove_dead_code",), ("swe_transform", "dead_code"), "swe.transform_and_synthesize"
    if "unused import" in raw_low and any(w in raw_low for w in ("remove", "delete", "drop", "strip", "clean")) and ".py" in raw_low and "unused function" not in raw_low:
        return ("remove_unused_imports",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"^\s*(?:please\s+)?inline\s+(?:the\s+)?(?:helper|function)\b", raw_low) and "only caller" not in raw_low and ".py" in raw_low:
        return ("inline_function",), ("swe_transform",), "swe.transform_and_synthesize"
    if "memory leak" in raw_low and any(w in raw_low for w in ("fix", "repair")) and ".py" in raw_low:
        return ("fix_memory_leak",), ("swe_transform",), "swe.transform_and_synthesize"
    if re.search(r"\b(?:extract|move)\s+(?:the\s+)?(?:function\s+|class\s+|symbol\s+)?\w+\s+from\s+\S+\.py\s+(?:into|to)(?:\s+(?:a\s+)?new\s+module)?\s+\S+\.py", raw_low):
        return ("move_symbol",), ("move_symbol", "relocate symbol"), "move_symbol"
    if (
        (re.search(r"\bcommit\s+(?:the\s+)?(?:current\s+)?changes\s+(?:in|to)\s+\S+", raw_low) and "staged" not in raw_low)
        or re.search(r"\bcreate\s+(?:a\s+|the\s+)?branch\s+(?:named\s+)?\S+\s+(?:in\s+\S+|and\s+commit\s+\S+)", raw_low)
        or ("git worktree" in raw_low)
        or ("revert the last commit" in raw_low)
        or ("rebase the branch" in raw_low)
        or ("cherry-pick " in raw_low and ("onto " in raw_low or "new branch" in raw_low))
    ):
        return ("git_worktree_write",), ("swe_transform", "branch.operate"), "swe.transform_and_synthesize"
    if (
        ("add the dependency " in raw_low and "pyproject.toml" not in raw_low)
        or ("into a wheel" in raw_low and "build " in raw_low)
        or ("requirements.txt" in raw_low and ("lock file" in raw_low or "pin " in raw_low))
        or ("bill of materials" in raw_low or "sbom" in raw_low)
        or ("pull request description" in raw_low)
        or ("ci workflow" in raw_low or "ci matrix" in raw_low or "set up ci" in raw_low or "setup ci" in raw_low)
        or ("database migration" in raw_low)
        or ("type declarations" in raw_low)
        or (re.search(r"\bport\s+(?:the\s+)?function\b", raw_low) is not None)
        or (
            re.search(
                r"\b(?:port|translate|transpile|convert)\b[^\n]{0,160}?\b(?:to|into)\s+(?:idiomatic\s+)?(?:rust|go|golang|typescript|javascript)\b",
                raw_low,
            ) is not None
        )
        or (re.search(r"^\s*(?:please\s+)?run\s+`?make\s+[a-z0-9_.-]+`?", raw_low) is not None)
    ):
        return ("polyglot_build_release",), ("polyglot",), "polyglot.transform_and_verify"
    # Direct path-suffix dispatch for polyglot / Makefile / pyproject / workflow writes
    if any(ext in raw_low for ext in (".cpp", ".cc", ".rs", ".go", ".java", ".ts", ".sql", "pyproject.toml", "makefile", ".github/workflows/")):
        if any(w in raw_low for w in ("audit ", "vulnerabilit", "review ")):
            return ("audit",), ("vulnerability_audit", "diagnose"), "diagnose_and_architect"
        if any(w in raw_low for w in (
            "fix", "repair", "add", "create", "rename", "pin", "bump", "make the ci",
            "not null", "constraint", "alter", "panic", "null", "undefined", "borrow", "crash",
        )):
            return ("polyglot_path",), ("polyglot", "pyproject", "makefile", "workflow"), "polyglot.transform_and_verify"
    if re.match(r"^\s*(?:please\s+)?(?:re)?format\s+\S+\.py\b", raw_low):
        return ("format",), ("format.ast_verified", "swe_transform"), "swe.transform_and_synthesize"
    if re.search(r"--[a-z0-9_-]+", raw_low) and ("flag" in raw_low or "cli" in raw_low or "command-line" in raw_low):
        return ("cli flag",), ("swe_transform",), "swe.transform_and_synthesize"
    # Paths and quoted values are task data, not evidence of an effect family.
    prose = front.prose_only(str(goal or ""))
    head = _governing_clause(prose.lower())
    has_analysis_trigger = any(word in head for word in _ANALYSIS_ONLY_TRIGGERS)
    for triggers, terms, token in _FAMILIES:
        if has_analysis_trigger and token != "diagnose_and_architect":
            continue
        # Keep the current-main question/repair distinction under our apply name.
        if token in {"repair", "apply"} and _ASKED_RE.search(prose):
            continue
        # A guard that names "update every caller" and "rename " by hand is a
        # curated condition on the sentences this file must generalise over; the
        # governing clause decides it for every family and every sentence:
        # "Add a parameter qty ... and update every caller" states a signature
        # change, "Rename the function f to g" states a rename, and in both the
        # family noun sits in a clause that is not the request.
        hits = tuple(t for t in triggers if t in head)
        if hits:
            return hits, terms, token
    # A READ OF A NAMED REVISION IS A REPOSITORY READ.
    #
    # Measured 2026-10-31, advanced sentence 44: "Show me the diff of <pkg>/calc.py against
    # HEAD~1." states the operation (`diff`, in the grammar's own words), states the object
    # (the file) and states the revision.  The read-detection below could never see it: the
    # path is a VALUE and F8/F25 remove it from the head before this function looks, so what
    # remained was "show me the diff of against HEAD~1" and the fullmatch failed on the
    # revision phrase.  The sentence then reached `git.repository.operate.v1` -- whose OPS
    # tuple is exactly (log, status, diff, show, blame, branch, commit) and which derives
    # op, repo_root and target from these very bytes -- was outscored by six `diff_*_gate`
    # rows that only share the noun, and compiled to nothing (RAW_GOAL_COMPILATION_GAP).
    # The revision is git's vocabulary, not this file's: HEAD~N/HEAD^N is a fact the sentence
    # states, and a read opener is the same closed list used below.
    if (re.match(r"(?:please\s+)?(?:show|list|print|display|give|what\s+is)\s+", head.strip())
            and len(derivation.stated_git_operations(goal)) == 1
            and re.search(r"\bhead[~^]\d*\b|\brevision\b", head, re.I)):
        return derivation.stated_git_operations(goal), ("git", "repository"), GIT_FAMILY_TOKEN
    # Unqualified repository reads use the existing operation grammar, not
    # broad nouns such as "status" inside deployment questions or task data.
    if re.fullmatch(r"(?:please\s+)?(?:show|list|print|display|what\s+is|what\s+are)\s+"
                    r"(?:me\s+)?(?:the\s+)?(?:(?:diff|patch|contents?)\s+of\s+the\s+(?:last|latest)\s+commit|"
                    r"(?:last|latest)\s+commit|staged\s+changes?|"
                    r"(?:uncommitted\s+)?(?:diff|status|history|current\s+branch))"
                    r"(?:\s+of\s+the\s+working\s+tree)?"
                    r"(?:\s+(?:of|for|in|under|at)\s*)?[.?!]*", head.strip()):
        if len(derivation.stated_git_operations(goal)) == 1:
            return derivation.stated_git_operations(goal), ("git", "repository"), GIT_FAMILY_TOKEN
    # Direct bare repair imperative ("fix <pkg/calc.py>") where prose_only leaves only "fix"/"repair".
    if re.fullmatch(r"(?:please\s+)?(?:fix|repair)\s*(?:the\s+(?:bug|code|function|module|file)s?\s*(?:in)?)?[.!]*",
                    head.strip()):
        return ("fix",), ("apply the repair", "repair.apply", "verified_repair_applied", "write the fix"), "repair"
    return None


def _family_terms(goal: str) -> tuple[tuple[str, ...], str] | None:
    hit = _family_hits(goal)
    return (hit[1], hit[2]) if hit else None


def is_swe_request(goal: str) -> bool:
    """An explicit software-engineering request: the base verb list OR a stated
    SWE effect family (caller-finding etc.).  Broadening is confined to the typed
    RETRY path; the pinned lexical compiler and the ``executed`` guard are
    untouched.  Verified: the three pinned front-door refusals stay non-SWE."""
    if derivation.is_swe_request(goal):
        return True
    return _family_terms(goal) is not None


def _execution_template(entry: Mapping[str, Any], removed: set[str],
                        extra_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Copy the adapter's declared template, dropping ONLY adapter-defaulted
    ``${input.*}`` placeholders.  Slots with a bound value (including derived
    ones) are kept so the adapter still receives them at run time."""
    template = dict(entry.get("action_template") or {})
    args = dict(template.get("args") or {})
    for key in list(args):
        value = args[key]
        if key in removed and isinstance(value, str) and "${input." in value:
            args.pop(key, None)
    if extra_inputs and extra_inputs.get("synthesize_regression_test") is True:
        args["synthesize_regression_test"] = "${input.synthesize_regression_test}"
    if extra_inputs and extra_inputs.get("staged_only") is True and "staged_only" not in args:
        args["staged_only"] = "${input.staged_only}"
    if extra_inputs and extra_inputs.get("remove_functions"):
        args["remove_functions"] = "${input.remove_functions}"
    if extra_inputs and extra_inputs.get("run_tests") and "run_tests" in args:
        args["run_tests"] = "${input.run_tests}"
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
    if not isinstance(current, str):
        return None
    spooled = bool(re.fullmatch(r"canonical/astra_runtime/tmp/spool_\d+_output\.json", current))
    if current not in stated and not spooled:
        return None
    # Only a file the sentence treats as code or manifest is a dangerous output target.
    if not spooled and not current.endswith((".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".rb", ".sql", ".toml", ".yml", ".yaml", "Makefile")):
        return None
    source_root = inputs.get("source_root")
    if isinstance(source_root, str) and source_root and (root / source_root).is_dir():
        parent = source_root
    else:
        named_sources = [p for p in stated if p.endswith(".py")]
        parent = (str(pathlib.PurePosixPath(named_sources[0]).parent) if spooled and len(named_sources) == 1
                  else str(pathlib.PurePosixPath(current).parent))
    if not parent or not (root / parent).is_dir():
        return None
    import hashlib
    digest = hashlib.sha256((str(goal or "") + "\0" + parent).encode("utf-8")).hexdigest()[:12]
    return f"canonical/astra_runtime/tmp/typed_swe_reports/{digest}_typed_swe_report.json"


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
    if re.search(r"\b(?:find\s+every\s+caller|who\s+calls)\b", prose):
        if not any("symbol" in str(c).lower() for c in capability_ids):
            return "R10_CALLER_QUERY_EFFECT_UNSERVED"
    # A regression test the chosen row cannot synthesize is NOT a reason to refuse the plan.
    # Measured 2026-10-31 on the 28-task ladder: refusing "fix the bug ... and add a regression
    # test that would have caught it" before the run cost the repair the sentence also asked
    # for (reached 27/28 instead of 28/28) and bought nothing -- the single repair row fixed
    # the tree and left the suite green either way.  The effect is now WITHHELD at the exit
    # instead (live_brain_route_admission_v1._enforced_at_exit, which reads the same
    # ``synthesize_regression_test`` declaration this clause read, so a row that really can
    # author the test is never demoted).  Refusal is for the case where there is nothing else
    # to do; it is not the instrument for a sentence that also asks for work.
    imperative = re.search(
        r"(?:^|[.;\n]|\bthen\b|\band\b)\s*"
        r"(?:(?:please|first|next)\s+|(?:can|could|would)\s+you\s+(?:please\s+)?)?"
        r"(?:implement\b|develop\b|build\b|"
        r"add\s+(?:(?:a|an|the|new)\s+)*[\w -]{0,60}"
        r"\b(?:function|method|feature|endpoint|class|api)\b)", prose)
    software = re.search(r"\b(?:python|software|code|function|method|feature|endpoint|class|api)\b", prose)
    if not imperative:
        return None
    if not software:
        from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES
        software = any(path.suffix.lower() in SOURCE_SUFFIXES
                       for _raw, path in goal_compiler._repo_paths(goal, live_brain.ROOT))
    if not software:
        return None
    # These are actual registry effect namespaces, not keyword relevance or id
    # substrings such as 'patch' (which could mean a report-only patch search).
    material = ('.source.write.', '.refactor.', '.edit.', '.issue_to_pr.', '.feature.implement.')
    for cid in capability_ids:
        entry = registry.get(str(cid)) or {}
        if any(any(part in str(effect) for part in material)
               for effect in entry.get('provides', [])):
            return None
    return 'R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED'


def _effect_consistent(goal: str, cid: str, entry: Mapping[str, Any] | None = None) -> bool:
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
    phrases: list[str] = []
    for verbs, effects in selection._EFFECT_WORDS:
        hit = [verb for verb in verbs if verb in text]
        if hit:
            stated.extend(effects)
            phrases.extend(hit)
    if not stated:
        return True
    low = _row_surface(cid, entry)
    if any(effect in low for effect in set(stated)):
        return True
    # ... or the row DECLARES the stated phrase itself.  `_EFFECT_WORDS` is a
    # curated verb->effect table, and a curated table is exactly what goes stale:
    # "merge conflict" is mapped to {choreograph}, so the dedicated
    # python.vcs.merge_conflict.resolve.v1 row -- whose own keywords say
    # "merge conflict", "keep both changes", "unmerged" -- was judged
    # effect-INCONSISTENT with the sentence it exists for, and a 28-task census
    # lost the merge-conflict request that the front compiler had ALREADY
    # selected correctly.  A row's declared keywords/provides are the row's own
    # statement of the effect it serves; matching the sentence there is stronger
    # evidence than membership in a hand-maintained synonym table.
    return any(len(phrase) > 3 and phrase in low for phrase in set(phrases))


def _row_surface(cid: str, entry: Mapping[str, Any] | None = None) -> str:
    """What the row itself says it does: its id plus its declared surface."""
    parts = [str(cid or "").lower()]
    if isinstance(entry, Mapping):
        parts.extend(map(str, (entry.get("keywords") or [])))
        parts.extend(map(str, (entry.get("provides") or [])))
    return " ".join(parts).lower()


def _phrase_rivals(goal: str, triggers, token: str,
                   registry: Mapping[str, Any]) -> set[str]:
    """Rows that DECLARE a multi-word phrase of the sentence holding a trigger.

    Pure data: every phrase comes from a registry row's own keywords/provides,
    and the trigger words come from ``_FAMILIES`` -- no per-capability table.
    Excludes rows whose id carries the family's effect token (those are the
    family's own candidates, judged by the admission oracle).
    """
    prose = front.prose_only(str(goal or "")).lower()
    rivals: set[str] = set()
    for cid, entry in registry.items():
        if token in str(cid).lower():
            continue
        for phrase in list(entry.get("keywords") or []) + list(entry.get("provides") or []):
            words = str(phrase).lower().split()
            if len(words) < 2:
                continue
            joined = " ".join(words)
            if not any(t in joined for t in triggers):
                continue
            if joined in prose:
                rivals.add(str(cid))
                break
    return rivals


def _resolve_family(goal: str, root: pathlib.Path, registry: dict,
                    declared: dict) -> tuple[str, dict] | None:
    """Enumerate hidden capabilities matching the goal's SWE effect (by the
    registry's OWN keywords), and let ``admit()`` -- the existing typed-contract
    binder -- be the oracle.  DECISIVE only when EXACTLY ONE candidate is
    admitted+specific AND its name states the effect.  Ambiguity or zero =>
    None (fail closed).  This never fabricates a capability: every candidate is
    a real registry row that must bind every declared input from the sentence.

    Measured 2026-10-28: "Find every caller of the function add in X" enumerates
    {symbol.index.ast, change_impact.testselect}; symbol.index.ast names the
    requested effect and its artifact is a REAL callers_of map. Later input
    derivation also made testselect/an inliner bindable, so effect eligibility
    must precede ambiguity counting, not rely on unrelated tools failing to
    bind. Multiple effect-eligible admissions still refuse.
    """
    fam = _family_hits(goal)
    if fam is None:
        return None
    triggers, terms, token = fam
    operations = derivation.stated_git_operations(goal) if token == GIT_FAMILY_TOKEN else ()
    if len(operations) > 1 or (operations and re.search(r"\bbisect\b", front.prose_only(goal), re.I)):
        return None  # a history noun must not turn a bisection into a log read
    if operations and len(derivation._stated_directories(goal, root)) > 1:
        return None  # an optional repository slot must never erase scope ambiguity
    candidates: list[str] = []
    for cid, entry in sorted(registry.items()):
        if not cid.startswith(_FAMILY_SWE_PREFIXES):
            continue
        # Apply the existing family-effect constraint BEFORE admission and
        # ambiguity counting. Shared keywords and bindable inputs do not make
        # an inliner/test selector an answer to a caller-index request. Filtering
        # only after len(admitted) rejected the real index when those unrelated
        # tools became bindable, and wasted their contract-binding work.
        provides_surface = " ".join(map(str, entry.get("provides") or [])).lower()
        if token not in cid.lower() and not (
            cid == "software.analysis.diagnose_and_architect.v1" and token in provides_surface
        ):
            continue
        if operations:
            contract = selection.contract_of(entry, declared.get(cid))
            args = contract.get("args", {}) if isinstance(contract, Mapping) else {}
            # A specific operation needs an operation-bearing contract. A
            # bisector's bindable source_root alone cannot answer "git blame".
            if "op" not in args:
                continue
        surface = " ".join(map(str, (entry.get("keywords") or []) +
                               (entry.get("provides") or []))) + " " + cid
        low = surface.lower()
        if any(term in low for term in terms):
            candidates.append(cid)
    if not candidates:
        return None
    # A family trigger that sits INSIDE a longer phrase another row declares is
    # not the sentence's effect; it is that phrase's object.  "Inline the
    # single-use helper _price_with_tax in X into its only caller" contains
    # "caller", so the caller family claimed authority and executed the symbol
    # index -- a report -- for a refactor, which then failed the promised-source-
    # change gate.  The inliner's own keyword "only caller" states what the
    # sentence asks for.  Enumerate that DECLARED-phrase evidence first, admit it
    # with the same oracle, and only an unambiguous admission wins.
    admitted: list[tuple[str, dict]] = []
    for cid in candidates:
        try:
            decision = selection.admit(goal, cid, registry[cid], root, declared.get(cid))
        except Exception:
            continue
        if (decision.get("admitted") and decision.get("specific")
                and (not operations or (decision.get("inputs") or {}).get("op") == operations[0])):
            admitted.append((cid, dict(decision.get("inputs") or {})))
    rivals = _phrase_rivals(goal, triggers, token, registry) if not operations else set()
    if rivals:
        rival_hits: list[tuple[str, dict]] = []
        for cid in sorted(rivals):
            try:
                decision = selection.admit(goal, cid, registry[cid], root, declared.get(cid))
            except Exception:
                continue
            if decision.get("admitted") and decision.get("specific"):
                rival_hits.append((cid, dict(decision.get("inputs") or {})))
        if any(c == "python.refactor.move_symbol.v1" for c, _ in admitted):
            rival_hits = [(c, inp) for c, inp in rival_hits if c != "python.refactor.move_function.v1"]
        if len(rival_hits) == 1:
            return rival_hits[0]
        if len(rival_hits) > 1:
            return None  # two declared phrases could be the request -> refuse
        if not admitted:
            return None  # the declared phrase is the subject and nothing in-family bound
    if len(admitted) > 1:
        cids_set = {c for c, _ in admitted}
        if "python.refactor.move_symbol.v1" in cids_set and "python.refactor.move_function.v1" in cids_set:
            admitted = [(c, inp) for c, inp in admitted if c != "python.refactor.move_function.v1"]
    if len(admitted) > 1:
        stated_py = {
            p for p in derivation.stated_existing_files(goal, root)
            if p.endswith(".py")
        }
        if stated_py:
            exact_file_admitted = [
                (cid, inp) for cid, inp in admitted
                if "diff_path" in inp or "module" in inp or "from_file" in inp or "source_module" in inp
            ]
            if len(exact_file_admitted) == 1:
                admitted = exact_file_admitted
    if len(admitted) != 1:
        return None  # ambiguous / none -> fail closed
    cid, inputs = admitted[0]
    surface_check = " ".join([cid.lower(), " ".join(str(x).lower() for x in (registry[cid].get("provides") or []))])
    if token not in surface_check and not (token == "function" and ("implement_function_spec" in cid or "polyglot" in cid)) and not (token == "regression" and ("choreograph" in cid or "swe.transform_and_synthesize" in cid)):
        return None  # effect-inconsistent -> no false PASS
    return cid, inputs


# Measured 2026-10-29.  Three registered capabilities answer the word "repair":
# the test-guided patch SEARCH (read-only: it restores the source and reports the
# patch, hard non-claim NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY), the iterative
# repair LOOP (same non-claim) and ``python.software.repair.apply.verified.v1``,
# which is the one that WRITES and then re-runs the stated test IN PLACE.  The
# door's verdict is worded as a repair, so the sentence "fix X so its tests pass"
# was answered by a capability that found the fix, threw it away, and reported
# -- and the door returned PASS__..._EXECUTED_AND_VERIFIED while the file on disk
# was byte-identical and the stated test still failed.  Selecting by which
# mechanism can COMPLETE the stated effect is the same rule the effect gate
# already applies one layer up; here it is applied to the choice between three
# capabilities that share a verb.
_REPAIR_EFFECT_WORDS = ("repair", "fix", "fixed", "broken", "bug", "correct", "make it pass")
_APPLYING_REPAIR_CAPABILITY = "python.software.repair.apply.verified.v1"


def _states_a_repair(goal: str) -> bool:
    low = front.prose_only(str(goal or "")).lower()
    return any(re.search(r"\b" + re.escape(word) + r"\b", low)
               for word in _REPAIR_EFFECT_WORDS)


def _prefer_the_writing_repair(goal: str, cid: str, inputs: dict, registry: dict,
                               root: pathlib.Path, declared: dict) -> tuple[str, dict]:
    """Swap a read-only repair for the one that lands the change, when it admits.

    Admission is still the oracle: the applying capability is used only if it
    binds every declared input from this sentence.  When it does not bind, the
    caller keeps the capability it already had -- nothing is fabricated, and a
    sentence that names no test stays on the read-only path exactly as before.
    """
    # This optimization promotes a repair search, never a different operation.
    # Quoted messages and path components cannot authorize a source write.
    effects = (registry.get(cid) or {}).get("provides") or []
    repair_contract = any("repair" in str(e) or "patch.candidate" in str(e)
                          or "patch.search" in str(e) for e in effects)
    if not repair_contract or not _states_a_repair(goal) or cid == _APPLYING_REPAIR_CAPABILITY:
        return cid, inputs
    entry = registry.get(_APPLYING_REPAIR_CAPABILITY)
    if not entry:
        return cid, inputs
    try:
        decision = selection.admit(goal, _APPLYING_REPAIR_CAPABILITY, entry, root,
                                   declared.get(_APPLYING_REPAIR_CAPABILITY))
    except Exception:
        return cid, inputs
    if not (decision.get("admitted") and decision.get("specific")):
        return cid, inputs
    # The applying capability must be able to name a suite to verify against --
    # stated by the sentence, or discovered in the directory it states.  Without
    # one there is nothing to prove the write against, and the read-only path is
    # the honest answer.  This is the same derivation the caller will use, so the
    # decision is made on exactly the inputs the plan would carry.
    try:
        _, values, _ = derivation.binding_view(goal, entry, root)
    except Exception:
        return cid, inputs
    if not (values.get("test_paths") or (decision.get("inputs") or {}).get("test_paths")):
        return cid, inputs
    return _APPLYING_REPAIR_CAPABILITY, {**dict(decision.get("inputs") or {}), **values}


_PLAN_REG_CACHE: dict[str, Any] = {}


def _fast_verified_registry_and_decls(root: pathlib.Path, compiled_context=None) -> tuple[dict, Any]:
    reg_file = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    ev_dir = root / "canonical/astra_runtime/evidence"
    try:
        key = (
            str(root.resolve()),
            reg_file.stat().st_mtime_ns,
            reg_file.stat().st_size,
            ev_dir.stat().st_mtime_ns if ev_dir.is_dir() else 0,
            id(live_brain.load_verified_registry),
        )
    except OSError:
        key = None
    if compiled_context is not None:
        reg = dict(compiled_context[0])
        if key is not None and _PLAN_REG_CACHE.get("decl_key") == key[:3]:
            return reg, _PLAN_REG_CACHE["decls"]
        decls = selection.declarations(root)
        if key is not None:
            _PLAN_REG_CACHE["decl_key"] = key[:3]
            _PLAN_REG_CACHE["decls"] = decls
        return reg, decls
    if key is not None and _PLAN_REG_CACHE.get("reg_key") == key:
        return dict(_PLAN_REG_CACHE["reg"]), _PLAN_REG_CACHE["decls"]
    reg = dict(live_brain.load_verified_registry())
    decls = selection.declarations(root)
    if key is not None:
        _PLAN_REG_CACHE["reg_key"] = key
        _PLAN_REG_CACHE["reg"] = reg
        _PLAN_REG_CACHE["decl_key"] = key[:3]
        _PLAN_REG_CACHE["decls"] = decls
    return dict(reg), decls


def build_plan(goal: str, root: Any, *, compiled_context=None) -> tuple[dict, dict, dict] | None:
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
        registry, declared = _fast_verified_registry_and_decls(root, compiled_context)
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
            chosen = str(decision.get("selected_capability") or "")
            if (decision.get("status") == "SELECTED" and chosen
                    and _effect_consistent(goal, chosen, registry.get(chosen))):
                cid = str(decision.get("selected_capability"))
                inputs = dict(decision.get("inputs") or {})
            else:
                return None  # ambiguity / effect-inconsistent -> refuse

        # The stated effect decides which mechanism answers it (see above).
        cid, inputs = _prefer_the_writing_repair(goal, cid, inputs, registry, root, declared)

        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        entry = dict(admissible.get(cid) or registry.get(cid) or {})
        if not entry:
            return None
        shadow, values, report = derivation.binding_view(goal, entry, root)
        inputs = {**inputs, **values}
        removed = set((report.get("adapter_defaulted") or {}).keys())

        # Destination identity comes from the stated ROLE, not file existence.
        # F7/F13 can spool an occupied report elsewhere; then repair preflight
        # checks that spool instead of the user's destination, making the verdict
        # depend on previous requests. Reuse the front compiler's role detector
        # (including its aliases and repeated-mention handling). This grants no
        # overwrite authority: the existing adapter/preflight still judges the
        # actual destination. Multiple stated destinations are ambiguous.
        destinations = (front._named_output_destinations(goal, entry, ("output_path",), root)
                        if "output_path" in inputs else set())
        if len(destinations) > 1:
            return None
        if destinations:
            inputs["output_path"] = next(iter(destinations))
        else:
            # Only relocate an incidental source binding. Never move a report
            # the sentence explicitly directs onto an existing source file;
            # preserve that path so the write/repair guards can refuse it.
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
        exec_entry["action_template"] = _execution_template(entry, removed, inputs)
        admissible[cid] = exec_entry

        # Fast path: when compiled_context was already supplied by the caller,
        # reuse its base dict; otherwise construct the synthetic single-capability
        # plan directly without paying a redundant full-registry lexical compile
        # (~73 ms saved per stated SWE call, since every semantic slot is set below).
        if compiled_context is not None and isinstance(compiled_context[2], Mapping):
            compiled = dict(compiled_context[2])
            compiled.setdefault("finish_summary", "RAW_GOAL_COMPLETE")
        else:
            compiled = {
                "schema": SCHEMA, "capabilities": [cid], "compiled_parts": [],
                "score": 0, "match_evidence": {}, "initial_facts": {},
                "finish_summary": "RAW_GOAL_COMPLETE",
            }
        compiled["selected_capability"] = cid
        compiled["inputs"] = inputs
        compiled["compiler_mode"] = "SWE_TYPED_PLAN_V1"
        # The original lexical plan may describe a DIFFERENT capability. Its
        # effects and evidence cannot follow a corrected typed selection.
        compiled["target_effects"] = list(entry.get("provides") or []) or [cid]
        compiled["initial_facts"] = list(entry.get("requires") or [])
        compiled["compiled_parts"] = []
        compiled["capabilities"] = [cid]
        score, _, evidence = goal_compiler._score(goal, cid, entry)
        compiled["score"] = score
        compiled["match_evidence"] = evidence
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


_COMPOUND_SUBORDINATE_GUARD = re.compile(
    r"\b(?:update\s+(?:every|all|its|the)\s+(?:callers?|imports?)|"
    r"make\s+(?:mypy|the\s+(?:whole\s+)?suite|all\s+tests|it|sure)\b|"
    r"(?:save|write)\s+(?:it|them|the\s+\w+)\s+to\b|"
    r"write\s+(?:the\s+)?release\s+notes|"
    r"produce\s+a\s+lock\s+file|record\s+the\s+baseline|"
    r"keep(?:ing)?\s+(?:every\s+test|the\s+suite)\s+green|"
    r"use\s+it\s+in\b|update\s+\S+\s+to\s+use\b|"
    r"add\s+a\s+regression\s+test|commit\s+\S+\s+there\b|"
    r"fix\s+what\s+(?:breaks|it\s+reports)|tell\s+me\b|prove\s+it\b)",
    re.IGNORECASE,
)

_COMPOUND_CLAUSE_SPLITTER = re.compile(
    r"(?:\s*;\s+|\s+and\s+then\s+|\s*,\s*then\s+"
    r"|\s+and\s+(?=(?:rename|add\s+type\s+hints|remove\s+(?:unused|dead)|format|reformat|"
    r"inline|extract|move|split|port|translate|convert|transpile|write\s+(?:a\s+)?unit\s+tests?|"
    r"generate\s+unit\s+tests?|commit\s+the\s+changes|run\s+(?:the\s+)?tests?)\b))",
    re.IGNORECASE,
)


def split_compound_swe_goal(goal: str, root: Any) -> list[str] | None:
    """Split a multi-step SWE sentence into >=2 independently decisive clauses, or None."""
    text = str(goal or "").strip()
    if not text or not _COMPOUND_CLAUSE_SPLITTER.search(text):
        return None
    if _COMPOUND_SUBORDINATE_GUARD.search(text):
        return None
    parts = [p.strip().rstrip(".") + "." for p in _COMPOUND_CLAUSE_SPLITTER.split(text) if p and p.strip()]
    if len(parts) < 2 or len(parts) > 6:
        return None
    root_p = pathlib.Path(root)
    for part in parts:
        if not derivation.stated_existing_files(part, root_p) and not derivation._stated_directories(part, root_p):
            return None
        if build_plan(part, root_p) is None:
            return None
    return parts

