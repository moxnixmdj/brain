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
    FOLLOW      when the declared command is a wrapper -- npm test, make
                test -- it is a promise about what some other command will
                do, and substituting the wrapper never touches that. So the
                wrapper is followed through the manifest that defines it
                (package.json scripts, Makefile recipe, Justfile) to the
                command actually executed, and that is what gets adapted.

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

    # A missing test runner is not a pytest problem; it is the general
    # case. What decides the substitute is what this project's tests are
    # written against and whether that runner exists here -- one rule,
    # living in repair_v1 so that both modules ask the same question and
    # neither can drift from the other.
    try:
        from repair_v1 import _find_runner, _TEST_RUNNERS
    except Exception:
        # A missing import must never look like "no substitute exists".
        _find_runner, _TEST_RUNNERS = None, frozenset()

    if token in _TEST_RUNNERS:
        if _find_runner is None:
            return None, f"{token} absent and the substitution rule is unavailable"
        found, evidence = _find_runner(root)
        if found and found.strip().lower() != (command or "").strip().lower():
            return found, evidence or (
                f"{token} absent; substituted on evidence in this project's "
                f"own test files")
        return None, (f"{token} absent and no runner this project's tests are "
                      f"written against exists here")

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


# A command that delegates to a runner is not the runner.
#
# `npm test` says nothing about whether mocha exists; it says what mocha
# will be asked to do. When mocha is absent, substituting the wrapper is
# pointless -- the absence lives one level down, in the thing the wrapper
# invokes. So a wrapper is followed, through the manifest that defines it,
# to the command actually executed. This is not a list of tools: it is the
# observation that a declaration can be indirect, and that following the
# indirection is what makes substitution reach the real failure.
_WRAPPER_TOKENS = frozenset({
    "npm", "npx", "yarn", "pnpm", "bun", "make", "gmake", "just",
})


def _npm_script(root: Path, name: str) -> list[str]:
    """package.json scripts.<name>, the command `npm run <name>` executes."""
    pkg = root / "package.json"
    if not pkg.is_file():
        return []
    try:
        data = json.loads(_read(pkg) or "{}")
    except Exception:
        return []
    cmd = (data.get("scripts") or {}).get(name)
    return [cmd.strip()] if isinstance(cmd, str) and cmd.strip() else []


def _recipe(root: Path, filenames: list[str], target: str) -> list[str]:
    """The recipe lines a Make/Just target runs, read from the manifest."""
    for filename in filenames:
        path = root / filename
        if not path.is_file():
            continue
        text = _read(path)
        if not text:
            continue
        out: list[str] = []
        grabbing = False
        for line in text.splitlines():
            if re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*\s*:", line):
                grabbing = line.split(":", 1)[0].strip() == target
                continue
            if not grabbing or not line.strip():
                continue
            if line[:1] in ("\t", " "):
                cmd = line.strip()
                if cmd.startswith("@"):
                    cmd = cmd[1:].strip()
                if cmd and not cmd.startswith("#"):
                    out.append(cmd)
            else:
                break
        if out:
            return out
    return []


def _resolve(command: str, root: str) -> list[str]:
    """What a wrapper command actually executes, when the manifest says."""
    parts = (command or "").strip().split()
    if not parts:
        return []
    token = parts[0]
    if token not in _WRAPPER_TOKENS:
        return []
    base = Path(root)
    args = [a for a in parts[1:] if not a.startswith("-")]
    if not args:
        return []
    if token in ("npm", "npx", "yarn", "pnpm", "bun"):
        name = args[0]
        if name == "run" and len(args) > 1:
            name = args[1]
        return _npm_script(base, name)
    if token in ("make", "gmake"):
        return _recipe(base, ["Makefile", "makefile", "GNUmakefile"], args[0])
    if token == "just":
        return _recipe(base, ["Justfile", "justfile"], args[0])
    return []


def fit(root: str) -> dict:
    """Of what this environment declares, what can actually happen here."""
    decls = declared(root)
    runnable_now, adapted, blocked = [], [], []
    seen: set[str] = set()

    def evaluate(command: str, source: str, kind: str, original: str = "") -> None:
        command = (command or "").strip()
        if not command or command.lower() in seen:
            return
        seen.add(command.lower())
        ok, why = runnable(command)
        if ok:
            runnable_now.append({"command": command, "source": source,
                                 "kind": kind, "why": why})
            return
        sub, reason = substitute(command, root)
        if sub:
            adapted.append({"command": sub, "source": source, "kind": kind,
                            "original": original or command, "why": reason})
        else:
            blocked.append({"command": command, "source": source, "kind": kind,
                            "why": reason or why})

    for d in decls:
        evaluate(d["command"], d["source"], d["kind"])
        # Follow the wrapper. The absence usually lives in the command this
        # one invokes, not in the one that was declared.
        for inner in _resolve(d["command"], root):
            if inner.strip().lower() != d["command"].strip().lower():
                evaluate(inner, f"{d['source']} -> {d['command']}",
                         d["kind"], original=d["command"])

    return {"schema": SCHEMA, "root": root, "declared": decls,
            "runnable": runnable_now, "adapted": adapted, "blocked": blocked}


# Evidence, in command output, that tests actually ran. A command that
# exits zero proves nothing on its own -- the decoy in env_toolchain prints
# "no tests here" and exits 0. What distinguishes a test run is what it
# says, so the judgement is made on the output and not the exit code.
#
# The reading itself lives in repair_v1, once. Two copies of "what a test
# run looks like" would agree today and drift the first time either was
# changed, which is how a system ends up believing one of its own hands
# while the other one is doing the work.
def _tests_ran(output: str) -> tuple[bool, int, str]:
    """Did this command actually run tests, and how many?"""
    try:
        from repair_v1 import tests_ran
    except ImportError:  # pragma: no cover
        from canonical.runtime.repair_v1 import tests_ran
    return tests_ran(output)


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
