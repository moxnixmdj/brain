#!/usr/bin/env python3
"""Learn to drive a program by trying it, when reading its help is not enough.

cli_contract_inference reads help text. Plenty of programs have none that is
structured, some have none at all, and some lie. All of those currently end in
CLI_HELP_CONTRACT_TEXT_REQUIRED and the machine learns nothing -- about a
program it has sitting right there on the disk, able to be run.

This tries instead. A pattern is a hypothesis about how to drive the program:
which flag names the output, and how the input gets in. Hypotheses are settled
by running them and looking at what appears on disk. The contract that comes
back is derived from OBSERVED EFFECT, not from a claim in a man page.

Which pattern is tried first is itself learned. Real programs cluster on a
handful of conventions -- -o, --output, --outfile -- and the machine should get
better at guessing, across programs, the more programs it meets. So each
pattern's rank comes from the ledger: patterns that have worked before are
tried before patterns that have not. That is not a hardcoded preference order;
it is experience, and it changes.

Nothing here needs a model, a network, or documentation.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile

from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_EMPIRICAL_CLI_PROBE_V1"

PASS = "PASS__EMPIRICAL_CONTRACT_OBSERVED"
NO_EFFECT = "OPEN__EMPIRICAL_NO_OBSERVED_EFFECT"

# (output flag, how the input is delivered)
# input modes: "positional" -> appended last; "stdin" -> piped;
#              "<flag>"     -> passed as that flag's value
PATTERNS: tuple[tuple[str, str], ...] = (
    ("-o", "positional"),
    ("--output", "positional"),
    ("--output=", "positional"),
    ("--outfile", "positional"),
    ("--out", "positional"),
    ("-f", "positional"),
    ("--file", "positional"),
    (">", "positional"),          # shell redirection: no output flag at all
    # reads stdin, writes stdout -- the unix filter convention. base64, sort and
    # friends work this way and were unlearnable until this pair existed.
    (">", "stdin"),
    ("-o", "stdin"),
    ("--output", "stdin"),
    ("--outfile", "stdin"),
    ("-o", "-i"),
    ("--output", "--input"),
    ("-o", "-d"),
    ("--output", "--data"),
)

_MAGIC_BY_SUFFIX = {
    ".png": "89504e470d0a1a0a",
    ".jpg": "ffd8ff",
    ".jpeg": "ffd8ff",
    ".pdf": "25504446",
    ".gz": "1f8b",
    ".zip": "504b0304",
}


def _pattern_key(output_flag: str, input_mode: str) -> str:
    return f"probe:{output_flag}|{input_mode}"


def _ordered_patterns() -> list[tuple[str, str]]:
    """Patterns in the order experience says is worth trying."""
    try:
        from canonical.runtime import ignorance_ledger_v1 as led
        for flag, mode in PATTERNS:
            led.note(_pattern_key(flag, mode), why="empirical cli probe", cost=1.0)
        ranked = led.rank(limit=len(PATTERNS))
        keys = [str(r["what"]) for r in ranked]
        order = []
        for k in keys:
            for flag, mode in PATTERNS:
                if _pattern_key(flag, mode) == k and (flag, mode) not in order:
                    order.append((flag, mode))
        for p in PATTERNS:
            if p not in order:
                order.append(p)
        return order
    except Exception:
        return list(PATTERNS)


def _credit(flag: str, mode: str, worked: bool) -> None:
    try:
        from canonical.runtime import ignorance_ledger_v1 as led
        gid = led.note(_pattern_key(flag, mode), why="empirical cli probe", cost=1.0)
        led.resolve(gid, helped=worked, close=False)
    except Exception:
        pass


def _invoke(exe: str, flag: str, mode: str, out_path: pathlib.Path,
            sample: str, timeout: float, workdir: pathlib.Path) -> dict[str, Any] | None:
    """One hypothesis, run once. Returns what was observed, or None if it errored."""
    argv = [exe]
    if flag == ">":
        pass  # output via shell redirection
    elif flag.endswith("="):
        argv.append(flag + str(out_path))
    elif flag:
        argv.extend([flag, str(out_path)])

    if mode == "positional":
        argv.append(sample)
    elif mode == "stdin":
        pass
    elif mode.startswith("-"):
        argv.extend([mode, sample])

    try:
        if flag == ">":
            # redirection captures stdout, but the input mode still has to be
            # honoured -- a filter like base64 reads stdin, and piping nothing
            # into it produces an empty file, which looks identical to a
            # program that does nothing at all.
            with open(out_path, "wb") as fh:
                if mode == "stdin":
                    proc = subprocess.run(argv, input=sample.encode("utf-8"),
                                          stdout=fh, stderr=subprocess.PIPE,
                                          timeout=timeout, cwd=str(workdir))
                else:
                    proc = subprocess.run(argv, stdout=fh, stderr=subprocess.PIPE,
                                          timeout=timeout, cwd=str(workdir))
        elif mode == "stdin":
            proc = subprocess.run(argv, input=sample, text=True,
                                  capture_output=True, timeout=timeout,
                                  cwd=str(workdir))
        else:
            proc = subprocess.run(argv, capture_output=True, timeout=timeout,
                                  cwd=str(workdir))
    except (subprocess.TimeoutExpired, OSError):
        return None

    return {"returncode": proc.returncode, "argv": list(argv)}


def probe(exe: str, goal: str = "", *, suffix: str = ".out",
          sample: str = "brain-probe-1234",
          timeout: float = 20.0,
          max_trials: int | None = None) -> dict[str, Any]:
    """Drive this program well enough to produce a file, and report how."""
    resolved = exe if (pathlib.Path(exe).is_file() or shutil.which(exe)) else None
    if resolved is None:
        return {"schema": SCHEMA, "status": "OPEN__EMPIRICAL_EXECUTABLE_NOT_FOUND",
                "executable": exe, "trials": []}

    order = _ordered_patterns()
    if max_trials:
        order = order[:max_trials]
    trials: list[dict[str, Any]] = []
    want_magic = _MAGIC_BY_SUFFIX.get(suffix.lower())

    for flag, mode in order:
        with tempfile.TemporaryDirectory(prefix="brain-empirical-") as td:
            work = pathlib.Path(td)
            out = work / ("probe" + suffix)
            observed = _invoke(resolved, flag, mode, out, sample, timeout, work)
            if observed is None:
                _credit(flag, mode, False)
                trials.append({"flag": flag, "mode": mode, "outcome": "ERROR"})
                continue

            exists = out.exists() and out.stat().st_size > 0
            magic_ok = True
            if exists and want_magic:
                magic_ok = out.read_bytes().hex().startswith(want_magic)
            worked = exists and magic_ok
            _credit(flag, mode, worked)

            trials.append({"flag": flag, "mode": mode,
                           "returncode": observed["returncode"],
                           "outcome": "OBSERVED" if worked else
                                      ("MAGIC_MISMATCH" if exists else "NO_OUTPUT")})
            if worked:
                argv_template = [exe]
                if flag not in (">", ""):
                    if flag.endswith("="):
                        argv_template.append(flag + "${input.output_path}")
                    else:
                        argv_template.extend([flag, "${input.output_path}"])
                if mode == "positional":
                    argv_template.append("${input.text}")
                elif mode.startswith("-"):
                    argv_template.extend([mode, "${input.text}"])
                return {
                    "schema": SCHEMA,
                    "status": PASS,
                    "executable": exe,
                    "output_flag": flag,
                    "input_mode": mode,
                    "argv_template": argv_template,
                    "required_inputs": (["text", "output_path"]
                                        if mode != "stdin" else ["output_path"]),
                    "output_prefix_hex": want_magic,
                    # learned by running it, not by trusting what it claims
                    "authority": "EFFECT_OBSERVED_NOT_SEMANTICALLY_PROVEN",
                    "evidence": {"trials": trials,
                                 "output_bytes": out.stat().st_size},
                }

    return {"schema": SCHEMA, "status": NO_EFFECT, "executable": exe,
            "trials": trials}
