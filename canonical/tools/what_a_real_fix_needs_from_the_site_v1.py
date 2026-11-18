"""Of the fixes real people actually wrote, how many could a site's own material build?

Everything in this tree has been measured on a corpus of 40 known bugs. That is self-congratulation,
and the number that decides whether the whole family is worth anything has never been measured: **of
real fixes in real projects, what fraction is a single expression replacement at a single site, and of
those, what fraction needs something the site does not already contain?**

The last build found expressiveness -- not evidence, not memory, not speed -- to be the first
obstacle: one bug lost every candidate because the fix was not in the pool. This measures that
obstacle at scale, on real code, from real commit history, with no benchmark harness, no model, and no
network at run time.

Population: commits on real Python projects whose message claims a fix, touching one Python file with
a small diff -- the population a single-site repair can even address. For every changed expression:

  IN_VOCABULARY        every free name is already in scope at that site, and the expression is small
  NEEDS_NEW_NAME       the fix uses a name the site does not have (an import, a new local, a callee)
  TOO_LARGE            the expression exceeds the enumerator's node budget
  NOT_SINGLE_EXPRESSION the change is a new statement, a control-flow change, or several edits

Reported per project and in total, with the missing names ranked. This is the vocabulary-insufficiency
certificate, on real code, in the only form that can be acted on: exactly what is missing, and how
often.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import collections
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

from expressions_from_a_site_v1 import MAX_NODES  # noqa: E402

SCHEMA = "BRAIN_WHAT_A_REAL_FIX_NEEDS_FROM_THE_SITE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

IN_VOCABULARY = "IN_VOCABULARY"
NEEDS_NEW_NAME = "NEEDS_NEW_NAME"
TOO_LARGE = "TOO_LARGE"
NOT_SINGLE_EXPRESSION = "NOT_SINGLE_EXPRESSION"

FIX_WORDS = re.compile(r"\b(fix|fixes|fixed|bug|bugs|repair|broken|crash|crashing|regression|"
                       r"incorrect|wrong)\b", re.I)
MAX_CHANGED_LINES = 6


def commits(repo: pathlib.Path, limit: int) -> Iterator[tuple[str, str]]:
    done = subprocess.run(["git", "-C", str(repo), "log", "--no-merges", "--format=%H%x09%s",
                           "-n", str(limit)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in done.stdout.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        if FIX_WORDS.search(subject):
            yield sha, subject


def changed_files(repo: pathlib.Path, sha: str) -> list[str]:
    done = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", sha],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line.strip() for line in done.stdout.splitlines() if line.strip().endswith(".py")]


def file_at(repo: pathlib.Path, sha: str, path: str) -> str | None:
    done = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.stdout if done.returncode == 0 else None


def changed_pairs(repo: pathlib.Path, sha: str, path: str) -> list[tuple[str, str]]:
    """The removed/added line pairs of one file in one commit, from a zero-context diff."""
    done = subprocess.run(["git", "-C", str(repo), "show", "--unified=0", "--format=", sha, "--", path],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    removed: list[str] = []
    added: list[str] = []
    pairs: list[tuple[str, str]] = []
    for line in done.stdout.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
        else:
            if removed or added:
                pairs.extend(zip(removed, added) if (removed and added) else [])
                removed, added = [], []
    if removed or added:
        pairs.extend(zip(removed, added) if (removed and added) else [])
    return pairs


def paths_of(tree: ast.AST) -> dict[tuple, ast.AST]:
    out: dict[tuple, ast.AST] = {}

    def walk(node: ast.AST, path: tuple) -> None:
        out[path] = node
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        walk(child, path + ((field, index),))
            elif isinstance(value, ast.AST):
                walk(value, path + ((field, None),))

    walk(tree, ())
    return out


def single_change(old: ast.AST, new: ast.AST) -> tuple[ast.expr, ast.expr] | None:
    """Exactly one subtree differs, and it differs in an expression: old -> new."""
    old_paths = paths_of(old)
    new_paths = paths_of(new)
    common = set(old_paths) & set(new_paths)
    differing = [p for p in common
                 if ast.dump(old_paths[p], annotate_fields=False)
                 != ast.dump(new_paths[p], annotate_fields=False)]
    if not differing:
        return None
    # The change point is the DEEPEST differing node: every ancestor of a changed node differs too
    # (its dump contains the change), so the shallowest differing node is always the module. Choosing
    # that one classified every real edit as "not a single expression", which is how this measurement
    # first reported 100% NOT_SINGLE_EXPRESSION over 242 real edits.
    deepest = max(differing, key=len)
    if any(path != deepest and deepest[:len(path)] != path for path in differing):
        return None  # two independent differences: not one edit
    old_node, new_node = old_paths[deepest], new_paths[deepest]
    if not (isinstance(old_node, ast.expr) and isinstance(new_node, ast.expr)):
        return None
    return old_node, new_node


def names_in_scope(source: str, line: int) -> set[str]:
    """Everything a site may legally name: imports, module globals, parameters, and locals above it."""
    scope: set[str] = set(dir(builtins))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return scope
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                scope.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                scope.update(flat_target_names(target))
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            scope.update(flat_target_names(node.target))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line <= getattr(node, "end_lineno", node.lineno):
                scope.update(a.arg for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs)
                if node.args.vararg:
                    scope.add(node.args.vararg.arg)
                if node.args.kwarg:
                    scope.add(node.args.kwarg.arg)
                for inner in ast.walk(node):
                    target_line = getattr(inner, "lineno", 0) or 0
                    if target_line >= line:
                        continue
                    if isinstance(inner, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For,
                                          ast.With, ast.comprehension, ast.NamedExpr)):
                        for target in ast.walk(inner):
                            if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                                scope.add(target.id)
                            elif isinstance(target, ast.arg):
                                scope.add(target.arg)
                    elif isinstance(inner, (ast.Import, ast.ImportFrom)):
                        for alias in inner.names:
                            scope.add((alias.asname or alias.name).split(".")[0])
    return scope


def flat_target_names(target: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}


def free_names(expression: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(expression)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def expression_size(expression: ast.expr) -> int:
    return sum(1 for node in ast.walk(expression) if isinstance(node, ast.expr))


def classify(repo: pathlib.Path, sha: str, path: str) -> dict[str, Any] | None:
    parent = file_at(repo, f"{sha}^", path)
    child = file_at(repo, sha, path)
    if parent is None or child is None:
        return None
    pairs = changed_pairs(repo, sha, path)
    if not pairs or len(pairs) > MAX_CHANGED_LINES:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "DIFF_TOO_LARGE_OR_EMPTY",
                "changed_pairs": len(pairs)}
    if len(pairs) > 1:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "SEVERAL_LINES_CHANGED",
                "changed_pairs": len(pairs)}
    old_line, new_line = pairs[0]
    try:
        old_stmt = ast.parse(old_line.strip())
        new_stmt = ast.parse(new_line.strip())
    except SyntaxError:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "LINE_DOES_NOT_PARSE",
                "old": old_line.strip()[:120], "new": new_line.strip()[:120]}
    change = single_change(old_stmt, new_stmt)
    if change is None:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "NOT_ONE_SUBTREE",
                "old": old_line.strip()[:120], "new": new_line.strip()[:120]}
    _old_expr, new_expr = change
    line = _line_of(parent, old_line.strip())
    scope = names_in_scope(parent, line)
    missing = sorted(free_names(new_expr) - scope)
    size = expression_size(new_expr)
    verdict: dict[str, Any] = {"size": size, "new": ast.unparse(new_expr)[:160]}
    if size > MAX_NODES:
        verdict.update({"kind": TOO_LARGE})
    elif missing:
        verdict.update({"kind": NEEDS_NEW_NAME, "missing": missing})
    else:
        verdict.update({"kind": IN_VOCABULARY})
    return verdict


def _line_of(source: str, needle: str) -> int:
    for index, line in enumerate(source.splitlines(), start=1):
        if line.strip() == needle:
            return index
    return 1


def single_line_candidates(repo: pathlib.Path, limit: int) -> Iterator[dict[str, Any]]:
    """Every commit in the history whose whole diff for one .py file is ONE removed and ONE added line.

    This is the population a single-site replacement can even address, so it is the population the
    question is about. It is found in one streaming pass over the log rather than one subprocess per
    commit, because the classification is cheap and the subprocesses are not.
    """
    done = subprocess.run(["git", "-C", str(repo), "log", "-p", "--unified=0", "--no-merges",
                           "--format=%x01%H%x09%s", "-n", str(limit)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    sha = subject = None
    files: list[str] = []
    removed: list[str] = []
    added: list[str] = []
    current_file: str | None = None

    def flush() -> dict[str, Any] | None:
        if sha and len(files) == 1 and len(removed) == 1 and len(added) == 1:
            return {"sha": sha, "subject": subject or "", "path": files[0],
                    "old": removed[0], "new": added[0]}
        return None

    for line in done.stdout.splitlines():
        if line.startswith("\x01"):
            ready = flush()
            if ready:
                yield ready
            sha, _, subject = line[1:].partition("\t")
            files, removed, added = [], [], []
            current_file = None
            continue
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file.endswith(".py"):
                files.append(current_file)
            continue
        if line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("-") and current_file and current_file.endswith(".py"):
            removed.append(line[1:])
        elif line.startswith("+") and current_file and current_file.endswith(".py"):
            added.append(line[1:])
    ready = flush()
    if ready:
        yield ready


def classify_line(repo: pathlib.Path, candidate: dict[str, Any]) -> dict[str, Any] | None:
    parent = file_at(repo, f"{candidate['sha']}^", candidate["path"])
    if parent is None:
        return None
    old_line, new_line = candidate["old"], candidate["new"]
    try:
        old_stmt = ast.parse(old_line.strip())
        new_stmt = ast.parse(new_line.strip())
    except SyntaxError:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "LINE_DOES_NOT_PARSE"}
    change = single_change(old_stmt, new_stmt)
    if change is None:
        return {"kind": NOT_SINGLE_EXPRESSION, "reason": "NOT_ONE_SUBTREE"}
    _old_expr, new_expr = change
    line = _line_of(parent, old_line.strip())
    scope = names_in_scope(parent, line)
    missing = sorted(free_names(new_expr) - scope)
    size = expression_size(new_expr)
    verdict: dict[str, Any] = {"size": size, "new": ast.unparse(new_expr)[:160],
                               "old": ast.unparse(_old_expr)[:160]}
    if size > MAX_NODES:
        verdict["kind"] = TOO_LARGE
    elif missing:
        verdict["kind"] = NEEDS_NEW_NAME
        verdict["missing"] = missing
    else:
        verdict["kind"] = IN_VOCABULARY
    return verdict


def sweep(root: pathlib.Path, limit: int = 4000) -> dict[str, Any]:
    projects: list[dict[str, Any]] = []
    totals: collections.Counter[str] = collections.Counter()
    missing_names: collections.Counter[str] = collections.Counter()
    examples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    evaluated = 0
    skipped = 0
    reasons: collections.Counter[str] = collections.Counter()
    for repo in sorted(p for p in root.iterdir() if (p / ".git").exists()):
        counts: collections.Counter[str] = collections.Counter()
        for candidate in single_line_candidates(repo, limit):
            verdict = classify_line(repo, candidate)
            if verdict is None:
                skipped += 1  # the parent version of the file is absent (new file, or shallow clone)
                continue
            evaluated += 1
            counts[verdict["kind"]] += 1
            totals[verdict["kind"]] += 1
            for name in verdict.get("missing", []):
                missing_names[name] += 1
            reasons[str(verdict.get("reason"))] += 1
            if len(examples[verdict["kind"]]) < 5:
                examples[verdict["kind"]].append({
                    "project": repo.name, "commit": candidate["sha"][:10],
                    "subject": candidate["subject"][:80], "file": candidate["path"],
                    "old": verdict.get("old"), "new": verdict.get("new"),
                    "missing": verdict.get("missing"), "reason": verdict.get("reason"),
                    "old_line": candidate["old"][:120], "new_line": candidate["new"][:120]})
        projects.append({"project": repo.name, "counts": dict(counts)})
    total = sum(totals.values())
    return {"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-18",
            "projects": projects, "totals": dict(totals), "single_line_edits_examined": total,
            "skipped_no_parent_version": skipped,
            "what_in_vocabulary_means": (
                'A NECESSARY condition, not sufficiency: every free name of the new expression is in '
                'scope at the site in the parent version, the expression is within the enumerator '
                'node budget, and exactly one expression subtree changed. Reachability also needs the '
                'grammar to generate that form, which the enumerator covers for the operators, '
                'subscripts, attributes and calls it implements; this measurement does not execute '
                'the site, so it cannot confirm generation for a specific case.'),
            "rates": {k: round(v / total, 4) for k, v in totals.items()} if total else {},
            "missing_names_rank": missing_names.most_common(25),
            "not_single_expression_reasons": reasons.most_common(10),
            "examples": {k: v for k, v in examples.items()}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    receipt = sweep(args.repos, limit=args.limit)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"single_line_edits_examined": receipt["single_line_edits_examined"],
                      "totals": receipt["totals"], "rates": receipt["rates"]}, indent=1))
    for name, count in receipt["missing_names_rank"][:10]:
        print(f"    missing  {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
