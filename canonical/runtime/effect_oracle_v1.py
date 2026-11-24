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

# THERE IS NO FORMAT TABLE HERE. Measured 2026-11-24: a table of suffix ->
# program (`gz` -> `gzip`) is memorised world knowledge wearing the costume of a
# derivation, and it breaks on the first compound name (`out.tar.gz` names two
# programs in order, and no single word matches either). What replaces it:
#
#   * CANDIDATES come from the machine's own naming -- `computer_env_v1.programs_for`
#     returns installed programs whose name is a subsequence of the suffix, and
#     each candidate is only a guess;
#   * a candidate becomes a READER only by PROOF: it encodes a scratch copy of
#     the source and decodes its own output back to exactly those bytes, in a
#     scratch room. A guess that cannot prove itself is never used;
#   * a compound suffix is a CHAIN, decoded right to left (`.tar.gz` = gzip of
#     tar of the source), with every link proven separately.


def _components(output_name: str) -> list[str]:
    if "." not in output_name:
        return []
    return [c for c in output_name.split(".", 1)[1].lower().split(".")
            if any(ch.isalnum() for ch in c)]


def _encode_shapes(program: str, source: pathlib.Path) -> list[list[str]]:
    return [[program, "-c", str(source)],
            [program, "-cf", "-", source.name],
            [program, "-c", "-f", "-", source.name]]


def _decode_shapes(program: str) -> list[list[str]]:
    return [[program, "-dc"], [program, "-d", "-c"],
            [program, "-xOf", "-"], [program, "-xO", "-f", "-"]]


def _run(argv: list[str], *, cwd: pathlib.Path, stdin: bytes | None = None,
         timeout_s: float = 20.0):
    return subprocess.run(argv, cwd=str(cwd), capture_output=True,
                          input=stdin if stdin is not None else b"",
                          timeout=timeout_s)


def prove_reader(program: str, source: pathlib.Path, scratch: pathlib.Path,
                 timeout_s: float = 20.0) -> dict[str, Any] | None:
    """Can this program carry the source out and bring it back unchanged?

    Proven on a scratch copy, never on the artifact being judged: a reader that
    cannot round-trip the source is not a reader for this format.
    """
    wanted = source.read_bytes()
    for shape in _encode_shapes(program, source):
        try:
            encoded = _run(shape, cwd=scratch, timeout_s=timeout_s)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if encoded.returncode != 0 or len(encoded.stdout) < 4:
            continue
        for decode in _decode_shapes(program):
            try:
                back = _run(decode, cwd=scratch, stdin=encoded.stdout,
                            timeout_s=timeout_s)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if back.returncode == 0 and back.stdout == wanted:
                return {"program": program, "encode": shape, "decode": decode,
                        "signature": _invariant_header(program, wanted, encoded.stdout,
                                                       scratch, timeout_s),
                        "encoded_bytes": len(encoded.stdout)}
    return None


def _invariant_header(program: str, source_bytes: bytes, first: bytes,
                      scratch: pathlib.Path, timeout_s: float) -> bytes:
    """The part of an encoder's output that identifies the FORMAT, derived.

    Measured 2026-11-24: a fixed 4-byte signature rejected a real `.tar.gz`
    because `gzip -c file` writes the original name into byte 4 (0x08) while
    `tar -czf -` pipes to gzip, which does not (0x00). Byte 4 is an OPTION, not
    the format. So the invariant is what stays the same when the same encoder is
    invoked two different ways -- the file named, and the bytes piped in -- and
    the answer is computed on this machine, not remembered. When nothing is
    invariant (tar's header is the member's own name), the result is empty and
    the round trip alone carries the proof.
    """
    second = None
    for shape in ([program], [program, "-c"], [program, "-cf", "-", "."]):
        try:
            done = _run(shape, cwd=scratch, stdin=source_bytes, timeout_s=timeout_s)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if done.returncode == 0 and done.stdout and done.stdout != first:
            second = done.stdout
            break
    if second is None:
        return first[:4]
    limit = min(len(first), len(second), 8)
    keep = 0
    while keep < limit and first[keep] == second[keep]:
        keep += 1
    return first[:keep]


_MAX_CANDIDATES = 8


def _candidates(component: str, programs: Sequence[str] | None) -> list[str]:
    """Shortlist, cheapest guess first; the proof decides, not the order.

    A subsequence match over the whole of PATH returns 24 names for a nonsense
    suffix, and proving each one costs subprocesses. The list is therefore
    ordered (a name that literally contains the component first) and bounded --
    the cap can only lose a reader, never manufacture one, and the receipt says
    NO_READER rather than guessing.
    """
    if programs is not None:
        # A caller-supplied list is a hint about which programs EXIST, never a
        # licence for one of them to stand in for another layer. Measured
        # 2026-11-24: with ["tar", "gzip"] handed in, `tar` proved itself as the
        # reader for `gz` (tar -xOf returns the source bytes), so a plain tar
        # named out.gz came back EFFECT_VERIFIED. Filter per layer; if nothing
        # is named for this layer, the honest answer is that there is no reader.
        named = [str(p) for p in programs if component in str(p)]
        if named:
            return named
        try:
            from canonical.runtime.computer_env_v1 import programs_for

            return list(programs_for(component, limit=_MAX_CANDIDATES))
        except Exception:  # noqa: BLE001
            return []
    try:
        from canonical.runtime.computer_env_v1 import programs_for

        found = list(programs_for(component, limit=24))
    except Exception:  # noqa: BLE001 - no index is a smaller candidate set, not a pass
        return []
    literal = [p for p in found if component in p]
    rest = [p for p in found if p not in literal]
    return (literal + rest)[:_MAX_CANDIDATES]


def prove_layer(program: str, component: str, source: pathlib.Path,
                scratch: pathlib.Path, timeout_s: float = 20.0) -> dict[str, Any]:
    """Is this program the machine's implementation of THIS layer?

    Measured 2026-11-24: matching a layer to a program by name (`gz` in `gzip`)
    is pattern matching, and it is wrong in both directions -- an alias called
    `zpack` that really is gzip gets no match, and generous name matching let
    `tar` stand in for `gz` elsewhere. So the match is made by behaviour: the
    program must encode the source, decode its own artifact back to the same
    bytes, and -- when the layer's format has an invariant header at all -- write
    that header. `tar`'s invariant is empty, so the round trip carries it alone.
    """
    import shutil
    import tempfile

    if not shutil.which(program):
        return {"proved": False, "reason": "NOT_INSTALLED", "program": program}
    with tempfile.TemporaryDirectory(prefix="layer-proof-") as room:
        room_path = pathlib.Path(room)
        subject = room_path / source.name
        subject.write_bytes(source.read_bytes())
        known = resolve_chain("probe." + component, subject, room_path,
                              programs=None)
        signature = b""
        if known.get("verdict") == "READER_CHAIN_PROVEN" and known.get("links"):
            signature = known["links"][0].get("signature") or b""
        for argv in _encode_shapes(program, subject):
            done = _run(argv, cwd=room_path, timeout_s=timeout_s)
            if done.returncode != 0 or not done.stdout:
                continue
            artifact = done.stdout
            if signature and not artifact.startswith(signature):
                return {"proved": False, "program": program, "component": component,
                        "reason": "THE_ARTIFACT_IS_NOT_THIS_FORMAT",
                        "artifact": artifact[:8].hex(), "signature": signature.hex()}
            for decode in _decode_shapes(program):
                back = _run(decode, cwd=room_path, stdin=artifact, timeout_s=timeout_s)
                if back.returncode == 0 and back.stdout == subject.read_bytes():
                    return {"proved": True, "program": program, "component": component,
                            "encode": argv, "decode": decode,
                            "signature": signature.hex()}
    return {"proved": False, "program": program, "component": component,
            "reason": "NO_ROUND_TRIP"}


def resolve_chain(output_name: str, source: pathlib.Path, scratch: pathlib.Path,
                  *, programs: Sequence[str] | None = None) -> dict[str, Any]:
    """The proof-carrying reader chain for this output name, or the reason there is none.

    The chain is returned in DECODE order (outermost first): for `out.tar.gz`
    that is [gzip, tar] -- the gzip is undone first because it was done last.
    """
    components = _components(output_name)
    if not components:
        return {"verdict": NO_READER, "detail": "the output name declares no format",
                "components": []}
    links: list[dict[str, Any]] = []
    for component in reversed(components):          # outermost layer was applied last
        proven = None
        for candidate in _candidates(component, programs):
            proven = prove_reader(candidate, source, scratch)
            if proven is not None:
                proven["component"] = component
                break
        if proven is None:
            return {"verdict": NO_READER, "component": component,
                    "components": components,
                    "detail": "no installed program named for %r could carry the "
                              "source out and bring it back" % component}
        links.append(proven)
    return {"verdict": "READER_CHAIN_PROVEN", "links": links,
            "components": components,
            "chain": [link["program"] for link in links],
            "signature": links[0]["signature"]}


def verify_roundtrip(work_dir: str | pathlib.Path, output_name: str,
                     source_name: str, *, programs: Sequence[str] | None = None,
                     timeout_s: float = 20.0) -> dict[str, Any]:
    """Is `output_name` a correct representation of `source_name`?

    Three checks, in this order, and every one of them is derived from the
    machine rather than remembered:

      1. the artifact's header must be what this machine's own encoder writes
         for the format the name declares (a liberal reader is not proof);
      2. every layer the name declares must have a PROVEN reader (it carried a
         scratch copy of the source out and brought it back unchanged);
      3. undoing the layers, outermost first, must return exactly the source
         bytes.

    `.tar.gz` is therefore two layers with two proofs, not one suffix with a
    guess. A name whose format has no provable reader yields NO_READER -- an
    explicit refusal, never a pass.
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
    components = _components(output_name)
    with tempfile.TemporaryDirectory(prefix="brain-reader-proof-") as where:
        scratch = pathlib.Path(where)
        probe = scratch / source.name
        shutil.copy2(source, probe)
        chain = resolve_chain(output_name, probe, scratch, programs=programs)
    if chain["verdict"] != "READER_CHAIN_PROVEN":
        same = output.read_bytes() == wanted
        # a byte-for-byte copy is never what a declared format produces, so the
        # copy case keeps its own verdict instead of dissolving into NO_READER
        if same:
            verdict = WRONG_FORMAT
        elif components:
            verdict = NO_READER
        else:
            verdict = NO_ORACLE
        return {"schema": SCHEMA, "verdict": verdict,
                "detail": chain.get("detail"), "components": components,
                "output": output_name, "source": source_name,
                "bytes_equal_source": same}

    head = output.read_bytes()[:8]
    signature = chain["signature"]
    if signature and head[:len(signature)] != signature:
        return {"schema": SCHEMA, "verdict": WRONG_FORMAT, "reader": chain["chain"][0],
                "detail": "the artifact's header is not what this machine writes "
                          "for that format",
                "artifact_header": head.hex(), "machine_signature": signature.hex(),
                "components": components, "output": output_name,
                "source": source_name}

    data = output.read_bytes()
    applied: list[list[str]] = []
    for link in chain["links"]:
        argv = list(link["decode"])
        try:
            done = _run(argv, cwd=root, stdin=data, timeout_s=timeout_s)
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"schema": SCHEMA, "verdict": WRONG_FORMAT,
                    "reader": link["program"], "detail": repr(error)[:200],
                    "components": components, "output": output_name,
                    "source": source_name}
        applied.append(argv)
        if done.returncode != 0:
            return {"schema": SCHEMA, "verdict": WRONG_FORMAT,
                    "reader": link["program"],
                    "detail": (done.stderr or b"").decode("utf-8", "replace")[:200],
                    "components": components, "output": output_name,
                    "source": source_name}
        data = done.stdout
    matched = data == wanted
    return {
        "schema": SCHEMA,
        "verdict": EFFECT_VERIFIED if matched else WRONG_FORMAT,
        "reader": chain["chain"][-1] if len(chain["chain"]) == 1 else chain["chain"],
        "reader_chain": chain["chain"],
        "reader_argv": applied,
        "components": components,
        "output": output_name,
        "source": source_name,
        "bytes_decoded": len(data),
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


def _mentioned(goal: str) -> list[str]:
    """Names the instruction actually says, kept whole (dots and dashes included)."""
    import re

    return [m.group(0) for m in re.finditer(r"[A-Za-z0-9_.-]*[A-Za-z0-9_][A-Za-z0-9_.-]*",
                                            str(goal or ""))]


def oracle_from_goal(goal: str, *, programs: Sequence[str] | None = None):
    """The whole contract, derived from the instruction and the observation.

    This is the hand-holding remover. The caller supplies a sentence; nothing
    else. The output name is read from the sentence (`into out.gz`), the source
    is read from the world (a file the sentence names, else the only file that
    is not the output), and the effect is the proven round trip. When the
    sentence does not determine the output, or the world does not determine the
    source, this returns None and the caller must not learn -- an instruction
    that can be read two ways is not a specification.

    The returned object is a live predicate for `learn_model(goal_check=...)`
    and `perfect_algorithm_v1.run(goal_check=...)`, and carries `.contract(env)`
    for the operator that gets lifted.
    """
    try:
        from canonical.runtime.computer_env_v1 import output_name as _output_name

        output = _output_name(goal)
    except Exception:  # noqa: BLE001 - no parser is a refusal, not a guess
        output = None
    if not output:
        return None

    def _bind(env: Any) -> dict[str, Any]:
        root = getattr(env, "root", None)
        if root is None:
            return {"source": None, "reason": "this environment exposes no files"}
        base = pathlib.Path(str(root))
        try:
            files = sorted(p.name for p in base.iterdir() if p.is_file())
        except OSError:
            return {"source": None, "reason": "the environment's files are unreadable"}
        candidates = [name for name in files if name != output]
        for word in _mentioned(goal):
            if word in candidates:
                return {"source": word, "reason": "the instruction names it",
                        "files": files}
        if len(candidates) == 1:
            return {"source": candidates[0],
                    "reason": "the only file here that is not the output",
                    "files": files}
        if not candidates:
            return {"source": None, "reason": "there is no input file here",
                    "files": files}
        return {"source": None,
                "reason": "%d candidate inputs (%s); the instruction does not say "
                          "which" % (len(candidates), ", ".join(candidates[:4])),
                "files": files}

    def check(env: Any) -> bool:
        bound = _bind(env)
        if not bound.get("source"):
            check.last = {"verdict": "REFUSED__SOURCE_NOT_DETERMINED",
                          "detail": bound.get("reason"), "binding": bound,
                          "output": output}
            return False
        verdict = verify_roundtrip(getattr(env, "root"), output, bound["source"],
                                   programs=programs)
        verdict["binding"] = bound
        check.last = verdict
        return verdict.get("verdict") == EFFECT_VERIFIED

    def contract(env: Any) -> dict[str, Any] | None:
        bound = _bind(env)
        if not bound.get("source"):
            return None
        return {"source": bound["source"], "output": output}

    check.last = None
    check.output = output
    check.contract = contract
    check.describe = lambda: {"goal": str(goal)[:200], "output": output,
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
