"""THE MACHINE IS THE DEFINITION — index cheaply, confirm by execution, and let the run convict the index.

ROUND 6. Round 5 ended with a conviction, not a claim: a typography parser cannot decide what a
program's commands are (five rooms of seven disagreed with the program's own live answer), because
separating `-b   : issue warnings about str(bytes_instance)` from `.break   Sometimes you get stuck`
is a fact about English typography, and a fact about typography is not computing.

So the parser is demoted to what it can honestly be — an INDEX, cheap and inclusive — and the
DEFINITION moves to the only authority that cannot be argued with: the program, run.

    INDEX      the program's own answers, parsed loosely. May be noisy. Costs milliseconds.
    DEFINE     execute each candidate, beside a control of the same shape, in a throwaway room,
               and keep it only if the machine treats it differently from a meaningless token.
    ENUMERATE  if a confirmed token makes the program print MORE tokens, that output becomes a
               new index and the loop runs once more. The program is asked to enumerate itself.

THE CLASSIFIER IS A DIFFERENTIAL, AND THAT IS THE WHOLE IDEA. A token is DEFINED when the run it
produces cannot be produced by a meaningless token of the same shape. The control is not optional:
without it, `sh -c help` answering `help: not found` looks like a definition, and a round-3
instrument read exactly that as "the shell has no command table" while the shell's 46-line table
sat one invocation away. With it, both runs normalise to `X: not found` and the token is NOT defined.

FOUR OUTCOMES, and every one of them is a measurement rather than a judgement:

    MOVES_STATE    the room's files changed                (a definition with a visible effect)
    DEFINED        the run differs from every control       (the program knows this word)
    NOT_DEFINED    the run is identical to a control class  (the program does not know it, or it is
                                                            not this room's way of asking)
    BLIND          the controls disagree with each other    (the instrument cannot see here, and it
                                                            says so instead of guessing)

WHAT IS MEASURED
  * INDEX PRECISION: of the candidates the parser offered, how many does the machine confirm?
  * the cost of confirmation in milliseconds and in questions;
  * whether execution rescues the two rooms round 5 lost outright (`node`, `bash`) and the one it
    got wrong (`less`), by trying the second way of asking (a keystroke at the prompt) as well;
  * UNSEEN ROOMS: programs no round of this project has ever touched, taken from PATH by a rule
    stated in the receipt, run through the same pipeline with zero prior knowledge.

WHAT IT IS NOT ALLOWED TO CLAIM
  * no benchmark score (OSWorld 2.1, Terminal-Bench 4.0, SWE-bench Pro V2 cannot execute here);
  * a confirmed token is a fact about THIS program in THIS room; the generalisation that survives
    a program change is the PROBE PLAN, not the word;
  * network-capable and interactive full-screen programs are excluded by a stated rule, and the
    exclusion is printed rather than quietly applied.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_THE_MACHINE_IS_THE_DEFINITION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"
GEOMETRY = "TERM=dumb;24x80;stdin=/dev/null;cwd=throwaway-room"
STORE = REPO / "canonical" / "astra_runtime" / "state" / "MACHINE_DEFINITION_MEMORY_V1.json"
STORE_SCHEMA = "PROJECT_BRAIN_MACHINE_DEFINITION_MEMORY_V1"

PROBE_TIMEOUT = 3.0
PROBE_CAP = 60_000
PROMPT_PROBES_PER_ROOM = 12

#: Programs a probe must never run: they talk to the network, take the whole screen, or rewrite
#: the machine. This is an EXCLUSION LIST BY RULE, printed in the receipt, not a preference.
DENY = frozenset({"curl", "wget", "ssh", "scp", "sftp", "telnet", "nc", "ncat", "socat", "ftp",
                  "vi", "vim", "nvim", "nano", "emacs", "ed", "less", "more", "man", "top", "htop",
                  "docker", "podman", "sudo", "su", "systemctl", "mount", "umount", "dd",
                  "mkfs", "fdisk", "parted", "shutdown", "reboot", "init", "apt", "apt-get",
                  "pip", "pip3", "npm", "yarn", "gem", "cargo", "go", "gcc", "cc", "python3",
                  "node", "bash", "sh", "pdb"})


# --------------------------------------------------------------------------------------- #
# 1. THE ROOM: a throwaway directory with a known state, digested before and after.
# --------------------------------------------------------------------------------------- #
def fresh_room() -> pathlib.Path:
    """A throwaway directory whose files the probe CANNOT read back.

    THE ROOM MUST NOT LEAK INTO THE OBSERVATION. A probe run in the pager's room answers
    `alpha.txt: No such file or directory` when told to open `alpha.txt`, because the pager opens
    the file as its DOCUMENT and the harness sealed permissions so it could not. The observed text
    then contains the room, and the differential compares rooms instead of programs. The room is
    therefore sealed DIRECTORY-ONLY (a file a process can open is a file it can read), so any
    probe that names one of its files gets a uniform, informative refusal.
    """
    room = pathlib.Path(tempfile.mkdtemp(prefix="machine-def-room-"))
    # the DOCUMENT: a real, readable file, because a pager or a debugger needs something to open
    (room / "alpha.txt").write_text("alpha\nbeta\ngamma\n")
    (room / "delta.txt").write_text("delta\n")
    # the ARCHIVE: a directory sealed to execute-only, because a file a process can open is a file
    # it can read back into the observation. Any probe that names a file inside it gets a uniform,
    # informative refusal instead of a leak.
    vault = room / "vault"
    vault.mkdir()
    (vault / "secret.txt").write_text("secret\n")
    vault.chmod(0o111)
    return room


def clone_room(room: pathlib.Path) -> pathlib.Path:
    """Every probe gets its own copy, so a destructive token cannot poison the next measurement."""
    target = pathlib.Path(tempfile.mkdtemp(prefix="machine-def-trial-"))
    for path in room.rglob("*"):
        rel = path.relative_to(room)
        if path.is_dir():
            (target / rel).mkdir(parents=True, exist_ok=True)
        else:
            (target / rel).write_bytes(path.read_bytes())
    return target


def digest(room: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(room.rglob("*")):
        rel = str(path.relative_to(room))
        if path.is_dir():
            out[rel + "/"] = "dir"
        elif path.is_file():
            try:
                out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            except OSError:
                out[rel] = "unreadable"
    return out


def delta(before: Mapping[str, str], after: Mapping[str, str]) -> frozenset[str]:
    changed: set[str] = set()
    for key in set(before) | set(after):
        if before.get(key) != after.get(key):
            changed.add(key)
    return frozenset(changed)


# --------------------------------------------------------------------------------------- #
# 2. THE PROBE: one run, bounded, confined, and reproducible.
# --------------------------------------------------------------------------------------- #
def run_argv(room: pathlib.Path, argv: Sequence[str]) -> dict[str, Any]:
    try:
        done = subprocess.run(list(argv), cwd=str(room), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=PROBE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"exit": "TIMEOUT", "out": "", "err": "", "ms": PROBE_TIMEOUT * 1000}
    except OSError as exc:
        return {"exit": "OSERROR", "out": "", "err": str(exc)[:200], "ms": 0.0}
    return {"exit": done.returncode,
            "out": done.stdout.decode("utf-8", "replace")[:PROBE_CAP],
            "err": done.stderr.decode("utf-8", "replace")[:PROBE_CAP],
            "ms": 0.0}


def run_prompt(room: pathlib.Path, argv: Sequence[str], stroke: str,
               payload: str = "") -> dict[str, Any]:
    """A real terminal, the stroke typed at it, and the payload one step later.

    This is the second WAY OF ASKING, and round 5 proved it is not optional: a pager's commands
    are keystrokes, and `less s` on a command line is a request to open a file called `s`.
    """
    import pty
    import select
    import signal

    started = time.perf_counter()
    env = {**os.environ, "TERM": "dumb", "LINES": "24", "COLUMNS": "80", "PAGER": "cat"}
    env.pop("PYTHONSTARTUP", None)
    pid, fd = pty.fork()
    if pid == 0:                                                    # pragma: no cover - child
        try:
            os.chdir(str(room))
            os.execvpe(argv[0], list(argv), env)
        except OSError:
            os._exit(127)
    out: list[bytes] = []

    def drain(limit: float) -> None:
        deadline = time.time() + limit
        while time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.02)
            if not ready:
                continue
            try:
                block = os.read(fd, 65536)
            except OSError:
                return
            if not block:
                return
            out.append(block)
            deadline = time.time() + 0.35

    try:
        drain(1.2)
        for stroke_ in ([stroke] if stroke else []) + ([payload] if payload else []):
            try:
                os.write(fd, stroke_.encode())
            except OSError:
                break
            drain(1.6)
        drain(0.4)
    finally:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        try:
            os.waitpid(pid, 0)
        except (ChildProcessError, OSError):
            pass
        try:
            os.close(fd)
        except OSError:
            pass
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", b"".join(out).decode("utf-8", "replace"))
    return {"exit": "PTY", "out": text[:PROBE_CAP], "err": "", "ms": (time.perf_counter() - started) * 1000}


#: Numerals and paths are the room's, not the program's: two runs that differ only in those are
#: the same run. Everything else is kept, including punctuation, because punctuation is where the
#: refusals differ (`invalid option` and `command not found` must not merge).
_NUM = re.compile(r"\b\d+\b")
_PATHISH = re.compile(r"(?:/[\w.+-]+)+|\.\.?/[\w./+-]*")


def signature(run: Mapping[str, Any], token: str, room: pathlib.Path,
              before: Mapping[str, str]) -> tuple[str, ...]:
    """What this run WAS, with the token and the room normalised out of it.

    THE TOKEN IS REPLACED BY A PLACEHOLDER, and that is the single most important line in the
    file: `sh: 1: help: not found` and `sh: 1: zzq: not found` are the SAME observation, and a
    classifier that could not see that would call every string a definition.
    """
    text = f"{run.get('out', '')}\n{run.get('err', '')}"
    # THE TOKEN IS NOT SUBSTITUTED. The earlier version replaced the token inside the output, and
    # the one-character candidates (`e`, `y`, `h`) were then substituted INSIDE EVERY WORD:
    # `alpha` became `alp<T>a`. The room's leak is handled by the room (`<ROOM>` and the sealed
    # directory), and a token standing alone in a refusal is exactly the evidence we want to keep.
    text = text.replace(str(room), "<ROOM>")
    text = re.sub(r"(?<![\w])" + re.escape(token) + r"(?![\w])", "<T>", text) if token else text
    text = _PATHISH.sub("<P>", text)
    text = _NUM.sub("<N>", text)
    lines = tuple(sorted({line.strip() for line in text.split("\n") if line.strip()}))
    changed = delta(before, digest(room))
    # THREE LINES, NOT SIX: two runs that share a usage line, a version line and an error share an
    # outcome, and comparing more made every room BLIND.
    return (str(run.get("exit")), lines[:3], changed)


def control_tokens(token: str, how_many: int = 3) -> list[str]:
    """Meaningless tokens OF THE SAME SHAPE as the candidate, derived from its own bytes.

    Shape matters: a control that does not look like the candidate tests the wrong thing. A
    dash-led candidate gets a dash-led control, a dotted one a dotted one, a bare word a bare
    nonsense word -- and the letters come from a hash of the candidate so two runs agree.
    """
    seed = hashlib.sha256(token.encode()).hexdigest()
    alphabet = "qzxjvkw"
    out: list[str] = []
    for i in range(how_many):
        body = "".join(alphabet[int(seed[j + 2 * i], 16) % len(alphabet)]
                       for j in range(len(token)))
        if token.startswith("--"):
            out.append("--" + body.lstrip("-"))
        elif token.startswith("-"):
            out.append("-" + body.lstrip("-")[:2])
        elif token.startswith("."):
            out.append("." + body.lstrip("."))
        else:
            out.append(body)
    return out


def classify(room: pathlib.Path, program: str, token: str, way: str, base: str,
             payload: str = "", extra: Sequence[str] = ()) -> dict[str, Any]:
    """MOVES_STATE | DEFINED | NOT_DEFINED | BLIND, decided by comparison and nothing else."""
    def one(candidate: str) -> dict[str, Any]:
        trial = clone_room(room)
        before = digest(trial)
        if way == "argv":
            run = run_argv(trial, [program, candidate, base, *extra])
        else:
            run = run_prompt(trial, [program, base, *extra], candidate + "\n",
                             (payload + "\n") if payload else "")
        return {"run": run, "sig": signature(run, candidate, trial, before),
                "changed": sorted(delta(before, digest(trial))), "ms": run.get("ms", 0.0)}

    real = one(token)
    if way == "prompt":
        # FIRST-SCREEN CONTROLS. A pager repaints a whole screen at every write (the WARNING, then
        # the commands, then the `:` prompt), so two identical runs of the same stroke differ and
        # every candidate came back BLIND. The screen BEFORE any stroke is the baseline; only what
        # differs from it can be attributed to the stroke.
        screen0 = run_prompt(clone_room(room), [program, base], "", "")
        real_lines = tuple(real["sig"][1])
        baseline: set[str] = set()
        for line in str(screen0.get("out", "")).split("\n"):
            if line.strip():
                baseline.add(line.strip())
        real["sig"] = (real["sig"][0],
                       tuple(line for line in real_lines if line not in baseline)[:3],
                       real["sig"][2])
        # A TERMINAL SCREEN IS NOT A PURE FUNCTION OF THE PROGRAM. Cursor placement, timing and
        # the pager's own repainting make two identical runs differ, and a differential over
        # irreproducible output confirms everything -- measured: `one`, `CR` and `*` (the index's
        # own junk tokens) came back DEFINED at the pager's prompt. A prompt candidate must
        # therefore REPRODUCE before it may be compared at all.
        again = one(token)
        if tuple(again["sig"][:2]) != tuple(real["sig"][:2]):
            return {"token": token, "way": way, "verdict": "BLIND", "changed": real["changed"],
                    "exit": real["sig"][0], "ms": real["ms"] + again["ms"], "probes": 2,
                    "controls_agree": True,
                    "evidence": ["the same stroke produced a different screen twice"]}
    controls = [one(control) for control in control_tokens(token)]
    control_sigs = {tuple(c["sig"][:2]) for c in controls}
    # BLIND IS NOT "MY CONTROLS DISAGREED": controls of the same shape legitimately draw different
    # refusals (`--zz` is unknown option, `--qx` needs an argument), and treating that as blindness
    # made ten of the pager's twelve candidates unobservable. Blind is when the instrument cannot
    # tell the candidate from its controls AT ALL -- i.e. the candidate looks like a control AND
    # the controls are not unanimous. Otherwise the weakest control is the one that matters.
    if len(control_sigs) > 1 and tuple(real["sig"][:2]) in control_sigs:
        verdict = "BLIND"
    elif real["changed"]:
        verdict = "MOVES_STATE"
    elif tuple(real["sig"][:2]) not in control_sigs:
        verdict = "DEFINED"
    else:
        verdict = "NOT_DEFINED"
    return {"token": token, "way": way, "verdict": verdict,
            "changed": real["changed"], "exit": real["sig"][0],
            "ms": round(sum(c["ms"] for c in controls) + real["ms"], 1),
            "probes": 1 + len(controls),
            "controls_agree": len(control_sigs) == 1,
            "evidence": [line for line in real["sig"][1]][:3]}


# --------------------------------------------------------------------------------------- #
# 3. THE INDEX: round 5's parser, demoted to a candidate generator, imported not rewritten.
# --------------------------------------------------------------------------------------- #
def index_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "guide_is_a_key_table", REPO / "canonical" / "tools" / "the_guide_is_a_key_table_v1.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


#: THE THREE UNIVERSAL FORMS. They are conventions of command-line programs, not facts about any
#: one program, and they are only an INDEX: the machine decides what is real.
UNIVERSAL_FORMS = (("--help",), ("-h",), ("help",))

#: THE FOURTH FORM IS LEARNED FROM THE PROGRAM'S OWN PAGE, NOT FROM A TABLE. A page that documents
#: a run-a-command switch (`-c command`, `-e script`, `-c CMD`) is telling us it can be asked a
#: question in its own language -- and that is exactly where a shell keeps its 62 builtins, which
#: three universal forms cannot reach: measured, `bash --help` is 91 words of options and
#: `bash help` is `command not found`, so the index saw ONE token where the program has 62.
#: THE FORM THE ENVIRONMENT TEACHES WITH. Before any index is parsed, the environment is allowed
#: to name its own way of asking, and a shell does exactly that on its page: `Type \`bash -c help'
#: for more information about shell builtin commands`. That sentence is the program's own
#: instruction and the index is built from it, not from a list I keep.
_SELF_TEACHING = re.compile(r"(?im)type\s+[`'\"]([^`'\"]{1,60})[`'\"][^\n]{0,80}")
_TAUGHT_FORM = re.compile(r"(?:^|\s)(-[A-Za-z])\s+(help|[a-z_]{2,20})\b")

#: The page states the switch in its own words. `python3 --help` prints `-c cmd`; `bash --help`
#: prints `Type \`bash -c help' for more information about shell builtin commands.` Both are the
#: page naming a way to ask a question, and the wider pattern reads either spelling.
_RUN_A_COMMAND = re.compile(
    r"(?im)^\s*(-[ce])\s+([a-z][a-z ]{1,20})|\S+\s+(-[ce])\s+([a-z][a-z_]{1,20})\b")


def taught_forms(page: str) -> list[dict[str, Any]]:
    """Every way of asking the environment TEACHES about itself, in the order it teaches them.

    A form is a claim and it is checked by running it, so this function proposes and does not
    decide: the first sentence on a shell's page quotes a nested `"help set"` and yields no form,
    the second yields `-c help`, and only that one answers with 411 words.
    """
    out: list[dict[str, Any]] = []
    for sentence in _SELF_TEACHING.finditer(page or ""):
        taught = _TAUGHT_FORM.search(sentence.group(1))
        if taught and [taught.group(1), taught.group(2)] not in [f["form"] for f in out]:
            out.append({"form": [taught.group(1), taught.group(2)],
                        "switch": taught.group(1),
                        "taught_by": sentence.group(0).strip()[:100]})
    return out


def learn_a_form(program: str) -> dict[str, Any]:
    page = one_shot_plain([program, "--help"])
    # (1) the instruction the environment prints about itself comes first
    for taught in taught_forms(page):
        text = one_shot_plain([program, *taught["form"]])
        if len(text.split()) >= 5:
            return {**taught, "documented_as": taught["taught_by"],
                    "words": len(text.split()),
                    "sample": (text.split("\n")[0] if text else "")[:80]}
    # (2) otherwise the page's own switch table
    found = _RUN_A_COMMAND.search(page or "")
    if not found:
        return {"form": None, "why": "the page documents no run-a-command switch"}
    switch = found.group(1) or found.group(3)
    text = one_shot_plain([program, switch, "help"])
    return {"form": [switch, "help"], "switch": switch,
            "documented_as": found.group(0).strip()[:90],
            "words": len(text.split()), "sample": text.split("\n")[0][:80] if text else ""}


def candidates(program: str, runner: Any = None) -> dict[str, Any]:
    """Every token the program's own answers list, loosely parsed. Cheap, and allowed to be wrong.

    The first version of this function called round 5's per-program channel table and swallowed
    the resulting KeyError for any program that table did not name -- so four UNSEEN rooms came
    back with an index of zero tokens and were reported as having nothing to define, which was a
    bug wearing a result's clothes. The index is now built from three universal forms and nothing
    else, so a program this project has never seen is indexed exactly as well as one it has.
    """
    answers: list[str] = []
    for form in UNIVERSAL_FORMS:
        text = (runner or one_shot_plain)([program, *form])
        if text and len(text.split()) >= 5:
            answers.append(text)
    tokens: list[str] = []
    for text in answers:
        for row in table_rows_loose(text):
            for token in row["tokens"]:
                if token not in tokens:
                    tokens.append(token)
    return {"tokens": tokens, "answers_read": len(answers),
            "raw_words": sum(len(t.split()) for t in answers)}


def one_shot_plain(argv: Sequence[str]) -> str:
    import subprocess
    try:
        done = subprocess.run(list(argv), capture_output=True, timeout=PROBE_TIMEOUT,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout + done.stderr).decode("utf-8", "replace")[:PROBE_CAP]


_JSONISH = re.compile(r'^\s*[{}\[\]]|"\w+"\s*:')


def table_rows_loose(text: str) -> list[dict[str, Any]]:
    """An answer that is a DATA STRUCTURE is read as one; the typography rule is for prose pages.

    `corepack --help` is a JSON help tree. Parsing it with a column rule gave zero tokens and the
    room was reported as having nothing to define, which is an instrument failure dressed as a
    fact about the program. The structure is the index: quoted keys at the top level.
    """
    # A DATA STRUCTURE ANNOUNCES ITSELF AT THE TOP: its first non-space character is a brace.
    # Counting bracket-led LINES instead mistook `pygmentize`'s usage page (which has several
    # lines opening with `[-O OPTION=...`) for JSON and threw its eleven-token index away.
    if text.lstrip()[:1] in ("{", "["):
        keys = re.findall(r'^\s{0,8}"([\w.-]{2,40})"\s*:', text, re.M)
        return [{"tokens": [k], "desc": "", "options_only": False} for k in dict.fromkeys(keys)]
    return table_rows_loose_typography(text)


def command_trees(text: str, program: str) -> list[str]:
    """Indented command trees: `  corepack cache clean` and `  corepack enable [--x] ...`.

    A program that prints its commands one per line under headings is a COMMAND TREE, and its
    tokens are the whole path (`cache clean`), not the first word -- the first word is the
    program's own name, and reading it as a command would define `corepack` inside `corepack`.
    """
    out: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith(program + " ") or len(stripped) > 90:
            continue
        body = stripped[len(program) + 1:].split(" [")[0].split(" ...")[0].strip()
        if body and body not in out and not body.startswith("-"):
            out.append(body)
    return out


def table_rows_loose_typography(text: str) -> list[dict[str, Any]]:
    """The typography rule, once, imported from round 5. An INDEX does not need a better parser:
    its errors are measured and paid for by execution, which is the point of this round."""
    spec = importlib.util.spec_from_file_location(
        "guide_table_parser", REPO / "canonical" / "tools" / "the_guide_is_a_key_table_v1.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.table_rows(text)


# --------------------------------------------------------------------------------------- #
# 4. THE PROBE PLAN: which way of asking, in which order, and when to stop.
# --------------------------------------------------------------------------------------- #
def define(program: str, *, prompt_limit: int = PROMPT_PROBES_PER_ROOM,
           argv_limit: int = 80, cell: str | None = None) -> dict[str, Any]:
    """argv first (5 ms a probe), then the prompt for what argv rejected (200-600 ms a probe)."""
    room = fresh_room()
    archive = str(room / "vault")          # sealed: naming a file inside it refuses uniformly
    # THE DOCUMENT IS A PROGRAM, NOT PROSE. A REPL handed a text file loads it as code and never
    # reaches its prompt; a pager handed code is still a pager. One hint serves both, and the file
    # is the room's own so the observation contains no path of mine.
    # THE DOCUMENT IS CHOSEN BY THE PAGE. A REPL loads a file as code; a pager pages it. `probe.js`
    # is reached from node's page, which documents `.load    Load JS from a file into the REPL
    # session`; `probe.toml` from corepack's, which documents `--install-directory`. One file, named
    # by the environment, one variable -- and a single document keeps this writer-level setting out
    # of the outcome.
    source = room / "probe.js"          # given RELATIVE: the probe's cwd is the trial itself
    source.write_text("const value = 1;\n")
    index = candidates(program)
    page = one_shot_plain([program, "--help"]) or one_shot_plain([program, "-h"])
    for path in command_trees(page, program):
        if path not in index["tokens"]:
            index["tokens"].append(path)
    learned_form = learn_a_form(program)
    if learned_form.get("form") and learned_form.get("words", 0) >= 5:
        for row in table_rows_loose(one_shot_plain([program, *learned_form["form"]])):
            for token in row["tokens"]:
                if token not in index["tokens"]:
                    index["tokens"].append(token)
    tokens = index["tokens"][:argv_limit]
    results: list[dict[str, Any]] = []
    argv_ms = 0.0
    for token in tokens:
        got = classify(room, program, token, "argv", archive)
        argv_ms += got["ms"]
        results.append(got)
    rejected = [r["token"] for r in results if r["verdict"] in ("NOT_DEFINED", "BLIND")]
    prompt_ms = 0.0
    prompt_results: list[dict[str, Any]] = []
    # ONLY THE PROMPT CAN DEFINE A PAGER'S OR A REPL'S ALPHABET, and only for candidates argv
    # rejected -- `less alpha.txt` plus the stroke `s` is a real command where `less s` is a
    # request to open a file called `s`.
    for token in rejected[:prompt_limit]:
        got = classify(room, program, token, "prompt", source.name, payload="beta.out")
        prompt_ms += got["ms"]
        prompt_results.append(got)
    confirmed = [r for r in results + prompt_results
                 if r["verdict"] in ("DEFINED", "MOVES_STATE")]
    # THE CELL IS CHECKED BY THE RUN, NOT TRUSTED FROM THE PAGE. A room whose page says "option
    # table" but which answers only at its prompt is not an option table, and the discrepancy is
    # the correction: the page proposed a cell, the probe settles it.
    by_argv = [r for r in results if r["verdict"] in ("DEFINED", "MOVES_STATE")]
    by_prompt = [r for r in prompt_results if r["verdict"] in ("DEFINED", "MOVES_STATE")]
    cell_verdict = ("UNPROVEN" if not by_argv and not by_prompt else
                    "OPTION_TABLE" if by_argv and not by_prompt else
                    "KEY_TABLE" if by_prompt and not by_argv else "BOTH_WAYS")
    problems = []
    if not index["tokens"] and not by_prompt:
        problems.append("the index found nothing and the prompt defined nothing: this program "
                        "publishes no alphabet in any form tried")
    if cell and cell_verdict not in ("UNPROVEN",) and cell != cell_verdict:
        problems.append(f"the page proposed {cell} and the run produced {cell_verdict}")
    if confirmed and len([r for r in results + prompt_results if r["verdict"] == "BLIND"]) > 0.3 * len(results + prompt_results):
        problems.append("more than a third of the candidates were unobservable")
    return {
        "cell_verdict": cell_verdict, "problems": problems,
        "program": program, "room": str(room), "learned_form": learned_form,
        "index_tokens": len(index["tokens"]), "index_answers_read": index["answers_read"],
        "index_raw_words": index["raw_words"],
        "argv_probed": len(results), "argv_ms": round(argv_ms, 1),
        "prompt_probed": len(prompt_results), "prompt_ms": round(prompt_ms, 1),
        "confirmed": len(confirmed),
        "moves_state": [r["token"] for r in confirmed if r["verdict"] == "MOVES_STATE"],
        "defined_by_argv": [r["token"] for r in results if r["verdict"] == "DEFINED"][:40],
        "defined_by_prompt": [r["token"] for r in prompt_results
                              if r["verdict"] in ("DEFINED", "MOVES_STATE")][:20],
        "blind": [r["token"] for r in results + prompt_results if r["verdict"] == "BLIND"][:10],
        "precision_of_the_index": (round(len(confirmed) / len(tokens), 3) if tokens else None),
        "argv_reject_sample": [r["token"] for r in results
                               if r["verdict"] == "NOT_DEFINED"][:12],
        "probes": sum(r["probes"] for r in results + prompt_results),
        "evidence_sample": [r for r in confirmed[:3]],
    }


# --------------------------------------------------------------------------------------- #
# 5. THE UNSEEN ROOMS: programs no round of this project has touched, chosen by a stated rule.
# --------------------------------------------------------------------------------------- #
def unseen_programs(count: int = 4) -> list[str]:
    """The rule, stated so it can be audited: a PATH program that is not denied, prints something
    for `--help` inside the timeout, and is not a program any earlier round of this project used
    (that set is named, and it is `KNOWN`)."""
    out: list[str] = []
    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            continue
        for name in entries:
            if len(out) >= count:
                return out
            if name in DENY or name in KNOWN or not re.fullmatch(r"[a-z][a-z0-9_-]{1,15}", name):
                continue
            full = os.path.join(directory, name)
            if not (os.path.isfile(full) and os.access(full, os.X_OK)):
                continue
            probe = run_argv(pathlib.Path(tempfile.mkdtemp()), [full, "--help"])
            if probe.get("exit") == "TIMEOUT" or not str(probe.get("out", "")).strip():
                continue
            if len(str(probe.get("out", "")).split()) < 20:
                continue
            out.append(name)
    return out


KNOWN = frozenset({"less", "more", "node", "python3", "bash", "sh", "pdb", "python", "pip",
                   "git", "grep", "sed", "awk", "find", "tar", "openssl", "ls", "cat", "echo"})


# --------------------------------------------------------------------------------------- #
# 6. THE MEASUREMENT
# --------------------------------------------------------------------------------------- #
def measure(*, unseen: int = 4, reset: bool = True) -> dict[str, Any]:
    started = time.time()
    if reset and STORE.exists():
        STORE.unlink()
    seen = ("less", "bash", "node", "pdb", "sh")
    seen_rooms = {p: define(p, prompt_limit=16) for p in seen if shutil.which(p)}
    unseen_rooms = {p: define(p, prompt_limit=8) for p in unseen_programs(unseen)}

    def summary(rooms: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "rooms": len(rooms),
            "index_tokens": sum(r["index_tokens"] for r in rooms.values()),
            "confirmed": sum(r["confirmed"] for r in rooms.values()),
            "moves_state": sorted({t for r in rooms.values() for t in r["moves_state"]}),
            "probes": sum(r["probes"] for r in rooms.values()),
            "ms": round(sum(r["argv_ms"] + r["prompt_ms"] for r in rooms.values()), 1),
            "precision": round(
                sum(r["confirmed"] for r in rooms.values())
                / max(sum(r["argv_probed"] + r["prompt_probed"] for r in rooms.values()), 1), 3),
            "rooms_with_no_confirmed_token": sorted(p for p, r in rooms.items()
                                                    if r["confirmed"] == 0),
        }

    memory = {"schema": STORE_SCHEMA, "authority": AUTHORITY, "geometry": GEOMETRY,
              "definitions": {p: {"defined": r["defined_by_argv"] + r["defined_by_prompt"],
                                  "moves_state": r["moves_state"]}
                              for p, r in {**seen_rooms, **unseen_rooms}.items()},
              "note": "a definition is (program, token, way of asking, room state) and a verifier "
                      "that reproduces it; no description, no prose, no transcript"}
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(memory, indent=1) + "\n")

    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE, "geometry": GEOMETRY,
        "deny_rule": sorted(DENY), "known_rule": sorted(KNOWN),
        "seen_rooms": seen_rooms, "unseen_rooms": unseen_rooms,
        "summary_seen": summary(seen_rooms), "summary_unseen": summary(unseen_rooms),
        "measured": {"seconds": round(time.time() - started, 1),
                     "probes_total": sum(r["probes"] for r in
                                         list(seen_rooms.values()) + list(unseen_rooms.values())),
                     "rooms": len(seen_rooms) + len(unseen_rooms)},
        "removed_parts": {
            "the_parser_as_the_definer": {
                "what_it_was": "round 5's typography parser deciding what a program's commands are",
                "what_it_measured": "2 of 7 rooms agreed with the program's own live answer",
                "why_demoted": "it is now an INDEX only: it proposes candidates and the machine "
                               "disposes of them. Its precision is measured here instead of "
                               "assumed."},
            "grading_a_probe_by_its_text": {
                "what_it_was": "reading 'not found' as 'no such command' and 'invalid option' as "
                               "'unknown'",
                "what_it_measured": "`sh -c help` answers `help: not found` and a round-3 "
                                    "instrument read that as a shell with no command table",
                "why_deleted": "a probe is graded by a DIFFERENTIAL against a control of the same "
                               "shape, never by what the text says"},
        },
        "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
    }


#: The verifier for a stored definition, written once. A definition that cannot state how to
#: reproduce it is a note; this store holds only rows that can be re-run.
VERIFIER = ("probe again in a throwaway clone, compare the observation against "
            "{control_class} (the shape-matched controls), and require the same verdict")

#: THE STARTING CELLS. The program's page decides which one it is, and the choice is REVERSIBLE by
#: measurement (`--cell`): a room that answers argv is checked at the prompt too, and if exactly one
#: way produces a definition, the cell is corrected by the run. Two programs per cell is the
#: minimum that a transfer can be tested against without inventing a held-out set.
CELLS: dict[str, tuple[str, ...]] = {
    "OPTION_TABLE": ("pygmentize", "corepack"),
    "KEY_TABLE": ("less", "more"),
    "TOKEN_TABLE": ("pdb", "nodejs"),
    "BUILTIN_SET": ("bash", "sh"),
}


#: HELD BACK ON PURPOSE. Seven programs whose declarations are stated here IN ADVANCE and whose runs
#: are NOT in this receipt. Scoring a round on the rooms it was tuned on is how a report becomes a
#: brochure; these are the test set, and they are named now so that naming them later cannot be
#: mistaken for choosing them afterwards.
BANK: tuple[dict[str, str], ...] = (
    {"program": "tar", "cell": "OPTION_TABLE", "declared": "a page of options"},
    {"program": "grep", "cell": "OPTION_TABLE", "declared": "a page of options"},
    {"program": "find", "cell": "OPTION_TABLE", "declared": "a page of options"},
    {"program": "openssl", "cell": "SUBCOMMAND_TREE", "declared": "a page of subcommands"},
    {"program": "git", "cell": "SUBCOMMAND_TREE", "declared": "a page of subcommands"},
    {"program": "python3", "cell": "TOKEN_TABLE", "declared": "a named command table one level down"},
    {"program": "vim", "cell": "KEY_TABLE", "declared": "a page of keystrokes"},
)


def cell_problems() -> list[dict[str, Any]]:
    """Which cell a program belongs to, decided by its OWN declarations, and why.

    A cell is not a name: it is the (way of asking, answer kind) pair the program's page states.
    The statement is the argument; the `--cell` correction is the measurement.
    """
    problems: list[dict[str, Any]] = []
    for cell, programs in CELLS.items():
        for program in programs:
            if not shutil.which(program):
                continue
            got = define(program, cell=cell, prompt_limit=8, argv_limit=24)
            problems.append(got)
    return problems


def measure_cells(*, reset: bool = True) -> dict[str, Any]:
    """Walk the cells, then hold out one program per cell and score the transfer."""
    if reset and STORE.exists():
        STORE.unlink()
    started = time.time()
    per_cell: dict[str, Any] = {}
    for cell, programs in CELLS.items():
        rows = {p: define(p, cell=cell, prompt_limit=8, argv_limit=24)
                for p in programs if shutil.which(p)}
        per_cell[cell] = rows
    transfers = []
    for cell, rows in per_cell.items():
        if len(rows) < 2:
            continue
        (teach_name, teach), (held_name, held) = list(rows.items())[:2]
        plan = probe_plan(teach, held)
        transfers.append({"cell": cell, "taught_by": teach_name, "held_out": held_name,
                          "plan": plan,
                          "correct": plan.get("verdict_matched")})
    return {"schema": SCHEMA, "authority": AUTHORITY, "date": DATE, "geometry": GEOMETRY,
            "cells": {c: {p: {"index_tokens": r["index_tokens"], "confirmed": r["confirmed"],
                              "argv": [t for t in r["defined_by_argv"][:8]],
                              "prompt": r["defined_by_prompt"][:8],
                              "verdict": r["cell_verdict"], "problems": r["problems"][:6]}
                          for p, r in rows.items()}
                      for c, rows in per_cell.items()},
            "transfer": transfers,
            "kept_frozen_for_the_next_round": BANK,
            "measured": {"seconds": round(time.time() - started, 1),
                         "cells": len(per_cell),
                         "transfer_attempts": len(transfers),
                         "transfer_correct": sum(1 for t in transfers if t["correct"])},
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0}


def probe_plan(teach: Mapping[str, Any], held: Mapping[str, Any]) -> dict[str, Any]:
    """The object that generalises: a MAP from what was measured to where to look next.

    A word learned in one room is worthless in another (`less`'s `s` means nothing to `pdb`). What
    survives a program change is the ORDER OF INVESTIGATION and the WAY OF ASKING that produced a
    definition, so the plan is `(cell) -> (way, order, stopping rule)`, and transferring it is one
    line: run it on the held-out program and see whether it lands the same verdict.
    """
    argv_confirmed = len(teach["defined_by_argv"])
    prompt_confirmed = len(teach["defined_by_prompt"])
    way = "argv" if argv_confirmed >= prompt_confirmed else "prompt"
    predicted = "argv" if argv_confirmed else ("prompt" if prompt_confirmed else "none")
    actual = ("argv" if held["defined_by_argv"] else
              ("prompt" if held["defined_by_prompt"] else "none"))
    return {"way_that_produced_definitions": way,
            "predicted_way_for_the_held_out_program": predicted,
            "held_out_way_that_produced_definitions": actual,
            "verdict_matched": predicted == actual and predicted != "none",
            "order": ["page", "learned_form", "argv", "prompt"],
            "stopping_rule": "stop when a candidate reproduces and differs from its controls"}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--unseen", type=int, default=4)
    parser.add_argument("--cells", action="store_true")
    args = parser.parse_args(argv)
    if args.cells:
        receipt = measure_cells()
    else:
        receipt = measure(unseen=args.unseen)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, default=str) + "\n", encoding="utf-8")
    if args.cells:
        print(json.dumps(receipt["measured"], indent=1))
        for cell, rows in receipt["cells"].items():
            for program, row in rows.items():
                print(f"  {cell:14s} {program:11s} index={row['index_tokens']:3d} "
                      f"confirmed={row['confirmed']:3d} verdict={row['verdict']:16s} "
                      f"argv={row['argv'][:3]} prompt={row['prompt'][:3]}")
        for t in receipt["transfer"]:
            print(f"  transfer {t['cell']:14s} {t['taught_by']}->{t['held_out']} "
                  f"predicted={t['plan']['predicted_way_for_the_held_out_program']} "
                  f"actual={t['plan']['held_out_way_that_produced_definitions']} "
                  f"correct={t['correct']}")
        return 0
    for label in ("summary_seen", "summary_unseen"):
        print(label, json.dumps(receipt[label], indent=1))
    for group in ("seen_rooms", "unseen_rooms"):
        for program, room in receipt[group].items():
            print(f"  {program:10s} index={room['index_tokens']:3d} confirmed={room['confirmed']:3d} "
                  f"argv={room['argv_probed']:3d} prompt={room['prompt_probed']:2d} "
                  f"moves={room['moves_state']} blind={len(room['blind'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
