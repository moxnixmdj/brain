"""Scan a host, retrieve what is already known, fetch only what is not.

This is the user's own algorithm, taken literally:

    "scan everything in the environment and then retrieve from his memory what he knows
     and what he doesn't know. What he doesn't know, he should get it instantly"

The previous instruments each did part of this. `cost_to_learn_a_host_v1` swept a host and
relearned it from scratch every time. `compose_a_host_never_seen_v1` read a program's type
from its own help page but asked every program, on every run. Neither had a memory, so
neither could distinguish known from unknown, which means neither could skip anything.

Three findings decide the memory design, and all three were measured:

1. NAMES SHARE BYTES. /usr/bin has 635 names for 481 distinct files. A cache keyed on the
   NAME would store `/usr/bin/xz` eight times.
2. BYTES DO NOT DETERMINE BEHAVIOUR. `/usr/bin/xz` and its `unxz` link are byte-identical
   and behave oppositely: `xz` compresses plain text and `unxz` rejects it. So a cache keyed
   on CONTENT ALONE would answer "this program compresses" for the decompressor. The name
   is an input to the program, not a label on it.
3. THE HELP PAGE IS NOT ALWAYS AT THE TOP. GNU puts the self-description in the first prose
   line; busybox puts a banner and a usage synopsis first and the description on line five,
   with flags described one per line. GNU `gzip --help` describes its transform only in prose
   and never names `-d`; busybox `gzip --help` names `-d` and its prose says only "Compress".
   Neither format alone is sufficient, so both are read.

The key is therefore (content digest, invoked name), and the payload is a type scheme plus
the flags the program's own help associates with each role.

Schema BRAIN_SCAN_RETRIEVE_FETCH_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import select
import signal
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

SCHEMA = "BRAIN_SCAN_RETRIEVE_FETCH_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# Where a memory lives. One JSON file: the thing the user asked to keep, and nothing else.
MEMORY_PATH = pathlib.Path("/tmp/brain_memory/memory.json")
MEMORY_SCHEMA = "BRAIN_HOST_MEMORY_V1"

# The same closed verb classes the host instruments use. These are English, not programs.
CONSTRUCTIVE = ("compress", "uncompress", "decompress", "pack", "encode", "decode")
ROLE_WORDS = {
    "decompress": ("decompress", "uncompress", "decode"),
    "compress": ("compress",),
    "stdout": ("stdout", "standard output", "write to stdout"),
    "keep": ("keep",),
}


# --------------------------------------------------------------------------- scanning
def scan(host: pathlib.Path) -> list[dict[str, Any]]:
    """Every program the host offers, addressed by the two things that predict behaviour.

    Hashing is 3.8 ms/file and probing is 12 ms/program, so the scan is cheap enough to
    run every time. What it must NOT do is re-probe a program it has already learned:
    that is the whole point of the retrieval step.
    """
    rows: list[dict[str, Any]] = []
    for entry in sorted(host.iterdir()):
        if not entry.is_file():
            continue
        try:
            digest = hashlib.sha256(entry.read_bytes()).hexdigest()
        except OSError:
            continue
        rows.append({"name": entry.name, "path": str(entry), "digest": digest,
                     "key": f"{digest[:16]}:{entry.name}"})
    return rows


def scan_multicall(host: pathlib.Path, binary: pathlib.Path) -> list[dict[str, Any]]:
    """A multi-call binary offers hundreds of programs behind one file.

    `busybox --list` is the host naming its own applets, so the names are evidence, and
    the key is (digest of busybox, applet name) exactly as for a normal program.
    """
    try:
        listed = subprocess.run([str(binary), "--list"], capture_output=True,
                                text=True, timeout=20)
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    except (OSError, subprocess.SubprocessError):
        return []
    rows: list[dict[str, Any]] = []
    for applet in listed.stdout.split():
        rows.append({"name": applet, "path": str(binary), "digest": digest,
                     "key": f"{digest[:16]}:{applet}", "via": str(binary)})
    return rows


# --------------------------------------------------------------------------- reading
def ask(row: dict[str, Any], workdir: str, budget: int = 16384,
        deadline: float = 3.0) -> dict[str, Any]:
    """One bounded question to one program, addressed by the name it will be run under.

    `subprocess.run(capture_output=True)` is a trap and it was sprung here: with no byte
    bound it collects whatever the program prints, and an executable that prints forever
    takes the learner down with the OOM killer (exit 137, twice in this repository). The
    budget is not a nicety; it is what makes scanning a foreign host survivable.
    """
    argv = [row.get("via", row["path"])]
    if row.get("via"):
        argv.append(row["name"])
    argv.append(f"--help")
    started = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, cwd=workdir,
                                start_new_session=True)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason": type(exc).__name__, "text": "",
                "seconds": round(time.perf_counter() - started, 4)}
    # Read with a DEADLINE, not with a blocking `read(n)`. A buffered read of n bytes does
    # not return until n bytes arrive, so a program that prints 50 bytes and keeps its
    # stdout open hangs the learner forever. This hung a full 900 s run. The loop below
    # polls with select and keeps whatever arrived when the deadline expires.
    import select as _select
    chunks: list[bytes] = []
    total = 0
    fd = proc.stdout.fileno()
    try:
        while total < budget:
            remaining = deadline - (time.perf_counter() - started)
            if remaining <= 0:
                break
            ready, _, _ = _select.select([fd], [], [], remaining)
            if not ready:
                break
            block = os.read(fd, min(2048, budget - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
    except (OSError, ValueError):
        pass
    finally:
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
    return {"ok": bool(text.strip()), "text": text, "reason": "OK",
            "seconds": round(time.perf_counter() - started, 4)}


def read_type(text: str) -> dict[str, Any] | None:
    """The type the program states about itself, read from wherever it states it.

    GNU and busybox disagree about layout, so the description is not "the first prose line"
    but "the first prose line that names a transform verb", searched down the page. A
    banner, a synopsis, and a copyright block are all skipped because none of them names a
    transform verb. That single change is what makes one rule read both formats.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 8:
            continue
        low = stripped.lower()
        if low.startswith(("usage", "or:", "options", "busybox v", "licensed under",
                           "copyright", "see source", "this program is free")):
            continue
        if "-" in stripped and ("[" in stripped or stripped.startswith("-")):
            continue
        if any(marker in low for marker in cost.NOT_A_DESCRIPTION):
            continue
        transform = cost.transform_of(stripped)
        if transform:
            return {"description": stripped[:200], "transform": transform}
    return None


def read_flag(text: str, role: str) -> str | None:
    """The flag this help page associates with a role, in either layout.

    GNU packs a flag and its description on one line (`-d, --decompress  decompress`).
    busybox puts the description after a tab (`\\t-d\\tDecompress`). Both are a flag and
    words about it, so the rule is the same: find the line mentioning the role, take the
    flag from it, prefer the long form.
    """
    words = ROLE_WORDS.get(role, (role,))
    long_hit = short_hit = None
    for line in text.splitlines():
        low = line.lower()
        if not any(word in low for word in words):
            continue
        for candidate in re.findall(r"--[a-z][a-z0-9-]*", line):
            if long_hit is None:
                long_hit = candidate
        for candidate in re.findall(r"(?<![\w-])-[a-zA-Z](?![\w-])", line):
            if short_hit is None:
                short_hit = candidate
    return long_hit or short_hit


def learn(row: dict[str, Any], workdir: str) -> dict[str, Any] | None:
    """Turn one program's own words into the record that is worth remembering."""
    got = ask(row, workdir)
    if not got["ok"]:
        return None
    typed = read_type(got["text"])
    if not typed:
        return None
    return {"key": row["key"], "name": row["name"], "path": row["path"],
            "digest": row["digest"], "via": row.get("via"),
            "transform": typed["transform"], "description": typed["description"],
            "flags": {role: read_flag(got["text"], role) for role in ROLE_WORDS},
            "help_digest": hashlib.sha256(got["text"].encode()).hexdigest()[:16],
            "learned_seconds": got["seconds"]}


# --------------------------------------------------------------------------- memory
def load_memory(path: pathlib.Path = MEMORY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema": MEMORY_SCHEMA, "entries": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"schema": MEMORY_SCHEMA, "entries": {}}
    if data.get("schema") != MEMORY_SCHEMA:
        return {"schema": MEMORY_SCHEMA, "entries": {}}
    return data


def save_memory(memory: dict[str, Any], path: pathlib.Path = MEMORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=1, sort_keys=True))


def retrieve(memory: dict[str, Any], rows: list[dict[str, Any]]
             ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Split a scan into what is already known and what is not.

    Known means the exact (content, name) pair was learned before. A changed name or a
    changed binary is a miss, because measurements show both change behaviour.
    """
    entries = memory.get("entries", {})
    known: dict[str, dict[str, Any]] = {}
    unknown: list[dict[str, Any]] = []
    for row in rows:
        hit = entries.get(row["key"])
        if hit is not None:
            known[row["name"]] = {**hit, "path": row["path"], "via": row.get("via")}
        else:
            unknown.append(row)
    return known, unknown


# --------------------------------------------------------------------------- composing
def rows_for_algebra(known: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The learned records, expressed as the type schemes the composer already searches."""
    rows: dict[str, Any] = {}
    for name, rec in known.items():
        constructor = re.sub(r"[^A-Z0-9]", "", name.upper())
        schemes: list[dict[str, Any]] = []
        if rec["transform"] in ("compress", "encode"):
            schemes.append({"from": "ANY", "to": f"{constructor}[_]", "polymorphic": True,
                            "why": f"{name} says {rec['transform']!r}"})
            if rec["flags"].get("decompress"):
                schemes.append({"from": constructor, "to": "UNWRAP",
                                "polymorphic": False,
                                "why": f"{name} names {rec['flags']['decompress']}"})
        elif rec["transform"] == "decode":
            schemes.append({"from": constructor, "to": "UNWRAP", "polymorphic": False,
                            "why": f"{name} says 'decode'"})
        else:
            # A program that only PRINTS, LISTS, or SEARCHES does not declare its input
            # type, so it gets an UNTYPED scheme and takes no part in composition.
            #
            # The first version typed these `TEXT -> NAME[TEXT]`, which reads plausible and
            # is a search catastrophe: on a real host 398 of 429 programs landed in that
            # bucket, giving the BFS 398 one-step moves into `X[TEXT]` and 22 wrappers that
            # can re-wrap any of them. A one-hop goal was then buried under 50,000 states
            # and the search ran for 20 s and had to refuse. Declaring what you do not know
            # is cheaper than guessing it.
            schemes.append({"from": "UNTYPED", "to": "UNTYPED", "polymorphic": False,
                            "untyped": True,
                            "why": f"{name} says {rec['transform']!r}, which names no "
                                   f"input type"})
        rows[name] = {"program": name, "path": rec["path"], "schemes": schemes,
                      "roles": rec["flags"], "via": rec.get("via"),
                      "constructor": constructor}
    return rows


PAYLOAD = b"the quick brown fox jumps over the lazy dog\n" * 3


def argv_for(rows: dict[str, Any], name: str, direction: str) -> list[str]:
    row = rows[name]
    head = [row["via"], name] if row.get("via") else [row["path"]]
    if direction == "back":
        flag = row["roles"].get("decompress")
    else:
        flag = row["roles"].get("stdout")
    return head + ([flag] if flag else [])


def run_chain(rows: dict[str, Any], chain: list[str], direction: str, data: bytes,
              workdir: str = "/tmp") -> bytes:
    """One stage at a time, bounded in bytes and time, in a directory we own.

    `subprocess.run(capture_output=True)` on an arbitrary program is how this instrument
    hung for 600 s: a program that copies stdin while also waiting on its own children
    never closes stdout, and the capture never returns. Bounding the read and killing the
    process group are the only things that make an unknown host usable.
    """
    current = data
    for name in chain:
        argv = argv_for(rows, name, direction)
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=workdir,
                                start_new_session=True)
        chunks: list[bytes] = []
        total = 0
        started = time.perf_counter()
        try:
            proc.stdin.write(current)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        fd = proc.stdout.fileno()
        try:
            while total < 8_000_000:
                remaining = 20.0 - (time.perf_counter() - started)
                if remaining <= 0:
                    break
                ready, _, _ = select.select([fd], [], [], remaining)
                if not ready:
                    break
                block = os.read(fd, 65536)
                if not block:
                    break
                chunks.append(block)
                total += len(block)
        finally:
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
        out = b"".join(chunks)
        if not out:
            raise RuntimeError(f"{name} produced nothing")
        current = out
    return current


def prove(rows: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    """Compose, execute, and reverse — using only what the memory recorded.

    The search is deliberately LENIENT and the check is STRICT, which is the opposite of
    what it looks like and is the whole design.

    A "sink" is covered by one program, found by direct lookup, not by search: that is
    O(1) and cannot explode. The expensive part is proving the order *between* programs,
    and that is where a full BFS over a host with 22 wrapping schemes is hopeless — 22
    wrappers each able to re-wrap each other is a combinatorial space with a depth-4 cap
    still inside it. So the search is run with a small state ceiling and is ALLOWED to
    give up; what decides the outcome is the byte-exact round trip, which cannot be
    faked. A search that refuses costs milliseconds; a claim without a round trip costs
    the whole result.
    """
    wraps = sorted({r["program"] for r in rows.values()
                    if any(s.get("from") == "ANY" for s in r["schemes"])})
    proves: list[dict[str, Any]] = []
    for outer in wraps[:limit]:
        # `outer` is a PROGRAM NAME (lowercase) but a TYPE constructor is upper-cased by
        # `rows_for_algebra`. Building the sink from the name produced `base32[TEXT]`
        # while the graph produces `BASE32[TEXT]`, so every search refused and the
        # instrument reported zero compositions on a host where six round trips work.
        # A sink is a TYPE, so it comes from the type, never from the name.
        constructor = rows[outer].get("constructor") or re.sub(r"[^A-Z0-9]", "", outer.upper())
        sink = f"{constructor}[TEXT]"
        wraps_of = [n for n, r in rows.items()
                    if any(sc.get("to", "").startswith(f"{constructor}[")
                           for sc in r["schemes"])]
        if wraps_of:
            found = {"found": True, "chain": [wraps_of[0]],
                     "reason": "DIRECT: one program covers this sink"}
        else:
            found = algebra.find_path(rows, "TEXT", sink, max_states=2000)
        if not found["found"]:
            proves.append({"sink": sink, "chain": [], "ok": False,
                           "reason": "no route: " + found.get("reason", "")[:100]})
            continue
        back = algebra.invert(found["chain"], rows, sink, "TEXT", )
        try:
            forward = run_chain(rows, found["chain"], "forward", PAYLOAD)
            exact = (back["found"]
                     and run_chain(rows, back["chain"], "back", forward) == PAYLOAD)
        except (RuntimeError, OSError) as exc:
            proves.append({"sink": sink, "chain": found["chain"],
                           "ok": False, "reason": str(exc)[:120]})
            continue
        proves.append({"sink": sink, "chain": found["chain"],
                       "inverse": back["chain"], "final_bytes": len(forward),
                       "source_bytes": len(PAYLOAD), "ok": bool(exact)})
    return proves


# --------------------------------------------------------------------------- the loop
def visit(host: pathlib.Path, memory_path: pathlib.Path = MEMORY_PATH,
          multicall: pathlib.Path | None = None) -> dict[str, Any]:
    """One pass of the user's algorithm over one host."""
    started = time.perf_counter()
    workdir = tempfile.mkdtemp(prefix="scan-retrieve-fetch-")
    try:
        rows = scan(host)
        if multicall and multicall.exists():
            rows += scan_multicall(host, multicall)
        memory = load_memory(memory_path)
        known, unknown = retrieve(memory, rows)

        fetched: list[dict[str, Any]] = []
        unreadable = 0
        for row in unknown:
            record = learn(row, workdir)
            if record is None:
                unreadable += 1
                continue
            memory["entries"][record["key"]] = record
            fetched.append(record)
        save_memory(memory, memory_path)

        learned = {**{k: v for k, v in known.items()},
                   **{r["name"]: r for r in fetched}}
        typed = rows_for_algebra(learned)
        proofs = prove(typed)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    elapsed = round(time.perf_counter() - started, 3)
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "host": str(host),
        "programs_on_host": len(rows),
        "known_from_memory": len(known),
        "unknown_probed": len(unknown),
        "unreadable": unreadable,
        "newly_learned": len(fetched),
        "memory_entries": len(memory["entries"]),
        "typed_after_visit": len(typed),
        "compositions_proved": sum(1 for p in proofs if p["ok"]),
        "compositions": proofs,
        "seconds": elapsed,
        "cost_zeros": {"model_calls": 0, "network_calls": 0, "parameters_stored": 0},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="/usr/bin")
    parser.add_argument("--multicall", default=None,
                        help="a multi-call binary whose applets are also programs")
    parser.add_argument("--memory", type=pathlib.Path, default=MEMORY_PATH)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.reset and args.memory.exists():
        args.memory.unlink()
    report = visit(pathlib.Path(args.host), args.memory,
                   pathlib.Path(args.multicall) if args.multicall else None)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=1))
    if not args.quiet:
        print(json.dumps({k: report[k] for k in
                          ("programs_on_host", "known_from_memory", "unknown_probed",
                           "newly_learned", "unreadable", "typed_after_visit",
                           "compositions_proved", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
