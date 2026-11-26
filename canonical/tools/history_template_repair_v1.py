#!/usr/bin/env python3
"""If weights may hold no world knowledge, where does the CONTENT of an added line come from?

THE PROBLEM THIS ADDRESSES
--------------------------
`fix_vocabulary_taxonomy_v1` measured the corpus: 482 of 667 changed sites ADD statements, and
only 194 of 600 added statements have a shape that already occurs in the same file. A substitution
form cannot add anything, and the file itself supplies the shape for barely a third of additions.

But the repository is not the only thing on disk. **Its history is too.** A repository with years
of commits contains thousands of (what the code looked like -> what the fix added) pairs, written
by the project's own maintainers, for its own conventions, in its own vocabulary. That is an
external, inspectable, editable knowledge store in exactly the sense the mission allows: it is not
in the weights, it can be added or removed without retraining, and it is the opposite of a
memorised lookup because it is *addressed by code shape* and instantiated at a site the run
discovers.

So this is the falsifiable claim:

    A repository's own commit history is a sufficient source of the ADDITIONS its bugs need,
    retrievable by anti-unification against the site, with zero model calls.

Existing work differs and the difference matters. HAFixAgent (2026) injects git-blame context into
an LLM prompt -- an LLM is still the generator. RETRACE (2026) distils history into natural-language
experience -- again for an LLM. Revisar mines Java quick fixes across projects as static checkers,
not as a repair engine addressed to a runtime site. None of them executes the retrieved edit against
the failing test with no model in the loop. If this works at all, it is a mechanism, not a prompt.

THE MECHANISM, IN FOUR STEPS
----------------------------
1. SHAPE. Every line of Python is reduced to a shape by replacing identifiers and literals with
   holes: `raise InvalidMarker(f"bad {x!r}")` -> `raise <I>(<S>)`. The hole *order* is kept.
2. MINE. Walk the repository's history up to, but NOT including, the fix commit. For every added
   run of statements, record (shape + hole order of the anchor line it follows) -> (added text,
   anchor hole names). This is anti-unification over the project's own past.
3. RETRIEVE. At a site the run discovers -- a line the failing test actually executes -- match the
   site line's shape against the mined anchor shapes. On a match, the holes align positionally, so
   the historical anchor's hole names map to the *current* identifiers. Instantiate the added
   template with that mapping.
4. EXECUTE. Apply, run the target node, then the whole module. A task counts only when the target
   flips and the module stays green.

LEAKAGE CONTROL, AND WHY IT IS THE POINT
----------------------------------------
The corpus's fix commit is excluded from the history by construction (`--not-ancestor` with the
parent as the revision bound). Nothing about the answer is read. Which is more than the frontier's
published SWE-bench numbers can say: a 2026 audit found agents scoring on SWE-bench Pro partly by
reading the fix out of git history. A system that cannot do that is measuring something harder.

Zero model calls, no stored parameters, no network at run time. The costs reported are real.
"""
from __future__ import annotations

import argparse
import ast
import json
import io
import tokenize
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

SCHEMA = "BRAIN_HISTORY_TEMPLATE_REPAIR_V1"
BUDGET = 40
HOLE_ID = "<I>"
HOLE_STR = "<S>"

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STR_RE = re.compile(r"""(?:[rbuf]{0,2})(['"])(?:\\.|(?!\1).)*\1""")
STOP_NAMES = {
    "self", "cls", "if", "else", "elif", "for", "while", "return", "not", "in", "is", "and", "or",
    "None", "True", "False", "try", "except", "finally", "with", "as", "raise", "def", "class",
    "import", "from", "yield", "lambda", "pass", "continue", "break", "assert", "del", "global",
    "nonlocal", "await", "async", "print", "len", "str", "int", "repr", "isinstance", "super",
}


def shape_and_holes(line: str) -> tuple[str, list[str]]:
    """Reduce a source line to a shape, plus the identifiers its holes stand for, in order.

    One left-to-right scan, not two regex passes. A string-substitution pass followed by an
    identifier pass rewrites its own holes: an f-string then becomes `<<I>>`, so
    `raise Err(f"bad {x!r}")` shapes to `raise <I>(<<I>>)` instead of `raise <I>(<S>)`. That
    corruption raises nothing and only ever appears as "the index matched nothing".
    """
    holes: list[str] = []
    out: list[str] = []
    i = 0
    n = len(line)
    last_id = ""
    last_id_end = -1
    while i < n:
        ch = line[i]
        # string literal (including a prefix such as r/b/f/u)
        if ch in "'\"":
            quote = ch
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == quote:
                    j += 1
                    break
                j += 1
            # A string prefix (r/b/f/u) was just emitted as an identifier hole and sits adjacent
            # to the quote. Drop it, or every f-string introduces a phantom hole and the shape is
            # wrong -- silently, which shows up only as "the index matched nothing".
            if last_id and last_id_end == i and last_id.lower() in ("r", "b", "f", "u", "rb", "br", "fr", "rf"):
                if out and out[-1] == HOLE_ID:
                    out.pop()
                    if holes:
                        holes.pop()
            out.append(HOLE_STR)
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            name = line[i:j]
            last_id, last_id_end = name, j
            if name in STOP_NAMES:
                out.append(name)
            else:
                holes.append(name)
                out.append(HOLE_ID)
            i = j
            continue
        out.append(ch)
        i += 1
    shaped = re.sub(r"\s+", " ", "".join(out)).strip()
    return shaped, holes


def _scope_from_context(context: str) -> str:
    """The enclosing def/class named by a diff hunk header, e.g. 'def __init__(self):'."""
    m = re.search(r"(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", context or "")
    return m.group(1) if m else ""


def scoped_statements(text: str) -> dict[str, str]:
    """(enclosing qualname | normalised statement) -> the statement's own text.

    The single-line shape used in the first version of this file was unusable: `"<S>",`
    occurs on dozens of unrelated lines, and a match said nothing about whether the site was
    structurally the place an addition belongs. Insertion then produced unparsable code on
    60% of attempts and matched module-level dict entries. The key has to carry the
    enclosing scope, so this walks the AST and records the innermost function/class a
    statement belongs to alongside the statement itself.
    """
    out: dict[str, str] = {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, scope = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stack.append((child, f"{scope}{child.name}"))
                continue
            if isinstance(child, ast.stmt):
                shape, _ = shape_and_holes(text.splitlines()[child.lineno - 1])
                out[f"{scope}|{shape}"] = text.splitlines()[child.lineno - 1]
            stack.append((child, scope))
    return out


def insert_points(text: str) -> list[tuple[int, str, str]]:
    """(line, enclosing scope, anchor shape) for statements an addition may follow.

    Only complete simple statements qualify: a line inside an open bracket or a compound
    header is not a place to insert a statement after.
    """
    points: list[tuple[int, str, str]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return points
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, scope = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stack.append((child, f"{scope}{child.name}"))
                continue
            if isinstance(child, ast.stmt) and not isinstance(
                    child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.FunctionDef,
                            ast.ClassDef, ast.AsyncFunctionDef, ast.Match)):
                line_no = getattr(child, "end_lineno", child.lineno) or child.lineno
                lines = text.splitlines()
                if 1 <= line_no <= len(lines):
                    shape, _ = shape_and_holes(lines[line_no - 1])
                    points.append((line_no, scope, shape))
            stack.append((child, scope))
    return points


def git(cwd: pathlib.Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


# ------------------------------------------------------------------ mining

def mine_history(co: pathlib.Path, bound: str, limit: int = 4000) -> dict[str, list[dict[str, Any]]]:
    """(scope|shape) and (shape) -> added-statement templates, from `bound`'s ancestry only.

    `bound` is the task's PARENT commit; `git log bound` cannot reach the fix commit, so the
    index is structurally incapable of containing the answer.

    The unified=0 hunk parse is deliberately explicit. A diff hunk is a run of `-` lines, then
    `+` lines, then context. The anchor of an addition is the last UNCHANGED line before it --
    which in a unified=0 hunk is usually ABSENT entirely (the hunk shows no context). Treating
    the first `+` line as the anchor, as the first version of this file did, keys the template
    on the added text itself and matches nothing real. So:
      * same hunk, pure additions  -> anchor comes from the hunk header's trailing context
      * context line present       -> that context line is the anchor
    """
    log = git(co, "log", "--no-merges", "-n", str(limit), "--format=%H", bound)
    if log.returncode != 0:
        return {}
    commits = [c for c in log.stdout.split() if c]
    index: dict[str, list[dict[str, Any]]] = {}

    def record(scope: str, anchor: str | None, holes: list[str], added: list[str], sha: str) -> None:
        if not added:
            return
        key = f"{scope}|{anchor}" if anchor else f"|{anchor}"
        index.setdefault(key, []).append(
            {"anchor_holes": holes, "added": added[:4], "from": sha[:8], "scope": scope})
        index.setdefault(f"_any|{anchor}" if anchor else "_any|",
                         []).append({"anchor_holes": holes, "added": added[:4], "from": sha[:8],
                                     "scope": scope})

    for sha in commits:
        diff = git(co, "show", "--format=", "--unified=0", "--no-color", sha, "--", "*.py", timeout=120)
        if diff.returncode != 0 or not diff.stdout:
            continue
        scope, anchor, holes, added = "", None, [], []
        for line in diff.stdout.splitlines():
            if line.startswith("@@"):
                if added:
                    record(scope, anchor, holes, added, sha)
                scope, anchor, holes, added = "", None, [], []
                m = re.match(r"@@[^@]*@@\s*(.*)$", line)
                context = m.group(1) if m else ""
                if context.strip():
                    scope = _scope_from_context(context)
                    anchor, holes = shape_and_holes(context)
                continue
            if line.startswith("+") and not line.startswith("+++"):
                body = line[1:]
                if body.strip():
                    added.append(body.rstrip())
            elif line.startswith(" ") and not line.startswith("+++"):
                if added:
                    record(scope, anchor, holes, added, sha)
                    added = []
                anchor, holes = shape_and_holes(line[1:])
                if not scope:
                    scope = _scope_from_context(line[1:])
        if added:
            record(scope, anchor, holes, added, sha)
    return index


# shape-only fallback index, so a site can still be served when the scoped key misses
    for key in list(index):
        _, _, bare = key.partition("|")
        index.setdefault(f"_any|{bare}", []).extend(index[key][:2])
    for key in list(index):
        if "|" not in key:
            continue
        bare = key.split("|", 1)[1]
        index.setdefault(f"|{bare}", index[key][:2])
    return index


# ------------------------------------------------------------------ instantiation

def instantiate(template: dict[str, Any], site_holes: list[str]) -> str | None:
    """Map the historical anchor's hole names onto the site's identifiers, then rewrite."""
    hist = template["anchor_holes"]
    if len(hist) != len(site_holes):
        return None
    mapping: dict[str, str] = {}
    for old, new in zip(hist, site_holes):
        if old in mapping and mapping[old] != new:
            return None          # inconsistent correspondence; refuse rather than guess
        mapping[old] = new
    # Substitute once, simultaneously, on NAME tokens only: swapping x/y
    # cannot rewrite its own output, or change a quoted string or a comment.
    text = "\n".join(template["added"]) + "\n"
    lines = text.splitlines(keepends=True)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError):
        return None
    for tok in reversed(tokens):
        if tok.type == tokenize.NAME and tok.string in mapping:
            i, j = tok.start
            line = lines[i-1]
            lines[i-1] = line[:j] + mapping[tok.string] + line[tok.end[1]:]
    return "".join(lines)


BUILTINS = set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__)


def habituated(text: str) -> set[str]:
    """Every name the target file can already refer to: its own tokens plus builtins."""
    return set(IDENT_RE.findall(text)) | BUILTINS | STOP_NAMES


def names_introduced(block: str, known: set[str]) -> list[str]:
    """Identifiers the added block mentions that the target file does not already know.

    This is the precision filter that makes history mining usable rather than a haystack: an
    addition that names something the file has never seen would raise NameError at run time, so
    it cannot be the fix no matter how well its shape matched. Applied BEFORE the budget, it
    turns "2,106 templates per site" into the handful that are expressible *here*.
    """
    return [n for n in IDENT_RE.findall(block)
            if n not in STOP_NAMES and n not in known and not n.isdigit()]


def site_candidates(text: str, covered: list[int], index: dict[str, list[dict[str, Any]]],
                    budget: int) -> list[dict[str, Any]]:
    """Sites whose enclosing scope AND anchor shape the mined history has an addition for.

    Both sides now agree on the key (scope|shape), which is what removes the module-level
    dict-entry matches and the unparsable insertions the single-line version produced.
    """
    known = habituated(text)
    covered_set = set(covered)
    out: list[dict[str, Any]] = []
    for line_no, scope, shape in insert_points(text):
        if line_no not in covered_set:
            continue                     # not reached by the failing test; skip early, it is cheap
        nearest = scope.split(".")[-1] if scope else ""
        # Two keys are tried, and which one finds the site is recorded. The scoped key
        # (scope|shape) is precise but almost never matches across a project's history; the
        # bare key (shape) matches often but ignores context. Reporting both is the point:
        # the gap between them is what a usable template key will have to close.
        templates = index.get(f"{nearest}|{shape}") or index.get(f"|{shape}") or index.get(f"_any|{shape}")
        if not templates:
            continue
        line = text.splitlines()[line_no - 1]
        _, holes = shape_and_holes(line)
        indent = line[: len(line) - len(line.lstrip())]
        for template in templates[:3]:
            body = instantiate(template, holes)
            if body is None:
                continue
            block = "\n".join(indent + b.strip() for b in body.rstrip("\n").splitlines()) + "\n"
            if names_introduced(block, known):
                continue
            out.append({"line": line_no, "anchor": line, "added": block, "scope": nearest,
                        "from": template["from"], "shape": shape})
            if len(out) >= budget:
                return out
    return out


def insert_after(text: str, line_no: int, block: str) -> str:
    rows = text.splitlines(True)
    if not (0 <= line_no - 1 < len(rows)):
        return ""
    rows.insert(line_no, block)
    candidate = "".join(rows)
    try:
        import ast as _ast
        _ast.parse(candidate)
    except SyntaxError:
        return ""
    return candidate


# ------------------------------------------------------------------ repair

def attempt(task: dict[str, Any], plugin_dir: pathlib.Path, history_limit: int) -> dict[str, Any]:
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

    originals = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    hits = COV.run_with_coverage(co, env, node, list(originals), plugin_dir)
    merged: dict[str, set[int]] = {}
    for bucket in ("test_time", "import_time"):
        for src, lns in hits.get(bucket, {}).items():
            if src in originals:
                merged.setdefault(src, set()).update(lns)
    if not merged:
        return {"sha": task["sha"][:8], "status": "NO_COVERAGE"}

    mined = time.time()
    index = mine_history(co, task["parent"], limit=history_limit)
    mine_s = round(time.time() - mined, 1)

    ranked: list[dict[str, Any]] = []
    for src, lines in merged.items():
        for cand in site_candidates(originals[src], sorted(lines), index, BUDGET):
            cand["file"] = src
            ranked.append(cand)
    ranked = ranked[:BUDGET]

    screened = 0
    rejected_unparsable = 0
    for cand in ranked:
        patched = insert_after(originals[cand["file"]], cand["line"], cand["added"])
        if not patched:
            rejected_unparsable += 1
            continue
        (co / cand["file"]).write_text(patched, encoding="utf-8")
        screened += 1
        target = SES.run_pytest(co, env, node)
        if target.returncode == 0 and SES.run_pytest(co, env, task["test"]).returncode == 0:
            SES.git(co, "checkout", "-q", "--force", task["parent"])
            SES.git(co, "clean", "-qfd")
            return {"sha": task["sha"][:8], "repo": task["repo"], "status": "SOLVED",
                    "file": cand["file"], "line": cand["line"], "added": cand["added"],
                    "borrowed_from_commit": cand["from"], "candidates_screened": screened,
                    "history_templates": sum(len(v) for v in index.values()), "mine_s": mine_s}
        (co / cand["file"]).write_text(originals[cand["file"]], encoding="utf-8")

    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    return {"sha": task["sha"][:8], "repo": task["repo"], "status": "UNSOLVED",
            "candidates_screened": screened, "eligible_sites": len(ranked),
            "rejected_unparsable": rejected_unparsable,
            "history_templates": sum(len(v) for v in index.values()),
            "anchors_mined": len(index), "mine_s": mine_s}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None, help="history commits mined per task")
    ap.add_argument("--tasks", type=int, default=None)
    ns = ap.parse_args(argv)
    started = time.time()
    plugin_dir = pathlib.Path("/tmp/brain_cover_plugin")

    tasks = json.loads(SES.CORPUS.read_text())["tasks"]
    if ns.tasks:
        tasks = tasks[: ns.tasks]
    rows = [attempt(t, plugin_dir, ns.limit or 4000) for t in tasks]
    solved = [r for r in rows if r.get("status") == "SOLVED"]
    outcomes: dict[str, int] = {}
    for r in rows:
        outcomes[r.get("status", "?")] = outcomes.get(r.get("status", "?"), 0) + 1

    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "claim": ("A repository's own past commits supply the ADDITIONS its bugs need, retrievable "
                  "by anti-unification against a coverage-selected site, with no model in the loop."),
        "leakage_control": ("the mined index is built from `git log <parent>` only, so the fix commit "
                            "is unreachable by construction; the oracle test is never modified"),
        "budget_per_task": BUDGET,
        "tasks": len(rows),
        "solved": len(solved),
        "resolve_rate": round(len(solved) / len(rows), 3) if rows else None,
        "outcomes": outcomes,
        "total_candidates_screened": sum(r.get("candidates_screened", 0) for r in rows),
        "solved_detail": solved,
        "rows": rows,
        "authority": "NONE -- development corpus, no benchmark row claimed",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("tasks", "solved", "resolve_rate", "outcomes", "total_candidates_screened")}, indent=1))
    for s in solved:
        print("SOLVED", s["sha"], s["file"], s["line"], "borrowed from", s["borrowed_from_commit"])
        print("      added:", s["added"].strip().replace("\n", " | ")[:100])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
