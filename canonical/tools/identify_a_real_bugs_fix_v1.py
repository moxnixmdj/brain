"""Repair a real bug in a real repository, verified by that repository's own tests.

Everything this tree has measured so far has been QuixBugs -- 40 known bugs -- or a static
classification of real edits. This runs the actual loop on real code:

  1. take a real fix commit that changed ONE line of source and touched a test file;
  2. check out the PARENT commit and copy in the POST-FIX tests, so the project's own suite fails on
     the parent -- the ordinary, honest construction of an oracle (the tests are the project's, not
     mine, and they were written by the person who fixed the bug);
  3. enumerate the expressions the site's own material can build;
  4. for every candidate, patch the file and run the test file once -- one row of a behaviour table
     across all the tests in it;
  5. select the next test that splits the survivors hardest until one is left, then check that survivor
     against the tests it was never chosen by.

Nothing is stored. The pool is the site's own material plus the attributes the object already uses.
No model, no network at run time, no synthetic data: the oracle is someone else's real test suite.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import what_a_real_fix_needs_from_the_site_v1 as needs  # noqa: E402
from expressions_from_a_site_v1 import MAX_NODES, _combinations  # noqa: E402

SCHEMA = "BRAIN_IDENTIFY_A_REAL_BUGS_FIX_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# pytest -v prints `path::test VERDICT [ pct]`; its summary prints `VERDICT path::test - reason`. Both.
# A test that did not run is not a test that failed. `SKIPPED` is what pytest prints for a test that
# declined to execute, and reading it as a failure made four attrs rows and several jinja rows look like
# they had an oracle when the "failing" test was one that had skipped itself.
NOT_A_FAILURE = frozenset({"PASSED", "SKIPPED", "XFAIL", "XPASS"})
FAILURE_VERDICTS = frozenset({"FAILED", "ERROR"})

# `\S+` for a node id is wrong: pytest ids are arbitrary and routinely contain spaces, e.g.
# `test_help_spec[True-param_decls2-kwargs2---color / --no-color]`. Truncating at the space produced a
# node id that ran nothing, which read as "the run changed" rather than "the id was wrong". Anchor the
# status at the end of the line instead and let the id be whatever is in front of it.
VERDICT_AFTER = re.compile(r"^(\S.*?::.+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)"
                           r"(?:\s+\[\s*\d+%\])?\s*$")
VERDICT_BEFORE = re.compile(r"^(FAILED|PASSED|ERROR)\s+(\S+)")


def git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return done.stdout


def show(repo: pathlib.Path, sha: str, path: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return done.stdout


def test_command(worktree: pathlib.Path, test_file: str) -> list[str]:
    # `-o asyncio_default_fixture_loop_scope=function` is not cosmetic: tqdm sets
    # `filterwarnings = error`, and pytest-asyncio's unset-scope warning then escalates to
    # INTERNALERROR, so the suite cannot run at all and every tqdm row reads as "no oracle".
    return [sys.executable, "-m", "pytest", test_file, "-v", "--tb=no", "-p", "no:cacheprovider",
            "-o", "asyncio_default_fixture_loop_scope=function"]


def failing_tests(verdicts: dict[str, str]) -> list[str]:
    """The tests that actually failed, in file order. Skips and timeouts are not failures."""
    return [name for name, verdict in verdicts.items() if verdict in FAILURE_VERDICTS]


def fresh_bytecode(worktree: pathlib.Path) -> dict[str, str]:
    """No bytecode, in either direction, for any run of the oracle.

    CPython validates a cached `.pyc` against the source's mtime **and** size, and the mtime is stored as
    whole seconds. A repair that swaps a value for a name of the same length, written inside the same
    second as the previous candidate, is therefore invisible to the import system: python loads the
    bytecode of the *previous* file and the candidate is scored on a run it never had. Measured on a
    one-line fixture: 4 of 8 explorations reported FAILED for an expression that passes, with the
    corrected file on disk and `assert 3 == 4` in the traceback -- `x + x` had been scored as `x + 1`.

    An oracle that can lie in either direction is not an oracle: the same mask turns a failing
    candidate into a verified one whenever a passing candidate of the same size ran first. So every run
    deletes the caches and writes none.
    """
    for cache in worktree.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    return {"PYTHONPATH": "src:.", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(worktree / ".brain_pycache")}


def run_tests_full(worktree: pathlib.Path, test_file: str, seconds: int = 60,
                   extra_env: dict[str, str] | None = None) -> tuple[dict[str, str], str]:
    """The verdicts AND what pytest said, because an empty verdict map is not a passing suite.

    A collection error (a missing dependency, a broken conftest) produces no PASSED/FAILED lines at all.
    Reporting that as NO_ORACLE says "the project's tests pass on the parent", which is a claim about the
    project. It was false for every `requests` and `httpx` commit in the first sweep: their conftests
    import `urllib3`, which was not installed, and the run was over in half a second.
    """
    try:
        done = subprocess.run(test_command(worktree, test_file), cwd=worktree, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ, **fresh_bytecode(worktree),
                                   **(extra_env or {})})
    except subprocess.TimeoutExpired:
        return {"<timed out>": "TIMEOUT"}, "TIMEOUT"
    outcomes: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        stripped = line.strip()
        after = VERDICT_AFTER.match(stripped)
        if after:
            outcomes[after.group(1)] = after.group(2)
            continue
        before = VERDICT_BEFORE.match(stripped)
        if before:
            outcomes.setdefault(before.group(2), before.group(1))
    return outcomes, ((done.stdout or "") + (done.stderr or ""))[-2500:]


def run_tests(worktree: pathlib.Path, test_file: str, seconds: int = 60) -> dict[str, str]:
    """One test file, one verdict per test, and a hard stop.

    stdin is closed: a candidate expression that makes a prompt fire would otherwise sit on a read
    forever, and a hang is not a measurement. A timed-out run is recorded as TIMEOUT, which nothing can
    survive.
    """
    return run_tests_full(worktree, test_file, seconds)[0]


def span_of(source: str, line: int, node: ast.AST) -> tuple[int, int] | None:
    """The real column span of `node` on `line`, taken from the full parse of the parent file.

    Not from the standalone line: the standalone parse rewrites `elif` to `if` to make it parse at all,
    which shifts every column by two, and the first attempt at this silently patched the wrong text and
    reported zero candidates instead of an error.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    wanted = ast.dump(node, include_attributes=False)
    for candidate in ast.walk(tree):
        if candidate.lineno != line if hasattr(candidate, "lineno") else True:
            continue
        if getattr(candidate, "end_lineno", line) != line:
            continue
        if ast.dump(candidate, include_attributes=False) == wanted:
            return candidate.col_offset, candidate.end_col_offset
    return None


def parse_line(text: str) -> ast.Module:
    """Parse one indented source line, giving a compound statement the body it cannot have alone.

    `if self.show_envvar:` is not a SyntaxError in a file and is one on its own, and the run on click
    `1b0e19f505` reported the human's one-line fix as unparseable because of it.
    """
    if text.lstrip().startswith("elif "):
        # `elif` is not a statement on its own; as `if` it is the same node shape and the same test.
        text = text.lstrip().replace("elif ", "if ", 1)
    if text.lstrip().startswith("except ") and text.rstrip().endswith(":"):
        return ast.parse(f"try:\n    pass\n{text.strip()}\n    pass\n")
    try:
        return ast.parse(text)
    except SyntaxError:
        if text.rstrip().endswith(":"):
            return ast.parse(text + "\n        pass")
        # A changed line is often one ENTRY of a literal, e.g. httpx's
        # `"raw_path": request.url.raw_path,`. Wrapping it in a dict makes both sides parse the same
        # way, so the change point is the entry's value and not "unparseable".
        try:
            return ast.parse("{" + text.strip().rstrip(",") + "}")
        except SyntaxError:
            return ast.parse(f"def _f({text.strip().rstrip(',')}):\n    pass\n")


def enclosing_class(source: str, line: int) -> ast.ClassDef | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.lineno <= line <= getattr(node, "end_lineno", node.lineno):
                if best is None or node.lineno > best.lineno:
                    best = node
    return best


def guarded_body(source: str, site_line: int) -> list[ast.stmt]:
    """The block the changed condition guards: the statements that run when the site is true.

    On click `1b0e19f505` the site is `self.show_envvar` and the very next line is
    `result += f" (env var: '{self.envvar}')"`. The value that made the guard wrong is printed one line
    below the guard. The material for the fix is not in the file's name table; it is in the data flow the
    guard controls.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    inside = [node for node in ast.walk(tree)
              if isinstance(node, (ast.If, ast.While))
              and node.test.lineno <= site_line <= getattr(node.test, "end_lineno", node.test.lineno)]
    if not inside:
        return []
    nearest = max(inside, key=lambda node: node.test.lineno)
    return list(nearest.body)


def _material_of(nodes: list[ast.AST]) -> list[tuple[int, str]]:
    """`base.attr` chains and free names, tagged with line and with which kind they are.

    A bare `self` is not material: it is the base of an attribute, and offering it as an atom spends a
    candidate on `site and self`. Field accesses come before bare locals inside a ring because that is
    what a fix adds -- a value the object already holds, named where the guard can see it.
    """
    chains: list[tuple[int, str]] = []
    names: list[tuple[int, str]] = []
    bases: set[str] = set()
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    chains.append((node.lineno, f"{node.value.id}.{node.attr}"))
                    bases.add(node.value.id)
            elif isinstance(node, ast.Name) and node.id.isidentifier() and not node.id.startswith("__"):
                names.append((node.lineno, node.id))
    names = [pair for pair in names if pair[1] not in bases]
    return chains + names


def proximity_material(source: str, site_line: int, site_text: str) -> list[str]:
    """The site's material, ordered by how much of it the site's own data flow already contains.

    Free enumeration priced every atom the same, so it spent its whole budget on
    `ParameterSource.COMMANDLINE + ParameterSource.COMMANDLINE` before reaching anything on the line.
    Distance is the only thing that can order a pool that is too large to exhaust: the value that made a
    guard wrong is in the guarded body first, then in the same function, then in the class, then in the
    module.
    """
    try:
        site_node = ast.parse(site_text, mode="eval").body
    except SyntaxError:
        site_node = None
    rings: list[list[tuple[int, str]]] = [
        _material_of([site_node]) if site_node is not None else [],          # ring 0: the site itself
        _material_of(guarded_body(source, site_line)),                        # ring 1: what the guard controls
        [],                                                                   # ring 2: the function
        [],                                                                   # ring 3: the class
    ]
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        enclosing = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.lineno <= site_line <= getattr(node, "end_lineno", node.lineno)]
        if enclosing:
            nearest_function = max(enclosing, key=lambda node: node.lineno)
            rings[2] = _material_of([nearest_function])
            rings[2] += [(site_line, name) for name in needs.names_in_scope(source, site_line)
                         if name.isidentifier() and not name.startswith("__")]
        klass = enclosing_class(source, site_line)
        if klass is not None:
            rings[3] = _material_of(list(klass.body))
        rings.append(_material_of(list(tree.body)))                           # ring 4: the module
    ordered: dict[str, tuple[int, int]] = {}
    for distance, ring in enumerate(rings):
        for position, (_line, text) in enumerate(ring):
            if len(text) > 24:
                continue
            if text not in ordered:
                ordered[text] = (distance, position)
    ranked = sorted(ordered.items(), key=lambda pair: pair[1])
    material = [text for text, _distance in ranked]
    # A name that only ever appears as the base of an attribute is not a value the site can use.
    bases = {text.split(".")[0] for text in material if "." in text}
    material = [text for text in material if text not in bases]
    for constant in ("None", "0", "1", "True", "False"):
        if constant not in order_counts(material):
            material.append(constant)
    return material


def order_counts(material: list[str]) -> dict[str, int]:
    return {text: index for index, text in enumerate(material)}


# The forms a real single-site fix takes, commonest first. A guard that lets a bad value through is
# widened with a None-test (conditional fixes are the largest class in every fix taxonomy measured), then
# with a general guard, then narrowed, then compared. Each form is one *edit applied to the site's tree*,
# so the pool is ordered by distance from the site instead of by size.
FORMS = (
    "({site}) and ({atom}) is not None",
    "({site}) and ({atom})",
    "({site}) and not ({atom})",
    "({site}) or ({atom})",
    "({site}) is not None",
    "({site}) is None",
    "not ({site})",
    "({atom}) is not None",
    "({atom}) is None",
    "({site}) or ({atom}) is not None",
    "({atom})",
    "({site}) and ({atom}) is None",
    "({site}) == ({atom})",
    "({site}) != ({atom})",
)


def candidates_at(source: str, site_line: int, site_text: str, *, budget: int = 400,
                  max_size: int = MAX_NODES) -> list[str]:
    """Site-rooted first, free combinations last. Pure syntax: nothing here executes."""
    material = proximity_material(source, site_line, site_text)
    produced: list[str] = [site_text]
    seen: set[str] = {site_text}
    usable = [atom for atom in material if atom != site_text]
    # Ring by ring through the material, and inside a ring the whole form family. The first ring is the
    # guarded body, so `site and X is not None` for the value the block actually uses comes before any
    # combination of two unrelated atoms.
    for atom in usable:
        for form in FORMS:
            text = form.format(site=site_text, atom=atom)
            if text in seen:
                continue
            try:
                body = ast.parse(text, mode="eval").body
            except SyntaxError:
                continue
            if needs.expression_size(body) > max_size:
                continue
            seen.add(text)
            produced.append(text)
            if len(produced) >= budget:
                return produced
    pool = [atom for atom in usable[:60]]
    frontier = list(produced[:40])
    while len(produced) < budget and frontier:
        following: list[str] = []
        for left in frontier:
            for right in pool:
                for text in _combinations(left, right, "____never____"):
                    if text in seen:
                        continue
                    try:
                        body = ast.parse(text, mode="eval").body
                    except SyntaxError:
                        continue
                    if needs.expression_size(body) > max_size:
                        continue
                    seen.add(text)
                    produced.append(text)
                    following.append(text)
                    if len(produced) >= budget:
                        return produced
        frontier = following
    return produced


def replace_site(source: str, site_line: int, start_col: int, end_col: int, expression: str) -> str | None:
    """Put `expression` where the old sub-expression was, by column, not by matching its text.

    Literal matching failed on `default_value == ""`: the AST unparses the constant with single quotes
    and the file uses double ones, so every candidate was silently skipped and the run reported zero
    candidates while claiming to have measured them.
    """
    lines = source.splitlines(keepends=True)
    index = site_line - 1
    if index < 0 or index >= len(lines):
        return None
    line = lines[index]
    if end_col > len(line):
        return None
    lines[index] = line[:start_col] + expression + line[end_col:]
    patched = "".join(lines)
    try:
        ast.parse(patched)
    except SyntaxError:
        return None
    return patched


def geometry_of(old_node: ast.AST, new_node: ast.AST) -> str:
    """Where the fix lives relative to the site: widening, narrowing, or a straight replacement."""
    def dump(node: ast.AST) -> str:
        return ast.dump(node, include_attributes=False)

    def contains(outer: ast.AST, inner: ast.AST) -> bool:
        needle = dump(inner)
        return any(dump(node) == needle for node in ast.walk(outer))

    if contains(new_node, old_node):
        return "SITE_SURVIVES_INSIDE_THE_FIX"
    if contains(old_node, new_node):
        return "FIX_IS_INSIDE_THE_SITE"
    return "SITE_IS_REPLACED"


def summarise(table: list[dict[str, Any]], baseline: dict[str, str],
              human_fix: str) -> dict[str, Any]:
    """Who survives the project's own tests, and how many tests it took to get there.

    A row is *consistent* when it makes every test that failed on the parent pass and leaves every test
    that passed on the parent passing. If exactly one row is consistent, the suite identified the fix. If
    several are, the suite could not tell them apart -- which is an identifiability result about the
    oracle, not a bug in the search, and it is reported as such.
    """
    failing_at_parent = {name for name, verdict in baseline.items() if verdict != "PASSED"}
    passing_at_parent = {name for name, verdict in baseline.items() if verdict == "PASSED"}
    consistent: list[str] = []
    for row in table:
        outcomes = row["outcomes"]
        if all(outcomes.get(name) == "PASSED" for name in failing_at_parent) and \
           all(outcomes.get(name) != "FAILED" for name in passing_at_parent):
            consistent.append(row["expression"])
    human_ast = ast.dump(ast.parse(human_fix, mode="eval").body)
    human_equivalent = [text for text in consistent
                        if ast.dump(ast.parse(text, mode="eval").body) == human_ast]
    # How many tests does it take to force one survivor? Greedy: the test that splits the living set
    # hardest, until a single row is left or nothing splits any further.
    living = list(range(len(table)))
    queries: list[str] = []
    while len(living) > 1:
        best_test, best_split = None, 0
        for name in baseline:
            buckets: dict[str, int] = {}
            for index in living:
                buckets.setdefault(str(table[index]["outcomes"].get(name)), 0)
                buckets[str(table[index]["outcomes"].get(name))] += 1
            split = max(buckets.values()) if buckets else len(living)
            # The useful test leaves the largest class as small as possible.
            if best_test is None or split < best_split:
                best_test, best_split = name, split
        if best_test is None or best_split == len(living):
            break
        observed = str(table[living[0]]["outcomes"].get(best_test))
        queries.append(best_test)
        living = [index for index in living
                  if str(table[index]["outcomes"].get(best_test)) == observed]
        if len(queries) > 30:
            break
    return {
        "consistent_candidates": len(consistent),
        "consistent": [text[:90] for text in consistent[:8]],
        "human_fix_is_consistent": bool(human_equivalent),
        "queries_to_one_survivor": len(queries),
        "questions": queries[:8],
        "identified": len(consistent) == 1 and bool(human_equivalent),
        "tests_in_file": len(baseline),
    }


def identify(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
             budget: int = 200, seconds: int = 20) -> dict[str, Any]:
    started = time.time()
    parent_sha = f"{sha}^"
    parent_source = show(repo, parent_sha, source_path)
    fix_source = show(repo, sha, source_path)
    if not parent_source or not fix_source:
        return {"stage": "SOURCE_NOT_FOUND"}
    pair = next(iter(needs.changed_pairs(repo, sha, source_path)), None)
    if pair is None:
        return {"stage": "NOT_A_SINGLE_LINE_FIX", "sha": sha}
    old_line_text, new_line_text = (pair[0].strip(), pair[1].strip())
    line_number = needs._line_of(parent_source, old_line_text)  # noqa: SLF001
    try:
        old_stmt, new_stmt = parse_line(old_line_text), parse_line(new_line_text)
    except SyntaxError:
        return {"stage": "FIX_LINE_DOES_NOT_PARSE", "old": old_line_text, "new": new_line_text}
    changes = needs.change_points(old_stmt, new_stmt)
    if len(changes) != 1 or not isinstance(changes[0][2], ast.expr):
        return {"stage": "FIX_IS_NOT_A_SINGLE_EXPRESSION",
                "old": old_line_text, "new": new_line_text}
    site_text = ast.unparse(changes[0][1])
    span = span_of(parent_source, line_number, changes[0][1])
    if span is None:
        return {"stage": "SITE_NOT_LOCATED_IN_THE_PARENT"}
    site_start, site_end = span
    human_fix = ast.unparse(changes[0][2])

    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                        parent_sha], capture_output=True, text=True)
        try:
            (worktree / test_path).write_text(show(repo, sha, test_path), encoding="utf-8")
            baseline, output = run_tests_full(worktree, test_path, seconds)
            failing = {name for name, verdict in baseline.items() if verdict != "PASSED"}
            if not baseline or "error during collection" in output.lower() or "Interrupted:" in output:
                # A collection error is not a failing test: blaming it would be blaming a fixture.
                return {"stage": "SUITE_DID_NOT_RUN", "output_tail": output[-600:]}
            if not failing:
                return {"stage": "NO_ORACLE__THE_POST_FIX_TESTS_PASS_ON_THE_PARENT",
                        "baseline": baseline}
            # Reachability and ordering are different failures and must be counted apart: an answer
            # missing from a 400-long pool is a coverage failure, an answer at rank 300 is an ordering
            # failure, and only the second one gets fixed by better questions.
            full_pool = candidates_at(parent_source, line_number, site_text, budget=400)
            human_ast = ast.dump(ast.parse(human_fix, mode="eval").body)
            rank_full = next((index for index, text in enumerate(full_pool)
                              if ast.dump(ast.parse(text, mode="eval").body) == human_ast), None)
            options = full_pool[:budget]
            rank = rank_full if rank_full is not None and rank_full < len(options) else None
            target = worktree / source_path
            original = target.read_text(encoding="utf-8")
            table: list[dict[str, Any]] = []
            for expression in options:
                patched = replace_site(original, line_number, site_start, site_end, expression)
                if patched is None:
                    continue
                target.write_text(patched, encoding="utf-8")
                outcomes = run_tests(worktree, test_path, seconds)
                target.write_text(original, encoding="utf-8")
                table.append({"expression": expression, "outcomes": outcomes})
            analysis = summarise(table, baseline, human_fix)
            return {
                "stage": "MEASURED", "analysis": analysis, "sha": sha, "source": source_path, "test_file": test_path,
                "site": site_text, "line": line_number, "human_fix": human_fix,
                "oracle_failures_at_parent": sorted(failing),
                "candidates": len(table), "table": table,
                "human_fix_rank": rank, "human_fix_in_pool": rank is not None,
                "human_fix_rank_in_full_pool": rank_full,
                "geometry": geometry_of(changes[0][1], changes[0][2]),
                "seconds": round(time.time() - started, 2),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def sweep(entries: list[dict[str, str]], *, budget: int, receipt: pathlib.Path,
          seconds: int = 20) -> dict[str, Any]:
    """Run the whole loop on every qualifying commit in the history, not on one chosen example."""
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = pathlib.Path("/tmp/repos") / entry["repo"]
        row: dict[str, Any] = {k: entry[k] for k in ("repo", "commit", "source", "test")}
        try:
            result = identify(repo, entry["commit"], source_path=entry["source"],
                              test_path=entry["test"], budget=budget, seconds=seconds)
        except Exception as error:  # a broken checkout must not end the sweep
            result = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:200]}
        row["stage"] = result.get("stage")
        row["analysis"] = result.get("analysis")
        row["human_fix_rank"] = result.get("human_fix_rank")
        row["candidates"] = result.get("candidates")
        row["human_fix"] = result.get("human_fix")
        row["geometry"] = result.get("geometry")
        row["rank_in_full_pool"] = result.get("human_fix_rank_in_full_pool")
        row["site"] = result.get("site")
        rows.append(row)
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:10]} "
              f"{row['stage']} consistent={((row['analysis'] or {}).get('consistent_candidates'))} "
              f"rank={row['human_fix_rank']}", file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({
            "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-18",
            "mode": "SWEEP_REAL_HISTORY", "budget": budget, "rows": rows,
            "seconds": round(time.time() - started, 1)}, indent=1) + "\n")
    return {"rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", type=pathlib.Path, default=None,
                        help="JSON list of {repo, commit, source, test}: run the loop on all of them")
    parser.add_argument("--repo", type=pathlib.Path, default=None)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--test", default=None)
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--test-seconds", type=int, default=20)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    if args.sweep is not None:
        entries = json.loads(args.sweep.read_text())
        sweep(entries, budget=args.budget, receipt=args.receipt or pathlib.Path("/tmp/sweep.json"),
              seconds=args.test_seconds)
        return 0
    if not (args.repo and args.commit and args.source and args.test):
        parser.error("--repo, --commit, --source and --test are required without --sweep")
    result = identify(args.repo, args.commit, source_path=args.source, test_path=args.test,
                      budget=args.budget, seconds=args.test_seconds)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-18", "result": result}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "table"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
