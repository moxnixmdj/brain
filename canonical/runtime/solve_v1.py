"""The whole system, reduced to what cannot be removed.

A computer is a state machine. Every task, without exception -- writing
code, finding a document, organising a folder, driving a browser -- is a
desired change of state. That single observation decides the design:

    PERCEPTION   what is true, read by the kernel, never self-reported
    ACTION       change the state, by running code
    JUDGEMENT    is it done, and what next

The first two can be built once and work everywhere. The third cannot be
built at all: any rule that decides whether an arbitrary task is finished
is a rule about that task, and it will fail on the next one. Judgement
belongs to a model. That is not a gap in this design; it is the reason
the design is small.

So the harness is two things -- observe and act -- wrapped in a loop,
and it holds no knowledge whatsoever about any domain. It does not know
what a test is, what a log is, what a manifest is. It reads the machine
and it runs code.

    while not done:
        see  <- observe(root)        kernel truth, not the model's report
        act  <- model(goal, see)     the general part; a program, or None
        run(act)
        see' <- observe(root)
        done <- model(goal, see')

That is the loop, and it is the same shape as the car: act, watch what
actually happened, correct against observed reality rather than against
what was predicted. Not plan-once-and-commit.

What this file deliberately does not contain, because each was a special
case wearing a general name: no knowledge of manifests or toolchains, no
failure-signature table, no task vocabulary, no ranking of commands. All
of that was built, worked on the cases it was written for, and let
everything else fall through -- five ordinary tasks, all unanswered.

Speed is a design constraint, not an afterthought: observation is one
stat() pass, and it reports only what changed. A loop that re-derives
the world each step is slow and brittle for the same reason, so the
world is diffed rather than rebuilt.

The model is a callable, not a dependency. It is passed in. A harness
that owns the model would be hard-coding the very knowledge this design
exists to keep out, and would stop the moment the model changed.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_SOLVE_V1"

DONE = "DONE"
GAVE_UP = "GAVE_UP"
BOUNDED = "BOUNDED"

# Directories that are never the subject of a task. Kept to structure,
# not to any domain: vendored, generated, or someone else's code.
_NOISE = {".git", "node_modules", "__pycache__", ".venv", "venv",
          "site-packages", "vendor", "dist", "build", ".mypy_cache"}


def observe(root: str, before: dict | None = None,
            preview_bytes: int = 600) -> dict:
    """What is true of this tree, read by the kernel.

    One stat() pass, plus a short preview of any small text file.

    The preview is the difference between a loop that is fast and one
    that is not. Without it the model knows a file EXISTS but not what
    is in it, and has to spend an action reading each one before it can
    decide anything -- so answering a question about six files costs
    seven steps instead of one. Perception that withholds the obvious
    pushes the cost into the loop and makes every task slower.

    Capped hard, on size and count, so one pass stays one pass however
    large the tree. A preview is a hint, never the evidence; when the
    answer turns on exact contents, read() gets the bytes.

    Nothing here is reported by the thing being judged.
    """
    base = Path(root)
    now: dict[str, tuple[int, int]] = {}
    previews: dict[str, str] = {}
    if base.is_dir():
        for path in base.rglob("*"):
            rel = path.relative_to(base).as_posix()
            if _NOISE & set(rel.split("/")):
                continue
            try:
                st = path.stat()
                now[rel] = (st.st_size, st.st_mtime_ns)
            except OSError:
                continue
            if (not path.is_file() or st.st_size > 200_000
                    or len(previews) >= 60):
                continue
            try:
                head = path.read_bytes()[:preview_bytes]
            except OSError:
                continue
            if b"\0" in head:          # binary: a preview would be noise
                continue
            previews[rel] = head.decode("utf-8", "replace")
    changed = (sorted(set(now) - set(before)) +
               sorted(k for k in set(now) & set(before or {})
                      if now[k] != before[k])) if before is not None else []
    return {"root": os.path.realpath(root), "files": now, "changed": changed,
            "count": len(now), "previews": previews}


def read(root: str, path: str, limit: int = 4000) -> dict:
    """Read a file so the model can look. Refuses to leave the tree."""
    base = os.path.realpath(root)
    target = os.path.realpath(os.path.join(base, path))
    if target != base and not target.startswith(base + os.sep):
        return {"ok": False, "error": "refused: outside the project"}
    try:
        text = Path(target).read_text(errors="replace")
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "path": path, "text": text[:limit],
            "truncated": len(text) > limit}


def act(root: str, program: str, timeout: int = 120,
        network: bool = False) -> dict:
    """Run code. The only action there is, because it is all of them.

    Confined by default.

    This is the system's primary action path, which is exactly why
    confinement belongs here rather than beside it: a guarantee that
    applies to every code path except the one that actually runs is not
    a guarantee. For a while that was the state of things -- confine_v1
    existed, was measured, and was used by nothing.

    Where confinement is unavailable the run proceeds unconfined and
    says so in `confined: False`. Silently falling back would let the
    same code report the same result with and without a sandbox, and
    the caller could not tell the difference.
    """
    try:
        import confine_v1 as C
        if C.available():
            r = C.run(program, root, timeout=timeout, network=network)
            return {"exit": r.get("exit_status"), "out": r.get("output") or "",
                    "err": "" if r.get("verdict") == "OK"
                           else (r.get("output") or ""),
                    "timed_out": r.get("verdict") == "INDETERMINATE",
                    "confined": True,
                    # Propagated, or the receipt cannot answer "which
                    # runs could talk to the outside".
                    "network": bool(r.get("network", network))}
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "step.py"
        script.write_text(
            program if program.endswith("\n") else program + "\n")
        try:
            r = subprocess.run(["python3", str(script)], cwd=root,
                               timeout=timeout, capture_output=True, text=True)
            return {"exit": r.returncode, "out": (r.stdout or "")[-2000:],
                    "err": (r.stderr or "")[-2000:], "timed_out": False,
                    "confined": False}
        except subprocess.TimeoutExpired:
            return {"exit": None, "out": "", "err": "timed out",
                    "timed_out": True, "confined": False}
        except Exception as exc:
            return {"exit": None, "out": "",
                    "err": f"{type(exc).__name__}: {exc}", "timed_out": False,
                    "confined": False}


def solve(goal: str, root: str, model, steps: int = 6,
          timeout: int = 120) -> dict:
    """Plain goal in, work out.

    `model(goal, seeing)` returns a program, or None when it judges the
    goal reached. `seeing` carries what the machine says is true: the
    tree, what just changed, and the result of the last action. It never
    carries the program's own account of itself -- a program is the worst
    possible narrator of what it did.
    """
    if not Path(root).is_dir():
        return {"schema": SCHEMA, "verdict": BOUNDED, "goal": goal,
                "steps": 0, "trace": [], "detail": f"{root!r} is not a directory"}

    trace: list[dict] = []
    state = observe(root)
    verdict = GAVE_UP
    # Pathologies hit on the way. Recorded at the END, once it is known
    # whether the run recovered -- a failure that was later fixed is
    # evidence, and a failure that was not is evidence too, but they are
    # not the same evidence and scoring them as you go would flatter the
    # loop for having struggled.
    hit: list[tuple] = []
    pending: list[str] = []   # failures not yet resolved this run
    # Consulted BEFORE the first action, not after the first failure.
    # See flywheel_v1.primers: asked too late, the store repairs the
    # next step of this run and never prevents the next run's mistake,
    # and the measured benefit is exactly zero.
    learned_for_next = None
    try:
        import flywheel_v1 as F
        primed = F.primers()
        if primed:
            learned_for_next = {"primers": primed}
    except Exception:
        pass

    for step in range(1, steps + 1):
        seeing = {
            "step": step,
            "tree": sorted(state["files"]),
            "count": state["count"],
            "changed": state["changed"],
            "preview": state.get("previews") or {},
            "last": trace[-1]["result"] if trace else None,
            # What a PREVIOUS run learned about this exact way of
            # failing, so the model does not have to rediscover it.
            "learned": learned_for_next,
        }
        try:
            program = model(goal, seeing)
        except Exception as exc:
            trace.append({"step": step, "error":
                          f"model raised {type(exc).__name__}: {exc}"})
            break
        if program is None:
            # The model may PROPOSE that it is finished. It may not
            # CERTIFY it.
            #
            # Found by measuring: a run whose only action FAILED was
            # still reported DONE, because the loop took "I'm done" at
            # the model's word and never asked the machine whether the
            # last thing worked. Every run came back DONE in one step
            # and the failure was invisible.
            #
            # That is precisely what the ownership law forbids -- the
            # model proposes, deterministic code credits. So the machine
            # gets the last word: stopping is only success if nothing
            # actually failed on the way.
            last = trace[-1]["result"] if trace else None
            failed = bool(last and (last["exit"] not in (0, None)
                                    or last["timed_out"]))
            if failed:
                verdict = GAVE_UP
                trace.append({"step": step,
                              "error": "declared done after a failed action"})
                break
            verdict = DONE
            break

        result = act(root, program, timeout=timeout)
        after = observe(root, before=state["files"])
        trace.append({"step": step, "result": result,
                      "changed": after["changed"]})
        state = after

        # Name the failure from the error alone, then ask what has been
        # learned about it. Both are keyed on how things break, never on
        # what the task was.
        learned_for_next = None
        failed_now = (result["exit"] not in (0, None)) or result["timed_out"]
        if failed_now:
            try:
                import flywheel_v1 as F
                where, why = F.classify(result["err"] or result["out"] or "")
                cell = F.cell_of(where, why)
                hit.append((where, why))
                pending.append(cell)
                trace[-1]["pathology"] = cell
            except Exception:
                pass
        elif pending:
            # THE FIX IS THE LESSON.
            #
            # Credit was being granted to cells whose procedure was
            # permanently None, because outcomes were recorded and the
            # thing that actually recovered was never captured. So the
            # store was credited and empty, primers() had nothing to
            # hand over, and the measured speed gain was exactly zero.
            #
            # The program that just succeeded IS the resolution for
            # every pathology still outstanding. Captured as a
            # candidate; it is only handed back once credit is earned.
            try:
                import flywheel_v1 as F
                for cell in dict.fromkeys(pending):
                    if not (F.status(cell)["procedure"]):
                        F.teach(cell, program)
                pending.clear()
            except Exception:
                pending.clear()
    else:
        verdict = GAVE_UP

    # The flywheel turns here: every pathology met on the way is scored
    # by whether the run recovered from it.
    if hit:
        try:
            import flywheel_v1 as F
            recovered = (verdict == DONE)
            for where, why in dict.fromkeys(hit):
                F.record(where, why, recovered)
        except Exception:
            pass

    return {"schema": SCHEMA, "verdict": verdict, "goal": goal,
            "steps": len(trace), "trace": trace,
            "final_tree": sorted(state["files"]),
            "changed": state["changed"]}


def render(result: dict) -> str:
    lines = [f"goal:   {result['goal']}",
             f"verdict:{result['verdict']:>8}  after {result['steps']} step(s)"]
    for t in result.get("trace") or []:
        if "error" in t:
            lines.append(f"  #{t['step']} error {t['error'][:60]}")
            continue
        r = t["result"]
        lines.append(f"  #{t['step']} exit={r['exit']} "
                     f"changed={len(t['changed'])}"
                     + (f" {t['changed'][:2]}" if t["changed"] else ""))
    return "\n".join(lines)
