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

import hashlib
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
    """Can this command execute here? Judged by asking the machine.

    Defined once, in repair_v1, and used here too. Two answers to "can
    this run" would be two chances to disagree about what running means,
    and the disagreement would surface as a command that one half of the
    system considers available and the other half cannot start.
    """
    try:
        from repair_v1 import command_runnable
    except ImportError:  # pragma: no cover
        from canonical.runtime.repair_v1 import command_runnable
    return command_runnable(command)


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


# Where isolated environments are created: OUTSIDE the project, in a
# cache keyed by the project's path.
#
# Inside the project was tried first and is wrong. Provisioning is a side
# effect, and a directory of installed packages inside a repository is a
# side effect that changes what the repository looks like -- to the
# scanner reading its test files, to the monster environment whose entire
# purpose is to punish exactly that, and to anyone who later tries to
# understand what belongs to the project. An environment the system
# created is not part of the project it was created for.
def _env_dir(root: str) -> Path:
    import os as _os
    import tempfile as _tf
    key = hashlib.sha256(_os.path.abspath(root).encode("utf-8")).hexdigest()[:16]
    base = _os.environ.get("BRAIN_ENV_DIR") or _os.path.join(
        _tf.gettempdir(), "brain_envs")
    return Path(base) / key

_PY_MODULE = re.compile(r"^python3?\s+-m\s+([A-Za-z0-9_.-]+)")

# Failures that mean "something is missing", as opposed to "the project is
# broken". Only these justify going to fetch something.
_DEPENDENCY_CLASSES = frozenset({
    "missing_binary", "missing_python_module", "missing_node_module",
})


def _requirement(command: str) -> str:
    """The obtainable thing a command needs, named by the command itself.

    Not a list of tools. `python -m X` names X; anything else names its
    first word. Whether that name is obtainable is then discovered by
    trying, which is the only way to know, and works for packages that
    did not exist when this file was written.
    """
    m = _PY_MODULE.match((command or "").strip())
    if m:
        return m.group(1)
    return _first_token(command)


def provision(command: str, root: str, timeout: int = 600) -> tuple[str | None, str]:
    """Obtain what a command needs, in isolation -- then prove it works.

    ADAPT is always tried first, because borrowing what already exists is
    cheaper and safer than fetching something new. PROVISION is the move
    for when there is nothing to borrow: the project genuinely needs a
    tool this machine does not have, and the honest alternatives are to
    fetch it or to admit the task cannot be done here.

    Two rules, both learned the hard way:

    It happens in a virtual environment inside the project, never against
    the system interpreter, so a fetched package cannot disturb anything
    that was already working.

    And it is verified before it is trusted. Installing is not the same as
    being able to run; the command is executed after the install and only
    reported as provisioned if it responds. A provision that was assumed
    rather than checked would fail later, in a way that looked like the
    project's fault.
    """
    name = _requirement(command)
    if not name:
        return None, "nothing to obtain"

    import sys as _sys
    base = Path(root)
    venv = _env_dir(root) / "venv"
    python = venv / "bin" / "python"

    if not python.is_file():
        try:
            r = subprocess.run([_sys.executable, "-m", "venv", str(venv)],
                               capture_output=True, text=True, timeout=timeout)
        except Exception as exc:
            return None, f"could not create an isolated environment: {exc}"
        if r.returncode != 0:
            return None, ("could not create an isolated environment: "
                          + (r.stderr or "").strip()[:160])

    try:
        r = subprocess.run([str(python), "-m", "pip", "install", "-q", name],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"obtaining {name} timed out"
    except Exception as exc:
        return None, f"could not obtain {name}: {exc}"
    if r.returncode != 0:
        return None, f"could not obtain {name}: {(r.stderr or '').strip()[:160]}"

    # Prove it, rather than assuming the install took.
    m = _PY_MODULE.match((command or "").strip())
    if m:
        probe = [str(python), "-c", f"import {m.group(1)}"]
        working = command.replace("python3 -m", f"{python} -m", 1).replace(
            "python -m", f"{python} -m", 1)
    else:
        probe = [str(venv / "bin" / name), "--version"]
        working = command.replace(_first_token(command),
                                  str(venv / "bin" / name), 1)
    try:
        p = subprocess.run(probe, capture_output=True, timeout=120)
    except Exception as exc:
        return None, f"{name} installed but did not run: {exc}"
    if p.returncode != 0:
        return None, f"{name} installed but did not run"
    return working, f"obtained {name} into an isolated environment and verified it runs"


def _ensure_venv(root: str, timeout: int = 600):
    """An isolated interpreter for this project, created if absent."""
    import sys as _sys
    venv = _env_dir(root) / "venv"
    python = venv / "bin" / "python"
    if python.is_file():
        return str(python)
    venv.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run([_sys.executable, "-m", "venv", str(venv)],
                           capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    return str(python) if r.returncode == 0 and python.is_file() else None


def _declared_python_test_deps(root: Path) -> list[str]:
    """What the project says its tests need, read from its own manifest.

    Not a guess about which packages are popular. The project states its
    dependencies; that statement is the most reliable thing available
    about what has to be present, and it is right for packages that did
    not exist when this code was written.
    """
    found: list[str] = []
    pp = root / "pyproject.toml"
    if pp.is_file():
        try:
            import tomllib
            data = tomllib.loads(_read(pp))
        except Exception:
            data = {}
        groups = data.get("dependency-groups") or {}
        for name, packages in groups.items():
            if re.search(r"test", str(name), re.I) and isinstance(packages, list):
                for pkg in packages:
                    if isinstance(pkg, str):
                        # drop the environment marker, keep the requirement
                        found.append(pkg.split(";")[0].strip())
        optional = ((data.get("project") or {}).get("optional-dependencies") or {})
        for name, packages in optional.items():
            if re.search(r"test", str(name), re.I) and isinstance(packages, list):
                for pkg in packages:
                    if isinstance(pkg, str):
                        found.append(pkg.split(";")[0].strip())
    return [f for f in found if f]


def satisfy(root: str, timeout: int = 900) -> tuple[bool, str]:
    """Install what the project declares it needs.

    Obtaining the test runner is not the same as being able to run the
    tests, and a real repository made that plain: pytest alone reported
    five collection errors because the project could not import itself
    and had no freezegun. The runner is one dependency among several, and
    the project's own manifest is what lists the rest.

    Everything goes into the project's isolated environment, and every
    step is run and checked rather than assumed.
    """
    base = Path(root)
    python = _ensure_venv(root, timeout)
    if not python:
        return False, "could not create an isolated environment"

    steps: list[str] = []
    ran = False

    def pip(*args) -> bool:
        try:
            r = subprocess.run([python, "-m", "pip", "install", "-q", *args],
                               cwd=root, capture_output=True, text=True,
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
        return r.returncode == 0

    if (base / "pyproject.toml").is_file() or (base / "setup.py").is_file():
        ran = True
        # A plain install, not an editable one: a src-layout project cannot
        # import itself until it is installed, but an editable install
        # writes build artefacts back into the working tree, which is the
        # project's space and not ours to alter.
        if pip("."):
            steps.append("installed the project")
        deps = _declared_python_test_deps(base)
        if deps:
            if pip(*deps):
                steps.append("installed declared test dependencies: " + ", ".join(deps))
            else:
                steps.append("could not install: " + ", ".join(deps))

    for req in sorted(base.glob("requirements*.txt")):
        ran = True
        if pip("-r", str(req)):
            steps.append(f"installed {req.name}")

    if (base / "package.json").is_file() and shutil.which("npm"):
        ran = True
        try:
            r = subprocess.run(["npm", "install"], cwd=root, capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            steps.append("npm install timed out")
        else:
            steps.append("npm install succeeded" if r.returncode == 0
                         else "npm install failed")

    if not ran:
        return False, "no recognised manifest to satisfy"
    return True, "; ".join(steps)


def _looks_obtainable(command: str) -> bool:
    """Worth trying to fetch? Refuse to chase nonsense.

    A command with globs, shell redirection or a path is not a package
    name, and asking an index for it wastes a round trip and produces a
    confusing error. Provisioning is only attempted where the thing being
    asked for could plausibly be the name of something.
    """
    token = _requirement(command)
    if not token:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", token))


# Perception is cached, because an environment that has not changed is
# the same environment. FSD does not re-read the road on every frame; it
# reads it once and then only tracks what moves. The key is the content
# of the manifests themselves, so editing any of them invalidates the
# answer and nothing else does.
_FIT_CACHE: dict[str, dict] = {}


def _fit_key(root: str) -> str:
    base = Path(root)
    parts = [os.path.abspath(root)]
    for name in ("pyproject.toml", "package.json", "Makefile", "Justfile",
                 "tox.ini", "setup.py", "requirements.txt", "tasks.toml"):
        path = base / name
        try:
            st = path.stat()
            parts.append(f"{name}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append(f"{name}:-")
    for wf in sorted(base.glob(".github/workflows/*")):
        try:
            st = wf.stat()
            parts.append(f"{wf.name}:{st.st_mtime_ns}")
        except OSError:
            continue
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ---- 2. Rank candidates by how much evidence calls them a test command.
#         Trying every candidate in declaration order means running full
#         builds to discover what the manifest already said.
_TESTISH = re.compile(
    r"\b(test|tests|spec|specs|unit|pytest|unittest|vitest|jest|mocha|"
    r"tap|nose|check|verify)\b", re.I)
_NOT_A_TEST = re.compile(
    r"\b(lint|format|typecheck|type|black|ruff|mypy|build|publish|"
    r"deploy|docs?|pre-?commit|install|clean|release)\b", re.I)


def _test_likelihood(command: str, source: str) -> int:
    """How strongly the evidence says this command runs tests.

    Three grades, and the point is ordering rather than exclusion: the
    cheap, well-evidenced candidate runs first and, if it works, nothing
    else runs at all. On a real repository this is the difference between
    one test run and four -- the other three being a build, a publish
    step and a type check, none of which anyone needed.
    """
    text = f"{command} {source}"
    if _NOT_A_TEST.search(text) and not _TESTISH.search(command):
        return 0
    if re.search(r"\b(test|tests|spec|pytest|unittest|vitest|jest|mocha)\b",
                 command, re.I):
        return 3
    if _TESTISH.search(source):
        return 2
    return 1


def fit(root: str, provision_allowed: bool = True, use_cache: bool = True) -> dict:
    """Of what this environment declares, what can actually happen here.

    Provisioning is permitted by default and always reported separately,
    never folded into "runnable" as though the tool had been there all
    along. The distinction matters: a command that runs because something
    was fetched from the network is a different kind of fact from one that
    runs because it was already installed.
    """
    if use_cache:
        key = _fit_key(root)
        cached = _FIT_CACHE.get(key)
        if cached is not None:
            return dict(cached)
    decls = declared(root)
    runnable_now, adapted, blocked, provisioned = [], [], [], []
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
            return
        if provision_allowed and _looks_obtainable(command):
            obtained, preason = provision(command, root)
            if obtained:
                provisioned.append({"command": obtained, "source": source,
                                    "kind": kind, "original": command,
                                    "why": preason})
                return
            reason = f"{reason}; provisioning: {preason}"
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

    result = {"schema": SCHEMA, "root": root, "declared": decls,
              "runnable": runnable_now, "adapted": adapted, "blocked": blocked,
              "provisioned": provisioned}
    if use_cache:
        _FIT_CACHE[_fit_key(root)] = dict(result)
    return result


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
    for d in f["runnable"] + f["adapted"] + f["provisioned"]:
        command = d["command"]
        if re.search(r"\b(lint|format|typecheck|black|ruff|mypy)\b", command, re.I):
            continue
        source = d.get("source", "?")
        candidates.append((command, source, d.get("why", "")))

    # Best-evidenced first, so the first survivor is usually the only
    # command that ever runs. Every candidate executed in full is a test
    # suite, a build or a publish step that someone has to wait for.
    candidates.sort(key=lambda c: (-_test_likelihood(c[0], c[1]),
                                   -len(c[1]), c[0]))

    tried = []
    observed: list[tuple[str, str, str, str]] = []
    for command, source, why in candidates:
        try:
            r = subprocess.run(command, shell=True, cwd=root, timeout=timeout,
                               capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
        except Exception as exc:
            tried.append((command, f"failed to run: {type(exc).__name__}"))
            continue
        observed.append((command, source, why, out))
        ran, n, kind = _tests_ran(out)
        tried.append((command, f"{'ran' if ran else 'no tests'} ({n}, {kind or '-'})"))
        if ran:
            return command, source, f"{n} tests actually ran via {kind}"

    # Nothing ran tests. Before concluding the project cannot be tested
    # here, satisfy what the project itself declares it needs and try
    # once more: a runner with nothing to import reports zero tests for
    # reasons that have nothing to do with the runner.
    # Provisioning is a response to an observed failure, never a
    # precaution. Installing packages on the chance they might be needed
    # turns every unknown project into a network round trip, and -- worse
    # -- writes into a repository that was only being inspected. So the
    # outputs already gathered are classified first, and the dependencies
    # are satisfied only if something genuinely failed for want of them.
    needed = False
    for _command, _source, _why, _out in observed:
        try:
            from repair_v1 import diagnose
        except ImportError:  # pragma: no cover
            from canonical.runtime.repair_v1 import diagnose
        if diagnose(_command, _out, 1, root).get("class") in _DEPENDENCY_CLASSES:
            needed = True
            break

    ok, what = (satisfy(root) if needed else (False, "no dependency failure seen"))
    if ok:
        for command, source, why in candidates:
            try:
                r = subprocess.run(command, shell=True, cwd=root, timeout=timeout,
                                   capture_output=True, text=True)
                out = (r.stdout or "") + (r.stderr or "")
            except Exception as exc:
                continue
            ran, n, kind = _tests_ran(out)
            if ran:
                return command, source, f"{n} tests ran via {kind} after {what}"

    # Nothing testable. Say so rather than returning a command that merely
    # executes -- a test command that tests nothing is worse than none,
    # because it reports success.
    detail = "; ".join(f"{c} -> {w}" for c, w in tried[:5])
    if ok:
        detail = f"[{what}] " + detail
    return None, "", "no candidate ran any tests; tried: " + detail
