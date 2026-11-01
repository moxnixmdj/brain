#!/usr/bin/env python3
"""Produce a program that does the job, then prove it by running it.

Composing reaches what is registered. This reaches what is merely POSSIBLE:
python3 is on this machine, and the standard library can produce a great many
formats without installing anything. What was missing was not the ability to
run code -- it was any way to know which code to write.

The answer is the same one that works everywhere else in this machine:
generate a finite set of candidates and let the EFFECT decide. Every
candidate is really executed, and the output is really checked -- a gzip
file is accepted only if its first bytes are 1f8b. A program that cannot be
shown to work is not returned.

This is synthesis, not recall: no candidate is trusted because it looks
plausible. The oracle is the file it produced.

What is learned is kept. A goal answered once is answered instantly the next
time, because the verified program is remembered keyed by what it produces --
the point of learning is not to do it twice.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROGRAM_SYNTHESIS_V1"

STATE_PATH = os.environ.get(
    "BRAIN_PROGRAM_SYNTHESIS_STATE",
    str(pathlib.Path(__file__).resolve().parents[2]
        / "canonical/astra_runtime/state/PROGRAM_SYNTHESIS_V1.json"))


def _magic_for(suffix: str) -> str | None:
    from canonical.runtime import empirical_cli_probe_v1 as emp
    return emp._MAGIC_BY_SUFFIX.get(str(suffix or "").lower())


# --------------------------------------------------------------------------- #
# candidate programs, keyed by the format they claim to produce
# --------------------------------------------------------------------------- #
# Each template receives `content` and `out`. They are stdlib only, so they
# cost nothing and always import -- the reason this works at all on a machine
# where nothing may be installed.
CANDIDATES: dict[str, list[tuple[str, str]]] = {
    ".gz": [
        ("gzip_module", "import gzip\n"
                        "gzip.open(OUT, 'wt', encoding='utf-8').write(CONTENT)\n"),
        ("gzip_bytes", "import gzip\n"
                       "with gzip.open(OUT, 'wb') as fh:\n"
                       "    fh.write(CONTENT.encode('utf-8'))\n"),
    ],
    ".bz2": [
        ("bz2_module", "import bz2\n"
                       "with bz2.open(OUT, 'wt', encoding='utf-8') as fh:\n"
                       "    fh.write(CONTENT)\n"),
    ],
    ".xz": [
        ("lzma_module", "import lzma\n"
                        "with lzma.open(OUT, 'wt', encoding='utf-8') as fh:\n"
                        "    fh.write(CONTENT)\n"),
    ],
    ".zip": [
        ("zipfile_module", "import zipfile\n"
                           "with zipfile.ZipFile(OUT, 'w') as zf:\n"
                           "    zf.writestr('content.txt', CONTENT)\n"),
    ],
    ".tar": [
        ("tarfile_module", "import io, tarfile\n"
                           "data = CONTENT.encode('utf-8')\n"
                           "info = tarfile.TarInfo('content.txt')\n"
                           "info.size = len(data)\n"
                           "with tarfile.open(OUT, 'w') as tf:\n"
                           "    tf.addfile(info, io.BytesIO(data))\n"),
    ],
    ".json": [
        ("json_dump", "import json\n"
                      "json.dump({'content': CONTENT}, open(OUT, 'w', encoding='utf-8'))\n"),
    ],
    ".csv": [
        # A TABLE HAS FIELDS.  This wrote the whole sample into one cell, and a
        # one-column file is exactly what the verifier must stop accepting --
        # any text parses as one unquoted column.  The sample's words are the
        # fields; one row per line keeps it a table that the check can tell
        # apart from prose.
        ("csv_module", "import csv\n"
                       "rows = [ln.split() for ln in CONTENT.splitlines() if ln.strip()]\n"
                       "with open(OUT, 'w', newline='', encoding='utf-8') as fh:\n"
                       "    csv.writer(fh).writerows(rows or [[CONTENT]])\n"),
    ],
    ".png": [
        ("png_minimal", "import struct, zlib\n"
                        "w = h = 1\n"
                        "raw = b'\\x00' + b'\\xff\\xff\\xff'\n"
                        "def chunk(t, d):\n"
                        "    c = t + d\n"
                        "    return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)\n"
                        "png = (b'\\x89PNG\\r\\n\\x1a\\n'\n"
                        "       + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))\n"
                        "       + chunk(b'IDAT', zlib.compress(raw))\n"
                        "       + chunk(b'IEND', b''))\n"
                        "open(OUT, 'wb').write(png)\n"),
    ],
    ".txt": [
        ("plain_write", "open(OUT, 'w', encoding='utf-8').write(CONTENT)\n"),
    ],
    ".md": [
        ("plain_write", "open(OUT, 'w', encoding='utf-8').write(CONTENT)\n"),
    ],
}


def suffixes() -> list[str]:
    return sorted(CANDIDATES)


def _render(template: str, out: str, content: str) -> str:
    return (template.replace("OUT", repr(out))
                    .replace("CONTENT", repr(content)))


# --------------------------------------------------------------------------- #
# the oracle: really run it, really check what came out
# --------------------------------------------------------------------------- #
def run_candidate(source: str, out: pathlib.Path, workdir: pathlib.Path,
                  timeout: float = 20.0) -> dict[str, Any]:
    """Execute one candidate for real. Returns what happened."""
    script = workdir / "candidate.py"
    script.write_text(source, encoding="utf-8")
    started = time.time()
    try:
        proc = subprocess.run([sys.executable, str(script)],
                              cwd=str(workdir), capture_output=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "TIMEOUT", "duration_s": time.time() - started}
    except Exception as exc:  # noqa: BLE001 - a candidate must never break the search
        return {"ok": False, "reason": type(exc).__name__,
                "duration_s": time.time() - started}
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "stderr": (proc.stderr or b"").decode("utf-8", "replace")[-400:],
            "duration_s": round(time.time() - started, 4)}


# A file that merely exists has proved nothing. Where a format can be opened
# by the very stdlib that writes it, open it: a sqlite file is only a sqlite
# file if sqlite3 will read it, a tar only if tarfile will list it. Accepting
# "EXISTS_NO_FORMAT_TO_CHECK" is how a machine writes a text file, calls it a
# database, and reports the gap closed.
_SQLITE_CHECK = (
    "import sys\n"
    "P=sys.argv[1]\n"
    "d=open(P,'rb').read(16)\n"
    "assert d[:15]==b'SQLite format 3', 'not a sqlite header'\n"
    "import sqlite3\n"
    "c=sqlite3.connect(P)\n"
    "c.execute('select name from sqlite_master').fetchall()\n"
    "c.close()\n")

_PNG_CHECK = (
    "import sys, struct\n"
    "P=sys.argv[1]\n"
    "d=open(P,'rb').read()\n"
    "assert d[:8]==b'\\x89PNG\\r\\n\\x1a\\n', 'not a png signature'\n"
    "assert b'IHDR' in d[:32], 'no IHDR chunk'\n"
    "w,h=struct.unpack('>II', d[16:24])\n"
    "assert w>0 and h>0, 'zero sized image'\n"
    "assert b'IEND' in d[-12:], 'no IEND chunk'\n")

# A JPEG is verified by its own structure: SOI, then an SOF frame header, then EOI.
# PIL is not required and is not installed everywhere; these four markers are the format.
_IMAGE_CHECK = (
    "import sys\n"
    "P=sys.argv[1]\n"
    "d=open(P,'rb').read()\n"
    "assert d[:2]==b'\\xff\\xd8', 'not a jpeg start-of-image'\n"
    "assert d[-2:]==b'\\xff\\xd9', 'no end-of-image marker'\n"
    "assert any(m in d for m in (b'\\xff\\xc0', b'\\xff\\xc1', b'\\xff\\xc2')), "
    "'no SOF frame header'\n")

_ROUND_TRIP: dict[str, str] = {
    ".json": "import sys, json; json.load(open(sys.argv[1], encoding='utf-8'))",
    # csv.reader accepts EVERYTHING -- a tar, a digest line, a version banner --
    # as one long unquoted row.  A TABLE has a separator in it; a file of prose
    # does not.  Measured 2026-11-01: "dump data.db into data.csv" was answered
    # by ['run_gcov-dump'] and closed, because the banner it printed parsed.
    ".csv": ("import sys, csv; "
             "rows=list(csv.reader(open(sys.argv[1], newline='', encoding='utf-8'))); "
             "assert rows, 'empty'; "
             "assert any(len(r) > 1 for r in rows), 'no separator: not a table'"),
    # sqlite3.connect() opens ANY file -- it does not read the header until
    # you touch a table, so 'select 1' passes on a text file. Check the
    # signature bytes, then actually read the schema.
    ".db": _SQLITE_CHECK,
    ".sqlite": _SQLITE_CHECK,
    ".sqlite3": _SQLITE_CHECK,
    ".tar": "import sys, tarfile; tarfile.open(sys.argv[1]).getnames()",
    ".zip": "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).namelist()",
    ".gz": "import sys, gzip; gzip.open(sys.argv[1], 'rb').read(1)",
    ".bz2": "import sys, bz2; bz2.open(sys.argv[1], 'rb').read(1)",
    ".xz": "import sys, lzma; lzma.open(sys.argv[1], 'rb').read(1)",
    ".png": _PNG_CHECK,
    ".txt": "import sys; open(sys.argv[1], encoding='utf-8').read()",
    ".md": "import sys; open(sys.argv[1], encoding='utf-8').read()",
    # A COMPOUND FORMAT IS VERIFIED BY THE LIBRARY THAT OWNS THE OUTER LAYER.
    #
    # `.tar.gz` is not `.gz`: `gzip.open` reads the gzip wrapper of a tarball happily and
    # says nothing about whether a tar stream is inside.  Measured 2026-11-01: "pack pkg
    # into pkg.tar.gz" was answered with the plan `run_gzip`, whose output is a gzip of a
    # FILE, and the machine reported it VERIFIED -- because this table had no `.tar.gz`
    # entry at all and an entry-less format used to pass.  tarfile reads the tar and the
    # compression in one call, so the check costs one import.
    ".tar.gz": "import sys, tarfile; tarfile.open(sys.argv[1], 'r:gz').getnames()",
    ".tgz": "import sys, tarfile; tarfile.open(sys.argv[1], 'r:gz').getnames()",
    ".tar.bz2": "import sys, tarfile; tarfile.open(sys.argv[1], 'r:bz2').getnames()",
    ".tar.xz": "import sys, tarfile; tarfile.open(sys.argv[1], 'r:xz').getnames()",
    # A DIGEST IS A DIGEST SHAPE, and nothing else is.  `run_md5sum` "answered" a request
    # for a sha256 file on 2026-11-01 because any bytes under the name were accepted.
    ".sha256": "import sys, re; t=open(sys.argv[1], encoding='utf-8').read(); "
               "assert re.search(r'\\b[0-9a-f]{64}\\b', t), 'no sha256 digest'",
    ".sha1": "import sys, re; t=open(sys.argv[1], encoding='utf-8').read(); "
             "assert re.search(r'\\b[0-9a-f]{40}\\b', t), 'no sha1 digest'",
    ".md5": "import sys, re; t=open(sys.argv[1], encoding='utf-8').read(); "
            "assert re.search(r'\\b[0-9a-f]{32}\\b', t), 'no md5 digest'",
    ".jpeg": _IMAGE_CHECK,
    ".jpg": _IMAGE_CHECK,
}


# --------------------------------------------------------------------------- #
# WHAT KIND OF BYTES ARE THESE, and is that allowed to be this format
# --------------------------------------------------------------------------- #
# A verifier that only asks "does the library open it" answers the wrong half of
# the question.  Measured 2026-11-01 on main, store empty, discover() called
# directly: "dump data.db into data.csv" was answered by the plan ['run_tar'] and
# reported PASS__SINGLE_ACTION_FOUND_AND_VERIFIED -- csv.reader accepts a tar as
# one long unquoted row, so the library DID open it.  The file was a tar.
#
# Every format this repository verifies is either a CONTAINER (its own bytes say
# what it is) or PLAIN TEXT (no bytes of a container may appear in it).  So the
# negative test costs one read of 512 bytes and settles the whole class: if a
# container signature is present and the suffix does not own that container, the
# file is not the requested format, whatever a parser will tolerate.
_CONTAINER_SIGNS: tuple[tuple[str, int, bytes], ...] = (
    ("gzip", 0, b"\x1f\x8b"),
    ("xz", 0, b"\xfd7zXZ\x00"),
    ("bzip2", 0, b"BZh"),
    ("zstd", 0, b"\x28\xb5\x2f\xfd"),
    ("zip", 0, b"PK\x03\x04"),
    ("png", 0, b"\x89PNG\r\n\x1a\n"),
    ("jpeg", 0, b"\xff\xd8\xff"),
    ("pdf", 0, b"%PDF"),
    ("7z", 0, b"7z\xbc\xaf\x27\x1c"),
    ("elf", 0, b"\x7fELF"),
    ("sqlite", 0, b"SQLite format 3\x00"),
    # a tar header starts with the member's name; its format marker sits at 257
    ("tar", 257, b"ustar"),
)

_CONTAINER_OWNER: dict[str, set[str]] = {
    ".gz": {"gzip"}, ".tgz": {"gzip"}, ".tar.gz": {"gzip"},
    ".xz": {"xz"}, ".tar.xz": {"xz"},
    ".bz2": {"bzip2"}, ".tar.bz2": {"bzip2"},
    ".zip": {"zip"},
    ".tar": {"tar"},
    ".png": {"png"},
    ".jpg": {"jpeg"}, ".jpeg": {"jpeg"},
    ".pdf": {"pdf"},
    ".db": {"sqlite"}, ".sqlite": {"sqlite"}, ".sqlite3": {"sqlite"},
}

# A TEXT FORMAT CANNOT CARRY A CLAIM ABOUT ITS CONTENT.
#
# `.txt` and `.md` are verified by opening them as UTF-8, which any byte stream
# of text satisfies.  Measured 2026-11-01: "write the commit log of repo into
# log.txt" was answered by ['run_md5sum.textutils'] and closed.  A digest of a
# README is a text file and is not a commit log, and nothing in the bytes says
# which one it is -- so no verifier exists here, and a format with no verifier
# is not a closed goal (see verify_round_trip).  The learning channel asks
# `carries_content_evidence` before it books a win.
_FORMAT_ONLY: frozenset[str] = frozenset({".txt", ".md"})


def carries_content_evidence(suffix: str) -> bool:
    """Can a file of this format be checked for being the thing asked for?

    False where the only possible check is "it opens as text" -- because then the
    name of the format is all that was ever verified.
    """
    return str(suffix or "").lower() not in _FORMAT_ONLY


def _container_of(data: bytes) -> str | None:
    for name, offset, sign in _CONTAINER_SIGNS:
        if data[offset:offset + len(sign)] == sign:
            return name
    return None


def container_mismatch(head: bytes, suffix: str) -> str | None:
    """The container these bytes are, when that container is not this suffix.

    None means "nothing in the head contradicts the suffix".  This is the test
    that separates a tar called out.csv from a csv.
    """
    found = _container_of(head)
    if not found:
        return None
    key = str(suffix or "").lower()
    if found in _CONTAINER_OWNER.get(key, ()):
        return None
    return found


_KNOWN_SUFFIXES: tuple[str, ...] = tuple(sorted(
    set(_ROUND_TRIP) | set(_CONTAINER_OWNER), key=len, reverse=True))


def suffix_for_name(name: str) -> str:
    """The LONGEST extension the table knows that ends this name.

    pathlib answers `.gz` for pkg.tar.gz, and that answer is why a gzip of one
    file was accepted as a tarball: the machine asked a verifier that owns the
    OUTER wrapper only.  The table of verifiers already knows both suffixes, so
    the longest match is the one whose verifier must be satisfied.
    """
    low = str(name or "").lower()
    for suf in _KNOWN_SUFFIXES:
        if low.endswith(suf):
            return suf
    return pathlib.Path(low).suffix


_HEAD_BYTES = 512


def verify_round_trip(out: pathlib.Path, suffix: str,
                      timeout: float = 15.0) -> tuple[bool, str]:
    """Open it with the library that owns the format. If it will not open,
    it is not that format, however many bytes it has."""
    import subprocess
    key = str(suffix or "").lower()
    if out.is_file():
        # the negative test first: a tar called out.csv is not a csv, however
        # happily csv.reader reads it.  512 bytes, never the whole file.
        with out.open("rb") as fh:
            head = fh.read(_HEAD_BYTES)
        wrong = container_mismatch(head, key)
        if wrong:
            return False, "CONTAINER_MISMATCH:" + wrong
    snippet = _ROUND_TRIP.get(key)
    if not snippet:
        # AN UNCHECKED FORMAT IS NOT A VERIFIED ONE.
        #
        # This returned ``True, "NO_VERIFIER_FOR_FORMAT"``, and that single line is the worst
        # defect class this repository names -- a verification claim that is silently
        # skipped -- sitting inside the machine's own learning channel.  Measured
        # 2026-11-01, store empty, eight goal families, discover() called directly:
        #
        #   "convert tiny.png into tiny.jpg"   -> PASS__SINGLE_ACTION_FOUND_AND_VERIFIED,
        #                                         plan ['run_unexpand']   (a whitespace tool)
        #   "pack pkg into pkg.tar.gz"         -> PASS..., plan ['run_gzip']
        #   "hash blob.bin into blob.sha256"   -> PASS..., plan ['run_sha256sum']
        #   "write the commit log of repo..."  -> PASS..., plan ['run_md5sum.textutils']
        #
        # Four of eight "closed" goals were closed over bytes nobody checked.  So: where a
        # MAGIC SIGNATURE exists in the table this repository already keeps, that signature
        # is the check; where even that is missing, the honest verdict is that nothing was
        # verified -- reported as such, never as a pass.
        magic = _magic_for(key)
        if magic and out.is_file():
            head = out.read_bytes()[:16].hex()
            if head.startswith(magic):
                return True, "MAGIC_OK"
            return False, "MAGIC_MISMATCH:" + head
        return False, "NO_VERIFIER_FOR_FORMAT"
    script = out.parent / "_verify.py"
    # the path is an ARGUMENT, never text substituted into the source.
    # Substituting it replaced the P in b'\\x89PNG...' and turned the
    # signature check into garbage -- a verifier that corrupts itself fails
    # everything and the machine reports a real file as not real.
    script.write_text(snippet, encoding="utf-8")
    try:
        proc = subprocess.run([sys.executable, str(script), str(out)],
                              cwd=str(out.parent), capture_output=True,
                              timeout=timeout)
    except Exception:  # noqa: BLE001 - a verifier must never break the search
        return False, "VERIFIER_ERROR"
    finally:
        try:
            script.unlink()
        except OSError:
            pass
    if proc.returncode == 0:
        return True, "ROUND_TRIP_OK"
    return False, "NOT_READABLE_AS_" + (suffix or "?")


def check_effect(out: pathlib.Path, suffix: str) -> tuple[bool, str]:
    """Does the artifact exist, and is it really the format claimed?"""
    if not out.is_file() or out.stat().st_size == 0:
        return False, "NO_OUTPUT"
    want = _magic_for(suffix)
    if want:
        head = out.read_bytes()[:16].hex()
        if not head.startswith(want):
            return False, "MAGIC_MISMATCH:" + head
        return verify_round_trip(out, suffix)
    return verify_round_trip(out, suffix)


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #
def synthesize(goal: str, content: str = "brain-synthesis-sample",
               suffix: str | None = None,
               workdir: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Find a program that produces what the goal asks for.

    Candidates are executed in order and the first one whose output really
    matches is returned. Nothing is accepted on plausibility.
    """
    from canonical.runtime import cli_capability_acquisition_v1 as acq

    suffix = suffix or acq._requested_suffix(goal)
    if not suffix:
        return {"schema": SCHEMA, "pass": False, "status": "OPEN__NO_OUTPUT_FORMAT_IN_GOAL",
                "goal": goal, "detail": "nothing to verify an effect against"}
    candidates = CANDIDATES.get(suffix.lower())
    if not candidates:
        return {"schema": SCHEMA, "pass": False,
                "status": "OPEN__NO_CANDIDATE_FOR_FORMAT", "goal": goal,
                "suffix": suffix, "known_formats": suffixes()}

    tmp = pathlib.Path(workdir) if workdir else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-synth-"))
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / ("out" + suffix)
    rows: list[dict[str, Any]] = []
    winner: dict[str, Any] = {}
    try:
        for name, template in candidates:
            if out.exists():
                out.unlink()
            source = _render(template, str(out), content)
            ran = run_candidate(source, out, tmp)
            ok, why = (check_effect(out, suffix) if ran.get("ok") else (False, "DID_NOT_RUN"))
            rows.append({"candidate": name, "ran": ran.get("ok"),
                         "returncode": ran.get("returncode"),
                         "effect": why, "worked": ok,
                         "duration_s": ran.get("duration_s")})
            if ok:
                winner = {"name": name, "source": source,
                          "output_path": str(out),
                          "output_bytes": out.stat().st_size,
                          "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                          "effect": why}
                break
    finally:
        if workdir is None:
            shutil.rmtree(tmp, ignore_errors=True)

    if not winner:
        return {"schema": SCHEMA, "pass": False,
                "status": "OPEN__NO_CANDIDATE_PRODUCED_THE_EFFECT",
                "goal": goal, "suffix": suffix, "trials": rows,
                "authority": "SYNTHESIS_SEARCH_EXHAUSTED"}
    return {"schema": SCHEMA, "pass": True,
            "status": "PASS__PROGRAM_SYNTHESISED_AND_VERIFIED",
            "goal": goal, "suffix": suffix, "trials": rows, **winner,
            "authority": "SYNTHESISED_EXECUTED_AND_EFFECT_VERIFIED"}


# --------------------------------------------------------------------------- #
# remembering what worked, so it is instant next time
# --------------------------------------------------------------------------- #
def _load() -> dict[str, Any]:
    p = pathlib.Path(STATE_PATH)
    if not p.is_file():
        return {"schema": SCHEMA, "learned": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema") == SCHEMA:
            data.setdefault("learned", {})
            return data
    except (OSError, ValueError):
        pass
    return {"schema": SCHEMA, "learned": {}}


def _save(state: dict[str, Any]) -> None:
    p = pathlib.Path(STATE_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def remember(result: Mapping[str, Any]) -> None:
    """File a verified program where it can be found again."""
    if not result.get("pass"):
        return
    key = str(result.get("suffix") or "").lower()
    if not key or not result.get("source"):
        return
    state = _load()
    state["learned"][key] = {
        "name": result.get("name"), "source": result.get("source"),
        "effect": result.get("effect"),
        "learned_at": time.time(),
        "goal": str(result.get("goal") or "")[:200],
        "verified_sha256": result.get("output_sha256"),
    }
    _save(state)


def recall(suffix: str) -> dict[str, Any] | None:
    """A program already proven to produce this format."""
    return _load()["learned"].get(str(suffix or "").lower())


def synthesize_or_recall(goal: str, content: str = "brain-synthesis-sample",
                         suffix: str | None = None) -> dict[str, Any]:
    """instant when known, honest when not."""
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    suffix = suffix or acq._requested_suffix(goal)
    known = recall(suffix) if suffix else None
    if known:
        return {"schema": SCHEMA, "pass": True, "from_memory": True,
                "status": "PASS__RECALLED_VERIFIED_PROGRAM",
                "goal": goal, "suffix": suffix, **known,
                "authority": "PREVIOUSLY_SYNTHESISED_AND_VERIFIED"}
    result = synthesize(goal, content=content, suffix=suffix)
    remember(result)
    result.setdefault("from_memory", False)
    return result
