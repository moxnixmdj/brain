#!/usr/bin/env python3
"""Scan an environment, and say which parts of it the machine has never met.

THE IDEA THIS IMPLEMENTS, and the one thing it refuses to be. The owner's proposal:
go into an arbitrary environment, scan it, diff the scan against what memory knows, and
everything in the remainder is what to go and learn. It is right, and the naive version of
it is worthless, which is the whole problem.

WHY THE NAIVE VERSION IS WORTHLESS. A directory full of files can always be "recognised":
that name is a `.json`, that one is a `.png`. An agent that calls those KNOWN has learned
nothing and will fail anyway, because the extension is a claim about the bytes and nothing
checks it. This repository has already paid for that lesson -- `cli_contract_inference.py`
carries `MAGIC_BY_SUFFIX`, a table mapping suffix to magic bytes, which is exactly the
guess-shaped knowledge that looks like knowing. A `.png` that is not a PNG, a `.json` that
does not parse, a `.py` with a syntax error: all three are KNOWN under an extension rule
and none of them work.

WHAT IS USED INSTEAD: whether a program that DECLARES it can read that kind actually
ACCEPTS these bytes. Every validator here is a program saying so about itself --
`gzip -t` "test compressed file integrity", `tar -tf` "list contents", `unzip -t` "test
archive integrity", and a one-line JSON parse. Each one REJECTS what is not that kind, so
the signature is a test the bytes must pass, not a claim made about them. `bad.json` is
accepted as utf8 text and refused as json; `broken.py` is refused as python. Identity in
this repository is supposed to be content, not name, and this is that applied to a scan.

WHY THE KEY IS THE SIGNATURE AND NOT THE EXTENSION. THE TRANSFER TEST. Learn on one
directory, predict on a directory never seen. Keyed by extension, a `.md` in the new
directory is UNKNOWN because no markdown happened to appear in the first one -- the memory
has transferred nothing, it has memorised a listing. Keyed by the signature, that file is
already understood, because what memory holds is *which programs accept these bytes*, and
that question has the same answer in a directory it has never seen. The extension is kept
in the row as evidence about where this kind tends to appear, never as the identity.

WHAT "UNKNOWN" OBLIGES. A signature memory has never recorded is the entire output that
makes the scan useful: it is the list of what to go and learn, ranked by whether anything
at all accepts it. `sig=()` -- no validator on this machine accepts these bytes -- is not
a failure of the scan; it is the honest statement that this kind is not understood here
yet, and it is the strongest candidate for the next thing to learn.

WHAT THE TWO KEYINGS ACTUALLY DIFFER BY, MEASURED RATHER THAN ARGUED. The honest result is
not a transfer-rate win. Leave-one-out over 100 real files from this repository: signature
keying 100/100, suffix keying 100/100, **signatures buy 0** -- because the repository holds
only three signature classes, so any key that has seen a `.json` recognises the next one.
An earlier version of this file claimed 0.8 against 0.6 on nine hand-made files; that
number was noise from a contrived sample and is retracted here.

What signatures buy instead is LYING NAMES, and there the gap is absolute. Of seven test
files, three declare a kind their bytes are refused by -- `lying.json` (does not parse),
`lying.py` (does not parse), `lying.png` (not a PNG). A suffix rule calls all three known.
The signature catch, whatever their names.

So both keyings are kept and reported, and NEITHER is claimed to be the better predictor.
The scan's product is not "these files are known" -- it is the honest list of what is not.

WHAT A SCAN MUST NOT COST. Measured on this repository: 40 files took 5.1 s, because
`unzip -t` alone spends ~0.2 s per file and every validator runs on every file. A scan must
be cheap or it is not a scan, so each validator is SKIPPED when its kind is impossible for
these bytes by a leading-magic test, and those requests are bounded.

WHAT IT DOES NOT DO. It does not fetch anything (that is `jit_knowledge_v1`, a separate
and existing channel). It does not claim an unknown file is unusable, or a known one
usable, beyond what the validators proved. It does not read a suffix as a promise. And it
does not record an action or a path: what persists is `signature -> which declared
validators accept it`, which is the same question in the next directory.

Authority NONE. Reads a directory and runs short local validations; writes nothing.
$0, no model call, no network call.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

SCHEMA = "PROJECT_BRAIN_SCAN_AND_DIFF_AGAINST_MEMORY_V1"

KNOWN = "KNOWN__MEMORY_HAS_THIS_SIGNATURE"
UNKNOWN = "UNKNOWN__NOTHING_IN_MEMORY_ACCEPTS_THESE_BYTES"
PROVEN_UNUSABLE = "PROVEN_UNUSABLE__NAMED_AS_ONE_KIND_AND_REFUSED_BY_IT"


# --------------------------------------------------------------------------- #
# validators: programs stating what they accept, and rejecting what they do not
# --------------------------------------------------------------------------- #
def _rc(argv: Sequence[str], path: str, timeout: float = 20.0) -> int:
    try:
        return subprocess.run(list(argv) + [path], capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=timeout).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 127


def _py_test(source: str, path: str) -> int:
    """Run a python one-liner against a path; a failure to run is a rejection."""
    try:
        return subprocess.run(["python3", "-c", source, path], capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=20).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 127


#: Each entry is a KIND, the program that declares it can judge that kind, and the test.
#: The test must REJECT bytes that are not the kind -- a validator that accepts everything
#: (`cat`) tells you nothing and is deliberately absent.
VALIDATORS: dict[str, Callable[[str], int]] = {
    "json": lambda p: _py_test("import json,sys;json.load(open(sys.argv[1]))", p),
    # `py_compile` WRITES `__pycache__` NEXT TO THE FILE IT JUDGES -- measured: a scan of
    # `intake/` reported `json+python+utf8_text` for markdown, because the scanner was
    # reading the .pyc files its own validator had just created and calling them python.
    # A measurement that changes what it measures is not a measurement. `ast.parse` judges
    # the same property and writes nothing, so the scan stays a read.
    "python": lambda p: _py_test(
        'import ast,sys;ast.parse(open(sys.argv[1],"rb").read())', p),
    "utf8_text": lambda p: _py_test(
        'import sys;open(sys.argv[1],"rb").read().decode("utf-8")', p),
    "png": lambda p: _py_test(
        'import sys;sys.exit(0 if open(sys.argv[1],"rb").read(8)==bytes([137,80,78,71,13,10,26,10]) else 1)', p),
    "gzip": lambda p: _rc(["gzip", "-t"], p),
    "tar": lambda p: _rc(["tar", "-tf"], p),
    "zip": lambda p: _rc(["unzip", "-t"], p),
}


#: A cheap NECESSARY condition per kind, so a validator is not run when its kind is
#: impossible. It is used only to SKIP -- never to accept -- so a wrong entry here can lose
#: a kind but can never invent one. `unzip -t` costs ~0.2 s per file and dominated the scan.
_MAGIC = {
    "png": lambda head: head.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10])),
    "gzip": lambda head: head.startswith(b"\x1f\x8b"),
    "zip": lambda head: head.startswith((b"PK\x03\x04", b"PK\x05\x06")),
    "tar": lambda head: len(head) > 262 and head[257:262] == b"ustar",
}


def _possible(kind: str, path: str) -> bool:
    test = _MAGIC.get(kind)
    if test is None:
        return True
    try:
        with open(path, "rb") as handle:
            return bool(test(handle.read(512)))
    except OSError:
        return False


def signature(path: str, validators: Mapping | None = None) -> tuple[str, ...]:
    """WHICH DECLARED VALIDATORS ACCEPT THESE BYTES. The identity of a file, here."""
    chosen = validators if validators is not None else VALIDATORS
    return tuple(name for name, test in sorted(chosen.items())
                 if _possible(name, path) and test(path) == 0)


# --------------------------------------------------------------------------- #
# the scan
# --------------------------------------------------------------------------- #
@dataclass
class Item:
    path: str
    suffix: str
    size: int
    sig: tuple[str, ...]
    verdict: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "suffix": self.suffix, "size": self.size,
                "signature": list(self.sig), "verdict": self.verdict, "note": self.note}


def scan(root: str | os.PathLike[str], *, max_files: int = 200,
         max_bytes: int = 8_000_000) -> list[Item]:
    """Every regular file, with the signature of its CONTENT rather than of its name."""
    items: list[Item] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "node_modules"})
        for name in sorted(names):
            if len(items) >= max_files:
                return items
            path = os.path.join(current, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size > max_bytes:
                continue
            items.append(Item(path=os.path.relpath(path, root),
                              suffix=os.path.splitext(name)[1].lower(),
                              size=size, sig=signature(path)))
    return items


# --------------------------------------------------------------------------- #
# memory: signature -> what accepted it, and nowhere does a path go in
# --------------------------------------------------------------------------- #
@dataclass
class Memory:
    """What the machine has met, keyed by CONTENT SIGNATURE.

    A path never enters this store. That is the property that makes the transfer test
    meaningful: nothing here can be answered by remembering a filename.
    """
    seen: dict[tuple[str, ...], dict[str, Any]] = field(default_factory=dict)
    unread: int = 0

    def learn(self, items: Sequence[Item]) -> None:
        for item in items:
            # THE EMPTY SIGNATURE IS NEVER LEARNED, and this is the defect that made the
            # whole idea worthless until it was found by a failing test. `sig=()` means
            # NOTHING accepts these bytes -- it is the ABSENCE of knowledge, and it is the
            # same key for every kind the machine cannot read. Storing it made the FIRST
            # unaccepted file teach memory that unaccepted bytes are a known kind, so every
            # later unknown file was reported KNOWN: the machine confidently claiming to
            # know exactly the things it does not know. An absence can never be evidence.
            if not item.sig:
                self.unread += 1
                continue
            row = self.seen.setdefault(item.sig, {"count": 0, "suffixes": {}, "items": 0})
            row["count"] += 1
            row["items"] += 1
            row["suffixes"][item.suffix] = row["suffixes"].get(item.suffix, 0) + 1

    def judge(self, item: Item) -> tuple[str, str]:
        if not item.sig:
            return UNKNOWN, "no declared validator accepts these bytes"
        if item.sig in self.seen:
            row = self.seen[item.sig]
            return KNOWN, f"{row['count']} earlier file(s) with this signature"
        # Nothing accepts these bytes. Not a failure -- the honest gap.
        if not item.sig:
            return UNKNOWN, "no declared validator accepts these bytes"
        return UNKNOWN, f"accepted as {', '.join(item.sig)} but this signature is new"

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA,
                "signatures": [{"signature": list(sig), **row}
                               for sig, row in sorted(self.seen.items(), key=lambda kv: -kv[1]["count"])],
                "distinct_signatures": len(self.seen),
                "unread_files_seen": self.unread}


def judge_all(memory: Memory, items: Sequence[Item]) -> list[Item]:
    for item in items:
        item.verdict, item.note = memory.judge(item)
    return list(items)


# --------------------------------------------------------------------------- #
# the one number that matters: does memory transfer to a directory never seen?
# --------------------------------------------------------------------------- #
def transfer(*, learned: Sequence[Item], new: Sequence[Item]) -> dict[str, Any]:
    """Score a memory built on `learned` when it judges `new`.

    BOTH KEYINGS ARE SCORED, because the difference is the whole argument. An extension
    key can only recognise what it was shown; a signature key recognises the KIND. If the
    two agree, signatures are not buying anything and this module should be deleted.
    """
    learned_signatures = {item.sig for item in learned}
    learned_suffixes = {item.suffix for item in learned}

    by_signature = sum(1 for item in new if item.sig in learned_signatures)
    by_suffix = sum(1 for item in new if item.suffix in learned_suffixes)
    signature_new, suffix_new = len(new) - by_signature, len(new) - by_suffix
    return {
        "new_files": len(new),
        "signature_keying": {"recognised": by_signature, "unrecognised": signature_new,
                             "rate": round(by_signature / len(new), 3) if new else None},
        "suffix_keying": {"recognised": by_suffix, "unrecognised": suffix_new,
                          "rate": round(by_suffix / len(new), 3) if new else None},
        "signatures_buy": by_signature - by_suffix,
        "learned_signatures": len(learned_signatures),
        "learned_suffixes": len(learned_suffixes),
    }


def census(root: str | os.PathLike[str], *, memory: Memory | None = None,
           max_files: int = 200) -> dict[str, Any]:
    """The scan the owner described: read it, diff it against memory, count what is missing."""
    items = scan(root, max_files=max_files)
    memory = memory or Memory()
    judged = judge_all(memory, items)
    known = [i for i in judged if i.verdict == KNOWN]
    unknown = [i for i in judged if i.verdict == UNKNOWN]
    nothing = [i for i in judged if not i.sig]
    return {"schema": SCHEMA, "root": str(root), "files": len(judged),
            "known": len(known), "unknown": len(unknown),
            "unknown_with_no_validator": len(nothing),
            "items": [i.as_dict() for i in judged],
            # WHAT TO GO AND LEARN, ranked: nothing accepts these bytes at all first
            "learn_next": [i.path for i in sorted(nothing, key=lambda i: -i.size)[:10]] +
                          [i.path for i in unknown if i.sig][:10],
            "signature_histogram": _histogram(judged)}


def to_ignorance(gaps: Sequence[Item], *, path: str | None = None) -> list[str]:
    """Put each unknown file into the existing ranked gap ledger, and return the ids.

    REUSE, NOT A SECOND LEDGER. `ignorance_ledger_v1` already ranks a gap by
    `value = p_useful / (1 + cost)` with a Beta prior, so an untried gap scores 0.5 and one
    tried ten times useless scores 0.045. Feeding the scan into it means the scan chooses
    what to learn next from ITS OWN OUTCOME HISTORY rather than from a rule written here.

    THE COST IS THE THING THAT MATTERS, and it is not 1.0 for every file. A file nothing
    accepts is the cheap, decisive gap: one `jit_knowledge` resolve can settle what these
    bytes are. A file some validator accepts is already half understood and buys less. So
    the unaccepted ones are noted cheap and the half-known ones dearer, and the ordering
    falls out of the existing formula instead of being asserted.
    """
    from canonical.runtime import ignorance_ledger_v1 as ledger
    identity = {}
    for item in gaps:
        what = "content kind " + ("+".join(item.sig) if item.sig else "(unaccepted)")
        why = f"a file of this kind must be usable: {item.suffix or 'no suffix'}"
        if (what, why) in identity:
            identity[(what, why)].append(item.path)
            continue
        identity[(what, why)] = [item.path]
    ids = []
    for (what, why), paths in identity.items():
        cost = 1.0 if "(unaccepted)" in what else 2.0
        if path is not None:
            ids.append(ledger.note(what, why=why, cost=cost, path=path))
        else:
            ids.append(ledger.note(what, why=why, cost=cost))
    return ids


def _histogram(items: Sequence[Item]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = "+".join(item.sig) if item.sig else "(none)"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


Mapping = dict  # tiny alias so the signature() annotation stays readable


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root")
    parser.add_argument("--memory")
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)

    memory = Memory()
    if args.memory and os.path.exists(args.memory):
        raw = json.load(open(args.memory, encoding="utf-8"))
        for row in raw.get("signatures", []):
            memory.seen[tuple(row["signature"])] = {"count": row["count"],
                                                     "suffixes": row["suffixes"],
                                                     "items": row.get("items", row["count"])}
    out = census(args.root, memory=memory)
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.receipt}")
    else:
        print(json.dumps({k: v for k, v in out.items() if k != "items"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
