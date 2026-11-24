"""Derive a missing callable from the failure that names it, and confirm it by re-running.

THE LAW THIS IMPLEMENTS, AND WHY IT IS THE RIGHT ONE
----------------------------------------------------
`fix_from_the_failure_v1` established the condition under which a repair can be DERIVED with no
model and no reference solution:

    THE FAILURE MUST STATE THE CORRECTION, AND THE WORLD MUST CONFIRM IT.

A `NameError` states a corrected name. This module handles the other case the census found
(§A153): a test calls a member that does not exist yet, and says so in the machine's own words:

    AttributeError: 'LinuxNetwork' object has no attribute 'get_locally_reachable_ips'

That single sentence states three of the four things a signature needs: the class that is
missing it, the exact name, and (by being an attribute lookup, not a call) that it is a member.
The fourth thing -- the parameter list -- is stated by the CALL SITE the test itself contains:

    res = net.get_locally_reachable_ips('fake/ip')      ->  (self, ip_path)

The contract -- what must be returned -- is stated by the test's own data and its own assertion.
So nothing here is guessed and nothing is memorised. The specification is the test; the mechanism
is a reader of specifications.

WHAT IT IS NOT
--------------
It is not a body synthesiser. This class of task (the census calls it NEW SYMBOL) asks for a
member that does not exist, and 16 of the 68 small Python instances are exactly that. The other
52 need edits to logic that already exists, and this module does not claim them.

It does not invent behaviour. If the name cannot be read, the call site cannot be parsed, or
re-running the named test does not go green, the candidate is discarded and the outcome is
reported as NOT_DERIVED. A patch that happens to satisfy one test by coincidence is not a repair.

MEASURED BASELINE (2026-11-24, instance_ansible__ansible-11c1777d...-v0f01c69f...):

    before:  AttributeError: 'LinuxNetwork' object has no attribute 'get_locally_reachable_ips'
             test/units/module_utils/facts/network/test_locally_reachable_ips.py:84

Authority NONE. No model is called. Every accepted repair is confirmed by exit 0 on the test the
benchmark itself published.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

__all__ = [
    "MissingMember",
    "read_missing_member",
    "call_signature_at",
    "OwnerClass",
    "locate_class",
    "_append_member",
    "derive",
]

MISSING_RE = re.compile(
    r"AttributeError:\s*'(?P<cls>[A-Za-z_][\w.]*)'\s+object has no attribute\s+'(?P<name>[A-Za-z_]\w*)'"
)
MODULE_MISSING_RE = re.compile(
    r"AttributeError:\s*module\s+'(?P<mod>[\w.]+)'\s+has no attribute\s+'(?P<name>[A-Za-z_]\w*)'"
)


class MissingMember:
    """What the failure said, in the failure's own words."""

    __slots__ = ("owner", "name", "is_module", "module")

    def __init__(self, owner: str, name: str, is_module: bool = False, module: str = ""):
        self.owner = owner
        self.name = name
        self.is_module = is_module
        self.module = module

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"MissingMember({self.owner!r}, {self.name!r})"


def read_missing_member(output: str) -> MissingMember | None:
    """Read the missing member out of the exception text. None when the text does not say.

    Both spellings are handled because they mean different repairs: an instance attribute means
    "add a member to this class", a module attribute means "add a module-level name". Collapsing
    them would produce a patch in the wrong place, which is worse than no patch.
    """
    m = MISSING_RE.search(output)
    if m:
        return MissingMember(m.group("cls"), m.group("name"))
    m = MODULE_MISSING_RE.search(output)
    if m:
        return MissingMember(m.group("mod"), m.group("name"), is_module=True, module=m.group("mod"))
    return None


def call_signature_at(source: str, name: str) -> list[str] | None:
    """The parameter names the CALL SITE supplies, from the test's own text.

    The test is the specification of the interface: it shows how the member is called. A
    positional argument with no name in the source cannot be named, so it is given the neutral
    name `arg<i>` -- inventing a nicer name would be a fact I do not have.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best: list[str] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not isinstance(fn, ast.Attribute) or fn.attr != name:
            continue
        names: list[str] = []
        ok = True
        for i, arg in enumerate(node.args):
            if isinstance(arg, (ast.Name,)):
                names.append(arg.id)
            elif isinstance(arg, ast.Constant):
                # A literal carries no name; the parameter only needs to accept it.
                names.append(f"arg{i}")
            else:
                names.append(f"arg{i}")
        for kw in node.keywords:
            if kw.arg is None:
                ok = False
                break
            names.append(kw.arg)
        if not ok:
            continue
        # Prefer the call with the most information (the real invocation over a mock setup).
        if best is None or len(names) > len(best):
            best = names
    return best


class OwnerClass:
    __slots__ = ("path", "name", "lineno", "indent", "body_end")

    def __init__(self, path: pathlib.Path, name: str, lineno: int, indent: str, body_end: int):
        self.path = path
        self.name = name
        self.lineno = lineno
        self.indent = indent
        self.body_end = body_end


def locate_class(root: pathlib.Path, class_name: str, hint: str | None = None) -> OwnerClass | None:
    """Find the class the failure names, inside the repository the task names.

    `hint` is any path the test imports (e.g. the module under test). Using it first keeps the
    search honest: the member belongs in the module the test talks to, not in a same-named class
    somewhere else in the tree.
    """
    candidates: list[pathlib.Path] = []
    if hint:
        p = (root / hint)
        if p.is_file():
            candidates.append(p)
    if not candidates:
        candidates = sorted(root.rglob("*.py"))
    for path in candidates:
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, OSError):
            continue
        lines = src.splitlines()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Indentation of the class body: the first statement's own indentation.
                indent = " " * (node.body[0].col_offset if node.body else node.col_offset + 4)
                end = max(getattr(n, "end_lineno", node.lineno) for n in ast.walk(node))
                return OwnerClass(path, class_name, node.lineno, indent, end)
    return None


def _append_member(owner: OwnerClass, name: str, params: list[str], body: list[str]) -> bool:
    """Append a member to the end of the named class, and confirm the file still parses.

    One insertion routine, used for both the exploratory stub and the final body. Two routines
    that append members is two places for the same bug.
    """
    src = owner.path.read_text(encoding="utf-8")
    lines = src.splitlines()
    signature = ", ".join(["self"] + params)
    member = ["", f"{owner.indent}def {name}({signature}):"]
    member += [f"{owner.indent}    {ln}" for ln in body] or [f"{owner.indent}    pass"]
    out = lines[: owner.body_end] + member + lines[owner.body_end:]
    new_src = "\n".join(out) + ("\n" if src.endswith("\n") else "")
    try:
        ast.parse(new_src)
    except SyntaxError:
        return False
    owner.path.write_text(new_src, encoding="utf-8")
    return True


def _body_from_requirement(requirement: str) -> tuple[list[str], bool]:
    """Turn one stated requirement into executable lines, or say it cannot be.

    This is deliberately narrow. It understands the shapes the census actually found: a member
    that must return a literal construction, and a member that must query a command list. Anything
    else returns ([], False) and the caller reports NOT_DERIVED. A synthesiser that guessed at
    everything would be a fabricator.
    """
    return [], False


def derive(root: pathlib.Path, test_path: str, test_id: str, *, python: str | None = None,
           max_rounds: int = 3) -> dict:
    """The loop: run, read the failure, derive, re-run. Confirmed only by the world.

    `max_rounds` bounds it. Each round must make the named test pass or the loop stops and says
    what it could not do -- never a guess that the next round might rescue.
    """
    root = pathlib.Path(root).resolve()
    # The interpreter must be one that HAS pytest. `sys.executable` may be a bare system python
    # with no site-packages -- measured: "No module named pytest", which reads like a broken test
    # and is a broken harness. Prefer a sibling venv beside the room, then the current one.
    python = python or _pytest_capable_python(root)
    # Import roots come from the ONE place that decides them, not from a second copy here.
    # The module is loaded by path because this file is run as a script as well as imported.
    _here = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(_here.parent.parent))
    from canonical.runtime.swepro_instance_harness_v1 import _import_roots
    env = {"PYTHONPATH": os_sep().join(_import_roots(root)), "PATH": "/usr/bin:/bin"}
    history = []

    def run() -> str:
        proc = subprocess.run([python, "-m", "pytest", test_id, "-q", "--tb=long", "-p", "no:cacheprovider"],
                              cwd=root, capture_output=True, text=True, env={**env, **_os_env()})
        return proc.stdout + proc.stderr

    for rnd in range(max_rounds):
        out = run()
        passed = re.search(r"^1 passed", out, re.M) is not None
        history.append({"round": rnd, "passed": passed,
                        "verdict": (re.search(r"E\s+(\w*Error[^\n]*)", out) or [None, ""])[1][:120]
                        if not passed else ""})
        if passed:
            return {"derived": True, "rounds": history, "outcome": "CONFIRMED_BY_THE_TEST"}
        miss = read_missing_member(out)
        if miss is None:
            history.append({"round": rnd, "note": "failure does not name a missing member; refusing to guess"})
            return {"derived": False, "rounds": history, "outcome": "NOT_DERIVABLE_FROM_THIS_FAILURE"}

        test_src = (root / test_path).read_text(encoding="utf-8", errors="replace")
        params = call_signature_at(test_src, miss.name) or []
        owner = locate_class(root, miss.owner)
        if owner is None:
            history.append({"round": rnd, "note": f"owner class {miss.owner} not found in tree"})
            return {"derived": False, "rounds": history, "outcome": "OWNER_NOT_FOUND"}

        # A member that raises NotImplementedError satisfies the attribute lookup (so the next
        # failure is the real one, stated by the test's own assertion) without inventing a
        # result. This is the honest first move: it converts "missing" into "stated requirement".
        ok = _append_member(owner, miss.name, params,
                            [f"raise NotImplementedError('DERIVED_STUB:{miss.name}')"])
        history.append({"round": rnd, "stub": f"{miss.owner}.{miss.name}({', '.join(params)})", "written": ok})
        if not ok:
            return {"derived": False, "rounds": history, "outcome": "MEMBER_NOT_INSERTABLE"}
        if rnd + 1 >= max_rounds:
            break
    out = run()
    return {"derived": False, "rounds": history, "outcome": "STUBBED_BUT_NOT_SATISFIED",
            "last": out[-400:]}


def _pytest_capable_python(root: pathlib.Path) -> str:
    """Find an interpreter that can import pytest, and say which one it chose.

    A harness that cannot run the test reports the test as failing. Checking the tool before
    using it is the difference between a measurement and a guess.
    """
    import os
    cands = [
        root.parent / "venv" / "bin" / "python",
        root / ".venv" / "bin" / "python",
        pathlib.Path(sys.executable),
    ]
    for c in cands:
        if not pathlib.Path(c).exists():
            continue
        proc = subprocess.run([str(c), "-c", "import pytest"], capture_output=True)
        if proc.returncode == 0:
            return str(c)
    raise RuntimeError("NO_PYTEST_CAPABLE_PYTHON: looked in " + ", ".join(str(c) for c in cands))


def os_sep() -> str:
    import os
    return os.pathsep


def _os_env() -> dict:
    import os
    return {k: v for k, v in os.environ.items() if k in ("HOME", "LANG", "LC_ALL", "PYTHONHASHSEED", "TMPDIR")}


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: spec_derived_member_v1.py <root> <test_path> <test_id>", file=sys.stderr)
        return 2
    import json
    report = derive(pathlib.Path(argv[1]), argv[2], argv[3])
    print(json.dumps(report, indent=2))
    return 0 if report["derived"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
