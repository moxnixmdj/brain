#!/usr/bin/env python3
"""The computer itself, as an environment the learner can act in.

Composing needs a registered capability. Synthesising needs a format in a
table. Reading documentation needs a module whose name the goal happened to
use. All three are ways of knowing the shape of the answer before starting.

This one assumes nothing. It offers a real directory, a real set of actions,
and a real reset -- and lets the learner find out, by acting, which sequence
of actions reaches the goal. That is the difference between a machine that
recalls what it was told and one that finds out.

The actions are DISCOVERED, not declared: the programs on this machine are
read from PATH at runtime. Nothing here knows that gzip compresses, or that
tar archives. The learner finds out which program does what by running them
and watching the directory change.

Every action is real -- a real subprocess or a real file operation on a real
disk -- and reset puts the directory back, so probing is free and the only
thing that survives is what was learned.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_COMPUTER_ENV_V1"

# programs that only read, or that could do damage, are never given as actions
_NEVER = frozenset("""rm rmdir dd mkfs shutdown reboot halt poweroff init
kill killall pkill chmod chown chgrp sudo su chroot mount umount fdisk
parted shred wipe systemctl service telinit""".split())

_EXT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,24}$")


def installed_programs(limit: int = 60) -> list[str]:
    """What is actually on this machine. Discovered, never assumed."""
    found: set[str] = set()
    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        if not directory or not os.path.isdir(directory):
            continue
        try:
            names = os.listdir(directory)
        except OSError:
            continue
        for name in names:
            if name in _NEVER or not _EXT.match(name):
                continue
            path = os.path.join(directory, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                found.add(name)
    return sorted(found)[:limit]


def _digest(root: pathlib.Path) -> str:
    """The state of a directory: names, sizes and a hash of each file.

    Names alone would make two different files the same state, and the
    learner would then 'achieve' goals it never achieved.
    """
    parts: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            p = pathlib.Path(dirpath) / name
            try:
                data = p.read_bytes()
            except OSError:
                data = b""
            import hashlib
            parts.append("%s:%d:%s" % (p.relative_to(root), len(data),
                                       hashlib.sha256(data).hexdigest()[:12]))
    return "|".join(parts)


class ComputerEnv:
    """A real working directory. Actions really run. Reset really undoes."""

    def __init__(self, seed: Mapping[str, bytes] | None = None,
                 root: str | pathlib.Path | None = None,
                 programs: Sequence[str] | None = None) -> None:
        self._owned = root is None
        self.root = pathlib.Path(root) if root else pathlib.Path(
            tempfile.mkdtemp(prefix="brain-computer-env-"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.seed = dict(seed or {"input.txt": b"brain computer env sample\n"})
        self.programs = list(programs) if programs is not None else installed_programs()
        self.actions: dict[str, Callable[[ComputerEnv], bool]] = {}
        self.register(file_actions())
        self.reset()

    def register(self, actions: Sequence[tuple[str, Callable[[ComputerEnv], bool]]]) -> None:
        for name, fn in actions:
            self.actions[str(name)] = fn

    def act(self, action: str) -> bool:
        """The learner records actions as dict keys, so they are names."""
        fn = self.actions.get(str(action))
        if fn is None:
            return False
        try:
            return bool(fn(self))
        except Exception:  # noqa: BLE001 - a failing action is data, not a crash
            return False

    @property
    def action_names(self) -> list[str]:
        return sorted(self.actions)

    # -- environment protocol --------------------------------------------- #
    def state(self) -> str:
        return _digest(self.root)

    def reset(self) -> None:
        for child in self.root.iterdir():
            shutil.rmtree(child, ignore_errors=True) if child.is_dir() \
                else child.unlink()
        for name, data in self.seed.items():
            (self.root / name).write_bytes(data)

    def snapshot(self) -> bytes:
        """Everything, so probing can be undone. A snapshot that misses part
        of the world is how a learner corrupts the very thing it studies."""
        tmp = tempfile.mkdtemp(prefix="brain-env-snap-")
        shutil.copytree(self.root, os.path.join(tmp, "root"),
                        symlinks=False, dirs_exist_ok=True)
        self._snap = os.path.join(tmp, "root")
        return self._snap.encode()

    def restore(self, token: bytes) -> None:
        src = pathlib.Path(token.decode())
        for child in self.root.iterdir():
            shutil.rmtree(child, ignore_errors=True) if child.is_dir() \
                else child.unlink()
        for child in src.iterdir():
            target = self.root / child.name
            shutil.copytree(child, target) if child.is_dir() \
                else shutil.copy2(child, target)

    def close(self) -> None:
        if self._owned:
            shutil.rmtree(self.root, ignore_errors=True)
        snap = getattr(self, "_snap", None)
        if snap:
            shutil.rmtree(pathlib.Path(snap).parent, ignore_errors=True)

    # -- reading ----------------------------------------------------------- #
    def read(self, name: str) -> bytes:
        p = self.root / name
        return p.read_bytes() if p.is_file() else b""

    def exists(self, name: str) -> bool:
        return (self.root / name).is_file()

    def listing(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir())


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #
def file_actions() -> list[tuple[str, Callable[[ComputerEnv], bool]]]:
    """The things one can do to a directory, independent of any program."""
    def copy_input(env: ComputerEnv) -> bool:
        src = next((n for n in env.seed if (env.root / n).is_file()), None)
        if not src:
            return False
        shutil.copy2(env.root / src, env.root / "copy.txt")
        return True

    def move_copy_to_out(env: ComputerEnv) -> bool:
        if not (env.root / "copy.txt").is_file():
            return False
        shutil.copy2(env.root / "copy.txt", env.root / "out.bin")
        return True

    return [("copy_input", copy_input), ("copy_to_out", move_copy_to_out)]


def program_actions(env: ComputerEnv,
                    programs: Sequence[str] | None = None,
                    target: str = "out.bin") -> list[tuple[str, Callable[[ComputerEnv], bool]]]:
    """One action per program on this machine: run it and keep what it wrote.

    The learner is not told which program compresses. It is given all of them
    and finds out by trying.
    """
    actions: list[tuple[str, Callable[[ComputerEnv], bool]]] = []
    src = next(iter(env.seed), "input.txt")

    def make(prog: str) -> Callable[[ComputerEnv], bool]:
        def run(env: ComputerEnv) -> bool:
            # Try the forms a filter is usually invoked in. Programs that
            # cannot be driven this way simply produce nothing, and the
            # learner records that as a transition it can use.
            #
            # What counts as an effect is decided by what appeared, not by
            # what name we expected: a rule saying "look for src + '.gz'"
            # reports failure for bzip2, xz and every program not yet
            # thought of, and an environment that lies about its own
            # effects teaches the learner a false model.
            before = set(env.listing())
            for argv in ([prog, src], [prog, "-c", src], [prog, src, "-k"]):
                try:
                    proc = subprocess.run(argv, cwd=str(env.root),
                                          capture_output=True, timeout=10)
                except Exception:  # noqa: BLE001 - a program must never break learning
                    continue
                if proc.returncode != 0:
                    continue
                if proc.stdout:
                    (env.root / target).write_bytes(proc.stdout)
                    return True
                if set(env.listing()) - before:
                    return True
            return False
        return run

    for prog in (programs if programs is not None else env.programs):
        actions.append(("run_" + prog, make(prog)))
    return actions


# --------------------------------------------------------------------------- #
# discovering which program does it, by acting
# --------------------------------------------------------------------------- #
def programs_for(suffix: str, limit: int = 14) -> list[str]:
    """Which programs to try. Discovered from PATH, then narrowed by whether
    their name could plausibly produce this suffix -- 'gzip' for .gz is not
    a fact anyone wrote down, it is a guess, and the learner proves it by
    running the program.
    """
    letters = [c for c in str(suffix or "").lower().lstrip(".") if c.isalnum()]
    installed = installed_programs(limit=400)
    if not letters:
        return installed[:limit]

    def subsequence(prog: str) -> bool:
        it = iter(prog)
        return all(c in it for c in letters)

    hits = [p for p in installed if subsequence(p)]
    rest = [p for p in installed if p not in hits]
    return (hits + rest)[:limit]


def discover(gap: str, budget: int = 120, seed: int = 11) -> dict[str, Any]:
    """Find out which program reaches this goal by acting, not by being told.

    Nothing here is given a table of what any program does. The programs are
    read from PATH, they are run in a scratch directory, and the shortest
    sequence that produced the goal is what is returned -- and remembered, so
    the same shape of problem does not have to be learned twice.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    try:
        from canonical.runtime import transfer_learning_v1 as tl
    except Exception as exc:  # noqa: BLE001 - a channel never breaks a caller
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}

    suffix = acq._requested_suffix(gap)
    if not suffix:
        return {"closed": False, "status": "OPEN__NO_OUTPUT_FORMAT_IN_GAP",
                "detail": "nothing to verify an effect against"}

    env = None
    try:
        env = ComputerEnv()
        env.register(program_actions(env, programs=programs_for(suffix)))
        target = "input.txt" + suffix
        outcome = tl.drive(env, env.action_names,
                           is_goal=lambda snap: target in str(snap),
                           budget=budget, seed=seed)
        tried = len(env.action_names)
    except Exception as exc:  # noqa: BLE001
        return {"closed": False, "status": "CHANNEL_ERROR",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}
    finally:
        if env is not None:
            env.close()

    ok = outcome.get("reached") is True
    plan = list(outcome.get("plan") or [])
    return {"closed": ok, "status": outcome.get("status"), "plan": plan,
            "suffix": suffix, "actions_tried": tried,
            "from_memory": "RECALLED" in str(outcome.get("status") or ""),
            "detail": ("found it by acting: %s" % ", ".join(plan)) if ok
                      else (outcome.get("status") or "never reached it")}
