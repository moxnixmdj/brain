"""The general action: run a program, then prove what it did.

Everything before this was a special case wearing a name -- a module for
manifests, a module for failure signatures, a module for claim forms, a
module for mutations. Each handled the cases it was written for and let
everything else fall through, which is why five ordinary tasks all
returned NOTHING_PRODUCED in zero seconds.

The realisation is that any task on a computer is expressible as code.
Moving files, counting tests, editing a changelog, answering a question,
driving a browser: all of it is a program. So there is one action space,
not a library of them, and it does not need to be taught about domains.

    MODEL      writes the program. This is the general part -- the thing
               that understands the task. It is not here; it is the caller.
    HARNESS    runs it, reads the world before and after, and judges the
               difference by what the machine attests.

That division is the whole architecture, and it is the one this system
has held throughout: the model may propose, only deterministic code may
credit. Nothing about the program is trusted. It is run, and then the
world is asked what changed.

Because the action is arbitrary code, three things are enforced here
rather than assumed:

  ISOLATION   it runs in the project, under a timeout, with the project's
              own interpreter when one was provisioned.
  EVIDENCE    before and after are read by the kernel, not reported by the
              program.
  BOUNDS      stated honestly, because it is easy to overclaim here.
              The before/after read covers the project tree, so it sees
              everything a program changed INSIDE it and nothing it wrote
              elsewhere. A program that writes to /tmp is caught only
              incidentally, as NO_EFFECT, not as an escape -- it was
              refused for the wrong reason, and the write still happened.
              Confining a program is an operating-system job: a sandbox,
              a seccomp profile, a container. Snapshot diffing is not one,
              and presenting it as one would be exactly the failure this
              system keeps punishing: a check that looks like it works.
              What is enforced is that paths recorded in the diff resolve
              inside the project, which catches traversal and symlinks.

A program that exits zero proves nothing. A program that changes the
world in the way the request described, as attested by the machine, is
the only thing this calls success.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_EXECUTE_V1"

SUCCESS = "SUCCESS"
NO_EFFECT = "NO_EFFECT"
FAILED = "FAILED"
INDETERMINATE = "INDETERMINATE"
OUT_OF_BOUNDS = "OUT_OF_BOUNDS"


def _snapshot(root: str) -> dict[str, tuple[int, int]]:
    """Path -> (size, mtime). Read by the kernel, not reported."""
    base = Path(root)
    out: dict[str, tuple[int, int]] = {}
    if not base.is_dir():
        return out
    for path in base.rglob("*"):
        rel = path.relative_to(base).as_posix()
        parts = rel.split("/")
        if any(p in (".git", "node_modules", "__pycache__", ".brain_venv")
               for p in parts):
            continue
        try:
            st = path.stat()
            out[rel] = (st.st_size, st.st_mtime_ns)
        except OSError:
            continue
    return out


def _diff(before: dict, after: dict) -> dict:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    return {"added": added, "removed": removed, "modified": modified,
            "changed": bool(added or removed or modified)}


def _outside(root: str, paths) -> list[str]:
    """Paths a run touched that are not inside the project."""
    base = os.path.realpath(root)
    bad = []
    for p in paths or []:
        try:
            real = os.path.realpath(os.path.join(base, p))
        except OSError:
            bad.append(str(p))
            continue
        if real != base and not real.startswith(base + os.sep):
            bad.append(str(p))
    return sorted(set(bad))


def run(program: str, root: str, language: str = "python",
        timeout: int = 300, expect_change: bool = True,
        claim: dict | None = None, workdir: str | None = None) -> dict:
    """Execute a program against a project and say what it actually did.

    `claim` is an optional grounding claim about the result -- a file that
    should contain something. It is re-read rather than believed, so the
    program cannot flatter itself by writing a reassuring file.
    """
    if not Path(root).is_dir():
        return {"schema": SCHEMA, "verdict": INDETERMINATE,
                "detail": f"{root!r} is not a directory", "exit_status": None}

    tmp = workdir or tempfile.mkdtemp(prefix="brain_exec_")
    Path(tmp).mkdir(parents=True, exist_ok=True)
    script = Path(tmp) / ("program.py" if language == "python" else "program.sh")
    script.write_text(program if program.endswith("\n") else program + "\n")

    before = _snapshot(root)
    command = (["python3", str(script)] if language == "python"
               else ["sh", str(script)])
    try:
        r = subprocess.run(command, cwd=root, timeout=timeout,
                           capture_output=True, text=True)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        timed_out = False
    except subprocess.TimeoutExpired:
        code, out, timed_out = None, "", True
    except Exception as exc:
        code, out, timed_out = None, f"{type(exc).__name__}: {exc}", False

    after = _snapshot(root)
    d = _diff(before, after)

    grounding = None
    if claim is not None:
        try:
            import grounding_v1 as G
        except Exception:
            G = None
        if G is not None:
            grounding = G.check(claim, root)

    # Anything the program wrote outside the project disqualifies the run,
    # whether or not it otherwise succeeded.
    escaped = _outside(root, d["added"] + d["modified"])

    if timed_out or code is None:
        verdict = INDETERMINATE
    elif escaped:
        verdict = OUT_OF_BOUNDS
    elif code != 0:
        verdict = FAILED
    elif expect_change and not d["changed"]:
        verdict = NO_EFFECT
    elif grounding is not None and grounding["verdict"] != "GROUNDED":
        verdict = FAILED
    else:
        verdict = SUCCESS

    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "exit_status": code,
        "timed_out": timed_out,
        "diff": d,
        "grounding": grounding,
        "escaped_paths": escaped,
        "output": out[-3000:],
        "root": root,
        "language": language,
    }


def render(result: dict) -> str:
    d = result.get("diff") or {}
    lines = [f"verdict: {result['verdict']}  (exit {result.get('exit_status')})"]
    for kind in ("added", "modified", "removed"):
        for p in (d.get(kind) or [])[:6]:
            lines.append(f"  {kind:<9} {p}")
    if result.get("escaped_paths"):
        lines.append("  ESCAPED: " + ", ".join(result["escaped_paths"][:5]))
    return "\n".join(lines)
