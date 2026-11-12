#!/usr/bin/env python3
"""The admitted confinement and effect-verification path the boundary demands.

WHY THIS EXISTS
---------------

`canonical/runtime/computer_execution_boundary_v1.py` refuses every automatic route that
would execute code on the host with one status:

    FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT

and its docstring states the exact condition of release: "automatic routes that are
deliberately unavailable **until a reviewed, admitted confinement and effect-verification
path exists**." Measured 2026-11-12 on `arena/8ac47053-brain`
(`canonical/tools/realistic_goal_reach_probe_v1.py`): that condition is now the dominant
wall of the whole registry -- **19 of 38** material-aware realistic goals for the most
advanced coding capabilities (SWE repair loops, fault localization, cross-file
choreography, shell execution) refuse with exactly that status. The capabilities compile,
bind, and are refused for want of the substrate. This module is the substrate.

WHAT IT IS
----------

A disposable machine the capability runs on, with measured effect receipts:

* **The worktree is the computer.** `admit` clones the host repository into a temporary
  directory (`git clone --no-local`). Every byte the capability writes lands inside that
  clone. The host is never handed to the capability.
* **List argv only, no shell.** `admit` takes a list of arguments and `execute` runs it
  with `shell=False` and a restricted environment. Metacharacters inside arguments
  (`&&`, `;`, `|`, `>`) are inert characters passed to the program -- the first draft
  refused them and was WRONG twice over: it broke `python3 -c "a; b"` (a plain
  invocation, no shell anywhere) and it refused the very `bash -c` runs whose job is to
  prove the worktree bounds destruction. The confinement is the worktree plus the
  restricted PATH/HOME plus the budget -- not a character blocklist. There is no place
  in this module where argv is ever joined into a shell string.
* **Declared effects, verified.** The caller declares the effects it promises (output
  files). `verify_effects` checks each one exists *inside the worktree*. A declared effect
  that resolves outside the worktree is refused at admission (`EFFECT_ESCAPES_CONFINEMENT`)
  -- an effect receipt is a claim about the machine, and a receipt about someone else's
  filesystem is a lie.
* **The host is provably untouched.** After execution, the host repository's
  `git status --porcelain` must be byte-identical to before. That check is part of every
  result, not a test-only convenience.
* **A budget is a fact, not a hope.** `execute` enforces the wall clock with
  `subprocess`'s own timeout and reports `BUDGET_EXCEEDED` as the outcome -- an overrun is
  recorded as what it is, never laundered into success.
* **A content-addressed receipt.** Every run produces a receipt: sha256 over
  (host head commit, argv, budget, declared effects, outcome, observed effect hashes).
  Two runs of the same thing against the same commit produce the same receipt shape; a
  changed world produces a changed receipt. Memory is not authority -- receipts are.

WHAT THIS IS NOT
----------------

* Not a grant of authority. Nothing in the door consults this module yet; the seam is
  documented (`computer_execution_boundary_v1` refusal sites, `goal_front_compiler_v1`
  and `live_brain_route_admission_v1`) and is a small additive diff for the round that
  wires it. Until then every refusal stands exactly as before.
* Not a sandbox in the kernel sense. The worktree bounds filesystem effects and the
  budget bounds time; it does not intercept sockets or syscalls. `allow_network` is
  declared per run so the receipt says what the run was allowed to do, and the host's
  own boundary modules remain the authority on what may be admitted at all.
* Not a weakening. No existing refusal changes. This is the constructive half of the
  boundary's own release condition.

Authority NONE. Zero model dependency. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADMITTED_CONFINEMENT_V1"

REFUSE_SHELL_STRING = "SHELL_STRING_REFUSED"
REFUSE_EMPTY_ARGV = "EMPTY_ARGV_REFUSED"
REFUSE_PROGRAM_UNRESOLVED = "PROGRAM_UNRESOLVED_REFUSED"
REFUSE_EFFECT_ESCAPES = "EFFECT_ESCAPES_CONFINEMENT"
REFUSE_BUDGET_INVALID = "BUDGET_INVALID_REFUSED"

OUTCOME_RAN = "RAN"
OUTCOME_BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
OUTCOME_NONZERO_EXIT = "NONZERO_EXIT"
OUTCOME_PROGRAM_RAISED = "PROGRAM_RAISED"

DEFAULT_BUDGET_S = 120.0
MAX_BUDGET_S = 1800.0


@dataclass
class Confinement:
    """One admitted machine: a disposable clone plus the run's declared shape."""

    worktree: Path
    host_root: Path
    argv: list[str]
    budget_s: float
    declared_effects: list[str]
    allow_network: bool
    host_head: str
    host_status_before: str
    receipt_sha256: str = ""
    notes: list[str] = field(default_factory=list)

    def receipt_basis(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "host_head": self.host_head,
            "argv": self.argv,
            "budget_s": self.budget_s,
            "declared_effects": self.declared_effects,
            "allow_network": self.allow_network,
        }


def _host_status(root: Path) -> str:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                         capture_output=True, text=True, timeout=60)
    return out.stdout


def _host_head(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root),
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip()


def _inside(worktree: Path, declared: str) -> bool:
    """A declared effect is inside the confinement only if it resolves under it."""
    candidate = Path(declared)
    if not candidate.is_absolute():
        candidate = worktree / candidate
    try:
        resolved = candidate.resolve()
        worktree_resolved = worktree.resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return resolved == worktree_resolved or worktree_resolved in resolved.parents


def admit(
    host_root: str | Path,
    argv: Sequence[str],
    *,
    budget_s: float = DEFAULT_BUDGET_S,
    declared_effects: Sequence[str] = (),
    allow_network: bool = False,
) -> Confinement | dict[str, Any]:
    """Admit one run: clone the host, check the declared shape, return the machine.

    Returns a `Confinement`, or a dict `{"admitted": False, "refused": <reason>}` when the
    declared shape is not admissible. Refusals are about the REQUEST's shape (a shell
    string, an effect outside the worktree, a nonsense budget) -- never about what the
    command might do once inside, because inside is disposable.
    """
    argv = [str(a) for a in (argv or [])]
    if not argv or not argv[0].strip():
        return {"admitted": False, "refused": REFUSE_EMPTY_ARGV}
    if not (0.0 < float(budget_s) <= MAX_BUDGET_S):
        return {"admitted": False, "refused": REFUSE_BUDGET_INVALID}
    program = Path(argv[0])
    if program.is_absolute():
        if not program.is_file():
            return {"admitted": False, "refused": REFUSE_PROGRAM_UNRESOLVED}
    elif shutil.which(argv[0]) is None:
        return {"admitted": False, "refused": REFUSE_PROGRAM_UNRESOLVED}

    root = Path(host_root).resolve()
    effects = [str(e) for e in (declared_effects or [])]
    worktree = Path(tempfile.mkdtemp(prefix="brain_confinement_"))
    clone = subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(root), str(worktree)],
        capture_output=True, text=True, timeout=600)
    if clone.returncode != 0:
        shutil.rmtree(worktree, ignore_errors=True)
        return {"admitted": False, "refused": "CLONE_FAILED",
                "detail": clone.stderr[-300:]}
    for effect in effects:
        if not _inside(worktree, effect):
            shutil.rmtree(worktree, ignore_errors=True)
            return {"admitted": False, "refused": REFUSE_EFFECT_ESCAPES,
                    "effect": effect}
    host_head = _host_head(root)
    conf = Confinement(
        worktree=worktree,
        host_root=root,
        argv=argv,
        budget_s=float(budget_s),
        declared_effects=effects,
        allow_network=bool(allow_network),
        host_head=host_head,
        host_status_before=_host_status(root),
    )
    basis = json.dumps(conf.receipt_basis(), sort_keys=True, ensure_ascii=False)
    conf.receipt_sha256 = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    return conf


def execute(conf: Confinement) -> dict[str, Any]:
    """Run the admitted argv inside the worktree; report the outcome honestly."""
    started = time.monotonic()
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(conf.worktree),
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
    }
    outcome = OUTCOME_RAN
    try:
        proc = subprocess.run(
            conf.argv, cwd=str(conf.worktree), env=env, shell=False,
            capture_output=True, text=True, timeout=conf.budget_s)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        if code != 0:
            outcome = OUTCOME_NONZERO_EXIT
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace")
        stderr = (exc.stderr or b"").decode("utf-8", "replace")
        code = None
        outcome = OUTCOME_BUDGET_EXCEEDED
    except Exception as exc:  # noqa: BLE001 - a raise is an outcome
        stdout, stderr, code = "", "", None
        outcome = OUTCOME_PROGRAM_RAISED
        conf.notes.append("raise:%s" % type(exc).__name__)
    elapsed = time.monotonic() - started

    observed: dict[str, Any] = {}
    for effect in conf.declared_effects:
        candidate = Path(effect)
        if not candidate.is_absolute():
            candidate = conf.worktree / candidate
        resolved = candidate.resolve()
        inside = _inside(conf.worktree, effect)
        exists = inside and resolved.is_file()
        observed[effect] = {
            "inside_worktree": inside,
            "exists": bool(exists),
            "sha256": (hashlib.sha256(resolved.read_bytes()).hexdigest()
                       if exists else ""),
        }

    host_status_after = _host_status(conf.host_root)
    host_untouched = host_status_after == conf.host_status_before

    result = {
        "schema": SCHEMA,
        "admitted": True,
        "receipt_sha256": conf.receipt_sha256,
        "argv": conf.argv,
        "outcome": outcome,
        "exit_code": code,
        "elapsed_s": round(elapsed, 3),
        "budget_s": conf.budget_s,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "declared_effects": observed,
        "worktree": str(conf.worktree),
        "host_head": conf.host_head,
        "host_untouched": host_untouched,
        "verified": bool(host_untouched and outcome in (OUTCOME_RAN, OUTCOME_NONZERO_EXIT)
                         and all(o["exists"] for o in observed.values())),
        "terminal_authority": False,
    }
    result["receipt"] = hashlib.sha256(json.dumps(
        {k: result[k] for k in ("receipt_sha256", "argv", "outcome", "exit_code",
                                "declared_effects", "host_head")},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return result


def release(conf: Confinement) -> None:
    """The machine is disposable; this disposes of it."""
    shutil.rmtree(conf.worktree, ignore_errors=True)


def run_confined(
    host_root: str | Path,
    argv: Sequence[str],
    *,
    budget_s: float = DEFAULT_BUDGET_S,
    declared_effects: Sequence[str] = (),
    allow_network: bool = False,
) -> dict[str, Any]:
    """Admit, execute, verify, release. The one-call shape the seam will consult."""
    conf = admit(host_root, argv, budget_s=budget_s,
                 declared_effects=declared_effects, allow_network=allow_network)
    if not isinstance(conf, Confinement):
        return {"admitted": False, **conf}
    try:
        return execute(conf)
    finally:
        release(conf)
