"""The environment broker: go into an arbitrary environment knowing nothing, ask the right
questions, verify every answer by running it, and only then keep it.

WHY THIS EXISTS
---------------
The user's proposal, taken literally:

    "an algorithm that enters any new arbitrary environment and does not know anything;
     it only asks the right questions and learns everything it needs, instantly."

This project has already measured the pieces. What it does not have is the link that turns
"the host printed something" into "the environment works, and here is the proof". That link
is the broker. It is deliberately NOT the whole agent and deliberately NOT smart: it holds
a fixed, declared set of environment questions, because a question set that can grow without
bound is the knowledge house coming back through the side door. When the goal is not inside
the declared contracts, the broker refuses by name instead of improvising.

THE FIVE QUESTIONS, AND THE ORDER THEY MUST BE ASKED IN
-------------------------------------------------------
    LAYOUT        what shape is this tree          (files only, never executes)
    INTERPRETER   what runs it                     (pyproject requires-python, checked)
    RUNNER        what checks it                   (candidate command lines, EXECUTED)
    DEPS          what must exist for it to run    (the project's own declarations)
    CONTRACT      what counts as success           (from the goal, or REFUSE)

The verification half is the whole point. Every answer except LAYOUT is confirmed by
execution before it is believed, because a printed page is not a machine (this tree's own
measured lesson: 0 of 164 catalogue options that own programs would run were executed to a
state change). A file can be stale, a doc can lie, a digest can drift -- a bounded run that
returns exit code 0 cannot.

THE SECOND GOAL: env-ready
--------------------------
`run-tests` answers "does this environment's suite pass". It cannot be asked until the
environment is armed, and arming was the measured wall: every real repository this project
brokered needed dependencies the isolation did not have, and the refusal that follows is
not about the task -- it is about the environment being incomplete. `env-ready` is the
contract in front of it:

    A declared dependency of THIS environment is ready when, inside the isolated
    interpreter this environment will be asked in, its distribution is importable at a
    version satisfying the environment's own declaration -- and for anything the isolation
    does not yet have, the bytes are fetched from the machine-readable registry, hashed,
    and compared against the registry's own published digest before pip is allowed to
    touch them.

Host-first, always: a dependency already present in the isolation costs a metadata read
(a few milliseconds), never a round trip. The registry is the fallback for what the
isolation cannot answer, version-pinned by the environment's declaration -- the web is
asked only for what the machine itself says it needs, never for an open question.

Two independent readers must agree before an artifact is believed: this code hashes the
bytes it downloaded, and the registry's JSON states what those bytes should hash to. A
disagreement is a refusal, not a warning. Installation is still not the arbiter: after the
install, every declared dependency's version is read back out of the installed metadata by
execution, and only that execution result is recorded.

WHAT IS CACHED, AND WHAT THAT MAKES THE MEMORY
-----------------------------------------------
One record per (goal, environment), keyed by the sha256 of the EVIDENCE FILES' contents
(never by path, never by name): the answer set, the command it verified with, its exit
code, and the wall clock. Nothing about the action sequence is stored; actions do not
transfer and are the cheapest thing to re-derive.

A cache is never trusted blindly. On a warm run the cached runner is re-executed (and the
cached dependency records are re-read out of the installed metadata) and must still pass;
if they do not, the entry is discarded and re-derived. So the broker's staleness window is
one check, not the lifetime of the file.

COST
----
run-tests: local evidence only, no model, no network, no weights. env-ready: no model, no
weights, and network only for the registry fetch of declarations the isolation cannot
satisfy locally -- counted in the result's `network` block, never hidden. Host-first is
measured, not stylistic: asking this host costs 6.78 ms against 255.2 ms for the web, and
7,432 man-page citations on this host resolve to zero present files
(intake/SCAN_RETRIEVE_FETCH_20261121_V1.md). The registry tier is machine-readable
(pypi.org JSON), so the answer is a fact a machine can check, not prose to interpret.

REFUSALS, ALL BY NAME
---------------------
    REFUSE__NOT_A_PYTHON_ENVIRONMENT   no pyproject/setup/requirements evidence found
    REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS  the goal is not one of the declared contracts
    REFUSE__REQUIRES_PYTHON_NOT_MET_LOCALLY     the declared floor excludes this interpreter
    REFUSE__NO_RUNNER_EXECUTED_CLEANLY          no candidate check command ran at all (no
                                                runner, or it could not import/collect)
    REFUSE__VERIFICATION_FAILED                 the suite RAN in the armed environment and
                                                did not exit cleanly: a result about the
                                                project, reported separately from any claim
                                                about the environment
    REFUSE__VERIFICATION_FAILED                 the suite (or the check) does not pass;
                                                nothing is cached, nothing is claimed
    REFUSE__DECLARATION_NOT_UNDERSTOOD          a declaration is not a plain registry
                                                requirement (direct URL reference, syntax
                                                this reader does not understand); guessing
                                                would be inventing the environment's needs
    REFUSE__DEPENDENCY_NOT_ON_REGISTRY          the registry has no such name (live 404)
    REFUSE__NO_COMPATIBLE_VERIFIED_ARTIFACT     no non-yanked wheel this interpreter can
                                                run satisfies the declaration (sdist-only
                                                counts: unverifiable bytes, refused)
    REFUSE__DIGEST_DISAGREE                     the bytes we hashed are not the bytes the
                                                registry published; nothing is installed
    REFUSE__REGISTRY_UNREACHABLE                the machine-readable tier did not answer
    REFUSE__INSTALL_FAILED                      the verified bytes would not install
    REFUSE__VERSION_CHECK_FAILED                post-install execution does not show the
                                                declared version; the environment is not armed
    REFUSE__ISOLATION_ENVIRONMENT_UNAVAILABLE   no isolated interpreter could be created

Authority NONE__PRODUCER_RUN_SANDBOX. Model calls zero at every stage. Network only in
env-ready's registry stage, and only for what the environment itself declares.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time
import zipfile
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_THE_ENVIRONMENT_BROKER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
CACHE_SCHEMA = "BRAIN_ENVIRONMENT_MEMORY_V2"
DEFAULT_MEMORY = pathlib.Path("/tmp/brain_memory/world_broker.json")

EVIDENCE_NAMES = ("pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "Makefile",
                  "requirements.txt")
GOAL_KINDS = ("run-tests", "env-ready")
# A runner bound, not a verdict: tox's own suite takes ~175 s on this host, so a 180 s cap
# turned "still running" into "no runner executed cleanly" (measured, twice). Long enough
# that only a hung suite hits it, and a timeout is then reported as a timeout.
TIMEOUT = 600.0
REGISTRY_JSON = "https://pypi.org/pypi/{name}/json"
TIME_BUDGET = 900.0


# ---------------------------------------------------------------- evidence
def evidence_digest(tree: pathlib.Path) -> tuple[str, list[str]]:
    """Digest of the evidence files that produced the answer. Not the path: the path is a
    label, and labels do not survive a move. Missing evidence is simply absent. Every
    requirements*.txt counts, because each one is a declaration this environment makes;
    an uncounted one would be an edit the cache could not see."""
    parts: list[bytes] = []
    names: list[str] = []
    seen: set[str] = set()
    for name in EVIDENCE_NAMES:
        candidate = tree / name
        if candidate.is_file() and name not in seen:
            seen.add(name)
            parts.append(name.encode() + b"\0" + hashlib.sha256(candidate.read_bytes()).hexdigest().encode())
            names.append(name)
    for extra in sorted(tree.glob("requirements*.txt")) if tree.is_dir() else []:
        if extra.is_file() and extra.name not in seen:
            seen.add(extra.name)
            parts.append(extra.name.encode() + b"\0" + hashlib.sha256(extra.read_bytes()).hexdigest().encode())
            names.append(extra.name)
    # History is evidence, not context: a project whose version is derived from its git tags
    # produces a different environment from the same tree without them (measured -- tox
    # cannot even import itself, attrs' own metadata tests disagree with it). So the tag and
    # commit state enters the digest; a clone that later gains its tags is a different
    # environment and is re-derived instead of being answered from a record about the old one.
    git_head = tree / ".git"
    if git_head.exists():
        try:
            import subprocess as _sp
            commit = _sp.run(["git", "-C", str(tree), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30).stdout.strip()
            tags = _sp.run(["git", "-C", str(tree), "describe", "--tags", "--abbrev=0"],
                           capture_output=True, text=True, timeout=30).stdout.strip()
            state = f"{commit}\0{tags}".encode()
            parts.append(b".git-state\0" + hashlib.sha256(state).hexdigest().encode())
            names.append(".git-state")
        except Exception:
            parts.append(b".git-state\0unreadable")
            names.append(".git-state")
    return hashlib.sha256(b"\n".join(parts)).hexdigest(), names


def declared_table(pyproject: pathlib.Path | None) -> dict[str, Any] | None:
    """The project's manifest as a table, or None when nothing here can read it.

    This used to be a regex, and the regex was the bug rather than the environments: real
    declarations contain `python_version<'3.13'` (a single quote inside a double-quoted
    string) and arrays that span lines with trailing commas, and quote-alternation cannot
    survive either. Python 3.11 ships tomllib, so the honest reader is the standard one --
    and a tree whose parser is missing is told so rather than guessed at.
    """
    if pyproject is None or not pyproject.is_file():
        return None
    try:
        import tomllib
        return tomllib.loads(pyproject.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def read_toml_project(pyproject: pathlib.Path) -> dict[str, Any]:
    """The flat keys the broker needs, read by the standard parser. A tree read by the
    fallback reports nothing rather than guessing: an invented dependency is an invented
    environment."""
    out: dict[str, Any] = {"present": True, "requires_python": None, "declared_deps": [],
                           "build_backend": None, "build_requires": [], "project_name": None}
    table = declared_table(pyproject)
    if table is not None:
        project = table.get("project") or {}
        build = table.get("build-system") or {}
        out["requires_python"] = project.get("requires-python")
        out["declared_deps"] = [d for d in project.get("dependencies") or [] if isinstance(d, str)]
        out["build_backend"] = build.get("build-backend")
        out["build_requires"] = [d for d in build.get("requires") or [] if isinstance(d, str)]
        out["project_name"] = project.get("name")
    return out


def detect_layout(tree: pathlib.Path) -> dict[str, Any]:
    """LAYOUT is the one question answered with no execution: the file tree is the answer."""
    src = tree / "src"
    if src.is_dir():
        pkgs = sorted(p.name for p in src.iterdir()
                      if p.is_dir() and (p / "__init__.py").is_file())
        if pkgs:
            return {"kind": "src-layout", "packages": pkgs}
    pkgs = sorted(p.name for p in tree.iterdir()
                  if p.is_dir() and (p / "__init__.py").is_file()) if tree.is_dir() else []
    if pkgs:
        return {"kind": "flat", "packages": pkgs[:16]}
    return {"kind": "unknown", "packages": []}


_RUNNER_TOKENS = re.compile(r"^(pytest|python3?|tox|nox|make|hatch|uv|poetry)\b")


def declared_test_commands(tree: pathlib.Path,
                           pyproject: pathlib.Path | None = None) -> list[list[str]]:
    """The command the project says runs its tests, read from the project.

    `run-tests` used to assume pytest. That is the same mistake `env-ready` was built to
    delete one layer down: a guess standing where a declaration exists. An environment
    states its test command in pytest's testpaths, in a Makefile target, in a tox
    `commands =` block, or in a noxfile -- so those are read here as CLAIMS to execute,
    never as truth. A target whose first token is not a known runner (a README check, a docs
    build) is not this environment's suite and is left alone.
    """
    found: list[dict[str, str]] = []

    def add(text: str, what: str) -> None:
        text = (text or "").strip()
        if not text or not _RUNNER_TOKENS.match(text):
            return
        argv = [a for a in shlex.split(text, comments=False)
                if a not in ("{posargs:tests}", "{posargs}")]
        if not argv:
            return
        found.append({"argv": argv, "declared_by": what})

    table = declared_table(pyproject)
    if table is not None:
        tool = (table.get("tool") or {}).get("pytest") or {}
        ini = tool.get("ini_options") or {}
        paths = [p for p in (ini.get("testpaths") or []) if isinstance(p, str)]
        if paths:
            add("pytest -q " + " ".join(paths),
                "pyproject.toml:[tool.pytest.ini_options].testpaths")
        tox_tool = (table.get("tool") or {}).get("tox") or {}
        for section in ("testenv",):
            commands = ((tox_tool.get(section) or {}).get("commands") or [])
            for entry in commands:
                if isinstance(entry, list) and entry:
                    add(str(entry[0]).split("--")[0], f"pyproject.toml:[tool.tox.{section}]")

    makefile = next((tree / n for n in ("Makefile", "makefile", "GNUmakefile")
                     if (tree / n).is_file()), None)
    if makefile is not None:
        text = makefile.read_text(encoding="utf-8", errors="replace")
        for name in ("test", "tests", "pytest", "unit", "check"):
            m = re.search(r"^" + name + r"\s*:(?!=)(.*)$((?:\n\t.*)*)", text, re.MULTILINE)
            if not m:
                continue
            body = m.group(2) or ""
            first = next((ln.strip().lstrip("@-").strip() for ln in body.splitlines()
                          if ln.strip() and not ln.strip().startswith("#")), "")
            if first:
                add(first, f"Makefile:{name}")
            break

    tox_ini = tree / "tox.ini"
    if tox_ini.is_file():
        text = tox_ini.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^commands\s*=\s*((?:\n[ \t]+.*)*)", text, re.MULTILINE)
        if m:
            for line in m.group(1).splitlines():
                add(line.split("--")[0], "tox.ini:commands")

    noxfile = tree / "noxfile.py"
    if noxfile.is_file():
        m = re.search(r"session\.run\(\s*\"([^\"]+)\"",
                      noxfile.read_text(encoding="utf-8", errors="replace"))
        if m:
            add(m.group(1), "noxfile.py:session.run")

    # an interpreter running pytest is always a legitimate last claim to execute: a project
    # that declares no command and ships tests is not refused for want of a sentence.
    add("python -m pytest -q", "default")

    seen: set[tuple[str, ...]] = set()
    out: list[list[str]] = []
    for item in found:
        argv = list(item["argv"])
        if argv[0] in ("python", "python3"):
            argv[0] = sys.executable
        elif argv[0] == "pytest":
            argv = [sys.executable, "-m"] + argv
            if "-q" not in argv:
                argv = argv + ["-q"]
        if argv[0] == sys.executable and "-m" not in argv:
            continue          # a python script that is not a test runner; not our claim
        key = tuple(argv)
        if key not in seen:
            seen.add(key)
            out.append(argv)
    return out


def runner_candidates(tree: pathlib.Path,
                      pyproject: pathlib.Path | None = None) -> list[list[str]]:
    """The declared commands first, then the default. Execution decides which is the suite."""
    return declared_test_commands(tree, pyproject)


def python_floor_ok(requirement: str | None) -> tuple[bool, str]:
    if not requirement:
        return True, "no requires-python declared"
    m = re.search(r">=\s*(\d+)(?:\.(\d+))?", requirement)
    if not m:
        return True, f"requires-python {requirement!r} not understood; not refusing on it"
    floor = (int(m.group(1)), int(m.group(2) or 0))
    here = sys.version_info[:2]
    return (here >= floor), f"requires-python {requirement!r} vs this interpreter {here[0]}.{here[1]}"


def run_check(tree: pathlib.Path, argv: Sequence[str]) -> dict[str, Any]:
    """One bounded execution of the candidate runner. The verifier is the environment."""
    # The isolated interpreter is the oracle now, so the tree must NOT be put in front of
    # site-packages: a build can GENERATE files into the installed copy that do not exist in
    # the checkout (measured -- hatch-vcs writes `tox/version.py` at build time, and putting
    # the repo's own src/ first made the suite fail with `No module named tox.version` while
    # the isolation imported it fine). Only conftest/test-helpers paths are added.
    # When nothing has been installed, the tree IS the only place its package lives, so
    # src/ and the root go on the path (a bare checkout must still be runnable). When the
    # suite is being asked of an installed copy, they must not: the installed copy is the
    # thing being verified, generated files included.
    # "installed" means argv[0] is THIS tree's own isolation -- the interpreter the tree was
    # armed in. Not "any venv" (the broker commonly runs inside one, measured: that probe
    # wrongly dropped src/ for a plain checkout and its package stopped importing), and not
    # "differs from sys.executable" (same failure).
    interpreter = pathlib.Path(argv[0])
    own_isolation = existing_isolation_python(tree)
    installed = bool(own_isolation) and \
        interpreter.resolve() == pathlib.Path(own_isolation).resolve()
    paths = [str(tree / "tests")] if (tree / "tests").is_dir() else []
    if installed:
        if (tree / "src" / "conftest.py").is_file():
            paths.append(str(tree / "src"))
    else:
        paths = [str(tree)] + ([str(tree / "src")] if (tree / "src").is_dir() else []) + paths
    env = {"PYTHONPATH": ":".join(paths),
           "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
           "HOME": str(tree), "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.perf_counter()
    try:
        done = subprocess.run(list(argv), cwd=str(tree), capture_output=True, text=True,
                              timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return {"command": list(argv), "exit_code": None, "ok": False, "detail": "TIMEOUT",
                "seconds": round(time.perf_counter() - started, 4)}
    tail = (done.stdout + done.stderr)[-2000:]
    counted = re.findall(r"(\d+)\s+passed", tail)
    errors = re.findall(r"(\d+)\s+(?:failed|errors?)", tail)
    return {"command": list(argv), "exit_code": done.returncode,
            "ok": done.returncode == 0,
            "reported_passed": int(counted[-1]) if counted else None,
            "reported_failed_or_errored": int(errors[-1]) if errors else None,
            "seconds": round(time.perf_counter() - started, 4),
            "tail": tail[-400:]}


# ---------------------------------------------------------------- env-ready
# The contract in front of run-tests. A declared dependency is ready when the isolated
# interpreter this environment will be asked in imports it at a spec-satisfying version,
# and anything that interpreter does not already have came from the machine-readable
# registry, hashed by us and compared against the registry's own published digest.


class Refusal(Exception):
    """A named refusal. The name is the answer when the environment cannot be armed."""

    def __init__(self, verdict: str, detail: str) -> None:
        super().__init__(f"{verdict}: {detail}")
        self.verdict = verdict
        self.detail = detail


def normalize_name(name: str) -> str:
    """PEP 503 spelling. A name is a label; the label must be compared one way only."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


# --- an independent PEP 440 subset. `packaging` is not importable on this host, and a
# --- version comparison that cannot be tested is not a comparator. This one is pinned by
# --- tests: release ordering, pre/post/dev ordering, epochs.
_PRE_ORDER_SIZE = 3
_PRE_ORDER = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2, "preview": 2}
_VERSION_RE = re.compile(
    r"^\s*v?(?:(?P<epoch>\d+)!)?(?P<release>\d+(?:\.\d+)*)"
    r"(?:[-_.]?(?P<pre_l>a|b|c|rc|alpha|beta|pre|preview)[-_.]?(?P<pre_n>\d+)?)?"
    r"(?:-(?P<post_n1>\d+)|[-_.]?(?:post|rev|r)[-_.]?(?P<post_n2>\d+))?"
    r"(?:[-_.]?dev(?:[-_.]?(?P<dev_n>\d+))?)?"
    r"(?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?\s*$",
    re.IGNORECASE)


def version_key(text: str) -> tuple | None:
    """Ordering key for a PEP 440 version string, or None when it is not one.

    A pre-release sorts before its release, a post-release after, a dev-release before
    everything at that level -- the three orderings a dependency resolver actually uses.
    """
    m = _VERSION_RE.match(str(text or ""))
    if not m:
        return None
    release = tuple(int(part) for part in m.group("release").split("."))
    trimmed = list(release)
    while len(trimmed) > 1 and trimmed[-1] == 0:
        trimmed.pop()
    epoch = int(m.group("epoch") or 0)
    pre_l, pre_n = m.group("pre_l"), m.group("pre_n")
    if pre_l:
        pre = (_PRE_ORDER[pre_l.lower()], int(pre_n or 0))
    elif m.group("dev_n") and not (m.group("post_n1") or m.group("post_n2")):
        pre = (-1, 0)  # a bare dev release precedes every pre-release of that release
    else:
        pre = (_PRE_ORDER_SIZE, 0)  # no pre-release sorts after every pre-release
    post = int(m.group("post_n1") or m.group("post_n2") or 0) if (
        m.group("post_n1") or m.group("post_n2")) else -1
    # `4dev` and `4.0.dev1` are dev releases (no dev number means .dev0 in PEP 440), and a
    # dev release sorts BELOW its release. `m.group("dev_n")` is None both when no `dev`
    # appears at all and when it appears without a number, so the two are distinguished by
    # the text, not by the group.
    has_dev = "dev" in m.group(0).lower()
    dev = (int(m.group("dev_n") or 0)) if has_dev else float("inf")
    return (epoch, tuple(trimmed), pre, post, dev)


def _specifier_parts(specifier: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for chunk in (specifier or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(===|==|!=|~=|>=|<=|>|<)\s*(\S+)$", chunk)
        if not m:
            raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                          f"specifier {chunk!r} is not one this reader understands")
        out.append((m.group(1), m.group(2)))
    return out


def specifier_satisfied(version: str, specifier: str) -> bool:
    key = version_key(version)
    if key is None:
        return False
    for op, raw in _specifier_parts(specifier):
        if op == "===":
            if str(version).strip() != raw:
                return False
            continue
        if op in ("==", "!=") and raw.endswith(".*"):
            # prefix match: `==2.0.*` accepts 2.0, 2.0.4, 2.0rc1 -- the release prefix only
            prefix = tuple(int(p) for p in raw[:-2].split(".") if p.isdigit())
            release = tuple(int(p) for p in re.match(r"^[^0-9]*([0-9.]+)", str(version)).group(1)
                            .rstrip(".").split(".")) if re.match(r"^[^0-9]*[0-9]", str(version)) else ()
            hit = bool(prefix) and release[:len(prefix)] == prefix
            if (op == "==") != hit:
                return False
            continue
        bound = version_key(raw)
        if bound is None:
            raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                          f"bound {raw!r} is not a version this reader understands")
        if op == "==" and not key == bound:
            return False
        if op == "!=" and key == bound:
            return False
        if op == ">" and not key > bound:
            return False
        if op == ">=" and not key >= bound:
            return False
        if op == "<" and not key < bound:
            return False
        if op == "<=" and not key <= bound:
            return False
        if op == "~=":
            release_bound = version_key(raw)
            if release_bound is None or not key >= release_bound:
                return False
            parts = raw.split(".")
            if len(parts) < 2:
                raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                              f"~={raw} needs at least two release components")
            upper = int(parts[0]) + 1 if len(parts) == 2 else int(parts[0])
            if len(parts) > 2:
                upper_key = version_key(".".join([parts[0], str(int(parts[1]) + 1)]))
            else:
                upper_key = version_key(str(upper))
            if upper_key is not None and not key < upper_key:
                return False
    return True


_REQUIREMENT_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<rest>.*)$")


def parse_requirement(raw: str) -> dict[str, Any]:
    """One declaration, as the environment wrote it. Direct URLs and extras-bearing
    declarations are refused by name rather than guessed: an invented requirement is an
    invented environment."""
    text = (raw or "").split("#", 1)[0].strip()
    if not text:
        return {}
    if "@" in text.split(";")[0] or "://" in text:
        raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                      f"{raw!r} is a direct reference; only registry requirements are brokered")
    body = text.split(";", 1)[0].strip()
    marker = text.split(";", 1)[1].strip() if ";" in text else ""
    m = _REQUIREMENT_RE.match(body)
    if not m:
        raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD", f"{raw!r} is not a requirement")
    name, rest = m.group("name"), m.group("rest").strip()
    extra: list[str] = []
    if rest.startswith("["):
        close = rest.find("]")
        if close < 0:
            raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD", f"{raw!r} has an unclosed extra")
        extra = [e.strip() for e in rest[1:close].split(",") if e.strip()]
        rest = rest[close + 1:].strip()
    if rest.startswith("(") and rest.endswith(")"):
        rest = rest[1:-1].strip()
    if rest and not rest.startswith((">", "<", "=", "!", "~")):
        raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                      f"{raw!r} carries text this reader does not read as a specifier")
    _specifier_parts(rest)  # raises if unsupported
    return {"raw": raw.strip(), "name": name, "normalized": normalize_name(name),
            "specifier": rest, "extras": extra, "marker": marker}


def _requirements_lines(path: pathlib.Path) -> list[str]:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r", "-e", "--", "-c")):
            continue  # nested/inclusion files are a different declaration; refused if seen alone
        lines.append(line)
    return lines


def read_declarations(tree: pathlib.Path,
                      pyproject: pathlib.Path | None) -> dict[str, Any]:
    """What this environment says it needs, from its own files. Runtime dependencies plus
    declared test dependencies; nothing inferred from popularity or from our own history."""
    sources: list[str] = []
    raw_deps: list[str] = []
    declared = read_toml_project(pyproject) if pyproject is not None and pyproject.is_file() else {}
    project_name = None
    if pyproject is not None and pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\s*name\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
        project_name = m.group(1) if m else None
        if declared.get("declared_deps"):
            raw_deps.extend(declared["declared_deps"])
            sources.append("pyproject.toml:[project].dependencies")
    for path in sorted(tree.glob("requirements*.txt")):
        lines = _requirements_lines(path)
        if lines:
            raw_deps.extend(lines)
            sources.append(path.name)
    for path in (tree / "setup.py",):
        if path.is_file():
            sources.append("setup.py")
    test_deps = _test_group_declarations(pyproject) if pyproject is not None and pyproject.is_file() else []
    if test_deps:
        raw_deps.extend(test_deps)
        sources.append("pyproject.toml:test-groups")

    required: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    extras: list[str] = []
    skipped: list[str] = []
    for raw in raw_deps:
        parsed = parse_requirement(raw)
        if not parsed:
            continue
        if project_name and parsed["normalized"] == normalize_name(project_name):
            # `requests[socks]` in a test group is the project naming one of ITS OWN extras:
            # the extra is a declaration of what the tests need, and dropping it whole is
            # how a genuinely incomplete environment gets blamed on the tests. The fourth
            # live trial was exactly this (8 proxy tests failing on missing SOCKS support).
            extras.extend(parsed["extras"])
            parsed["self"] = True
            required.append(parsed)
            continue
        if marker_ok(parsed.get("marker", "")) is False:
            # a declaration whose marker excludes this interpreter is not a dependency here.
            # Measured: black's uvloop extra declares winloop for win32, and refusing the
            # whole environment because a Windows wheel has no linux tag would be the broker
            # blaming the environment for stating itself correctly.
            skipped.append(parsed["raw"])
            continue
        marker = (parsed["normalized"], parsed["specifier"])
        if marker in seen:
            continue
        seen.add(marker)
        required.append(parsed)
    extras.extend(group_own_extras(pyproject, project_name))
    declared_installs = declared_extras_in(tree, pyproject)
    extras.extend(declared_installs)
    if declared_installs:
        sources.append("project-declared self-install extras: " + ",".join(declared_installs))
    extras = list(dict.fromkeys(extras))
    if extras:
        for raw in own_extras(pyproject, extras) if pyproject is not None else []:
            parsed = parse_requirement(raw)
            if not parsed:
                continue
            if marker_ok(parsed.get("marker", "")) is False:
                skipped.append(parsed["raw"])
                continue
            if (parsed["normalized"], parsed["specifier"]) in seen:
                continue
            seen.add((parsed["normalized"], parsed["specifier"]))
            required.append(parsed)
        sources.append("pyproject.toml:[project.optional-dependencies]:"
                       + ",".join(sorted(set(extras))))
    return {"sources": sources, "required": required, "project_name": project_name,
            "self_extras": extras, "skipped_for_this_interpreter": skipped}


def own_extras(pyproject: pathlib.Path, extras: Sequence[str]) -> list[str]:
    """The requirements a project lists for its own named extras, read the standard way."""
    table = declared_table(pyproject)
    if table is None:
        return []
    optional = ((table.get("project") or {}).get("optional-dependencies") or {})
    out: list[str] = []
    for extra in dict.fromkeys(extras):
        out.extend(d for d in (optional.get(extra) or []) if isinstance(d, str))
    return out


def group_own_extras(pyproject: pathlib.Path | None, project_name: str | None) -> list[str]:
    """Own extras referenced by any test-ish dependency group, including groups reached
    through an `{include-group = ...}` reference. A declaration can sit one indirection
    away, and black's own suite reaches its extras exactly that way."""
    if pyproject is None or not project_name:
        return []
    table = declared_table(pyproject) or {}
    groups = table.get("dependency-groups") or {}
    own = normalize_name(project_name)
    seen: set[str] = set()
    out: list[str] = []

    def walk(name: str, depth: int = 0) -> None:
        if depth > 6 or name in seen:
            return
        seen.add(name)
        for entry in groups.get(name) or []:
            if isinstance(entry, dict):
                inner = entry.get("include-group")
                if isinstance(inner, str):
                    walk(inner, depth + 1)
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\[([^\]]+)\]", str(entry).strip())
            if m and normalize_name(m.group(1)) == own:
                out.extend(e.strip() for e in m.group(2).split(",") if e.strip())

    for name in groups:
        if re.search(r"test", str(name), re.I):
            walk(str(name))
    return out


def declared_extras_in(tree: pathlib.Path, pyproject: pathlib.Path | None) -> list[str]:
    """Extras the project's own test environment says to install, e.g. tox's
    `commands = pip install -e .[d]`.

    A declaration, not an inference: black's unit-test environment installs `.[d]` because
    its suite needs aiohttp, and nothing else in the manifest says so. Reading the
    environment's own command honours the claim instead of guessing at it. Only extras this
    manifest actually declares are returned: a CI matrix fragment is not an extra, and
    installing an undeclared name would be inventing a package.
    """
    if pyproject is None or not pyproject.is_file():
        return []
    table = declared_table(pyproject) or {}
    declared_names = set(((table.get("project") or {}).get("optional-dependencies") or {}))
    if not declared_names:
        return []
    extras: list[str] = []

    def absorb(text: str) -> None:
        for m in re.finditer(
                r"(?:-e\s+)?(?:\.|\$\{toxinidir\})\[([A-Za-z0-9_,\s.-]+)\]", text):
            extras.extend(e.strip() for e in m.group(1).split(",") if e.strip())

    for entry in ((((table.get("tool") or {}).get("tox") or {}).get("testenv") or {})
                  .get("commands") or []):
        if isinstance(entry, list):
            absorb(" ".join(str(x) for x in entry))
    # tox's modern config is TOML, and it names extras as data rather than inside a
    # command string: `extras = [ "completion" ]`. Measured on tox-dev/tox, whose suite
    # imports argcomplete only because its own tox.toml installs the `completion` extra --
    # a reader that only scanned command strings missed it and the suite could not collect.
    for name in ("tox.toml",):
        config = tree / name
        if not config.is_file():
            continue
        config_table = declared_table(config) or {}
        for env_table in (config_table.get("env") or {}).values():
            if not isinstance(env_table, dict):
                continue
            listed = env_table.get("extras")
            if isinstance(listed, list):
                extras.extend(x.strip() for x in listed
                              if isinstance(x, str) and x.strip())
    # tox's modern config is TOML, and it names extras as data rather than inside a
    # command string: `extras = [ "completion" ]`. Measured on tox-dev/tox, whose suite
    # imports argcomplete only because its own tox.toml installs the `completion` extra --
    # a reader that only scanned command strings missed it and the suite could not collect.
    for name in ("tox.toml",):
        config = tree / name
        if not config.is_file():
            continue
        config_table = declared_table(config) or {}
        for env_table in (config_table.get("env") or {}).values():
            if not isinstance(env_table, dict):
                continue
            listed = env_table.get("extras")
            if isinstance(listed, list):
                extras.extend(x.strip() for x in listed
                              if isinstance(x, str) and x.strip())
    tox_ini = tree / "tox.ini"
    if tox_ini.is_file():
        absorb(tox_ini.read_text(encoding="utf-8", errors="replace"))
    for name in ("Makefile", "makefile", "GNUmakefile"):
        if (tree / name).is_file():
            absorb((tree / name).read_text(encoding="utf-8", errors="replace"))
    workflows = tree / ".github" / "workflows"
    if workflows.is_dir():
        for path in sorted(workflows.glob("*.y*ml")):
            absorb(path.read_text(encoding="utf-8", errors="replace"))
    return [e for e in dict.fromkeys(extras) if e in declared_names]


def _test_group_declarations(pyproject: pathlib.Path) -> list[str]:
    """The project's own test-dependency groups, read with the same reader the rest of the
    tree uses, so a group declared here is not invisible to arming."""
    try:
        from canonical.runtime import environment_fit_v1 as fit
        return [d for d in fit._declared_python_test_deps(pyproject.parent) if d]
    except Exception:
        return []


# --- what a verified artifact says IT needs. The declaration lives inside the bytes we
# --- just confirmed, or in the registry's own requires_dist for those same bytes; both are
# --- machine-readable statements about the artifact, not our opinion about it.
_MARKER_ENV = {
    "python_version": f"{sys.version_info[0]}.{sys.version_info[1]}",
    "python_full_version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
    "platform_system": __import__("platform").system(),
    "platform_machine": __import__("platform").machine(),
    "sys_platform": sys.platform,
    "os_name": __import__("os").name,
    "implementation_name": sys.implementation.name,
    "platform_python_implementation": __import__("platform").python_implementation(),
}
_MARKER_OP = re.compile(r'^\s*([A-Za-z_.]+)\s*(===|==|!=|>=|<=|~=|>|<)\s*["\']([^"\']*)["\']\s*$')


def _marker_clause(clause: str) -> bool | None:
    """True/False, or None when this reader cannot evaluate the clause."""
    clause = clause.strip().strip("()").strip()
    if not clause:
        return True
    m = _MARKER_OP.match(clause)
    if not m:
        return None
    name, op, raw = m.group(1), m.group(2), m.group(3)
    here = _MARKER_ENV.get(name)
    if here is None:
        return None
    if name.startswith("python"):
        left, right = version_key(here), version_key(raw)
    else:
        left, right = here, raw
    if left is None or right is None:
        return None
    compare = {"==": left == right, "===": left == right, "!=": left != right,
               ">": left > right, ">=": left >= right, "<": left < right,
               "<=": left <= right, "~=": left >= right}
    return compare[op]


def marker_ok(marker: str) -> bool | None:
    """A dependency marker against THIS interpreter. `extra` markers are not evaluated
    here: an extra is a decision (install it or not), not a fact, and arming installs only
    what the environment needs unconditionally."""
    text = (marker or "").strip()
    if not text:
        return True
    if re.search(r"\bextra\b", text):
        return False
    for or_part in re.split(r"\bor\b", text):
        results = [_marker_clause(c) for c in re.split(r"\band\b", or_part)]
        if any(r is None for r in results):
            return None
        if all(results):
            return True
    return False


def requires_dist(payload: Mapping[str, Any]) -> list[str]:
    declared = (payload.get("info") or {}).get("requires_dist") or []
    return [d for d in declared if isinstance(d, str)]


# --- the registry tier: machine-readable facts, two independent readers
def fetch_json_urllib(url: str, timeout: float = 30.0) -> dict[str, Any]:
    import urllib.request
    request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                   "User-Agent": "brain-env-broker/2"})
    with urllib.request.urlopen(request, timeout=timeout) as handle:
        return json.loads(handle.read().decode("utf-8", "replace"))


def fetch_bytes_urllib(url: str, timeout: float = 120.0) -> bytes:
    import urllib.request
    request = urllib.request.Request(url, headers={"User-Agent": "brain-env-broker/2"})
    with urllib.request.urlopen(request, timeout=timeout) as handle:
        return handle.read()


_LEGACY_MANYLINUX = {"manylinux1": (2, 5), "manylinux2010": (2, 12), "manylinux2014": (2, 17)}


def _glibc_at_least(major: int, minor: int) -> bool:
    import platform as _platform
    try:
        _, version = _platform.libc_ver()
        here = tuple(int(p) for p in version.split(".")[:2])
    except (ValueError, TypeError):
        return False
    return here >= (major, minor)


def _platform_accepts(plat: str) -> bool:
    """Whether one platform tag can run HERE. The first live trial caught the previous
    version accepting an aarch64 wheel on an x86_64 host and letting pip discover the
    mistake -- a compatibility check that defers to the install is not a check. The tag
    states its architecture and, when it is a linux tag, its C-library floor; both are
    compared against this host."""
    import platform as _platform
    if plat in ("any", "none"):
        return True
    machine = _platform.machine().lower()
    aliases = {"x86_64": {"x86_64", "amd64"}, "amd64": {"x86_64", "amd64"},
               "aarch64": {"aarch64", "arm64"}, "arm64": {"aarch64", "arm64"}}
    ok_arches = aliases.get(machine, {machine})
    # architecture is a suffix of the tag and may itself contain an underscore (x86_64)
    if not any(plat.endswith("_" + arch) for arch in ok_arches):
        return False
    for prefix, floor in _LEGACY_MANYLINUX.items():
        if plat.startswith(prefix + "_"):
            return _glibc_at_least(*floor)
    m = re.match(r"^manylinux_(\d+)_(\d+)_", plat)
    if m:
        return _glibc_at_least(int(m.group(1)), int(m.group(2)))
    if plat.startswith(("linux_", "linux2_")):
        return True
    return False

def _wheel_tags_ok(filename: str) -> int:
    """0 = unusable, 1 = universal py3, 2 = this interpreter via abi3, 3 = exact."""
    stem = filename[:-4] if filename.lower().endswith(".whl") else filename
    parts = stem.split("-")
    if len(parts) < 5:
        return 0
    py, abi, plat = parts[-3], parts[-2], parts[-1]
    hosts = f"cp{sys.version_info[0]}{sys.version_info[1]}"
    # a wheel may compress several platform tags with dots: any one acceptable tag is enough
    if not _platform_accepts(plat) and not any(
            _platform_accepts(alt) for alt in plat.split(".") if alt):
        return 0
    plat = next((alt for alt in plat.split(".") if _platform_accepts(alt)), plat)
    if py in ("py2.py3", "py3") and abi == "none" and plat == "any":
        return 1
    if py == hosts and abi == hosts:
        return 3
    if py == hosts and abi == "none":
        return 2
    m = re.match(r"^cp3(\d+)$", py or "")
    if m and abi == "abi3" and int(m.group(1)) <= sys.version_info[1]:
        return 2
    if py in ("py2.py3", "py3") and abi == "none":
        return 2
    return 0


def choose_artifact(payload: Mapping[str, Any], requirement: Mapping[str, Any],
                    base_url: str) -> dict[str, Any]:
    """The newest release that satisfies the declaration AND ships a wheel this interpreter
    can run. A release with only an sdist has no bytes a reader can verify against the
    registry's own statement of the same file, so it is not a candidate."""
    name = requirement["name"]
    specifier = requirement["specifier"]
    releases = payload.get("releases")
    candidates: list[dict[str, Any]] = []
    if isinstance(releases, Mapping) and releases:
        for version, files in releases.items():
            key = version_key(version)
            if key is None:
                continue
            try:
                if not specifier_satisfied(version, specifier):
                    continue
            except Refusal:
                raise
            best: dict[str, Any] | None = None
            best_rank = 0
            for entry in files or []:
                if entry.get("packagetype") != "bdist_wheel":
                    continue
                if entry.get("yanked"):
                    continue
                rank = _wheel_tags_ok(entry.get("filename", ""))
                if rank > best_rank:
                    best_rank, best = rank, entry
            if best is not None:
                candidates.append({"version": version, "key": key, "rank": best_rank,
                                   "file": best})
    else:
        info = payload.get("info") or {}
        version = info.get("version")
        if version and specifier_satisfied(version, specifier):
            for entry in payload.get("urls") or []:
                if entry.get("packagetype") != "bdist_wheel" or entry.get("yanked"):
                    continue
                rank = _wheel_tags_ok(entry.get("filename", ""))
                if rank:
                    candidates.append({"version": version, "key": version_key(version),
                                       "rank": rank, "file": entry})
                    break
    if not candidates:
        raise Refusal("REFUSE__NO_COMPATIBLE_VERIFIED_ARTIFACT",
                      f"{name}{specifier} has no wheel this interpreter can run and whose "
                      f"bytes the registry states a digest for")
    winners = [c for c in candidates if c["key"] == max(c["key"] for c in candidates)]
    winners.sort(key=lambda c: c["rank"], reverse=True)
    chosen = winners[0]
    file = chosen["file"]
    url = file.get("url") or f"{base_url}/{name}/{chosen['version']}/{file.get('filename')}"
    digest = (file.get("digests") or {}).get("sha256")
    if not digest:
        raise Refusal("REFUSE__NO_COMPATIBLE_VERIFIED_ARTIFACT",
                      f"{name} {chosen['version']} ships a wheel with no published sha256")
    return {"name": name, "version": chosen["version"], "filename": file.get("filename"),
            "url": url, "sha256": digest, "size": file.get("size"),
            "requires_python": file.get("requires_python") or (payload.get("info") or {}).get("requires_python")}


# --- the isolation: an interpreter outside the tree, reused across runs
# A distribution name is not a module name, and the mapping is the package's own choice:
# `MarkupSafe` installs `markupsafe`, `pytest-xdist` installs `xdist`, `python-dotenv`
# installs `dotenv`. No naming rule recovers that. The wheel does know -- it lists its own
# top-level modules -- so the import check reads the mapping out of the verified bytes
# instead of guessing it. Three live trials went 60 artifacts deep finding these one at a
# time; one wheel read finds all of them at once.
_PROBE = ("import json,sys,importlib\n"
          "from importlib import metadata\n"
          "want=json.loads(sys.argv[1])\n"
          "out={}\n"
          "for n,modules in want.items():\n"
          "    try: version=metadata.version(n)\n"
          "    except Exception: out[n]={'version':None,'import':'no-metadata','module':None}; continue\n"
          "    state='no-importable-module'; hit=None\n"
          "    for module in modules or []:\n"
          "        try:\n"
          "            importlib.import_module(module); state='ok'; hit=module; break\n"
          "        except ModuleNotFoundError as exc:\n"
          "            state='ModuleNotFoundError'\n"
          "            if module.split('.')[0] == getattr(exc, 'name', None): continue\n"
          "        except Exception as exc: state=type(exc).__name__; hit=module; break\n"
          "    out[n]={'version':version,'import':state,'module':hit}\n"
          "print(json.dumps(out))\n")


_HOST_HOOKS = {
    "pytest": re.compile(r"^def\s+pytest_\w+\s*\(", re.MULTILINE),
    "pytest_plugins": re.compile(r"^pytest_plugins\s*=", re.MULTILINE),
    "nox": re.compile(r"@nox\.", re.MULTILINE),
}


def declared_entry_point_hosts(wheel_path: pathlib.Path) -> list[str]:
    """Entry-point groups this wheel registers, other than scripts. Each group name is a
    host that loads the artifact itself (`matplotlib.backend`, `pytest11`)."""
    import zipfile
    groups: list[str] = []
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            for member in zf.namelist():
                if member.endswith(".dist-info/entry_points.txt"):
                    for line in zf.read(member).decode("utf-8", "replace").splitlines():
                        m = re.match(r"^\[([^\]]+)\]\s*$", line)
                        if m and m.group(1) not in ("console_scripts", "gui_scripts"):
                            groups.append(m.group(1))
    except (OSError, zipfile.BadZipFile):
        return []
    return groups


def plugin_host(wheel_path: pathlib.Path) -> str | None:
    """Which host application loads this artifact as a plugin, if any -- read from the
    artifact's own source, which is inside the hash we verified.

    A plugin is not a module the project imports: it is a module its HOST imports, and the
    plugin contract means the host must NOT be declared as a dependency. So "does it import
    standalone" is the wrong question for one, and asking it refused correct environments
    twice in the live trials (`matplotlib-inline`, `detect-test-pollution`, both plugins that
    import their host at module level and declare it nowhere). Two pieces of evidence inside
    the verified bytes answer it: the host hooks the plugin registers in its own source, and
    the entry-point group it declares (which IS a host saying "load me").
    """
    import zipfile
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            for member in zf.namelist():
                if not member.endswith(".py"):
                    continue
                try:
                    source = zf.read(member).decode("utf-8", "replace")
                except (OSError, KeyError):
                    continue
                for host, pattern in _HOST_HOOKS.items():
                    if pattern.search(source):
                        return host
    except (OSError, zipfile.BadZipFile):
        return None
    declared = declared_entry_point_hosts(wheel_path)
    if declared:
        return declared[0]
    return None


def top_level_modules(wheel_path: pathlib.Path) -> list[str]:
    """The module names this artifact actually provides, read from inside the bytes we
    hash-checked. A wheel's file list is the package's own statement about itself."""
    import zipfile
    names: list[str] = []
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            listing = zf.namelist()
            for member in listing:
                if member.endswith(".dist-info/top_level.txt"):
                    for line in zf.read(member).decode("utf-8", "replace").splitlines():
                        line = line.strip()
                        if line and line not in names:
                            names.append(line)
    except (OSError, zipfile.BadZipFile):
        return []
    if names:
        return names
    for member in listing:
        head = member.split("/", 1)[0]
        if head.endswith((".dist-info", ".data", "..")) or "/" not in member:
            if member.endswith(".py") and "/" not in member:
                stem = member[:-3]
                if stem not in names:
                    names.append(stem)
            continue
        if head not in names:
            names.append(head)
    return [n for n in names if not n.startswith("_")] or names


def fallback_modules(name: str) -> list[str]:
    base = re.sub(r"[-_.]+", "_", name)
    return list(dict.fromkeys([base, name.replace("-", "_"), base.lower()]))


def isolation_python(tree: pathlib.Path, timeout: float = TIME_BUDGET,
                     fresh: bool = False) -> tuple[str, bool]:
    from canonical.runtime import environment_fit_v1 as fit
    env_dir = fit._env_dir(str(tree))
    python = env_dir / "venv" / "bin" / "python"
    if fresh and python.is_file():
        import shutil
        shutil.rmtree(env_dir, ignore_errors=True)
    if python.is_file():
        return str(python), False
    env_dir.mkdir(parents=True, exist_ok=True)
    try:
        done = subprocess.run([sys.executable, "-m", "venv", str(env_dir / "venv")],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("REFUSE__ISOLATION_ENVIRONMENT_UNAVAILABLE",
                      "an isolated interpreter could not be created")
    if done.returncode != 0 or not python.is_file():
        raise Refusal("REFUSE__ISOLATION_ENVIRONMENT_UNAVAILABLE",
                      (done.stderr or done.stdout or "").strip()[:200])
    return str(python), True


def installed_versions(python: str, names: Sequence[str], tree: pathlib.Path,
                       timeout: float = 120.0) -> dict[str, str | None]:
    """Version as the interpreter itself reports it, or None."""
    if not names:
        return {}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tree),
           "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        done = subprocess.run([python, "-c", _PROBE,
                               json.dumps({n: fallback_modules(n) for n in names})],
                              capture_output=True, text=True, timeout=timeout, env=env,
                              cwd=str(tree))
    except (OSError, subprocess.SubprocessError):
        return {name: None for name in names}
    if done.returncode != 0:
        return {name: None for name in names}
    try:
        raw = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {name: None for name in names}
    return {name: (raw.get(name) or {}).get("version") for name in names}


def probe_imports(python: str, names: Sequence[str], tree: pathlib.Path,
                  timeout: float = 120.0,
                  modules: Mapping[str, Sequence[str]] | None = None
                  ) -> dict[str, dict[str, Any]]:
    """Version AND import state, because `importlib.metadata` answers "a file claims this
    version" while an import answers "this module runs here". The second live trial proved
    the difference: pytest was at 9.2.0 with pluggy absent, so the metadata said a version
    and the module said ModuleNotFoundError. An environment that is versioned but not
    importable is not armed."""
    if not names:
        return {}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tree),
           "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        wanted = {name: list((modules or {}).get(name) or fallback_modules(name))
                  for name in names}
        done = subprocess.run([python, "-c", _PROBE, json.dumps(wanted)],
                              capture_output=True, text=True, timeout=timeout, env=env,
                              cwd=str(tree))
    except (OSError, subprocess.SubprocessError):
        return {name: {"version": None, "import": "probe-failed"} for name in names}
    if done.returncode != 0:
        return {name: {"version": None, "import": "probe-failed"} for name in names}
    try:
        raw = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {name: {"version": None, "import": "probe-failed"} for name in names}
    return {name: raw.get(name) or {"version": None, "import": "absent"} for name in names}


def _pip_install(python: str, wheel: pathlib.Path, tree: pathlib.Path,
                 timeout: float = TIME_BUDGET) -> dict[str, Any]:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tree),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    started = time.perf_counter()
    argv = [python, "-m", "pip", "install", "--no-deps", "--no-index",
            "--disable-pip-version-check", "--no-cache-dir", "--quiet", str(wheel)]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=env, cwd=str(tree))
    except subprocess.TimeoutExpired:
        return {"command": argv, "exit_code": None, "ok": False, "detail": "TIMEOUT",
                "seconds": round(time.perf_counter() - started, 4)}
    except OSError as exc:
        return {"command": argv, "exit_code": None, "ok": False, "detail": str(exc)[:200],
                "seconds": round(time.perf_counter() - started, 4)}
    return {"command": argv, "exit_code": done.returncode, "ok": done.returncode == 0,
            "seconds": round(time.perf_counter() - started, 4),
            "tail": (done.stdout + done.stderr)[-400:]}


def arm(tree: pathlib.Path, memory_path: pathlib.Path,
        fetch_json: Any = None, fetch_bytes: Any = None,
        work_dir: pathlib.Path | None = None) -> dict[str, Any]:
    """The env-ready contract. Registry facts in, execution-confirmed records out.

    Transitives are resolved from the verified bytes' own declarations, not by trusting a
    resolver's word: the wheel's METADATA (inside the hash we checked) and the registry's
    requires_dist for that same release are read, marker-filtered against this interpreter,
    and fetched through the same check. The second live trial is why: pytest was installed
    at 9.2.0 while pluggy was absent, so arming reported success on an environment whose
    test runner could not import. A dependency is ready only when it imports.
    """
    started = time.perf_counter()
    fetch_json = fetch_json or fetch_json_urllib
    fetch_bytes = fetch_bytes or fetch_bytes_urllib
    pyproject = tree / "pyproject.toml"
    result: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY, "tree": str(tree),
                              "goal": "env-ready", "verdict": None, "from_memory": False,
                              "network": {"json_requests": 0, "artifact_downloads": 0,
                                          "bytes": 0}}

    declarations = read_declarations(tree, pyproject)
    result["declarations"] = {"sources": declarations["sources"],
                              "skipped_for_this_interpreter":
                                  declarations.get("skipped_for_this_interpreter") or [],
                              "required": [{k: r.get(k) for k in
                                            ("name", "specifier", "marker", "extras", "self")}
                                           for r in declarations["required"]]}
    required = [r for r in declarations["required"] if not r.get("self")]
    if not required:
        result["verdict"] = "ENVIRONMENT_READY_NO_DECLARED_DEPENDENCIES"
        result["records"] = []
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    manifest = read_toml_project(pyproject) if pyproject.is_file() else {}
    declared_build = manifest.get("build_requires") or []
    build_backend = manifest.get("build_backend")
    python, created = isolation_python(tree)
    result["isolation"] = {"python": python, "created": created}

    before = {name: state["version"] for name, state in
              probe_imports(python, [r["name"] for r in required], tree).items()}
    digest, evidence = evidence_digest(tree)
    result["evidence"] = evidence
    result["evidence_digest"] = digest

    memory = load_memory(memory_path)
    key = f"env-ready::{digest}"
    entry = memory["entries"].get(key)
    modules: dict[str, list[str]] = {}   # distribution -> the modules its own wheel lists

    # warm: every recorded dependency must still import at its recorded version. The
    # interpreter is asked, the memory is not believed.
    if entry:
        recorded = {rec["name"]: rec["version"] for rec in entry.get("records", [])
                    if rec.get("status") in ("SATISFIED_BY_HOST", "ACQUIRED_VERIFIED")}
        modules.update(entry.get("modules") or {})
        now = probe_imports(python, list(recorded), tree, modules=modules) if recorded else {}
        same = bool(recorded) and all(
            (now.get(name) or {}).get("version") == version
            and (now.get(name) or {}).get("import") == "ok"
            for name, version in recorded.items())
        result["from_memory"] = True
        result["recheck"] = {"ok": same,
                             "observed": {n: (now.get(n) or {}).get("version") for n in recorded}}
        if same:
            result["records"] = entry["records"]
            result["verdict"] = "ENVIRONMENT_BROKERED_FROM_MEMORY"
            result["seconds"] = round(time.perf_counter() - started, 4)
            return result
        memory["entries"].pop(key, None)
        result["from_memory"] = False

    records: list[dict[str, Any]] = []
    verified_names: list[str] = []

    def refuse(verdict: str, detail: str) -> dict[str, Any]:
        result["verdict"] = verdict
        result["detail"] = detail
        result["records"] = records
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    def acquire(requirement: Mapping[str, Any], depth: int = 0) -> None:
        """Fetch, hash, install and import-check one requirement, then recurse into what
        the verified bytes say they need."""
        nonlocal records
        name = requirement["name"]
        specifier = requirement.get("specifier") or ""
        state = probe_imports(python, [name], tree, modules=modules).get(name) or {}
        if state.get("version") and state.get("import") == "ok" and specifier_satisfied(
                state["version"], specifier):
            if not any(r["name"] == name for r in records):
                records.append({"name": name, "specifier": specifier,
                                "version": state["version"], "status": "SATISFIED_BY_HOST",
                                "source": "isolation", "import": "ok",
                                "verified_by_execution": True})
                verified_names.append(name)
            return
        if depth > 8:
            raise Refusal("REFUSE__DECLARATION_NOT_UNDERSTOOD",
                          f"dependency chain deeper than 8 from {name}; refusing to guess")
        try:
            payload = fetch_json(REGISTRY_JSON.format(name=name))
        except Exception as exc:
            text = str(exc)
            raise Refusal(
                "REFUSE__DEPENDENCY_NOT_ON_REGISTRY" if ("404" in text or "Not Found" in text)
                else "REFUSE__REGISTRY_UNREACHABLE", f"{name}: {text[:200]}")
        result["network"]["json_requests"] += 1
        artifact = choose_artifact(payload, {"name": name, "specifier": specifier},
                                   REGISTRY_JSON.format(name=name))
        blob = fetch_bytes(artifact["url"])
        result["network"]["artifact_downloads"] += 1
        result["network"]["bytes"] += len(blob)
        observed = hashlib.sha256(blob).hexdigest()
        if observed != artifact["sha256"]:
            raise Refusal("REFUSE__DIGEST_DISAGREE",
                          f"{artifact['filename']}: registry says {artifact['sha256']}, "
                          f"these bytes hash to {observed}")
        wheel_dir = (work_dir or (memory_path.parent / "wheels"))
        wheel_dir.mkdir(parents=True, exist_ok=True)
        wheel_path = wheel_dir / str(artifact["filename"])
        wheel_path.write_bytes(blob)
        install = _pip_install(python, wheel_path, tree)
        if not install["ok"]:
            result["install"] = install
            raise Refusal("REFUSE__INSTALL_FAILED",
                          f"{artifact['filename']}: {install.get('tail', '')[-200:]}")
        declared_modules = top_level_modules(wheel_path)
        if declared_modules:
            modules[name] = declared_modules  # the bytes say what they provide, before
                                              # anything is asked to import
        host = plugin_host(wheel_path)
        after = probe_imports(python, [name], tree, modules=modules).get(name) or {}
        if not after.get("version") or not specifier_satisfied(after["version"], specifier):
            raise Refusal("REFUSE__VERSION_CHECK_FAILED",
                          f"{name}: after installing {artifact['version']} the interpreter "
                          f"reads {after.get('version')!r}")
        record = {"name": name, "specifier": specifier, "version": after["version"],
                  "status": "ACQUIRED_VERIFIED", "source": "registry",
                  "plugin_host": host,
                  "artifact": artifact["filename"], "size": len(blob),
                  "sha256_registry": artifact["sha256"], "sha256_observed": observed,
                  "import": None, "verified_by_execution": False}
        records = [r for r in records if r["name"] != name] + [record]
        verified_names.append(name)
        # A package is armed only once what IT declares is armed: this is the order the
        # second live trial demanded (pytest present, pluggy absent, metadata satisfied).
        wired = _artifact_requires(payload, artifact, wheel_path)
        for child in wired:
            if child["normalized"] in {normalize_name(v) for v in verified_names}:
                continue
            acquire(child, depth + 1)
        settled = probe_imports(python, [name], tree, modules=modules).get(name) or {}
        if settled.get("import") != "ok" and host:
            record["status"] = "PLUGIN_ARMED_IMPORTED_BY_HOST"
            record["plugin_host"] = host
            record["import"] = "deferred-to-host"
            record["detail"] = (f"a plugin for {host}: that host imports it, so its import is "
                                f"verified when the suite runs, not in isolation")
            return
        if settled.get("import") != "ok":
            raise Refusal("REFUSE__VERSION_CHECK_FAILED",
                          f"{name} {after['version']} installed but does not import: "
                          f"{settled.get('import')} -- its own dependencies are not armed")
        record["import"] = "ok"
        record["verified_by_execution"] = True

    try:
        for requirement in required:
            acquire(requirement)
    except Refusal as refusal:
        return refuse(refusal.verdict, refusal.detail)

    # the project installs itself: its own metadata is part of a ready environment
    project_name = declarations.get("project_name")
    build_requires = [d for d in (declared_build or []) if d]
    try:
        for raw in build_requires:
            parsed = parse_requirement(raw)
            if parsed and marker_ok(parsed.get("marker", "")) is not False:
                acquire(parsed)
    except Refusal as refusal:
        return refuse(refusal.verdict, refusal.detail)
    if build_with_wheel_package(build_backend):
        try:
            acquire({"name": "wheel", "specifier": "", "normalized": "wheel"})
        except Refusal as refusal:
            return refuse(refusal.verdict, refusal.detail)
    project_install = None
    if project_name and sets_up_a_distribution(tree, pyproject):
        project_install = install_project(python, tree, project_name, backend=build_backend,
                                          extras=declarations.get("self_extras") or [])
        seen_version = probe_imports(python, [project_name], tree,
                                     modules=modules).get(project_name) or {}
        # Version-from-history is a real limit: a shallow clone carries no tags, so
        # hatch-vcs/setuptools-scm fall back to 0.1.devN for a project whose version is
        # DYNAMIC. That is recorded rather than hidden, because the project's own metadata
        # then disagrees with itself and some of its tests will say so.
        version_source = "git-history"
        if "dev" in str(seen_version.get("version") or ""):
            # `4.67.16.dev4+g794908a7f` is a CORRECT git-derived version (four commits past
            # tag 4.67.15 at that commit). A wrong label here once sent a whole trial
            # chasing a cache bug that did not exist; the version was right all along.
            version_source = ("git-history (dev version derived from tags and commit count, "
                              "as the project's own build hook intends)")
        # A project that cannot build itself is a fact about the project, not evidence that
        # its dependencies are missing. Both facts are recorded; neither is inflated into
        # the other. (Refusing here would report an unarmed environment when the
        # environment is armed and the packaging is broken.)
        records.append({"name": project_name, "specifier": "the project itself",
                        "version": seen_version.get("version"),
                        "status": "PROJECT_INSTALLED" if project_install["ok"]
                                  else "PROJECT_NOT_INSTALLABLE",
                        "artifact": "<staged copy of the tree>",
                        "version_source": version_source,
                        "verified_by_execution": bool(seen_version.get("version")),
                        "detail": None if project_install["ok"]
                                  else (project_install.get("tail") or "")[-200:]})
    result["project_install"] = project_install

    final = probe_imports(python, [r["name"] for r in required], tree, modules=modules)
    deferred = {rec["name"] for rec in records
                if rec.get("status") == "PLUGIN_ARMED_IMPORTED_BY_HOST"}
    unmet = [name for name in [r["name"] for r in required]
             if not (final.get(name) or {}).get("version")
             # a plugin's import is its HOST's job: it is verified when the suite runs, so
             # this final gate must not demand what the plugin contract forbids
             or ((final.get(name) or {}).get("import") != "ok" and name not in deferred)
             or not specifier_satisfied((final.get(name) or {}).get("version") or "0",
                                        next(r["specifier"] for r in required
                                             if r["name"] == name))]
    if unmet:
        return refuse("REFUSE__VERSION_CHECK_FAILED",
                      "declarations not satisfied after arming: " + ", ".join(unmet))

    memory["entries"][key] = {
        "goal": "env-ready", "verdict": "ENVIRONMENT_BROKERED",
        "evidence_digest": digest, "records": records, "modules": modules,
        "isolation": "reused by path hash", "declarations": result["declarations"],
        "verified_versions": {n: (s or {}).get("version") for n, s in final.items()},
    }
    save_memory(memory, memory_path)
    result["records"] = records
    result["verified_versions"] = {n: (s or {}).get("version") for n, s in final.items()}
    result["from_host_before_arming"] = before
    result["verdict"] = "ENVIRONMENT_BROKERED"
    result["seconds"] = round(time.perf_counter() - started, 4)
    return result


def _artifact_requires(payload: Mapping[str, Any], artifact: Mapping[str, Any],
                       wheel_path: pathlib.Path) -> list[dict[str, Any] | None]:
    """What this exact artifact declares it needs, filtered by this interpreter's markers.

    Read from the bytes we verified (the wheel's own METADATA), falling back to the
    registry's requires_dist for the same release. Either source describes the artifact we
    hash-checked; neither is a resolver's opinion about the whole tree."""
    declared: list[str] = []
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            for member in zf.namelist():
                if member.endswith(".dist-info/METADATA"):
                    text = zf.read(member).decode("utf-8", "replace")
                    declared = [line.split(":", 1)[1].strip() for line in text.splitlines()
                                if line.lower().startswith("requires-dist:")]
                    break
    except (OSError, zipfile.BadZipFile):
        declared = []
    if not declared:
        declared = requires_dist(payload)
    out: list[dict[str, Any] | None] = []
    for raw in declared:
        try:
            parsed = parse_requirement(raw)
        except Refusal:
            out.append(None)
            continue
        if not parsed:
            continue
        if parsed.get("extras"):
            continue  # an extra is a decision, not a fact about what is needed here
        if marker_ok(parsed.get("marker", "")) is not True:
            continue
        out.append(parsed)
    return out


def sets_up_a_distribution(tree: pathlib.Path, pyproject: pathlib.Path | None) -> bool:
    """Whether this project states how it is built. That statement -- a [build-system]
    table or a setup.py -- is the project declaring it is a distributable. A manifest that
    only lists dependencies says nothing about being built, and building it anyway would be
    inventing a package the environment never asked for."""
    if pyproject is not None and pyproject.is_file():
        if re.search(r"^\[build-system\]", pyproject.read_text(encoding="utf-8",
                                                                errors="replace"), re.MULTILINE):
            return True
    return (tree / "setup.py").is_file()


def build_with_wheel_package(backend: str | None) -> bool:
    """setuptools reaches its wheel only through the `wheel` package; pip's build isolation
    supplies it and `--no-build-isolation` (used so nothing is fetched behind our back,
    unverified) does not. Other backends build their own wheel."""
    return bool(backend) and str(backend).startswith("setuptools")


def install_project(python: str, tree: pathlib.Path, name: str,
                    backend: str | None = None, extras: Sequence[str] | None = None,
                    timeout: float = max(TIME_BUDGET, 900.0)) -> dict[str, Any]:
    """Make the project's OWN distribution metadata present, without writing into the tree.

    The third live trial is why this exists: 246 of flask's tests passed in a correctly
    armed isolation and one failed with `No package metadata was found for flask`. The
    declaration was honoured and the environment was still not the environment the project
    expects, because the project expects to be installed. Building from a copy keeps the
    repository exactly as it was found -- a build artifact inside the tree is a change to
    the tree."""
    import shutil
    import tempfile
    staging = pathlib.Path(tempfile.mkdtemp(prefix="brain-project-"))
    copied = staging / "src"
    try:
        shutil.copytree(tree, copied, symlinks=True,
                        ignore=shutil.ignore_patterns("*.egg-info", "build", "dist",
                                                      "__pycache__", ".venv", "node_modules"))
    except OSError as exc:
        return {"ok": False, "detail": f"could not stage the project: {exc}"[:200]}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(staging),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    started = time.perf_counter()
    target = str(copied)
    if extras:
        target = f"{copied}[{','.join(extras)}]"
    argv = [python, "-m", "pip", "install", "--no-deps", "--no-build-isolation",
            "--disable-pip-version-check", "--no-cache-dir", "--quiet", target]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=env, cwd=str(staging))
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "detail": str(exc)[:200], "seconds": round(time.perf_counter() - started, 4)}
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"command": argv[:-1] + ["<staged copy of the tree>"],
            "exit_code": done.returncode, "ok": done.returncode == 0,
            "seconds": round(time.perf_counter() - started, 4),
            "tail": (done.stdout + done.stderr)[-400:]}


def existing_isolation_python(tree: pathlib.Path) -> str | None:
    """The isolation this tree was armed in, if it exists. Read-only: a goal that has not
    been armed is refused by the parser's own answer, never silently provisioned here."""
    try:
        from canonical.runtime import environment_fit_v1 as fit
        python = fit._env_dir(str(tree)) / "venv" / "bin" / "python"
    except Exception:
        return None
    return str(python) if python.is_file() else None


# ---------------------------------------------------------------- memory
def load_memory(path: pathlib.Path) -> dict[str, Any]:
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            if data.get("schema") == CACHE_SCHEMA:
                return data
        except (OSError, ValueError):
            pass
    return {"schema": CACHE_SCHEMA, "entries": {}}


def save_memory(memory: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=1, sort_keys=True))


def broker(tree: pathlib.Path, goal: str, memory_path: pathlib.Path = DEFAULT_MEMORY,
           *, fetch_json: Any = None, fetch_bytes: Any = None,
           work_dir: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY,
                              "tree": str(tree), "goal": goal, "verdict": None}
    if goal not in GOAL_KINDS:
        result["verdict"] = "REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    if not tree.is_dir():
        result["verdict"] = "REFUSE__NOT_A_PYTHON_ENVIRONMENT"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    pyproject = tree / "pyproject.toml"
    setup_py = tree / "setup.py"
    requirements = sorted(tree.glob("requirements*.txt"))
    if not pyproject.is_file() and not setup_py.is_file() and not requirements:
        result["verdict"] = "REFUSE__NOT_A_PYTHON_ENVIRONMENT"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    declared = read_toml_project(pyproject) if pyproject.is_file() else {
        "present": False, "requires_python": None, "declared_deps": [], "build_backend": None}
    floor_ok, floor_note = python_floor_ok(declared.get("requires_python"))
    if not floor_ok:
        result["interpreter"] = {"version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
                                 "check": floor_note, "ok": floor_ok}
        result["verdict"] = "REFUSE__REQUIRES_PYTHON_NOT_MET_LOCALLY"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    if goal == "env-ready":
        try:
            got = arm(tree, memory_path, fetch_json=fetch_json, fetch_bytes=fetch_bytes,
                      work_dir=work_dir)
        except Refusal as refusal:
            got = {"schema": SCHEMA, "authority": AUTHORITY, "tree": str(tree),
                   "goal": goal, "verdict": refusal.verdict, "detail": refusal.detail,
                   "from_memory": False, "records": [],
                   "seconds": round(time.perf_counter() - started, 4)}
        got["interpreter"] = {"version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
                             "check": floor_note, "ok": floor_ok}
        return got

    digest, evidence = evidence_digest(tree)
    result["evidence"] = evidence
    result["evidence_digest"] = digest

    memory = load_memory(memory_path)
    cached = memory["entries"].get(f"{goal}::{digest}")
    layout = detect_layout(tree)
    result["layout"] = layout
    result["requirements"] = {"requires_python": declared.get("requires_python"),
                              "declared_deps": declared.get("declared_deps", []),
                              "build_backend": declared.get("build_backend")}
    result["interpreter"] = {"version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
                             "check": floor_note, "ok": floor_ok}

    # the runner asks the isolation the environment was armed in first, then the host.
    # Only an isolation that already exists is asked: run-tests must never install.
    isolated = existing_isolation_python(tree)
    # Every declared command, asked with the isolation's interpreter first: the project's
    # own test command is a declaration, and re-pointing it at the isolated interpreter is
    # the whole point of arming. A command that names a tool the isolation does not have
    # (tox, nox, make) is asked as declared -- and fails honestly if it is not there.
    declared_argv = runner_candidates(tree, pyproject)
    candidates: list[list[str]] = []
    if isolated:
        # The armed isolation IS the environment being judged. Falling back to the host
        # interpreter when the isolation's suite fails would answer a different question --
        # the host python simply has no pytest, so every such fallback failed for a reason
        # that says nothing about the arming, and its tail (measured) was the only thing a
        # refusal reported.
        for argv in declared_argv:
            if argv[:1] == [sys.executable]:
                candidates.append([isolated] + argv[1:])
            else:
                candidates.append([isolated, "-m"] + argv)
    else:
        candidates.extend(declared_argv)

    # the cache is re-verified, never trusted: the runner is re-executed, the derivation is skipped
    if cached is not None:
        recheck = run_check(tree, cached["runner"]["command"])
        result["from_memory"] = True
        result["recheck"] = {k: recheck[k] for k in ("exit_code", "ok", "seconds")}
        if recheck["ok"]:
            result["verdict"] = "ENVIRONMENT_BROKERED_FROM_MEMORY"
            result["runner"] = recheck
            result["seconds"] = round(time.perf_counter() - started, 4)
            return result
        memory["entries"].pop(digest, None)  # stale: discard and re-derive

    result["from_memory"] = False
    outcome = None
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        outcome = run_check(tree, candidate)
        attempts.append({k: outcome.get(k) for k in ("command", "exit_code", "ok")})
        if outcome["ok"]:
            break
    result["runner_attempts"] = attempts
    result["runner"] = outcome or {"ok": False, "detail": "NO_CANDIDATE_RUNNER"}
    result["runner_candidates"] = candidates
    if not (outcome and outcome["ok"]):
        # Two different facts, and collapsing them would hide the more useful one:
        # "the suite ran and some tests failed" is a statement about the PROJECT, while
        # "no runner could run" is a statement about the ENVIRONMENT. Measured on attrs
        # (1408 passed, 1 failed -- an upstream py3.11 failure) and tox (4253 passed, 3
        # man-page errors), both of which used to report the same environment refusal.
        ran_any = bool((outcome or {}).get("reported_passed"))
        timed_out = (outcome or {}).get("detail") == "TIMEOUT"
        result["verdict"] = ("REFUSE__VERIFICATION_FAILED" if ran_any
                            else "REFUSE__NO_RUNNER_EXECUTED_CLEANLY")
        result["detail"] = (
            f"the suite exceeded the {TIMEOUT:.0f} s runner bound and was stopped: a bound of "
            f"ours, so it says nothing about the environment or the project"
            if timed_out else
            (f"the suite ran in the armed environment: "
             f"{(outcome or {}).get('reported_passed')} passed, and did not "
             f"exit cleanly -- this is a result about the project, not a "
             f"refusal about the environment") if ran_any else
            "no candidate check command ran to completion")
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result  # NOTE: nothing is cached -- a failure is not an environment

    memory["entries"][f"{goal}::{digest}"] = {
        "goal": goal, "verdict": "ENVIRONMENT_BROKERED",
        "layout": layout, "requirements": result["requirements"],
        "runner": {k: outcome[k] for k in ("command", "exit_code", "reported_passed",
                                           "reported_failed_or_errored", "seconds")},
        "evidence_digest": digest,
    }
    save_memory(memory, memory_path)
    result["verdict"] = "ENVIRONMENT_BROKERED"
    result["seconds"] = round(time.perf_counter() - started, 4)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=pathlib.Path)
    parser.add_argument("--goal", default="run-tests")
    parser.add_argument("--memory", type=pathlib.Path, default=DEFAULT_MEMORY)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--work-dir", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    got = broker(args.tree, args.goal, args.memory, work_dir=args.work_dir)
    text = json.dumps(got, indent=1, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    verdict = str(got.get("verdict", ""))
    ok = verdict.startswith(("ENVIRONMENT_BROKERED", "ENVIRONMENT_READY_"))
    return 0 if ok else 1


def self_check() -> dict[str, Any]:
    """Behavioral positive+negative proof contract for the_environment_broker_v1."""
    import tempfile as _tf
    checks: dict[str, bool] = {}
    checks["normalize_name_pep503"] = normalize_name("My_Pkg.Name") == "my-pkg-name"
    _req = parse_requirement("pytest>=7.0")
    checks["parse_requirement_name"] = isinstance(_req, dict) and _req.get("name") == "pytest"
    checks["specifier_satisfied_pos"] = specifier_satisfied("7.4.0", ">=7.0") is True
    checks["specifier_satisfied_neg"] = specifier_satisfied("6.2.0", ">=7.0") is False
    with _tf.TemporaryDirectory(prefix="w51_eb_") as _td:
        _p = pathlib.Path(_td)
        (_p / "src" / "pkg").mkdir(parents=True)
        (_p / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        _lay = detect_layout(_p)
        checks["detect_src_layout"] = isinstance(_lay, dict) and bool(_lay)
    _ok = all(checks.values())
    return {"pass": _ok, "verdict": "PASS" if _ok else "FAIL", "checks": len(checks), "passed": sum(checks.values()), "details": checks}

if __name__ == "__main__":
    raise SystemExit(main())
