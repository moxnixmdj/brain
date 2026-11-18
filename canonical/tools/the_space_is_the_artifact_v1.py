#!/usr/bin/env python3
"""The space is the artifact, not the neighbourhood -- and here is its ceiling.

What the previous round established, and what it left standing
--------------------------------------------------------------
`the_same_guard_twice_is_the_discriminator_v1` turned identification into an execution: flip one firing of
one guard, one bit, no model. On 15 fresh real commits it reached the human's changed line 3 times and the
human's expression 0 times. The address was cheap; the *content* was not there. This round takes the next
question, which is the only one left that is not anecdote:

    if the address is GIVEN -- the human's line, for free, an upper bound no system could beat on this
    population -- how much of a real fix can a ZERO-PARAMETER space over the artifact's own vocabulary
    even express, and what does it cost in oracle calls to reach it?

That is a ceiling, not a demo. If the answer is low, then no amount of retention, indexing, flips,
forced values or instant knowledge can close the gap, because the missing thing is not in the artifact's
vocabulary at all -- and the "best part is no part" law has to be read as *the smallest calculated prior
that closes the gap*, not as "zero parameters forever". If the answer is high, the wall was the space's
*construction* and the next round is an ordering problem.

The one construction this round adds
------------------------------------
The merged proximity pool collects the attribute chains that already appear near the site, so a fix like

    ca.converter  ->  ca._converter            (attrs 0f758fe54a, the attribute is defined 40 lines away)

is not in it: `self._converter` was collected, `ca._converter` never was, because nothing crossed the
bases that are in scope with the attribute names the artifact itself defines and uses. Crossing them is
the whole idea of this file, and it is calculated, not learned:

    atoms = site's own operands + names in scope + (base x attribute vocabulary of the file) + literals

then closed under the language's own grammar (the tree's `expressions_from_a_site_v1` combinations), and
ordered by ring then size -- Occam, no parameters.

Integrity
---------
  1. The population is mined by a stated mechanical rule and screened before anything is measured, on the
     parent commit with the post-fix test file: a test must actually FAIL (a skip is not a failure).
  2. The human's expression is read ONLY after the search has produced its verdict, to score the rank. It
     never enters the space, the order, or the stopping rule.
  3. A candidate counts only if the WHOLE test file stays green on an uninstrumented copy.
  4. A row whose fix is not a single expression replacement is EXCLUDED and named, not silently dropped.
  5. The space is capped, and a fix outside the cap is `OUTSIDE_CAP`, never "impossible" -- the tree's own
     completeness-witness rule, learned from `is_the_fix_even_in_the_pool_v1`.

Zero model calls, zero stored parameters, no network at run time. Authority NONE.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import what_a_real_fix_needs_from_the_site_v1 as needs  # noqa: E402
import expressions_from_a_site_v1 as expressions  # noqa: E402

SCHEMA = "BRAIN_THE_SPACE_IS_THE_ARTIFACT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
HUNK = __import__("re").compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


# ----------------------------------------------------------------------------------------------------
# population: mined by a rule, screened before measurement
# ----------------------------------------------------------------------------------------------------


def git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          errors="replace").stdout


def candidates(repo: pathlib.Path, limit: int = 600, stride: int = 5, skip: int = 0) -> list[dict[str, Any]]:
    """Commits that touch a test file and a source file, spaced by the stride, newest first."""
    log = git(repo, "log", "--no-merges", f"-n{limit}", "--format=@@%H", "--name-only")
    out: list[dict[str, Any]] = []
    for block in log.split("@@"):
        lines = [line for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        sha, files = lines[0].strip(), lines[1:]
        tests = [f for f in files if f.startswith("tests/") and f.endswith(".py")]
        source = [f for f in files if f.endswith(".py") and not f.startswith("tests/")
                  and "test" not in f and not f.endswith("conftest.py")]
        if not tests or not source:
            continue
        out.append({"repo": repo.name, "commit": sha, "sources": source, "tests": tests})
    return out[skip::stride]


def screen(entry: dict[str, Any], repo: pathlib.Path, seconds: int) -> dict[str, Any]:
    """Does the oracle exist? Parent commit, post-fix test file, at least one real failure."""
    sha = entry["commit"]
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                f"{sha}^"], capture_output=True, text=True)
        if added.returncode != 0:
            return {"keep": False, "why": "WORKTREE_FAILED"}
        try:
            for test in entry["tests"][:2]:
                text = identify.show(repo, sha, test)
                if not text.strip():
                    continue
                (worktree / test).write_text(text, encoding="utf-8")
            best = None
            for test in entry["tests"][:2]:
                if not (worktree / test).exists():
                    continue
                verdicts, output = identify.run_tests_full(worktree, test, seconds)
                lowered = (output or "").lower()
                if not verdicts or "error during collection" in lowered or "interrupted:" in lowered:
                    continue
                failing = identify.failing_tests(verdicts)
                if failing:
                    best = {"test": test, "failing": failing[0], "failing_count": len(failing),
                            "tests_in_file": len(verdicts)}
                    break
            if best is None:
                return {"keep": False, "why": "NO_ORACLE"}
            share = best["failing_count"] / max(best["tests_in_file"], 1)
            if share >= 0.10:
                return {"keep": False, "why": f"FAILING_SHARE_TOO_HIGH:{share:.3f}"}
            return {"keep": True, **best, "failing_share": round(share, 4)}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


# ----------------------------------------------------------------------------------------------------
# the site: the human's changed expression, located in the parent source
# ----------------------------------------------------------------------------------------------------


def hunk_lines(repo: pathlib.Path, sha: str, path: str) -> list[dict[str, Any]]:
    """Zero-context hunks with their parent-side line numbers and their removed/added text."""
    done = subprocess.run(["git", "-C", str(repo), "show", "--unified=0", "--format=", sha, "--", path],
                          capture_output=True, text=True, errors="replace")
    hunks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in done.stdout.splitlines():
        match = HUNK.match(line)
        if match:
            current = {"parent_start": int(match.group(1)), "removed": [], "added": []}
            hunks.append(current)
            continue
        if current is None:
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            current["removed"].append(line[1:])
        elif line.startswith("+"):
            current["added"].append(line[1:])
    return hunks


def site_of(repo: pathlib.Path, sha: str, path: str,
            parent_source: str) -> dict[str, Any] | None:
    """The one-expression edit in this file, as (line, old_expression, old_span, human_expression)."""
    return site_or_reason(repo, sha, path, parent_source)[0]


def site_or_reason(repo: pathlib.Path, sha: str, path: str,
                   parent_source: str) -> tuple[dict[str, Any] | None, str]:
    """Why a commit is or is not a single-expression replacement, in the population's own words.

    Half of the fresh population is not one expression, and the kinds are different: a line that does not
    parse is a statement split across lines (a fragment, and a fragment is not a fix that any space over
    expressions could be asked to say), a change of two or more independent places is an edit of two
    things, and a change whose shared ancestor is a statement is a statement-form edit. Reporting all
    three as "excluded" would hide the structure of the population this claim is about.
    """
    reason = "NO_SINGLE_LINE_PAIR_IN_ANY_HUNK"
    for hunk in hunk_lines(repo, sha, path):
        removed = [text for text in hunk["removed"] if text.strip()]
        added = [text for text in hunk["added"] if text.strip()]
        if len(removed) != 1 or len(added) != 1:
            reason = "MULTI_LINE_EDIT"
            continue
        old_line, new_line = removed[0].strip(), added[0].strip()
        try:
            old_tree = identify.parse_line(old_line)
            new_tree = identify.parse_line(new_line)
        except SyntaxError:
            reason = "THE_LINE_IS_A_FRAGMENT_OF_A_LARGER_STATEMENT"
            continue
        changes = needs.change_points(old_tree, new_tree)
        if not changes:
            reason = "NOTHING_DIFFERS_AS_AN_EXPRESSION"
            continue
        if len(changes) > 4:
            reason = "MORE_THAN_FOUR_INDEPENDENT_CHANGES"
            continue
        # A rewrite changes several nodes at once: `x + 1 -> x * 2` differs in the operator AND in the
        # operand, and requiring exactly one differing node threw away every such repair -- 10 of 19
        # fresh commits were "excluded" for it before this was fixed. The site is the SMALLEST
        # ENCLOSING EXPRESSION the human touched, which is the common ancestor of the change points.
        paths = [path for path, _old, _new in changes]
        shared = paths[0]
        for path in paths[1:]:
            cut = 0
            while cut < len(shared) and cut < len(path) and shared[cut] == path[cut]:
                cut += 1
            shared = shared[:cut]
        if not shared:
            reason = "THE_CHANGES_HAVE_NO_COMMON_ENCLOSING_NODE"
            continue
        old_paths, new_paths = needs.paths_of(old_tree), needs.paths_of(new_tree)
        if shared not in old_paths or shared not in new_paths:
            reason = "THE_SHARED_NODE_IS_NOT_IN_BOTH"
            continue
        old_expr, new_expr = old_paths[shared], new_paths[shared]
        if not (isinstance(old_expr, ast.expr) and isinstance(new_expr, ast.expr)):
            reason = "THE_SHARED_NODE_IS_A_STATEMENT_NOT_AN_EXPRESSION"
            continue
        line = hunk["parent_start"] + hunk["removed"].index(removed[0])
        span = identify.span_of(parent_source, line, old_expr)
        if span is None:
            # the standalone parse rewrites `elif`; fall back to matching the node text on that line
            span = span_by_text(parent_source, line, ast.unparse(old_expr))
        if span is None:
            reason = "THE_SPAN_IS_NOT_IN_THE_PARENT_SOURCE"
            continue
        return ({"line": line, "old_expression": ast.unparse(old_expr),
                 "human_expression": ast.unparse(new_expr), "span": span}, "SINGLE_EXPRESSION")
    return (None, reason)


EXPRESSION_BEARING = {ast.Assign: "value", ast.AnnAssign: "value", ast.AugAssign: "value",
                   ast.Return: "value", ast.Expr: "value", ast.If: "test", ast.While: "test",
                   ast.Assert: "test"}


def expression_of(statement: ast.AST) -> ast.expr | None:
    for kind, field in EXPRESSION_BEARING.items():
        if isinstance(statement, kind):
            node = getattr(statement, field, None)
            return node if isinstance(node, ast.expr) else None
    return None


def _text(statement: ast.AST) -> str:
    try:
        return ast.unparse(statement)
    except Exception:  # noqa: BLE001
        return repr(statement)


def _descend(old_body: list[ast.stmt], new_body: list[ast.stmt],
             depth: int = 0) -> tuple[ast.stmt, ast.stmt, str] | str:
    """The single statement the two revisions disagree about, or a reason they disagree about more."""
    import difflib
    left, right = [_text(s) for s in old_body], [_text(s) for s in new_body]
    regions = [op for op in difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes()
               if op[0] != "equal"]
    if not regions:
        return "NOTHING_DIFFERS_AT_AST_LEVEL"
    if len(regions) > 1:
        return "MORE_THAN_ONE_CHANGE_REGION"
    tag, i1, i2, j1, j2 = regions[0]
    olds, news = old_body[i1:i2], new_body[j1:j2]
    if not olds or not news:
        # a pure insertion or deletion is a different edit operation, not a replacement; refusing it is a
        # statement about this tool, and it is named rather than folded into "not a single expression".
        return "THE_CHANGE_INSERTS_OR_DELETES_WHOLE_STATEMENTS"
    if len(olds) == 1 and len(news) == 1:
        old, new = olds[0], news[0]
        if isinstance(old, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and type(old) is type(new) and getattr(new, "name", None) == getattr(old, "name", None):
            return _descend(old.body, new.body, depth + 1)
        if expression_of(old) is not None and expression_of(new) is not None:
            return old, new, type(old).__name__
        return "THE_CHANGED_STATEMENT_CARRIES_NO_SINGLE_EXPRESSION"
    return "MORE_THAN_ONE_STATEMENT_CHANGED"


def semantic_site(parent_source: str, child_source: str) -> tuple[dict[str, Any] | None, str]:
    """The site of the fix, read from the two revisions rather than from their diff's line shape.

    `MULTI_LINE_EDIT` is a fact about formatting. `frozenset(["a"])` rewritten over three lines is one
    expression; a line moved three lines up is no new expression at all. Comparing the two revisions as
    ASTs deletes formatting, comments and continuation lines, so what differs afterwards is the change the
    program actually underwent -- and 4 of the 15 rows this tool excluded as "not a single expression" are
    one statement once that is done.
    """
    try:
        old_tree, new_tree = ast.parse(parent_source), ast.parse(child_source)
    except SyntaxError:
        return None, "THE_REVISION_DOES_NOT_PARSE"
    located = _descend(old_tree.body, new_tree.body)
    if isinstance(located, str):
        return None, located
    old_statement, new_statement, kind = located
    old_expr, new_expr = expression_of(old_statement), expression_of(new_statement)
    if old_expr is None or new_expr is None:
        return None, "THE_CHANGED_STATEMENT_CARRIES_NO_SINGLE_EXPRESSION"
    if getattr(old_expr, "end_lineno", old_expr.lineno) != old_expr.lineno:
        # The finder located the fix and the patcher cannot address it: a site that spans several source
        # lines needs an absolute-offset splice, and this patcher replaces one line's columns. Naming the
        # real cause matters -- "the span is not in the parent source" would blame the source.
        return None, "THE_CHANGED_EXPRESSION_SPANS_SEVERAL_LINES"
    span = identify.span_of(parent_source, old_expr.lineno, old_expr)
    if span is None:
        return None, "THE_SPAN_IS_NOT_IN_THE_PARENT_SOURCE"
    return ({"line": old_expr.lineno, "old_expression": ast.unparse(old_expr),
             "human_expression": ast.unparse(new_expr), "span": span},
            "SINGLE_STATEMENT_" + kind)


STATEMENT_EXPRESSIONS = ((ast.Return, "value"), (ast.Expr, "value"), (ast.Assign, "value"),
                         (ast.If, "test"), (ast.While, "test"), (ast.For, "iter"))


def sites_in_function(source: str, line: int, limit: int = 8,
                      exclude: int | None = None) -> list[dict[str, Any]]:
    """Every statement-level expression in the function the change lives in.

    A demand is a value; the site that produces it does not have to be the site the human touched. Asking
    the same demand at the other productions in the same function is the composition the grammar was
    missing -- and it costs no combinatorics, because the value is fixed and only its producer moves.

    The human's line is never offered, by construction: it is the answer key, and a run that reads it is
    not a run. Measured on 30 real commits, 27 such shifts verified 0 repairs: another site is not
    another production, and that is a fact about the population, not a bug in this function.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    function = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.lineno <= line <= (getattr(node, "end_lineno", None) or node.lineno):
            if function is None or node.lineno >= function.lineno:
                function = node
    if function is None:
        return []
    skip = {line} | ({exclude} if exclude is not None else set())
    found: list[dict[str, Any]] = []
    for node in ast.walk(function):
        for kind, field in STATEMENT_EXPRESSIONS:
            if not isinstance(node, kind):
                continue
            expression = getattr(node, field, None)
            if not isinstance(expression, ast.expr):
                continue
            where = getattr(expression, "lineno", None)
            if where is None or where in skip:
                continue
            if getattr(expression, "end_lineno", where) != where:
                continue  # the patcher replaces one line's columns; a spanning site is named elsewhere
            span = identify.span_of(source, where, expression)
            if span is None:
                continue
            text = ast.unparse(expression)
            if any(item["line"] == where and item["old_expression"] == text for item in found):
                continue
            found.append({"line": where, "old_expression": text, "human_expression": text,
                          "span": span})
    found.sort(key=lambda item: abs(item["line"] - line))
    return found[:limit]


def census(entries: Sequence[dict[str, Any]], repos_root: pathlib.Path) -> list[dict[str, Any]]:
    """The population's shape, with no oracle calls: what kind of edit each fresh commit is."""
    rows: list[dict[str, Any]] = []
    for entry in entries:
        repo = pathlib.Path(entry.get("repo_path") or (repos_root / entry["repo"]))
        parent = f"{entry['commit']}^"
        found, reasons = None, []
        for source_path in entry["sources"]:
            text = identify.show(repo, parent, source_path)
            if not text:
                continue
            site, why = site_or_reason(repo, entry["commit"], source_path, text)
            reasons.append({"source": source_path, "why": why})
            if site is not None and found is None:
                found = {"source": source_path, **{key: site[key] for key in
                                                   ("line", "old_expression", "human_expression")}}
        rows.append({"repo": entry["repo"], "commit": entry["commit"], "test": entry.get("test"),
                     "site": found, "reasons": reasons,
                     "kind": "SINGLE_EXPRESSION" if found else
                             (reasons[0]["why"] if reasons else "NO_SOURCE_FILE")})
    return rows


def span_by_text(source: str, line: int, text: str) -> tuple[int, int] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.expr) or getattr(node, "lineno", None) != line:
            continue
        if getattr(node, "end_lineno", None) != line:
            continue
        try:
            if ast.unparse(node) == text:
                return node.col_offset, node.end_col_offset
        except Exception:  # noqa: BLE001
            continue
    return None


# ----------------------------------------------------------------------------------------------------
# the space: the artifact's own vocabulary, crossed, then closed under the language's grammar
# ----------------------------------------------------------------------------------------------------


def attribute_vocabulary(source: str) -> list[str]:
    """Every attribute name the file itself uses or defines -- `self._converter = ...` is in here."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and not node.attr.startswith("__"):
            names.add(node.attr)
    return sorted(names)


def atoms(source: str, line: int, site_text: str, *, bases_cap: int = 24,
          attributes_cap: int = 400, include_builtins: bool = False) -> list[tuple[int, str]]:
    """(ring, text). Ring 0: the site's own operands. 1: what is in scope. 2: base x attribute. 3: literals."""
    ring: list[tuple[int, str]] = []
    seen: set[str] = set()

    def add(level: int, text: str, *, literal: bool = False) -> None:
        text = text.strip()
        if not text or text in seen or len(text) > 48:
            return
        try:
            node = ast.parse(text, mode="eval").body
        except SyntaxError:
            return
        if isinstance(node, ast.Constant) and not literal:
            return  # a bare constant is not a base for anything; it enters as a literal below
        seen.add(text)
        ring.append((level, text))

    try:
        site = ast.parse(site_text, mode="eval").body
    except SyntaxError:
        site = None
    if site is not None:
        for node in ast.walk(site):
            if isinstance(node, ast.Constant) and isinstance(node.value, (bool, type(None))):
                add(0, repr(node.value), literal=True)
        for node in ast.walk(site):
            if isinstance(node, ast.expr) and not isinstance(node, (ast.Constant, ast.Slice,
                                                                    ast.FormattedValue, ast.Starred)):
                try:
                    add(0, ast.unparse(node))
                except Exception:  # noqa: BLE001
                    continue
    scope = needs.names_in_scope(source, line)
    # `dir(builtins)` is the machine's own vocabulary, computed in microseconds and never stale. It was
    # filtered out here at first, which is the same mistake as refusing `str.join`: a fix that renames
    # `hash_` to the builtin `hash` was then unsayable for a reason that had nothing to do with the world.
    available = scope if include_builtins else scope - set(dir(builtins))
    plain: list[str] = []
    for name in sorted(available):
        if name.isidentifier() and not name.startswith("__"):
            add(1, name)
            plain.append(name)
    vocabulary = attribute_vocabulary(source)[:attributes_cap]
    for base in plain[:bases_cap]:
        for attribute in vocabulary:
            add(2, f"{base}.{attribute}")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    for constant in (True, False, None):
        add(3, repr(constant), literal=True)
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and len(repr(node.value)) <= 30:
                add(3, repr(node.value), literal=True)
    return ring


def live_vocabulary() -> list[str]:
    """The attribute vocabulary of the MACHINE, computed by asking it -- nothing stored, nothing frozen.

    This is the whole reason the ceiling is worth measuring: a space over the artifact's own words cannot
    say `", ".join(parts)` unless the artifact happens to mention `join`, and most artifacts do not. The
    interpreter, however, knows exactly which attributes a `str` has, and `dir(str)` costs 4 microseconds
    and no parameters. Knowledge of the library is not stored here; it is computed, at run time, from the
    thing that will run the fix.
    """
    names: set[str] = set()
    for kind in (str, bytes, list, dict, set, tuple, int, float, complex, type(None)):
        try:
            names.update(attribute for attribute in dir(kind) if not attribute.startswith("_"))
        except Exception:  # noqa: BLE001
            continue
    return sorted(names)


def widened(source: str, line: int, site_text: str, *, over: int = 12,
            live_cap: int = 120) -> list[tuple[int, str]]:
    """The same atoms, closed under the FOUR productions the first sweep's misses named.

    Every production here is the language's own grammar and nothing else -- a call, a comprehension, a
    membership test, a subscript. No template, no pattern, no knowledge. They exist so that a claim about
    the space's ceiling can be separated from a claim about this construction's poverty: if the human's
    expression is still absent once the grammar can say a call and a comprehension, the wall is not here.
    """
    base = [text for level, text in atoms(source, line, site_text) if level <= 1]
    plain = [text for text in base if not text.startswith(("'", '"'))][:over]
    # a literal is a legitimate base for a method call (`", ".join(parts)`), and refusing it would be a
    # construction defect masquerading as a ceiling -- the tree has made that mistake once already.
    literals = [text for level, text in atoms(source, line, site_text)
                if text.startswith(("'", '"'))][:8]
    callable_like = [text for text in plain + literals if "." in text or text.isidentifier()
                     or text.startswith(("'", '"'))]
    made: list[tuple[int, str]] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        if text in seen or len(text) > 96:
            return
        try:
            ast.parse(text, mode="eval")
        except SyntaxError:
            return
        seen.add(text)
        made.append((5, text))

    # a method named on a literal (`", ".join(..)`) is a literal base crossed with the file's own
    # attribute vocabulary; without this the production cannot say it, which is a fact about the
    # production, not about the language.
    live = live_vocabulary()[:live_cap]
    crossed_literal = [f"{literal}.{attribute}" for literal in literals[:6]
                       for attribute in attribute_vocabulary(source)[:40] + live]
    # a value's own methods: the production that turns `args` into `args.copy()` or `parts` into
    # `parts.join(..)`, with the attribute names taken from the running interpreter.
    crossed_value: list[str] = []
    for text in plain[:over]:
        for attribute in live:
            crossed_value.append(f"{text}.{attribute}")
    for text in crossed_value[:4_000]:
        add(text)
    for function in crossed_value[:over * 8]:
        for argument in plain[:6]:
            add(f"{function}({argument})")
    for function in callable_like[:over] + crossed_literal:
        add(f"{function}()")
        for argument in plain:
            add(f"{function}({argument})")
    for element in plain[:6]:
        for binding in plain[:6]:
            for container in plain[:6]:
                add(f"[{element} for {binding} in {container}]")
                add(f"[{element} for {binding} in {container} if {binding}]")
    for left in plain[:8]:
        for right in plain[:8]:
            add(f"{left} in {right}")
            add(f"{left}[{right}]")
            add(f"{left}.get({right})")
    return made


def space(source: str, line: int, site_text: str, *, cap: int = 200_000,
          combinations_over: int = 60, grammar: str = "base") -> Iterator[tuple[int, str, int]]:
    """(rank, expression, ring) in a deterministic, calculated order: ring, then size, then position."""
    base = atoms(source, line, site_text, include_builtins=grammar == "full")
    ordered = sorted(range(len(base)), key=lambda index: (base[index][0],
                                                          expressions._size(base[index][1]), index))
    pool: list[tuple[int, str]] = [(base[index][0], base[index][1]) for index in ordered]
    head = [base[index][1] for index in ordered[:combinations_over]]
    for left in head:
        for right in head:
            for text in expressions._combinations(left, right, "self"):
                try:
                    ast.parse(text, mode="eval")
                except SyntaxError:
                    continue
                pool.append((4, text))
    if grammar in ("wide", "full"):
        pool.extend(widened(source, line, site_text))
    seen: set[str] = set()
    ordered_pool = sorted(range(len(pool)), key=lambda index: (pool[index][0],
                                                               expressions._size(pool[index][1]), index))
    rank = 0
    for index in ordered_pool:
        level, text = pool[index]
        if text in seen or text == site_text:
            continue
        seen.add(text)
        yield rank, text, level
        rank += 1
        if rank >= cap:
            return


FORM_NODES = {ast.ListComp: "a comprehension", ast.SetComp: "a comprehension",
              ast.DictComp: "a comprehension", ast.GeneratorExp: "a generator expression",
              ast.Lambda: "a lambda", ast.Await: "an await", ast.Yield: "a yield",
              ast.NamedExpr: "a walrus", ast.Starred: "a starred argument"}


def classify_miss(human_expression: str, source: str, line: int, site_text: str) -> list[str]:
    """WHY the artifact's own vocabulary cannot say the human's expression.

    A miss is not one kind of thing, and the next mechanism depends on which kind it is: a name the parent
    file never mentions is a *vocabulary* wall (no space over the parent can express it), a form the
    grammar does not generate is a *grammar* wall (cheap to widen), and a literal whose content appears
    nowhere is a *specification* wall (no amount of search helps).
    """
    reasons: list[str] = []
    try:
        node = ast.parse(human_expression, mode="eval").body
    except SyntaxError:
        return ["THE_EXPRESSION_DOES_NOT_PARSE"]
    for kind, label in FORM_NODES.items():
        if any(isinstance(child, kind) for child in ast.walk(node)):
            reasons.append(f"GRAMMAR__THE_FIX_IS_{label.upper().replace(' ', '_')}")
    if isinstance(node, ast.Tuple):
        reasons.append("GRAMMAR__THE_FIX_IS_A_TUPLE_DISPLAY")
    if any(isinstance(child, ast.Compare) and any(isinstance(op, (ast.Is, ast.IsNot))
                                                  for op in child.ops) for child in ast.walk(node)):
        reasons.append("GRAMMAR__THE_FIX_NEEDS_AN_IDENTITY_COMPARISON")
    calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
    if any(call.keywords for call in calls):
        reasons.append("GRAMMAR__THE_FIX_NEEDS_A_KEYWORD_ARGUMENT")
    if calls:
        # the construction builds no calls at all, so this is the widest cheap wall there is
        reasons.append("GRAMMAR__THE_FIX_NEEDS_A_CALL")
    if isinstance(node, ast.Constant):
        reasons.append("THE_FIX_IS_A_BARE_CONSTANT:" + repr(node.value))
    if expressions._size(human_expression) > expressions.MAX_NODES:
        reasons.append(f"SIZE__{expressions._size(human_expression)}_NODES_OVER_THE_{expressions.MAX_NODES}_CAP")
    vocabulary = set(attribute_vocabulary(source))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    names: set[str] = set()
    if tree is not None:
        for child in ast.walk(tree):
            if isinstance(child, ast.Name):
                names.add(child.id)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(child.name)
            elif isinstance(child, ast.arg):
                names.add(child.arg)
    scope = needs.names_in_scope(source, line)
    unknown = []
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr not in vocabulary:
            unknown.append(f".{child.attr}")
        elif isinstance(child, ast.Name) and child.id not in names and child.id not in scope \
                and not hasattr(builtins, child.id):
            unknown.append(child.id)
    if unknown:
        reasons.append("VOCABULARY__THE_PARENT_FILE_NEVER_MENTIONS:" + ",".join(sorted(set(unknown))[:6]))
    literals = {repr(child.value) for child in ast.walk(node) if isinstance(child, ast.Constant)}
    try:
        site = ast.parse(site_text, mode="eval").body
        literals |= {repr(child.value) for child in ast.walk(site) if isinstance(child, ast.Constant)}
    except SyntaxError:
        pass
    source_literals = set()
    if tree is not None:
        source_literals = {repr(child.value) for child in ast.walk(tree) if isinstance(child, ast.Constant)}
    new_literals = literals - source_literals
    if new_literals:
        reasons.append("SPECIFICATION__NEW_LITERAL_CONTENT:" + ",".join(sorted(new_literals)[:4]))
    return reasons or ["IN_THE_WORLD_BUT_NOT_IN_THIS_CONSTRUCTION"]


# ----------------------------------------------------------------------------------------------------
# the search: blind, ordered, one oracle call per candidate
# ----------------------------------------------------------------------------------------------------


def run_one(worktree: pathlib.Path, test_path: str, node: str, seconds: int) -> str:
    argv = [sys.executable, "-m", "pytest", node, "-x", "-q", "--no-header", "--tb=line",
            "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(argv, cwd=worktree, capture_output=True, text=True, errors="replace",
                              timeout=seconds, stdin=subprocess.DEVNULL,
                              env={**os.environ, **identify.fresh_bytecode(worktree)})
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    text = (done.stdout or "") + (done.stderr or "")
    if done.returncode == 0 and " passed" in text:
        return "PASSED"
    if done.returncode == 1:
        return "FAILED"
    return "NO_RUN"


def explore(repo: pathlib.Path, entry: dict[str, Any], *, budget: int = 48, cap: int = 200_000,
            seconds: int = 120, grammar: str = "base") -> dict[str, Any]:
    started = time.time()
    sha, test_path = entry["commit"], entry["test"]
    parent = f"{sha}^"
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED"}
        try:
            (worktree / test_path).write_text(identify.show(repo, sha, test_path), encoding="utf-8")
            source_path = None
            site = None
            for candidate_source in entry["sources"]:
                text = identify.show(repo, parent, candidate_source)
                if not text:
                    continue
                found = site_of(repo, sha, candidate_source, text)
                if found is not None:
                    source_path, site = candidate_source, found
                    break
            if source_path is None or site is None:
                return {"stage": "EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT",
                        "sources": entry["sources"][:3]}
            node_id = entry.get("failing") or identify.failing_tests(
                identify.run_tests_full(worktree, test_path, seconds)[0])[0]
            node = node_id if "::" in node_id else f"{test_path}::{node_id}"
            original = (worktree / source_path).read_text(encoding="utf-8")
            line, span = site["line"], site["span"]

            human_dump = ast.dump(ast.parse(site["human_expression"], mode="eval").body)
            offered = 0
            human_rank: int | None = None
            visited = 0
            verdicts = 0
            verdict_log: list[dict[str, Any]] = []
            found_at: dict[str, Any] | None = None
            for rank, expression, ring in space(original, line, site["old_expression"], cap=cap,
                                                grammar=grammar):
                visited += 1
                try:
                    if ast.dump(ast.parse(expression, mode="eval").body) == human_dump:
                        human_rank = rank
                except SyntaxError:
                    continue
                if found_at is not None or verdicts >= budget:
                    continue
                patched = identify.replace_site(original, line, span[0], span[1], expression)
                if patched is None:
                    continue
                (worktree / source_path).write_text(patched, encoding="utf-8")
                verdict = run_one(worktree, test_path, node, seconds)
                verdicts += 1
                if len(verdict_log) < 12:
                    # a candidate that "failed" says nothing until the machine says what it saw; the log
                    # exists because a test that flips under load must be able to explain itself
                    verdict_log.append({"rank": rank, "expression": expression[:60], "verdict": verdict})
                if verdict == "PASSED":
                    whole = identify.run_tests(worktree, test_path, seconds)
                    if whole and all(value == "PASSED" for value in whole.values()):
                        found_at = {"rank": rank, "expression": expression, "ring": ring,
                                    "tests_green": len(whole)}
            (worktree / source_path).write_text(original, encoding="utf-8")
            offered = visited
            log = verdict_log
            crossed = human_rank is not None
            if not crossed:
                # was it reachable by the merged construction, i.e. without crossing names with the
                # artifact's attribute vocabulary? That is the delta this round's construction buys.
                site_only: dict[str, Any] | None = None
                for rank, expression, _ring in space(original, line, site["old_expression"], cap=cap,
                                                     combinations_over=0, grammar="base"):
                    try:
                        if ast.dump(ast.parse(expression, mode="eval").body) == human_dump:
                            site_only = {"rank": rank}
                            break
                    except SyntaxError:
                        continue
            else:
                site_only = {"rank": human_rank}
            miss_reasons = [] if crossed else classify_miss(
                site["human_expression"], original, line, site["old_expression"])
            return {
                "stage": "VERIFIED" if found_at else "NO_CANDIDATE_PASSES",
                "sha": sha, "source": source_path, "test_file": test_path, "failing_test": node_id,
                "site_line": line, "site_expression": site["old_expression"],
                "human_expression": site["human_expression"],
                "space_offered": offered, "space_cap": cap, "grammar": grammar,
                "human_expression_in_space": human_rank is not None,
                "human_expression_rank": human_rank,
                "human_expression_in_site_only_space": bool(site_only),
                "human_expression_site_only_rank": (site_only or {}).get("rank"),
                "miss_reasons": miss_reasons,
                "oracle_calls": verdicts, "oracle_budget": budget,
                "verdict_log": log,
                "found": found_at,
                "found_is_the_human_fix": bool(
                    found_at and ast.dump(ast.parse(found_at["expression"], mode="eval").body) == human_dump),
                "parameters_stored": 0,
                "seconds": round(time.time() - started, 2),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def mine(repos: Sequence[str], *, limit: int, stride: int, skip: int, want: int,
         seconds: int) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for name in repos:
        repo = pathlib.Path("/tmp/repos") / name
        kept_here = 0
        for entry in candidates(repo, limit, stride, skip):
            if kept_here >= want:
                break
            result = screen(entry, repo, seconds)
            if not result.get("keep"):
                continue
            kept_here += 1
            kept.append({**entry, **{key: result[key] for key in
                                     ("test", "failing", "failing_count", "tests_in_file")}})
            print(f"KEEP {name} {entry['commit'][:10]} {result['test']} "
                  f"({result['failing_count']}/{result['tests_in_file']})", file=sys.stderr, flush=True)
    return kept


def sweep(entries: Sequence[dict[str, Any]], *, receipt: pathlib.Path, budget: int, cap: int,
          seconds: int, grammar: str = "base") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = pathlib.Path(entry.get("repo_path") or (pathlib.Path("/tmp/repos") / entry["repo"]))
        try:
            result = explore(repo, entry, budget=budget, cap=cap, seconds=seconds, grammar=grammar)
        except Exception as error:  # noqa: BLE001
            result = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:300]}
        row = {key: entry.get(key) for key in ("repo", "commit", "test", "sources")}
        row.update(result)
        rows.append(row)
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:10]} {row.get('stage')} "
              f"in_space={row.get('human_expression_in_space')} rank={row.get('human_expression_rank')} "
              f"calls={row.get('oracle_calls')}", file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)}, indent=1) + "\n")
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mine", nargs="+", metavar="REPO", help="mine and screen a fresh corpus")
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--limit", type=int, default=600)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--want", type=int, default=4)
    parser.add_argument("--commits", type=pathlib.Path)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--budget", type=int, default=48)
    parser.add_argument("--cap", type=int, default=200_000)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--only", default="")
    parser.add_argument("--grammar", choices=("base", "wide", "full"), default="base")
    parser.add_argument("--census-only", action="store_true")
    args = parser.parse_args(argv)

    if args.mine:
        corpus = mine(args.mine, limit=args.limit, stride=args.stride, skip=args.skip,
                      want=args.want, seconds=args.seconds)
        args.receipt.write_text(json.dumps({"rule": __doc__, "entries": corpus}, indent=1) + "\n",
                                encoding="utf-8")
        print(json.dumps({"kept": len(corpus)}))
        return 0
    if args.commits is None:
        parser.error("--commits is required unless --mine is given")
    entries = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = entries.get("entries", entries) if isinstance(entries, dict) else entries
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries if any(entry["commit"].startswith(w) for w in wanted)]
    for entry in entries:
        entry.setdefault("repo_path", str(args.repos_root / entry["repo"]))
    if args.census_only:
        rows = census(entries, args.repos_root)
        args.receipt.write_text(json.dumps({"schema": SCHEMA + "_CENSUS", "authority": AUTHORITY,
                                            "date": "2026-11-19", "rows": rows}, indent=1) + "\n",
                                encoding="utf-8")
        print(json.dumps({"rows": len(rows)}))
        return 0
    result = sweep(entries, receipt=args.receipt, budget=args.budget, cap=args.cap,
                   seconds=args.seconds, grammar=args.grammar)
    print(json.dumps({"rows": len(result["rows"]), "receipt": str(args.receipt)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
