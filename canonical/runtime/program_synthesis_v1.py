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
        ("csv_module", "import csv\n"
                       "with open(OUT, 'w', newline='', encoding='utf-8') as fh:\n"
                       "    csv.writer(fh).writerow([CONTENT])\n"),
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

_ROUND_TRIP: dict[str, str] = {
    ".json": "import sys, json; json.load(open(sys.argv[1], encoding='utf-8'))",
    ".csv": "import sys, csv; [r for r in csv.reader(open(sys.argv[1], newline='', encoding='utf-8'))]",
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
}


def verify_round_trip(out: pathlib.Path, suffix: str,
                      timeout: float = 15.0) -> tuple[bool, str]:
    """Open it with the library that owns the format. If it will not open,
    it is not that format, however many bytes it has."""
    import subprocess
    snippet = _ROUND_TRIP.get(str(suffix or "").lower())
    if not snippet:
        return True, "NO_VERIFIER_FOR_FORMAT"
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
# --------------------------------------------------------------------------- #
# what this layer may and may not claim
# --------------------------------------------------------------------------- #
# The candidates above are FORMAT WRITERS.  They write a payload in a named format and the
# oracle proves the format.  Nothing here can fuzz a function, build a wheel, add a
# dependency, inline a function or write docstrings -- no stdlib one-liner does those -- and
# yet `synthesize_or_recall` answered every one of them.  Measured on the 43-act probe:
# "Fuzz the function add in calc.py ... report it to out/fuzz.json", "Build a wheel ...",
# "Add the dependency requests ...", "Add logging and metrics ...", "Inline the function
# sub ..." and "Write docstrings for the functions ..." were each returned with
# `pass: true, from_memory: true, authority: PREVIOUSLY_SYNTHESISED_AND_VERIFIED`, by
# recalling a remembered `json_dump` -- because `remember` keyed the learned program on the
# OUTPUT SUFFIX alone (`json`), so the store held one program per FILE EXTENSION and any
# sentence ending in ".json" recalled it.  composure, that is a false claim of the worst
# kind: a verified program was named for a request no program in this file can perform.
#
# So the fallback is admitted for the one class it actually serves -- produce a file in the
# requested format -- and for nothing else.  A request whose act is not among these words is
# not a format write, and this layer says so instead of writing a JSON file about it.
_FORMAT_WRITE_VERBS = frozenset("""
write save create output dump store put generate make encode produce print convert
format export render serialise serialize compose emit record
compress uncompress decompress archive pack unpack zip gzip bundle unbundle
""".split())

_ACT_STOP = frozenset("""
a an the this that these those it its is are was were be been am do does did and or but if
then than so as at by for from in into of on to with without using use please me my we you
please first second every all each any some few more most
report reports receipt receipts findings summary summaries result results
out dest destination target tmp temp output outputs
""".split())

# The nouns a FORMAT WRITE is made of: the payload and the shape it is written in.  A
# sentence containing any OTHER content noun is not a format write, however it opens.
_FORMAT_WRITE_OBJECTS = frozenset("""
json xml csv tsv txt yaml yml toml html htm markdown md pdf png jpg jpeg gif gz bz2 zip tar
xz svg docx xlsx rtf text string content contents data payload bytes value values object
objects array record records row rows sample file files document documents archive manifest
listing list image raster font chart line lines number numbers total totals
""".split())


def _act_words(text: str) -> set[str]:
    """The words that name WHAT TO DO, with the destination's own words removed.

    The prose is read through the front compiler's own value stripper, so a path, a URL or a
    quoted payload cannot vote -- the same rule the composer route applies, and for the same
    measured reason (a destination's suffix once decided the task).
    """
    try:
        from canonical.runtime import goal_front_compiler_v1 as _front
        text = _front.prose_only(str(text or ""))
        # The PAYLOAD the sentence states is a value, not a word about the act.  Reused from
        # the composer route, which already draws this distinction: measured, "Write the text
        # hello." was refused with ACT_NOT_A_FORMAT_WRITE:hello -- and `hello` was the text to
        # write, not part of the job.
        from canonical.runtime import composer_route_v1 as _cr
        stated = _cr.extract_content(str(text or ""))
        if stated:
            text = str(text).replace(str(stated), " ")
    except Exception:  # noqa: BLE001 - no front compiler, read the sentence itself
        pass
    words = {w for w in re.findall(r"[a-z][a-z0-9]+", str(text or "").lower())}
    return {w for w in words if w not in _ACT_STOP}


def claims_the_request(goal: str) -> tuple[bool, str]:
    """May this layer answer `goal`?  Only when it is a format write.

    Returns (may_answer, why).  `why` names the act that made it impossible, so callers can
    refuse in words the owner can act on rather than with a generic status.
    """
    # `_requested_suffix` answers "" as well as None when the sentence names no format; the
    # earlier test compared with `is None` and so admitted every sentence as a format write.
    if not _requested_suffix_guarded(goal):
        return False, "NO_FORMAT_STATED"
    act = _act_words(goal)
    if not act:
        return False, "NO_ACT_STATED"
    # EVERY content word has to belong to a format write -- the verb AND the object.  "Write
    # docstrings for the functions in X" opens with a format-write verb and is not one: the
    # thing it asks for is docstrings, and a JSON writer cannot produce docstrings.
    # Measured: with only the verb tested, that sentence and "Make the network calls ...
    # retry safely" were still admitted, and each was answered with a JSON file.
    extra = act - _FORMAT_WRITE_VERBS - _FORMAT_WRITE_OBJECTS
    if extra:
        return False, "ACT_NOT_A_FORMAT_WRITE:" + ",".join(sorted(extra))
    if act & _FORMAT_WRITE_VERBS:
        return True, "FORMAT_WRITE"
    return False, "NO_FORMAT_WRITE_VERB:" + ",".join(sorted(act))


def _requested_suffix_guarded(goal: str) -> str | None:
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    try:
        return acq._requested_suffix(goal)
    except Exception:  # noqa: BLE001 - no suffix question, no suffix answer
        return None


def _covers(a_goal: str, b_goal: str) -> bool:
    """Does an act verified for `b_goal` also name everything `a_goal` asks for?"""
    want = _act_words(a_goal)
    have = _act_words(b_goal)
    return bool(want) and want <= have



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


def recall(suffix: str, goal: str | None = None) -> dict[str, Any] | None:
    """A program already proven to produce this format -- AND to do this job.

    The format is recorded on the program; the ACT is recorded on the goal it was verified
    against.  Recalling on the format alone made every `.json` sentence recall a JSON
    writer, including sentences asking for a fuzzer (see the header of this section).
    """
    known = _load()["learned"].get(str(suffix or "").lower())
    if not known:
        return None
    if goal is None:
        return known
    if _covers(goal, str(known.get("goal") or "")) or _covers(
            str(known.get("goal") or ""), goal):
        return known
    return None


def synthesize_or_recall(goal: str, content: str = "brain-synthesis-sample",
                         suffix: str | None = None) -> dict[str, Any]:
    """instant when known, honest when not."""
    from canonical.runtime import cli_capability_acquisition_v1 as acq
    suffix = suffix or acq._requested_suffix(goal)
    allowed, why = claims_the_request(goal)
    if not allowed:
        return {"schema": SCHEMA, "pass": False, "from_memory": False,
                "status": "REFUSED__NOT_A_FORMAT_WRITE",
                "reason": "SYNTHESIS_CANNOT_PERFORM:" + why,
                "goal": goal, "suffix": suffix,
                "authority": "NO_PROGRAM_IN_THIS_LAYER_PERFORMS_THE_ACT"}
    known = recall(suffix, goal) if suffix else None
    if known:
        return {"schema": SCHEMA, "pass": True, "from_memory": True,
                "status": "PASS__RECALLED_VERIFIED_PROGRAM",
                "goal": goal, "suffix": suffix, **known,
                "authority": "PREVIOUSLY_SYNTHESISED_AND_VERIFIED"}
    result = synthesize(goal, content=content, suffix=suffix)
    remember(result)
    result.setdefault("from_memory", False)
    return result
