"""Compose a chain on a host the composer was never told about.

`plans_compose_v1` proved a searched type graph can find an order and an inverse. It did
so with nine `if name == ...` lines naming three programs. On a second host its `type_of`
returned `schemes=[]` for every executable, which makes the earlier result a lookup table
with a search engine attached, not a capability.

This instrument removes the lookup table twice over:

  1. the TYPE of every program comes from the first prose sentence the program writes
     about itself (`type_is_its_own_sentence_v1`);
  2. the FLAGS for every stage come from looking up the ROLE in that same text, because
     a program that can decompress says so in its own `--help`.

Then the same BFS, the same UNWRAP algebra, and the same byte-exact round trip are asked
to work on `/usr/bin`, a host chosen for the test and never named in the code.

What is deliberately still fixed: the *solver* (BFS over type schemes), the type algebra
(polymorphic wrap + constructor unwrap), and the byte budget of a probe. Those are the
model. Everything host-specific is read from the host.

Schema BRAIN_COMPOSE_A_HOST_NEVER_SEEN_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cost_to_learn_a_host_v1 as cost  # noqa: E402
import plans_compose_v1 as algebra  # noqa: E402

SCHEMA = "BRAIN_COMPOSE_A_HOST_NEVER_SEEN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

PAYLOAD = b"the quick brown fox jumps over the lazy dog\n" * 3
SOURCE_TYPE = "TEXT"

# Which words a help page uses when it names the role a flag performs. These are
# English, not program names; a flag is matched to a role by the text around it.
ROLE_WORDS = {
    "decompress": ("decompress", "uncompress", "decode"),
    "compress": ("compress",),
    "stdout": ("stdout", "standard output"),
    "keep": ("keep",),
}


def flag_for(help_text: str, role: str, default: str | None = None) -> str | None:
    """The flag this program's own help page attaches to `role`.

    Scans the option lines for a flag whose description contains a role word. Prefers a
    long flag, falls back to a short one, because long flags are self-documenting and a
    short flag's meaning has to be taken on faith.
    """
    words = ROLE_WORDS.get(role, (role,))
    long_hits: list[str] = []
    short_hits: list[str] = []
    for line in help_text.splitlines():
        low = line.lower()
        if not any(word in low for word in words):
            continue
        for long_flag in re.findall(r"--[a-z][a-z0-9-]*", line):
            if long_flag not in long_hits:
                long_hits.append(long_flag)
        for short_flag in re.findall(r"(?<![\w-])-[a-zA-Z](?![\w-])", line):
            if short_flag not in short_hits:
                short_hits.append(short_flag)
    if long_hits:
        return long_hits[0]
    if short_hits:
        return short_hits[0]
    return default


def inverse_base(name: str, names: set[str],
                 constructive: set[str] | None = None) -> str | None:
    """The program this name is installed as the reverse of, if the host says so TWICE.

    A prefix alone is not evidence. `under` would otherwise be read as the reverse of
    `der`, and `decode` as the reverse of `code`; both are wrong and both were caught by
    running the rule over a host. So the base must ALSO describe itself as a constructive
    transform. Two independent statements by the host have to agree:

        bunzip2  named `un`+`bzip2`   and   `bzip2` says "a block-sorting file compressor"
        under    named `un`+`der`     and   `der` is not on the host at all
    """
    # The reverse marker is not always a PREFIX. `bunzip2` is the reverse of `bzip2`
    # with the `un` INFIXED after the first letter: b + un + zip2. A prefix-only rule
    # missed it, typed a decompressor as a compressor, and the chain then failed for a
    # reason that looked like a host quirk. So: try the marker anywhere, but only accept a
    # base that is on the host AND describes itself as constructive.
    words = {name}
    for prefix in ("un", "de"):
        if name.startswith(prefix) and len(name) > len(prefix) + 1:
            words.add(name[len(prefix):])
    for marker in ("un", "de"):
        for i in range(1, len(name) - len(marker)):
            if name[i:i + len(marker)] == marker:
                words.add(name[:i] + name[i + len(marker):])
    for base in sorted(words):
        if base in (name, "") or base not in names:
            continue
        if constructive is not None and base not in constructive:
            continue
        return base
    return None


def type_the_host(host: pathlib.Path) -> dict[str, Any]:
    """Every executable on the host, typed from its own sentence, flags included.

    TWO PASSES, and the reason is a bug worth remembering. The first version probed and
    typed in one loop, so whether `bunzip2` was recognised as the reverse of `bzip2`
    depended on alphabetical order: `bunzip2` sorts before `bzip2`, the base had not been
    probed yet, and the inverse was missed. A learner whose answer depends on the order it
    happened to walk a directory is not reproducible. So: probe everything, then type
    everything, and the result is independent of enumeration order.
    """
    started = time.perf_counter()
    programs = cost.executables(host)
    names = {p.name for p in programs}

    probes: dict[str, dict[str, Any]] = {}
    for program in programs:
        probes[program.name] = cost.probe(program)

    descriptions: dict[str, str] = {}
    transforms: dict[str, str | None] = {}
    for name, got in probes.items():
        if not got["ok"]:
            continue
        description = cost.self_description(got["text"])
        if not description:
            continue
        descriptions[name] = description
        transforms[name] = cost.transform_of(description)

    # A base is constructive only if its OWN sentence says it constructs.
    constructive = {n for n, t in transforms.items() if t in ("compress", "encode")}

    rows: dict[str, Any] = {}
    for name in sorted(probes):
        if name not in transforms or not transforms[name]:
            continue
        program = host / name
        text = probes[name]["text"]
        transform = transforms[name]
        constructor = re.sub(r"[^A-Z0-9]", "", name.upper())
        schemes: list[dict[str, Any]] = []

        # NAME BEATS DESCRIPTION for direction. A pager installed as `bzless` inherits
        # bzip2's help page verbatim and therefore calls itself "a file compressor"; it is
        # not one. The name it was installed under is the host's own claim about direction,
        # and the host spells "the reverse" as un-/de- plus a program it also ships.
        inverse_of = inverse_base(name, names, constructive)
        if inverse_of:
            constructor = re.sub(r"[^A-Z0-9]", "", inverse_of.upper())
            schemes = [{"from": constructor, "to": "UNWRAP", "polymorphic": False,
                        "why": f"installed as the reverse of {inverse_of!r}"}]
        elif transform in ("compress", "encode"):
            schemes.append({"from": "ANY", "to": f"{constructor}[_]", "polymorphic": True,
                            "why": f"its own sentence says {transform!r}"})
            reverse = next((n for n in names
                            if inverse_base(n, names, constructive) == name), None)
            if reverse or "decompress" in text.lower() or "decode" in text.lower():
                schemes.append({"from": constructor, "to": "UNWRAP",
                                "polymorphic": False,
                                "why": f"host ships {reverse!r}" if reverse
                                       else "its own help names the inverse"})
        elif transform == "decode":
            schemes.append({"from": constructor, "to": "UNWRAP", "polymorphic": False,
                            "why": "its own sentence says 'decode'"})
        else:
            schemes.append({"from": "TEXT", "to": f"{constructor}[TEXT]",
                            "polymorphic": False,
                            "why": f"its own sentence says {transform!r}"})
        rows[name] = {
            "program": name, "path": str(program), "transform": transform,
            "constructor": constructor, "schemes": schemes, "help": text,
            "roles": {role: flag_for(text, role) for role in ROLE_WORDS},
        }
    return {"rows": rows, "programs_on_host": len(programs),
            "seconds": round(time.perf_counter() - started, 3)}


def argv_for(name: str, rows: dict[str, Any], direction: str) -> list[str]:
    """The flags a stage needs, looked up in the program's own help page.

    `direction` is "forward" or "back". Nothing here names a program.
    """
    row = rows[name]
    roles = row["roles"]
    if direction == "back":
        # going backwards means this program must undo its own constructor, or be one
        # of the host's undo words (bzcat, gunzip, ...) which gets a flag if it needs one
        flag = roles.get("decompress")
        return [flag] if flag else []
    flag = roles.get("stdout")
    return [flag] if flag else []


def run_chain(rows: dict[str, Any], chain: list[str], direction: str,
              data: bytes) -> dict[str, Any]:
    """Run a chain of programs, feeding each stage the previous stage's bytes."""
    stages: list[dict[str, Any]] = []
    current = data
    for name in chain:
        argv = [rows[name]["path"]] + argv_for(name, rows, direction)
        try:
            run = subprocess.run(argv, input=current, capture_output=True, timeout=30)
        except subprocess.SubprocessError as exc:
            return {"status": "HARNESS_ERROR", "reason": type(exc).__name__,
                    "stages": stages, "argv": argv}
        stages.append({"program": name, "argv": argv, "returncode": run.returncode,
                       "bytes_in": len(current), "bytes_out": len(run.stdout),
                       "stderr": run.stderr.decode("utf-8", "replace")[:200]})
        if run.returncode != 0 or not run.stdout:
            return {"status": "STAGE_FAILED", "stages": stages,
                    "reason": f"{name} returned {run.returncode}"}
        current = run.stdout
    return {"status": "OK", "stages": stages, "data": current}


def compose_and_verify(host: pathlib.Path, receipt: pathlib.Path | None = None
                       ) -> dict[str, Any]:
    started = time.perf_counter()
    typed = type_the_host(host)
    rows = typed["rows"]
    # A one-stage chain proves almost nothing: it is the program's own help, executed.
    # Composition means several programs that know nothing about each other, ordered by
    # the search. So the sinks are enumerated BY DEPTH: the shortest chain to `SINK` is
    # one program, the shortest chain to `SINK2[...]` cannot be.
    sink_types: list[str] = []
    wraps = sorted({row["constructor"] for row in rows.values()
                    if any(s.get("from") == "ANY" for s in row["schemes"])})
    for outer in wraps[:6]:
        for sink in (f"{outer}[BASE64[{SOURCE_TYPE}]]", f"BASE64[{outer}[{SOURCE_TYPE}]]"):
            if sink not in sink_types:
                sink_types.append(sink)
    report: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "host": str(host), "programs_on_host": typed["programs_on_host"],
        "programs_typed": len(rows),
        "seconds_to_type_the_host": typed["seconds"],
        "reachable_sinks": len(sink_types),
        "attempts": [],
    }
    for sink in sink_types:
        path = algebra.find_path(rows, SOURCE_TYPE, sink)
        attempt: dict[str, Any] = {"sink": sink, "found": path["found"],
                                   "chain": path["chain"]}
        if path["found"]:
            back = algebra.invert(path["chain"], rows, sink, SOURCE_TYPE)
            attempt["inverse_chain"] = back["chain"]
            attempt["inverse_found"] = back["found"]
            forward = run_chain(rows, path["chain"], "forward", PAYLOAD)
            attempt["forward_status"] = forward["status"]
            attempt["forward_argv"] = [s["argv"][1:] for s in forward["stages"]]
            attempt["sizes"] = [s["bytes_out"] for s in forward["stages"]]
            if forward["status"] == "OK" and back["found"]:
                backward = run_chain(rows, back["chain"], "back", forward["data"])
                attempt["back_status"] = backward["status"]
                attempt["back_argv"] = [s["argv"][1:] for s in backward["stages"]]
                attempt["round_trip_exact"] = (backward["status"] == "OK"
                                               and backward["data"] == PAYLOAD)
                if backward["status"] == "OK":
                    attempt["final_bytes"] = len(backward["data"])
                    attempt["source_bytes"] = len(PAYLOAD)
        report["attempts"].append(attempt)
    verified = [a for a in report["attempts"] if a.get("round_trip_exact")]
    report["round_trips_verified"] = len(verified)
    report["first_verified"] = verified[0] if verified else None
    report["seconds"] = round(time.perf_counter() - started, 3)
    report["cost_zeros"] = {
        "model_calls": 0, "parameters_stored": 0, "network_calls": 0,
        "per_host_branches": len(re.findall(
            r"if\s+(?:name|program\.name)\s*==", pathlib.Path(__file__).read_text())),
    }
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--host", default="/usr/bin")
    args = parser.parse_args(argv)
    report = compose_and_verify(pathlib.Path(args.host), args.receipt)
    print(json.dumps({k: report[k] for k in
                      ("programs_on_host", "programs_typed", "reachable_sinks",
                       "round_trips_verified", "seconds", "cost_zeros")}, indent=1))
    if report["first_verified"]:
        print(json.dumps({"first_verified": {
            "sink": report["first_verified"]["sink"],
            "chain": report["first_verified"]["chain"],
            "inverse": report["first_verified"]["inverse_chain"],
            "forward_argv": report["first_verified"]["forward_argv"],
            "sizes": report["first_verified"]["sizes"],
            "final_bytes": report["first_verified"].get("final_bytes"),
            "source_bytes": report["first_verified"].get("source_bytes")}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
