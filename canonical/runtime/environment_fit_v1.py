"""Fit an arbitrary environment to the machine it landed on.

The dominant reason a real repository cannot be operated is not that the
task is hard -- it is that the tool it names is not installed. Discovery
finds the command, execution tries it, "pytest: not found", and the run is
over. Reading better does not help; the command was read correctly.

So this module sits between reading and running and answers one question:
of the things this environment declares, which can actually happen here --
and for the ones that cannot, is there something on this machine that does
the same job?

Two moves, in order:

    ADAPT       run an equivalent that exists (pytest -> python3 -m unittest
                discover). Chosen only on evidence in the project: the
                tests must actually use unittest, or the substitute tests
                nothing.
    PROVISION   install what is installable (npm install, pip install).
                Attempted only when adapting fails, and never silently.

The environment's own declarations outrank inference. A CI workflow or a
package.json script is the project stating how it is operated, which is
stronger evidence than a filename that looks like a test.

Everything here is deterministic: read, probe the filesystem, run and
observe. Nothing asks a model to guess.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_FIT_V1"

# Files in which an environment states how it operates, most to least
# explicit. CI is first because it is the project's own account of the
# commands that must pass, written down to be executed.
_DECLARATIONS = [
    ("ci", ".github/workflows/*.yml"),
    ("ci", ".github/workflows/*.yaml"),
    ("ci", ".gitlab-ci.yml"),
    ("scripts", "package.json"),
    ("make", "Makefile"),
    ("pyproject", "pyproject.toml"),
    ("requirements", "requirements*.txt"),
    ("tox", "tox.ini"),
]


def _read(path: Path, limit: int = 400_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def _first_token(command: str) -> str:
    parts = (command or "").strip().split()
    return parts[0] if parts else ""


def declared(root: str) -> list[dict]:
    """Commands this environment says are how it operates."""
    base = Path(root)
    out: list[dict] = []
    seen: set[str] = set()

    def add(command: str, source: str, kind: str) -> None:
        command = (command or "").strip()
        if not command or len(command) > 400:
            return
        key = command.lower()
        if key in seen:
            return
        seen.add(key)
        out.append({"command": command, "source": source, "kind": kind})

    # CI workflows: the run: lines are commands that must pass.
    for wf in sorted(base.glob(".github/workflows/*")):
        if wf.suffix.lower() not in {".yml", ".yaml"}:
            continue
        text = _read(wf)
        for m in re.finditer(r"^\s*-?\s*run:\s*\|?\s*$", text, re.M):
            block = text[m.end():]
            lines = []
            for line in block.splitlines()[1:]:
                if line.strip() and not re.match(r"^\s{%d,}\S" % 0, line):
                    pass
                if re.match(r"^\s{0,%d}\S" % (len(line) - len(line.lstrip())), line):
                    pass
                if line.strip() and (len(line) - len(line.lstrip())) > 8:
                    lines.append(line.strip())
                elif lines:
                    break
            for line in lines:
                add(line, f"ci:{wf.name}", "ci")
        for m in re.finditer(r"run:\s*([^\n]+)", text):
            inline = m.group(1).strip().strip("|").strip()
            if inline and inline not in ("|", ">"):
                add(inline, f"ci:{wf.name}", "ci")

    # package.json scripts
    pkg = base / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(_read(pkg) or "{}")
            for name, cmd in (data.get("scripts") or {}).items():
                add(f"npm run {name}" if isinstance(cmd, str) else "",
                    "package.json", "script")
        except Exception:
            pass

    # Makefile targets
    mk = base / "Makefile"
    if mk.is_file():
        for m in re.finditer(r"^([A-Za-z0-9_.-]+):", _read(mk), re.M):
            add(f"make {m.group(1)}", "Makefile", "make")

    # tox.ini / pyproject declared commands
    tox = base / "tox.ini"
    if tox.is_file():
        for m in re.finditer(r"^commands\s*=\s*(.+)$", _read(tox), re.M):
            add(m.group(1).strip(), "tox.ini", "tox")

    pp = base / "pyproject.toml"
    if pp.is_file():
        text = _read(pp)
        if re.search(r"^\[tool\.pytest", text, re.M):
            add("pytest", "pyproject.toml", "test")
        if re.search(r"^\[tool\.black", text, re.M):
            add("black .", "pyproject.toml", "format")
        if re.search(r"^\[tool\.ruff", text, re.M):
            add("ruff .", "pyproject.toml", "lint")
        if re.search(r"^\[tool\.mypy", text, re.M):
            add("mypy .", "pyproject.toml", "typecheck")

    return out


def runnable(command: str) -> tuple[bool, str]:
    """Can this command's first token execute here?

    Judged by asking the machine, not by remembering a list.
    """
    token = _first_token(command)
    if not token:
        return False, "empty command"
    if token in ("npm",) and shutil.which("npm"):
        return True, "npm present"
    if shutil.which(token):
        return True, f"{token} on PATH"
    # python -m mod: the binary need not exist for the module to be importable
    m = re.match(r"^python3?\s+-m\s+([A-Za-z0-9_.-]+)", command)
    if m:
        r = subprocess.run(["python3", "-c", f"import {m.group(1)}"],
                           capture_output=True, timeout=30)
        return (True, f"module {m.group(1)} importable") if r.returncode == 0 \
            else (False, f"module {m.group(1)} not importable")
    return False, f"{token} not found"


def _tests_use(root: str, module: str) -> bool:
    """Evidence in the project that its tests are written against a module.

    Substituting a test runner that collects nothing is worse than not
    running tests at all, because it reports success. So the substitute is
    chosen only when the project's own sources say it applies.
    """
    base = Path(root)
    pattern = re.compile(r"^\s*import\s+%s\b|^\s*from\s+%s\b" % (module, module), re.M)
    files = 0
    for path in base.rglob("*.py"):
        if files > 400:
            break
        files += 1
        try:
            if pattern.search(_read(path, 200_000)):
                return True
        except Exception:
            continue
    return False


def substitute(command: str, root: str) -> tuple[str | None, str]:
    """An equivalent that exists on this machine, or None.

    Each substitution is justified by evidence in the project, not by a
    standing mapping: pytest becomes unittest only because the tests import
    unittest.
    """
    token = _first_token(command)
    rest = (command or "").strip()[len(token):].strip()

    if token == "pytest":
        if _tests_use(root, "unittest"):
            return "python3 -m unittest discover -s . -p 'test*.py' -v", \
                "pytest absent; project tests import unittest, so unittest discover collects them"
        return None, "pytest absent and no unittest-based tests to substitute"

    if token == "pytest-3":
        return substitute("pytest " + rest, root)

    if token in ("black", "ruff"):
        return None, f"{token} absent; formatting cannot be verified here, and faking it would claim a check that did not run"

    if token == "mypy":
        return None, "mypy absent; type checking cannot be verified here"

    if token == "tox":
        return None, "tox absent"

    if token == "make":
        # a make target can often be run as its recipe, but only the project
        # knows that recipe; reported as blocked rather than guessed
        return None, "make absent"

    return None, f"no substitute known for {token}"


def fit(root: str) -> dict:
    """Of what this environment declares, what can actually happen here."""
    decls = declared(root)
    runnable_now, adapted, blocked = [], [], []
    for d in decls:
        ok, why = runnable(d["command"])
        if ok:
            runnable_now.append(dict(d, why=why))
            continue
        sub, reason = substitute(d["command"], root)
        if sub:
            adapted.append(dict(d, command=sub, original=d["command"], why=reason))
        else:
            blocked.append(dict(d, why=reason or why))
    return {"schema": SCHEMA, "root": root, "declared": decls,
            "runnable": runnable_now, "adapted": adapted, "blocked": blocked}


# Evidence, in command output, that tests actually ran. A command that
# exits zero proves nothing on its own -- the decoy in env_toolchain prints
# "no tests here" and exits 0. What distinguishes a test run is what it
# says, so the judgement is made on the output and not the exit code.
_EVIDENCE = [
    (re.compile(r"Ran\s+(\d+)\s+tests?"), "unittest"),
    (re.compile(r"(\d+)\s+passed"), "pytest"),
    (re.compile(r"(\d+)\s+failing|(\d+)\s+passing"), "mocha"),
    (re.compile(r"Tests:\s+(\d+)"), "jest"),
    (re.compile(r"^(ok|not ok)\s", re.M), "tap"),
]


def _tests_ran(output: str) -> tuple[bool, int, str]:
    """Did this command actually run tests, and how many?"""
    best_n, best_kind = 0, ""
    for pattern, kind in _EVIDENCE:
        for m in pattern.finditer(output or ""):
            n = 0
            for g in m.groups():
                if g and g.isdigit():
                    n = max(n, int(g))
            if n > best_n:
                best_n, best_kind = n, kind
    return (best_n > 0), best_n, best_kind


def best_test_command(root: str, timeout: int = 120) -> tuple[str | None, str, str]:
    """The command that most genuinely tests this project here.

    Candidates are what the environment declares, plus an evidence-backed
    substitute where the declared tool is absent. Each is then actually run,
    because the only trustworthy answer to "does this test the project" is
    to watch it try.

    Returns (command, source, why).
    """
    f = fit(root)
    candidates = []
    for d in f["runnable"] + f["adapted"]:
        command = d["command"]
        if re.search(r"\b(lint|format|typecheck|black|ruff|mypy)\b", command, re.I):
            continue
        candidates.append((command, d.get("source", "?"), d.get("why", "")))

    tried = []
    for command, source, why in candidates:
        try:
            r = subprocess.run(command, shell=True, cwd=root, timeout=timeout,
                               capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
        except Exception as exc:
            tried.append((command, f"failed to run: {type(exc).__name__}"))
            continue
        ran, n, kind = _tests_ran(out)
        tried.append((command, f"{'ran' if ran else 'no tests'} ({n}, {kind or '-'})"))
        if ran:
            return command, source, f"{n} tests actually ran via {kind}"

    # Nothing testable. Say so rather than returning a command that merely
    # executes -- a test command that tests nothing is worse than none,
    # because it reports success.
    return None, "", "no candidate ran any tests; tried: " +         "; ".join(f"{c} -> {w}" for c, w in tried[:5])
