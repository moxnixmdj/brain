#!/usr/bin/env python3
"""Coverage narrows 28 files to 6% of their lines and keeps a fix line on 22 tasks.
Can a generator that only emits edits *already present in the file* actually solve?

WHY THIS TEST AND NOT ANOTHER
-----------------------------
`coverage_selector_measurement_v1` measured the input side: with no traceback frame, running
the failing test reduces the candidate lines from 21,288 to 1,345 (6.3%) and still touches a
real fix line on 22 of 28 tasks. That is a usable pointer. It says nothing about whether the
edits we can emit contain the right one.

The hypothesis, stated before measuring: **the edits that fix these bugs are mostly
recombinations of tokens, constants and expressions already present in the same file** --
`[^\\s;)]*` -> `+`, `[^ \\t]+` -> `\\S+`, a dropped `if`, an inverted condition. If that is true,
a small generator that recombines what it can see should solve a non-trivial fraction, and the
zero-emission result of six earlier rounds was an artefact of *where it was told to look*, not
of the vocabulary. If it is false, the vocabulary really is the wall and more families are
waste.

THE FORMS, ALL BLIND, ALL SITE-LOCAL
------------------------------------
Every form edits one line at one site, and emits only tokens the file already contains:

  TOKEN_SWAP     replace one regex/string literal token with another token that appears
                 elsewhere in the same file, inside a string constant
  QUANTIFIER     `*`->`+`, `+`->`*`, `?`->``, `$`->`\\Z` inside a string or regex literal
  LITERAL_SWAP   replace one numeric/string literal with another literal already in the file
  GUARD          add `if not <arg>: return` / invert a boolean test on an `if` line
  RETURN_NEAR    replace a `return X` with another `return Y` already present in the file

The budget is 40 candidates per task, interleaved across families, and each candidate is run
against the target node AND the whole test module. A task counts only when the target flips
and the module stays green. Nothing is tuned per task; no task is special-cased; the fix diff
is read only afterwards, to classify failures.

INTEGRITY
---------
The generator sees the source file, the failing test's own text (the corpus's rule), and the
lines coverage reported. It never sees the fix commit, never sees the expected patch, and
never sees another task. Zero model calls, no stored parameters, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import coverage_selector_measurement_v1 as COV  # noqa: E402
from canonical.tools import site_edit_space_measurement_v1 as SES  # noqa: E402

SCHEMA = "BRAIN_COVERAGE_SEEDED_GENERATION_V1"
BUDGET = 40
STRING_RE = re.compile(r"""(?P<q>['"])(?P<body>(?:\\.|(?!\1).)*)(?P=q)""")
QUANT_SWAPS = (("*", "+"), ("+", "*"), ("?", ""), ("$", r"\Z"))


def string_literals(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in STRING_RE.finditer(line):
            out.append((i, m.group("body")))
    return out


def token_candidates(covered: dict[str, list[int]], texts: dict[str, str]) -> list[dict[str, Any]]:
    """Recombine tokens the file already contains, at sites coverage says execute."""
    out: list[dict[str, Any]] = []
    for src, lines in covered.items():
        text = texts.get(src, "")
        if not text:
            continue
        rows = text.splitlines()
        pool = {body for _, body in string_literals(text) if len(body) <= 80}
        for ln in lines:
            if not (1 <= ln <= len(rows)):
                continue
            line = rows[ln - 1]
            for m in STRING_RE.finditer(line):
                body = m.group("body")
                if len(body) > 80:
                    continue
                for other in pool:
                    if other == body:
                        continue
                    new = line[: m.start("body")] + other + line[m.end("body"):]
                    out.append({"family": "TOKEN_SWAP", "file": src, "line": ln, "text_line": line,
                                "new": new, "why": f"string {body!r} -> {other!r} (both in file)"})
                for old, new_tok in QUANT_SWAPS:
                    if old in body:
                        replaced = body.replace(old, new_tok, 1)
                        if replaced == body:
                            continue
                        new = line[: m.start("body")] + replaced + line[m.end("body"):]
                        out.append({"family": "QUANTIFIER", "file": src, "line": ln, "text_line": line,
                                    "new": new, "why": f"quantifier {old!r} -> {new_tok!r} in {body!r}"})
    return out


def guard_candidates(covered: dict[str, list[int]], texts: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src, lines in covered.items():
        rows = texts.get(src, "").splitlines()
        for ln in lines:
            if not (1 <= ln <= len(rows)):
                continue
            line = rows[ln - 1]
            stripped = line.strip()
            if stripped.startswith("if ") and stripped.endswith(":"):
                cond = stripped[3:-1]
                new = line.replace("if " + cond + ":", "if not (" + cond + "):", 1)
                out.append({"family": "GUARD", "file": src, "line": ln, "text_line": line,
                            "new": new, "why": "invert the boolean test"})
            m = re.match(r"^(\s*)return (?P<v>.+)$", line)
            if m:
                indent = m.group(1)
                new = f"{indent}if not {m.group('v').strip()}: return"
                out.append({"family": "GUARD", "file": src, "line": ln, "text_line": line,
                            "new": new, "why": "guard a return on its own value"})
    return out


def return_candidates(covered: dict[str, list[int]], texts: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src, lines in covered.items():
        rows = texts.get(src, "").splitlines()
        returns = [rows[i - 1].strip() for i in lines if 1 <= i <= len(rows)
                   and rows[i - 1].strip().startswith("return ")]
        pool = sorted(set(returns))
        for ln in lines:
            if not (1 <= ln <= len(rows)):
                continue
            line = rows[ln - 1]
            if not line.strip().startswith("return "):
                continue
            indent = line[: len(line) - len(line.lstrip())]
            for other in pool:
                if other == line.strip():
                    continue
                out.append({"family": "RETURN_NEAR", "file": src, "line": ln, "text_line": line,
                            "new": indent + other, "why": f"return already present in file: {other}"})
    return out


def apply_candidate(texts: dict[str, str], cand: dict[str, Any]) -> dict[str, str]:
    src = cand["file"]
    rows = texts[src].splitlines(True)
    idx = cand["line"] - 1
    if not (0 <= idx < len(rows)):
        return {}
    original = rows[idx]
    if cand["text_line"] not in original:
        return {}
    rows[idx] = original.replace(cand["text_line"], cand["new"], 1)
    return {src: "".join(rows)}


def build_pool(texts: dict[str, str], covered: dict[str, list[int]]) -> list[dict[str, Any]]:
    families = [token_candidates(covered, texts), guard_candidates(covered, texts),
                return_candidates(covered, texts)]
    pool: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rank in range(max((len(f) for f in families), default=0)):
        for family in families:
            if rank >= len(family):
                continue
            cand = family[rank]
            key = (cand["file"], cand["new"])
            if key in seen:
                continue
            seen.add(key)
            pool.append(cand)
            if len(pool) >= BUDGET:
                return pool
    return pool


def solve_task(task: dict[str, Any], plugin_dir: pathlib.Path) -> dict[str, Any]:
    root = SES.CHECKOUTS.get(task["repo"])
    if not root or not pathlib.Path(root).exists():
        return {"sha": task["sha"][:8], "status": "NO_CHECKOUT"}
    co = pathlib.Path(root)
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    if SES.git(co, "checkout", task["sha"], "--", task["test"]).returncode != 0:
        return {"sha": task["sha"][:8], "status": "TEST_NOT_APPLICABLE"}

    roots = SES.import_roots(task["source_files"], co)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(plugin_dir), *roots, str(co)]),
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}

    node = task["failed_nodes"][0]
    base = SES.run_pytest(co, env, node)
    if base.returncode == 0:
        return {"sha": task["sha"][:8], "status": "NOT_FAIL_TO_PASS"}
    frames = SES.traced_frames(base.stdout + base.stderr, task["source_files"])

    originals = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    hits = COV.run_with_coverage(co, env, node, list(originals), plugin_dir)
    merged: dict[str, set[int]] = {}
    for bucket in ("test_time", "import_time"):
        for src, lns in hits.get(bucket, {}).items():
            if src in originals:
                merged.setdefault(src, set()).update(lns)
    covered = {s: sorted(v) for s, v in merged.items()}
    if not covered:
        return {"sha": task["sha"][:8], "status": "NO_COVERAGE", "has_source_frame": bool(frames)}

    pool = build_pool(originals, covered)
    tried = 0
    for cand in pool:
        patched = apply_candidate(originals, cand)
        if not patched:
            continue
        for src, text in patched.items():
            (co / src).write_text(text, encoding="utf-8")
        tried += 1
        target = SES.run_pytest(co, env, node)
        ok = target.returncode == 0
        module_ok = False
        if ok:
            module_ok = SES.run_pytest(co, env, task["test"]).returncode == 0
        for src, text in originals.items():
            (co / src).write_text(text, encoding="utf-8")
        if ok and module_ok:
            SES.git(co, "checkout", "-q", "--force", task["parent"])
            SES.git(co, "clean", "-qfd")
            return {"sha": task["sha"][:8], "repo": task["repo"], "status": "SOLVED",
                    "family": cand["family"], "why": cand["why"], "candidates_screened": tried,
                    "has_source_frame": bool(frames), "covered": sum(len(v) for v in covered.values())}
        if ok and not module_ok:
            # target flipped but the module broke: recorded, never counted
            last_partial = {"family": cand["family"], "why": cand["why"]}

    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    return {"sha": task["sha"][:8], "repo": task["repo"], "status": "UNSOLVED",
            "candidates_screened": tried, "pool": len(pool), "has_source_frame": bool(frames),
            "covered": sum(len(v) for v in covered.values()),
            "target_flipped_module_broke": locals().get("last_partial")}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    started = time.time()
    plugin_dir = pathlib.Path("/tmp/brain_cover_plugin")

    tasks = json.loads(SES.CORPUS.read_text())["tasks"]
    rows = [solve_task(t, plugin_dir) for t in tasks]
    solved = [r for r in rows if r.get("status") == "SOLVED"]
    outcomes: dict[str, int] = {}
    for r in rows:
        outcomes[r.get("status", "?")] = outcomes.get(r.get("status", "?"), 0) + 1

    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "question": ("With a coverage pointer instead of a traceback frame, do site-local edits "
                     "recombining tokens already in the file solve real fail-to-pass tasks?"),
        "rule": ("A task is solved only when the target node flips AND the whole test module stays "
                 "green. Target-flips-but-module-breaks is recorded and never counted."),
        "budget_per_task": BUDGET,
        "tasks": len(rows),
        "solved": len(solved),
        "resolve_rate": round(len(solved) / len(rows), 3) if rows else None,
        "outcomes": outcomes,
        "solved_detail": solved,
        "rows": rows,
        "authority": "NONE -- development corpus, not a benchmark; no benchmark row claimed",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("tasks", "solved", "resolve_rate", "outcomes")}, indent=1))
    for s in solved:
        print("SOLVED", s["sha"], s["family"], s["why"][:70])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
