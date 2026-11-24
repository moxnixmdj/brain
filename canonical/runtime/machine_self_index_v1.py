#!/usr/bin/env python3
"""Ask this machine what its programs do, and keep the answer as knowledge.

THE WALL THIS ADDRESSES
-----------------------
Measured on 2026-11-24: a sentence that names its program can be bound to that program's own
door (``grounded_binder_v1``), but ordinary sentences mostly do not name it. "Make a compressed
copy of data.txt that gunzip can restore exactly" names the *decompressor*; the thing that
compresses is ``gzip``, a word the sentence never says. The system therefore refused all eight
gate tasks even though every one of them is a thing a person does in two keystrokes.

That is not a knowledge gap in the world, it is a gap between an English word and a program
name -- and the machine closes it itself: ``wc`` says "print the newline counts", ``sha256sum``
says "print or check SHA256 (256-bit) checksums", ``mv`` says "rename SOURCE to DEST". The
vocabulary that routes a sentence to a program is published by the program.

WHAT THIS IS
------------
A one-pass reading of every executable on PATH, stored as JSON next to the ledger:

    once per machine (~15 s measured for 646 programs, ~0.02 s each)
    then a sentence is routed by IDF-weighted overlap against what the programs SAID

Nothing here holds a list of program names, a synonym table or a meaning: the words come from
the machine, and the weights are computed from this machine's own distribution (a word every
program uses -- "usage", "file", "options" -- routes nothing and is weighted to zero).

WHAT IT IS NOT
--------------
It is not a model. Zero parameters, zero training, zero calls out. Rebuilding it on another
machine reads that machine instead.
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MACHINE_SELF_INDEX_V1"
DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[2] / "canonical" / "verification" / "MACHINE_SELF_INDEX_20261124_V1.json"

_STOP = frozenset("""a an the and or of to in on for with that this it is are be so which who
into from by as at its their there then than not no yes if when where what how all any each
every some more most other such only own same very can will just should would could may
usage use uses used using option options optional file files print prints printed printout
command commands program programs following also like value values argument arguments
default defaults note notes see show shows shown given one two may be will if then
else e.g i.e""".split())


def _says(executable: str, *, timeout: float = 0.8, cap: int = 16384) -> str:
    """What the program says about itself, in its own words. `--help` first, then `-h`."""
    for flag in ("--help", "-h"):
        try:
            completed = subprocess.run([executable, flag], capture_output=True,
                                       timeout=timeout, stdin=subprocess.DEVNULL)
        except Exception:
            continue
        text = (completed.stdout or completed.stderr).decode("utf-8", "replace")
        if text.strip():
            return text[:cap]
    return ""


def _words(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z][a-z0-9_+.\-]{2,}", str(text or "").lower())
            if word not in _STOP]


def executables(path: str | None = None) -> dict[str, str]:
    found: dict[str, str] = {}
    for folder in (path or os.environ.get("PATH", "")).split(":"):
        if not folder or not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            candidate = os.path.join(folder, name)
            if name not in found and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                found[name] = candidate
    return found


_FLAG = re.compile(r"--([a-z][a-z0-9-]{1,30})")


def declared_options(said: str) -> tuple[list[str], list[str]]:
    """The option NAMES a program publishes, and the words it uses to describe them.

    A `--help` dump is mostly prose, and prose over 16 KB shares a word with every sentence:
    `ld` mentions "read" fourteen times and won every routing question on sheer volume. The
    part of a help text an author actually curates is the option table -- `-l, --lines   print
    the newline counts` -- where the NAME is a definition and the description is one clause.
    So the vocabulary that routes a sentence is taken from flag lines only.
    """
    names: list[str] = []
    words: list[str] = []
    for line in str(said or "").splitlines():
        if "--" not in line:
            continue
        for match in _FLAG.findall(line):
            names.append(match)
        words.extend(_words(line))
    return sorted(set(names)), sorted(set(words))


def build(*, limit: int | None = None, timeout: float = 0.8,
          names: Sequence[str] | None = None) -> dict[str, Any]:
    """Read every executable on PATH once. The result is the instant-knowledge store.

    `names` restricts the reading to a named few, which is what the tests use: the routing
    logic is what they check, not how many programs this particular container happens to hold.
    """
    programs: dict[str, Any] = {}
    available = executables()
    if names is not None:
        available = {name: available[name] for name in names if name in available}
    for name, path in available.items():
        said = _says(path, timeout=timeout)
        if not said:
            continue
        flags, words = declared_options(said)
        programs[name] = {"path": path, "flags": flags, "words": words,
                          "says": said[:400]}
        if limit and len(programs) >= limit:
            break
    # A word's routing weight is computed from THIS machine: how rare is it among programs?
    frequency: dict[str, int] = {}
    for row in programs.values():
        for word in set(row["words"]) | set(row["flags"]):
            frequency[word] = frequency.get(word, 0) + 1
    total = max(1, len(programs))
    idf = {word: round(math.log((total + 1) / (count + 1)), 4) for word, count in frequency.items()}
    return {"schema": SCHEMA, "programs": programs, "document_frequency": frequency,
            "idf": idf, "count": len(programs), "model_calls": 0, "parameters": 0}


def save(index: Mapping[str, Any], path: str | pathlib.Path = DEFAULT_PATH) -> str:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=0, sort_keys=True))
    return str(path)


def load(path: str | pathlib.Path = DEFAULT_PATH) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())


def route(instruction: str, index: Mapping[str, Any], *, limit: int = 6,
          floor: float = 1.0) -> list[dict[str, Any]]:
    """Which programs does the sentence sound like? Ranked by what they said about themselves.

    Scoring is IDF-weighted overlap: a word carried by one program is worth much more than a
    word carried by half of them, so "newline" routes to `wc` while "file" routes nowhere.
    """
    idf: Mapping[str, float] = index.get("idf") or {}
    asked = {part for token in re.findall(r"[A-Za-z0-9_.+/\-]+", str(instruction or ""))
             for part in _words(re.split(r"[./_=]", token.lower()))}
    ranked: list[dict[str, Any]] = []
    for name, row in (index.get("programs") or {}).items():
        # An identifier the sentence CONTAINS: "sha256" names `sha256sum`. Prefix only from the
        # left, and only for words of four letters or more, because substring matching anywhere
        # made `lnstat` a candidate for "lines" and `taskset` for "table" -- measured, rejected.
        called = {word for word in asked if len(word) >= 4 and name.startswith(word)}
        optioned = asked & set(row.get("flags") or [])
        shared = ((asked & set(row.get("words") or [])) - called) - optioned
        if not (called or optioned):
            continue
        # An identifier beats a coincidence. Being NAMED in the sentence is the caller choosing
        # the program; naming one of the program's own options is the caller describing the
        # operation. Prose overlap only breaks ties, so `ld`'s fourteen incidental "read"s can
        # no longer outvote `wc`'s `--lines`.
        score = 3.0 * sum(idf.get(word, 0.5) for word in called) \
            + 2.0 * sum(idf.get(word, 0.5) for word in optioned) \
            + 0.2 * sum(idf.get(word, 0.0) for word in shared)
        ranked.append({"program": name, "score": round(score, 3),
                       "shared": sorted(called | optioned),
                       "options": sorted(optioned),
                       "says": (row.get("says") or "")[:110]})
    ranked.sort(key=lambda item: (item["score"], len(item["shared"])), reverse=True)
    return [item for item in ranked[:limit] if item["score"] >= floor]


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--route")
    parser.add_argument("--out", default=str(DEFAULT_PATH))
    args = parser.parse_args(argv)
    if args.build:
        index = build()
        print(save(index, args.out), index["count"], "programs")
        return 0
    if args.route:
        index = load(args.out)
        for row in route(args.route, index):
            print(f"{row['score']:6.2f} {row['program']:16s} {row['shared']} | {row['says'][:70]}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
