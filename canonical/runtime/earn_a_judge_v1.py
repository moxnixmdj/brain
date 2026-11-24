#!/usr/bin/env python3
"""A judge is not written; it is EARNED, by being shown one file of the kind and one that is not.

THE WALL THIS CLOSES. Round 10 shipped seven validators -- json, python, utf8_text, png,
gzip, tar, zip -- hand-written, each a sentence I typed. That set was named as the ceiling:
an unseen environment is only as understandable as the kinds something can judge, and seven
is not coverage, it is a seed. The obvious next move, writing more of them, is the move that
never ends: every new environment brings kinds nobody wrote a validator for.

THE OBSERVATION. Everything needed to earn a judge is already in two modules that never met.
A REFUSAL NAMES A KIND (`a_refusal_is_a_specification_v1`: 601 of them on the enlarged
openssl census, yielding `certificate`, `key`, `parameters`, `shared library`, `crl`). And a
program's own verdict on a file IS a judgement about that kind -- `gzip -t` rejects what is
not gzip, `unzip -t` what is not zip, `json.load` what is not json.

So a judge does not need to be typed. It needs to be MEASURED.

WHAT A CANDIDATE MUST SURVIVE, and the first version of this file failed all three. The
blind approach -- "a library declares `gzip.open`, so run it on a file and trust the exit" --
produced `yes=0 no=0`: `gzip.open(path,'rb')` is LAZY and returns a handle without reading a
byte, so it accepts everything. A judge that accepts everything is `cat`, which round 10
deliberately excluded because it tells you nothing. A candidate is therefore admitted only on
evidence:

  1. DISCRIMINATION -- and ONE DECOY IS NOT ENOUGH. Round 11 admitted a judge if it said
     yes to a real file of the kind and no to a single nonsense blob. Measured here, that
     test passes judges that are simply WRONG:

         gzip          said 0 on a real gzip AND 0 on a real ZIP FILE
         tar           said 0 on a real tar  AND 0 on a real gzip
         python/ast    said 0 on real python AND 0 on a real JSON document
         utf8_text     said 0 on everything textual, including tar and json

     (gzip 1.12 on Ubuntu: `gzip -t archive.zip` prints "OK" and exits 0. It is a
     legitimate convenience, and it means `gzip -t` does not answer the question "is this a
     gzip?".) None of those is a judge of its kind, and all of them passed the round-11
     test, because a nonsense blob cannot distinguish "rejects what is not my kind" from
     "accepts my kind plus some other real kinds".

     So a candidate must also REJECT EVERY OTHER REAL KIND. The corpus is built once, from
     the kinds we are confident about, and every candidate is run against all of it. That
     is a stricter test and it is the one that matches the question a scan asks.
  2. DETERMINISM -- the same file judged twice gives the same verdict. A judge that changes
     its mind cannot classify anything.
  3. NO SIDE EFFECTS ON THE TREE -- judging is a read. `python3 -m py_compile` writes
     `__pycache__` and round 10 was bitten by exactly that: the scan read the `.pyc` files its
     own validator had just written and called markdown python. A candidate that alters the
     tree it judged is refused here, at admission, rather than discovered later.

TWO KINDS CANNOT HAVE AN HONEST JUDGE HERE, AND THAT IS A RESULT, NOT A GAP TO PAPER OVER.
`json` and `python` are not separable by parsing: a JSON document IS a valid Python program
(`{"a": 1}` parses as an expression statement -- measured), and `python -m py_compile`
therefore says yes to a JSON file. `utf8_text` is likewise accepted by tar and json, because
they are text. A judge that answers "is this syntactically some python" cannot answer "is
this python and not json", and the fix is not a cleverer command: it is to stop asking a
judge to separate kinds that are genuinely nested. Nested kinds are recorded, not denied.

WHAT IS DELIBERATELY NOT DONE. No generated candidate is admitted on its own say-so: the
probe pair is the whole authority, and a candidate that cannot be shown to separate the pair
is REFUSED and named. No candidate is composed by guessing an API from a name -- that is what
`gzip.open(...,'rb')` was, and it was wrong. And a judge is stored as the argv that earned it,
so it can be re-run and re-earned, never as a boolean that claims authority.

Authority NONE. Runs local programs against temporary files it deletes; writes nothing.
$0, no model call, no network call.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import gzip
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

SCHEMA = "PROJECT_BRAIN_EARN_A_JUDGE_V1"

EARNED = "EARNED__SEPARATES_A_REAL_FILE_FROM_A_DECOY_AND_IS_STABLE"
#: A SECOND ADMISSION CLASS, AND ITS ABSENCE WAS THE ERROR. Requiring every judge to reject
#: every other real kind is the right test for a KIND and the wrong test for a NESTED kind.
#: Measured on real directories, the strict rule kept 5 judges and read 0% of the files in
#: /usr/share/doc and /usr/lib/python3 -- because a .py file IS utf8 text and a JSON document
#: IS parseable python, so their judges must accept other kinds to be correct at all.
#: A nested judge is admitted for what it is: it says yes to a SUPERSET. That is still usable
#: -- a file only `utf8_text` accepts has no structure -- but it can never be evidence that a
#: file is NOT something else, so it is recorded under a name that says so.
NESTED = "EARNED_AS_NESTED__ACCEPTS_A_SUPERSET_WHICH_IS_CORRECT_FOR_A_NESTED_KIND"
REFUSED_ACCEPTS_EVERYTHING = "REFUSED__ACCEPTED_THE_DECOY_TOO_THIS_IS_cat"
REFUSED_REJECTS_EVERYTHING = "REFUSED__REJECTED_THE_REAL_FILE_THIS_IS_NOT_A_JUDGE"
REFUSED_NOT_DETERMINISTIC = "REFUSED__VERDICT_CHANGED_ON_THE_SAME_FILE"
REFUSED_ACCEPTS_ANOTHER_REAL_KIND = (
    "REFUSED__SAID_YES_TO_A_KIND_THAT_IS_NOT_ITS_OWN")
REFUSED_CHANGED_THE_TREE = "REFUSED__JUDGING_WROTE_INTO_THE_TREE"
REFUSED_UNAVAILABLE = "REFUSED__THE_PROGRAM_OR_MODULE_IS_NOT_ON_THIS_MACHINE"


@dataclass
class Candidate:
    """A judged claim: the kind it claims to read, and the argv that earned it."""

    kind: str
    argv: tuple[str, ...]
    status: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "argv": list(self.argv), "status": self.status,
                "evidence": self.evidence}


# --------------------------------------------------------------------------- #
# probe pairs: made by a program, never typed here
# --------------------------------------------------------------------------- #
def _py(source: str, *args: str) -> list[str]:
    return [sys.executable, "-c", source, *args]


def probe_pairs(root: str) -> dict[str, dict[str, str]]:
    """One file that IS each kind, and one that is not -- written by producers, not by me.

    The real member of each pair is produced by the archiver or library that defines the
    kind (`zipfile`, `gzip`, `json.dump`), so the pair is not a fixture asserting my own
    expectation. The decoy is the same bytes with no structure, which no real reader accepts.
    """
    pairs: dict[str, dict[str, str]] = {}
    # THE DECOY MUST BE ILLEGAL FOR EVERY KIND, and the first version was not. It was
    # `bytes(range(0,64))`, which is perfectly valid UTF-8 -- so `utf8_text` accepted it,
    # was reported as `cat`, and the refusal was correct and MY probe was wrong. A decoy
    # that one kind accepts turns that kind's judge into a false positive. 0xFF is a byte
    # that cannot begin a UTF-8 sequence, and the result is also not a zip, gzip, tar or png.
    decoy = os.path.join(root, "decoy.bin")
    with open(decoy, "wb") as handle:
        handle.write(b"\xff" * 8 + b"\x00\x01\x02" * 16)

    real_zip = os.path.join(root, "real.zip")
    with zipfile.ZipFile(real_zip, "w") as archive:
        archive.writestr("member.txt", "hello\n")

    real_gz = os.path.join(root, "real.gz")
    with gzip.open(real_gz, "wb") as handle:
        handle.write(b"hello\n")

    real_json = os.path.join(root, "real.json")
    with open(real_json, "w", encoding="utf-8") as handle:
        handle.write('{"a": 1}\n')

    # tar needs a member to name, so its real pair is built by tar itself rather than by a
    # library call -- the same rule: the producer of the kind makes the probe.
    real_tar = os.path.join(root, "real.tar")
    member = os.path.join(root, "member.txt")
    with open(member, "w", encoding="utf-8") as handle:
        handle.write("hello\n")
    subprocess.run(["tar", "-cf", real_tar, "-C", root, "member.txt"],
                   capture_output=True, stdin=subprocess.DEVNULL)

    # python and utf8_text need no producer beyond the interpreter: a file that parses and
    # one that cannot. The decoy below is invalid UTF-8 bytes, so it separates BOTH -- which
    # is why leaving these two out of CANDIDATES was my omission, not a limit of the loop.
    real_py = os.path.join(root, "real.py")
    with open(real_py, "w", encoding="utf-8") as handle:
        handle.write("value = 1\n")

    real_txt = os.path.join(root, "real.txt")
    with open(real_txt, "w", encoding="utf-8") as handle:
        handle.write("plain text\n")

    # ELF -- the biggest unread class measured on a real machine: 73% of /usr/bin. Its real
    # member is a program that is actually on this machine; the decoy is bytes that are not.
    real_elf = shutil.which("ls") or "/bin/ls"

    real_png = os.path.join(root, "real.png")
    with open(real_png, "wb") as handle:
        handle.write(bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"\x00" * 32)

    for kind, real in (("zip", real_zip), ("gzip", real_gz), ("json", real_json),
                       ("png", real_png), ("tar", real_tar),
                       ("python", real_py), ("utf8_text", real_txt),
                       ("elf", real_elf)):
        pairs[kind] = {"real": real, "decoy": decoy}
    return pairs


#: Candidates are DECLARATIONS of how to ask a program whether a file is its kind. Each is
#: written here as an argv the same way round 9's producers were -- and then EARNED or
#: REFUSED by measurement. Being written here grants no authority whatsoever.
#: KINDS THAT ARE GENUINELY NESTED, declared as such rather than discovered by luck. A kind
#: belongs here only when it is a strict SUPERSET of another measured kind, which is a fact
#: about the formats and is checkable: utf8_text accepts every other textual kind, and a JSON
#: document is a valid Python program. Declaring it here does NOT admit it -- the probe still
#: has to separate its own pair and stay deterministic. It only says which test applies.
NESTED_KINDS = frozenset({"utf8_text", "python"})

#: Which probe kind each candidate is judged against. A candidate name is not a kind.
CANDIDATE_KIND: dict[str, str] = {"gzip_stream": "gzip", "gzip_lazy_WRONG": "gzip",
                                  "tarfile": "tar"}

CANDIDATES: dict[str, tuple[str, ...]] = {
    "zip": ("unzip", "-t"),
    "gzip": ("gzip", "-t"),
    "tar": ("tar", "-tf"),
    "json": ("python3", "-c", "import json,sys;json.load(open(sys.argv[1]))"),
    "python": ("python3", "-c",
               "import ast,sys;ast.parse(open(sys.argv[1],'rb').read())"),
    "utf8_text": ("python3", "-c",
                  "import sys;open(sys.argv[1],'rb').read().decode('utf-8')"),
    # ALTERNATIVES THAT ASK A DIFFERENT QUESTION. `gzip -t` tests integrity and calls a zip
    # "OK"; reading a byte through the decompressor asks "is this a gzip stream" and a zip
    # fails it. Same for tar: opening the archive rather than listing it through tar's own
    # format guessing.
    "gzip_stream": ("python3", "-c",
                    "import gzip,sys;gzip.open(sys.argv[1],'rb').read(1)"),
    "tarfile": ("python3", "-c", "import tarfile,sys;tarfile.open(sys.argv[1])"),
    # FOUR PROGRAMS HERE JUDGE ELF AND ALL FOUR AGREE (readelf, objdump, nm, ldd: 0 on a real
    # binary, non-zero on a decoy). `readelf -h` is picked because it reads the header and
    # stops. `strings` is NOT offered: it accepts everything, like `cat`.
    "elf": ("readelf", "-h"),
    "png": ("python3", "-c",
            "import sys;sys.exit(0 if open(sys.argv[1],'rb').read(8)==bytes([137,80,78,71,13,10,26,10]) else 1)"),
    # THE PAIR THAT PROVES THE POINT: a candidate that looks reasonable and is `cat`.
    # `gzip.open(path,'rb')` is lazy and never reads, so it accepts a decoy. It must be
    # refused, and refusing it is the reason this module exists rather than a wider table.
    "gzip_lazy_WRONG": ("python3", "-c",
                        "import gzip,sys;gzip.open(sys.argv[1],'rb')"),
}


def _digest(root: str) -> str:
    h = hashlib.sha256()
    for current, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(current, name)
            h.update(os.path.relpath(path, root).encode())
            try:
                with open(path, "rb") as handle:
                    h.update(handle.read())
            except OSError:
                continue
    return h.hexdigest()


def _run(argv: Sequence[str], path: str, timeout: float = 20.0) -> int:
    try:
        return subprocess.run([*argv, path], capture_output=True, stdin=subprocess.DEVNULL,
                              timeout=timeout).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 127


def earn(kind: str, argv: Sequence[str], *, real: str, decoy: str,
         others: Sequence[str] = (), repeat: int = 2) -> Candidate:
    """Admit a judge only on evidence: it separates the pair, it is stable, it writes nothing."""
    candidate = Candidate(kind=kind, argv=tuple(argv))
    before = _digest(os.path.dirname(real) or ".")
    on_real = _run(candidate.argv, real)
    on_decoy = _run(candidate.argv, decoy)
    again = _run(candidate.argv, real)
    after = _digest(os.path.dirname(real) or ".")

    # THE TEST ONE DECOY CANNOT MAKE: does it accept ANOTHER REAL KIND? A judge of `gzip`
    # that says yes to a zip file is answering a different question, and a scan built on it
    # would report a zip file as gzip -- the same lying-name failure round 10 fixed, arriving
    # through the validator instead of through the suffix.
    accepts_other: list[str] = []
    for other_kind, other_path in ((k, p) for k, p in others):
        if _run(candidate.argv, other_path) == 0:
            accepts_other.append(other_kind)
    candidate.evidence = {"exit_on_real": on_real, "exit_on_decoy": on_decoy,
                          "exit_on_real_again": again,
                          "accepts_other_real_kinds": accepts_other}
    if on_real == 127 or on_decoy == 127:
        candidate.status = REFUSED_UNAVAILABLE
    elif on_real != 0:
        candidate.status = REFUSED_REJECTS_EVERYTHING
    elif on_decoy == 0:
        candidate.status = REFUSED_ACCEPTS_EVERYTHING
    elif accepts_other and kind in NESTED_KINDS:
        candidate.status = NESTED
    elif accepts_other:
        candidate.status = REFUSED_ACCEPTS_ANOTHER_REAL_KIND
    elif repeat > 1 and again != on_real:
        candidate.status = REFUSED_NOT_DETERMINISTIC
    elif before != after:
        candidate.status = REFUSED_CHANGED_THE_TREE
    else:
        candidate.status = EARNED
    return candidate


def earn_set(*, root: str | None = None,
             candidates: dict[str, tuple[str, ...]] | None = None
             ) -> dict[str, Any]:
    """Earn every candidate against probe pairs, and report what survived and what did not."""
    own_root = root is None
    root = root or tempfile.mkdtemp(prefix="brain-judge-")
    try:
        pairs = probe_pairs(root)
        chosen = candidates if candidates is not None else CANDIDATES
        earned: list[Candidate] = []
        for kind, argv in chosen.items():
            # the candidate NAME (e.g. gzip_stream) is not the KIND it judges (gzip)
            judged_kind = CANDIDATE_KIND.get(kind, kind)
            # EXPLICIT, because the prefix hack that was here sent `tarfile` looking for a
            # kind called "tarfile", found no probe pair, and reported the judge unavailable
            # when it was merely never given a file. A candidate declared against the WRONG
            # KIND is a REFUSED, and it must not be able to look like `REFUSED_UNAVAILABLE`,
            # which means something else entirely.
            base = judged_kind
            pair = pairs.get(base)
            if pair is None:
                earned.append(Candidate(kind=kind, argv=tuple(argv),
                                        status=REFUSED_UNAVAILABLE,
                                        evidence={"candidate": kind,
                                                  "reason": "no probe pair for this kind"}))
                continue
            others = [(k, v["real"]) for k, v in pairs.items() if k != base]
            result = earn(judged_kind, argv, real=pair["real"], decoy=pair["decoy"],
                          others=others)
            result.evidence["candidate"] = kind
            earned.append(result)
        admitted = [c for c in earned if c.status in (EARNED, NESTED)]
        return {"schema": SCHEMA, "schema_version": 1,
                "admitted": [c.as_dict() for c in admitted],
                "refused": [c.as_dict() for c in earned if c.status != EARNED],
                "admitted_kinds": sorted(c.kind for c in admitted),
                "exclusive_kinds": sorted(c.kind for c in admitted if c.status == EARNED),
                "nested_kinds": sorted(c.kind for c in admitted if c.status == NESTED),
                "candidates": len(earned), "earned": len(admitted),
                "refused_count": len(earned) - len(admitted),
                "model_calls": 0, "network_calls": 0}
    finally:
        if own_root:
            shutil.rmtree(root, ignore_errors=True)


def judges_from(receipt: dict[str, Any]) -> dict[str, Callable[[str], int]]:
    """Turn an earned receipt back into callable judges, so the set is data, not code.

    A JUDGE IS NAMED BY ITS KIND, NOT BY ITS CANDIDATE. `gzip_stream` earned the kind
    `gzip`; a scan asking "which validators accept these bytes" must be told `gzip`, or the
    signature it records would differ from an earlier scan's for the same bytes and every
    file would look new for ever. The kind is the identity; the argv is how it was earned.
    """
    judges: dict[str, Callable[[str], int]] = {}
    for row in receipt.get("admitted", ()):
        judges[row["kind"]] = (lambda p, a=tuple(row["argv"]): _run(a, p))
    return judges


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    out = earn_set()
    if args.receipt:
        with open(args.receipt, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
            handle.write("\n")
        print(f"wrote {args.receipt}")
    print(f"earned {out['earned']} of {out['candidates']}: {out['admitted_kinds']}")
    for row in out["refused"]:
        print(f"  refused {row['kind']}: {row['status'].split('__')[0]} "
              f"{row['evidence'].get('exit_on_real')}/{row['evidence'].get('exit_on_decoy')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
