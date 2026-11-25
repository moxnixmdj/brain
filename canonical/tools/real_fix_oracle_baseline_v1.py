#!/usr/bin/env python3
"""Real-fix oracle baseline: 87 execution-verified tasks, judged by the repo's own tests.

WHY THIS EXISTS
---------------
`canonical/corpus/real_fix_pairs_20261119_V1.json` carries 87 tasks mined under
the rule *"the commit's test must FAIL at the parent and PASS at the commit,
verified by execution"*.  Each row has the repository, the parent and fix
commits, the source path, the full before/after text, and the exact failing test
node ids.

That is a real oracle, and until now nothing in this tree ran it.  Every number
about repair reach in this repository was measured on QuixBugs or on synthetic
witnesses.  This harness makes the 87 runnable:

    git checkout <fix sha>          # the tests the fix added now exist
    write `before` over the source  # revert ONLY the fix
    pytest <failed_nodes>  -> FAIL  # confirmed
    write `after`                  # the fix
    pytest <failed_nodes>  -> PASS  # confirmed

A task is only *well-formed* if both directions hold.  Tasks that are not
well-formed are reported and excluded, never silently dropped.

INTEGRITY
---------
The candidate arm sees: the `before` source text, the repository path, the
failing node ids, and the interpreter.  It NEVER sees `after`, the commit
subject, or the diff.  `after` is held by the judge only.

AUTHORITY: NONE.  Producer-run sandbox measurement.  No model, no network at
decision time, no spend.  Nothing here repairs a repository; the judge applies a
candidate to a throwaway clone and reverts it.

Usage
-----
    python3 canonical/tools/real_fix_oracle_baseline_v1.py --validate-only
    python3 canonical/tools/real_fix_oracle_baseline_v1.py --arm blind --limit 20
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

SCHEMA = "PROJECT_BRAIN_REAL_FIX_ORACLE_BASELINE_V1"
CORPUS = pathlib.Path(__file__).resolve().parents[1] / "corpus" / "real_fix_pairs_20261119_V1.json"
DEFAULT_WORKDIR = pathlib.Path("/tmp/real")

REPO_URL = {
    "pypa/packaging": "packaging",
    "hukkin/tomli": "tomli",
    "pallets/itsdangerous": "itsdangerous",
}


# --------------------------------------------------------------------------- #
# the oracle
# --------------------------------------------------------------------------- #

@dataclass
class Oracle:
    """One repository at one commit, with a private virtualenv."""

    repo_slug: str
    workdir: pathlib.Path
    py: str = ""
    path: pathlib.Path = field(init=False)

    def __post_init__(self) -> None:
        name = REPO_URL.get(self.repo_slug, self.repo_slug.split("/")[-1])
        self.path = self.workdir / name
        self.py = str(self.workdir / "venvs" / name / "bin" / "python")

    # -- environment ------------------------------------------------------- #
    def ensure(self) -> dict[str, Any]:
        """Clone + venv + install.  Returns a receipt; never raises."""
        steps: dict[str, Any] = {}
        try:
            if not self.path.exists():
                subprocess.run(
                    ["git", "clone", "-q", "--no-checkout",
                     f"https://github.com/{self.repo_slug}", str(self.path)],
                    check=True, capture_output=True, timeout=900)
                steps["cloned"] = True
            else:
                steps["cloned"] = False
            venv = pathlib.Path(self.py).parents[1]
            if not pathlib.Path(self.py).exists():
                subprocess.run([sys.executable, "-m", "venv", str(venv)],
                               check=True, capture_output=True, timeout=600)
                subprocess.run([self.py, "-m", "pip", "install", "-q", "--upgrade", "pip"],
                               check=True, capture_output=True, timeout=900)
                subprocess.run([self.py, "-m", "pip", "install", "-q", "pytest", "flaky"],
                               check=True, capture_output=True, timeout=900)
                # build backends first: tomli needs flit_core, and without it the
                # editable install fails silently and every task becomes
                # "ORACLE_DISAGREES" for the wrong reason
                subprocess.run([self.py, "-m", "pip", "install", "-q",
                                "flit_core", "hatchling", "setuptools", "wheel",
                                "poetry-core"],
                               check=False, capture_output=True, timeout=1200)
                r = subprocess.run([self.py, "-m", "pip", "install", "-q", "-e", str(self.path)],
                                   capture_output=True, text=True, timeout=1800)
                steps["install_rc"] = r.returncode
                if r.returncode != 0:
                    steps["install_error"] = (r.stderr or r.stdout)[-400:]
                steps["venv"] = True
            else:
                steps["venv"] = False
            steps["ok"] = True
        except Exception as exc:  # noqa: BLE001
            steps["ok"] = False
            steps["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return steps

    # -- state ------------------------------------------------------------- #
    def checkout(self, ref: str) -> None:
        # A bare `--no-checkout` clone has no worktree files, so discarding
        # edits can legitimately fail.  Never fatal: the point is only to drop
        # whatever the previous task wrote.
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=self.path, check=False)
        subprocess.run(["git", "checkout", "-q", ref], cwd=self.path, check=True)

    def write_source(self, rel: str, text: str) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def fail_set(self, nodes: Sequence[str], timeout: int = 900) -> set[str]:
        """The set of failing node ids, WITHOUT `-x`.

        `-x` stops at the first failure, which makes it impossible to ask "did
        this repair break anything *else*".  A repair oracle has to compare
        failure SETS: the candidate's failures must be a subset of the baseline's.
        """
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            r = subprocess.run(
                [self.py, "-m", "pytest", *nodes, "-q", "--no-header",
                 "-p", "no:cacheprovider", "--tb=no", "-rfE"],
                cwd=self.path, capture_output=True, text=True, env=env, timeout=timeout)
            out = (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return {"<TIMEOUT>"}
        failed: set[str] = set()
        for ln in out.splitlines():
            if ln.startswith(("FAILED ", "ERROR ")):
                parts = ln.split()
                if len(parts) >= 2:
                    failed.add(parts[1])
        # a collection error is not "one failure", it is every test in the file
        # failing; represent it as the file itself so subset checks cannot pass
        if any("::" not in f for f in failed):
            failed.add("<COLLECTION_ERROR>")
        return failed

    def test(self, nodes: Sequence[str], timeout: int = 900) -> dict[str, Any]:
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        t0 = time.perf_counter()
        try:
            r = subprocess.run(
                [self.py, "-m", "pytest", *nodes, "-q", "--no-header",
                 "-p", "no:cacheprovider", "-x"],
                cwd=self.path, capture_output=True, text=True, env=env, timeout=timeout)
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out = 124, "TIMEOUT"
        dt = time.perf_counter() - t0
        passed = rc == 0
        tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1:] or [""]
        return {"rc": rc, "passed": passed, "seconds": round(dt, 2),
                "tail": tail[0][:160], "output": out}


# --------------------------------------------------------------------------- #
# the candidate arm
# --------------------------------------------------------------------------- #

def blind_candidates(before: str, repo_path: pathlib.Path,
                     *, limit: int = 64) -> list[tuple[str, str]]:
    """Candidate single-statement edits, built ONLY from what the file already contains.

    No knowledge of the fix.  The vocabulary is the file's own: its imports, its
    names, its calls, and the identifiers used elsewhere in the same repository.
    An edit that needs a name that appears nowhere is not proposed, because an
    invented name is a fabricated repair.
    """
    import ast

    try:
        tree = ast.parse(before)
    except SyntaxError:
        return []

    # vocabulary already present in the file
    called: set[str] = set()
    attrs: set[str] = set()
    imported: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
        elif isinstance(n, ast.Attribute):
            attrs.add(n.attr)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                imported.add(a.asname or a.name.split(".")[0])
    vocab = sorted((called | imported) - {"print", "len", "range", "isinstance"})

    # sibling modules in the same repository: names a real fix could reach for
    sibling: set[str] = set()
    try:
        for p in list(repo_path.rglob("*.py"))[:400]:
            if any(x in p.parts for x in (".git", "tests", "test", "__pycache__",
                                          "node_modules", "build", "dist")):
                continue
            try:
                sub = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(sub):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    sibling.add(n.name)
    except Exception:
        pass

    out: list[tuple[str, str]] = []
    lines = before.splitlines(keepends=True)
    # 1. wrap an existing call in a cast/coerce that already exists in the file
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "#", "@", "import ", "from ")):
            continue
        for name in list(vocab)[:12]:
            for wrap in ("tuple", "list", "set", "frozenset", "dict", "sorted", "str", "int"):
                if f"{wrap}(" in line:
                    continue
                out.append((f"wrap:{wrap}@{i}", f"{wrap}({stripped.rstrip()}))"))
                if len(out) >= limit:
                    return out
    # 2. add a missing import for a sibling name the file already references
    for name in sorted(sibling)[:24]:
        if name in before:
            continue
        out.append((f"import:{name}", f"import {name}\n"))
        if len(out) >= limit:
            break
    return out[:limit]


# --------------------------------------------------------------------------- #
# traceback-terminal localization
# --------------------------------------------------------------------------- #
#
# The failing test is not the only signal: the traceback's LAST frame inside the
# repository names the line that actually raised.  That is a localisation the
# system did not have to search for, and it collapses the candidate space from
# "every line in the file" to "the few lines the failure passed through".
#
# Mutations are derived from the LANGUAGE, never from the fix: literal nudges,
# comparison and arithmetic operator swaps, boolean duals, and guard removal.
# Nothing here knows what the correct answer is.

_CMP = [("<", "<="), ("<=", "<"), (">", ">="), (">=", ">"), ("==", "!="), ("!=", "==")]
_ARITH = [("+", "-"), ("-", "+"), ("*", "//"), ("//", "*"), ("%", "//")]
_BOOL = [("and", "or"), ("or", "and")]


def _swap_all(line: str, pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Swap operator tokens on WORD BOUNDARIES only.

    A plain ``str.replace`` rewrote ``or`` -> ``and`` inside ``TypeError`` and
    ``not`` -> ``''`` inside ``cannot``.  Those are not mutations, they are
    typos, and they cost a judge call each.
    """
    import re as _re
    out: list[str] = []
    for a, b in pairs:
        pat = _re.compile(r"(?<![\w])" + _re.escape(a) + r"(?![\w])")
        if pat.search(line):
            out.append(pat.sub(b, line, count=1))
            out.append(pat.sub(b, line))
    return out


def _literal_nudges(line: str) -> list[str]:
    import re as _re
    out: list[str] = []
    for m in _re.finditer(r"(?<![\w.])(\d+)(?![\w.])", line):
        n = int(m.group(1))
        for repl in (n + 1, n - 1, 0, 1, -1, 2 * n):
            if repl == n:
                continue
            out.append(line[:m.start()] + str(repl) + line[m.end():])
    return out


def mutations_of(line: str) -> list[tuple[str, str]]:
    """Bounded, language-derived single-line mutations.  Order is the priority."""
    cands: list[tuple[str, str]] = []
    seen: set[str] = set()
    stripped = line.strip()

    def add(kind: str, text: str) -> None:
        if text == line or text in seen:
            return
        seen.add(text)
        cands.append((kind, text))

    # 1. guard removal: a `raise` that fires is the most localisable failure there is
    if stripped.startswith("raise "):
        add("drop_raise", " " * (len(line) - len(line.lstrip())) + "pass\n")
    # 2. comparison / arithmetic / boolean duals
    for pairs, tag in ((_CMP, "cmp"), (_ARITH, "arith"), (_BOOL, "bool")):
        for text in _swap_all(line, pairs):
            add(f"swap_{tag}", text)
    # 3. literal nudges
    for text in _literal_nudges(line):
        add("literal", text)
    # 4. negation and return-coercion
    import re as _re
    if _re.search(r"(?<![\w])not\s+", line):
        add("drop_not", _re.sub(r"(?<![\w])not\s+", "", line, count=1))
    if stripped.startswith("return "):
        expr = stripped[len("return "):].rstrip()
        for wrap in ("tuple", "list", "set", "sorted", "str", "int", "len"):
            add(f"ret_{wrap}", line.replace(expr, f"{wrap}({expr})", 1))
    # 5. slice bounds
    if "[" in line and ":" in line:
        add("slice_shift", line.replace("[", "[1:", 1).replace("[1::", "[1:", 1))
    return cands


def localize_failure(pytest_output: str, repo_path: pathlib.Path) -> list[tuple[str, int]]:
    """(relative path, line) for every traceback frame inside the repository."""
    import re as _re
    hits: list[tuple[str, int]] = []
    # pytest prints `path:line: ErrorType` and `path:line: in name`
    for m in _re.finditer(r"^(?P<p>[^\s:][^:\n]*?):(?P<n>\d+):\s", pytest_output, _re.M):
        raw, num = m.group("p"), m.group("n")
        if raw.startswith(("/usr/", "/tmp/real/venvs", "<")):
            continue
        cand = (repo_path / raw)
        if not cand.exists():
            continue
        if "/tests/" in str(cand) or cand.name.startswith("test_") or "conftest" in cand.name:
            continue
        try:
            rel = str(cand.relative_to(repo_path))
        except ValueError:
            continue
        pair = (rel, int(num))
        if pair not in hits:
            hits.append(pair)
    return hits


def enclosing_statement(source: str, lineno: int) -> tuple[int, int] | None:
    """Smallest statement whose extent covers `lineno`, as (first, last) 1-based.

    A `raise` is often three physical lines; mutating the first one alone is a
    syntax error.  The AST gives the real extent for free.
    """
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best: tuple[int, int] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if node.lineno <= lineno <= end:
            if best is None or (end - node.lineno) < (best[1] - best[0]):
                best = (node.lineno, end)
    return best


def _stmt_mutations(stmt_src: str, indent: str) -> list[tuple[str, str]]:
    """Mutations of ONE statement, text-level, on word boundaries."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(kind: str, text: str) -> None:
        if text == stmt_src or text in seen:
            return
        seen.add(text)
        out.append((kind, text))

    body = stmt_src.strip()

    # 1. the statement kind decides the most likely repair
    if body.startswith("raise "):
        # a guard that fires: remove it, or make it unreachable
        add("drop_raise", indent + "pass")
        if "if " not in body:
            add("dead_raise", indent + "if False:\n" + indent + "    pass")
    if body.startswith("if ") and body.endswith(":"):
        cond = body[3:-1].strip()
        if cond.startswith("not "):
            add("drop_not", f"{indent}if {cond[4:]}:")
        add("negate_if", f"{indent}if not ({cond}):")
    if body.startswith("return "):
        expr = body[7:].strip()
        for wrap in ("tuple", "list", "set", "sorted", "str", "int", "len", "dict"):
            add(f"ret_{wrap}", f"{indent}return {wrap}({expr})")
        if expr in ("True", "False"):
            add("ret_flip", f"{indent}return {not (expr == 'True')}")
    if body.startswith("assert "):
        expr = body[7:].strip()
        add("drop_assert", indent + "pass")
        add("negate_assert", f"{indent}assert not ({expr})")

    # 2. operator duals over the whole statement
    for pairs, tag in ((_CMP, "cmp"), (_ARITH, "arith"), (_BOOL, "bool")):
        for text in _swap_all(stmt_src, pairs):
            add(f"swap_{tag}", text)

    # 3. literal nudges
    for text in _literal_nudges(stmt_src):
        add("literal", text)
    return out


def local_candidates(before: str, repo_path: pathlib.Path,
                     *, failure_output: str = "", limit: int = 96) -> list[tuple[str, str]]:
    """Mutate only the statement the failure actually raised from.

    Localisation comes from the traceback, which names the exact line.  Nothing
    here reads the fix; the mutations are derived from the Python grammar.
    """
    if not failure_output:
        return []
    sites = localize_failure(failure_output, repo_path)
    if not sites:
        return []
    out: list[tuple[str, str]] = []
    for rel, lineno in sites[:6]:
        try:
            text = (repo_path / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        extent = enclosing_statement(text, lineno)
        if extent is None:
            continue
        first, last = extent
        lines = text.splitlines(keepends=True)
        stmt_src = "".join(lines[first - 1:last])
        indent = lines[first - 1][: len(lines[first - 1]) - len(lines[first - 1].lstrip())]
        for kind, mutated in _stmt_mutations(stmt_src, indent):
            # the payload IS the statement's replacement; apply_candidate
            # recomputes the extent so multi-line statements are replaced whole
            out.append((f"local:{rel}:{first}:{kind}", mutated))
            if len(out) >= limit:
                return out
    return out[:limit]


ARMS: dict[str, Callable[..., list[tuple[str, str]]]] = {
    "blind": blind_candidates,
    "local": local_candidates,
}


# --------------------------------------------------------------------------- #
# self-judging arms: they run the real test themselves, so the harness does not
# apply a candidate -- it only records what they report and re-checks the claim.
# --------------------------------------------------------------------------- #

def witness_candidates(before: str, repo_path: pathlib.Path, *,
                      oracle: Oracle | None = None, task: Mapping[str, Any] | None = None,
                      budget: int = 12) -> list[tuple[str, str]]:
    """`witness_inversion_v1` as a pure PROPOSER.

    It already implements the idea: the assertion names a required value, the
    failing frame carries the concrete inputs, so the expression at that site is
    inverted by evaluation over an alphabet read from the frame.  This arm adds
    nothing to it.  It points it at the real oracle, uses the task's own
    virtualenv instead of this interpreter, and hands the proposals back so the
    HARNESS judges them -- a self-report is not a result.
    """
    if oracle is None or task is None:
        return []
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "swe_kernel"))
    try:
        import witness_inversion_v1 as W
    except Exception:
        return []
    node = task["failed_nodes"][0]
    test_file, _, test_name = node.partition("::")
    report = W.capture(oracle.path, [oracle.path / task["source"]],
                       oracle.path / test_file, test_name, python=oracle.py)
    if report.get("outcome") != "WITNESSED":
        return []
    out: list[tuple[str, str]] = []
    for site in report.get("sites", [])[:4]:
        for expression in W.invert(site)[:budget]:
            rebuilt = W.apply_expression(before, site, expression)
            if rebuilt and rebuilt != before:
                out.append((f"witness:{site.get('function')}:{expression}", rebuilt))
            if len(out) >= 96:
                return out
    return out


ARMS["witness"] = witness_candidates


def apply_candidate(before: str, kind: str, payload: str,
                    repo_path: pathlib.Path | None = None) -> str:
    """Materialise a candidate edit.  Unknown kinds are refused, not guessed."""
    if kind.startswith("local:"):
        # local:<rel>:<line>:<mutation> -> replace the STATEMENT at that line
        try:
            _tag, rel, num, _m = kind.split(":", 3)
            target = (repo_path or pathlib.Path(".")) / rel
            text = target.read_text(encoding="utf-8")
            extent = enclosing_statement(text, int(num))
            if extent is None:
                return before
            first, last = extent
            lines = text.splitlines(keepends=True)
            block = payload if payload.endswith("\n") else payload + "\n"
            target.write_text("".join(lines[: first - 1] + [block] + lines[last:]),
                              encoding="utf-8")
        except Exception:
            return before
        return before
    if kind.startswith("import:"):
        return payload + before
    if kind.startswith("wrap:"):
        try:
            idx = int(kind.split("@")[1])
        except (IndexError, ValueError):
            return before
        lines = before.splitlines(keepends=True)
        if not 0 <= idx < len(lines):
            return before
        lines[idx] = payload + "\n"
        return "".join(lines)
    return before


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #

def run(corpus: pathlib.Path, workdir: pathlib.Path, *, arm: str | None,
        limit: int | None, validate_only: bool, out_path: pathlib.Path | None,
        per_task_budget_s: float = 120.0, offset: int = 0) -> dict[str, Any]:
    tasks = json.loads(corpus.read_text())["tasks"]
    tasks = tasks[offset:]
    if limit:
        tasks = tasks[:limit]
    oracles: dict[str, Oracle] = {}
    rows: list[dict[str, Any]] = []
    env_receipts: dict[str, Any] = {}

    for t in tasks:
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, workdir)
            env_receipts[slug] = oracles[slug].ensure()
        o = oracles[slug]
        row: dict[str, Any] = {
            "repo": slug, "sha": t["sha"][:10], "parent": t["parent"][:10],
            "source": t["source"], "nodes": len(t["failed_nodes"]),
        }
        if not env_receipts[slug].get("ok"):
            row["well_formed"] = False
            row["reason"] = "ENV_UNAVAILABLE"
            row["env_error"] = env_receipts[slug].get("error")
            rows.append(row)
            continue

        if not t.get("failed_nodes"):
            # pytest with no node ids runs the WHOLE suite: slow, and it would
            # silently redefine the oracle.  Refuse the task instead.
            row["well_formed"] = False
            row["reason"] = "NO_FAILED_NODES"
            rows.append(row)
            continue

        try:
            o.checkout(t["sha"])
            o.write_source(t["source"], t["before"])
            before_run = o.test(t["failed_nodes"])
            o.write_source(t["source"], t["after"])
            after_run = o.test(t["failed_nodes"])
        except Exception as exc:  # noqa: BLE001
            row["well_formed"] = False
            row["reason"] = f"HARNESS_{type(exc).__name__}"
            rows.append(row)
            continue

        row["well_formed"] = (before_run["passed"] is False and after_run["passed"] is True)
        row["before_passes"] = before_run["passed"]
        row["after_passes"] = after_run["passed"]
        row["oracle_s"] = round(before_run["seconds"] + after_run["seconds"], 2)

        if not row["well_formed"]:
            row["reason"] = "ORACLE_DISAGREES"
            rows.append(row)
            continue
        if validate_only:
            rows.append(row)
            continue

        # ---- the arm runs BLIND: `before` only ---------------------------- #
        o.write_source(t["source"], t["before"])
        first = o.test(t["failed_nodes"])
        # A PASS on the first run means the task is not usable; say so.
        if first["passed"]:
            row["well_formed"] = False
            row["reason"] = "FIX_ALREADY_SATISFIED"
            rows.append(row)
            continue

        # the regression oracle: the whole test FILE, compared as a failure SET.
        # Passing the failing node alone is not a repair -- dropping a `raise`
        # makes that node pass and breaks the invariant it guarded.  `-x` cannot
        # express "no new failures", so this uses fail_set.
        test_file = ""
        if t.get("failed_nodes") and "::" in t["failed_nodes"][0]:
            test_file = t["failed_nodes"][0].split("::")[0]
        baseline_fail: set[str] | None = None
        if test_file and (o.path / test_file).exists():
            baseline_fail = o.fail_set([test_file])

        gen = ARMS.get(arm or "")
        solved: dict[str, Any] | None = None
        tried = 0
        regressed = 0
        t0 = time.perf_counter()
        if gen is not None:
            try:
                if arm == "local":
                    cands = gen(t["before"], o.path, failure_output=first["output"])
                elif arm == "witness":
                    cands = gen(t["before"], o.path, oracle=o, task=t)
                else:
                    cands = gen(t["before"], o.path)
            except Exception:
                cands = []
            for kind, payload in cands:
                if time.perf_counter() - t0 > per_task_budget_s:
                    break
                tried += 1
                o.write_source(t["source"], t["before"])
                patched = (payload if kind.startswith("witness:")
                           else apply_candidate(t["before"], kind, payload, repo_path=o.path))
                if arm != "local":
                    if patched == t["before"]:
                        continue
                    o.write_source(t["source"], patched)
                verdict = o.test(t["failed_nodes"])
                if not verdict["passed"]:
                    continue
                # it passes the failing test -- now break nothing else
                if baseline_fail is not None:
                    cand_fail = o.fail_set([test_file])
                    if not cand_fail <= baseline_fail:
                        regressed += 1
                        continue
                solved = {"kind": kind, "attempt": tried,
                          "seconds": round(time.perf_counter() - t0, 2)}
                break
        row["arm"] = arm
        row["arm_tried"] = tried
        row["arm_seconds"] = round(time.perf_counter() - t0, 2)
        row["arm_regressed"] = regressed
        row["baseline_failures"] = sorted(baseline_fail) if baseline_fail is not None else None
        row["solved"] = solved is not None
        if solved:
            row["solution"] = solved
        rows.append(row)
        print(f"{slug:24s} {t['sha'][:8]} nodes={len(t['failed_nodes']):3d} "
              f"well_formed={row['well_formed']} solved={row['solved']} tried={tried}",
              flush=True)

    good = [r for r in rows if r.get("well_formed")]
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_decision_time": 0,
        "arm": arm,
        "tasks": len(rows),
        "well_formed": len(good),
        "solved": sum(1 for r in good if r.get("solved")),
        "unsolved": sum(1 for r in good if r.get("solved") is False),
        "regressed_candidates": sum(r.get("arm_regressed", 0) for r in good),
        "not_well_formed": len(rows) - len(good),
        "oracle_seconds_mean": round(
            sum(r.get("oracle_s", 0.0) for r in good) / max(1, len(good)), 2),
        "environments": env_receipts,
        "rows": rows,
    }
    if out_path:
        out_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    ap.add_argument("--arm", default=None,
                    choices=[None, "blind", "local", "witness"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--offset", type=int, default=0,
                    help="skip the first N corpus tasks (sliced runs)")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--per-task-budget", type=float, default=120.0)
    ns = ap.parse_args(argv)

    s = run(pathlib.Path(ns.corpus), pathlib.Path(ns.workdir), arm=ns.arm,
            limit=ns.limit, offset=ns.offset, validate_only=ns.validate_only,
            out_path=pathlib.Path(ns.out) if ns.out else None,
            per_task_budget_s=ns.per_task_budget)
    print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
