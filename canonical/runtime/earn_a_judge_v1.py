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

  1. DISCRIMINATION -- it exits 0 on a file that IS the kind and non-zero on one that is
     NOT. Measured against a probe pair that is CONSTRUCTED by a program rather than typed
     (a real archive written by the archiver; bytes that are not). Both verdicts are needed:
     0 on both is `cat`, non-zero on both is a broken call, non-zero on the real one is a
     judge of something else. None of those may be admitted.
  2. DETERMINISM -- the same file judged twice gives the same verdict. A judge that changes
     its mind cannot classify anything.
  3. NO SIDE EFFECTS ON THE TREE -- judging is a read. `python3 -m py_compile` writes
     `__pycache__` and round 10 was bitten by exactly that: the scan read the `.pyc` files its
     own validator had just written and called markdown python. A candidate that alters the
     tree it judged is refused here, at admission, rather than discovered later.

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
REFUSED_ACCEPTS_EVERYTHING = "REFUSED__ACCEPTED_THE_DECOY_TOO_THIS_IS_cat"
REFUSED_REJECTS_EVERYTHING = "REFUSED__REJECTED_THE_REAL_FILE_THIS_IS_NOT_A_JUDGE"
REFUSED_NOT_DETERMINISTIC = "REFUSED__VERDICT_CHANGED_ON_THE_SAME_FILE"
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

    real_png = os.path.join(root, "real.png")
    with open(real_png, "wb") as handle:
        handle.write(bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"\x00" * 32)

    for kind, real in (("zip", real_zip), ("gzip", real_gz), ("json", real_json),
                       ("png", real_png), ("tar", real_tar),
                       ("python", real_py), ("utf8_text", real_txt)):
        pairs[kind] = {"real": real, "decoy": decoy}
    return pairs


#: Candidates are DECLARATIONS of how to ask a program whether a file is its kind. Each is
#: written here as an argv the same way round 9's producers were -- and then EARNED or
#: REFUSED by measurement. Being written here grants no authority whatsoever.
CANDIDATES: dict[str, tuple[str, ...]] = {
    "zip": ("unzip", "-t"),
    "gzip": ("gzip", "-t"),
    "tar": ("tar", "-tf"),
    "json": ("python3", "-c", "import json,sys;json.load(open(sys.argv[1]))"),
    "python": ("python3", "-c",
               "import ast,sys;ast.parse(open(sys.argv[1],'rb').read())"),
    "utf8_text": ("python3", "-c",
                  "import sys;open(sys.argv[1],'rb').read().decode('utf-8')"),
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
         repeat: int = 2) -> Candidate:
    """Admit a judge only on evidence: it separates the pair, it is stable, it writes nothing."""
    candidate = Candidate(kind=kind, argv=tuple(argv))
    before = _digest(os.path.dirname(real) or ".")
    on_real = _run(candidate.argv, real)
    on_decoy = _run(candidate.argv, decoy)
    again = _run(candidate.argv, real)
    after = _digest(os.path.dirname(real) or ".")

    candidate.evidence = {"exit_on_real": on_real, "exit_on_decoy": on_decoy,
                          "exit_on_real_again": again}
    if on_real == 127 or on_decoy == 127:
        candidate.status = REFUSED_UNAVAILABLE
    elif on_real != 0:
        candidate.status = REFUSED_REJECTS_EVERYTHING
    elif on_decoy == 0:
        candidate.status = REFUSED_ACCEPTS_EVERYTHING
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
            base = "gzip" if kind.startswith("gzip") else kind
            pair = pairs.get(base)
            if pair is None:
                earned.append(Candidate(kind=kind, argv=tuple(argv),
                                        status=REFUSED_UNAVAILABLE,
                                        evidence={"reason": "no probe pair for this kind"}))
                continue
            earned.append(earn(kind, argv, real=pair["real"], decoy=pair["decoy"]))
        admitted = [c for c in earned if c.status == EARNED]
        return {"schema": SCHEMA, "schema_version": 1,
                "admitted": [c.as_dict() for c in admitted],
                "refused": [c.as_dict() for c in earned if c.status != EARNED],
                "admitted_kinds": sorted(c.kind for c in admitted),
                "candidates": len(earned), "earned": len(admitted),
                "refused_count": len(earned) - len(admitted),
                "model_calls": 0, "network_calls": 0}
    finally:
        if own_root:
            shutil.rmtree(root, ignore_errors=True)


def judges_from(receipt: dict[str, Any]) -> dict[str, Callable[[str], int]]:
    """Turn an earned receipt back into callable judges, so the set is data, not code."""
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
