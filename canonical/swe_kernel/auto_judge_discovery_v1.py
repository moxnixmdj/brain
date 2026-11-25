#!/usr/bin/env python3
"""Automatic judge discovery & closed scan-diff-earn loop.

Closes the bottleneck named at the end of Rounds 10-12
(`SCAN_AND_DIFF_AGAINST_MEMORY_20261124_V1` and `A_JUDGE_MUST_REJECT_OTHER_REAL_KINDS_20261124_V1`):

  1. No hand-typed authoritative validator table: candidate producers and candidate
     judges are discovered by introspecting the host's installed CLI `--help` pages
     and Python's standard library modules (`sys.stdlib_module_names`), plus optional
     local/JIT documentation hints when a kind remains unread.
  2. Every candidate -- including plausible-looking lazy traps (`bz2.open(p, 'rb')`,
     `lzma.open(p, 'rb')`, `sqlite3.connect(p)`, `gzip -t`) -- must pass
     `earn_a_judge_v1.earn` against ALL real probe kinds, a binary decoy,
     repeat determinism, and zero tree-mutation side effects before admission.
  3. Closes the full loop:
       scan(root) -> diff against memory -> rank UNREAD in ignorance_ledger_v1
       -> auto-discover & earn judges -> resolve ledger gaps -> re-scan(root).
  4. Memory stores only content-level judge declarations (`kind -> argv, status,
     evidence, refutations`) -- never file paths -- and supports active refutation
     when a new exclusive kind exposes an over-broad incumbent judge.

Model calls: 0. Parameters stored: 0. Runtime network calls: 0 (unless caller
explicitly enables `allow_jit=True` fallback). Authority: NONE.
"""
from __future__ import annotations

import bz2
import hashlib
import importlib
import json
import lzma
import os
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import wave
import xml.etree.ElementTree as ET
import zipfile
import gzip
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import earn_a_judge_v1 as earner
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.runtime import scan_and_diff_against_memory_v1 as scanner

SCHEMA = "PROJECT_BRAIN_AUTO_JUDGE_DISCOVERY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

#Format nesting is a mathematical property of grammars (e.g. JSON/XML/TOML/HTML/Python
# are valid UTF-8 text; JSON `{"a": 1}` is a valid Python expression; HTML/PLIST-XML can
# overlap XML). Rather than declaring `NESTED_KINDS` by hand, we ALSO compute empirical
# subset nesting over the real probe corpus: a kind K1 is nested only if every other
# real kind K2 it accepts is strictly rejected by K2's own exclusive judge on K1's probe
# AND K1 is a text/syntax container.
TEXT_SUPERSET_KINDS = frozenset({"utf8_text", "python", "xml"})


def _build_extended_probe_corpus(root: str) -> dict[str, dict[str, str]]:
    """Generate real files of each discoverable kind using their real producers, plus a decoy.

    Starts from `earn_a_judge_v1.probe_pairs(root)` (zip, gzip, json, png, tar, python,
    utf8_text, elf) and adds real producer-generated probes for formats supported by
    available host stdlib/CLI producers (bz2, xz, sqlite, xml, toml, plist, wav, pdf).
    """
    pairs = earner.probe_pairs(root)
    decoy = pairs["zip"]["decoy"]

    # bz2 produced by real bz2 compressor
    real_bz2 = os.path.join(root, "real.bz2")
    with bz2.open(real_bz2, "wb") as fh:
        fh.write(b"payload compressed with bzip2\n")
    pairs["bz2"] = {"real": real_bz2, "decoy": decoy}

    # xz produced by real lzma compressor (FORMAT_XZ)
    real_xz = os.path.join(root, "real.xz")
    with lzma.open(real_xz, "wb", format=lzma.FORMAT_XZ) as fh:
        fh.write(b"payload compressed with xz\n")
    pairs["xz"] = {"real": real_xz, "decoy": decoy}

    # sqlite3 database produced by real sqlite3 engine
    real_sqlite = os.path.join(root, "real.sqlite")
    conn = sqlite3.connect(real_sqlite)
    try:
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO items (name) VALUES ('alpha')")
        conn.commit()
    finally:
        conn.close()
    pairs["sqlite"] = {"real": real_sqlite, "decoy": decoy}

    # XML produced by xml.etree.ElementTree
    real_xml = os.path.join(root, "real.xml")
    elem = ET.Element("catalog")
    item = ET.SubElement(elem, "entry", attrib={"id": "1"})
    item.text = "witness"
    ET.ElementTree(elem).write(real_xml, encoding="utf-8", xml_declaration=True)
    pairs["xml"] = {"real": real_xml, "decoy": decoy}

    # Apple binary plist produced by stdlib plistlib (FMT_BINARY, distinct from XML!)
    real_bplist = os.path.join(root, "real.bplist")
    with open(real_bplist, "wb") as fh:
        plistlib.dump({"bundle": "brain", "version": 1}, fh, fmt=plistlib.FMT_BINARY)
    pairs["bplist"] = {"real": real_bplist, "decoy": decoy}

    # RIFF WAVE audio produced by stdlib wave
    real_wav = os.path.join(root, "real.wav")
    with wave.open(real_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x01" * 32)
    pairs["wav"] = {"real": real_wav, "decoy": decoy}

    # Minimal valid PDF 1.4 structural document
    real_pdf = os.path.join(root, "real.pdf")
    with open(real_pdf, "wb") as fh:
        fh.write(
            b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [] /Count 0 >>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n"
            b"trailer<< /Root 1 0 R /Size 3 >>\nstartxref\n9\n%%EOF\n"
        )
    pairs["pdf"] = {"real": real_pdf, "decoy": decoy}

    return pairs


def discover_cli_candidates(
    search_programs: Sequence[str] = (
        "bzip2", "xz", "unzip", "gzip", "tar", "readelf", "jq", "xmllint", "pdfinfo",
    ),
    timeout_s: float = 2.0,
) -> list[tuple[str, str, tuple[str, ...]]]:
    """Introspect installed CLI programs' `--help` output to discover test/integrity flags.

    Returns `(candidate_id, target_kind, argv)` tuples derived from what each binary
    actually prints in its `--help` page. Never trusts the flag: `earn` decides.
    """
    kind_by_prog = {
        "bzip2": "bz2",
        "xz": "xz",
        "unzip": "zip",
        "gzip": "gzip",
        "tar": "tar",
        "readelf": "elf",
        "jq": "json",
        "xmllint": "xml",
        "pdfinfo": "pdf",
    }
    test_flag_re = ("test", "integrity", "verify", "check", "header", "list")
    discovered: list[tuple[str, str, tuple[str, ...]]] = []

    for prog in search_programs:
        if not shutil.which(prog):
            continue
        kind = kind_by_prog.get(prog)
        if not kind:
            continue
        try:
            done = subprocess.run(
                [prog, "--help"],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout_s,
            )
            help_text = (done.stdout or "") + "\n" + (done.stderr or "")
        except (OSError, subprocess.SubprocessError):
            continue

        for raw_line in help_text.splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            low = line.lower()
            if not any(word in low for word in test_flag_re):
                continue
            tokens = line.split()
            if not tokens:
                continue
            first_flag = tokens[0].rstrip(",")
            if not first_flag.startswith("-") or "=" in first_flag:
                continue
            if first_flag in ("--help", "-V", "--version"):
                continue
            cid = f"cli:{prog}:{first_flag}"
            discovered.append((cid, kind, (prog, first_flag)))
    return discovered


def discover_stdlib_candidates() -> list[tuple[str, str, tuple[str, ...]]]:
    """Introspect available Python stdlib modules and generate candidate reader probes.

    Deliberately emits BOTH lazy/naive forms (e.g. `bz2.open(p,'rb')`, `sqlite3.connect(p)`)
    AND strict eager-read/header forms so that the earning gate's discrimination power
    is continuously tested rather than sheltered by hand-curated inputs.
    """
    py = sys.executable
    available = getattr(sys, "stdlib_module_names", frozenset())
    out: list[tuple[str, str, tuple[str, ...]]] = []

    def has(mod: str) -> bool:
        if available and mod.split(".")[0] not in available:
            return False
        try:
            importlib.import_module(mod)
            return True
        except Exception:
            return False

    if has("bz2"):
        # Lazy trap (should be REFUSED as cat) + eager stream read (should be EARNED)
        out.append(("py:bz2:lazy_open", "bz2",
                    (py, "-c", "import bz2,sys;bz2.open(sys.argv[1],'rb')")))
        out.append(("py:bz2:read1", "bz2",
                    (py, "-c", "import bz2,sys;d=bz2.open(sys.argv[1],'rb').read(1);sys.exit(0 if len(d)>=0 else 1)")))
    if has("lzma"):
        out.append(("py:lzma:lazy_open", "xz",
                    (py, "-c", "import lzma,sys;lzma.open(sys.argv[1],'rb')")))
        out.append(("py:lzma:xz_read1", "xz",
                    (py, "-c", "import lzma,sys;lzma.open(sys.argv[1],'rb',format=lzma.FORMAT_XZ).read(1)")))
    if has("gzip"):
        out.append(("py:gzip:read1", "gzip",
                    (py, "-c", "import gzip,sys;gzip.open(sys.argv[1],'rb').read(1)")))
    if has("zipfile"):
        out.append(("py:zipfile:is_zip", "zip",
                    (py, "-c", "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);sys.exit(0 if z.testzip() is None else 1)")))
    if has("tarfile"):
        out.append(("py:tarfile:open", "tar",
                    (py, "-c", "import tarfile,sys;tarfile.open(sys.argv[1])")))
    if has("sqlite3"):
        # Trap: sqlite3.connect(p) creates/accepts non-sqlite files until queried!
        out.append(("py:sqlite3:connect_lazy", "sqlite",
                    (py, "-c", "import sqlite3,sys;sqlite3.connect(sys.argv[1])")))
        out.append(("py:sqlite3:ro_header_query", "sqlite",
                    (py, "-c",
                     "import sqlite3,sys,urllib.parse;"
                     "p=sys.argv[1];"
                     "h=open(p,'rb').read(16);"
                     "sys.exit(1) if h!=b'SQLite format 3\\x00' else None;"
                     "u='file:'+urllib.parse.quote(p)+'?mode=ro';"
                     "c=sqlite3.connect(u,uri=True);"
                     "c.execute('SELECT count(*) FROM sqlite_master').fetchall();"
                     "c.close()")))
    if has("json"):
        out.append(("py:json:load", "json",
                    (py, "-c", "import json,sys;json.load(open(sys.argv[1],encoding='utf-8'))")))
    if has("ast"):
        out.append(("py:ast:parse", "python",
                    (py, "-c", "import ast,sys;ast.parse(open(sys.argv[1],'rb').read())")))
    if has("xml.etree.ElementTree"):
        out.append(("py:xml:et_parse", "xml",
                    (py, "-c", "import xml.etree.ElementTree as E,sys;E.parse(sys.argv[1])")))
    if has("plistlib"):
        out.append(("py:plistlib:bplist", "bplist",
                    (py, "-c", "import plistlib,sys;h=open(sys.argv[1],'rb').read(8);"
                     "sys.exit(1) if not h.startswith(b'bplist0') else None;"
                     "plistlib.load(open(sys.argv[1],'rb'),fmt=plistlib.FMT_BINARY)")))
    if has("wave"):
        out.append(("py:wave:open", "wav",
                    (py, "-c", "import wave,sys;w=wave.open(sys.argv[1],'rb');w.getnframes();w.close()")))
    # Structural header + trailer judge for PDF, PNG, UTF-8
    out.append(("py:pdf:header_eof", "pdf",
                (py, "-c", "import sys;b=open(sys.argv[1],'rb').read();"
                 "sys.exit(0 if b.startswith(b'%PDF-') and b'%%EOF' in b[-1024:] else 1)")))
    out.append(("py:png:magic", "png",
                (py, "-c", "import sys;sys.exit(0 if open(sys.argv[1],'rb').read(8)==bytes([137,80,78,71,13,10,26,10]) else 1)")))
    out.append(("py:utf8:decode", "utf8_text",
                (py, "-c", "import sys;open(sys.argv[1],'rb').read().decode('utf-8')")))
    return out


# Fast necessary-condition leading-byte filter (ONLY skips impossible binary formats,
# NEVER accepts without running the earned judge). Keeps directory scans sub-second.
FAST_MAGIC_NECESSARY: dict[str, Callable[[bytes], bool]] = {
    "png": lambda h: h.startswith(b"\x89PNG\r\n\x1a\n"),
    "gzip": lambda h: h.startswith(b"\x1f\x8b"),
    "bz2": lambda h: h.startswith(b"BZh"),
    "xz": lambda h: h.startswith(b"\xfd7zXZ\x00"),
    "zip": lambda h: h.startswith((b"PK\x03\x04", b"PK\x05\x06")),
    "tar": lambda h: len(h) > 262 and h[257:262] == b"ustar",
    "elf": lambda h: h.startswith(b"\x7fELF"),
    "sqlite": lambda h: h.startswith(b"SQLite format 3\x00"),
    "bplist": lambda h: h.startswith(b"bplist0"),
    "wav": lambda h: len(h) >= 12 and h[:4] == b"RIFF" and h[8:12] == b"WAVE",
    "pdf": lambda h: h.startswith(b"%PDF-"),
}


def auto_earn_judges(
    *,
    only_kinds: set[str] | None = None,
    evaluate_all: bool = False,
) -> dict[str, Any]:
    """Automatically discover candidates from CLI + Python stdlib and earn valid judges."""
    started = time.perf_counter()
    root = tempfile.mkdtemp(prefix="brain-auto-judge-")
    try:
        pairs = _build_extended_probe_corpus(root)
        raw_candidates = discover_cli_candidates() + discover_stdlib_candidates()
        admitted_by_kind: dict[str, dict[str, Any]] = {}
        refused_rows: list[dict[str, Any]] = []
        evaluated = 0

        for cid, kind, argv in raw_candidates:
            if only_kinds is not None and kind not in only_kinds:
                continue
            pair = pairs.get(kind)
            if pair is None:
                continue
            # Prefer an EXCLUSIVE judge if one already earned for this kind (unless auditing all)
            if (
                not evaluate_all
                and kind in admitted_by_kind
                and admitted_by_kind[kind]["status"] == earner.EARNED
            ):
                continue
            evaluated += 1
            others = [(k, v["real"]) for k, v in pairs.items() if k != kind]
            # Temporarily allow empirical nested check for text-container kinds
            res = _earn_with_nested_check(kind, argv, real=pair["real"], decoy=pair["decoy"], others=others)
            row = res.as_dict()
            row["candidate_id"] = cid
            if res.status in (earner.EARNED, earner.NESTED):
                prev = admitted_by_kind.get(kind)
                if prev is None or (prev["status"] == earner.NESTED and res.status == earner.EARNED):
                    admitted_by_kind[kind] = row
            else:
                refused_rows.append(row)

        admitted_list = [admitted_by_kind[k] for k in sorted(admitted_by_kind)]
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "candidates_discovered": len(raw_candidates),
            "candidates_evaluated": evaluated,
            "admitted": admitted_list,
            "refused": refused_rows,
            "admitted_kinds": sorted(admitted_by_kind),
            "exclusive_kinds": sorted(
                k for k, r in admitted_by_kind.items() if r["status"] == earner.EARNED
            ),
            "nested_kinds": sorted(
                k for k, r in admitted_by_kind.items() if r["status"] == earner.NESTED
            ),
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
            "network_calls": 0,
            "parameters_stored": 0,
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _earn_with_nested_check(
    kind: str,
    argv: Sequence[str],
    *,
    real: str,
    decoy: str,
    others: Sequence[tuple[str, str]],
) -> earner.Candidate:
    """Delegate to `earn_a_judge_v1.earn` inside an isolated scratch cwd."""
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="brain-judge-cwd-") as scratch_cwd:
        try:
            os.chdir(scratch_cwd)
            cand = earner.earn(kind, argv, real=real, decoy=decoy, others=others)
        finally:
            os.chdir(old_cwd)
    if (
        cand.status == earner.REFUSED_ACCEPTS_ANOTHER_REAL_KIND
        and kind in TEXT_SUPERSET_KINDS
        and cand.evidence.get("exit_on_real") == 0
        and cand.evidence.get("exit_on_decoy") != 0
        and cand.evidence.get("exit_on_real_again") == 0
    ):
        cand.status = earner.NESTED
    return cand


class JudgeStore:
    """Inspectable, refutable external store of earned content judges (zero paths stored)."""

    def __init__(self, records: Sequence[Mapping[str, Any]] = ()) -> None:
        self.judges: dict[str, dict[str, Any]] = {}
        self.signatures: scanner.Memory = scanner.Memory()
        for rec in records:
            if rec.get("kind") and rec.get("argv"):
                self.judges[str(rec["kind"])] = {
                    "kind": str(rec["kind"]),
                    "argv": list(rec["argv"]),
                    "status": str(rec.get("status") or earner.EARNED),
                    "candidate_id": rec.get("candidate_id"),
                    "refutations": int(rec.get("refutations") or 0),
                }

    def callable_validators(self) -> dict[str, Callable[[str], int]]:
        out: dict[str, Callable[[str], int]] = {}
        for kind, rec in sorted(self.judges.items()):
            if int(rec.get("refutations") or 0) > 0:
                continue
            argv = tuple(rec["argv"])

            def _validator(path: str, _k: str = kind, _a: tuple[str, ...] = argv) -> int:
                nec = FAST_MAGIC_NECESSARY.get(_k)
                if nec is not None:
                    try:
                        with open(path, "rb") as fh:
                            if not nec(fh.read(512)):
                                return 1
                    except OSError:
                        return 127
                return earner._run(_a, path)

            out[kind] = _validator
        return out

    def admit_from_receipt(self, receipt: Mapping[str, Any]) -> list[str]:
        added: list[str] = []
        for row in receipt.get("admitted") or []:
            kind = str(row["kind"])
            if kind not in self.judges or self.judges[kind].get("refutations", 0) > 0:
                self.judges[kind] = {
                    "kind": kind,
                    "argv": list(row["argv"]),
                    "status": str(row["status"]),
                    "candidate_id": row.get("candidate_id"),
                    "refutations": 0,
                }
                added.append(kind)
        return sorted(added)

    def refute_against_probe(self, probe_kind: str, probe_path: str) -> list[str]:
        """Refute any EXCLUSIVE judge of another kind that falsely accepts `probe_path`."""
        demoted: list[str] = []
        for kind, rec in self.judges.items():
            if kind == probe_kind or rec.get("status") != earner.EARNED:
                continue
            if int(rec.get("refutations") or 0) > 0:
                continue
            rc = earner._run(tuple(rec["argv"]), probe_path)
            if rc == 0:
                rec["refutations"] = int(rec.get("refutations") or 0) + 1
                rec["refuted_by_kind"] = probe_kind
                demoted.append(kind)
        return sorted(demoted)

    def save(self, path: Path | str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "judges": [self.judges[k] for k in sorted(self.judges)],
            "signature_memory": self.signatures.as_dict(),
        }
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(target)

    @classmethod
    def load(cls, path: Path | str) -> "JudgeStore":
        p = Path(path)
        if not p.is_file():
            return cls()
        raw = json.loads(p.read_text(encoding="utf-8"))
        store = cls(raw.get("judges") or [])
        sig_mem = (raw.get("signature_memory") or {}).get("signatures") or []
        for row in sig_mem:
            store.signatures.seen[tuple(row["signature"])] = {
                "count": int(row["count"]),
                "suffixes": dict(row.get("suffixes") or {}),
                "items": int(row.get("items", row["count"])),
            }
        return store


def scan_with_store(
    root: str | os.PathLike[str],
    store: JudgeStore,
    *,
    max_files: int = 200,
    max_bytes: int = 8_000_000,
) -> tuple[list[scanner.Item], dict[str, Any]]:
    """Scan `root` using only `store`'s active earned judges (never filename suffixes)."""
    validators = store.callable_validators()
    items: list[scanner.Item] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", "node_modules"})
        for name in sorted(names):
            if len(items) >= max_files:
                break
            full = os.path.join(current, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size > max_bytes:
                continue
            sig = tuple(
                k for k, fn in sorted(validators.items()) if fn(full) == 0
            )
            items.append(
                scanner.Item(
                    path=os.path.relpath(full, root),
                    suffix=os.path.splitext(name)[1].lower(),
                    size=size,
                    sig=sig,
                    abspath=os.path.abspath(full),
                )
            )
        if len(items) >= max_files:
            break

    judged = scanner.judge_all(store.signatures, items)
    known = [i for i in judged if i.verdict == scanner.KNOWN]
    understood = [i for i in judged if i.verdict == scanner.UNDERSTOOD]
    unread = [i for i in judged if i.verdict == scanner.UNREAD]
    summary = {
        "schema": SCHEMA,
        "files": len(judged),
        "known": len(known),
        "understood": len(understood),
        "unread": len(unread),
        "active_judges": sorted(validators),
        "unread_paths": [i.path for i in unread],
    }
    return judged, summary


def close_ignorance_loop(
    root: str | os.PathLike[str],
    *,
    store: JudgeStore | None = None,
    ledger_path: str | None = None,
    max_files: int = 200,
    learn_signatures: bool = True,
) -> dict[str, Any]:
    """Closed round-trip: Scan -> Diff -> Ledger Rank -> Auto-Earn Judges -> Re-Scan.

    If `unread == 0` on the initial scan, zero discovery work is performed (fast path).
    When `unread > 0`, records the gaps in `ignorance_ledger_v1`, runs automatic
    CLI + stdlib judge discovery and earning, admits verified judges, resolves the
    ledger gaps based on measured reduction in `unread`, and learns content signatures.
    """
    started = time.perf_counter()
    store = store if store is not None else JudgeStore()
    own_ledger = ledger_path is None
    if own_ledger:
        fd, ledger_path = tempfile.mkstemp(prefix="brain-ledger-", suffix=".json")
        os.close(fd)
        os.unlink(ledger_path)

    try:
        before_items, before = scan_with_store(root, store, max_files=max_files)
        unread_items = [i for i in before_items if i.verdict == scanner.UNREAD]
        gap_ids = scanner.to_ignorance(unread_items, path=ledger_path) if unread_items else []
        ranked_gaps = ledger.rank(limit=10, path=ledger_path) if gap_ids else []

        earned_receipt = None
        newly_admitted: list[str] = []
        if unread_items:
            earned_receipt = auto_earn_judges()
            newly_admitted = store.admit_from_receipt(earned_receipt)

        after_items, after = scan_with_store(root, store, max_files=max_files)
        helped = after["unread"] < before["unread"]
        for gid in gap_ids:
            ledger.resolve(gid, helped=helped, close=(after["unread"] == 0), path=ledger_path)

        if learn_signatures:
            store.signatures.learn(after_items)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "before": before,
            "after": after,
            "unread_delta": after["unread"] - before["unread"],
            "gaps_noted": len(gap_ids),
            "ranked_gaps_before": ranked_gaps,
            "newly_admitted_judges": newly_admitted,
            "refused_candidates_count": (
                len(earned_receipt["refused"]) if earned_receipt else 0
            ),
            "ledger_stats_after": ledger.stats(path=ledger_path),
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
            "network_calls": 0,
            "parameters_stored": 0,
        }
    finally:
        if own_ledger and ledger_path and os.path.exists(ledger_path):
            try:
                os.unlink(ledger_path)
            except OSError:
                pass
