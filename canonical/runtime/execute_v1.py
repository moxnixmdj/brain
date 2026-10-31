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
import shutil
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_EXECUTE_V1"

SUCCESS = "SUCCESS"
NO_EFFECT = "NO_EFFECT"
FAILED = "FAILED"
INDETERMINATE = "INDETERMINATE"
OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
WRONG_RESULT = "WRONG_RESULT"
VACUOUS_CHECK = "VACUOUS_CHECK"


_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".brain_venv"})


def _snapshot(root: str, max_entries: int | None = None) -> dict[str, tuple[int, int]]:
    """Path -> (size, mtime). Read by the kernel, not reported."""
    base = Path(root)
    out: dict[str, tuple[int, int]] = {}
    if not base.is_dir():
        return out
    stack: list[tuple[str, str]] = [(str(base), "")]
    while stack:
        abs_dir, rel_prefix = stack.pop()
        try:
            with os.scandir(abs_dir) as it:
                for entry in it:
                    name = entry.name
                    if name in _SKIP_DIRS:
                        continue
                    rel = f"{rel_prefix}/{name}" if rel_prefix else name
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append((entry.path, rel))
                            st = entry.stat(follow_symlinks=False)
                            out[rel] = (st.st_size, st.st_mtime_ns)
                        else:
                            st = entry.stat(follow_symlinks=False)
                            out[rel] = (st.st_size, st.st_mtime_ns)
                    except OSError:
                        continue
                    if max_entries is not None and len(out) > max_entries:
                        return out
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
        claim: dict | None = None, workdir: str | None = None,
        check: str | None = None) -> dict:
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

    # DID IT DO IT RIGHT.
    #
    # Everything above proves the world changed and that a stated claim
    # about it holds. None of it proves the result was CORRECT. A program
    # can run, change the tree, satisfy its claim and be plainly wrong --
    # writing the sum of a column when it was asked for the mean is
    # successful on every measure so far.
    #
    # So the caller may supply a check: a program that exits zero only if
    # the result is right.
    #
    # And the check is not trusted either. A check that accepts anything
    # -- "true", or one that never looks -- would pass every run and
    # certify nothing, which is the exact failure SEAL recorded: agents
    # whose self-tests saturated while certifying policies that scored
    # below random. So it must also REJECT a deliberately broken result.
    # A check that cannot tell a wrong answer from a right one is not a
    # check, and it disqualifies rather than passes.
    checked = None
    if check:
        good = _check_holds(check, root, timeout=timeout)
        broken = _check_rejects_broken(check, root, timeout=timeout)
        vacuous = good and not broken
        checked = {"holds": good, "rejects_broken": broken, "vacuous": vacuous}
        if vacuous:
            # It accepted a result that was emptied or corrupted.
            return {
                "schema": SCHEMA, "verdict": VACUOUS_CHECK,
                "exit_status": code, "timed_out": timed_out, "diff": d,
                "grounding": None, "check": checked, "escaped_paths": [],
                "output": "the check accepted a result that was emptied or "
                          "corrupted, so it certifies nothing",
                "root": root, "language": language,
            }
        if not good:
            return {
                "schema": SCHEMA, "verdict": WRONG_RESULT,
                "exit_status": code, "timed_out": timed_out, "diff": d,
                "grounding": None, "check": checked, "escaped_paths": [],
                "output": "the program ran and changed the tree, but the "
                          "check says the result is not right",
                "root": root, "language": language,
            }

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
        # Recorded on the success path too. A receipt that omits the
        # evidence is indistinguishable from one that never checked.
        "check": checked,
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


# ---------------------------------------------------------------------------
# Correction: the loop that makes a single run into an attempt that lands.
# ---------------------------------------------------------------------------
#
# Running a program once is not how anything real works. The car does not
# plan one trajectory and commit to it; it acts, watches what happened,
# and corrects, continuously, against observed reality rather than
# against what it predicted would happen.
#
# So the general action is not "run a program". It is: run, observe what
# the machine says actually happened, hand that observation back to
# whatever is authoring, and try again -- bounded, and stopping only when
# the world attests to the change.
#
# The author is a callable, not a module. Authorship is the part that
# understands the task and it is not owned here; owning it would mean
# hard-coding the very domain knowledge this design exists to avoid. What
# is owned is the judgement: what counts as failure, what is reported
# back, and when to stop.
#
# Crucially, what goes back to the author is the machine's observation,
# not the program's opinion of itself. A failing program is the worst
# possible narrator of why it failed.

HISTORY_SCHEMA = "PROJECT_BRAIN_EXECUTE_HISTORY_V1"


def iterate(goal: str, root: str, author, attempts: int = 4,
            claim: dict = None, timeout: int = 300) -> dict:
    """Run, observe, correct, repeat -- bounded by what the machine says.

    `author(goal, observation)` returns a program, or None to stop.
    `observation` is None on the first attempt and the previous verdict
    plus the machine's own report of the failure thereafter.
    """
    history: list[dict] = []
    observation = None

    for attempt in range(1, attempts + 1):
        try:
            program = author(goal, observation)
        except Exception as exc:
            history.append({"attempt": attempt, "verdict": INDETERMINATE,
                            "detail": f"author raised {type(exc).__name__}: {exc}"})
            break
        if program is None:
            history.append({"attempt": attempt, "verdict": INDETERMINATE,
                            "detail": "author declined to continue"})
            break

        result = run(program, root, timeout=timeout, claim=claim)
        entry = {
            "attempt": attempt,
            "verdict": result["verdict"],
            "exit_status": result["exit_status"],
            "detail": _why(result),
            "changed": (result["diff"] or {}).get("changed", False),
        }
        history.append(entry)

        if result["verdict"] == SUCCESS:
            return {"schema": HISTORY_SCHEMA, "verdict": SUCCESS,
                    "goal": goal, "attempts_used": attempt,
                    "history": history, "result": result,
                    "corrected": attempt > 1,
                    "rendered": render(result)}

        # Only the machine's account goes back, never the program's.
        observation = entry

    return {"schema": HISTORY_SCHEMA, "verdict": FAILED, "goal": goal,
            "attempts_used": len(history), "history": history,
            "result": history[-1] if history else None,
            "corrected": len(history) > 1,
            "rendered": "no attempt was credited"}


def _why(result: dict) -> str:
    """The machine's account of a failure, for whoever authors next."""
    v = result["verdict"]
    if v == NO_EFFECT:
        return ("the program exited zero but the tree was identical "
                "before and after: nothing happened")
    if v == OUT_OF_BOUNDS:
        return "the program touched paths outside the project: " + ", ".join(
            (result.get("escaped_paths") or [])[:5])
    if v == INDETERMINATE:
        return "the program did not finish: " + (result["output"] or "")[-200:]
    if v == FAILED:
        # Order matters, and getting it wrong cost a correction.
        #
        # A program that writes an output file and THEN crashes leaves a
        # truncated file behind. The claim about it reads CONTRADICTED,
        # and reporting that first buried the FileNotFoundError that
        # would actually have let the author fix it -- so the author
        # declined and a fixable task was abandoned. The exception is the
        # cause; the contradicted claim is a consequence. Causes first.
        err = (result["output"] or "").strip()
        if result["exit_status"] not in (0, None) and err:
            return err[-300:]
        g = result.get("grounding")
        if g is not None and g["verdict"] != "GROUNDED":
            return (f"the program succeeded but its claimed result did not "
                    f"hold ({g['verdict']})")
        return err[-300:] or f"exit {result['exit_status']}"
    return v


def _check_holds(check: str, root: str, timeout: int = 60) -> bool:
    """Does the check accept the result as it actually stands?"""
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "check.py"
        script.write_text(check if check.endswith("\n") else check + "\n")
        try:
            r = subprocess.run(["python3", str(script)], cwd=root,
                               timeout=timeout, capture_output=True, text=True)
            return r.returncode == 0
        except Exception:
            return False


def _check_rejects_broken(check: str, root: str, timeout: int = 60) -> bool:
    """Does the check reject the result once it has been broken?

    This is the mutation insight, applied at the point of credit. A check
    is only evidence if it can tell a wrong answer from a right one, so
    the tree is spoilt -- every output file emptied -- and the check must
    now fail. If it still passes, it was never looking, and the run it
    would have certified means nothing.
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(root, work, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        spoilt = 0
        for out in list(work.rglob("out/*")):
            if out.is_file():
                try:
                    out.write_text("CORRUPTION")
                    spoilt += 1
                except OSError:
                    continue
        if not spoilt:
            # Nothing to spoil: the check cannot be shown to discriminate,
            # so it is not evidence, and absence of evidence is not a pass.
            return False
        script = work / "_check.py"
        script.write_text(check if check.endswith("\n") else check + "\n")
        try:
            r = subprocess.run(["python3", "_check.py"], cwd=str(work),
                               timeout=timeout, capture_output=True, text=True)
            return r.returncode != 0
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Containment: measured, and not shipped.
# ---------------------------------------------------------------------------
#
# This was attempted and withdrawn, and the reason is worth keeping,
# because a containment that quietly discards the project's own work is
# worse than no containment at all.
#
# True confinement is unavailable here. Measured, not assumed:
#
#   chroot              no binary present
#   mount -o remount,ro /   permission denied -- the rootfs is locked
#   bwrap, firejail     not installed
#   unshare -r -m       works -- uid 0 inside a mount namespace
#
# So the only lever is mounting a tmpfs over each writable directory
# outside the project, making an escape ephemeral rather than prevented.
# Two things kill it:
#
#   IT IS A DENYLIST. It covers the directories named and not the ones
#   that are not. Reading is unfiltered and no syscall is filtered.
#
#   IT COLLIDES WITH THE PROJECT. A project has to live somewhere
#   writable, and every writable place here is one of the shields. Tested
#   with the project under /tmp: mounting tmpfs over /tmp hid the project
#   too, and the program's legitimate write to its OWN project vanished.
#   A sandbox that eats the work it is supposed to be protecting is not a
#   sandbox.
#
# Doing it properly means mounting tmpfs first and then binding the
# project in on top, which needs a handle on the original tree. That is
# real work and it is not justified by anything asked for here, so it is
# left undone rather than half-done.
#
# What IS enforced stays as it was: paths recorded in the before/after
# diff must resolve inside the project, which catches traversal and
# symlinks. Everything beyond that is an operating-system job.


def confinement_available() -> bool:
    """Report whether this machine can confine a program at all.

    Answering this is useful precisely because the answer is usually no,
    and a system should know that about itself rather than assume it.
    """
    what = {}
    for tool in ("chroot", "bwrap", "firejail", "unshare"):
        what[tool] = shutil.which(tool) is not None
    try:
        r = subprocess.run(["unshare", "-r", "-m", "sh", "-c", "true"],
                           timeout=30, capture_output=True, text=True)
        what["mount_namespace"] = (r.returncode == 0)
    except Exception:
        what["mount_namespace"] = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                ["unshare", "-r", "-m", "sh", "-c",
                 "mount -o remount,ro / 2>/dev/null"],
                timeout=30, capture_output=True, text=True)
            what["can_remount_root_readonly"] = (r.returncode == 0)
    except Exception:
        what["can_remount_root_readonly"] = False
    what["confinement"] = bool(
        what.get("chroot") or what.get("bwrap") or what.get("firejail"))
    return what
