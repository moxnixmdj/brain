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


def installed_programs(limit: int | None = None) -> list[str]:
    """What is actually on this machine. Discovered, never assumed.

    limit is None by default: a cap of 400 on a machine with 603 returned
    the first 400 by name and silently lost zip, xz and everything else in
    the back half of the alphabet. A cap that quietly hides most of the
    computer is an assumption wearing the costume of a measurement.
    """
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
    all_found = sorted(found)
    return all_found if limit is None else all_found[:limit]


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
        # what each action actually did, filled in by program_actions when an
        # action succeeds -- see ComputerEnv.recipes
        self.recipes: dict[str, dict[str, Any]] = {}
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


# --------------------------------------------------------------------------- #
# asking a program how it wants to be called
# --------------------------------------------------------------------------- #
_HELP_CACHE: dict[str, str] = {}


def help_text(prog: str, timeout: float = 3.0) -> str:
    """What the program says about itself, in its own words.

    Not a table of flags we keep: the program is asked, and it answers. Most
    do. The answer is cached because a program's help does not change while
    the machine is thinking.
    """
    if prog in _HELP_CACHE:
        return _HELP_CACHE[prog]
    text = ""
    for flag in ("--help", "-h"):
        try:
            proc = subprocess.run([prog, flag], capture_output=True,
                                  timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        got = (proc.stdout or b"") + (proc.stderr or b"")
        if got.strip():
            text = got.decode("utf8", "replace")
            break
    _HELP_CACHE[prog] = text
    return text


def output_flags(prog: str, limit: int = 6) -> list[str]:
    """Flags the program's own help suggests for naming an output.

    Reused from the brain rather than rewritten: cli_capability_acquisition
    already reads help for exactly this. They are hypotheses, not facts --
    the help for cp offers --version, which is not how you name an output --
    so every one is tried and only the one that works is believed.
    """
    try:
        from canonical.runtime.cli_capability_acquisition_v1 import (
            _candidate_output_flags)
    except Exception:  # noqa: BLE001
        return []
    text = help_text(prog)
    if not text:
        return []
    try:
        return list(_candidate_output_flags(text))[:limit]
    except Exception:  # noqa: BLE001
        return []


_FLAG_LINE = re.compile(r"^\s*(-\w,\s+--[\w-]+|--[\w-]+|-\w)\s*(.*)$")
_STOP = {"the", "and", "for", "with", "from", "print", "each", "file", "files",
         "input", "output", "use", "when", "only", "not", "does", "instead",
         "that", "this", "than", "them", "then", "into", "also", "same"}


def flag_descriptions(prog: str, limit: int = 80) -> list[tuple[str, str]]:
    """Every flag the program documents, next to what it says the flag does.

    The program is the only authority here. Nothing about what -l or --lines
    means was written down by us; wc says '-l, --lines  print the newline
    counts' and that is where the knowledge comes from.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in help_text(prog).splitlines():
        m = _FLAG_LINE.match(line)
        if not m:
            continue
        desc = (m.group(2) or "").strip()
        if len(desc) < 4:
            continue
        for raw in re.split(r",\s*", m.group(1)):
            raw = raw.strip()
            if not raw or not raw.startswith("-"):
                continue
            if raw in seen:
                continue
            seen.add(raw)
            out.append((raw, desc))
    return out[:limit]


def _stem(word: str) -> set[str]:
    """Crude but honest: 'lines'/'line'/'newline' must count as the same
    idea, or the goal's plain words never meet the manual's words."""
    w = word.lower()
    out = {w}
    if w.endswith("s") and len(w) > 3:
        out.add(w[:-1])
    else:
        out.add(w + "s")
    if w.endswith("es") and len(w) > 4:
        out.add(w[:-2])
    if w.endswith("ing") and len(w) > 5:
        out.add(w[:-3])
    return out


def flags_for_goal(prog: str, goal: str, limit: int = 8) -> list[str]:
    """Flags whose documented meaning the goal actually mentions.

    'count the lines' picks wc's -l because wc's own help describes -l as
    'print the newline counts'. The machine is reading the manual and looking
    for the words it was given -- not reciting a table of what -l does.
    """
    text = str(goal or "")
    # the filenames in the goal are noise: 'count the lines in notes.txt'
    # must not make every mention of 'notes' look like a match
    noise: set[str] = set()
    for name in _FILENAME.findall(text):
        for tok in re.findall(r"[a-z0-9]+", name.lower()):
            noise |= _stem(tok)
    # the program's own name is not a clue about which flag to use:
    # 'sort in reverse' must not make every flag whose text says 'sort' win
    noise |= _stem(prog)
    words: set[str] = set()
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if len(tok) > 2 and tok not in _STOP and tok not in noise:
            words |= _stem(tok)
    if not words:
        return []

    def score(desc: str) -> int:
        d: set[str] = set()
        for tok in re.findall(r"[a-z0-9]+", desc.lower()):
            d |= _stem(tok)
        exact = len(words & d)
        # 'line' lives inside 'newline'. Counting both is what separates
        # --lines from --bytes: every wc flag says 'counts', so the exact
        # match alone leaves all of them tied.
        sub = 0
        for w in words:
            if len(w) < 4:
                continue
            for t in d:
                if len(t) >= 4 and (w in t or t in w):
                    sub += 1
                    break
        return 2 * exact + sub

    scored = [(score(desc), flag) for flag, desc in flag_descriptions(prog)]
    scored = [(n, f) for n, f in scored if n > 0]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [f for _, f in scored[:limit]]


def invocation_shapes(prog: str, src: str, target: str,
                      goal: str | None = None) -> list[list[str]]:
    """How to try calling this program, in the order worth trying.

    Six hand-written shapes were a strict program: it decided in advance how
    every program on the machine must be called. The shapes below are the
    ones that let the output be named, and then whatever the program's own
    help proposes -- so a program that wants -o, or --stdout, or -O, says so
    itself and is called the way it asked.
    """
    shapes: list[list[str]] = [
        [prog, target, src],
        [prog, src, target],
        [prog, "-c", src],
        [prog, src],
        [prog, src, "-k"],
    ]
    for flag in output_flags(prog):
        for shape in ([prog, flag, target, src], [prog, flag, src]):
            if shape not in shapes:
                shapes.append(shape)
    # flags the goal itself asked for, by meaning. 'count the lines' needs
    # wc -l, and no positional shape will ever produce that.
    if goal:
        for flag in flags_for_goal(prog, goal):
            for shape in ([prog, flag, src], [prog, flag, target, src]):
                if shape not in shapes:
                    shapes.append(shape)
    return shapes


def program_actions(env: ComputerEnv,
                    programs: Sequence[str] | None = None,
                    target: str = "out.bin",
                    goal: str | None = None) -> list[tuple[str, Callable[[ComputerEnv], bool]]]:
    """One action per program on this machine: run it and keep what it wrote.

    The learner is not told which program compresses. It is given all of them
    and finds out by trying.
    """
    actions: list[tuple[str, Callable[[ComputerEnv], bool]]] = []
    src = next(iter(env.seed), "input.txt")

    def make(prog: str) -> Callable[[ComputerEnv], bool]:
        def run(env: ComputerEnv) -> bool:
            # Success is the file the goal named actually appearing. Counting
            # ANY new file as success let 'gzip out.gz input.txt' pass by
            # creating input.txt.gz, and stopped the search before it ever
            # reached the form that would have made out.gz.
            def made(before: set) -> bool:
                return target not in before and (env.root / target).is_file()

            # Letting the program write the named file comes first:
            # 'zip out.zip input.txt' produces a real archive. Capturing
            # stdout comes after, because a program can exit 0 while
            # printing chatter -- 'zip -c input.txt' succeeds and prints
            # "adding: input.txt", which written to out.zip makes a file
            # called .zip that is not one.
            for argv in invocation_shapes(prog, src, target, goal):
                # Every form starts from the seed. Without this the first
                # form consumes the input -- 'gzip out.gz input.txt'
                # compresses input.txt into input.txt.gz and deletes it --
                # and every later form is then run against a file that is no
                # longer there, so the one that would have worked never gets
                # a chance to.
                env.reset()
                before = set(env.listing())
                try:
                    proc = subprocess.run(argv, cwd=str(env.root),
                                          capture_output=True, timeout=5)
                except Exception:  # noqa: BLE001 - a program must never break learning
                    continue
                if proc.returncode != 0:
                    continue
                # Only fall back to stdout if the program did not write the
                # file itself. 'zip out.zip input.txt' builds a real archive
                # AND prints "adding: input.txt" -- writing that chatter over
                # the archive replaced a good file with a bad one and called
                # it done.
                captured = bool(proc.stdout) and not made(before)
                if captured:
                    (env.root / target).write_bytes(proc.stdout)
                if made(before):
                    # Learning that stays in the sandbox is a party trick.
                    # The exact argv that worked is the difference between
                    # "gzip can do this" and a command that can be run on a
                    # real file, so it is recorded rather than thrown away.
                    env.recipes["run_" + prog] = {
                        "program": prog,
                        "argv": ["{input}" if a == src else a for a in argv],
                        "stdout_to": target if captured else None,
                        "target": target,
                    }
                    return True
            env.reset()
            return False
        return run

    for prog in (programs if programs is not None else env.programs):
        actions.append(("run_" + prog, make(prog)))
    return actions


# --------------------------------------------------------------------------- #
# discovering which program does it, by acting
# --------------------------------------------------------------------------- #
_MAX_RETRIES = 6

_FILENAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9_]{1,8}")


def output_name(gap: str) -> str | None:
    """The file the goal asks for, read out of the goal.

    "archive these files into out.tar.xz" names its own output. Inventing
    input.txt.xz instead throws away the only thing that said what to call
    it -- and throws away the name that has to be handed to programs which
    require the output as an argument, like zip out.zip input.txt.
    """
    text = str(gap or "")
    hits = _FILENAME.findall(text)
    if not hits:
        return None
    padded = " " + text + " "      # padded the same way it is searched
    low = padded.lower()
    for word in (" into ", " to ", " as ", " named ", " called ", " in "):
        i = low.rfind(word)
        if i >= 0:
            after = _FILENAME.findall(padded[i + len(word):])
            if after:
                return after[0]
    return hits[-1]


def programs_for(suffix: str, limit: int = 14) -> list[str]:
    """Which programs to try. Discovered from PATH, then narrowed by whether
    their name could plausibly produce this suffix -- 'gzip' for .gz is not
    a fact anyone wrote down, it is a guess, and the learner proves it by
    running the program.
    """
    letters = [c for c in str(suffix or "").lower().lstrip(".") if c.isalnum()]
    installed = installed_programs()  # all of them; narrowing happens next
    if not letters:
        return installed[:limit]

    def subsequence(prog: str) -> bool:
        it = iter(prog)
        return all(c in it for c in letters)

    hits = [p for p in installed if subsequence(p)]
    rest = [p for p in installed if p not in hits]
    return (hits + rest)[:limit]


def _verify_plan(plan: Sequence[str], suffix: str, target: str,
                 programs: Sequence[str]) -> tuple[bool, str]:
    """Run the plan again from scratch and check the file it made really is
    that format.

    Reaching a file called out.zip is not the same as making a zip: gzip -c
    will happily write gzip bytes under any name we like. Claiming the goal
    was reached because the NAME appeared is how a machine reports success
    on a goal it never achieved.
    """
    env = None
    try:
        from canonical.runtime import program_synthesis_v1 as ps
        env = ComputerEnv()
        env.register(program_actions(env, programs=list(programs),
                                     target=target))
        for step in plan:
            env.act(step)
        out = env.root / target
        if not out.is_file():
            return False, "PLAN_PRODUCED_NO_FILE"
        good, why = ps.verify_round_trip(out, suffix)
        if good and not _input_matters(
                (env.recipes.get(plan[-1]) or {}).get("argv") or [],
                next(iter(env.seed), "input.txt"), target, out.read_bytes()):
            return False, "INPUT_WAS_IGNORED"
        return good, why
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__ + ":" + str(exc)[:200]
    finally:
        if env is not None:
            env.close()


def _input_matters(argv: Sequence[str], src: str, target: str,
                   produced: bytes) -> bool:
    """Did this program actually use the input, or ignore it entirely?

    'arch input.txt' prints the machine architecture and exits 0 without
    ever opening the file, so any goal that merely needs SOME bytes written
    is 'solved' by it -- the machine reported saving results to out.csv by
    writing x86_64. The check is causal and needs no knowledge of the task:
    make the same call with the input taken away, and if nothing changes,
    the input was never involved.
    """
    # the recipe records the input as the token {input}, not as the filename
    control = [a for a in argv if a != "{input}" and a != src]
    if control == list(argv):
        return True                      # no input to remove; cannot judge
    env = None
    try:
        env = ComputerEnv()
        try:
            proc = subprocess.run(control, cwd=str(env.root),
                                  capture_output=True, timeout=5,
                                  stdin=subprocess.DEVNULL)
        except Exception:  # noqa: BLE001
            return True                  # could not compare; do not reject
        if proc.returncode != 0:
            return True                  # without the input it fails: it used it
        got = proc.stdout or b""
        alt = env.root / target
        if alt.is_file():
            got = alt.read_bytes() or got
        return got != produced
    finally:
        if env is not None:
            env.close()


def _single_step(programs: Sequence[str], suffix: str,
                 target: str) -> tuple[list[str], str, dict | None] | None:
    """Try each program on its own before paying for a search over sequences.

    One action is the shortest plan that can exist, so it is the first thing
    worth trying -- and trying each one directly is far more reliable than
    hoping a random walk stumbles onto the right one. Only if no single
    program does it is a sequence even considered.
    """
    from canonical.runtime import program_synthesis_v1 as ps
    for prog in programs:
        env = None
        try:
            env = ComputerEnv()
            env.register(program_actions(env, programs=[prog], target=target))
            src_name = next(iter(env.seed), "input.txt")
            env.act("run_" + prog)
            out = env.root / target
            if not out.is_file():
                continue
            good, why = ps.verify_round_trip(out, suffix)
            if good and not _input_matters(
                    env.recipes["run_" + prog]["argv"], src_name, target,
                    out.read_bytes()):
                good, why = False, "INPUT_WAS_IGNORED"
            if good:
                return ["run_" + prog], why, env.recipes.get("run_" + prog)

        except Exception:  # noqa: BLE001 - one broken program is not a failure
            continue
        finally:
            if env is not None:
                env.close()
    return None


def _recipe_of(plan: Sequence[str], suffix: str, target: str,
               programs: Sequence[str]) -> dict[str, Any] | None:
    """Replay the winning plan and keep the exact command that did it."""
    env = None
    try:
        env = ComputerEnv()
        env.register(program_actions(env, programs=list(programs),
                                     target=target))
        for step in plan:
            env.act(step)
        for step in reversed(plan):
            if env.recipes.get(step):
                return env.recipes[step]
        return None
    except Exception:  # noqa: BLE001
        return None
    finally:
        if env is not None:
            env.close()


def apply(recipe: Mapping[str, Any], src: str | pathlib.Path,
          out_dir: str | pathlib.Path | None = None,
          output_name: str | None = None,
          timeout: float = 30.0) -> dict[str, Any]:
    """Run a command the machine taught itself, on a real file.

    A plan that only works on the synthetic file it was learned on is not a
    capability, it is a fact about one directory. The recipe carries the argv
    that actually worked, so the same command can be pointed at a file the
    machine has never seen.

    Nothing is trusted: the output is opened with the library that owns the
    format before this reports success.
    """
    from canonical.runtime import program_synthesis_v1 as ps
    source = pathlib.Path(src)
    if not source.is_file():
        return {"pass": False, "status": "OPEN__NO_SUCH_INPUT_FILE",
                "detail": str(source)}
    argv_in = list(recipe.get("argv") or [])
    if not argv_in:
        return {"pass": False, "status": "OPEN__RECIPE_HAS_NO_COMMAND",
                "detail": "nothing to run"}

    target = recipe.get("target")
    name = (output_name or recipe.get("stdout_to")
            or (source.name + pathlib.Path(str(target or ".out")).suffix))
    out_dir = pathlib.Path(out_dir) if out_dir else source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / name

    # Run in the file's own directory and hand over its name, not an absolute
    # path: zip and tar store whatever they were given, so an absolute path
    # bakes /home/user/... into every archive forever.
    try:
        handed_over = str(source.relative_to(out_dir))
    except ValueError:
        handed_over = str(source)

    argv = []
    for token in argv_in:
        if token == "{input}":
            argv.append(handed_over)
        elif target and token == target:
            argv.append(name)          # the output follows the real input
        else:
            argv.append(str(token))

    try:
        proc = subprocess.run(argv, cwd=str(out_dir), capture_output=True,
                              timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"pass": False, "status": "OPEN__COMMAND_FAILED",
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}

    if recipe.get("stdout_to") and proc.stdout:
        out.write_bytes(proc.stdout)

    if not out.is_file():
        return {"pass": False, "status": "OPEN__COMMAND_PRODUCED_NO_FILE",
                "detail": " ".join(argv), "argv": argv}

    suffix = pathlib.Path(name).suffix
    good, why = ps.verify_round_trip(out, suffix)
    return {"pass": bool(good), "status": "PASS__APPLIED_TO_REAL_FILE"
            if good else "OPEN__OUTPUT_NOT_REALLY_THAT_FORMAT",
            "argv": argv, "output": str(out),
            "output_bytes": out.stat().st_size, "verification": why,
            "returncode": proc.returncode}


def perform(gap: str, cwd: str | pathlib.Path | None = None,
            timeout: float = 30.0) -> dict[str, Any]:
    """Learn it if it has to, then actually do it to the real file.

    discover() answers "which program could do this" -- knowledge. perform()
    answers "it is done" -- the file exists, on the machine, where the file
    being talked about actually lives. Learning that never leaves the sandbox
    is not the machine doing anything, it is the machine knowing something.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    if not acq._requested_suffix(gap):
        return {"pass": False, "status": "OPEN__NO_OUTPUT_FORMAT_IN_GAP",
                "detail": "nothing in the goal says what to produce"}

    wanted = output_name(gap)
    base = pathlib.Path(cwd) if cwd else pathlib.Path.cwd()

    # the input is a file the goal names that is actually there; a goal about
    # a file that does not exist is a gap, not a task
    src = None
    for token in _FILENAME.findall(str(gap or "")):
        if token == wanted:
            continue
        cand = (base / token)
        if cand.is_file():
            src = cand
            break
    if src is None:
        return {"pass": False, "status": "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL",
                "detail": "no file named in the goal exists in %s" % base}

    found = discover(gap)
    if not found.get("closed"):
        return {"pass": False, "status": found.get("status")
                or "OPEN__COULD_NOT_LEARN_IT", "detail": found.get("detail"),
                "plan": found.get("plan")}
    recipe = found.get("recipe")
    if not recipe:
        return {"pass": False, "status": "OPEN__NO_COMMAND_RECORDED",
                "detail": "it worked but the command was not kept"}

    done = apply(recipe, src, out_dir=src.parent, output_name=wanted,
                 timeout=timeout)
    done["goal"] = gap
    done["plan"] = found.get("plan")
    done["learned_by"] = found.get("status")
    done["from_memory"] = found.get("from_memory")
    return done


def discover(gap: str, budget: int = 120, seed: int = 11) -> dict[str, Any]:
    """Find out which program reaches this goal by acting, not by being told.

    Nothing here is given a table of what any program does. The programs are
    read from PATH, they are run in a scratch directory, and the shortest
    sequence that produced the goal is what is returned -- and remembered, so
    the same shape of problem does not have to be learned twice.

    Three ways through, cheapest first:
      1. remember -- this shape of problem was solved before, so just check
         the answer still works.
      2. one action -- the shortest plan that can exist, found by trying
         each program on its own.
      3. search -- only if neither worked, look for a sequence.
    In every case the file is opened with the library that owns the format
    before anything is called a success.
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

    named = output_name(gap) or ""
    target = named if named.endswith(suffix) else ("input.txt" + suffix)
    progs = programs_for(suffix)
    is_goal = lambda snap: target in str(snap)
    gkey = "goal"

    def fingerprint_of() -> dict[str, Any]:
        env = ComputerEnv()
        try:
            env.register(program_actions(env, programs=progs, target=target))
            return tl.fingerprint(env, env.action_names)
        finally:
            env.close()

    def recall() -> tuple[list[str], str, dict | None] | None:
        try:
            rows = tl.recall(fingerprint_of(), gkey, k=3)
        except Exception:  # noqa: BLE001 - no memory is not a failure
            return None
        for row in rows:
            plan = list(row.get("plan") or [])
            if not plan:
                continue
            good, why = _verify_plan(plan, suffix, target, progs)
            if good:
                return plan, why, _recipe_of(plan, suffix, target, progs)
        return None

    def keep(plan: list[str], status: str, why: str) -> None:
        """A good answer is worth remembering, or it has to be found again."""
        try:
            tl.remember(fingerprint_of(), gkey, plan, reached=True)
        except Exception:  # noqa: BLE001 - remembering is not the goal
            pass

    # 1. the instant path: was this shape of problem solved before?
    got = recall()
    if got is not None:
        return {"closed": True, "status": "PASS__RECALLED_AND_REVERIFIED",
                "plan": got[0], "suffix": suffix, "target": target,
                "recipe": got[2], "actions_tried": 0,
                "verification": got[1], "banned": [],
                "from_memory": True,
                "detail": "recalled: %s" % ", ".join(got[0])}

    # 2. one action is the shortest plan that can exist
    one = _single_step(progs, suffix, target)
    if one is not None:
        keep(one[0], "PASS__SINGLE_ACTION_FOUND_AND_VERIFIED", one[1])
        return {"closed": True, "status": "PASS__SINGLE_ACTION_FOUND_AND_VERIFIED",
                "plan": one[0], "suffix": suffix, "target": target,
                "recipe": one[2], "actions_tried": len(progs),
                "verification": one[1], "banned": [], "from_memory": False,
                "detail": "found it by acting: %s" % ", ".join(one[0])}

    # 3. only now pay for a search over sequences
    banned: set[str] = set()
    outcome: dict[str, Any] = {}
    why = ""
    tried = 0
    for _ in range(_MAX_RETRIES):
        env = None
        try:
            env = ComputerEnv()
            env.register(program_actions(env, programs=progs, target=target,
                                         goal=gap))
            usable = [a for a in env.action_names if a not in banned]
            if not usable:
                break
            # once a move has been shown to produce the wrong bytes, a
            # recalled plan is not allowed to put it back
            outcome = tl.drive(env, usable, is_goal=is_goal, budget=budget,
                               seed=seed, use_transfer=not banned)
        except Exception as exc:  # noqa: BLE001
            return {"closed": False, "status": "CHANNEL_ERROR",
                    "detail": type(exc).__name__ + ":" + str(exc)[:200]}
        finally:
            if env is not None:
                env.close()
        tried = len(usable)
        if outcome.get("reached") is not True:
            break
        plan = list(outcome.get("plan") or [])
        if not plan:
            break
        ok, why = _verify_plan(plan, suffix, target, progs)
        if ok:
            keep(plan, "PASS__SEARCH_FOUND_AND_VERIFIED", why)
            return {"closed": True, "status": outcome.get("status"),
                    "plan": plan, "suffix": suffix, "target": target,
                    "recipe": _recipe_of(plan, suffix, target, progs),
                    "actions_tried": tried, "verification": why,
                    "banned": sorted(banned), "from_memory": False,
                    "detail": "found it by acting: %s" % ", ".join(plan)}
        banned.add(plan[0])

    return {"closed": False, "status": outcome.get("status"),
            "plan": list(outcome.get("plan") or []), "suffix": suffix,
            "target": target, "actions_tried": tried, "verification": why,
            "banned": sorted(banned), "from_memory": False,
            "detail": why or (outcome.get("status") or "never reached it")}

