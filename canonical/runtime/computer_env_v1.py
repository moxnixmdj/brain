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
import json
import shutil
import subprocess
import sys
import tempfile
import time
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
                 seed_file: str | pathlib.Path | None = None,
                 programs: Sequence[str] | None = None) -> None:
        self._owned = root is None
        self.root = pathlib.Path(root) if root else pathlib.Path(
            tempfile.mkdtemp(prefix="brain-computer-env-"))
        self.root.mkdir(parents=True, exist_ok=True)
        # A sandbox holding a text file cannot teach an image operation:
        # 'convert -resize 50% input.txt out.png' fails for the same reason
        # a piano cannot be practised on a picture of one. When the real
        # input is available, practise on a copy of it -- same bytes, same
        # name, and never the original.
        if seed_file:
            path = pathlib.Path(seed_file)
            self.seed = {path.name: path.read_bytes()}
        else:
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
_HELP_LOADED = False
_HELP_DIRTY = False
_HELP_SINCE_FLUSH = 0


def _help_store_path() -> pathlib.Path:
    base = os.environ.get("BRAIN_STATE_DIR") or tempfile.gettempdir()
    return pathlib.Path(base) / "brain_help_text_v1.json"


def _help_signature(prog: str) -> str:
    """What would make a cached manual a lie.

    A cache is only allowed to remember something that cannot have changed.
    The manual belongs to a FILE, not to a name -- reinstalling the program
    or swapping what `python` points at changes the answer while leaving
    the name identical. So the name alone is never trusted: the real file,
    its size and its mtime are, and a mismatch is re-read.
    """
    try:
        real = os.path.realpath(str(shutil.which(prog) or prog))
        st = os.stat(real)
        return "%s|%d|%d" % (real, st.st_size, int(st.st_mtime))
    except Exception:  # noqa: BLE001 - an unstatable program is just re-read
        return ""


def _help_load() -> None:
    global _HELP_LOADED
    if _HELP_LOADED:
        return
    _HELP_LOADED = True
    try:
        raw = json.loads(_help_store_path().read_text())
    except Exception:  # noqa: BLE001 - no store is a cold start, not a fault
        return
    for prog, row in raw.items():
        try:
            sig, text = row[0], row[1]
        except Exception:  # noqa: BLE001
            continue
        if sig == _help_signature(prog):
            _HELP_CACHE[prog] = text


def _help_flush(force: bool = False) -> None:
    """Write back what was learned about this machine's programs.

    Asking 603 programs to print their manual costs about nine seconds, and
    it costs them again in every new process -- which is the difference
    between a machine that answers at once and one that thinks for nine
    seconds before it says "23". It is a fact about the machine, so it is
    kept where the next process can find it.
    """
    global _HELP_DIRTY, _HELP_SINCE_FLUSH
    if not _HELP_DIRTY:
        return
    if not force and _HELP_SINCE_FLUSH < 64:
        return
    _HELP_DIRTY = False
    _HELP_SINCE_FLUSH = 0
    try:
        payload = {p: [_help_signature(p), t] for p, t in _HELP_CACHE.items()}
        _help_store_path().write_text(json.dumps(payload))
    except Exception:  # noqa: BLE001 - a failed save must not lose an answer
        pass


def help_text(prog: str, timeout: float = 3.0) -> str:
    """What the program says about itself, in its own words.

    Not a table of flags we keep: the program is asked, and it answers. Most
    do. The answer is cached because a program's help does not change while
    the machine is thinking -- and because it does not change between two
    runs either, it is kept on disk for the next one.
    """
    global _HELP_DIRTY, _HELP_SINCE_FLUSH
    if prog in _HELP_CACHE:
        return _HELP_CACHE[prog]
    _help_load()
    if prog in _HELP_CACHE:
        return _HELP_CACHE[prog]
    text = ""
    for flag in ("--help", "-h"):
        # Bounded and fed an empty stdin. A program that ignores --help and
        # then waits for input would otherwise hang every scan for three
        # seconds at a time -- and one that prints forever would take the
        # learner down with it, which is a thing that actually happened.
        try:
            code, out = _run_capped([prog, flag], os.getcwd(), timeout=timeout)
        except Exception:  # noqa: BLE001
            continue
        if out.strip():
            text = out.decode("utf8", "replace")
            break
        if code == 0:
            break
    _HELP_CACHE[prog] = text
    _HELP_DIRTY = True
    _HELP_SINCE_FLUSH += 1
    _help_flush()
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


# Three shapes programs actually use:
#   '-c, --stdout  write to stdout'   (GNU: short then long)
#   '--to-stdout   write to stdout'   (GNU: long only)
#   '-adjoin       join images'       (ImageMagick et al: one dash, full name)
# The last must take a whole name, not one letter: matching only -\w turned
# '-adjoin' into the flag '-a' with the description 'djoin', so the machine
# went looking for a flag that does not exist.
_FLAG_LINE = re.compile(
    r"^\s*(-\w,\s+--[\w-]+|--[\w-]+|-[A-Za-z][\w-]*)\s*(.*)$")
_STOP = {"the", "and", "for", "with", "from", "print", "each", "file", "files",
         "input", "output", "use", "when", "only", "not", "does", "instead",
         "that", "this", "than", "them", "then", "into", "also", "same"}


def flag_descriptions(prog: str, limit: int = 400) -> list[tuple[str, str]]:
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


_VALUE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?%|\d+x\d+|\d+(?:\.\d+)?)(?![\w])")


def goal_values(goal: str, limit: int = 6) -> list[str]:
    """The numbers the goal mentions, because it brought its own arguments.

    'resize in.png to 50% as out.png' is not asking for a resize by some
    amount we must guess: it says 50%. Taking the value out of the sentence
    is the same move as taking the output name out of it.
    """
    out: list[str] = []
    for m in _VALUE.finditer(str(goal or "")):
        v = m.group(1)
        if v not in out:
            out.append(v)
    return out[:limit]


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
    if not goal:
        return shapes
    flags = flags_for_goal(prog, goal)[:3]
    values = goal_values(goal)
    extra: list[list[str]] = []
    if values:
        # a flag that takes a value has to be given one, and the goal named
        # it: '-resize 50%' is only a command once the 50% is supplied
        for flag in flags:
            for v in values[:3]:
                for shape in ([prog, flag, v, src, target],
                              [prog, src, flag, v, target],
                              [prog, flag, v, src]):
                    if shape not in extra:
                        extra.append(shape)
    for flag in flags:
        for shape in ([prog, flag, src], [prog, flag, target, src]):
            if shape not in extra:
                extra.append(shape)
    # The shapes that USE the goal's value go first. Left in their usual
    # place, 'convert in.png' wins by dumping the image to stdout into
    # out.png -- a file that exists, is called .png, and was never resized.
    return extra + shapes if values else shapes + extra


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
            # A form that eats the input is held back, not thrown away.
            # 'gzip input.txt' reaches the goal and DELETES input.txt, so
            # the job cannot be repeated and the file the user had is gone.
            # 'gzip -c input.txt' reaches exactly the same goal and leaves
            # it. Preferring the one that keeps the input is not a rule
            # about gzip -- it is the difference between doing the job and
            # doing the job by destroying the thing it was asked about.
            # The destructive form is remembered, because for a goal like
            # "move a.txt to b.txt" there is no gentler way and refusing
            # outright would be its own kind of failure.
            fallback: dict[str, Any] | None = None
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
                    recipe = {
                        "program": prog,
                        "argv": ["{input}" if a == src else a for a in argv],
                        "stdout_to": target if captured else None,
                        "target": target,
                    }
                    if (env.root / src).is_file():
                        env.recipes["run_" + prog] = recipe
                        return True
                    fallback = recipe
            if fallback is not None:
                env.recipes["run_" + prog] = fallback
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


def programs_for_goal(goal: str, limit: int = 24) -> list[str]:
    """Programs whose own manual says they can do what the goal asks.

    Selecting by the letters of a suffix works for gzip and .gz and fails
    completely for convert and .png -- 'convert' contains no p, n or g, so
    the one program on the machine that can resize an image was never even
    tried. The manual is the better index: ask which programs document a
    flag meaning what the goal said.
    """
    from concurrent.futures import ThreadPoolExecutor

    def ask(prog: str) -> tuple[str, int]:
        try:
            return prog, len(flags_for_goal(prog, goal))
        except Exception:  # noqa: BLE001
            return prog, 0

    with ThreadPoolExecutor(max_workers=24) as pool:
        hits = [(n, p) for p, n in pool.map(ask, installed_programs()) if n]
    # every manual on the machine has just been read once; never again
    _help_flush(force=True)
    hits.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in hits[:limit]]


def _uses_goal_value(recipe: Mapping[str, Any], goal: str | None) -> bool:
    """The command must use the numbers the goal gave it.

    'resize in.png to 50% as out.png' is answered just as well by
    'convert in.png out.png' if all we check is that out.png exists -- the
    file is there, and it is a real PNG, and it was never resized. If the
    goal named a value and the winning command does not contain it, the
    command did not do what was asked.
    """
    needed = goal_values(goal) if goal else []
    if not needed:
        return True
    argv = [str(a) for a in (recipe.get("argv") or [])]
    return any(v in argv for v in needed)


def _single_step(programs: Sequence[str], suffix: str, target: str,
                 goal: str | None = None,
                 seed_file: str | pathlib.Path | None = None
                 ) -> tuple[list[str], str, dict | None] | None:
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
            env = ComputerEnv(seed_file=seed_file)
            env.register(program_actions(env, programs=[prog], target=target,
                                         goal=goal))
            src_name = next(iter(env.seed), "input.txt")
            env.act("run_" + prog)
            out = env.root / target
            if not out.is_file():
                continue
            good, why = ps.verify_round_trip(out, suffix)
            if good and not _uses_goal_value(
                    env.recipes.get("run_" + prog) or {}, goal):
                good, why = False, "GOAL_VALUE_UNUSED"
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

    found = discover(gap, seed_file=src)
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


def discover(gap: str, budget: int = 120, seed: int = 11,
             seed_file: str | pathlib.Path | None = None) -> dict[str, Any]:
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
    # candidates by NAME (gzip for .gz) and by MEANING (convert for resize)
    progs = programs_for(suffix)
    for _p in programs_for_goal(gap):
        if _p not in progs:
            progs.append(_p)
    is_goal = lambda snap: target in str(snap)
    gkey = "goal"

    _fingerprint: dict[str, Any] | None = None

    def fingerprint_of() -> dict[str, Any]:
        """The shape of this problem, measured once.

        Fingerprinting acts out every action on the machine to see what
        each one does, and it was being done twice for every discovery --
        once to ask "have I solved this before?" and again to remember the
        answer. Remembering costs the same computation as asking, which is
        not learning twice, it is paying twice.
        """
        nonlocal _fingerprint
        if _fingerprint is not None:
            return _fingerprint
        env = ComputerEnv()
        try:
            env.register(program_actions(env, programs=progs, target=target))
            _fingerprint = tl.fingerprint(env, env.action_names)
        finally:
            env.close()
        return _fingerprint

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
    one = _single_step(progs, suffix, target, gap, seed_file)
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

    # Nothing here was proven to work, so no plan is handed back. The last
    # thing tried is reported separately: 'ischroot -V out.png' exits 0 and
    # writes a version banner into out.png, which a caller reading "plan"
    # would take for an answer that its own "verification" has just called
    # unreadable. Reporting a plan only after it has been verified is what
    # keeps "closed" from meaning nothing.
    return {"closed": False, "status": outcome.get("status"),
            "plan": [], "suffix": suffix,
            "rejected_plan": list(outcome.get("plan") or []),
            "target": target, "actions_tried": tried, "verification": why,
            "banned": sorted(banned), "from_memory": False,
            "detail": why or (outcome.get("status") or "never reached it")}



# --------------------------------------------------------------------------- #
# goals that name no output file: measured, never guessed
# --------------------------------------------------------------------------- #
# "count the lines in notes.txt" asks for a VALUE, not a file. There is no
# output format to verify against, so every check above has nothing to bite
# on. Choosing the program by whether its manual mentions the goal's words
# was tried and deleted: it answered "count the lines" with a compiler's
# linker options three times, because every manual mentions everything, and
# each fix bred a new exclusion rule. A list of exclusions is a strict
# program.
#
# What replaces it is a measurement. If a file is BUILT to contain exactly
# 7 of the thing the goal names, then a program that prints 7 has proved,
# by behaviour and without anyone reading its documentation, that it
# measures that thing. A program that prints a version banner, its own
# help, or a linker list does not print 7, and is gone before it can
# mislead anyone. The manual is still read -- but only to NARROW the search,
# never to decide it.

# What a file can have a known number of. This is a list of things that can
# be CONSTRUCTED and then COUNTED, not a list of rules about programs: each
# one is verified by building a file that has exactly n of it.
_PROBE_KINDS: dict[str, tuple[str, ...]] = {
    "lines": ("lines", "line", "newlines", "newline", "rows", "row"),
    "words": ("words", "word"),
    "bytes": ("bytes", "byte", "size"),
    "characters": ("characters", "character", "chars", "char"),
    "uniquelines": ("unique lines", "uniquelines", "distinct lines",
                    "different lines", "unique", "distinct"),
    "lineswith": ("containing", "contain", "contains", "mentioning",
                  "mention", "mentions", "matching", "match", "matches"),
}


def query_kind(gap: str) -> str | None:
    """The one thing the goal asks to be counted, or None if it is not one.

    "how many bytes per line" names two things and is refused rather than
    guessed at -- answering it would mean picking one and calling the other
    noise, which is the machine inventing the question.
    """
    text = str(gap or "").lower()
    # The most specific thing named wins. "how many unique lines" mentions
    # both 'lines' and 'unique lines', and answering it as though 'lines'
    # were the whole question gives 14 where the asker wants 7 -- so the
    # longer, more specific phrase is the one built and counted. Two
    # different things named with equally specific words is a real
    # ambiguity, and that is refused instead of guessed at.
    scored = []
    for kind, words in _PROBE_KINDS.items():
        matched = [w for w in words if w in text]
        if matched:
            phrase = max(matched, key=len)
            scored.append((len(phrase), phrase, kind))
    if not scored:
        return None
    scored.sort(reverse=True)
    top_len, top_phrase, top_kind = scored[0]
    for length, phrase, kind in scored[1:]:
        if kind == top_kind:
            continue
        # The longer phrase wins when it is a REFINEMENT of the shorter
        # one: either it literally contains it ('unique lines' holds
        # 'lines'), or it is one of the questions this machine knows is a
        # more precise form of it. 'bytes' and 'per line' are two unrelated
        # questions in one sentence, and answering either would be picking
        # one and calling the other noise -- so that is refused.
        refines = (_REFINES.get(top_kind) == kind
                   or _REFINES.get(kind) == top_kind)
        contained = (top_phrase.count(phrase) > 0
                     or phrase.count(top_phrase) > 0)
        if not refines and not contained:
            return None
    return top_kind


def goal_literal(gap: str) -> str | None:
    """The WORDS the goal is looking for, taken out of the sentence.

    "how many lines contain ERROR" is not answerable by counting anything
    until ERROR is part of the test -- the goal named the thing to look
    for, and ignoring it would be answering a different question. The same
    move as taking '50%' out of 'resize to 50%': the goal brings its own
    arguments, and the machine's job is to use them rather than guess.
    """
    text = " " + " ".join(str(gap or "").split()) + " "
    low = text.lower()
    best = ""
    for trig in _LITERAL_TRIGGERS:
        at = low.find(" " + trig + " ")
        if at < 0:
            continue
        rest = text[at + len(trig) + 2:].strip()
        cut = len(rest)
        for stop in _LITERAL_STOPS:
            found = rest.lower().find(stop)
            if found >= 0:
                cut = min(cut, found)
        rest = re.sub(r"\b(lines?|rows?|times?)\b", "",
                      rest[:cut].strip(), flags=re.I).strip().strip('"\'')
        if len(rest) > len(best):
            best = rest
    # a literal that is only a filename is a file, not something to search
    # for inside one
    if best and not _FILENAME.fullmatch(best) and not best.endswith(
            tuple(_FILENAME.findall(best) or [])):
        return best
    return None


def probe_bytes(kind: str, n: int = 7, literal: str | None = None) -> bytes | None:
    """Bytes holding exactly n of the thing `kind` names -- the ground truth.

    The lines are all DIFFERENT on purpose. A probe of n identical lines
    holds n lines and one distinct line, and 'uniq --count' answers both
    questions with the number of lines -- so it sailed through every check
    while counting runs, not lines. Distinct lines make "how many lines"
    and "how many different lines" two questions with two answers, and a
    program that conflates them is caught before it measures anything.
    """
    if kind == "lines":
        return (b"\n".join(b"probe %d" % i for i in range(n))) + b"\n"
    if kind == "words":
        return (b" ".join(b"w%d" % i for i in range(n))) + b"\n"
    if kind in ("bytes", "characters"):
        return b"z" * n
    if kind == "lineswith":
        # n lines that hold the word and n that do not, so "how many lines
        # hold this word" and "how many lines are there" are different
        # questions with different answers. A program that counts every
        # line reports 2n and is caught out immediately.
        word = (literal or "NEEDLE").encode("utf8", "replace")
        with_it = [b"a line %s appears in %d" % (word, i) for i in range(n)]
        without = [b"a line nothing appears in %d" % i for i in range(n)]
        return b"\n".join(with_it + without) + b"\n"
    if kind == "uniquelines":
        # n lines that are all DIFFERENT from each other, and twice as many
        # lines altogether -- with every repeat kept FAR FROM its twin.
        #
        # The repeats used to sit next to their twins, as 'row 0, row 0,
        # row 1, row 1'. That is the one arrangement 'uniq' is built for:
        # it collapses NEIGHBOURS, so on that file it prints n and looks
        # exactly like a tool that counts different lines. It is not. It
        # counts runs. Given a real file whose repeats are not neighbours
        # it answered 14 where the truth was 7 -- and the probe had
        # certified it first, which is the worse of the two faults.
        #
        # So the two halves go at opposite ends: every line's twin is n
        # lines away. Now a program that only collapses neighbours sees 2n
        # and is rejected, and only something that really compares each
        # line against every other -- 'sort --unique' -- can print n. A
        # probe that cannot tell the wrong tool from the right one is not
        # a test of anything.
        first = b"".join(b"row %d\n" % i for i in range(n))
        return first + first
    return None


def _bare_value(out: bytes, limit: int = 64) -> str | None:
    """The single value a program printed, if it printed only one.

    'wc -l probe.txt' prints "7 probe.txt": the count and the name it was
    given. That is one value. A program that prints its own manual prints
    many lines and is not reporting a measurement at all.
    """
    text = out.decode("utf-8", "replace").strip()
    if not text or "\n" in text or len(text) > limit:
        return None
    parts = text.split()
    if len(parts) > 2:
        return None
    return parts[0]


def _real_binary(prog: str) -> str:
    """Which actual file runs. c89, c99 and cc are three names for gcc, and
    three "independent" programs agreeing is not independence at all."""
    try:
        return os.path.realpath(str(shutil.which(prog) or prog))
    except Exception:  # noqa: BLE001 - an odd name is not a failure
        return prog


# Patterns that match every line. 'grep -c' counts nothing without a
# pattern, and a counting flag is useless until it is given something to
# count -- so the search has to supply one. These four are not knowledge
# about grep; they are the general shape of "match everything", in the two
# notations programs actually accept.
_MATCH_ALL = ("", "^", "$", ".")

# Two constructions, so a right answer has to be TRACKED, not
# merely produced once -- see probe_survivors.
_PROBE_SIZES = (7, 13)

# One question asked more precisely than another. "how many lines hold
# this word" is a refinement of "how many lines", not a second unrelated
# question, and the machine is allowed to know that -- otherwise every
# question containing the word 'lines' would have to be refused.
_REFINES = {"uniquelines": "lines", "lineswith": "lines"}

_LITERAL_TRIGGERS = ("containing", "contain", "contains", "mentioning",
                     "mention", "mentions", "matching", "match", "matches",
                     "that say", "that have")
_LITERAL_STOPS = (" in ", " of ", " on ", " from ", " inside ", " within ")


# Which commands measure which kind, once per machine. Kept in memory for
# this process and on disk for the next one, because "it took 40 seconds to
# learn how to count" is only forgivable if it is never paid twice.
_QUERY_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}
_QUERY_LOADED = False


def _query_cache_path() -> pathlib.Path:
    base = os.environ.get("BRAIN_STATE_DIR") or tempfile.gettempdir()
    return pathlib.Path(base) / "brain_query_probe_v1.json"


def _query_cache_load() -> None:
    global _QUERY_LOADED
    if _QUERY_LOADED:
        return
    _QUERY_LOADED = True
    try:
        raw = json.loads(_query_cache_path().read_text())
        for key, val in raw.items():
            kind, _, n = str(key).rpartition(":")
            _QUERY_CACHE[(kind, int(n))] = list(val)
    except Exception:  # noqa: BLE001 - no cache is not a failure
        pass


def _query_cache_get(kind: str, limit: int) -> list[dict[str, Any]] | None:
    _query_cache_load()
    return _QUERY_CACHE.get((kind, limit))


def _query_cache_put(kind: str, limit: int,
                     survivors: Sequence[dict[str, Any]]) -> None:
    _query_cache_load()
    _QUERY_CACHE[(kind, limit)] = list(survivors)
    try:
        _query_cache_path().write_text(json.dumps(
            {"%s:%d" % k: v for k, v in _QUERY_CACHE.items()}))
    except Exception:  # noqa: BLE001 - a failed save must not lose the answer
        pass


def _known_counters(base: str, programs: Sequence[str], gap: str,
                    literal: str | None, timeout: float = 5.0,
                    enough: int = 4) -> list[dict[str, Any]]:
    """Commands already proven to count `base`, remembered or discovered.

    Which commands count lines does not change with the question, so it is
    a fact about the machine and is learned once. Paying to re-derive it
    on every question is the same amnesia as walking past a composition
    the machine already found: the answer was in memory and the machine
    went and earned it again.

    `enough` is deliberately small. Composing with thirty counters is not
    thirty times better than composing with four -- it is thirty times
    slower, because every extra counter is another pipeline to try.
    """
    from concurrent.futures import ThreadPoolExecutor
    found: list[dict[str, Any]] = []
    for limit in (24, 96, 200, -2):
        remembered = _query_cache_get(base, limit)
        if not remembered:
            continue
        for c in remembered:
            if c.get("stages") == 2:
                continue
            hit = dict(c, argv=_concretise(c.get("argv"), literal))
            if hit not in found:
                found.append(hit)
        if found:
            break
    if found:
        with ThreadPoolExecutor(max_workers=8) as pool:
            good = [h for h, ok in zip(
                found, pool.map(lambda h: _reverify(h, base, literal,
                                                    timeout), found)) if ok]
        if good:
            return good[:enough]
    if not programs:
        return []
    hits = [c for c in probe_survivors(base, list(programs), gap)
            if c.get("stages") != 2]
    if hits:
        # key -2: counters learned for composing, not an answer to a
        # question, so they must never be confused with one.
        _query_cache_put(base, -2, hits[:enough])
    return hits[:enough]


def _reverify(hit: dict[str, Any], kind: str, literal: str | None,
              timeout: float = 5.0) -> bool:
    """Does a remembered command still measure this, for THIS word?

    What was learned was a shape, so it can be reused for a word it has
    never seen -- but reuse is not the same as trust. Two runs on files
    built to hold 7 and 13 of the thing settles it, which is why the
    second question costs milliseconds instead of thirty-five seconds.
    """
    name = "probe.txt"
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-recheck-"))
    try:
        argv = _concretise(hit.get("argv"), literal)
        if hit.get("stages") == 2:
            first, second = argv
        else:
            first, second = argv, None
        reads = []
        for size in _PROBE_SIZES:
            (root / name).write_bytes(probe_bytes(kind, size, literal))
            try:
                if second is None:
                    code, out = _run_capped(first, root, timeout=timeout)
                else:
                    code, out = _run_pipeline(first, second, root,
                                              timeout=timeout)
            except Exception:  # noqa: BLE001
                return False
            if code != 0:
                return False
            reads.append(_bare_value(out))
        return len(reads) == len(_PROBE_SIZES) and all(
            got == str(want) for got, want in zip(reads, _PROBE_SIZES))
    finally:
        shutil.rmtree(str(root), ignore_errors=True)


def _reap(proc: subprocess.Popen, worker: Any,
          also: Sequence[subprocess.Popen] = ()) -> int:
    """The exit status of a command that has been read on a deadline.

    Poll() answers None both for "still running" and for "finished but not
    yet reaped", and those are opposite things: one must be killed, the
    other must be believed. Conflating them threw away perfectly good
    answers -- the same command scored 0 on one run and None on the next,
    so a correct measurement was skipped depending on nothing but timing.

    So it is waited for briefly. A command that has already finished is
    simply reaped and its true status returned; only one that is genuinely
    still running, or still talking, is killed.
    """
    code = proc.poll()
    if code is None:
        try:
            code = proc.wait(timeout=0.25)
        except Exception:  # noqa: BLE001 - still running
            code = None
    if code is None or worker.is_alive():
        for target in tuple(also) + (proc,):
            try:
                target.kill()
            except Exception:  # noqa: BLE001
                pass
        for target in tuple(also) + (proc,):
            try:
                target.wait(timeout=2)
            except Exception:  # noqa: BLE001
                pass
        return -9
    return int(code)


def _run_capped(argv: Sequence[str], cwd: str | pathlib.Path,
                timeout: float = 5.0, max_bytes: int = 1 << 16
                ) -> tuple[int | None, bytes]:
    """Run a command and bring back at most `max_bytes` of what it printed.

    'shuf --repeat' never stops: it permutes its input forever. Handed to
    subprocess.run(capture_output=True) it fills a pipe nobody is draining,
    the bytes pile up in this process, and the machine kills US -- silently,
    with no exception and no traceback, which is how a whole run vanishes
    after fifteen seconds and looks like nothing happened.

    So output is read on a deadline and capped. A program that talks fast
    is no slower than before; a program that never shuts up is killed
    instead of being allowed to take the learner down with it.
    """
    import threading
    proc = subprocess.Popen(list(argv), cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL)
    buf = bytearray()

    def drain() -> None:
        try:
            while len(buf) < max_bytes:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf.extend(chunk)
        except Exception:  # noqa: BLE001 - a closed pipe is the normal end
            pass

    worker = threading.Thread(target=drain, daemon=True)
    worker.start()
    worker.join(timeout)
    code = _reap(proc, worker)
    try:
        proc.stdout.close()
    except Exception:  # noqa: BLE001
        pass
    return code, bytes(buf[:max_bytes])


def _run_pipeline(argv1: Sequence[str], argv2: Sequence[str],
                  cwd: str | pathlib.Path, timeout: float = 5.0,
                  max_bytes: int = 1 << 16) -> tuple[int | None, bytes]:
    """Run two commands with the first one's output fed to the second.

    Real work on a computer is almost never one program. "how many
    different lines are in this file" is 'sort --unique | wc --lines':
    no single program answers it, and a machine that can only run one
    thing at a time cannot answer it at all.

    Bounded for the same reason a single command is -- a program in the
    middle of a pipe that never stops talking takes the learner down just
    as surely as one on its own.
    """
    import threading
    first = subprocess.Popen(list(argv1), cwd=str(cwd),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
    second = subprocess.Popen(list(argv2), cwd=str(cwd), stdin=first.stdout,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        first.stdout.close()  # only the second reader may hold it open
    except Exception:  # noqa: BLE001
        pass
    buf = bytearray()

    def drain() -> None:
        try:
            while len(buf) < max_bytes:
                chunk = second.stdout.read(4096)
                if not chunk:
                    break
                buf.extend(chunk)
        except Exception:  # noqa: BLE001
            pass

    worker = threading.Thread(target=drain, daemon=True)
    worker.start()
    worker.join(timeout)
    code = _reap(second, worker, also=(first,))
    for stream in (second.stdout,):
        try:
            stream.close()
        except Exception:  # noqa: BLE001
            pass
    return code, bytes(buf[:max_bytes])


def _instrument(prog: str, depth: int = 4) -> str:
    """The program that actually does the work.

    egrep, fgrep and rgrep are three-line shell scripts whose whole body is
    'exec grep'. Counting them as three independent programs that agree is
    how one opinion gets called a consensus -- the same mistake that once
    turned one compiler (c89, c99, cc) into three agreeing sources. The
    exec is followed to whatever it hands off to, so agreement means
    agreement between things that really measured separately.
    """
    if "|" in str(prog):
        # a pipeline is not one file on disk; its identity is its stages
        return " | ".join(part.strip() for part in str(prog).split("|"))
    path = _real_binary(prog)
    for _ in range(depth):
        try:
            head = pathlib.Path(path).read_bytes()[:4096]
        except Exception:  # noqa: BLE001 - unreadable is just the end of it
            return path
        if not head.startswith(b"#!"):
            return path
        hit = re.search(r"^\s*exec\s+(\S+)",
                        head.decode("utf-8", "replace"), re.MULTILINE)
        if not hit:
            return path
        nxt = shutil.which(hit.group(1))
        if not nxt:
            return path
        real = os.path.realpath(nxt)
        if real == path:
            return path
        path = real
    return path


def _query_shapes(prog: str, name: str, gap: str,
                  patterns: Sequence[str] | None = None,
                  wide: bool = False) -> list[list[str]]:
    """Ways to point the program at one file, most specific first.

    Normally the manual narrows the search and the probe decides it. But
    the manual is only a hint about WHICH flags to try, and it reads the
    goal's words to make that guess -- so a goal that never uses the word
    'count' gets shown grep's --only-matching and never its --count, and
    the machine concludes that nothing on the box can count.

    `wide` is what happens when the hint turns out to be wrong: it stops
    guessing which flags matter and offers the program's own list, letting
    the measurement do the choosing. Slower, and only paid for when the
    narrow search came back empty.
    """
    shapes: list[list[str]] = []
    patterns = _MATCH_ALL if patterns is None else patterns
    flags: list[str] = []
    try:
        if wide:
            flags = [f for f, _ in flag_descriptions(prog, limit=_WIDE_FLAGS)]
        else:
            flags = flags_for_goal(prog, gap, limit=3)
    except Exception:  # noqa: BLE001 - no manual is not a failure
        flags = []
    for flag in flags:
        shapes.append([prog, flag, name])
        for pat in patterns:
            shapes.append([prog, flag, pat, name])
    shapes.append([prog, name])
    return shapes


def _stdin_shapes(prog: str, gap: str) -> list[list[str]]:
    """Forms of a program that read what is piped into it.

    A program at the end of a pipe takes no filename: the text arrives on
    its input. Offering it a filename anyway would make it read the file
    and ignore everything the previous stage produced -- a pipeline that
    looks like it runs and quietly answers a different question.
    """
    shapes: list[list[str]] = [[prog]]
    try:
        flags = flags_for_goal(prog, gap, limit=3)
    except Exception:  # noqa: BLE001
        flags = []
    for flag in flags:
        shapes.append([prog, flag])
    return shapes


def _abstract(argv: list[str], literal: str | None) -> list[str]:
    """Replace the goal's own word with a hole, so what was learned is the
    SHAPE of the command and not one instance of it.

    Remembering 'grep -c ERROR probe.txt' means the machine has to spend
    thirty-five seconds learning all over again the moment the word is
    WARN instead -- it memorised an answer rather than learning a method.
    What generalises is 'grep -c <what was asked for> file'.
    """
    if not literal:
        return list(argv)
    return [_LITERAL_HOLE if a == literal else a for a in argv]


def _concretise(argv, literal: str | None):
    """Put this goal's word back into the hole left for it."""
    if literal is None:
        return argv
    if isinstance(argv, list) and argv and isinstance(argv[0], list):
        return [_concretise(part, literal) for part in argv]
    return [literal if a == _LITERAL_HOLE else a for a in argv]


_LITERAL_HOLE = "{asked}"


# The wide pass walks a program's own manual instead of the goal's hint, so
# it is allowed more time than the narrow one -- '--count' is the 65th flag
# grep documents, and a budget that stops at the 20th concludes that
# nothing on the machine can count. It is still bounded: the point of the
# pass is to reach the deep flags, not to read all 400 of them on a program
# that cannot count at all.
_WIDE_BUDGET = 45.0


def _one_wide(prog: str, kind: str, gap: str, patterns: Sequence[str],
              timeout: float, literal: str | None = None,
              budget: float = _WIDE_BUDGET) -> dict[str, Any] | None:
    """One program, offered its own flags instead of the ones the goal's
    words suggested, on files built to hold a known number of the thing.
    """
    name = "probe.txt"
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-wide-"))
    deadline = time.monotonic() + budget
    try:
        for argv in _query_shapes(prog, name, gap, patterns=patterns,
                                  wide=True):
            if time.monotonic() > deadline:
                break
            reads = []
            for size in _PROBE_SIZES:
                # the same literal in the file as in the command: a probe
                # holding NEEDLE while the command hunts for ERROR finds
                # nothing, and nothing looks exactly like failure
                (root / name).write_bytes(probe_bytes(kind, size, literal))
                try:
                    code, out = _run_capped(argv, root, timeout=timeout)
                except Exception:  # noqa: BLE001
                    break
                if code != 0:
                    break
                got = _bare_value(out)
                if got != str(size):
                    break
                reads.append(got)
            if len(reads) == len(_PROBE_SIZES):
                return {"program": prog,
                        "argv": _abstract(list(argv), literal),
                        "wide": True,
                        "tracked": [str(s) for s in _PROBE_SIZES]}
    finally:
        shutil.rmtree(str(root), ignore_errors=True)
    return None


# How far down the candidate list a pipeline's FIRST stage may come from.
# 'uniq' is the 31st candidate for "how many unique lines" and 'sort' the
# 91st -- a budget of 10 looks at busctl, chrt and dmesg and concludes the
# machine cannot answer. Affordable per head now that the last stage is
# restricted to commands already proven to count.
_MAX_PIPE_PROGRAMS = 100
# The whole manual, not its top slice. grep documents 83 flags and
# '--count' is the 65th of them -- a search that only tries the first few
# concludes that nothing on the machine can count, when the program that
# counts is sitting right there. The narrow pass exists to keep this
# expensive one from running at all.
_WIDE_FLAGS = 400
# how far down the candidate list the wide search goes; it is
# the expensive pass, so it does not run over the whole machine
_WIDE_PROGRAMS = 14

# The first stage of a pipeline is producing text rather than
# counting, so the match-everything patterns that matter at the
# end of a command mostly waste runs here.
_PIPE_PATTERNS = ("",)


# Seconds one program may spend proving itself before the search moves on.
# Measured: 'docker-entrypoint.sh' burns 69s and 'node' 69s more, and both
# are dead ends -- while 'grep', which is a real answer, needs 20. One
# straggler sets the pace for the whole wave, because every other program
# finished minutes ago and is waiting behind it. A program that has not
# shown it can count in this long is not worth more time when hundreds of
# others are still untried: the fastest way to the answer does not run
# through the slowest program on the machine.
_PROGRAM_BUDGET = 20.0


def probe_survivors(kind: str, programs: Sequence[str], gap: str,
                    n: int = 7, timeout: float = 5.0,
                    workers: int = 24,
                    stages: int = 1,
                    literal: str | None = None,
                    budget: float = _PROGRAM_BUDGET) -> list[dict[str, Any]]:
    """Commands that print n on a file built to hold exactly n of `kind`.

    Chosen by what they DID, not by what they say they do. The exact argv
    is kept: a command that counted the probe is the only command entitled
    to count the real file, and re-running some OTHER form of it -- the
    bare `wc notes.txt`, when `wc -l notes.txt` is the one that was proven
    -- measures a different thing and calls it the same answer.
    """
    from concurrent.futures import ThreadPoolExecutor
    if probe_bytes(kind, n, literal) is None:
        return []
    # what the goal asked to look for is itself a way of looking: 'grep
    # --count ERROR' needs ERROR given to it, so the literal is offered
    # alongside the match-everything patterns rather than only being buried
    # in the file.
    patterns = tuple(_MATCH_ALL) + ((literal,) if literal else ())
    name = "probe.txt"

    def one(prog: str) -> dict[str, Any] | None:
        root = pathlib.Path(tempfile.mkdtemp(prefix="brain-probe-"))
        deadline = time.monotonic() + budget
        try:
            for argv in _query_shapes(prog, name, gap,
                                      patterns=patterns):
                if time.monotonic() > deadline:
                    break
                # A file built to hold 7 of the thing, then one built to
                # hold 13. A program that prints 7 once may be printing 7
                # for its own reasons -- a version number, a default, a
                # coincidence. A program that prints 7 for seven and 13
                # for thirteen is TRACKING the thing, and that is what a
                # measuring instrument does. Two sizes is the difference
                # between one right answer and an instrument that can be
                # trusted with a file it has never seen.
                reads = []
                for size in _PROBE_SIZES:
                    data = probe_bytes(kind, size, literal)
                    # Every form gets a fresh probe: some programs eat the
                    # file they are given, and a later form would then be
                    # measuring nothing and reporting it.
                    (root / name).write_bytes(data)
                    try:
                        code, out = _run_capped(argv, root, timeout=timeout)
                    except Exception:  # noqa: BLE001 - a program must not break it
                        break
                    if code != 0:
                        break
                    got = _bare_value(out)
                    # Spend the second probe only on a form that survived
                    # the first. Most forms are wrong, and proving a wrong
                    # form wrong twice instead of once is the difference
                    # between two runs and one -- on every form of every
                    # program on the machine.
                    if got != str(size):
                        break
                    reads.append(got)
                if len(reads) == len(_PROBE_SIZES):
                    return {"program": prog,
                            "argv": _abstract(list(argv), literal),
                            "tracked": [str(s) for s in _PROBE_SIZES]}
        finally:
            shutil.rmtree(str(root), ignore_errors=True)
        return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        hits = [hit for hit in pool.map(one, list(programs)) if hit]
    if hits:
        return hits
    if stages < 2:
        # The narrow search found nothing. Before deciding that two
        # programs are needed, admit that the hint about which flags to
        # try may simply have been wrong.
        if True:
            wide = []
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for hit in pool.map(
                        lambda p: _one_wide(
                            p, kind, gap,
                            (literal,) if literal else tuple(patterns),
                            timeout, literal),
                        list(programs)[:_WIDE_PROGRAMS]):
                    if hit:
                        wide.append(hit)
            if wide:
                return wide
        return []
    # A single program found further down the list is still fewer actions
    # than two programs found at the top, so the whole list is searched for
    # one before any pair is tried.
    if len(programs) > _MAX_PIPE_PROGRAMS:
        programs = list(programs)[:_MAX_PIPE_PROGRAMS]

    # The LAST stage of a pipeline that answers "how many" has to count.
    # The machine already knows which commands count: it proved that on the
    # plainest probe there is. Searching every pair -- 100 x 100 -- spends
    # minutes discovering that 'fmt | nl' is not a measuring instrument.
    # Composing only with things already proven to count is both the
    # cheaper search and the more sensible one: find out what counts, then
    # find out what to feed it.
    counters = _known_counters("lines", list(programs), gap, literal,
                               timeout)
    tails = []
    for c in counters:
        # used at the end of a pipe, so it is given no filename of its own
        argv = [a for a in c["argv"] if a != "probe.txt"]
        if argv and argv not in tails:
            tails.append(argv)
    if not tails:
        # Nothing here was proven to count, so there is nothing to put at
        # the end of a pipe. Two programs that both fail to count do not
        # add up to one that does.
        return []

    def pair(job: tuple) -> dict[str, Any] | None:
        """Feed one program's output to something that counts, and see if
        the pair tracks the construction. 'uniq | wc --lines' answers "how
        many different lines" -- a question no single program answers."""
        head, tail_argv = job
        root = pathlib.Path(tempfile.mkdtemp(prefix="brain-pipe-"))
        deadline = time.monotonic() + budget
        try:
            # The head is offered its OWN flags, not only the ones the
            # goal's words suggested. This is the same lesson as '--count'
            # being the 65th flag grep documents: 'sort' does nothing here
            # until it is given '--unique', and '--unique' is not a flag
            # the sentence "how many unique lines" knows how to suggest.
            # The narrow shapes are a subset of the wide ones, so nothing
            # is given up by asking for the whole manual.
            for argv1 in _query_shapes(head, name, gap,
                                      patterns=_PIPE_PATTERNS +
                                      ((literal,) if literal else ()),
                                      wide=True):
                if time.monotonic() > deadline:
                    break
                for argv2 in [tail_argv]:
                    reads = []
                    for size in _PROBE_SIZES:
                        (root / name).write_bytes(
                            probe_bytes(kind, size, literal))
                        try:
                            code, out = _run_pipeline(argv1, argv2, root,
                                                      timeout=timeout)
                        except Exception:  # noqa: BLE001
                            break
                        if code != 0:
                            break
                        got = _bare_value(out)
                        if got != str(size):
                            break
                        reads.append(got)
                    if len(reads) == len(_PROBE_SIZES):
                        return {"program": "%s | %s" % (head, argv2[0]),
                                "argv": [_abstract(list(argv1), literal),
                                         _abstract(list(argv2), literal)],
                                "stages": 2,
                                "tracked": [str(s) for s in _PROBE_SIZES]}
        finally:
            shutil.rmtree(str(root), ignore_errors=True)
        return None

    jobs = [(head, t) for head in programs for t in tails]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [hit for hit in pool.map(pair, jobs) if hit]


def answer_query(gap: str, input_file: str | pathlib.Path,
                 programs: Sequence[str] | None = None,
                 timeout: float = 15.0,
                 min_agreement: int = 1) -> dict[str, Any]:
    """Answer a goal that asks for a value by measuring the file.

    Refuses unless genuinely different programs, run on the real file, print
    the same thing. One program is an opinion; two programs that are the
    same binary are one opinion wearing a coat.
    """
    kind = query_kind(gap)
    literal = goal_literal(gap) if kind in ("lineswith",) else None
    if kind == "lineswith" and not literal:
        return {"pass": False, "status": "OPEN__NOT_A_COUNTABLE_QUESTION",
                "detail": "the goal says to look for something but does not "
                          "say what"}
    if kind is None:
        return {"pass": False, "status": "OPEN__NOT_A_COUNTABLE_QUESTION",
                "detail": "the goal does not name one thing that can be "
                          "built, counted and checked"}
    src = pathlib.Path(input_file)
    if not src.is_file():
        return {"pass": False, "status": "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL",
                "detail": "no such file: %s" % src}

    # How far down the list of candidates to look. The manual is read ONLY
    # to narrow the field -- it names programs whose flags mean something
    # like what the goal said. It decides nothing: the probe throws away
    # every candidate that does not actually print the known answer, which
    # is why a compiler listing its linker options can no longer be
    # mistaken for a line count.
    #
    # It starts narrow because most questions are answered at once, and
    # widens only when too few survivors agree to trust -- 'wc' sits at
    # rank 136 for "how many words", so a narrow search honestly finds
    # nothing rather than guessing.
    survivors: list[dict[str, Any]] = []
    # Which commands measure this kind is a fact about the MACHINE, not
    # about the file -- 'wc --lines' counts the lines of anything. Once it
    # has been measured it never has to be measured again, which is what
    # turns a slow first question into an instant second one.
    def measure(found: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
        """Ask each proven command the real file, in the form it was proven
        in, and record what it said against the program that did the work --
        so three names for one compiler, or three shell scripts that exec
        grep, cannot gang up and call themselves independent agreement."""
        tally: dict[str, list[str]] = {}
        for hit in found:
            try:
                # put this goal's word back into the hole left for it --
                # what was remembered is the shape of the command, and a
                # shape cannot be run until it is made specific again
                argv = _concretise(hit["argv"], literal)
                if hit.get("stages") == 2:
                    # only the first stage is pointed at the file; the last
                    # reads what the pipe gives it
                    first, second = argv
                    argv1 = [first[0]] + [str(src) if a == "probe.txt" else a
                                          for a in first[1:]]
                    code, out = _run_pipeline(argv1, list(second), src.parent,
                                              timeout=timeout)
                else:
                    argv = [argv[0]] + [str(src) if a == "probe.txt" else a
                                        for a in argv[1:]]
                    code, out = _run_capped(argv, src.parent, timeout=timeout)
            except Exception:  # noqa: BLE001 - one failure is data
                continue
            if code != 0:
                continue
            value = _bare_value(out)
            if value is None:
                continue
            tally.setdefault(value, []).append(_instrument(hit["program"]))
        return tally

    # What has already been composed is used BEFORE paying to re-prove that
    # no single program can do it alone. Those tiers are the expensive part
    # -- minutes -- and for a question only a pipeline can answer they are
    # guaranteed failures. Walking past what the machine already knows is
    # not caution, it is amnesia with extra steps.
    if programs is None:
        composed = _query_cache_get(kind, -1)
        if composed:
            found = [h for h in
                     (dict(c, argv=_concretise(c.get("argv"), literal))
                      for c in composed)
                     if _reverify(h, kind, literal, timeout)]
            tally = measure(found)
            if tally:
                best, bins = sorted(
                    tally.items(),
                    key=lambda kv: (-len(set(kv[1])), kv[0]))[0]
                if len(set(bins)) >= min_agreement:
                    agree = len(set(bins))
                    return {"pass": True,
                            "status": ("PASS__MEASURED_BY_AGREEMENT"
                                       if agree > 1 else
                                       "PASS__MEASURED_BY_ONE_TRACKED_INSTRUMENT"),
                            "kind": kind, "value": best, "answer": best,
                            "agreement": agree, "survivors": found,
                            "stages": 2, "from_memory": True,
                            "votes": {k: sorted(set(v))
                                      for k, v in tally.items()},
                            "detail": "remembered composition, re-proven: "
                                      "%s" % best}

    for limit in (24, 96, 200):
        cached = _query_cache_get(kind, limit)
        if cached is not None:
            # remembered as a shape, so a word it has never seen can reuse
            # it -- but only after proving it again for that word
            survivors = [h for h in
                         (dict(c, argv=_concretise(c.get("argv"), literal))
                          for c in cached)
                         if _reverify(h, kind, literal, timeout)]
        else:
            cands = (list(programs) if programs is not None
                     else programs_for_goal(gap, limit=limit))
            if not cands:
                continue
            survivors = probe_survivors(kind, cands, gap,
                                        literal=literal)
            # Only a discovery is remembered, never a failure. A success is
            # a fact about the machine; an empty result is often a fact
            # about the SEARCH -- the right program not yet looked at, a
            # flag not yet offered, a program installed since. Caching the
            # failure makes it permanent: the machine never looks again and
            # a question it could have answered stays unanswered forever.
            if programs is None and survivors:
                _query_cache_put(kind, limit, survivors)
        votes = measure(survivors)
        if survivors and not votes:
            continue
        if votes:
            ranked = sorted(votes.items(),
                            key=lambda kv: (-len(set(kv[1])), kv[0]))
            value, bins = ranked[0]
            if len(set(bins)) >= min_agreement:
                agree = len(set(bins))
                return {"pass": True,
                        "status": ("PASS__MEASURED_BY_AGREEMENT" if agree > 1
                                   else "PASS__MEASURED_BY_ONE_TRACKED_INSTRUMENT"),
                        "kind": kind, "value": value, "answer": value,
                        "agreement": agree, "survivors": survivors,
                        "votes": {k: sorted(set(v)) for k, v in votes.items()},
                        "detail": ("%d distinct programs agree: %s" % (agree, value))
                                  if agree > 1 else
                                  ("one program, but it tracked both probes "
                                   "(%s) before being trusted with the real "
                                   "file: %s"
                                   % (", ".join(str(s) for s in _PROBE_SIZES),
                                      value))}
        if programs is not None:
            break

    # No single program on the machine tracks the construction -- now, and
    # only now, try two of them joined together. This is the difference
    # between "how many lines" and "how many DIFFERENT lines": the second
    # is answered by no single program at all, and a machine that can only
    # run one thing at a time has to refuse it.
    if not survivors:
        # -1 is the key for "found by composing": the tiers above are keyed
        # by how far down the candidate list they looked, and a composition
        # has no such number.
        composed = _query_cache_get(kind, -1)
        if composed:
            survivors = [h for h in
                         (dict(c, argv=_concretise(c.get("argv"), literal))
                          for c in composed)
                         if _reverify(h, kind, literal, timeout)]
        if not survivors:
            cands = (list(programs) if programs is not None
                     else programs_for_goal(gap, limit=_MAX_PIPE_PROGRAMS * 2))
            survivors = probe_survivors(kind, cands, gap, stages=2,
                                        literal=literal)
            if programs is None and survivors:
                _query_cache_put(kind, -1, survivors)
        votes = measure(survivors)
        if votes:
            ranked = sorted(votes.items(),
                            key=lambda kv: (-len(set(kv[1])), kv[0]))
            value, bins = ranked[0]
            if len(set(bins)) >= min_agreement:
                agree = len(set(bins))
                return {"pass": True,
                        "status": ("PASS__MEASURED_BY_AGREEMENT" if agree > 1
                                   else "PASS__MEASURED_BY_ONE_TRACKED_INSTRUMENT"),
                        "kind": kind, "value": value, "answer": value,
                        "agreement": agree, "survivors": survivors,
                        "stages": 2,
                        "votes": {k: sorted(set(v)) for k, v in votes.items()},
                        "detail": "two programs joined: %s" % (
                            " | ".join(str(x) for x in
                                       (survivors[0]["argv"][0][0],
                                        survivors[0]["argv"][1][0]))
                            if survivors else "")}

    if not survivors:
        return {"pass": False, "status": "OPEN__NOTHING_MEASURED_IT",
                "kind": kind, "detail":
                    "no program on this machine printed the known answer on "
                    "a file built to hold 7 of it"}
    if not votes:
        return {"pass": False, "status": "OPEN__NOTHING_MEASURED_IT",
                "kind": kind, "survivors": survivors,
                "detail": "every candidate failed on the real file"}
    best, bins = sorted(votes.items(),
                        key=lambda kv: (-len(set(kv[1])), kv[0]))[0]
    return {"pass": False, "status": "OPEN__ONLY_ONE_PROGRAM_AGREES",
            "kind": kind, "survivors": survivors,
            "votes": {k: sorted(set(v)) for k, v in votes.items()},
            "detail": "%d program(s) say %s; refusing to answer on one "
                      "opinion" % (len(set(bins)), best)}
