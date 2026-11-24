#!/usr/bin/env python3
"""The goal is an effect, not a name. This is where that is checked.

THE DEFECT THIS EXISTS TO REMOVE
--------------------------------
Measured 2026-11-24, in `canonical/tools/learn_in_a_real_computer_probe_v1.py`:
the Perfect Algorithm was given the goal "compress the input into out.gz" on a
real computer. It scanned, planned `run_xz`, executed it, observed that a file
called `out.gz` existed, reported PASS, admitted the rule on two fresh
instances, persisted it, and replayed it instantly in 0.11 s on two more
instances -- **four times producing xz data inside a file named `out.gz`**. The
gzip reader refuses that file. The loop was fast, consistent, permanent and
wrong, and every receipt said so in a field nobody had taught it to read.

The cause is not the learner. The cause is that the goal was "a name appeared
in the observation". A name is satisfied by any program that writes that name.
What the goal MEANT was that the input's bytes are recoverable from the output
in the format the output's name declares.

THE LAW, AND WHY IT IS NOT A TABLE OF FORMATS
---------------------------------------------
An artifact is correct when the machine's own reader for its declared format
turns it back into exactly the input bytes. There are three parts, and none of
them is memorised world knowledge:

  1. **The suffix names a format.** `out.gz` declares gzip because its suffix
     says so -- this is the environment's own naming convention, visible in the
     name it was given, not a fact we stored.
  2. **The reader is derived from the suffix and then PROVEN.** `gz` names the
     program `gzip` (longest installed name that starts with it), `xz` names
     `xz`, `bz2` names `bzip2`, `zip` names `unzip`. A candidate is only a
     reader if it exists on this machine and accepts the artifact.
  3. **The round trip is the proof.** The decoded bytes must equal the source's
     bytes exactly. Not a prefix, not a size, not a checksum we chose.
  4. **A liberal reader is not proof of the format.** Measured 2026-11-24: a zip
     container named `out.gz` passed a `gzip -dc` round trip, because gzip(1) can
     extract zip archives. The artifact was not gzip and a strict reader refused
     it. So the artifact's own header must match the signature the machine's own
     compressor produces for that format -- derived by running it, not remembered.

This is why the oracle transfers to formats we never wrote down: a `.zst`
artifact with `zstd` installed is verified by `zstd -dc`, and an unknown suffix
with no installed reader yields `NO_READER` -- an explicit refusal, never a
pass. `UNVERIFIABLE` is an answer; "probably fine" is not.

WHAT THIS IS NOT
----------------
It is not a guarantee that a *user's* goal is verified. It verifies effects of
the shape "produce this artifact from that source", which is the shape a
computer uses for compression, archiving, copying, packing and encryption. A
goal outside that shape gets `NO_ORACLE` and the caller must refuse to learn
from it. Zero model calls, standard library only, and every verdict names the
reader that produced it.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EFFECT_ORACLE_V1"

EFFECT_VERIFIED = "EFFECT_VERIFIED"
WRONG_FORMAT = "WRONG_FORMAT__READER_REFUSED_THE_ARTIFACT"
NO_READER = "NO_READER__FORMAT_HAS_NO_TOOL_ON_THIS_MACHINE"
NOT_A_GOAL = "NOT_A_GOAL__NO_SUCH_ARTIFACT"
NO_ORACLE = "NO_ORACLE__EFFECT_SHAPE_NOT_KNOWN"
SOURCE_MISSING = "SOURCE_MISSING"

# How a suffix names a program. These are naming rules, not format facts:
# the artifact's own name is the only input, and the machine's installed
# programs are the only candidates. A candidate still has to prove itself by
# decoding the artifact back to the source.
_SUFFIX_PROGRAMS = {
    "gz": ("gzip", "pigz"),
    "xz": ("xz", "pxz"),
    "bz2": ("bzip2", "pbzip2"),
    "zst": ("zstd", "pzstd"),
    "lz4": ("lz4",),
    "zip": ("unzip",),
    "7z": ("7z", "7za", "7zr"),
    "z": ("uncompress", "gzip"),
    "lzma": ("xz", "lzma"),
}


def _reader_spec(suffix: str, programs: Sequence[str] | None = None
                 ) -> tuple[str, list[str]] | None:
    """Which installed program can turn `<artifact>.<suffix>` back into bytes."""
    installed = set(programs) if programs is not None else None

    def present(name: str) -> bool:
        return (name in installed) if installed is not None else bool(shutil.which(name))

    for candidate in _SUFFIX_PROGRAMS.get(suffix, ()):
        if present(candidate):
            if candidate in ("unzip", "7z", "7za", "7zr"):
                return candidate, [candidate, "-p", "-q", "-o{out}", "{artifact}"]
            return candidate, [candidate, "-d", "-c", "{artifact}"]
    return None


def _machine_signature(program: str, source: pathlib.Path, scratch: pathlib.Path,
                       timeout_s: float = 20.0) -> bytes | None:
    """What header does THIS machine's compressor write for this format?

    Derived by running it on the source in a scratch room. Nothing here knows
    that gzip writes `1f 8b`; the machine is asked and the answer is compared.
    """
    compressor = {"unzip": "zip", "7z": "7z", "7za": "7za", "7zr": "7zr"}.get(program, program)
    if shutil.which(compressor) is None:
        return None
    try:
        done = subprocess.run([compressor, "-c", str(source)], cwd=str(scratch),
                              capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0 or len(done.stdout) < 4:
        return None
    return done.stdout[:4]


def verify_roundtrip(work_dir: str | pathlib.Path, output_name: str,
                     source_name: str, *, programs: Sequence[str] | None = None,
                     timeout_s: float = 20.0) -> dict[str, Any]:
    """Is `output_name` a correct representation of `source_name`?

    Verified iff the machine's own reader for the output's declared suffix
    returns exactly the source bytes.
    """
    root = pathlib.Path(work_dir)
    output = root / output_name
    source = root / source_name
    if not output.is_file():
        return {"schema": SCHEMA, "verdict": NOT_A_GOAL, "output": output_name,
                "source": source_name}
    if not source.is_file():
        return {"schema": SCHEMA, "verdict": SOURCE_MISSING, "output": output_name,
                "source": source_name}
    wanted = source.read_bytes()
    suffix = output_name.rsplit(".", 1)[-1].lower() if "." in output_name else ""
    spec = _reader_spec(suffix, programs)
    if spec is None:
        # With no declared format there is still one honest check: the artifact
        # must not simply be a copy. A copy is not compression, and calling it
        # one is the same defect one layer down.
        same = output.read_bytes() == wanted
        return {"schema": SCHEMA,
                "verdict": WRONG_FORMAT if same else NO_ORACLE,
                "detail": "suffix %r names no installed reader" % suffix,
                "suffix": suffix, "output": output_name, "source": source_name,
                "bytes_equal_source": same}
    program, shape = spec
    with tempfile.TemporaryDirectory(prefix="brain-signature-") as where:
        scratch = pathlib.Path(where)
        probe = scratch / source.name
        shutil.copy2(source, probe)
        signature = _machine_signature(program, probe, scratch)
    try:
        if "{out}" in " ".join(shape):
            # readers that write a directory (zip family) refuse -c; keep the
            # verdict honest rather than pretending a listing was a decode
            return {"schema": SCHEMA, "verdict": NO_ORACLE,
                    "detail": "reader %r extracts to a directory; round-trip not "
                              "implemented for it" % program,
                    "suffix": suffix, "output": output_name, "source": source_name}
        argv = [program] + [part.replace("{artifact}", output_name) for part in shape[1:]]
        done = subprocess.run(argv, cwd=str(root), capture_output=True,
                              timeout=timeout_s)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"schema": SCHEMA, "verdict": WRONG_FORMAT, "reader": program,
                "detail": repr(error)[:200], "suffix": suffix,
                "output": output_name, "source": source_name}
    head = output.read_bytes()[:4]
    if signature is not None and head[:len(signature)] != signature:
        return {"schema": SCHEMA, "verdict": WRONG_FORMAT, "reader": program,
                "detail": "the artifact's header is not what this machine's %r "
                          "writes for that format" % program,
                "artifact_header": head.hex(), "machine_signature": signature.hex(),
                "suffix": suffix, "output": output_name, "source": source_name}
    if done.returncode != 0:
        return {"schema": SCHEMA, "verdict": WRONG_FORMAT, "reader": program,
                "detail": (done.stderr or b"").decode("utf-8", "replace")[:200],
                "suffix": suffix, "output": output_name, "source": source_name}
    matched = done.stdout == wanted
    return {
        "schema": SCHEMA,
        "verdict": EFFECT_VERIFIED if matched else WRONG_FORMAT,
        "reader": program,
        "reader_argv": argv,
        "suffix": suffix,
        "output": output_name,
        "source": source_name,
        "bytes_decoded": len(done.stdout),
        "bytes_source": len(wanted),
        "bytes_equal_source": bool(matched),
    }


def compress_oracle(source_name: str, output_name: str,
                    programs: Sequence[str] | None = None):
    """A live goal predicate: True only when the effect holds in `env` NOW.

    Shaped for `environment_learning_v1.learn_model(goal_check=...)` and
    `perfect_algorithm_v1.run(goal_check=...)`: it takes the environment, reads
    the world, and answers.
    """
    def check(env: Any) -> bool:
        root = getattr(env, "root", None)
        if root is None:
            return False
        verdict = verify_roundtrip(root, output_name, source_name, programs=programs)
        check.last = verdict  # the reason travels with the answer
        return verdict.get("verdict") == EFFECT_VERIFIED

    check.last = None
    check.describe = lambda: {"source": source_name, "output": output_name,
                              "programs": list(programs or [])}
    return check


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="verify one artifact against its source")
    parser.add_argument("work_dir")
    parser.add_argument("output_name")
    parser.add_argument("source_name")
    args = parser.parse_args(argv)
    print(json.dumps(verify_roundtrip(args.work_dir, args.output_name, args.source_name),
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
