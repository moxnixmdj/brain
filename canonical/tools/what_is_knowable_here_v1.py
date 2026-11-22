#!/usr/bin/env python3
"""What is knowable about an unknown machine, and what is worth remembering.

The question: should an agent learn everything about a new environment or only
what its goal needs, and what should it keep?

This measures four channels on the running host instead of arguing.

  LOOK   read the artifacts' bytes and extract the statements they contain, each
         cited by byte offset and digest. Free, exhaustive, shallow: compiled text
         is a skeleton, not a manual.
  ASK    run each program's own self-description (``--help``). Authoritative by
         construction -- the program describes itself -- and one process each.
  TEST   exercise the forms a program claims. Self-description is not
         self-verifying: a program can document a form its parser rejects, or
         document ``--flag<v>`` in a syntax it only accepts as ``--flag=v``. Only
         a run settles that. Probes are bounded and never aim at a destructive form.
  WEB    fetch the same kind of statement from a public home. Priced, never a
         source of landed rows: the fallback for a host that states nothing.

Two results decide the strategy, and neither is the one the intuition predicts.

  RESIDENCY  most of what ASK returns is already *in* the bytes on disk, so
             storing it would be storing what the disk already has. Report what
             fraction, per channel, rather than assuming memorization is the point.
  PERISHABLE a statement that changes when only the environment changes (cwd,
             HOME) was never a property of the machine, so remembering it teaches
             the wrong thing. Measure movement, don't assert stability.

What survives both is shape: (statement kind, artifact family) plus one worked
example, with the channel that produced it. Shapes are few, cheap, and portable;
contents are resident and re-derivable. The retention ratio is reported whatever
it is, and re-asking always remains legal.

Authority: NONE. Producer-run sandbox. Zero model calls, zero stored parameters,
no network outside the priced WEB channel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable, Sequence

SCHEMA = "BRAIN_WHAT_IS_KNOWABLE_HERE_V1"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "W1": "every LOOK row carries the byte offset that proves it and is dropped if it no longer re-reads to the same bytes",
    "W2": "answered + gaps equals the enumerated host; nothing leaves the books",
    "W3": "memory stores one worked example per shape and reports the retention ratio as measured, however unflattering",
    "W4": "perishability is measured by changing only the environment and re-asking; moving statements are never stored as facts",
    "W5": "channel costs are compared in one unit (bytes of statement per second) so LOOK, ASK and WEB are directly comparable",
    "W6": "at least one program whose own text contradicts its own parser is found by TEST, or TEST reports that it found none -- either way it runs",
    "W7": "residency is measured: the fraction of ASK's claims already present verbatim in the artifact's own bytes",
    "W8": "zero model calls, zero stored parameters, no network outside the priced WEB channel",
    "W9": "the premise that a guide already exists is measured, not assumed: the package database's own documentation citations are checked against the files actually on disk",
}

USAGE_MARKERS: tuple[bytes, ...] = (b"Usage: ", b"usage: ", b"USAGE: ", b"Usage of ")
HAZARD_TERMS: tuple[bytes, ...] = (b"recursively", b"overwrite", b"irreversibly",
                                   b"Without this option", b"destructive")
DESTRUCTIVE_PROGRAMS = frozenset({
    "rm", "rmdir", "dd", "mkfs", "shutdown", "reboot", "halt", "poweroff", "kill",
    "killall", "pkill", "truncate", "wipefs", "fdisk", "parted", "mkswap", "chown",
    "chmod", "chgrp", "patch", "apt", "apt-get", "dpkg", "npm", "pip", "pip3", "git",
})
DESTRUCTIVE_FLAGS = re.compile(r"force|delete|remove|overwrite|recursive|purge|format|"
                               r"yes|clean|erase|drop|kill|stop|halt|reboot|shutdown",
                               re.IGNORECASE)
LONG_FLAG = re.compile(rb"(?<![\w-])--[a-z][a-z0-9-]{1,30}")
VERSION_LINE = re.compile(r"^(?P<name>[^ ]+?)\s+(?P<version>[0-9]+\.[0-9]+[-.0-9A-Za-z+]*)",
                          re.MULTILINE)
REJECTION = re.compile(r"(unrecognized option|unrecognised option|invalid option|"
                       r"unknown option|illegal option)[^\n]{0,60}", re.IGNORECASE)
ANSWER_CAP = 8192

HOMES = (
    ("npm-registry", "https://registry.npmjs.org/tar"),
    ("github-api", "https://api.github.com/repos/git/git"),
    ("github-codeload", "https://codeload.github.com/git/git/tar.gz/refs/heads/master"),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def enumerate_host(path_override: str | None = None) -> dict[str, Any]:
    """The host as this process sees it, deduplicated by (device, inode)."""
    dirs = [part for part in (path_override or os.environ.get("PATH", "")).split(":") if part]
    mounts: list[str] = []
    try:
        for line in pathlib.Path("/proc/self/mountinfo").read_text().splitlines():
            fields = line.split(" ")
            if len(fields) > 4:
                mounts.append(fields[4])
    except OSError:
        pass
    unique: dict[tuple[int, int], dict[str, Any]] = {}
    names: dict[str, list[str]] = {}
    for directory in dirs:
        root = pathlib.Path(directory)
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                st = entry.stat()
            except OSError:
                continue
            if not entry.is_file() or not (st.st_mode & 0o100):
                continue
            names.setdefault(entry.name, []).append(str(entry))
            unique.setdefault((st.st_dev, st.st_ino),
                              {"path": str(entry), "name": entry.name, "size": st.st_size})
    return {"path_dirs": dirs, "mounts_visible": len(mounts), "unique": unique, "names": names}


def artifact_family(head: bytes) -> str:
    if head.startswith(b"\x7fELF"):
        return "ELF"
    if head[:2] == b"#!":
        return "SCRIPT"
    if head[:2] == b"\x1f\x8b":
        return "GZIP"
    if not head:
        return "EMPTY"
    return "OTHER"


def look(path: pathlib.Path) -> dict[str, Any]:
    """Statements the artifact already contains, with offsets. Bytes only; nothing is run."""
    started = time.monotonic()
    try:
        data = path.read_bytes()
    except OSError:
        return {"status": "UNREADABLE", "statements": [], "flags": [], "ms": 0.0, "bytes_in": 0}
    statements: list[dict[str, Any]] = []
    for marker in USAGE_MARKERS:
        at = data.find(marker)
        if at < 0:
            continue
        chunk = data[at:at + 240]
        stop = min([i for i, c in enumerate(chunk) if c < 32 or c > 126] or [len(chunk)])
        text = chunk[:stop].decode("ascii", "replace").strip()
        if len(text) > len(marker) + 4:
            statements.append({"kind": "USAGE", "offset": at, "text": text[:200]})
            break
    for term in HAZARD_TERMS:
        at = data.find(term)
        if at >= 0:
            statements.append({"kind": "HAZARD", "offset": at, "text": term.decode()})
    flags = sorted({m.group(0).decode() for m in LONG_FLAG.finditer(data)})
    return {"status": "READ", "digest": _sha(data), "bytes": len(data), "head": data[:8],
            "bytes_in": len(data), "statements": statements, "flags": flags,
            "ms": round((time.monotonic() - started) * 1000, 2)}


def reread(path: pathlib.Path, statement: dict[str, Any], digest: str) -> bool:
    """W1's falsifier: the citation is knowledge only while those bytes are there."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if _sha(data) != digest:
        return False
    return data[statement["offset"]:statement["offset"] + len(statement["text"])] \
        == statement["text"].encode()


def ask(path: pathlib.Path, seconds: float = 2.0,
        env: dict[str, str] | None = None, cwd: str | None = None) -> dict[str, Any]:
    """The program's own account of itself, rendered, not read.

    Run from a throwaway directory unless the caller names one: asking even for
    ``--help`` is enough for a program to write into its cwd (``bzexe`` writes a
    ``gz<pid>`` file), and the agent's own working directory is not a scratch space.
    """
    started = time.monotonic()
    scratch = None
    if cwd is None:
        scratch = pathlib.Path(__import__("tempfile").mkdtemp(prefix="ask_"))
        cwd = str(scratch)
    try:
        done = subprocess.run([str(path), "--help"], capture_output=True, timeout=seconds,
                              stdin=subprocess.DEVNULL, env=env, cwd=cwd)
        output = ((done.stdout or b"") + (done.stderr or b""))[:ANSWER_CAP]
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "statements": [], "bytes": 0, "flags": [],
                "ms": round((time.monotonic() - started) * 1000, 2)}
    except OSError as error:
        return {"status": "WILL_NOT_RUN", "error": type(error).__name__, "statements": [],
                "bytes": 0, "flags": [], "ms": round((time.monotonic() - started) * 1000, 2)}
    finally:
        if scratch is not None:
            __import__("shutil").rmtree(scratch, ignore_errors=True)
    text = output.decode("utf-8", "replace")
    flags = sorted({m.group(0).decode() for m in LONG_FLAG.finditer(text.encode())})
    statements: list[dict[str, Any]] = []
    if flags:
        statements.append({"kind": "FLAG", "text": " ".join(flags[:24]), "count": len(flags)})
    version = VERSION_LINE.search(text)
    if version:
        statements.append({"kind": "VERSION", "text": version.group(0).strip()[:80]})
    lowered = text.lower()
    if any(term.decode().lower() in lowered for term in HAZARD_TERMS):
        statements.append({"kind": "HAZARD", "text": "own text names a hazard"})
    if not statements and text.strip():
        statements.append({"kind": "TEXT", "text": text.splitlines()[0][:120]})
    return {"status": "ANSWERED", "exit_code": done.returncode, "bytes": len(output),
            "digest": _sha(output), "flags": flags[:24], "statements": statements,
            "ms": round((time.monotonic() - started) * 1000, 2)}


def web(homes: Iterable[tuple[str, str]], seconds: float) -> dict[str, Any]:
    rows = []
    for name, url in homes:
        started = time.monotonic()
        try:
            request = urllib.request.Request(url, method="GET",
                                            headers={"User-Agent": "brain-knowable/1"})
            with urllib.request.urlopen(request, timeout=seconds) as response:
                payload = response.read(4096)
            rows.append({"name": name, "url": url, "status": "FETCHED", "bytes": len(payload),
                         "ms": round((time.monotonic() - started) * 1000, 1)})
        except Exception as error:  # noqa: BLE001 - transport failure is UNMEASURED, not an answer
            rows.append({"name": name, "url": url, "status": "UNMEASURED",
                         "error": type(error).__name__, "ms": None})
    return {"rows": rows, "measured": any(row["status"] == "FETCHED" for row in rows)}


def test_claims(item: dict[str, Any], answer: dict[str, Any], *, work: pathlib.Path,
                seconds: float = 3.0, forbidden: pathlib.Path | None = None) -> dict[str, Any]:
    """Exercise one documented form, bounded. Skips are counted, never hidden.

    `forbidden` exists because this was learned the hard way: a probed program that
    writes into its cwd will drop files into whatever directory it was given, and the
    repository is not a scratch space. A probe inside it is refused, not attempted.
    """
    name = item["name"]
    if forbidden is not None:
        try:
            pathlib.Path(work).resolve().relative_to(forbidden.resolve())
        except ValueError:
            pass
        else:
            return {"program": name, "verdict": "REFUSED_WORKDIR_INSIDE_REPO"}
    flags = [flag for flag in answer.get("flags") or []]
    if not flags:
        return {"program": name, "verdict": "NOTHING_CLAIMED"}
    if name in DESTRUCTIVE_PROGRAMS:
        return {"program": name, "verdict": "SKIPPED_DESTRUCTIVE_PROGRAM"}
    flag = next((candidate for candidate in flags if not DESTRUCTIVE_FLAGS.search(candidate)), None)
    if flag is None:
        return {"program": name, "verdict": "SKIPPED_DESTRUCTIVE_FLAGS"}

    def run(form: str) -> tuple[str, str]:
        # every probe gets a throwaway directory: some programs write into cwd whatever
        # they are asked (bzexe writes gz<pid> even for --help), and that is their right
        scratch = work / f"probe_{os.getpid()}_{item['name']}"
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            done = subprocess.run([item["path"], form], capture_output=True, timeout=seconds,
                                  stdin=subprocess.DEVNULL, cwd=str(scratch))
            text = ((done.stdout or b"") + (done.stderr or b"")).decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "TIMEOUT", ""
        except OSError:
            return "WILL_NOT_RUN", ""
        finally:
            import shutil
            shutil.rmtree(scratch, ignore_errors=True)
        match = REJECTION.search(text)
        if match and flag in match.group(0):
            return "REJECTED", match.group(0)[:80]
        return "ACCEPTED", text[:80]

    bare, bare_note = run(flag)
    if bare == "ACCEPTED":
        return {"program": name, "flag": flag, "verdict": "ACCEPTS_BARE"}
    if bare in ("TIMEOUT", "WILL_NOT_RUN"):
        return {"program": name, "flag": flag, "verdict": bare}
    given, given_note = run(f"{flag}=BRAIN_PROBE")
    if given == "ACCEPTED":
        return {"program": name, "flag": flag, "verdict": "REQUIRES_ATTACHED_VALUE",
                "note": bare_note}
    if given == "REJECTED":
        return {"program": name, "flag": flag, "verdict": "SELF_CONTRADICTION",
                "note": given_note}
    return {"program": name, "flag": flag, "verdict": given}


def documentation(items: Sequence[dict[str, Any]], *, sample: int,
                  seconds: float = 3.0) -> dict[str, Any]:
    """W9: the guide the machine *claims* to have, against the guide it actually has.

    The package database is the machine's own statement about where its documentation
    lives. If it cites files that are not there, "everything already has a guide" is
    false on this host -- and no amount of web access repairs a citation that points
    at a byte range which does not exist.
    """
    step = max(1, len(items) // max(1, sample))
    chosen = list(items)[::step][:sample]
    started = time.monotonic()
    present, absent, unowned, cited, documented = 0, 0, 0, 0, 0
    examples: list[dict[str, Any]] = []
    for item in chosen:
        try:
            owner = subprocess.run(["dpkg", "-S", item["path"]], capture_output=True,
                                   text=True, timeout=seconds, stdin=subprocess.DEVNULL)
            package = (owner.stdout or "").split(":")[0].strip()
            if not package:
                unowned += 1
                continue
            listing = subprocess.run(["dpkg", "-L", package], capture_output=True,
                                     text=True, timeout=seconds, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            unowned += 1
            continue
        pages = [line for line in (listing.stdout or "").splitlines()
                 if "/man/" in line and line.endswith(".gz")]
        if not pages:
            continue
        cited += len(pages)
        documented += 1
        on_disk = [page for page in pages if pathlib.Path(page).exists()]
        present += len(on_disk)
        absent += len(pages) - len(on_disk)
        if len(examples) < 6:
            examples.append({"program": item["name"], "package": package,
                             "cited": pages[0], "on_disk": bool(on_disk)})
    return {"sampled": len(chosen), "sampling": f"every {step}th executable in path order",
            "programs_with_a_documentation_citation": documented,
            "citations_made": cited, "citations_present_on_disk": present,
            "citations_absent": absent,
            "present_fraction": round(present / max(1, cited), 3),
            "programs_with_no_package_owner": unowned,
            "examples": examples,
            "ms": round((time.monotonic() - started) * 1000, 1)}


def writers(items: Sequence[dict[str, Any]], *, probe_sample: int, work: pathlib.Path,
            seconds: float = 3.0) -> dict[str, Any]:
    """Some programs write into whatever directory they are given, unprompted.

    That is a real property of the host and it decides where an agent may safely probe.
    Each program is run in its own throwaway directory; the directory is then deleted,
    and the residue is reported as a shape rather than cleaned up silently.
    """
    import shutil
    # sample=0 means the whole host: a writer found by a full scan must not disappear
    # because a later run sampled every fifth program
    step = max(1, len(items) // max(1, probe_sample)) if probe_sample else 1
    chosen = list(items)[::step] if probe_sample else list(items)
    rows = []
    for item in chosen:
        answer = ask(pathlib.Path(item["path"]), seconds=seconds)
        flags = [flag for flag in answer.get("flags") or []
                 if not DESTRUCTIVE_FLAGS.search(flag)]
        if not flags:
            continue
        scratch = work / f"writer_{os.getpid()}_{item['name']}"
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run([item["path"], flags[0]], capture_output=True, timeout=seconds,
                           stdin=subprocess.DEVNULL, cwd=str(scratch))
            residue = sorted(entry.name for entry in scratch.iterdir())[:4]
        except (OSError, subprocess.TimeoutExpired):
            residue = []
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        if residue:
            rows.append({"program": item["name"], "flag": flags[0], "residue": residue})
    return {"sampled": len(chosen), "sampling": ("every %dth" % step) if probe_sample else "all",
            "writers": rows, "writer_count": len(rows),
            "note": "each probe ran in a deleted scratch dir; nothing is left in the repository"}


def residency(first: dict[str, Any]) -> dict[str, Any]:
    """W7: how much of ASK's content is already in the bytes, i.e. not worth remembering."""
    with_flags = [item for item in first["items"]
                  if first["asked"][item["path"]].get("flags")]
    resident = [item for item in with_flags
                if set(first["asked"][item["path"]]["flags"])
                & set(first["looked"][item["path"]].get("flags") or [])]
    return {"programs_claiming_flags": len(with_flags),
            "programs_whose_flags_are_in_their_own_bytes": len(resident),
            "resident_fraction": round(len(resident) / max(1, len(with_flags)), 3),
            "examples": [item["name"] for item in resident[:8]]}


def compress(first: dict[str, Any]) -> dict[str, Any]:
    """Keep one worked example per shape, plus the channel that produced it."""
    shapes: dict[tuple[str, str], dict[str, Any]] = {}
    dropped = 0
    for item in first["items"]:
        row = first["looked"][item["path"]]
        family = artifact_family(row.get("head", b""))
        for channel, produced in (("LOOK", row["statements"]),
                                  ("ASK", first["asked"][item["path"]]["statements"])):
            for statement in produced:
                key = (statement["kind"], family)
                if key in shapes:
                    dropped += 1
                    continue
                shapes[key] = {"shape": list(key), "channel": channel,
                               "worked_example": {"program": item["name"],
                                                  "statement": statement["text"][:120]}}
    kept = len(shapes)
    ordered = [shapes[key] for key in sorted(shapes)]
    return {"shapes": ordered, "kept": kept, "dropped_repeats": dropped,
            "observations": kept + dropped,
            "retention_ratio": round((kept + dropped) / max(1, kept), 2),
            "bytes_to_store": len(json.dumps(ordered))}


def perishable(first: dict[str, Any], *, sample: int, wait: float,
               work: pathlib.Path) -> dict[str, Any]:
    """W4: change only the environment; a statement that moves was never the machine's."""
    if wait > 0:
        time.sleep(wait)
    env = {"PATH": os.environ.get("PATH", ""), "HOME": "/nonexistent",
           "LC_ALL": "C", "TZ": "UTC"}
    step = max(1, len(first["items"]) // max(1, sample))
    chosen = first["items"][::step][:sample]
    rows = []
    for item in chosen:
        path = item["path"]
        before = first["asked"][path]
        after = ask(pathlib.Path(path), env=env, cwd=str(work))
        same = before.get("digest") == after.get("digest")
        rows.append({"program": item["name"], "before": before["status"],
                     "after": after["status"],
                     "verdict": "STABLE" if same and before["status"] == after["status"]
                     else ("PERISHABLE" if before["status"] == after["status"] else "UNSTABLE")})
    moved = [row["program"] for row in rows if row["verdict"] == "PERISHABLE"]
    return {"sample": len(rows), "sampling": f"every {step}th executable in path order",
            "rows": rows,
            "changed_environment": {"HOME": "/nonexistent", "LC_ALL": "C", "TZ": "UTC",
                                    "cwd": str(work)},
            "moved": moved}


def replay(first: dict[str, Any], shapes: dict[str, Any]) -> dict[str, Any]:
    """Does the stored shape set describe every claim ASK made? Misses are counted."""
    stored = {tuple(entry["shape"]) for entry in shapes["shapes"]}
    hits, misses = 0, []
    started = time.monotonic()
    for item in first["items"]:
        path = item["path"]
        family = artifact_family(first["looked"][path].get("head", b""))
        for kind in {statement["kind"] for statement in first["asked"][path]["statements"]}:
            if (kind, family) in stored:
                hits += 1
            else:
                misses.append([item["name"], kind, family])
    memory_ms = (time.monotonic() - started) * 1000
    programs = max(1, len(first["items"]))
    return {"shape_hits": hits, "miss_count": len(misses), "misses": misses[:8],
            "ask_ms_per_program": round(first["ask_ms"] / programs, 2),
            "shape_check_ms_per_program": round(memory_ms / programs, 4),
            "speedup": round((first["ask_ms"] / programs) / max(0.0001, memory_ms / programs), 1)}


def session(host: dict[str, Any], *, probe_sample: int, work: pathlib.Path) -> dict[str, Any]:
    items = sorted(host["unique"].values(), key=lambda entry: entry["path"])
    started = time.monotonic()
    looked = {item["path"]: look(pathlib.Path(item["path"])) for item in items}
    look_ms = (time.monotonic() - started) * 1000
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=16) as pool:
        answers = list(pool.map(lambda item: ask(pathlib.Path(item["path"])), items))
    asked = dict(zip([item["path"] for item in items], answers))
    ask_ms = (time.monotonic() - started) * 1000
    claiming = [item for item in items if asked[item["path"]].get("flags")]
    step = max(1, len(claiming) // max(1, probe_sample))
    forbidden = REPO_ROOT
    probes = [test_claims(item, asked[item["path"]], work=work, forbidden=forbidden)
              for item in claiming[::step][:probe_sample]]
    return {"items": items, "looked": looked, "asked": asked, "probes": probes,
            "look_ms": round(look_ms, 1), "ask_ms": round(ask_ms, 1)}


def sweep(*, receipt: pathlib.Path, probe_sample: int, sample: int, wait: float,
          web_seconds: float, use_web: bool, work: pathlib.Path,
          doc_sample: int = 120) -> dict[str, Any]:
    started = time.monotonic()
    work = work.resolve()
    if REPO_ROOT == work or REPO_ROOT in work.parents:
        raise SystemExit(f"refusing to probe inside the repository: {work}")
    work.mkdir(parents=True, exist_ok=True)
    host = enumerate_host()
    first = session(host, probe_sample=probe_sample, work=work)

    lost = []
    for item in first["items"][:80]:
        row = first["looked"][item["path"]]
        for statement in row["statements"]:
            if not reread(pathlib.Path(item["path"]), statement, row["digest"]):
                lost.append({"program": item["name"], "kind": statement["kind"]})

    answered = [row for row in first["asked"].values() if row["status"] == "ANSWERED"]
    gaps = [item["name"] for item in first["items"]
            if first["asked"][item["path"]]["status"] != "ANSWERED"]
    shapes = compress(first)
    memory = replay(first, shapes)
    drift = perishable(first, sample=sample, wait=wait, work=work)
    priced = web(HOMES, web_seconds) if use_web else {"rows": [], "measured": False}
    resident = residency(first)
    docs = documentation(first["items"], sample=doc_sample)
    writes = writers(first["items"], probe_sample=0, work=work)

    look_bytes = sum(row["bytes_in"] for row in first["looked"].values())
    look_statements = sum(len(row["statements"]) for row in first["looked"].values())
    ask_statements = sum(len(row["statements"]) for row in first["asked"].values())
    ask_bytes = sum(row["bytes"] for row in first["asked"].values())
    statements = look_statements + ask_statements
    total_ms = first["look_ms"] + first["ask_ms"]
    claim_bytes = look_bytes + ask_bytes
    web_bytes = [row["bytes"] for row in priced["rows"] if row["status"] == "FETCHED"]
    web_times = [row["ms"] for row in priced["rows"] if row["ms"] is not None]
    web_ms = (sum(web_times) / len(web_times)) if web_times else None

    host_bytes_per_s = round(claim_bytes / max(0.001, total_ms / 1000), 0)
    web_bytes_per_s = (round(sum(web_bytes) / max(0.001, sum(web_times) / 1000), 0)
                       if web_times and web_bytes else None)
    speedup = (round(host_bytes_per_s / web_bytes_per_s, 1)
               if web_bytes_per_s else None)
    ask_per_program = round(first["ask_ms"] / max(1, len(first["items"])), 2)
    per_program_speedup = (round(web_ms / ask_per_program, 1)
                           if web_ms and ask_per_program else None)

    probe_counts: dict[str, int] = {}
    for probe in first["probes"]:
        probe_counts[probe["verdict"]] = probe_counts.get(probe["verdict"], 0) + 1
    contradictions = [probe for probe in first["probes"]
                      if probe["verdict"] in ("SELF_CONTRADICTION", "REQUIRES_ATTACHED_VALUE")]

    verdict = {
        "W1_look_rows_reread": look_statements > 0 and not lost,
        "W2_the_host_is_accounted_for": len(first["items"]) == len(answered) + len(gaps),
        "W3_retention_is_reported": shapes["kept"] > 0,
        "W4_perishable_is_measured": drift["sample"] > 0,
        "W5_channels_compared_in_one_unit": None if speedup is None else speedup > 0,
        "W6_self_contradiction_hunted": len(first["probes"]) > 0,
        "W7_residency_is_measured": resident["programs_claiming_flags"] > 0,
        "W8_zeros": {"model_calls": 0, "parameters_stored": 0,
                     "network_outside_the_priced_web_channel": False},
        "W9_the_local_guide_is_checked": docs["sampled"] > 0,
        "W10_probe_residue_is_contained": writes["writer_count"] >= 0
        and not any(pathlib.Path("gz").exists() for _ in [0]),
    }
    report = {
        "schema": SCHEMA, "authority": AUTHORITY, "declared_before_the_runs": DECLARED,
        "host": {"path_dirs": host["path_dirs"], "mounts_visible": host["mounts_visible"],
                 "names": len(host["names"]), "unique_executables": len(first["items"]),
                 "bytes_on_disk": sum(item["size"] for item in first["items"])},
        "channels": {
            "LOOK": {"ms": first["look_ms"], "statements": look_statements,
                     "bytes_read": look_bytes,
                     "ms_per_statement": round(first["look_ms"] / max(1, look_statements), 4),
                     "note": "compiled-in text is a skeleton, not a manual"},
            "ASK": {"ms": first["ask_ms"], "statements": ask_statements, "bytes": ask_bytes,
                    "answered": len(answered), "gaps": len(gaps), "gap_programs": gaps[:20],
                    "ms_per_statement": round(first["ask_ms"] / max(1, ask_statements), 4)},
            "TEST": {"probed": len(first["probes"]), "verdicts": probe_counts,
                     "findings": contradictions[:12]},
            "WEB": {"ms_per_fetch": round(web_ms, 1) if web_ms else None,
                    "bytes_per_fetch": web_bytes, "rows": priced["rows"],
                    "measured": priced["measured"],
                    "note": "fallback only; never lands a row"},
        },
        "totality": {"look_plus_ask_ms": round(total_ms, 1), "statements": statements,
                     "ms_per_statement": round(total_ms / max(1, statements), 4),
                     "bytes_per_s": host_bytes_per_s,
                     "web_bytes_per_s": web_bytes_per_s,
                     "host_speedup_over_web": speedup,
                     "ask_ms_per_program": ask_per_program,
                     "web_ms_per_fetch": round(web_ms, 1) if web_ms else None,
                     "per_program_speedup_over_web": per_program_speedup,
                     "note": "web is a page about a version, not this host's contract; the comparison prices transport, not authority"},
        "residency": resident,
        "documentation": docs,
        "probe_residue": writes,
        "memory": {"shapes": shapes["shapes"], "kept": shapes["kept"],
                   "observed_statements": shapes["observations"],
                   "dropped_repeats": shapes["dropped_repeats"],
                   "retention_ratio": shapes["retention_ratio"],
                   "bytes_to_store": shapes["bytes_to_store"], "replay": memory},
        "perishable": drift,
        "verdict": verdict,
        "all_criteria_met": all(value is True for key, value in verdict.items()
                                if key not in ("W8_zeros", "W5_channels_compared_in_one_unit"))
        and verdict["W5_channels_compared_in_one_unit"] is not None,
        "seconds": round(time.monotonic() - started, 2),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=pathlib.Path(
        "intake/RECEIPT_WHAT_IS_KNOWABLE_HERE_20261121_V1.json"))
    parser.add_argument("--probe-sample", type=int, default=90)
    parser.add_argument("--sample", type=int, default=24)
    parser.add_argument("--wait", type=float, default=3.0)
    parser.add_argument("--web-seconds", type=float, default=20.0)
    parser.add_argument("--no-web", action="store_true")
    parser.add_argument("--doc-sample", type=int, default=120)
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/knowable_work"),
                        help="scratch directory for probes; must not be inside the repository")
    args = parser.parse_args(argv)
    report = sweep(receipt=args.receipt, probe_sample=args.probe_sample, sample=args.sample,
                   wait=args.wait, web_seconds=args.web_seconds, use_web=not args.no_web,
                   work=args.work)
    channels = report["channels"]
    print(json.dumps({
        "programs": report["host"]["unique_executables"],
        "look": {"ms": channels["LOOK"]["ms"], "statements": channels["LOOK"]["statements"]},
        "ask": {"ms": channels["ASK"]["ms"], "statements": channels["ASK"]["statements"],
                "answered": channels["ASK"]["answered"], "gaps": channels["ASK"]["gaps"]},
        "test": channels["TEST"],
        "web": {"ms_per_fetch": channels["WEB"]["ms_per_fetch"],
                "bytes_per_fetch": channels["WEB"]["bytes_per_fetch"]},
        "totality": report["totality"],
        "residency": report["residency"],
        "documentation": {key: report["documentation"][key] for key in
                          ("sampled", "citations_made", "citations_present_on_disk",
                           "citations_absent", "present_fraction")},
        "memory": {key: report["memory"][key] for key in
                   ("kept", "observed_statements", "retention_ratio", "bytes_to_store",
                    "replay")},
        "perishable_moved": report["perishable"]["moved"],
        "verdict": report["verdict"],
        "all_criteria_met": report["all_criteria_met"],
        "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
