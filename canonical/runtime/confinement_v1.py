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
import re
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
REFUSE_ARGV_ESCAPES_CONFINEMENT = "ARGV_NAMES_AN_ABSOLUTE_PATH"
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
    # The one declared effect the program writes to STDOUT rather than to a file it opens itself
    # (`gzip -c input` versus `tar -cf`). Empty means the program writes its own output files.
    stdout_to: str = ""
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
    """A fingerprint of the host tree, measured before and after the run.

    `git status --porcelain` is the cheapest and most precise form when the directory IS a
    repository, and it is what the receipt has always carried. A directory that is not a repository
    has no fewer claims to make about being untouched, so it gets the same guarantee by a different
    measurement: a digest of every path, size and mtime under it. Both are taken twice, so
    "host_untouched" is a comparison rather than an assertion either way.
    """
    out = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                         capture_output=True, text=True, timeout=60)
    if out.returncode == 0:
        return out.stdout
    return _tree_digest(root)


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts:
            continue
        try:
            st = path.lstat()
        except OSError:
            continue
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0" + str(st.st_size).encode("ascii"))
        digest.update(b"\0" + str(st.st_mtime_ns).encode("ascii") + b"\n")
    return "TREE:" + digest.hexdigest()


def _host_head(root: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root),
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip() if out.returncode == 0 else ""


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


def _names_absolute_path(value: str) -> bool:
    """True when this argument can address a file outside the worktree.

    Two forms, both measured to escape a clone: a bare absolute path, and an absolute path embedded
    in a command string (`bash -c "echo x > /tmp/p"`). A relative path is fine -- it resolves inside
    the copy. `/dev/null` is allowed because it is a device, not a place a program can leave
    evidence the host did not ask for, and every well-formed command uses it.
    """
    if value == "/dev/null":
        return False
    if value.startswith("/"):
        return True
    for match in re.finditer(r"(?<![\w.-])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", value):
        if match.group(0) != "/dev/null":
            return True
    return False



def admit(
    host_root: str | Path,
    argv: Sequence[str],
    *,
    budget_s: float = DEFAULT_BUDGET_S,
    declared_effects: Sequence[str] = (),
    allow_network: bool = False,
    stdout_to: str = "",
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
    # AN ARGV THAT NAMES AN ABSOLUTE PATH IS NOT CONFINED BY A CLONE.
    #
    # The clone bounds relative work: a program that opens "out.gz" writes it inside the copy.
    # It does NOT bound a program that opens "/tmp/x/proof.txt" -- that path is absolute, so it
    # resolves to the same file from inside the copy as from outside it. Measured: `bash -c
    # "echo PWNED > /tmp/hole/proof.txt"` was admitted, ran, and CREATED THE HOST FILE, with
    # `host_untouched: False` reported only afterwards -- a receipt for damage already done.
    #
    # So an argument carrying an absolute path is refused at admission, unless it points into this
    # very worktree-relative tree (which it cannot, since the worktree does not exist yet). This is
    # the same rule `_host_escaping` already applies to declared effects, applied to the argv where
    # it actually belongs: a blocklist of dangerous words would be the wrong fix (ms-agent tried
    # six regex layers and was bypassed), and a list of arguments that can reach outside the copy
    # is a property, not a spelling.
    # THE PROGRAM IS NOT AN ARGUMENT. `argv[0]` was already checked above, and an absolute interpreter
    # path (`/tmp/venv/bin/python`) is how the machine is run, not a file it can write: the danger below
    # is an argument that addresses the HOST, and the program's own path is not one. Measured: refusing
    # it here made the only honest repair -- run the probe with the SAME interpreter the caller used --
    # impossible, so the census silently ran a different Python and reported 3 capabilities dead for a
    # reason the audit had invented. Arguments are scanned from argv[1:].
    for arg in argv[1:]:
        if _names_absolute_path(str(arg)):
            return {"admitted": False, "refused": REFUSE_ARGV_ESCAPES_CONFINEMENT,
                    "detail": str(arg)[:200]}
    effects = [str(e) for e in (declared_effects or ())]
    worktree = Path(tempfile.mkdtemp(prefix="brain_confinement_"))
    clone = subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(root), str(worktree)],
        capture_output=True, text=True, timeout=600)
    if clone.returncode != 0:
        # A DIRECTORY THAT IS NOT A GIT REPOSITORY IS STILL A COMPUTER.
        #
        # Requiring `git clone` to run `gzip` made the confinement usable only inside a repository
        # checkout, so a recalled skill replayed in the user's own working directory was refused
        # with CLONE_FAILED -- "fatal: repository '/tmp/...' does not exist" -- for a reason that
        # has nothing to do with the command. Copy the tree instead; the three guarantees the
        # clone provided are kept exactly: the host is never handed over (the capability runs in
        # the copy), declared effects must land inside the copy, and the host's fingerprint is
        # taken before and compared after, so "untouched" is still measured rather than assumed.
        shutil.rmtree(worktree, ignore_errors=True)
        worktree = Path(tempfile.mkdtemp(prefix="brain_confinement_"))
        try:
            shutil.copytree(root, worktree, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git"), symlinks=True)
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(worktree, ignore_errors=True)
            return {"admitted": False, "refused": "CLONE_FAILED",
                    "detail": (type(exc).__name__ + ":" + str(exc))[:300]}
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
        stdout_to=str(stdout_to or ""),
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
        # BYTES, NOT TEXT.
        #
        # `text=True` decoded the program's output as UTF-8, which silently destroys every binary
        # result -- a compressed file piped to stdout came back mangled, so a `stdout_to` recipe
        # could never produce a valid artifact through the confinement. Output is captured as
        # bytes and only decoded for the human-readable tail.
        proc = subprocess.run(
            conf.argv, cwd=str(conf.worktree), env=env, shell=False,
            capture_output=True, timeout=conf.budget_s)
        stdout_b = proc.stdout or b""
        stderr = (proc.stderr or b"").decode("utf-8", "replace")
        stdout = stdout_b.decode("utf-8", "replace")
        code = proc.returncode
        # A recipe whose product is stdout has to be given its file; otherwise the effect it
        # declared can never exist and the run is honest but useless.
        for effect in conf.declared_effects:
            if getattr(conf, "stdout_to", None) and effect == conf.stdout_to and stdout_b:
                target = Path(effect)
                if not target.is_absolute():
                    target = conf.worktree / target
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stdout_b)
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
        # THE WHOLE OUTPUT, NOT A TAIL. `stdout[-2000:]` is a DISPLAY budget, and it was being used as
        # the answer to "list the files here": a 524-entry listing is 23,946 bytes, so the delivered
        # answer was the last 65 lines -- alphabetically cut mid-word, beginning with a fragment of
        # `gate_accepts_a_failed_repair_probe_20261112.py`. Measured 2026-11-23, that
        # fragment was read as a filename that does not exist, and the "answer" omitted 481 real
        # entries while reporting `count: 65` as if it were the count. A tail is for a human reading a
        # log. The full text is what the run produced, and it is already in memory.
        "stdout": stdout,
        "stderr": stderr,
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
