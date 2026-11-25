"""How often does a real fix recur as a copyable edit? Reproduces the V24 numbers.

Usage: python3 canonical/tools/measure_edit_shape_recurrence_v1.py --repos-dir /tmp/repos [--per-repo 30]

A template store is only worth building if the same template is needed twice. This measures that
directly on real history: for recent commits that change both a non-test module and a test (the shape
a bug-fix PR has), diff at function level, induce templates on each rung, and count

  * how many fixes each rung can express at all,
  * how many distinct full template keys (literals included) those produce,
  * how many keys recur in an independent commit -- the only ones there is anything to accumulate,
  * and, for the recurring keys, whether teaching on one commit actually reproduces another's fix.

Nothing here is asserted; every number printed is computed from git history at run time.
"""
from __future__ import annotations

import argparse
import ast
import collections
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import induced_edit_basis_v1 as basis  # noqa: E402


def git(repo_dir: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True).stdout


def function_pairs(repo_dir: pathlib.Path, sha: str) -> list[tuple[str, str, str]]:
    files = [f for f in git(repo_dir, "show", "--name-only", "--format=", sha, "--", "*.py").split("\n")
             if f.endswith(".py")]
    pairs = []
    for path in files:
        name = pathlib.Path(path).name.lower()
        if "test" in name or "/test" in path:
            continue
        pre = git(repo_dir, "show", f"{sha}^1:{path}")
        post = git(repo_dir, "show", f"{sha}:{path}")
        if not pre.strip() or not post.strip() or pre == post:
            continue
        try:
            before_tree, after_tree = ast.parse(pre), ast.parse(post)
        except SyntaxError:
            continue

        def index(tree: ast.AST) -> dict[str, str]:
            out: dict[str, str] = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.setdefault(node.name, ast.unparse(node))
            return out

        before, after = index(before_tree), index(after_tree)
        for function in sorted(set(before) & set(after)):
            if before[function] != after[function]:
                pairs.append((f"{repo_dir.name}:{sha[:7]}:{path}:{function}",
                              before[function], after[function]))
    return pairs


def rung_templates(pre: str, post: str) -> dict[str, list]:
    """leaf = EditTemplate (leaf pairs); deep = generalized node/insertion NodeTemplates."""
    out: dict[str, list] = {"leaf": [], "deep": []}
    try:
        out["leaf"] = [t for t in basis.induce_templates([("x", pre, post)]) if t.executable]
    except Exception:
        pass
    for inducer in (basis.induce_node_templates, basis.induce_insertion_templates):
        try:
            out["deep"].extend(t for t in inducer([("x", pre, post)], context_depth=0)
                               if t.kind == "RELATIONAL")
        except Exception:
            pass
    return out


def leaf_key(t) -> tuple:
    return t.key()


def deep_key(t) -> tuple:
    return (t.kind, t.mode, t.root_type, t.context, t.old_pattern, t.new_pattern)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-dir", default="/tmp/repos")
    parser.add_argument("--per-repo", type=int, default=30)
    parser.add_argument("--repos", default="pluggy,werkzeug,more-itertools,pyjwt,click,attrs")
    args = parser.parse_args()

    results = {"leaf": _measure(args, "leaf"), "deep": _measure(args, "deep")}
    for rung, data in results.items():
        print(f"\n[{rung}] fixes={data['fixes']} expressible={data['expressible']} "
              f"({data['expressible'] / max(data['fixes'], 1):.1%})")
        print(f"[{rung}] distinct full keys={data['keys']} recurring>=2 commits={data['recurring']} "
              f"(within one repo={data['same_repo']})")
        print(f"[{rung}] occurrences under a recurring key={data['covered_occurrences']} / {data['occurrences']}")
        print(f"[{rung}] transfer: recovered {data['transfer_hits']}/{data['transfer_tested']}")
        for line in data["transfer_lines"]:
            print("   " + line)
    return 0


def _measure(args, rung: str) -> dict:
    key_commits: dict[tuple, set] = collections.defaultdict(set)
    key_examples: dict[tuple, list] = collections.defaultdict(list)
    fixes = expressible = occurrences = 0
    transfer_tested = transfer_hits = 0
    transfer_lines: list[str] = []

    for repo in [r.strip() for r in args.repos.split(",") if r.strip()]:
        repo_dir = pathlib.Path(args.repos_dir) / repo
        if not (repo_dir / ".git").exists():
            continue
        shas = git(repo_dir, "log", "--no-merges", "-n", str(args.per_repo * 8),
                   "--format=%H", "--", "*.py").split()
        taken = 0
        for sha in shas:
            files = [f for f in git(repo_dir, "show", "--name-only", "--format=", sha, "--", "*.py").split("\n")
                     if f.endswith(".py")]
            if not any("test" in f for f in files):
                continue
            try:
                pairs = function_pairs(repo_dir, sha)
            except Exception:
                continue
            if not pairs:
                continue
            taken += 1
            for pair in pairs:
                fixes += 1
                templates = rung_templates(pair[1], pair[2])[rung]
                expressible += bool(templates)
                for template in templates:
                    key = (leaf_key if rung == "leaf" else deep_key)(template)
                    key_commits[key].add((repo, sha))
                    key_examples[key].append(pair)
                    occurrences += 1
            if taken >= args.per_repo:
                break

    recurring = [k for k in key_commits if len(key_commits[k]) >= 2]
    same_repo = [k for k in recurring
                 if len({r for r, _s in key_commits[k]}) < len(key_commits[k])]
    for key in sorted(recurring, key=lambda k: -len(key_commits[k]))[:10]:
        examples = key_examples[key]
        if len(examples) < 2:
            continue
        teacher, student = examples[0], examples[1]
        templates = basis.induce_node_templates([("t", teacher[1], teacher[2])], context_depth=0) + \
                    basis.induce_insertion_templates([("t", teacher[1], teacher[2])], context_depth=0)
        transfer_tested += 1
        try:
            candidates = basis.candidates_from_node_templates(student[1], templates)
        except Exception:
            candidates = []
        want = ast.dump(ast.parse(student[2]))
        hit = any(ast.dump(ast.parse(c["source"])) == want for c in candidates)
        transfer_hits += hit
        transfer_lines.append(f"{len(key_commits[key]):2d} commits cands={len(candidates):3d} "
                              f"{'RECOVERED' if hit else '-':9s} {student[0]}")

    return {"fixes": fixes, "expressible": expressible, "keys": len(key_commits),
            "recurring": len(recurring), "same_repo": len(same_repo),
            "occurrences": occurrences,
            "covered_occurrences": sum(len(key_examples[k]) for k in recurring),
            "transfer_tested": transfer_tested, "transfer_hits": transfer_hits,
            "transfer_lines": transfer_lines}


if __name__ == "__main__":
    raise SystemExit(main())
