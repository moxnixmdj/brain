"""Make a failed action succeed by reading why it failed.

Environments are infinite; the ways an action fails are not. A missing
binary, a missing module, an unmet dependency, a port already taken, a
directory that cannot be written -- these recur across every language and
every project, and each one says what it is in the output it produces.

So rather than testing our way through possible environments, this reads
the failure, classifies it, and applies the repair that class implies. The
repair is then re-run and judged by what actually happens -- never assumed
to have worked.

The loop is bounded and honest: a bounded number of attempts, and an
unclassifiable failure is reported as that, not guessed at.

Nothing here asks a model to interpret an error. The error is matched
against signatures and the repair is deterministic.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REPAIR_V1"

# Signatures of failure, most specific first. Each says what happened and
# what to do about it. A repair is either a different command that does the
# same job here (adapt), or a command to run before retrying (provision).
_SIGNATURES: list[tuple[str, re.Pattern]] = [
    ("missing_python_module", re.compile(r"ModuleNotFoundError:\s*No module named ['\"]([^'\"]+)")),
    ("missing_python_module", re.compile(r"ImportError:\s*No module named\s+([A-Za-z0-9_.-]+)")),
    ("missing_node_module",   re.compile(r"Cannot find module ['\"]([^'\"]+)")),
    ("missing_npm_script",    re.compile(r"npm (?:ERR! )?missing script:\s*([A-Za-z0-9_.:-]+)")),
    ("missing_binary",        re.compile(r"(?:^|\s)([A-Za-z0-9_./-]+):\s*command not found", re.M)),
    ("missing_binary",        re.compile(r"(?:^|\s)([A-Za-z0-9_./-]+):\s*not found", re.M)),
    ("missing_binary",        re.compile(r"sh:\s*\d*:\s*([A-Za-z0-9_./-]+):\s*not found")),
    ("no_such_file",          re.compile(r"No such file or directory:\s*['\"]?([^\s'\"]+)")),
    ("port_in_use",           re.compile(r"(?:EADDRINUSE|address already in use)")),
    ("permission_denied",     re.compile(r"Permission denied")),
    ("tests_not_found",       re.compile(r"(?:no tests ran|collected 0 items|No tests were found)")),
]


# When a project's declared runner is absent, what are its tests actually
# written against? Each row is evidence to look for in the project's own
# sources, and the command that runs that kind of test. This is a table of
# what test code looks like, not of projects -- which is why a runner that
# does not exist yet still lands on one of these rows.
#
# (evidence regex, command, the tool that must exist here)
_TEST_EVIDENCE = [
    (re.compile(r"^\s*import\s+unittest\b|^\s*from\s+unittest\b", re.M),
     "python3 -m unittest discover -s . -p 'test*.py' -v", "python3"),
    (re.compile(r"""from\s+['"]node:test['"]|require\(['"]node:test['"]\)""", re.M),
     "node --test", "node"),
    (re.compile(r"^\s*import\s+pytest\b|^\s*from\s+pytest\b", re.M),
     "python3 -m pytest -q", "python3"),
]

# Tools that are test runners. Only when the missing binary is one of these
# is it worth asking what the tests are written against.
_TEST_RUNNERS = frozenset({
    "pytest", "pytest-3", "py.test", "mocha", "jest", "vitest",
    "jasmine", "karma", "ava", "tap", "go",
})


_TEST_FILE = re.compile(
    r"(^|/)(tests?|specs?|__tests__)/"
    r"|(^|/)(test_.*|.*_test|.*\.test|.*\.spec)\.(py|js|mjs|cjs|ts)$",
    re.I,
)


def _is_test_file(path: Path) -> bool:
    """Is this file a test? Decided by its name and where it lives."""
    try:
        rel = path.as_posix()
    except Exception:
        return False
    return bool(_TEST_FILE.search(rel))


def _find_runner(root: str) -> tuple[str | None, str]:
    """A command that runs this project's tests with what exists here.

    The declared runner is gone. Rather than map that one tool to one
    substitute, look at the test sources: they name the framework they were
    written for, and that framework may well have a runner already present.
    """
    base = Path(root)
    if not base.is_dir():
        return None, ""
    files = 0
    for path in base.rglob("*"):
        if files > 600:
            break
        if not path.is_file() or path.stat().st_size > 400_000:
            continue
        if path.suffix.lower() not in {".py", ".js", ".mjs", ".cjs", ".ts"}:
            continue
        # ONLY TEST FILES COUNT. Scanning every file matched `import pytest`
        # inside pytest_run.py -- the one file in env_toolchain that cannot
        # run -- and so proposed `python3 -m pytest`, which failed at once,
        # while the real tests sat in tests/test_core.py using unittest.
        # Evidence about what the tests are written against has to come from
        # the tests; a runner merely mentioned in a helper proves nothing.
        if not _is_test_file(path):
            continue
        files += 1
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        for pattern, command, needs in _TEST_EVIDENCE:
            if pattern.search(text) and shutil.which(needs):
                return command, f"tests use {pattern.pattern[:24]!r}; {needs} is present"
    return None, ""


def _tests_use(root: str, module: str) -> bool:
    """Evidence in the project that its tests target a given module.

    Substituting a runner that collects nothing is worse than not running
    tests at all, because it reports success. So the substitute is chosen
    only when the project's own sources say it applies.
    """
    base = Path(root)
    if not base.is_dir():
        return False
    pattern = re.compile(r"^\s*import\s+%s\b|^\s*from\s+%s\b" % (module, module), re.M)
    for i, path in enumerate(base.rglob("*.py")):
        if i > 400:
            break
        try:
            if pattern.search(path.read_text(errors="ignore")[:200_000]):
                return True
        except Exception:
            continue
    return False


def diagnose(command: str, output: str, exit_code: int, root: str = "") -> dict:
    """What went wrong, and what would fix it here.

    Returns the class, the evidence matched, and either a repair or a
    reason no repair is available on this machine.
    """
    if exit_code == 0:
        return {"schema": SCHEMA, "class": "ok", "evidence": "",
                "repair": None, "setup": None, "reason": ""}
    text = output or ""
    for kind, pattern in _SIGNATURES:
        m = pattern.search(text)
        if not m:
            continue
        what = (m.group(1) if m.groups() else "").strip()
        out = {"schema": SCHEMA, "class": kind, "evidence": m.group(0).strip()[:200],
               "what": what, "repair": None, "setup": None, "reason": ""}

        if kind == "missing_python_module":
            if shutil.which("pip3") or shutil.which("pip"):
                out["setup"] = f"python3 -m pip install --quiet {what}"
                out["reason"] = f"python module {what} is not installed"
            else:
                out["reason"] = f"module {what} missing and no pip to install it"
            return out

        if kind == "missing_node_module":
            if (Path(root) / "package.json").is_file() and shutil.which("npm"):
                out["setup"] = "npm install --no-audit --no-fund"
                out["reason"] = f"node module {what} missing; project has a package.json"
            else:
                out["reason"] = f"node module {what} missing and nothing to install it from"
            return out

        if kind == "missing_npm_script":
            out["reason"] = f"npm has no script named {what}"
            try:
                import json
                data = json.loads((Path(root) / "package.json").read_text(errors="ignore"))
                names = list((data.get("scripts") or {}).keys())
                if names:
                    out["reason"] += f"; available: {', '.join(names[:8])}"
            except Exception:
                pass
            return out

        if kind == "missing_binary":
            tool = what
            # ADAPT: is there something on this machine that does the job?
            if tool in _TEST_RUNNERS:
                # Not a mapping from one absent tool to one substitute, but a
                # question put to the project: what are these tests written
                # against, and is that runner here?
                runner, why = _find_runner(root)
                if runner:
                    out["repair"] = runner
                    out["reason"] = f"{tool} absent; {why}"
                    return out
                out["reason"] = (f"{tool} absent and no runner matching the "
                                 "project's test sources is available here")
                return out
            if tool == "jq" and shutil.which("python3"):
                out["repair"] = "python3 -m json.tool"
                out["reason"] = "jq absent; python json.tool reads the same input"
                return out
            # PROVISION: is it installable here?
            if shutil.which("npm") and tool in ("eslint", "prettier", "jest", "mocha", "tsc"):
                out["setup"] = f"npm install --no-save {tool}"
                out["reason"] = f"{tool} absent but installable from npm"
                return out
            out["reason"] = (f"{tool} is not installed here and no equivalent "
                             "or installer is available")
            return out

        if kind == "port_in_use":
            out["reason"] = "the port is already taken"
            return out
        if kind == "permission_denied":
            out["reason"] = "not permitted to write or execute there"
            return out
        if kind == "tests_not_found":
            out["reason"] = "the runner found no tests to run"
            return out
        if kind == "no_such_file":
            out["reason"] = f"path {what} does not exist"
            return out

    return {"schema": SCHEMA, "class": "unclassified", "evidence": text.strip()[:200],
            "repair": None, "setup": None,
            "reason": "the failure matches nothing known; refusing to guess"}


def attempt(command: str, root: str, timeout: int = 300, max_attempts: int = 3,
            install_timeout: int = 600) -> dict:
    """Run a command; when it fails, repair and retry, judging each time.

    Returns the full trace: what was tried, what the failure was, what the
    repair was, and what finally happened. Success is whatever actually
    exited zero -- never an assumption that the repair helped.
    """
    trace: list[dict] = []
    current = command
    for n in range(1, max_attempts + 1):
        try:
            r = subprocess.run(current, shell=True, cwd=root, timeout=timeout,
                               capture_output=True, text=True)
            out, code = (r.stdout or "") + (r.stderr or ""), r.returncode
        except subprocess.TimeoutExpired:
            trace.append({"attempt": n, "command": current, "class": "timeout",
                          "reason": "timed out", "repair": None, "setup": None})
            break
        except Exception as exc:
            trace.append({"attempt": n, "command": current, "class": type(exc).__name__,
                          "reason": str(exc)[:200], "repair": None, "setup": None})
            break

        if code == 0:
            return {"schema": SCHEMA, "ok": True, "command": current,
                    "exit_code": 0, "output": out[-4000:], "attempts": trace}

        d = diagnose(current, out, code, root)
        trace.append({"attempt": n, "command": current, "class": d["class"],
                      "evidence": d.get("evidence", ""), "reason": d["reason"],
                      "repair": d.get("repair"), "setup": d.get("setup")})

        if d.get("setup"):
            try:
                subprocess.run(d["setup"], shell=True, cwd=root,
                               timeout=install_timeout, capture_output=True, text=True)
                continue          # retry the same command now the setup ran
            except Exception:
                pass
        if d.get("repair") and d["repair"] != current:
            current = d["repair"]
            continue
        break

    return {"schema": SCHEMA, "ok": False, "command": current, "attempts": trace,
            "reason": (trace[-1]["reason"] if trace else "unknown")}


def evaluate(commands: list[str], root: str, timeout: int = 300) -> dict:
    """Does repairing actually help here? Decided by the gates, not by us.

    The comparison is the point: each command is run twice, once plain and
    once with repair, and the pair is handed to credit_gates_v1. A repair
    that fires everywhere and changes nothing earns no credit -- which is
    exactly right, because mechanisms that do nothing are the most
    convincing-looking failures there are.

    This is the piece HarnessBank calls separating proposing from crediting.
    repair_v1 proposes; credit_gates_v1 decides.
    """
    import subprocess

    import credit_gates_v1 as G

    def plain(cmd: str) -> int:
        try:
            r = subprocess.run(cmd, shell=True, cwd=root, timeout=timeout,
                               capture_output=True, text=True)
            return 1 if r.returncode == 0 else 0
        except Exception:
            return 0

    before = {c: plain(c) for c in commands}
    after = {}
    detail = {}
    for c in commands:
        res = attempt(c, root, timeout=timeout)
        after[c] = 1 if res["ok"] else 0
        detail[c] = res

    verdict = G.credit(before, after)
    return {"schema": SCHEMA, "credited": verdict["credited"],
            "reason": verdict.get("reason"), "before": before, "after": after,
            "statistics": verdict.get("statistics", {}),
            "traces": {c: detail[c]["attempts"] for c in commands}}


def adopt_or_rollback(root: str, commands: list[str], timeout: int = 300) -> dict:
    """Adopt repairing only if it beats not repairing, else roll back.

    From SEAL (arXiv:2607.24300): self-authored scores drift upward while
    real performance falls -- in their runs every cell ended with a
    self-score of at least 0.70 while fifteen of thirty-five policies scored
    below random. The remedy is an acceptance boundary the agent cannot
    author: compare candidate against incumbent on a fixed audit, return one
    bit, and roll the whole state back on a clear regression.

    Here the candidate is "run it with repair", the incumbent is "run it
    plain", and the audit is the exit status of each command. A repair that
    cannot beat doing nothing is not adopted, however plausible it looked.

    The evidence is attested, not asserted: exit codes and output come from
    the machine. Nothing here is a claim the system wrote about itself.
    """
    import subprocess

    def plain(cmd: str) -> int:
        try:
            return 1 if subprocess.run(cmd, shell=True, cwd=root, timeout=timeout,
                                       capture_output=True).returncode == 0 else 0
        except Exception:
            return 0

    incumbent = {c: plain(c) for c in commands}
    candidate = {}
    for c in commands:
        try:
            candidate[c] = 1 if attempt(c, root, timeout=timeout)["ok"] else 0
        except Exception:
            candidate[c] = 0

    inc_total = sum(incumbent.values())
    cand_total = sum(candidate.values())

    # One bit. Roll back on a clear regression; adopt only on a clear gain.
    if cand_total > inc_total:
        decision, why = "ADOPT", f"{cand_total} vs {inc_total} commands succeed"
    elif cand_total < inc_total:
        decision, why = "ROLLBACK", f"worse than doing nothing: {cand_total} vs {inc_total}"
    else:
        decision, why = "ROLLBACK", f"no measurable gain: {cand_total} vs {inc_total}"

    return {"schema": SCHEMA, "decision": decision, "reason": why,
            "incumbent": incumbent, "candidate": candidate,
            "incumbent_total": inc_total, "candidate_total": cand_total,
            "adopted": decision == "ADOPT"}
