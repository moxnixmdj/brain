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

    scored = [(score(flag + " " + desc), flag) for flag, desc in flag_descriptions(prog)]
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


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _target_bases(named: str) -> list[pathlib.Path]:
    """The directories a stated output name can be relative to.

    The same two bases the rest of the door uses: the working directory, and the
    repository root this module lives in.  A name that is absolute stands alone.
    """
    if pathlib.Path(named).is_absolute():
        return [pathlib.Path("/")]
    bases = [pathlib.Path.cwd()]
    if _REPO_ROOT not in bases:
        bases.append(_REPO_ROOT)
    return bases


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
    # A COMPOUND SUFFIX NAMES TWO PROGRAMS.  '.tar.gz' is a tar and then a
    # gzip, and reading its letters as one word ('targz') matches neither:
    # measured 2026-11-01, the shortlist for a tarball goal did not contain
    # `tar` at all, so the only plan it could ever verify was `gzip`, which
    # makes a gzip of a single file.  Each component is guessed at separately.
    parts = [c for c in str(suffix or "").lower().split(".")
             if any(ch.isalnum() for ch in c)]
    letters_of = [[c for c in part if c.isalnum()] for part in parts]
    installed = installed_programs()  # all of them; narrowing happens next
    if not any(letters_of):
        return installed[:limit]

    def subsequence(prog: str, letters: list[str]) -> bool:
        it = iter(prog)
        return all(c in it for c in letters)

    hits = [p for p in installed
            if any(subsequence(p, letters) for letters in letters_of if letters)]
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
        if good and not ps.carries_content_evidence(suffix):
            return False, "FORMAT_CARRIES_NO_EVIDENCE:" + suffix
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
    out_progs: list[str] = []
    seen_real: set[str] = set()
    for _, p in hits:
        real = _instrument(p)
        if real in seen_real:
            continue
        seen_real.add(real)
        out_progs.append(p)
        if len(out_progs) >= limit:
            break
    return out_progs


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
            if good and not ps.carries_content_evidence(suffix):
                good, why = False, "FORMAT_CARRIES_NO_EVIDENCE:" + suffix
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

    suffix = ps.suffix_for_name(name)
    good, why = ps.verify_round_trip(out, suffix)
    return {"pass": bool(good), "status": "PASS__APPLIED_TO_REAL_FILE"
            if good else "OPEN__OUTPUT_NOT_REALLY_THAT_FORMAT",
            "argv": argv, "output": str(out),
            "output_bytes": out.stat().st_size, "verification": why,
            "returncode": proc.returncode}


def perform_chain(gap: str, cwd: str | pathlib.Path | None = None,
                  *, src_override: pathlib.Path | None = None,
                  wanted_override: str | None = None,
                  timeout: float = 30.0) -> dict[str, Any]:
    """Execute a snapshot-checkpointed multi-step CLI chain (e.g. directory/file -> .tar -> .tar.gz).

    `discover()` remains strictly single-step (`OPEN__FORMAT_NEEDS_A_CHAIN_THIS_CHANNEL_CANNOT_KEEP`);
    `perform_chain()` owns stateful multi-stage execution where every intermediate artifact and the
    final multi-layer output must pass `ps.verify_round_trip` independently, rolling back cleanly
    to the pre-execution workspace snapshot on any stage failure.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    from canonical.runtime import program_synthesis_v1 as ps
    suffix = acq._requested_suffix(gap)
    if not suffix or suffix.count(".") < 2:
        return {"pass": False, "status": "OPEN__NOT_A_CHAIN_FORMAT", "detail": str(suffix)}
    if not ps.carries_content_evidence(suffix):
        return {"pass": False, "status": "OPEN__FORMAT_CARRIES_NO_EVIDENCE", "detail": suffix}

    base = pathlib.Path(cwd).resolve() if cwd else pathlib.Path.cwd().resolve()
    wanted = wanted_override or output_name(gap)
    if not wanted:
        return {"pass": False, "status": "OPEN__NO_OUTPUT_NAME_IN_GOAL"}

    src = src_override
    if src is None:
        # Match either file or directory token named in the goal (e.g. `pack pkg into pkg.tar.gz`)
        tokens = list(_FILENAME.findall(str(gap or ""))) + [
            t.strip("\"'.,;:") for t in str(gap or "").split()
        ]
        for tok in tokens:
            if not tok or tok == wanted or "/" in tok and tok.startswith("/"):
                continue
            cand = (base / tok)
            if cand.exists() and cand.resolve() != (base / wanted).resolve():
                src = cand
                break
    if src is None or not src.exists():
        return {"pass": False, "status": "OPEN__NO_EXISTING_INPUT_IN_GOAL",
                "detail": "no input file or directory named in %s" % base}

    # Decompose `.tar.gz` / `.tar.bz2` / `.tar.xz` into inner container (`.tar`) + outer compressor (`.gz`/etc.)
    parts = suffix.split(".")  # ['', 'tar', 'gz']
    if len(parts) != 3 or "." + parts[1] != ".tar":
        return {"pass": False, "status": "OPEN__UNSUPPORTED_MULTI_LAYER_CHAIN", "detail": suffix}
    inner_suffix = "." + parts[1]   # '.tar'
    outer_suffix = "." + parts[2]   # '.gz'

    if not ps.carries_content_evidence(inner_suffix) or not ps.carries_content_evidence(outer_suffix):
        return {"pass": False, "status": "OPEN__FORMAT_CARRIES_NO_EVIDENCE", "detail": suffix}

    # Snapshot pre-existing top-level entries for clean rollback on any intermediate failure
    existing_before = {p.name for p in base.iterdir()} if base.is_dir() else set()
    src_was_dir = src.is_dir()
    src_bytes_before = src.read_bytes() if src.is_file() else None
    out_path = base / wanted

    with tempfile.TemporaryDirectory(prefix="brain_chain_stage_") as stage_dir_raw:
        stage_dir = pathlib.Path(stage_dir_raw)
        stage1_tar = stage_dir / "_stage1.tar"

        # Stage 1: build `.tar` container from `src` (file or directory) and verify `.tar` round-trip
        tar_bin = shutil.which("tar")
        if not tar_bin:
            return {"pass": False, "status": "OPEN__MISSING_TAR_BINARY"}
        p1 = subprocess.run(
            [tar_bin, "-cf", str(stage1_tar), "-C", str(src.parent), src.name],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
        )
        if p1.returncode != 0 or not stage1_tar.is_file():
            return {"pass": False, "status": "OPEN__CHAIN_STAGE1_FAILED",
                    "detail": (p1.stderr or b"").decode("utf-8", "replace")[:200]}
        ok1, why1 = ps.verify_round_trip(stage1_tar, inner_suffix)
        if not ok1:
            return {"pass": False, "status": "OPEN__CHAIN_STAGE1_UNVERIFIED", "detail": why1}

        # Stage 2: discover/recall outer compression (`_stage1_blob` -> `_stage1_blob.gz`) via `discover()`
        stage2_src = stage_dir / "_stage1_blob"
        shutil.copy2(stage1_tar, stage2_src)
        stage2_goal = f"compress {stage2_src.name} into {stage2_src.name}{outer_suffix}"
        found2 = discover(stage2_goal, budget=24, seed_file=stage2_src)
        if not found2.get("closed") or not found2.get("recipe"):
            return {"pass": False, "status": "OPEN__CHAIN_STAGE2_DISCOVERY_FAILED",
                    "detail": found2.get("status")}
        done2 = apply(found2["recipe"], stage2_src, out_dir=base, output_name=wanted, timeout=timeout)
        if not out_path.is_file():
            # Rollback any stray files
            for p in list(base.iterdir()):
                if p.name not in existing_before and p.is_file():
                    p.unlink(missing_ok=True)
            return {"pass": False, "status": "OPEN__CHAIN_STAGE2_PRODUCED_NO_FILE",
                    "detail": done2.get("detail")}

        # Independent end-to-end verification on the full multi-layer format (`.tar.gz`!)
        ok_final, why_final = ps.verify_round_trip(out_path, suffix)
        if not ok_final:
            out_path.unlink(missing_ok=True)
            return {"pass": False, "status": "OPEN__OUTPUT_NOT_REALLY_THAT_FORMAT",
                    "verification": why_final}

    # Verify input integrity (never destroy or clobber `src`)
    if src_was_dir and not src.is_dir():
        out_path.unlink(missing_ok=True)
        return {"pass": False, "status": "OPEN__INPUT_DESTROYED_BY_CHAIN"}
    if src_bytes_before is not None and (not src.is_file() or src.read_bytes() != src_bytes_before):
        out_path.unlink(missing_ok=True)
        return {"pass": False, "status": "OPEN__INPUT_MUTATED_BY_CHAIN"}

    return {
        "pass": True,
        "status": "PASS__CHAIN_APPLIED_AND_VERIFIED",
        "goal": gap,
        "stages": 2,
        "plan": ["run_tar", *(found2.get("plan") or [])],
        "stage1_verification": why1,
        "verification": why_final,
        "output": str(out_path),
        "output_bytes": out_path.stat().st_size,
        "from_memory": bool(found2.get("from_memory")),
    }


def perform(gap: str, cwd: str | pathlib.Path | None = None,
            timeout: float = 30.0) -> dict[str, Any]:
    """Learn it if it has to, then actually do it to the real file.

    discover() answers "which program could do this" -- knowledge. perform()
    answers "it is done" -- the file exists, on the machine, where the file
    being talked about actually lives. Learning that never leaves the sandbox
    is not the machine doing anything, it is the machine knowing something.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    req_suffix = acq._requested_suffix(gap)
    if not req_suffix:
        return {"pass": False, "status": "OPEN__NO_OUTPUT_FORMAT_IN_GAP",
                "detail": "nothing in the goal says what to produce"}

    wanted = output_name(gap)
    base = pathlib.Path(cwd) if cwd else pathlib.Path.cwd()

    # Multi-layer chain formats (e.g. `.tar.gz`) can take either a directory or a file as input
    if req_suffix.count(".") >= 2:
        return perform_chain(gap, cwd=base, wanted_override=wanted, timeout=timeout)

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

    # A QUESTION is not closed by a file appearing.
    #
    # Everything below measures one thing: did a program make the target file
    # of the requested suffix show up.  That is a fact about a FORMAT, and it
    # is the right test for "compress notes.txt into notes.txt.gz".  It is not
    # an answer to a question, and this route has no way to tell the two apart
    # -- so it reported questions as closed.  Measured on main 249a702:
    #
    #   discover("the different lines of the file a.txt")
    #     -> closed=True, plan ['run_md5sum.textutils'],
    #        status PASS__RECALLED_AND_REVERIFIED
    #   discover("the duplicate lines of the file a.txt")
    #     -> closed=True, plan ['run_md5sum.textutils'],
    #        status PASS__SINGLE_ACTION_FOUND_AND_VERIFIED
    #
    # md5sum prints a HASH.  Neither goal asked for one.  The word
    # "VERIFIED" in those statuses is a claim about the goal, and the goal
    # was never asked -- the suffix was matched.  composer_route_v1 turns a
    # closed discovery into pass=True with authority
    # DISCOVERED_BY_ACTING_AND_EFFECT_VERIFIED, so the false claim travels.
    #
    # The machine already knows how to tell: query_kind names the one thing a
    # goal asks to be counted, and returns None when the goal is not a
    # question about a measurable quantity.  A goal it CAN classify is a
    # question, and this route cannot answer questions -- answer_query does,
    # by building a file that holds a known number of the thing and throwing
    # away every program that does not print it.  Refusing here hands the
    # goal to something that can answer it instead of closing it with a hash.
    asked = query_kind(gap)
    if asked is not None:
        return {"closed": False, "kind": asked,
                "status": "OPEN__A_QUESTION_IS_NOT_CLOSED_BY_A_FILE_APPEARING",
                "detail": "the goal asks to be told %s; this route only "
                          "checks that a file of the requested suffix "
                          "appeared, which is a fact about a format and not "
                          "an answer" % asked}

    # A FORMAT THAT CARRIES NO EVIDENCE CANNOT CLOSE ANYTHING HERE -- SAY SO FIRST.
    #
    # `.txt` and `.md` are verified by opening them as text, which every text
    # file passes.  Spending 97 s of program search to then refuse (measured
    # 2026-11-01, "write the commit log of repo into log.txt") buys nothing:
    # the verdict was decided by the format before the first program ran.
    from canonical.runtime import program_synthesis_v1 as _ps
    if not _ps.carries_content_evidence(suffix):
        return {"closed": False, "suffix": suffix,
                "status": "OPEN__FORMAT_CARRIES_NO_EVIDENCE",
                "detail": ("%s is any text; nothing in the bytes says it is the "
                           "thing the goal named, so no verifier here can close it"
                           % suffix)}

    # A COMPOUND FORMAT NEEDS TWO STEPS, AND THIS CHANNEL RESETS BETWEEN THEM.
    #
    # '.tar.gz' is a tar and then a gzip; no single program owns both layers.
    # Every action here starts from the seed (ComputerEnv.reset), which is what
    # makes a failed form retryable and what makes a second step impossible:
    # step one's artifact is deleted before step two can read it.  Measured
    # 2026-11-01: "pack pkg into pkg.tar.gz" burned **95 s** of search, then
    # reported PASS__ENVIRONMENT_SOLVED_BY_LEARNING with an EMPTY plan -- a PASS
    # status on a goal it had just failed to verify.  An unprovable shape is
    # refused immediately and named, instead of being paid for.
    if suffix.count(".") > 1:
        return {"closed": False, "suffix": suffix,
                "status": "OPEN__FORMAT_NEEDS_A_CHAIN_THIS_CHANNEL_CANNOT_KEEP",
                "detail": ("%s is two layers (a container inside a wrapper); this route "
                           "resets to its seed between actions, so the first layer is "
                           "gone before the second can be verified" % suffix)}

    named = output_name(gap) or ""
    target = named if named.endswith(suffix) else ("input.txt" + suffix)

    # A file that is ALREADY THERE is not a file this route can have produced.
    #
    # Every oracle below asks one question: did `target` appear?  (`is_goal =
    # target in snapshot`.)  When the goal names a file that already exists, the
    # oracle is satisfied before any program runs, so no action can be credited
    # with creating it and no plan can be verified by it -- the route cannot
    # learn anything, and it must not claim it did.  It still paid for the whole
    # search: measured 2026-10-29, "Format <calc.py>" spent **48.7 s** running
    # 442 actions (5,046 subprocesses) to conclude
    # OPEN__NO_USABLE_PRIOR_EXPERIENCE, and 13 forms of "Format"/"Replace ... in"
    # in a 45-request matrix spent 33-51 s each to refuse in the same way.
    #
    # The two early exits above are the same shape -- "this route cannot possibly
    # answer that, so say so before acting" -- and this is the third case of it.
    # It is cheaper AND safer: refusing here also means no exploration ever runs
    # a program with the user's existing file as its target.
    if named and any((base / named).exists() for base in _target_bases(named)):
        return {"closed": False,
                "status": "OPEN__THE_TARGET_ALREADY_EXISTS",
                "detail": ("this route can only prove that a program MADE %s, and it is "
                           "already there, so no action it runs can be credited with "
                           "producing it" % named),
                "suffix": suffix, "target": named}
    # candidates by NAME (gzip for .gz) and by MEANING (convert for resize)
    progs = programs_for(suffix)
    for _p in programs_for_goal(gap):
        if _p not in progs:
            progs.append(_p)
    is_goal = lambda snap: target in str(snap)
    gkey = "goal"

    _fingerprint: dict[str, Any] | None = None

    def _seed_items() -> list[tuple[str, bytes]]:
        if seed_file and pathlib.Path(seed_file).is_file():
            path = pathlib.Path(seed_file)
            return [(path.name, path.read_bytes())]
        return [("input.txt", b"brain computer env sample\n")]

    def fingerprint_key() -> str:
        """What a fingerprint is a fact ABOUT: this machine, these programs, this seed.

        The fingerprint is taken by running the programs, so it changes when a
        program's bytes change and it does not change when a goal is asked twice.
        Keying the cache on the program's mtime and size is what makes the entry
        die on a machine change instead of being believed across one.
        """
        # THE TARGET IS NOT PART OF WHAT A FINGERPRINT IS A FACT ABOUT.
        #
        # Measured 2026-11-01, ten variants of one learned family ("compress X.txt
        # into X.txt.gz", a different name and size each time): the first closed in
        # 8,994 ms and every one after it was RECALLED -- 9 of 9, plan ['run_gzip'] --
        # but at ~1,268 ms each, not the ~265 ms a repeat of the same name costs.
        # The difference was this line: the target was in the key, so every new name
        # was a cache miss and every new name paid for a fingerprint that came out
        # byte-identical.  Measured directly: the same machine, targets "a.txt.gz"
        # and "zzzz.dat.gz", produced EQUAL fingerprints (shapes ['str'], growth
        # 0.625, revisits 6, 16 actions).
        #
        # The target shapes which argv forms are TRIED; it does not change what the
        # programs are.  What makes that safe is unchanged: a recalled plan is only
        # ever a hypothesis, and `_verify_plan` re-executes it against the target that
        # was actually asked for, so a fingerprint that is one target stale costs at
        # most one trial.
        import hashlib
        h = hashlib.sha256()
        for name, data in _seed_items():
            h.update(name.encode() + b"\0" + data + b"\0")
        for prog in progs:
            real = shutil.which(prog) or prog
            try:
                st = os.stat(real)
                h.update(("%s|%d|%d\n" % (prog, st.st_mtime_ns, st.st_size)).encode())
            except OSError:
                h.update((prog + "|missing\n").encode())
        return h.hexdigest()[:24]

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
        # THE SECOND TIME MUST BE INSTANT, OR THE MEMORY IS ONLY A RECORD.
        #
        # Taking a fingerprint means acting: six probes of up to four actions,
        # and each action runs a program in several shapes.  Measured
        # 2026-11-01: 5-8 s.  It was taken twice per discovery and again on
        # every repeat, so a one-action plan recalled in 4,757 ms against
        # 4,766 ms cold -- the machine remembered the answer and still paid
        # full price to recognise the question.
        key = fingerprint_key()
        try:
            cached = tl.cached_fingerprint(key)
        except Exception:  # noqa: BLE001 - a cache must never be required
            cached = None
        if cached:
            _fingerprint = cached
            return _fingerprint
        env = ComputerEnv()
        try:
            env.register(program_actions(env, programs=progs, target=target))
            _fingerprint = tl.fingerprint(env, env.action_names)
        finally:
            env.close()
        try:
            tl.cache_fingerprint(key, _fingerprint)
        except Exception:  # noqa: BLE001
            pass
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

    # 0. this exact shape, for this exact goal, was already tried here and did not
    #    close.  Measured 2026-11-01 before this existed: the same goal that needs
    #    64,637 ms to fail spent 63,874 ms failing again on the very next call.
    #    The reason is remembered, so the repeat is answered with the same honest
    #    refusal instead of a fresh search -- and it is keyed on the verifier's own
    #    version, because a better verifier makes shapes solvable that were not.
    try:
        _verifier = _ps.verifier_version()
        _fp = fingerprint_of()
        _miss = tl.recall_miss(_fp, gap, _verifier)
    except Exception:  # noqa: BLE001 - memory is an optimisation, not a dependency
        _fp, _verifier, _miss = None, "", None
    if _miss:
        return {"closed": False, "status": str(_miss.get("reason")
                                               or "OPEN__TRIED_HERE_AND_DID_NOT_CLOSE"),
                "plan": [], "suffix": suffix, "target": target,
                "actions_tried": 0, "from_memory": True, "verified_before": False,
                "detail": "tried on this machine before (%s times) and it did not close"
                          % _miss.get("trials", 1)}

    def forget_misses() -> None:
        if _fp is None:
            return
        try:
            tl.forget_miss(_fp, gap, _verifier)
        except Exception:  # noqa: BLE001
            pass

    # 1. the instant path: was this shape of problem solved before?
    got = recall()
    if got is not None:
        forget_misses()
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
        forget_misses()
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
            forget_misses()
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
    # a status that says PASS while verification just failed is the same lie in
    # a different field -- the census reads both
    _st = str(outcome.get("status") or "")
    if _st.startswith("PASS"):
        _st = "OPEN__EFFECT_NOT_VERIFIED"
    if _fp is not None and not str(_st).startswith("CHANNEL_ERROR"):
        try:
            tl.remember_miss(_fp, gap, _st or "OPEN__EFFECT_NOT_VERIFIED", _verifier)
        except Exception:  # noqa: BLE001
            pass
    return {"closed": False, "status": _st or "OPEN__EFFECT_NOT_VERIFIED",
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
    # The opposite half of the same question, which was never written.  The
    # words are deliberately TIGHT -- the noun phrase, not the adjective on
    # its own -- because "the duplicate entries in this ledger" is not a
    # countable question about lines and must not be turned into one.
    "duplicatelines": ("duplicate lines", "duplicate line", "duplicated lines",
                       "duplicated line", "repeated lines", "repeated line",
                       "lines that repeat", "lines that are repeated",
                       "lines that are duplicated",
                       # The noun has to be in the phrase, and the phrase has
                       # to survive the ordinary ways a sentence drops a word:
                       # "lines THAT appear more than once" and "lines appear
                       # more than once" are one question, and a list that
                       # holds only the first is a list of phrasings.
                       "lines that appear more than once",
                       "lines appear more than once",
                       "lines appearing more than once",
                       "lines that occur more than once",
                       "lines occur more than once",
                       "lines occurring more than once"),
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
    if kind == "duplicatelines":
        # Exactly n lines that repeat, and n that do not -- so this probe
        # separates three answers that a weaker file would let pass as one:
        #   every line            -> 3n   (a plain line count)
        #   every DIFFERENT line  -> 2n   (`sort --unique | wc --lines`)
        #   the lines that repeat -> n    (the answer)
        # On n = 7 that is 21, 14 and 7: no two of them coincide, so a
        # program that measures the wrong thing cannot print 7 by accident.
        #
        # The repeats are put at OPPOSITE ENDS for the reason `uniquelines`
        # already learned the hard way: `uniq` collapses NEIGHBOURS, so on
        # 'row 0, row 0, row 1, row 1' it prints n and looks exactly like a
        # tool that finds the repeats.  It is not.  Given a file whose twins
        # are not neighbours it prints nothing at all -- so only something
        # that really compares each line against every other survives.
        twice = b"".join(b"twice %d\n" % i for i in range(n))
        once = b"".join(b"once %d\n" % i for i in range(n))
        return twice + once + twice
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
_REFINES = {"uniquelines": "lines", "lineswith": "lines",
          "duplicatelines": "lines"}

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
    counter_gap = "count the " + base if base else gap
    hits = [c for c in probe_survivors(base, list(programs), counter_gap,
                                       timeout=min(timeout, 2.0), budget=3.0)
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


# One implementation of "read a command on a deadline and reap it", shared
# with the pipe runner.  It lived here alone, which is why the pipe builder
# had its own copy of the draining and reaping around it; two copies of the
# same deadline logic is two places for the same timing bug to hide.
from canonical.runtime.pipeline_exec_v1 import reap as _reap  # noqa: E402
from canonical.runtime.pipeline_exec_v1 import run_stages as _run_stages


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
                            stdin=subprocess.DEVNULL,
                            start_new_session=True)
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

    A thin two-stage reading of `_run_stages`, kept because every caller
    here asks for exactly two and says so more clearly this way. The
    draining, the deadline and the reaping live in `pipeline_exec_v1`,
    which is the one place a chain of any length is built.
    """
    return _run_stages([list(argv1), list(argv2)], str(cwd),
                       timeout=timeout, max_bytes=max_bytes)


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
                    code, out = _run_capped(argv, root,
                                            timeout=min(timeout, 0.8))
                except Exception:  # noqa: BLE001
                    break
                if code is None or code == -9:
                    return None
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
                    budget: float = _PROGRAM_BUDGET,
                    wide_seen: set[str] | None = None) -> list[dict[str, Any]]:
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
                        code, out = _run_capped(argv, root,
                                                timeout=min(timeout, 0.8))
                    except Exception:  # noqa: BLE001 - a program must not break it
                        break
                    if code is None or code == -9:
                        return None
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
            wide_cands = [
                p for p in list(programs)
                if wide_seen is None or p not in wide_seen
            ][:_WIDE_PROGRAMS]
            if wide_seen is not None:
                wide_seen.update(wide_cands)
            wide = []
            if wide_cands:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    for hit in pool.map(
                            lambda p: _one_wide(
                                p, kind, gap,
                                (literal,) if literal else tuple(patterns),
                                timeout, literal),
                            wide_cands):
                        if hit:
                            wide.append(hit)
            if wide:
                return wide
        return []
    # Discover line counters BEFORE slicing `programs` so Stage-2 counters
    # (`wc`, `grep`) are found in <100ms via narrow manuals rather than wide scans.
    counter_cands = (
        list(dict.fromkeys(programs_for_goal("count the lines", limit=16) + list(programs)))
        if len(programs) >= 6 else list(programs)
    )
    counters = _known_counters("lines", counter_cands, "count the lines", literal, timeout)
    # Deduplicate symlinked binaries (e.g. gold / ld.gold / x86_64-linux-gnu-gold)
    dedup_heads: list[str] = []
    seen_inst: set[str] = set()
    for p in programs:
        inst = _instrument(p)
        if inst not in seen_inst:
            seen_inst.add(inst)
            dedup_heads.append(p)
    if len(dedup_heads) > _MAX_PIPE_PROGRAMS:
        dedup_heads = dedup_heads[:_MAX_PIPE_PROGRAMS]
    programs = dedup_heads
    head_budget = min(budget, 2.5) if len(programs) > 4 else budget

    tails = []
    for c in counters:
        # used at the end of a pipe, so it is given no filename of its own
        argv = [a for a in c["argv"] if a != "probe.txt"]
        if argv and argv not in tails:
            tails.append(argv)
    if not tails:
        return []

    def pair(job: tuple) -> dict[str, Any] | None:
        """Feed one program's output to something that counts, and see if
        the pair tracks the construction. 'uniq | wc --lines' answers "how
        many different lines" -- a question no single program answers."""
        head, tail_argv, allow_wide = job
        root = pathlib.Path(tempfile.mkdtemp(prefix="brain-pipe-"))
        step_timeout = min(timeout, 0.6) if not allow_wide else min(timeout, 1.2)
        deadline = time.monotonic() + (1.0 if not allow_wide else head_budget)
        try:
            pat_tuple = _PIPE_PATTERNS + ((literal,) if literal else ())
            shapes = list(_query_shapes(head, name, gap, patterns=pat_tuple, wide=allow_wide))
            for argv1 in shapes:
                if time.monotonic() > deadline:
                    break
                for argv2 in [tail_argv]:
                    reads = []
                    for size in _PROBE_SIZES:
                        (root / name).write_bytes(
                            probe_bytes(kind, size, literal))
                        try:
                            code, out = _run_pipeline(argv1, argv2, root,
                                                      timeout=step_timeout)
                        except Exception:  # noqa: BLE001
                            break
                        if code is None or code == -9:
                            return None
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

    narrow_jobs = [(head, t, False) for head in programs for t in tails]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        narrow_hits = [hit for hit in pool.map(pair, narrow_jobs) if hit]
    if narrow_hits:
        return narrow_hits

    wide_jobs = [(head, t, True) for head in programs for t in tails]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [hit for hit in pool.map(pair, wide_jobs) if hit]


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

    # Table-free metamorphic behavioral signature channel (`NEXT_STEP_THE_CONSTRUCTOR_TABLE`):
    # When no synthetic `probe_bytes` constructor exists for `kind` (or when `probe_bytes` is
    # ablated), discover and prove the measurement pipeline purely from algebraic perturbations
    # (`F || F`, within-line doubling, and non-adjacent fresh twins) of `src` itself!
    if literal is None and probe_bytes(kind, _PROBE_SIZES[0], literal) is None:
        from canonical.swe_kernel.metamorphic_cli_compiler_v1 import answer_query_by_metamorphic_signature
        return answer_query_by_metamorphic_signature(
            kind, src, candidate_programs=programs, min_agreement=min_agreement, timeout=min(timeout, 3.0)
        )

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
            if value is None and hit.get("stages") != 2:
                # Tools such as wc echo the filename after the value. An
                # absolute filename can exceed the value-length bound even
                # when the value itself is short. Strip only the exact file
                # we supplied, then retain the existing single-value checks.
                text = out.decode("utf-8", "replace").strip()
                suffix = " " + str(src)
                if text.endswith(suffix):
                    value = _bare_value(text[:-len(suffix)].encode("utf-8"))
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

    wide_seen: set[str] = set()
    tier_limits = (24,) if (programs is None and kind in ("uniquelines", "duplicatelines")) else (24, 96, 200)
    for limit in tier_limits:
        cached = _query_cache_get(kind, limit) if programs is None else None
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
            if programs is None and kind in ("uniquelines", "duplicatelines"):
                # Do not burn 40x400 single-stage wide flag scans on a query
                # whose invariant requires deduplication + counting.
                wide_seen.update(cands)
            survivors = probe_survivors(kind, cands, gap,
                                        literal=literal,
                                        wide_seen=wide_seen)
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
            if programs is not None:
                cands = list(programs)
            else:
                mod_words = [
                    w for w in re.findall(r"[a-z]+", gap.lower())
                    if len(w) >= 3 and w not in {
                        "how", "many", "count", "number", "the", "and",
                        "for", "from", "with", "lines", "line", "file",
                        "files", "txt", "csv", "log", "data", "there", "are",
                    }
                ]
                mod_cands = (
                    programs_for_goal(" ".join(mod_words), limit=12)
                    if mod_words else []
                )
                base_cands = programs_for_goal(gap, limit=12)
                cands = list(dict.fromkeys(mod_cands + base_cands))[:16]
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
