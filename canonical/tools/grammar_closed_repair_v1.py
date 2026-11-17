"""A repair generator with no edit library: the program's own grammar is the hypothesis space.

WHY THIS EXISTS
---------------
`WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1` measured the bottleneck on 40 real published bugs and did
not argue it: the tree's repair primitive enumerates a hand-written list (swap a comparison, swap a
binary operator, swap min/max or any/all, add a None guard, substitute a mined literal). `bitcount`'s
published fix is `n ^= n - 1` -> `n &= n - 1`; there is no `AugAssign` rule in that list, so the fix
is not hard to find, it is *unreachable* -- 280 candidates, 0 accepted, and no budget changes that.
A search cannot return a hypothesis its generators cannot build.

Meanwhile the tree's *induced* basis, taught on 20 bugs, repaired 1 of the other 20 -- a different
failure mode, not a better one: a template fires only where its precondition recurs, so 17 of 20
held-out bugs were refused outright.

Both mechanisms fail for the same reason: the hypothesis space is a finite list someone wrote down.
The measured distribution of real fixes (13 token / 22 expression / 5 statement, see
`quixbugs_required_edit_taxonomy_v1`) says a list will always be short somewhere.

THE MECHANISM HERE: NO LIST
---------------------------
The candidate set is generated from the program itself, at the failing site, and the corpus's own
test data is the fitness signal:

  1. LOCALIZE BY EXECUTION. Run the defective program on one failing example under a tracer and
     record which lines actually executed. Sites outside the executed set cannot affect this
     failure, so they are searched last (they are not deleted: a fix may need a statement the
     current code never reaches).
  2. THE ALPHABET IS THE PROGRAM. Atoms are the identifiers, parameters and numeric literals that
     appear in the function itself -- nothing is imported from a library of fixes.
  3. THE SHAPES ARE THE GRAMMAR. Any expression node may be replaced by: an atom; the node itself
     wrapped (`H + 1`, `max(0, H)`, `abs(H)`, `H[1:]`, `-H`, ...); a pairing of two atoms
     (`a + b`, `a - b`, `a * b`); or an operator swap *of any binary/comparison/augmented-assign
     node*, which is why `^=` -> `&=` is reachable here and was not before.
  4. THE ORACLE IS THE EXAMPLES, THEN THE CORPUS'S OWN TEST. Scoring uses the published input/output
     examples in-process (microseconds, so tens of thousands of candidates fit in a budget). The
     verdict is never the search's opinion: a winner is applied to a FRESH copy of the task and the
     corpus's own pytest file is run there.

No model, no network at run time, no learned parameter, no edit library. The "best part is no part":
what would have been a growing list of hand-written fixes is replaced by the program's own
vocabulary plus the goal.

WHAT THIS IS NOT
----------------
* Python only, single-function defects, one edit at a time. Multi-edit and cross-file repairs are
  outside this mechanism and are not claimed.
* A candidate that satisfies every published example is *not* proven correct (the oracle is the
  examples); that is why the corpus's own test is re-run rather than trusted.
* Enumerative search over a huge space is slow by construction; the budget is explicit and reported.

Authority NONE. Producer-run, one sandbox, not independent verification.

Usage
-----
    python3 canonical/tools/grammar_closed_repair_v1.py --quixbugs /path/to/QuixBugs \
        --out /tmp/grammar_closed.jsonl [--tasks pascal bucketsort] [--budget-s 60]
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator, Sequence

SCHEMA = "BRAIN_GRAMMAR_CLOSED_REPAIR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
ANSWER_KEY = "correct_python_programs"

#: The shapes a hole may take, written as templates over the node itself. They are a grammar, not a
#: list of fixes: none names a program, a variable, or a bug class.
HOLE_SHAPES = ("H", "H + 1", "H - 1", "H * 2", "H // 2", "H ** 2", "H % 2", "1 - H", "-H", "abs(H)",
               "len(H)", "H[0]", "H[1:]", "max(0, H)", "min(1, H)", "max(H, 0)", "min(H, 1)",
               "not H", "H == 0", "H != 0", "H and H", "H or H")
CALLABLE_SHAPES = ("len", "abs", "max", "min", "sorted", "sum", "int", "float")
#: Builtins are part of the language, not a list of fixes: a callee may be any builtin name.
BUILTIN_NAMES = ("all", "any", "len", "abs", "sum", "sorted", "min", "max", "int", "float", "round",
                 "reversed", "enumerate", "range", "zip", "list", "set", "tuple", "str", "bool")


class _Timeout(Exception):
    pass


def _on_alarm(signum, frame):  # noqa: ARG001
    raise _Timeout()


def _install_alarm() -> bool:
    try:
        signal.signal(signal.SIGALRM, _on_alarm)
        return True
    except (ValueError, AttributeError):  # not the main thread
        return False


# --------------------------------------------------------------------------------------------------
# task construction: what the solver may see
# --------------------------------------------------------------------------------------------------
def build_task(root: pathlib.Path, name: str, into: pathlib.Path) -> dict[str, Any]:
    """Defective programs + the corpus's own tests. The answer key never enters the directory."""
    shutil.copytree(root / "python_programs", into / "python_programs")
    (into / "python_testcases").mkdir(parents=True, exist_ok=True)
    test = root / "python_testcases" / f"test_{name}.py"
    shutil.copy2(test, into / "python_testcases" / test.name)
    loader = root / "python_testcases" / "load_testdata.py"
    if loader.is_file():
        shutil.copy2(loader, into / "python_testcases" / loader.name)
    # The corpus's test data is the specification, so it must reach the task. Only this task's data
    # is copied -- no other problem's examples, and never the answer key.
    data_dir = into / "json_testcases"
    data_dir.mkdir(parents=True, exist_ok=True)
    data = root / "json_testcases" / f"{name}.json"
    if data.is_file():
        shutil.copy2(data, data_dir / data.name)
    if (root / "conftest.py").is_file():
        shutil.copy2(root / "conftest.py", into / "conftest.py")
    if (into / ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    return {"test_path": f"python_testcases/test_{name}.py", "test_sha256": sha256(test),
            "program_sha256": sha256(root / "python_programs" / f"{name}.py"),
            "answer_key_in_task_dir": (into / ANSWER_KEY).exists()}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def examples_of(root: pathlib.Path, name: str) -> list[tuple[list[Any], Any]]:
    """The corpus's published input/output examples -- the same data its test file loads."""
    path = root / "json_testcases" / f"{name}.json"
    if not path.is_file():
        return []
    out: list[tuple[list[Any], Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        try:
            args, expected = json.loads(line)
        except ValueError:
            continue
        if isinstance(args, list):
            out.append((args, expected))
    return out


# --------------------------------------------------------------------------------------------------
# the generator
# --------------------------------------------------------------------------------------------------
def _paths(tree: ast.AST) -> Iterator[tuple[tuple[tuple[str, int | None], ...], ast.AST]]:
    """Every node with the path that reaches it, so a site survives re-parsing and re-building."""
    def walk(node: ast.AST, path: tuple[tuple[str, int | None], ...]):
        # Document order, so "the first site" in a report is the first site in the source.
        yield path, node
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        yield from walk(item, path + ((field, index),))
            elif isinstance(value, ast.AST):
                yield from walk(value, path + ((field, None),))

    yield from walk(tree, ())


def replace_at(tree: ast.AST, path: tuple[tuple[str, int | None], ...], replacement: ast.AST) -> ast.AST:
    new = copy.deepcopy(tree)
    node: Any = new
    for field, index in path[:-1]:
        node = getattr(node, field)
        if index is not None:
            node = node[index]
    field, index = path[-1]
    if index is None:
        setattr(node, field, replacement)
    else:
        getattr(node, field)[index] = replacement
    ast.fix_missing_locations(new)
    return new


def atoms_of(function: ast.AST) -> list[str]:
    """The alphabet: identifiers, parameters and small numeric literals of the function itself."""
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            names.add(repr(node.value))
    names.update({"0", "1", "2"})
    return sorted(n for n in names if n.isidentifier() or _is_number(n))


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def candidate_texts(node_src: str, atoms: Sequence[str]) -> list[str]:
    """Everything the grammar can put where this node is. Ordered cheap and local first."""
    texts = [hole.replace("H", f"({node_src})") for hole in HOLE_SHAPES]
    texts += list(atoms)
    small = list(atoms)[:8]
    for left in small:
        for right in small:
            if left != right:
                for op in ("+", "-", "*"):
                    texts.append(f"{left} {op} {right}")
    for name in small:
        for op in ("+", "-"):
            for literal in ("0", "1", "2"):
                texts.append(f"{name} {op} {literal}")
        # A comparison is part of the language, and leaving it out was a real hole: the fix for
        # `is_valid_parenthesization` is `return True` -> `return depth == 0`, which needs a
        # comparison over an ATOM, not over the node (`True == 0` is not the fix).
        for literal in ("0", "1"):
            for op in ("==", "!=", ">", "<", ">=", "<="):
                texts.append(f"{name} {op} {literal}")
        texts.append(f"not {name}")
    for callable_name in CALLABLE_SHAPES:
        for name in small:
            texts.append(f"{callable_name}({name})")
    seen: set[str] = set()
    ordered = []
    for text in texts:
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def operator_swaps(node: ast.AST) -> list[ast.AST]:
    """Swap the operator of ANY binary/comparison/augmented-assign node.

    This is the rung the hand-written list missed: `n ^= n - 1` -> `n &= n - 1` is a `BitXor` to
    `BitAnd` swap on an `AugAssign`, reachable here because the rule is "any operator node", not
    "the operators someone wrote down".
    """
    swaps: list[ast.AST] = []
    if isinstance(node, ast.BinOp):
        for kind in (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
                     ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift):
            if not isinstance(node.op, kind):
                swaps.append(kind())
    elif isinstance(node, ast.AugAssign):
        for kind in (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
                     ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift):
            if not isinstance(node.op, kind):
                swaps.append(kind())
    elif isinstance(node, ast.Compare):
        for kind in (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn):
            if not isinstance(node.ops[0], kind):
                swaps.append(kind())
    return swaps


def executed_lines(source: str, function_name: str, args: Sequence[Any],
                   timeout: float = 0.05) -> set[int]:
    """Which lines actually ran on a failing example. Sites outside this set cannot explain it."""
    lines: set[int] = set()
    namespace: dict[str, Any] = {}

    def tracer(frame, event, arg):  # noqa: ANN001
        if event == "line" and frame.f_code.co_filename == "<defective>":
            lines.add(frame.f_lineno)
        return tracer

    try:
        exec(compile(source, "<defective>", "exec"), namespace)  # noqa: S102 -- corpus code, sandboxed
        function = namespace.get(function_name)
        if function is None:
            return lines
        sys.settrace(tracer)
        try:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            function(*copy.deepcopy(args))
        except _Timeout:
            pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            sys.settrace(None)
    except Exception:  # noqa: BLE001 -- a crash is a perfectly good reason to have executed lines
        pass
    return lines


def score(source: str, function_name: str, examples: Sequence[tuple[list[Any], Any]],
          per_example_timeout: float) -> int:
    """How many of the published examples this candidate satisfies. -1 means it cannot even run."""
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<candidate>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return -1
    function = namespace.get(function_name)
    if function is None:
        return -1
    passed = 0
    for args, expected in examples:
        try:
            signal.setitimer(signal.ITIMER_REAL, per_example_timeout)
            got = function(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except _Timeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            return -1
        except Exception:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            return -1
        if not _equal(got, expected):
            return passed
        passed += 1
    return passed


def _equal(got: Any, expected: Any) -> bool:
    """The corpus's own tests use ==; floats are compared exactly, as it does."""
    try:
        return bool(got == expected)
    except Exception:  # noqa: BLE001
        return False


#: Rewrite forms: a hypothesis is a small rewrite of a REGION, not a value dropped at one node.
#: Each is instantiated from the node's own children and atoms, so nothing here names a program, a
#: variable or a bug class. These exist because the audit (`repair_space_audit_v1`) showed the
#: refusals clustering into four families the substitution space could not express: permutation,
#: composition of two edits at one site, shapes over an ATOM rather than over the node, and a
#: statement that must be inserted.
ATOM_SHAPES = ("not H", "len(H)", "H[1:]", "H[:-1]", "H[-1]", "H[0]", "abs(H)", "H + 1", "H - 1")
COMMUTATIVE = (ast.Add, ast.Mult, ast.BitAnd, ast.BitOr, ast.BitXor, ast.And, ast.Or)


def _permutations(items: list[ast.AST]) -> list[list[ast.AST]]:
    """All orderings of a call's arguments (bounded), excluding the identity."""
    import itertools

    if not 2 <= len(items) <= 3:
        return []
    seen = {ast.dump(i) for i in items}
    if len(seen) != len(items):
        return []  # identical arguments make a permutation meaningless (and noisy)
    out = []
    for order in itertools.permutations(range(len(items))):
        if list(order) == sorted(order):
            continue
        out.append([copy.deepcopy(items[i]) for i in order])
    return out


def _rewrites(tree: ast.AST, atoms: Sequence[str]) -> list[dict[str, Any]]:
    """Region rewrites, generated from the tree itself.

    Cheap by construction: a call with two arguments yields ONE permutation whatever the program's
    size, where the substitution family yields thousands of expressions at the same site -- so this
    family is both more expressive and easier to reach inside a budget.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(kind: str, site: str, replacement: str, lineno: int, patched: ast.AST) -> None:
        try:
            source = ast.unparse(patched)
            compile(source, "<candidate>", "exec")
        except Exception:  # noqa: BLE001
            return
        if source in seen:
            return
        seen.add(source)
        out.append({"kind": kind, "site": site, "replacement": replacement,
                    "lineno": lineno, "source": source})

    for path, node in _paths(tree):
        lineno = getattr(node, "lineno", 0)
        # 1. permutation: a call's arguments reordered (`gcd(a % b, b)` -> `gcd(b, a % b)`)
        if isinstance(node, ast.Call):
            for order in _permutations(node.args):
                patched = copy.deepcopy(tree)
                target: Any = patched
                for field, index in path:
                    target = getattr(target, field)
                    if index is not None:
                        target = target[index]
                target.args = order
                ast.fix_missing_locations(patched)
                add("PERMUTE", ast.unparse(node),
                    ",".join(ast.unparse(a) for a in order), lineno, patched)
        # 2. permutation: a non-commutative binary operation's operands swapped (`b - a` -> `a - b`)
        if isinstance(node, ast.BinOp) and not isinstance(node.op, COMMUTATIVE):
            patched = copy.deepcopy(tree)
            target = patched
            for field, index in path:
                target = getattr(target, field)
                if index is not None:
                    target = target[index]
            target.left, target.right = target.right, target.left
            ast.fix_missing_locations(patched)
            add("PERMUTE_OPERANDS", ast.unparse(node), "swapped", lineno, patched)
        # 3. shape over an atom: the substitution family only wraps the NODE, never an atom inside it,
        #    so `total < 0` could not become `not coins`.
        if isinstance(node, (ast.Name, ast.Attribute)):
            atom = ast.unparse(node)
            for shape in ATOM_SHAPES:
                try:
                    replacement = ast.parse(shape.replace("H", f"({atom})"), mode="eval").body
                except SyntaxError:
                    continue
                if ast.dump(replacement) == ast.dump(node):
                    continue
                add("ATOM_SHAPE", atom, shape.replace("H", atom), lineno, replace_at(tree, path, replacement))
        # 4. composition at one site: two edits where one statement must change in two places
        #    (`len(stack) + 0` -> `len(stack) == 0`).
        if isinstance(node, ast.BinOp):
            for shape in ("H == 0", "H != 0", "H > 0", "H < 0", "not H"):
                inner = ast.unparse(node.left)
                try:
                    replacement = ast.parse(shape.replace("H", f"({inner})"), mode="eval").body
                except SyntaxError:
                    continue
                add("COMPOSE", ast.unparse(node), shape.replace("H", inner), lineno,
                    replace_at(tree, path, replacement))
        # 5. statement insertion: a guard drawn from the atoms, in front of a statement inside a body.
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Return)):
            for atom in list(atoms)[:6]:
                if not atom.isidentifier():
                    continue
                try:
                    guard = ast.parse(f"if not {atom}:\n    return {atom}", mode="exec").body
                except SyntaxError:
                    continue
                patched = copy.deepcopy(tree)
                target = patched
                for field, index in path[:-1]:
                    target = getattr(target, field)
                    if index is not None:
                        target = target[index]
                field, index = path[-1]
                if index is None:
                    continue
                holder = getattr(target, field)
                if not isinstance(holder, list) or not isinstance(holder[index], ast.stmt):
                    continue
                holder.insert(index, guard[0])
                ast.fix_missing_locations(patched)
                add("INSERT_GUARD", ast.unparse(node), f"if not {atom}: return {atom}", lineno, patched)
    return out


def _site_key(node: ast.AST) -> int:
    return id(node)


def _operators_of(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, (ast.BinOp, ast.AugAssign)):
        return [ast.Add(), ast.Sub(), ast.Mult(), ast.Div(), ast.FloorDiv(), ast.Mod(), ast.Pow(),
                ast.BitAnd(), ast.BitOr(), ast.BitXor(), ast.LShift(), ast.RShift()]
    if isinstance(node, ast.UnaryOp):
        return [ast.USub(), ast.UAdd(), ast.Not(), ast.Invert()]
    if isinstance(node, ast.Compare):
        return [ast.Eq(), ast.NotEq(), ast.Lt(), ast.LtE(), ast.Gt(), ast.GtE(), ast.In(), ast.NotIn()]
    return []


def _set_operator(patched: ast.AST, path: tuple[tuple[str, int | None], ...], swap: ast.AST) -> ast.AST:
    """Rewrite the operator FIELD of the node at `path` -- never the node itself."""
    tree = copy.deepcopy(patched)
    node: Any = tree
    for field, index in path:
        node = getattr(node, field)
        if index is not None:
            node = node[index]
    if isinstance(swap, ast.cmpop) and getattr(node, "ops", None) is not None:
        node.ops = [swap] * len(node.ops)
    else:
        node.op = swap
    ast.fix_missing_locations(tree)
    return tree


def _enumerate(tree: ast.AST, atoms: Sequence[str]) -> list[dict[str, Any]]:
    """The whole hypothesis space, materialised and labelled.

    Two families, both generated from the program rather than from a list of known fixes:
      REPLACE  an expression node becomes any expression the grammar can build from the program's
               own atoms, with the node itself as the hole;
      OPERATOR any binary/unary/comparison/augmented operator becomes any other operator of its
               class -- which is the rung the hand-written list could not reach (`^=` -> `&=`).
    """
    out: list[dict[str, Any]] = _rewrites(tree, atoms)
    seen: set[str] = {c["source"] for c in out}
    for path, node in _paths(tree):
        # A store target (`count` in `count += 1`) cannot be replaced by an expression: doing so
        # yields `count + 1 += 1`, which does not parse. Such a site is not a hypothesis.
        store_target = isinstance(node, ast.expr) and isinstance(getattr(node, "ctx", None), ast.Store)
        if isinstance(node, ast.expr) and not store_target:
            node_src = ast.unparse(node)
            attempts: list[tuple[str, ast.AST]] = []
            for text in candidate_texts(node_src, atoms):
                try:
                    attempts.append((text, ast.parse(text, mode="eval").body))
                except SyntaxError:
                    continue
            if isinstance(node, ast.Name):
                # a callee or value may be any builtin, whether or not the program mentions it
                for builtin_name in BUILTIN_NAMES:
                    if builtin_name != node.id:
                        attempts.append((builtin_name, ast.Name(id=builtin_name, ctx=ast.Load())))
            for text, attempt in attempts:
                try:
                    source = ast.unparse(replace_at(tree, path, attempt))
                    # A candidate is only a hypothesis if it is a program. Unparse can emit text
                    # that does not compile (a rewrapped augmented-assignment target, for one);
                    # such a candidate is dropped here rather than wasting an execution later.
                    compile(source, "<candidate>", "exec")
                except Exception:  # noqa: BLE001
                    continue
                if source in seen:
                    continue
                seen.add(source)
                out.append({"kind": "REPLACE", "site": node_src, "replacement": text,
                            "lineno": getattr(node, "lineno", 0), "source": source})
        for swap in _operators_of(node):
            try:
                source = ast.unparse(_set_operator(tree, path, swap))
                compile(source, "<candidate>", "exec")
            except Exception:  # noqa: BLE001
                continue
            if source in seen:
                continue
            seen.add(source)
            out.append({"kind": "OPERATOR", "site": ast.unparse(node),
                        "replacement": type(swap).__name__,
                        "lineno": getattr(node, "lineno", 0), "source": source})
    return out


def verify_with_corpus_test(where: pathlib.Path, test_path: str, timeout: int) -> dict[str, Any]:
    """The only verdict that counts: the corpus's own pytest file, on a fresh copy.

    QuixBugs tests do ``from node import Node`` / ``from load_testdata import ...``;
    those modules live under ``python_programs/`` and ``python_testcases/``. Without
    those roots on PYTHONPATH the suite dies at collection (rc 2) and a correct
    patch is misreported as failed. Same three roots as
    ``counterfactual_repair_quixbugs_measure_v1.corpus_pytest``.
    """
    env = dict(os.environ)
    roots = [str(where), str(where / "python_programs"), str(where / "python_testcases")]
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(roots + ([prior] if prior else []))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.time()
    try:
        done = subprocess.run([sys.executable, "-m", "pytest", test_path, "-q", "-p", "no:cacheprovider"],
                              cwd=str(where), capture_output=True, text=True, timeout=timeout, env=env)
        return {"returncode": done.returncode, "timed_out": False,
                "tail": (done.stdout + done.stderr).strip().splitlines()[-2:],
                "seconds": round(time.time() - started, 1)}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "timed_out": True, "tail": ["TIMEOUT"],
                "seconds": round(time.time() - started, 1)}


def repair_task(root: pathlib.Path, name: str, *, budget_s: float, per_example_timeout: float,
                verify_timeout: int) -> dict[str, Any]:
    """One published bug, start to finish."""
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task"}
    examples = examples_of(root, name)
    row["examples"] = len(examples)
    if not examples:
        row["stage"] = "NO_EXAMPLES"
        return row
    source = (root / "python_programs" / f"{name}.py").read_text()
    row["program_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["stage"] = "NO_FUNCTION"
        return row
    row["function"] = function.name
    row["model_dependency_count"] = 0
    row["external_capability_provider_count"] = 0
    row["network_calls"] = 0

    if not _install_alarm():
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row
    baseline = score(source, function.name, examples, per_example_timeout)
    row["baseline_examples_passed"] = baseline
    row["baseline_examples_total"] = len(examples)
    if baseline == len(examples):
        row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
        return row

    # 1. localize by execution: the lines that actually ran on a failing example cannot be found
    #    from `baseline`, so trace the first example whose value the program gets wrong.
    warm_lines: set[int] = set()
    for args, _expected in examples:
        warm_lines |= executed_lines(source, function.name, args, per_example_timeout)
    atoms = atoms_of(function)
    row["atoms"] = len(atoms)

    candidates = _enumerate(tree, atoms)
    row["candidate_space_size"] = len(candidates)
    if not candidates:
        row["stage"] = "NO_CANDIDATE_SPACE"
        return row

    warm_set = {_site_key(node) for node in candidates if node["lineno"] in warm_lines}
    ordered = [c for c in candidates if c["lineno"] in warm_lines] + \
              [c for c in candidates if c["lineno"] not in warm_lines]
    row["sites_executed"] = len(warm_set)
    row["sites_unexecuted"] = len(ordered) - len(warm_set)

    tested = 0
    best_score = baseline
    best: dict[str, Any] | None = None
    for index, candidate in enumerate(ordered):
        if time.time() - started > budget_s:
            row["search_exhausted_by_budget"] = True
            break
        tested += 1
        got = score(candidate["source"], function.name, examples, per_example_timeout)
        if got > best_score:
            best_score = got
            best = candidate
        if got == len(examples):
            break
    row["candidates_tested"] = tested
    # A two- and three-move composition pass was built and measured here and repaired ZERO
    # additional tasks on this corpus, so it was removed rather than shipped -- the "best part
    # is no part" applies to a part that pays nothing. The finding is recorded in
    # COMPOSITION_DOES_NOT_PAY_UNTIL_THE_FAMILIES_DO_20261116_V1: what the refusals need is
    # families, not depth.
    row["best_examples_passed"] = best_score
    row["best_of"] = len(examples)
    if not best:
        row["stage"] = "NOT_REPAIRED__NO_IMPROVING_CANDIDATE"
        row["seconds"] = round(time.time() - started, 1)
        return row
    row["edit"] = {"site": best["site"], "replacement": best["replacement"],
                   "kind": best["kind"]}
    if best_score != len(examples):
        row["stage"] = "NOT_REPAIRED__PARTIAL_EXAMPLES_ONLY"
        row["seconds"] = round(time.time() - started, 1)
        return row

    # 2. the verdict: apply to a FRESH copy, run the corpus's own test file there.
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp) / name
        row.update(build_task(root, name, where))
        (where / "python_programs" / f"{name}.py").write_text(best["source"] + "\n")
        verdict = verify_with_corpus_test(where, f"python_testcases/test_{name}.py", verify_timeout)
    if verdict["returncode"] == 0:
        # the artifact the judge accepted, carried in the record so a later arm can learn from the
        # verified program rather than from a description of it
        row["patched"] = best["source"] + "\n"
    row["corpus_test"] = verdict
    row["stage"] = "REPAIRED__CORPUS_TEST_PASSES" if verdict["returncode"] == 0 \
        else "NOT_REPAIRED__CORPUS_TEST_STILL_FAILS"
    row["seconds"] = round(time.time() - started, 1)
    return row


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stages: dict[str, list[str]] = {}
    for row in rows:
        stages.setdefault(str(row.get("stage")), []).append(str(row["task"]))
    repaired = sorted(stages.get("REPAIRED__CORPUS_TEST_PASSES", []))
    return {"tasks": len(rows), "repaired": len(repaired), "repaired_tasks": repaired,
            "candidates_tested": sum(int(r.get("candidates_tested") or 0) for r in rows),
            "by_stage": {k: {"count": len(v), "tasks": sorted(v)} for k, v in sorted(stages.items())},
            "seconds_total": round(sum(float(r.get("seconds") or 0) for r in rows), 1)}


def _builtins_in(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} & set(BUILTIN_NAMES)


def classify_repair(row: dict[str, Any], corpus_root: pathlib.Path | None) -> dict[str, Any]:
    """Is a passing patch a repair, or a rewrite that happens to satisfy the oracle?

    The corpus test says pass or fail and cannot tell the two apart -- which is the synthesis/
    verification asymmetry in miniature. The only mechanical signal available here is whether the
    patch reaches for a builtin the program never used: replacing a sort's bookkeeping with
    `sorted(arr)` passes the test without repairing anything. That is reported as a plausible
    rewrite, never counted as a repair, and it reads the corpus source only to compare names.
    """
    edit = row.get("edit") or {}
    replacement = str(edit.get("replacement") or "")
    if not replacement:
        return {"verdict": "NO_EDIT_RECORDED"}
    used = _builtins_in(replacement)
    if corpus_root is None:
        return {"verdict": "UNCLASSIFIED__NO_CORPUS", "builtins_in_replacement": sorted(used)}
    original_path = corpus_root / "python_programs" / f"{row['task']}.py"
    if not original_path.is_file():
        return {"verdict": "UNCLASSIFIED__NO_SOURCE", "builtins_in_replacement": sorted(used)}
    original = _builtins_in(original_path.read_text())
    introduced = sorted(used - original)
    if introduced:
        return {"verdict": "PLAUSIBLE_REWRITE__BUILTIN_NOT_IN_PROGRAM", "introduced": introduced}
    return {"verdict": "LOCAL_EDIT"}


def consolidate(jsonl_path: str, receipt_path: str,
                corpus_root: pathlib.Path | None = None) -> dict[str, Any]:
    """Fold raw rows into a receipt. Every number is computed from the rows; nothing is typed."""
    rows: list[dict[str, Any]] = []
    header: dict[str, Any] | None = None
    for line in pathlib.Path(jsonl_path).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("kind") == "header":
            header = header or row
            continue
        rows.append(row)
    summary = summarise(rows)
    by_edit_kind: dict[str, int] = {}
    classifications: dict[str, Any] = {}
    for row in rows:
        if row.get("stage") == "REPAIRED__CORPUS_TEST_PASSES":
            kind = str((row.get("edit") or {}).get("kind"))
            by_edit_kind[kind] = by_edit_kind.get(kind, 0) + 1
            classifications[str(row["task"])] = classify_repair(row, corpus_root)
    local_edits = sorted(t for t, c in classifications.items() if c["verdict"] == "LOCAL_EDIT")
    plausible = sorted(t for t, c in classifications.items()
                       if c["verdict"].startswith("PLAUSIBLE_REWRITE"))
    receipt = {
        "schema": "BRAIN_GRAMMAR_CLOSED_REPAIR_RECEIPT_V1",
        "authority": AUTHORITY,
        "corpus": {"upstream": UPSTREAM, "source_present": True},
        "header": header,
        "measured_tasks": len(rows),
        "repaired": summary["repaired"],
        "repaired_tasks": summary["repaired_tasks"],
        "repaired_by_edit_kind": dict(sorted(by_edit_kind.items())),
        "repairs_that_are_local_edits": local_edits,
        "repairs_that_are_plausible_rewrites": plausible,
        "repair_classification": classifications,
        "candidates_tested": summary["candidates_tested"],
        "by_stage": summary["by_stage"],
        "seconds_total": summary["seconds_total"],
        "reading": ("A repaired task means the corpus's own pytest file passed on a FRESH copy of the "
                    "task with the candidate applied, the answer key absent from the task directory, "
                    "and no model, network or learned parameter in the loop. NO_EXAMPLES means the "
                    "corpus specifies the task by constructing objects inline and asserting a bare "
                    "boolean, so no input/output example exists to search against: one bit per test "
                    "cannot direct a search, and that is reported as unmeasurable rather than as a "
                    "failure or a success."),
        "hard_nonclaims": ["NOT_A_FRONTIER_SCORE", "NOT_SWE_BENCH", "SINGLE_EDIT_ONLY",
                           "PYTHON_ONLY", "NO_MULTI_EDIT_OR_CROSS_FILE_REPAIR",
                           "EXAMPLES_ARE_NOT_A_PROOF_OF_CORRECTNESS",
                           "PRODUCER_RUN_NOT_INDEPENDENT_VERIFICATION"],
    }
    pathlib.Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", default=None, help="required unless --consolidate is used")
    parser.add_argument("--consolidate", default=None, metavar="JSONL", help="fold a run into a receipt")
    parser.add_argument("--receipt", default=None, help="where to write the consolidated receipt")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--budget-s", type=float, default=60.0, help="search budget per task")
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)
    if args.consolidate:
        receipt = consolidate(args.consolidate, args.receipt or args.out,
                              pathlib.Path(args.quixbugs).resolve() if args.quixbugs else None)
        print(json.dumps({k: receipt[k] for k in ("measured_tasks", "repaired", "repaired_tasks",
                                                  "repairs_that_are_local_edits",
                                                  "repairs_that_are_plausible_rewrites",
                                                  "candidates_tested")}, indent=1))
        return 0
    if not args.quixbugs:
        parser.error("--quixbugs is required unless --consolidate is used")
    root = pathlib.Path(args.quixbugs).resolve()
    names = args.tasks or sorted(p.name[len("test_"):-len(".py")]
                                for p in (root / "python_testcases").glob("test_*.py"))
    header = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "header", "upstream": UPSTREAM,
              "tasks_planned": names, "budget_s": args.budget_s,
              "answer_key_present_at_source": (root / ANSWER_KEY).exists(),
              "python": sys.version.split()[0],
              "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "model_dependency_count": 0, "incremental_spend_usd": 0,
              "network_calls_during_measurement": 0}
    with open(args.out, "a") as handle:
        handle.write(json.dumps(header) + "\n")
        for name in names:
            try:
                row = repair_task(root, name, budget_s=args.budget_s,
                                  per_example_timeout=args.per_example_timeout,
                                  verify_timeout=args.verify_timeout)
            except Exception as error:  # noqa: BLE001 -- one task must not take the others with it
                row = {"task": name, "kind": "task", "stage": "TASK_RAISED",
                       "detail": f"{type(error).__name__}: {error}"[:300]}
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            handle.flush()
            print(f"{name:<26} {str(row.get('stage')):<44} cands={row.get('candidates_tested')} "
                  f"ex={row.get('best_examples_passed')}/{row.get('best_of')} {row.get('seconds')}s",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
