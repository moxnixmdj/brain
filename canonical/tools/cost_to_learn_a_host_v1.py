"""How much does it cost to learn a host? Bounded, or catastrophic?

The user asked whether the system should "learn everything in all the environments" or be
goal-directed. That is an empirical question and the earlier instrument accidentally
answered it: typing every executable in `/usr/bin` by running it was **killed by the OOM
killer** (exit 137) and the bounded version did not finish in 120 s.

So this instrument prices both strategies on the same host and reports the failure mode
rather than a rate.

  LEARN_EVERYTHING   run every executable, read its self-description, type it.
  GOAL_DIRECTED      given a wanted type, run only the programs whose own name could
                     produce it, and stop when the goal is satisfied.

The bound is the whole instrument. An untrusted executable may print gigabytes, spawn a
daemon that holds stdout open forever, or wait on stdin. A learner must never collect
unbounded output and must never wait without a deadline, so `probe` reads with a byte
budget, a wall-clock deadline, and a process-group kill.

Schema BRAIN_COST_TO_LEARN_A_HOST_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import selectors
import signal
import subprocess
import sys
import time
from typing import Any

SCHEMA = "BRAIN_COST_TO_LEARN_A_HOST_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DEFAULT_BUDGET = 8192          # bytes of self-description that can matter
DEFAULT_DEADLINE = 2.0         # seconds before a program is assumed unusable


def probe(program: pathlib.Path, budget: int = DEFAULT_BUDGET,
          deadline: float = DEFAULT_DEADLINE,
          cwd: str | None = None) -> dict[str, Any]:
    """One bounded conversation with an executable. Never unbounded, never patient.

    Returns what happened, not just the text: a learner that cannot say *why* it failed
    cannot tell a missing program from a hostile one.

    `cwd` exists because probing is not read-only. `gzip --help` on this host writes a
    zero-byte `gz<pid>` into the CURRENT DIRECTORY, and the first version of this
    instrument therefore littered the repository root with 17 such files, which were then
    committed. A learner may not dirty the tree it is learning from.
    """
    started = time.perf_counter()
    try:
        proc = subprocess.Popen([str(program), "--help"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True,
                                cwd=cwd)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason": type(exc).__name__, "text": "",
                "bytes": 0, "seconds": round(time.perf_counter() - started, 4)}
    chunks: list[bytes] = []
    total = 0
    reason = "EOF"
    selector = selectors.DefaultSelector()
    try:
        fd = proc.stdout.fileno()
        selector.register(fd, selectors.EVENT_READ)
        while total < budget:
            remaining = deadline - (time.perf_counter() - started)
            if remaining <= 0:
                reason = "DEADLINE"
                break
            if not selector.select(remaining):
                reason = "DEADLINE"
                break
            block = os.read(fd, min(4096, budget - total))
            if not block:
                reason = "EOF"
                break
            chunks.append(block)
            total += len(block)
        else:
            reason = "BUDGET"
    except OSError:
        reason = "READ_ERROR"
    finally:
        selector.close()
        # kill the whole group: a child that forked a daemon must not survive the probe
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.wait(timeout=1.0)
        except subprocess.SubprocessError:
            pass
        try:
            proc.stdout.close()
        except OSError:
            pass
    text = b"".join(chunks).decode("utf-8", "replace")
    return {"ok": bool(text.strip()), "reason": reason, "text": text,
            "bytes": total, "seconds": round(time.perf_counter() - started, 4)}


# --- the same closed verb class as the typing instrument -------------------------
CONSTRUCTIVE = ("compress", "uncompress", "decompress", "pack", "encode", "decode")
LOSSY = ("print", "check", "sort", "reverse", "translate", "convert", "wrap",
         "write", "output", "render", "format", "extract", "concatenate",
         "display", "search", "list", "show", "find", "grep", "report", "inspect",
         "dump", "strip", "encode", "analyze", "measure", "count", "compare",
         "describe", "query", "test", "verify", "summarise", "summarize")

# A line that is the program's own error output, or a banner, is not a self-description.
NOT_A_DESCRIPTION = ("version:", "unknown option", "unrecognized option",
                     "invalid option", "unable to open", "no such file",
                     "error:", "fatal:", "cannot open", "usage error")


def self_description(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith(("usage", "or:", "options", "with no file", "with no arguments",
                           "-", "note", "see ", "example", "details")):
            continue
        # anywhere in the line, not just at the start: `identify: unable to open image`
        # carries the program's name before the error, so a startswith test misses it.
        if any(marker in low for marker in NOT_A_DESCRIPTION):
            continue
        # A synopsis is not prose: it carries bracketed option placeholders. A program
        # that answers `--help` with only a synopsis has not described itself at all.
        if "[" in stripped and ("OPTION" in stripped.upper() or "-" in stripped):
            continue
        if stripped.count("  ") > 3:
            continue
        # prose has a sentence in it; a bare row of words does not
        if not re.search(r"[a-z]{3,}", stripped):
            continue
        return stripped
    return ""


# Nouns a program uses when it names its transform by its product rather than a verb.
# `bzip2, a block-sorting file compressor` contains no verb at all, yet names itself
# exactly. Missing this cost 51 of 60 programs their type.
NOUN_FORMS = {"compressor": "compress", "encoder": "encode", "decoder": "decode",
              "archiver": "compress", "digest": "digest", "formatter": "format",
              "filter": "filter", "sorter": "sort"}


def transform_of(description: str) -> str | None:
    words = re.findall(r"[A-Za-z][A-Za-z-]+", description.lower())
    for word in words:
        stem = word[:-3] if word.endswith("ing") else word
        if stem in NOUN_FORMS:
            return NOUN_FORMS[stem]
        if stem in CONSTRUCTIVE:
            return "compress" if stem in ("compress", "uncompress", "decompress",
                                          "pack") else stem
        if stem in LOSSY:
            return stem
    return None


# Names a host uses to say "the reverse of this program". A program that ships one is
# telling us its transform is invertible, and is telling us so in the plainest way
# available: by supplying the undo command itself.
REVERSE_PREFIX = ("un", "de")


def inverse_pairs(names: set[str]) -> dict[str, str]:
    """Map each program name to the reverse command the host ships for it, if any.

    Found the hard way: `unxz` sorts before `xz`, so deduping executables by their real
    target silently deleted `xz` from the census. A symlink is not a duplicate; it is the
    host speaking about the program it points at.
    """
    pairs: dict[str, str] = {}
    for name in names:
        for prefix in REVERSE_PREFIX:
            if name.startswith(prefix) and name[len(prefix):] in names:
                base = name[len(prefix):]
                pairs.setdefault(base, name)
    return pairs


def executables(host: pathlib.Path) -> list[pathlib.Path]:
    """Regular files only, one entry per NAME.

    Not one per target: the name is the host's own vocabulary and the only field a
    learner may use before asking a program anything. `xz`, `unxz`, and `xzcat` are
    three words for one binary, and all three are evidence.
    """
    out: list[pathlib.Path] = []
    for entry in sorted(host.iterdir()):
        if entry.is_file():
            out.append(entry)
    return out


def learn_everything(host: pathlib.Path, limit: int | None = None) -> dict[str, Any]:
    """The expensive strategy: ask every executable, one bounded probe at a time."""
    started = time.perf_counter()
    programs = executables(host)
    sample = programs[:limit] if limit else programs
    typed: dict[str, Any] = {}
    failures: dict[str, int] = {}
    for program in sample:
        if time.perf_counter() - started > 120:
            failures["__stopped_at_120s__"] = failures.get("__stopped_at_120s__", 0) + 1
            break
        got = probe(program)
        if not got["ok"]:
            failures[got["reason"]] = failures.get(got["reason"], 0) + 1
            continue
        description = self_description(got["text"])
        transform = transform_of(description) if description else None
        if transform:
            typed[program.name] = {"transform": transform,
                                   "description": description[:120]}
        else:
            failures["NO_TRANSFORM_VERB"] = failures.get("NO_TRANSFORM_VERB", 0) + 1
    elapsed = round(time.perf_counter() - started, 3)
    return {"strategy": "LEARN_EVERYTHING", "host": str(host),
            "programs_on_host": len(programs), "programs_probed": len(sample),
            "typed": len(typed), "typed_names": sorted(typed),
            "failures": failures, "seconds": elapsed,
            "seconds_per_program": round(elapsed / max(1, len(sample)), 4),
            "extrapolated_seconds_all": round(elapsed / max(1, len(sample))
                                              * len(programs), 2)}


def goal_directed(host: pathlib.Path, wanted: str) -> dict[str, Any]:
    """The cheap strategy: only programs whose own name could produce `wanted`."""
    started = time.perf_counter()
    programs = executables(host)
    # The name is the host's own vocabulary, not the instrument's. We do not know what
    # a program does until we ask it; we only use the name to decide whom to ASK FIRST.
    candidates = [p for p in programs if wanted.lower() in p.name.lower()]
    asked: list[dict[str, Any]] = []
    found: dict[str, Any] | None = None
    for program in candidates:
        got = probe(program)
        description = self_description(got["text"]) if got["ok"] else ""
        transform = transform_of(description) if description else None
        asked.append({"program": program.name, "ok": got["ok"],
                      "reason": got["reason"], "transform": transform})
        if transform in ("compress", "encode"):
            found = {"program": program.name, "transform": transform,
                     "description": description[:120]}
            break
    elapsed = round(time.perf_counter() - started, 4)
    return {"strategy": "GOAL_DIRECTED", "host": str(host), "wanted": wanted,
            "programs_on_host": len(programs), "programs_considered": len(candidates),
            "programs_probed": len(asked), "asked": asked, "found": found,
            "seconds": elapsed}


def run(receipt: pathlib.Path | None = None, host: str = "/usr/bin",
        limit: int | None = 60) -> dict[str, Any]:
    started = time.perf_counter()
    host_path = pathlib.Path(host)
    everything = learn_everything(host_path, limit=limit)
    directed = [goal_directed(host_path, want) for want in ("gzip", "bzip2", "xz")]
    report: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "learn_everything": everything, "goal_directed": directed,
        "comparison": {
            "programs_on_host": everything["programs_on_host"],
            "learn_everything_probed": everything["programs_probed"],
            "learn_everything_extrapolated_seconds": everything["extrapolated_seconds_all"],
            "goal_directed_probed": [d["programs_probed"] for d in directed],
            "goal_directed_seconds": [d["seconds"] for d in directed],
            "ratio_of_programs_probed": round(
                everything["programs_on_host"]
                / max(1, max(d["programs_probed"] for d in directed)), 1),
        },
        "seconds": round(time.perf_counter() - started, 3),
    }
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--host", default="/usr/bin")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args(argv)
    report = run(args.receipt, args.host, args.limit)
    print(json.dumps(report["comparison"], indent=1))
    print(json.dumps({"learn_everything_failures": report["learn_everything"]["failures"],
                      "found": [d["found"] for d in report["goal_directed"]],
                      "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
