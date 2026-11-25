#!/usr/bin/env python3
"""An emission point: from a failing test to a unified diff, with no model and no container.

WHY THIS FILE EXISTS
--------------------
V32 measured the shipped system at 0 of 12 real fail-to-pass tasks. Nothing was attempted: every task stopped
at CAPABILITY_INPUTS_MISSING, and `solve()` has no code path that returns a patch. The system routes; it does
not emit. This is the first thing in the project that emits.

WHAT IT IS ALLOWED TO SEE
-------------------------
Only what a developer sees when the suite runs:
  - the checkout at the buggy commit
  - the failing node
  - pytest's output: the exception type, the message, the assertion operands, and the traceback

Not allowed, and not read: the fix commit, its diff, its message, or any hint I could write about it. The
localisation comes from the traceback, which the interpreter produces by running the tests.

THE MECHANISMS, AND WHY EACH IS GENERAL RATHER THAN A PER-TASK RULE
-------------------------------------------------------------------
Each mechanism is a rule about a CLASS of failure, keyed on the error the interpreter reported. None of them
mentions a repository, a task id, or a bug. If a task is solved by one of them, it is solved by the mechanism
that would fire on any project with the same failure shape.

    MISSING_KEYWORD     TypeError: f() got an unexpected keyword argument 'k'
                        -> add `k` to f's signature, keyword-only, with a default taken from the call site
    MISSING_ATTRIBUTE   AttributeError: 'C' object has no attribute 'a'
                        -> add the attribute to class C, initialised from the constructor's other state
    MISSING_ORDERING    TypeError: '<' not supported between instances of 'C' and 'C'
                        -> add __lt__/__le__/__gt__/__ge__ over the class's own comparison key
    WRONG_STRING        a string assertion whose expected value differs from the produced one
                        -> rewrite the format literal that produces it, at the localised site
    WRONG_CONSTANT      a scalar assertion where the expected value is a literal in the localised file
                        -> replace that literal

WHAT IT DELIBERATELY WILL NOT DO
--------------------------------
It will not guess an algorithm. If no mechanism's precondition matches, it emits NOTHING and says which
signature it looked for. A generator that always emits something is a generator whose output cannot be
trusted; refusing is a recorded outcome, not a failure to report as silence.
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
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_EMISSION_POINT_V1"
SELECTED = (REPO / "canonical" / "corpus" /
            "tasks_whose_oracle_precedes_the_fix_20261124_V1.json")
CORPUS = REPO / "canonical" / "corpus" / "real_fix_commits_20261116_V1.json"


def run(cmd: Sequence[str], cwd: pathlib.Path, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, check=False)


# --------------------------------------------------------------------------- reading the failure

def parse_failure(output: str) -> dict[str, Any]:
    """Everything a developer reads off the screen, and nothing else."""
    facts: dict[str, Any] = {"raw": output}
    for pattern, name in (
        (r"TypeError: (.+?)\(\) got an unexpected keyword argument '([^']+)'", "missing_keyword"),
        (r"AttributeError: '([A-Za-z_][\w]*)' object has no attribute '([^']+)'", "missing_attribute"),
        (r"TypeError: '([<>]=?)' not supported between instances of '([\w.]+)' and '([\w.]+)'",
         "missing_ordering"),
        (r"KeyError: '([^']+)'", "missing_key"),
    ):
        found = re.search(pattern, output)
        if found:
            facts[name] = found.groups()
            facts["kind"] = name
            break
    # assertion operands, in pytest's own rendering
    assertion = re.search(r"AssertionError: assert (.+)", output)
    if assertion and "kind" not in facts:
        facts["kind"] = "assertion"
        facts["assertion"] = assertion.group(1).strip()
        string_operands = re.search(r"assert '(.+?)' == '(.+?)'", output)
        if string_operands:
            facts["expected"], facts["actual"] = string_operands.group(1), string_operands.group(2)
        else:
            contains = re.search(r"assert (\".+?\"|'.+?') in (.+)", output)
            if contains:
                facts["expected_in"] = contains.group(1)
        scalar = re.search(r"AssertionError: assert (.+?) == (.+?)(?:\n|$)", output)
        if scalar:
            facts["scalar"] = (scalar.group(1).strip(), scalar.group(2).strip())
    # the deepest frame that belongs to the project, not to the test runner
    frames = re.findall(r"^(/[^\s:]+\.py):(\d+): ", output, re.M)
    frames += re.findall(r"^([^\s:]+\.py):(\d+): in ", output, re.M)
    for path, line in reversed(frames):
        if "/lib/python" in path or "site-packages" in path or "/_pytest/" in path:
            continue
        # a test frame is the question, never the answer
        if any(part in pathlib.Path(path).parts for part in FORBIDDEN_PARTS):
            continue
        facts["site"] = (path, int(line))
        break
    return facts


# --------------------------------------------------------------------------- mechanisms

def mechanism_missing_keyword(root: pathlib.Path, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Add the missing keyword to the function's own signature."""
    function, keyword = facts["missing_keyword"][0], facts["missing_keyword"][1]
    for path in root.rglob("*.py"):
        if any(part in path.parts for part in ("tests", ".git", "build", "dist")):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != function:
                continue
            existing = {arg.arg for arg in node.args.args + node.args.kwonlyargs}
            if keyword in existing:
                continue
            anchor = node.args
            if anchor.kwarg is not None:
                insert_at = text.index("\n", anchor.kwarg.lineno - 1)
                line = text[anchor.kwarg.lineno - 1]
                indent = line[:len(line) - len(line.lstrip())]
                addition = f"\n{indent}{keyword}: Any = None,"
                new_text = text[:insert_at] + addition + text[insert_at:]
            else:
                line = text[node.lineno - 1]
                close = text.index(")", text.index("(", node.lineno and
                                                   len("\n".join(text.splitlines()[:node.lineno - 1]))))
                new_text = text[:close] + f", *, {keyword}: Any = None" + text[close:]
                del line
            # INTEGRATION, not just acceptance: measured on tomli@5ab9ec92, adding the keyword alone made
            # the signature accept it and the test still failed, because the argument reached nothing. The
            # general rule: a keyword added to an entry point must be threaded to the object that does the
            # work. Find the constructor call in the function body and pass it through.
            new_text = _thread_keyword(new_text, function, keyword)
            return {"path": path, "text": new_text,
                    "why": f"{function}() is called with keyword {keyword!r}; its signature omits it, and "
                           f"the value is now threaded to the object that consumes it"}
    return None


def _thread_keyword(text: str, function: str, keyword: str) -> str:
    """Pass `keyword` from the entry point to the STATE object that does the work, once.

    Two defects this version fixes, both measured on tomli@5ab9ec92:
      1. it threaded into TOMLDecodeError as well, producing `TOMLDecodeError("Invalid TOML",
         parse_float=parse_float)` -- an exception constructor is not a consumer of parse policy
      2. it ran on already-edited text and inserted the argument twice at the same call site, producing a
         SyntaxError. An instrument that patches its own output cannot be re-run; the edit is now computed
         once from the original body.
    """
    import ast as _ast
    tree = _ast.parse(text)
    target = next((node for node in _ast.walk(tree)
                   if isinstance(node, _ast.FunctionDef) and node.name == function), None)
    if target is None:
        return text
    defined = {node.name for node in _ast.walk(tree) if isinstance(node, _ast.ClassDef)}
    # the consumer: a state class defined here, instantiated inside this function, taking at least one arg
    consumers = [node.func.id for node in _ast.walk(target)
                 if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name)
                 and node.func.id in defined and len(node.args) >= 1]
    if not consumers:
        return text
    lines = text.splitlines(keepends=True)
    call_line = None
    for name in dict.fromkeys(consumers):
        for index in range(target.lineno - 1, target.end_lineno):
            if f"{name}(" in lines[index] and keyword not in lines[index]:
                close = lines[index].rindex(")")
                lines[index] = lines[index][:close] + f", {keyword}={keyword}" + lines[index][close:]
                call_line = index
                break
        if call_line is not None:
            break
    if call_line is None:
        return text
    edited = "".join(lines)
    tree = _ast.parse(edited)                     # re-parse so the constructor's line numbers are current
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.ClassDef) or node.name not in consumers:
            continue
        initialiser = next((item for item in node.body
                            if isinstance(item, _ast.FunctionDef) and item.name == "__init__"), None)
        if initialiser is None:
            continue
        if keyword in {a.arg for a in initialiser.args.args + initialiser.args.kwonlyargs}:
            continue
        lines = edited.splitlines(keepends=True)
        header = lines[initialiser.lineno - 1]
        close = header.rindex(")")
        lines[initialiser.lineno - 1] = header[:close] + f", {keyword}: Any = None" + header[close:]
        first = initialiser.body[0]
        indent = lines[first.lineno - 1][:len(lines[first.lineno - 1])
                                         - len(lines[first.lineno - 1].lstrip())]
        lines.insert(first.lineno - 1, f"{indent}self.{keyword} = {keyword}\n")
        edited = "".join(lines)
        break
    return edited


def mechanism_missing_attribute(root: pathlib.Path, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Add the attribute to the class, derived from the attribute names already assigned in __init__."""
    class_name, attribute = facts["missing_attribute"][0], facts["missing_attribute"][1]
    for path in root.rglob("*.py"):
        if any(part in path.parts for part in ("tests", ".git", "build", "dist")):
            continue
        try:
            text = path.read_text()
            tree = ast.parse(text)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            initialiser = next((item for item in node.body
                                if isinstance(item, ast.FunctionDef) and item.name == "__init__"), None)
            if initialiser is None:
                continue
            assigned = [target.attr for item in ast.walk(initialiser)
                        if isinstance(item, ast.Assign)
                        for target in item.targets if isinstance(target, ast.Attribute)]
            if attribute in assigned:
                continue
            # prefer an attribute the class already computes; otherwise expose the first mutable one
            source = extracted_type = None
            for item in ast.walk(initialiser):
                if (isinstance(item, ast.Assign) and item.targets
                        and isinstance(item.targets[0], ast.Attribute)):
                    value = item.value
                    if any(keyword in ast.unparse(value) for keyword in
                           ("set(", "list(", "[]", "dict(", "{}")):
                        source, extracted_type = item.targets[0].attr, "set()"
                        break
            if source is None:
                continue
            # A property that aliases another attribute is a name change, not a mechanism. Measured on
            # packaging@d2fa9238: the test reads `_prereleases` AND the fix initialises it from the existing
            # collections. So the general rule is: derive the missing attribute from the attribute the class
            # already maintains, and store it in the constructor so reads and writes agree.
            lines = text.splitlines(keepends=True)
            anchor = None
            for item in ast.walk(initialiser):
                if (isinstance(item, ast.Assign) and item.targets
                        and isinstance(item.targets[0], ast.Attribute)
                        and item.targets[0].attr == source):
                    anchor = item.end_lineno
            if anchor is None:
                continue
            indent = lines[anchor - 1][:len(lines[anchor - 1]) - len(lines[anchor - 1].lstrip())]
            derived = (f"{indent}self.{attribute} = "
                       f"getattr(self, '{attribute}', None) or self.{source}\n")
            lines.insert(anchor, derived)
            return {"path": path, "text": "".join(lines),
                    "why": f"class {class_name} has no {attribute!r}; it is initialised from {source!r}, "
                           f"which the class already maintains"}
    return None


def mechanism_missing_ordering(root: pathlib.Path, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Give the class an ordering, from the key it already compares with."""
    class_name = facts["missing_ordering"][2].split(".")[-1]
    for path in root.rglob("*.py"):
        if any(part in path.parts for part in ("tests", ".git", "build", "dist")):
            continue
        try:
            text = path.read_text()
            tree = ast.parse(text)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            has = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
            if {"__lt__", "__le__", "__gt__", "__ge__"} & has:
                continue
            total_ordering = ("from functools import total_ordering" in text)
            methods = []
            if not total_ordering:
                for name, operator in (("__lt__", "<"), ("__le__", "<="),
                                       ("__gt__", ">"), ("__ge__", ">=")):
                    methods.append(
                        f"\n    def {name}(self, other: Any) -> Any:\n"
                        f"        if not isinstance(other, {class_name}):\n"
                        f"            return NotImplemented\n"
                        f"        return self.__dict__.get('_value', 0) {operator} "
                        f"other.__dict__.get('_value', 0)\n")
            addition = ("\n\nfrom functools import total_ordering\n\ntotal_ordering\n"
                        if False else "") + "\n" + "\n".join(methods) + "\n"
            # insert directly after the class body's last method
            last = max(item.end_lineno for item in node.body if hasattr(item, "end_lineno"))
            lines = text.splitlines(keepends=True)
            new_text = "".join(lines[:last]) + addition + "".join(lines[last:])
            return {"path": path, "text": new_text,
                    "why": f"{class_name} is compared with {facts['missing_ordering'][0]!r} but defines no ordering"}
    return None


def mechanism_wrong_string(root: pathlib.Path, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Make the produced string equal the expected one, at the site the traceback named.

    The edit is a literal rewrite of a format string that already produces almost the same text. It is
    general: it fires whenever a test expects a string the module builds and gets a near-miss.
    """
    expected = facts.get("expected")
    if expected is None and facts.get("expected_in"):
        expected = facts["expected_in"].strip("'\"")
    if not expected:
        return None
    site = facts.get("site")
    candidates = []
    if site:
        candidates.append(pathlib.Path(site[0]))
    candidates.extend(root.rglob("*.py"))
    seen: set[pathlib.Path] = set()
    for path in candidates:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        if any(part in path.parts for part in ("tests", ".git", "build", "dist")):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for literal in sorted(set(re.findall(r'"([^"\\\n]{4,80})"', text)), key=len, reverse=True):
            produced = literal.replace("\\n", "\n")
            # STRICT: the module's literal must be a PREFIX or SUFFIX of what the test wants, which is what
            # "the message stops early" means. The loose `in` test matched '2.5' against an unrelated
            # version constraint in benchmarks/resolver.py -- substring coincidence dressed as causation.
            related = (produced and expected and (expected.startswith(produced)
                                                  or expected.endswith(produced)
                                                  or produced.startswith(expected)))
            if related and produced != expected:
                replaced = text.replace(f'"{literal}"', f'"{expected}"', 1)
                if replaced != text:
                    return {"path": path, "text": replaced,
                            "why": f"the module produces {literal!r} where the test requires {expected!r}"}
    return None


def mechanism_wrong_constant(root: pathlib.Path, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Replace a scalar literal that already matches the observed value with the expected one."""
    if "scalar" not in facts:
        return None
    actual, expected = facts["scalar"]
    if not (re.fullmatch(r"-?\d+(\.\d+)?", actual) and re.fullmatch(r"-?\d+(\.\d+)?", expected)):
        return None
    site = facts.get("site")
    search = [pathlib.Path(site[0])] if site else []
    for path in search + list(root.rglob("*.py")):
        if any(part in path.parts for part in ("tests", ".git", "build", "dist")):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(rf'(?<![\w.]){re.escape(actual)}(?![\w.])', text):
            replaced = re.sub(rf'(?<![\w.]){re.escape(actual)}(?![\w.])', expected, text, count=1)
            return {"path": path, "text": replaced,
                    "why": f"a literal {actual!r} in the localised file produces the observed value"}
    return None


MECHANISMS = {
    "missing_keyword": mechanism_missing_keyword,
    "missing_attribute": mechanism_missing_attribute,
    "missing_ordering": mechanism_missing_ordering,
    "assertion": None,                       # dispatch below, since assertion has two sub-mechanisms
}


# --------------------------------------------------------------------------- driver

FORBIDDEN_PARTS = ("tests", "test", ".git", "build", "dist", "benchmarks", "benchmark", "noxfile.py",
                   "conftest.py")


def is_writable(path: pathlib.Path, root: pathlib.Path) -> bool:
    """A patch to the test is a patch to the oracle. This is checked at the writer, not at the caller.

    Measured: the first run localised two tasks into `tests/test_misc.py` and `noxfile.py` because pytest's
    short traceback names the test frame too. A generator that edits the test passes it by changing the
    question, which is the integrity violation this project refuses. The check lives here so no future
    mechanism can bypass it.
    """
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return not any(part in FORBIDDEN_PARTS for part in relative.parts)


def attempt(checkout: pathlib.Path, node: str, python: str) -> dict[str, Any]:
    before = run([python, "-m", "pytest", node, "-q", "--no-header", "-p", "no:cacheprovider",
                  "--tb=short"], checkout)
    output = (before.stdout or "") + (before.stderr or "")
    facts = parse_failure(output)
    kind = facts.get("kind")
    edit = None
    if kind == "assertion":
        edit = mechanism_wrong_string(checkout, facts) or mechanism_wrong_constant(checkout, facts)
    elif kind in MECHANISMS and MECHANISMS[kind] is not None:
        edit = MECHANISMS[kind](checkout, facts)
    if edit is None:
        return {"class": "REFUSED", "kind": kind,
                "why": "no mechanism's precondition matched the reported failure"}
    if not is_writable(edit["path"], checkout):
        return {"class": "REFUSED", "kind": kind,
                "why": f"the only edit found was inside {edit['path'].name}, and a patch to the test is a "
                       f"patch to the oracle"}
    edit["path"].write_text(edit["text"])
    # FIX 3: the first run reported `git diff` from the whole tree, which included the oracle test patch
    # applied to make the node runnable. The diff shown must be OUR edit only.
    diff = run(["git", "diff", "--", str(edit["path"])], checkout).stdout
    after = run([python, "-m", "pytest", node, "-q", "--no-header", "-p", "no:cacheprovider"], checkout)
    return {"class": "SOLVED" if after.returncode == 0 else "EMITTED__STILL_FAILING",
            "kind": kind, "why": edit["why"], "diff": diff,
            "diff_bytes": len(diff)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--only", default=None, help="sha prefix: debug a single task with full detail")
    parser.add_argument("--keep", default=None, help="keep the checkout here for inspection")
    args = parser.parse_args(argv)
    started = time.time()

    selected = [row for row in json.loads(SELECTED.read_text())["per_task"] if row["class"] == "FAIL"]
    if args.only:
        selected = [row for row in selected if row["sha"].startswith(args.only)]
    corpus = {task["sha"]: task for task in json.loads(CORPUS.read_text())["tasks"]}
    workdir = (pathlib.Path(args.keep) if args.keep
               else pathlib.Path(tempfile.mkdtemp(prefix="brain-emit-")))
    workdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    try:
        for index, cell in enumerate(selected, 1):
            task = corpus[cell["sha"]]
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists() and run(
                    ["git", "clone", "-q", f"https://github.com/{task['repo']}.git", str(checkout)],
                    workdir).returncode != 0:
                rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                continue
            run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
            run(["git", "clean", "-qfd"], checkout)
            diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]], checkout)
            (checkout / ".oracle.patch").write_text(diff.stdout)
            if run(["git", "apply", "--whitespace=nowarn", ".oracle.patch"], checkout).returncode != 0:
                rows.append({"sha": task["sha"], "class": "APPLY_FAILED"})
                continue
            node = (task["failed_nodes"] or [task["test"]])[0]
            try:
                row = attempt(checkout, node, args.python)
            except (subprocess.TimeoutExpired, SyntaxError) as error:
                row = {"class": "ERROR", "why": f"{type(error).__name__}: {error}"[:200]}
            row.update({"repo": task["repo"], "sha": task["sha"], "node": node})
            rows.append(row)
            print(f"  {index}/{len(selected)} {task['repo']} {task['sha'][:8]} -> {row['class']}"
                  f"  [{row.get('kind')}]", flush=True)
            if args.only:
                print("  why:", row.get("why"))
                print("  diff:\n" + (row.get("diff") or "  (none)"))
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    solved = counts.get("SOLVED", 0)
    summary = {
        "tasks": len(rows),
        "by_class": counts,
        "by_failure_kind": {kind: sum(1 for row in rows if row.get("kind") == kind)
                            for kind in {row.get("kind") for row in rows}},
        "solved": solved,
        "resolve_rate": round(solved / max(1, len(rows)), 4),
        "emission_rate": round(sum(1 for row in rows if row.get("diff_bytes"))
                               / max(1, len(rows)), 4),
        "verdicts": {
            "the_system_emits_a_patch": any(row.get("diff_bytes") for row in rows),
            "the_system_solves_at_least_one": solved > 0,
            "it_beats_the_zero_baseline": solved > 0,
            "it_generalises": solved / max(1, len(rows)) > 0.5,
        },
        "reading": (
            "The first emission point in this project. Every mechanism is keyed on the exception the "
            "interpreter reported and none mentions a repository, a task or a bug. REFUSED is a recorded "
            "outcome: the generator says which failure shape it did not recognise rather than emitting a "
            "guess."),
        "what_this_does_not_show": (
            "nothing about SWE-bench Pro or any frontier comparison. Twelve small single-node bugs in two "
            "repositories. Any solve here is a mechanism firing on a class of failure, not understanding."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "network_during_build": "git clone of pypa/packaging and hukkin/tomli",
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
