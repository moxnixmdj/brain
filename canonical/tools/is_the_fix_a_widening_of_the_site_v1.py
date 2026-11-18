"""Is the expression being replaced a *piece of* the expression that replaces it?

The enumerator builds expressions bottom-up from atoms. On the first real end-to-end run (click
`1b0e19f505`) that geometry produced eighty candidates in thirty seconds and not one of them was the
fix: `ParameterSource.COMMANDLINE + ParameterSource.COMMANDLINE` comes before
`self.show_envvar and self.envvar is not None`, because free enumeration prices the site's own text the
same as any other atom and the site is not an atom in the pool -- it is a *hole*.

Before paying for a better search, measure the geometry of real fixes, because the geometry decides the
search and nothing else does:

  SITE_SURVIVES_INSIDE_THE_FIX   the old expression is a syntactic subterm of the new one (widening)
  FIX_IS_INSIDE_THE_SITE         the new expression is a syntactic subterm of the old one (narrowing)
  SITE_IS_REPLACED               neither contains the other -- a genuine replacement

If most real fixes keep the site and add to it, then the search that matches reality is *site-rooted*:
enumerate one edit applied to the site's own tree, never a free combination of atoms. That is a smaller
space, it is ordered, and it reaches the fix on the first ring instead of the thousandth.

Measured on the same population as the vocabulary certificate: real commits on real projects, one
source `.py` file, exactly one line removed and one added, no benchmark, no model, no network.
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys
from typing import Any, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import what_a_real_fix_needs_from_the_site_v1 as site_tool  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify_tool  # noqa: E402

SCHEMA = "BRAIN_IS_THE_FIX_A_WIDENING_OF_THE_SITE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

SITE_SURVIVES = "SITE_SURVIVES_INSIDE_THE_FIX"
FIX_INSIDE_SITE = "FIX_IS_INSIDE_THE_SITE"
REPLACED = "SITE_IS_REPLACED"
NO_EXPRESSION = "NO_EXPRESSION_CHANGE"


parse_line = identify_tool.parse_line


def dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def contains(outer: ast.AST, inner: ast.AST) -> bool:
    """Is `inner` a subterm of `outer`? Structural equality, so formatting cannot fake it."""
    if inner is None or outer is None:
        return False
    needle = dump(inner)
    for node in ast.walk(outer):
        if dump(node) == needle:
            return True
    return False


def geometry(old_node: ast.AST, new_node: ast.AST) -> str:
    if contains(new_node, old_node):
        return SITE_SURVIVES
    if contains(old_node, new_node):
        return FIX_INSIDE_SITE
    return REPLACED


def expression_change(change: tuple[tuple, ast.AST, ast.AST]) -> tuple[ast.AST, ast.AST] | None:
    _path, old_node, new_node = change
    if isinstance(old_node, ast.expr) and isinstance(new_node, ast.expr):
        return old_node, new_node
    return None


def rank_in_pool(new_node: ast.AST, pool: list[str]) -> int | None:
    """Where the fix sits in the site-rooted pool. Ordering is what a search can afford; coverage is not."""
    wanted = dump(new_node)
    for index, text in enumerate(pool):
        try:
            if dump(ast.parse(text, mode="eval").body) == wanted:
                return index
        except SyntaxError:
            continue
    return None


def measure(repo: pathlib.Path, limit: int) -> dict[str, Any]:
    counts: collections.Counter[str] = collections.Counter()
    grown: list[int] = []
    shrunk: list[int] = []
    examples: dict[str, list[str]] = collections.defaultdict(list)
    ranks: list[int | None] = []
    added_kinds: collections.Counter[str] = collections.Counter()
    by_geometry: dict[str, list[int | None]] = collections.defaultdict(list)
    examined = 0
    for candidate in site_tool.single_line_candidates(repo, limit):
        examined += 1
        parent = site_tool.file_at(repo, f"{candidate['sha']}^", candidate["path"])
        child = site_tool.file_at(repo, candidate["sha"], candidate["path"])
        if parent is None or child is None:
            continue
        old_text, new_text = candidate["old"].strip(), candidate["new"].strip()
        try:
            old_stmt, new_stmt = parse_line(old_text), parse_line(new_text)
        except SyntaxError:
            counts["LINE_DOES_NOT_PARSE"] += 1
            continue
        changes = site_tool.change_points(old_stmt, new_stmt)
        if len(changes) != 1:
            counts[NO_EXPRESSION] += 1
            continue
        pair = expression_change(changes[0])
        if pair is None:
            counts[NO_EXPRESSION] += 1
            continue
        old_node, new_node = pair
        verdict = geometry(old_node, new_node)
        counts[verdict] += 1
        old_size = site_tool.expression_size(old_node)
        new_size = site_tool.expression_size(new_node)
        if verdict == SITE_SURVIVES:
            grown.append(new_size - old_size)
            # What the widening *added*: the productions the form family has to be able to write.
            for kind in sorted(site_tool.node_kinds(new_node) - site_tool.node_kinds(old_node)):
                added_kinds[kind] += 1
        elif verdict == FIX_INSIDE_SITE:
            shrunk.append(old_size - new_size)
        site_line = site_tool._line_of(parent, old_text)  # noqa: SLF001
        if site_line:
            pool = identify_tool.candidates_at(parent, site_line, ast.unparse(old_node), budget=400)
            rank = rank_in_pool(new_node, pool)
            ranks.append(rank)
            by_geometry[verdict].append(rank)
            if rank is not None and len(examples["REACHED"]) < 8:
                examples["REACHED"].append(f"{candidate['sha'][:10]} rank {rank} "
                                           f"{ast.unparse(new_node)[:60]}")
        if len(examples[verdict]) < 6:
            examples[verdict].append(f"{candidate['sha'][:10]} {ast.unparse(old_node)[:60]} -> {ast.unparse(new_node)[:60]}")
    total = sum(counts.values()) or 1
    return {
        "_ranks": dict(by_geometry),
        "project": repo.name,
        "counts": dict(counts),
        "rates": {k: round(v / total, 4) for k, v in counts.items()},
        "rank": _rank_summary(ranks),
        "added_node_kinds_when_widening": dict(added_kinds.most_common()),
        "rank_by_geometry": {k: _rank_summary(v) for k, v in by_geometry.items()},
        "median_growth_when_widening": _median(grown),
        "median_shrink_when_narrowing": _median(shrunk),
        "examples": {k: v for k, v in examples.items()},
    }


def _merge_kind_counts(projects: list[dict[str, Any]]) -> dict[str, int]:
    merged: collections.Counter[str] = collections.Counter()
    for project in projects:
        merged.update(project.get("added_node_kinds_when_widening") or {})
    return dict(merged.most_common())


def _rank_summary(ranks: list[int | None]) -> dict[str, Any]:
    if not ranks:
        return {"measured": 0}
    reached = [r for r in ranks if r is not None]
    return {
        "measured": len(ranks),
        "in_pool_at_400": len(reached),
        "rate": round(len(reached) / len(ranks), 4),
        "within_10": sum(1 for r in reached if r <= 10),
        "within_40": sum(1 for r in reached if r <= 40),
        "median_rank_when_reached": _median(reached),
        "best": min(reached) if reached else None,
    }


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    roots = sorted(p for p in args.repos.iterdir() if (p / ".git").exists())
    projects = [measure(root, args.limit) for root in roots]
    totals: collections.Counter[str] = collections.Counter()
    for project in projects:
        totals.update(project["counts"])
    all_ranks: list[int | None] = []
    geometry_ranks: dict[str, list[int | None]] = collections.defaultdict(list)
    for project in projects:
        summary = project.pop("_ranks", None)
        if summary:
            for verdict, values in summary.items():
                geometry_ranks[verdict].extend(values)
                all_ranks.extend(values)
    total = sum(totals.values()) or 1
    receipt = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "date": "2026-11-18",
        "population": "commits with exactly one source .py line removed and one added, real projects",
        "projects": projects,
        "totals": dict(totals),
        "rates": {k: round(v / total, 4) for k, v in totals.items()},
        "rank": _rank_summary(all_ranks),
        "rank_by_geometry": {k: _rank_summary(v) for k, v in geometry_ranks.items()},
        "added_node_kinds_when_widening": _merge_kind_counts(projects),
        "reading": ("If SITE_SURVIVES dominates, free enumeration over atoms is the wrong geometry: the "
                    "site is a subterm of its own fix, so the search must be edits applied to the site's "
                    "tree, ordered by distance from it."),
    }
    text = json.dumps(receipt, indent=1, sort_keys=True)
    if args.receipt:
        args.receipt.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
