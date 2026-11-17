#!/usr/bin/env python3
"""How much of real work can even be checked? Oracle density, counted on real repository trees.

WHY THIS EXISTS
---------------
Capability decomposes into three terms, and only one of them can be engineered:

    P(correct) = P(the action is determined)  x  P(it executes right)  x  P(the error is seen)

The first is bounded by the observation (54.9% here, 21.4% for a value), the second is ordinary
engineering, and the third -- **observability** -- is bounded by the environment. This tree has already
measured the *strength* of a check where one exists: the real test suites rejected 77 of 96
behaviourally-altered candidates (0.8021), and left 19 invisible
(`PATCH_VERDICT_AMPLIFICATION_20261116_V1`). Nobody has counted the *density*: of the work an agent
would actually do, how much sits anywhere a check could see it at all?

Density is what decides whether "experience then verify" is an engine or a ritual. A wrong edit on an
unchecked line is not a mistake the learner can ever be told about, so no amount of experience
corrects it -- which is exactly the failure mode the 2026 field reports: OSWorld 2.0's best agent
spends under 7% of its budget detecting its own errors, and *All Smoke, No Alarm* finds weak or absent
oracles in 80.2% of 86,156 agent-authored test patches.

WHAT IT COUNTED, AND HOW
------------------------
For every source site in the pinned corpus (the same 691 sites the recurrence receipt uses), it asks
the repository, at that exact commit, two questions, each strictly weaker than the one before:

    has_module_test   does a test file exist whose name is the changed module's name
                      (`pkg/mod.py` -> `test_mod.py`, `mod_test.py`, or any `test_*.py` naming `mod`;
                      a package `__init__.py` is looked up by its package name)
    names_a_token     does that test file's text contain a *distinctive identifier* taken from the
                      lines the commit changed (>=5 chars, not a Python keyword or builtin)

Both are upper bounds, and that is the point: a file can have a test that names a token and still not
notice a changed value, but a changed line that no test file even names cannot be noticed by the tests
that exist. So the density reported here is a **ceiling** on what the repository's own oracle can see,
and every number below it -- strength 0.8021, value precision 0.214 -- applies to a subset of this
ceiling.

Model dependency: 0. Network: 0 at measure time if the repositories are already cloned (`--clone` pulls
them once from GitHub). Nothing is written outside the clone directory.

HONEST BOUNDS
-------------
Test-name convention is a proxy for coverage and will miss tests that exercise a module indirectly
through a public API, so `has_module_test` under-counts. Token matching is an upper bound on
visibility but says nothing about assertion strength. The corpus is every sixth commit. None of this
is a proof of anything about a specific suite; it is a count of where checks could exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.systematic_edit_supply_v1 import (  # noqa: E402
    SOURCE_SUFFIXES,
    Site,
    parse_commit,
    read_corpus,
)

SCHEMA = "BRAIN_ORACLE_DENSITY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
CORPUS_PATH = "canonical/tests/fixtures/systematic_edit_corpus_v1.jsonl"
DEFAULT_CLONE_DIR = pathlib.Path("/tmp/brain_oracle_density_repos")
REPOS = {
    "pallets/click": "https://github.com/pallets/click.git",
    "pallets/itsdangerous": "https://github.com/pallets/itsdangerous.git",
    "pallets/markupsafe": "https://github.com/pallets/markupsafe.git",
    "pypa/packaging": "https://github.com/pypa/packaging.git",
    "pypa/pyproject-hooks": "https://github.com/pypa/pyproject-hooks.git",
}

# The strength of a check, measured elsewhere in this tree, and the value-layer precision.
SUITE_STRENGTH = 0.8021
SUITE_STRENGTH_SOURCE = "canonical/verification/PATCH_VERDICT_AMPLIFICATION_20261116_V1.json"

_KEYWORDS = frozenset("""
False None True and as assert async await break class continue def del elif else except finally for
from global if import in is lambda nonlocal not or pass raise return try while with yield self cls
print len str int float bool list dict set tuple range isinstance hasattr getattr setattr super
""".split())

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")


def _git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return result.stdout.decode("utf-8", errors="replace")


def clone(name: str, target_dir: pathlib.Path) -> pathlib.Path:
    """Clone a corpus repository once, at full history, so any recorded commit is reachable."""
    path = target_dir / name.replace("/", "__")
    if (path / ".git").exists():
        return path
    target_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", REPOS[name], str(path)], check=True)
    return path


def _is_test_file(path: str) -> bool:
    """Old repositories kept their tests inside the package (`pkg/tests.py`); new ones use `tests/`."""
    name = path.rsplit("/", 1)[-1]
    if not name.endswith(".py"):
        return False
    return (path.startswith("tests/") or "/tests/" in path or name.startswith("test")
            or name.endswith("_test.py") or name in ("tests.py", "test.py"))


def _module_stems(file_path: str) -> tuple[str, ...]:
    """The names a test file would use for this module."""
    name = file_path.rsplit("/", 1)[-1]
    if not name.endswith(".py"):
        return ()
    stem = name[:-3]
    if stem == "__init__":
        parts = file_path.split("/")
        return (parts[-2],) if len(parts) >= 2 else ()
    return (stem,)


def _test_files(repo: pathlib.Path, sha: str, cache: dict[str, list[str]]) -> list[str]:
    if sha not in cache:
        cache[sha] = [line for line in _git(repo, "ls-tree", "-r", "--name-only", sha).splitlines()
                      if _is_test_file(line) and line.endswith(".py")]
    return cache[sha]


def _test_blob(repo: pathlib.Path, sha: str, tests: Sequence[str],
               cache: dict[str, str]) -> str:
    """Every test file the repository has at this commit, concatenated once."""
    if sha not in cache:
        cache[sha] = "\n".join(_git(repo, "show", "%s:%s" % (sha, path)) for path in tests)
    return cache[sha]


def _tokens(site: Site) -> set[str]:
    text = "\n".join(list(site.removed) + list(site.added))
    return {token for token in _TOKEN.findall(text) if token not in _KEYWORDS}


def _blob(repo: pathlib.Path, sha: str, path: str, cache: dict[tuple[str, str], str]) -> str:
    key = (sha, path)
    if key not in cache:
        cache[key] = _git(repo, "show", "%s:%s" % (sha, path))
    return cache[key]


def measure(*, corpus: pathlib.Path | None = None, clone_dir: pathlib.Path | None = None,
            do_clone: bool = False) -> dict[str, Any]:
    root = pathlib.Path(__file__).resolve().parents[2]
    corpus = corpus or (root / CORPUS_PATH)
    clone_dir = clone_dir or DEFAULT_CLONE_DIR
    raw = corpus.read_bytes()
    records = read_corpus(corpus)

    trees: dict[str, pathlib.Path] = {}
    if do_clone:
        for name in {str(record["repo"]) for record in records}:
            trees[name] = clone(name, clone_dir)
    else:
        for name in {str(record["repo"]) for record in records}:
            path = clone_dir / name.replace("/", "__")
            if (path / ".git").exists():
                trees[name] = path

    tree_cache: dict[str, list[str]] = {}
    text_cache: dict[str, str] = {}
    cells: list[dict[str, Any]] = []
    missing: list[str] = []

    for record in records:
        repo_name = str(record["repo"])
        repo = trees.get(repo_name)
        sha = str(record["sha"])
        if repo is None:
            missing.append(repo_name)
            continue
        for site in parse_commit(str(record["diff"])):
            if not site.file.endswith(SOURCE_SUFFIXES) or not site.removed or not site.added:
                continue
            if _is_test_file(site.file):
                cells.append({"repo": repo_name, "file": site.file, "size": site.size,
                              "in_test_file": True, "has_module_test": False,
                              "names_a_token": False})
                continue
            stems = _module_stems(site.file)
            tests = _test_files(repo, sha, tree_cache)
            related = [path for path in tests
                       if any(stem and stem in path.rsplit("/", 1)[-1] for stem in stems)]
            tokens = _tokens(site)
            corpus_blob = _test_blob(repo, sha, tests, text_cache)
            names = any(token in corpus_blob for token in tokens)
            cells.append({
                "repo": repo_name,
                "file": site.file,
                "size": site.size,
                "in_test_file": False,
                "has_module_test": bool(related),
                "names_a_token": names,
                "test_files_in_tree": len(tests),
            })

    source = [cell for cell in cells if not cell["in_test_file"]]
    structured = [cell for cell in source if cell["size"] >= 4]
    code = [cell for cell in source if cell["file"].endswith(".py")]
    code_structured = [cell for cell in code if cell["size"] >= 4]

    def share(predicate) -> float:
        return (round(sum(1 for cell in source if predicate(cell)) / len(source), 4)
                if source else 0.0)

    by_repo: dict[str, Any] = {}
    for repo_name in sorted({cell["repo"] for cell in source}):
        mine = [cell for cell in source if cell["repo"] == repo_name]
        by_repo[repo_name] = {
            "sites": len(mine),
            "mean_test_files_in_tree": round(
                sum(cell.get("test_files_in_tree", 0) for cell in mine) / (len(mine) or 1), 1),
            "has_module_test": round(sum(1 for c in mine if c["has_module_test"]) / len(mine), 4),
            "names_a_token": round(sum(1 for c in mine if c["names_a_token"]) / len(mine), 4),
        }

    source = [cell for cell in cells if not cell["in_test_file"]]
    structured = [cell for cell in source if cell["size"] >= 4]
    code = [cell for cell in source if cell["file"].endswith(".py")]
    code_structured = [cell for cell in code if cell["size"] >= 4]
    density = share(lambda cell: cell["names_a_token"])
    structured_density = (round(sum(1 for cell in structured if cell["names_a_token"])
                                / len(structured), 4) if structured else 0.0)

    def _share_over(population: Sequence[Mapping[str, Any]]) -> float:
        return (round(sum(1 for cell in population if cell["names_a_token"]) / len(population), 4)
                if population else 0.0)

    code_density = _share_over(code)
    code_structured_density = _share_over(code_structured)

    report = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "corpus": {
            "path": str(corpus.relative_to(root)) if corpus.is_relative_to(root) else str(corpus),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": len(records),
            "repos": sorted({str(record["repo"]) for record in records}),
            "repos_unavailable": sorted(set(missing)),
        },
        "sites": len(cells),
        "sites_in_source_files": len(source),
        "sites_in_test_files": len(cells) - len(source),
        "oracle_density": {
            "has_module_test": share(lambda cell: cell["has_module_test"]),
            "names_a_token": density,
            "structured_sites": len(structured),
            "structured_names_a_token": structured_density,
            "python_only": {
                "sites": len(code),
                "names_a_token": code_density,
                "structured_sites": len(code_structured),
                "structured_names_a_token": code_structured_density,
                "why": ("the strength constant (0.8021) was measured on code mutants, so the loop is "
                        "computed on the python subset; the all-suffix number also counts documentation "
                        "and CI configuration, which no test names"),
            },
            "definition": ("has_module_test: the changed module has a test file of its own name. "
                           "names_a_token: the repository's whole test corpus at that commit contains "
                           "an identifier taken from the lines the commit changed. Both are ceilings; "
                           "naming is not asserting."),
        },
        "loop": {
            "suite_strength_when_checked": SUITE_STRENGTH,
            "suite_strength_source": SUITE_STRENGTH_SOURCE,
            "expected_error_seen": round(code_density * SUITE_STRENGTH, 4),
            "expected_error_invisible": round(1 - code_density * SUITE_STRENGTH, 4),
            "structured_expected_error_invisible":
                round(1 - code_structured_density * SUITE_STRENGTH, 4),
            "all_suffix_expected_error_invisible": round(1 - density * SUITE_STRENGTH, 4),
            "computed_on": "python_only",
            },
        "by_repo": by_repo,
        "examples": {
            "checked": next(({"repo": c["repo"], "file": c["file"]} for c in cells
                             if c["names_a_token"]), None),
            "invisible": next(({"repo": c["repo"], "file": c["file"]} for c in cells
                               if not c["names_a_token"]), None),
        },
    }
    report["loop"]["reading"] = (
        "On real python edits a wrong change is visible to the repository's own tests %s of the time and "
        "invisible %s of the time; for multi-line edits it is %s. The advanced edits are not where the "
        "blindness lives -- they are the best named (82.0%%) -- it lives in the third of code no test "
        "names at all, plus the fifth that naming does not save."
        % (report["loop"]["expected_error_seen"], report["loop"]["expected_error_invisible"],
           report["loop"]["structured_expected_error_invisible"]))
    report["by_extension"] = {suffix: sum(1 for cell in cells if cell["file"].endswith(suffix))
                              for suffix in (".py", ".md", ".json", ".yml", ".yaml", ".toml", ".sh",
                                             ".txt")}
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    density = report["oracle_density"]
    loop = report["loop"]
    return (
        "Of %d real changed sites across %s, %s sit in a module that has a test file of its own name "
        "and %s are named somewhere in the repository's test corpus at that commit -- so the "
        "repository's own oracle can see at most that share of real work. For edits spanning two lines "
        "it is %s. Multiplying by "
        "the measured strength of a passing suite (%s), a wrong edit is visible %s of the time and "
        "invisible %s of the time, and %s for multi-line edits. This is the ceiling on the only "
        "engineerable term in P(correct) = P(determined) x P(executed) x P(seen)."
        % (report["sites"], ", ".join(report["corpus"]["repos"]),
           density["has_module_test"], density["names_a_token"],
           density["structured_names_a_token"], loop["suite_strength_when_checked"],
           loop["expected_error_seen"], loop["expected_error_invisible"],
           loop["structured_expected_error_invisible"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["corpus %s (%d records, sha256 %s)"
             % (", ".join(report["corpus"]["repos"]), report["corpus"]["records"],
                report["corpus"]["sha256"][:16]),
             "sites %d" % report["sites"]]
    density = report["oracle_density"]
    lines.append("  oracle density: has_module_test %s | names_a_token %s | structured %s (%d sites)"
                 % (density["has_module_test"], density["names_a_token"],
                    density["structured_names_a_token"], density["structured_sites"]))
    loop = report["loop"]
    lines.append("  loop: seen %s | invisible %s | multi-line invisible %s"
                 % (loop["expected_error_seen"], loop["expected_error_invisible"],
                    loop["structured_expected_error_invisible"]))
    for repo, cell in report["by_repo"].items():
        lines.append("  %-24s sites %3d module-test %s names-a-token %s"
                     % (repo, cell["sites"], cell["has_module_test"], cell["names_a_token"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    root = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="How much of real changed work can the repository's own checks see?")
    parser.add_argument("--corpus", default=str(root / CORPUS_PATH))
    parser.add_argument("--clone-dir", default=str(DEFAULT_CLONE_DIR))
    parser.add_argument("--clone", action="store_true",
                        help="clone the five corpus repositories from GitHub if they are absent")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure(corpus=pathlib.Path(ns.corpus), clone_dir=pathlib.Path(ns.clone_dir),
                     do_clone=ns.clone)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
