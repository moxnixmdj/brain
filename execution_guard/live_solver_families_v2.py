"""Fresh-goal EXECUTION families for individual bound capabilities (heartbeat wave 2).

Each generator writes fresh inputs, states one plain sentence, and returns an oracle that
judges the REAL artifact with the standard library only - never with the library or binary
the tool itself used:

  JQ_QUERY                 json.query.jq               expected value computed in Python
  ARCHIVE_VERIFY_GNU       archive.verify.tar_gz.gnu   archive built by stdlib tarfile; one in
                                                       three is tampered and MUST fail closed
  PYTHON_SOURCE_AUDIT      python.source.audit.ast     generated package with known counts
  PYTHON_TESTS_AUDIT       python.tests.audit.unittest generated tests with known results; a
                                                       failing suite MUST surface as FAIL
  CODEC_MSGPACK            auto.pypi.msgpack           decoded by a hand-written msgpack reader
  CODEC_CBOR               auto.npm.dfinity-cbor       decoded by a hand-written CBOR reader
                                                       (integer/string/bool/list records: the
                                                       bound library @dfinity/cbor 0.2.3 TRUNCATES
                                                       floats - 1.5 encodes as 1)
  CODEC_CBOR_FLOATS_FAIL_CLOSED  auto.npm.dfinity-cbor records with floats MUST fail closed; a
                                                       truncated artifact must never be a PASS
  SQLITE_FROM_RECORDS      sqlite.table.create_from_json_records   rows read back with sqlite3

Nothing here is a capability credit.  A failure is recorded as a failure; generators are
never weakened to hide one.
"""
from __future__ import annotations

import json
import random
import sqlite3
import string
import struct
import tarfile
import textwrap
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word


# ----------------------------------------------------------------------------- helpers

def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _passed(result: dict[str, Any]) -> bool:
    return result.get("pass") is True


# ----------------------------------------------------------------------------- jq

def gen_jq(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    items = [{"name": _word(rng, 5), "v": rng.randint(1, 500)} for _ in range(rng.randint(2, 6))]
    doc = {"a": {"b": rng.randint(1, 9999)}, "items": items, "tag": _word(rng, 7)}
    src = work / f"doc_{i}_{_word(rng, 4)}.json"
    src.write_text(json.dumps(doc), encoding="utf-8")
    out = work / f"q_{i}_{_word(rng, 4)}.txt"
    k = rng.randrange(5)
    if k == 0:
        filt, expected = ".a.b", str(doc["a"]["b"])
    elif k == 1:
        filt, expected = ".items | length", str(len(items))
    elif k == 2:
        filt, expected = "[.items[].v] | add", str(sum(x["v"] for x in items))
    elif k == 3:
        idx = rng.randrange(len(items))
        filt, expected = f".items[{idx}].name", items[idx]["name"]
    else:
        filt, expected = ".tag", doc["tag"]
    goal = f'Run the jq query with jq filter "{filt}" on {_rel(src)} and save the output to {_rel(out)}.'

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "output not written"
        got = out.read_text(encoding="utf-8").strip()
        return (got == expected), f"expected {expected!r} got {got!r}"
    return Case("JQ_QUERY", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- archive verify

def gen_archive_verify(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    tag = _word(rng, 4)
    files = []
    for j in range(rng.randint(1, 3)):
        p = work / f"av_{i}_{tag}_{j}.txt"
        p.write_bytes(("\n".join(_word(rng, 8) for _ in range(rng.randint(1, 6))) + "\n").encode())
        files.append(p)
    manifest = work / f"manifest_{i}_{tag}.json"
    manifest.write_text(json.dumps({"records": [{"verification_paths": [_rel(p) for p in files]}]}), encoding="utf-8")
    archive = work / f"bundle_{i}_{tag}.tar.gz"
    tamper = (i % 3 == 2)
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(manifest, arcname=_rel(manifest))
        for idx, p in enumerate(files):
            if tamper and idx == 0:
                bad = work / f"tampered_{i}_{tag}.txt"
                bad.write_bytes(p.read_bytes() + b"tampered\n")
                tf.add(bad, arcname=_rel(p))  # same member name, different bytes
            else:
                tf.add(p, arcname=_rel(p))
    goal = f"Verify the tar.gz archive {_rel(archive)} against the manifest {_rel(manifest)} with gnu tar."

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if tamper:
            return (not _passed(result)), "tampered archive must fail closed; got " + str(result.get("status"))
        if not _passed(result):
            return False, "intact archive rejected: " + str(result.get("status")) + " " + str(result.get("reason"))[:120]
        return True, ""
    return Case("ARCHIVE_VERIFY_GNU", goal, oracle, not tamper, [])


# ----------------------------------------------------------------------------- python source audit

def gen_source_audit(rng: random.Random, work: Path, i: int) -> Case:
    pkg = work / f"srcaudit_{i}_{_word(rng, 4)}"
    pkg.mkdir(parents=True, exist_ok=True)
    total_functions = total_classes = 0
    nfiles = rng.randint(1, 3)
    for f in range(nfiles):
        nf, nc = rng.randint(0, 4), rng.randint(0, 3)
        total_functions += nf
        total_classes += nc
        body = ["import json", "import os", ""]
        body += [f"def fn_{f}_{k}(x):\n    return x + {k}\n" for k in range(nf)]
        body += [f"class C_{f}_{k}:\n    value = {k}\n" for k in range(nc)]
        (pkg / f"mod_{f}.py").write_text("\n".join(body) + "\n", encoding="utf-8")
    out = work / f"audit_{i}_{_word(rng, 4)}.json"
    goal = f"Audit the python source tree {_rel(pkg)} with the ast audit and save the report to {_rel(out)}."

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "report not written"
        report = _read_json(out)
        totals = report.get("totals") if isinstance(report, dict) else None
        if not isinstance(totals, dict):
            return False, "report has no totals"
        want = {"files": nfiles, "functions": total_functions, "classes": total_classes}
        got = {k: totals.get(k) for k in want}
        return (got == want), f"expected {want} got {got}"
    return Case("PYTHON_SOURCE_AUDIT", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- python tests audit

def gen_tests_audit(rng: random.Random, work: Path, i: int) -> Case:
    root = work / f"testaudit_{i}_{_word(rng, 4)}"
    root.mkdir(parents=True, exist_ok=True)
    failing = (i % 4 == 3)
    n_pass = rng.randint(1, 5)
    lines = ["import unittest", "", "class T(unittest.TestCase):"]
    for k in range(n_pass):
        lines.append(f"    def test_ok_{k}(self):\n        self.assertEqual({k} + 1, {k + 1})")
    if failing:
        lines.append("    def test_bad(self):\n        self.assertEqual(1, 2)")
    lines += ["", "if __name__ == '__main__':", "    unittest.main()"]
    (root / "test_gen.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = work / f"tests_{i}_{_word(rng, 4)}.json"
    goal = f'Audit the unittest tests under {_rel(root)} matching pattern "test_*.py" and save the report to {_rel(out)}.'

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if failing:
            return (not _passed(result)), "a failing suite must surface as FAIL; got " + str(result.get("status"))
        if not _passed(result):
            return False, "passing suite reported as failure: " + str(result.get("status"))
        if not out.is_file():
            return False, "report not written"
        report = _read_json(out)
        totals = report.get("totals") if isinstance(report, dict) else {}
        ok = isinstance(totals, dict) and totals.get("failed") == 0 and totals.get("errors") == 0 and totals.get("passed", totals.get("run")) == n_pass
        return ok, f"expected {n_pass} passed, 0 failed; totals {totals}"
    return Case("PYTHON_TESTS_AUDIT", goal, oracle, not failing, [out])


# ----------------------------------------------------------------------------- independent decoders

def msgpack_decode(data: bytes):
    """Minimal independent msgpack reader (nil, bool, ints, floats, str, bin, array, map)."""
    pos = 0

    def rd(n: int) -> bytes:
        nonlocal pos
        chunk = data[pos:pos + n]
        if len(chunk) != n:
            raise ValueError("truncated")
        pos += n
        return chunk

    def value():
        b = rd(1)[0]
        if b <= 0x7F:
            return b
        if b >= 0xE0:
            return b - 0x100
        if 0x80 <= b <= 0x8F:
            return {value(): value() for _ in range(b & 0x0F)}
        if 0x90 <= b <= 0x9F:
            return [value() for _ in range(b & 0x0F)]
        if 0xA0 <= b <= 0xBF:
            return rd(b & 0x1F).decode("utf-8")
        if b == 0xC0:
            return None
        if b == 0xC2:
            return False
        if b == 0xC3:
            return True
        if b == 0xC4:
            return rd(rd(1)[0])
        if b == 0xC5:
            return rd(struct.unpack(">H", rd(2))[0])
        if b == 0xC6:
            return rd(struct.unpack(">I", rd(4))[0])
        if b == 0xCA:
            return struct.unpack(">f", rd(4))[0]
        if b == 0xCB:
            return struct.unpack(">d", rd(8))[0]
        if b == 0xCC:
            return rd(1)[0]
        if b == 0xCD:
            return struct.unpack(">H", rd(2))[0]
        if b == 0xCE:
            return struct.unpack(">I", rd(4))[0]
        if b == 0xCF:
            return struct.unpack(">Q", rd(8))[0]
        if b == 0xD0:
            return struct.unpack(">b", rd(1))[0]
        if b == 0xD1:
            return struct.unpack(">h", rd(2))[0]
        if b == 0xD2:
            return struct.unpack(">i", rd(4))[0]
        if b == 0xD3:
            return struct.unpack(">q", rd(8))[0]
        if b == 0xD9:
            return rd(rd(1)[0]).decode("utf-8")
        if b == 0xDA:
            return rd(struct.unpack(">H", rd(2))[0]).decode("utf-8")
        if b == 0xDB:
            return rd(struct.unpack(">I", rd(4))[0]).decode("utf-8")
        if b == 0xDC:
            return [value() for _ in range(struct.unpack(">H", rd(2))[0])]
        if b == 0xDD:
            return [value() for _ in range(struct.unpack(">I", rd(4))[0])]
        if b == 0xDE:
            return {value(): value() for _ in range(struct.unpack(">H", rd(2))[0])}
        if b == 0xDF:
            return {value(): value() for _ in range(struct.unpack(">I", rd(4))[0])}
        raise ValueError("unsupported msgpack type 0x%02x" % b)

    out = value()
    if pos != len(data):
        raise ValueError("trailing bytes")
    return out


def cbor_decode(data: bytes):
    """Minimal independent CBOR reader (RFC 8949 major types 0-5, 7 simple/float)."""
    pos = 0

    def rd(n: int) -> bytes:
        nonlocal pos
        chunk = data[pos:pos + n]
        if len(chunk) != n:
            raise ValueError("truncated")
        pos += n
        return chunk

    def head():
        b = rd(1)[0]
        major, info = b >> 5, b & 0x1F
        if info < 24:
            return major, info
        if info == 24:
            return major, rd(1)[0]
        if info == 25:
            return major, struct.unpack(">H", rd(2))[0]
        if info == 26:
            return major, struct.unpack(">I", rd(4))[0]
        if info == 27:
            return major, struct.unpack(">Q", rd(8))[0]
        if info == 31:
            return major, None  # indefinite
        raise ValueError("reserved additional info")

    def value():
        nonlocal pos
        start = pos
        major, arg = head()
        if major == 0:
            return arg
        if major == 1:
            return -1 - arg
        if major == 2:
            return rd(arg)
        if major == 3:
            return rd(arg).decode("utf-8")
        if major == 4:
            if arg is None:
                items = []
                while data[pos] != 0xFF:
                    items.append(value())
                pos += 1
                return items
            return [value() for _ in range(arg)]
        if major == 5:
            if arg is None:
                out = {}
                while data[pos] != 0xFF:
                    k = value()
                    out[k] = value()
                pos += 1
                return out
            out = {}
            for _ in range(arg):
                k = value()
                out[k] = value()
            return out
        if major == 6:
            return value()  # tag: ignore semantics, return content
        if major == 7:
            info = data[start] & 0x1F
            if info == 20:
                return False
            if info == 21:
                return True
            if info == 22 or info == 23:
                return None
            if info == 25:
                return struct.unpack(">e", data[start + 1:start + 3])[0]
            if info == 26:
                return struct.unpack(">f", data[start + 1:start + 5])[0]
            if info == 27:
                return struct.unpack(">d", data[start + 1:start + 9])[0]
        raise ValueError("unsupported CBOR item")

    out = value()
    if pos != len(data):
        raise ValueError("trailing bytes")
    return out


def _fresh_records(rng: random.Random, floats: bool = True) -> list[dict[str, Any]]:
    out = []
    for _ in range(rng.randint(1, 5)):
        rec: dict[str, Any] = {"id": rng.randint(-5000, 70000), "name": _word(rng, rng.randint(1, 12)), "ok": rng.random() < 0.5,
                               "tags": [_word(rng, 3) for _ in range(rng.randint(0, 3))]}
        if floats:
            rec["score"] = round(rng.uniform(-100, 100), 3)
        out.append(rec)
    if floats and not any(isinstance(r.get("score"), float) and not float(r["score"]).is_integer() for r in out):
        out[0]["score"] = 1.5
    return out


def _gen_codec(family: str, words: str, suffix: str, decoder: Callable[[bytes], Any], floats: bool = True, expect_pass: bool = True):
    def gen(rng: random.Random, work: Path, i: int) -> Case:
        work.mkdir(parents=True, exist_ok=True)
        records = _fresh_records(rng, floats=floats)
        src = work / f"{family.lower()}_{i}_{_word(rng, 4)}.json"
        src.write_text(json.dumps(records), encoding="utf-8")
        out = work / f"{family.lower()}_{i}_{_word(rng, 4)}{suffix}"
        goal = f"Encode the JSON records in {_rel(src)} with {words} and save the binary output to {_rel(out)}."

        def oracle(result: dict[str, Any]) -> tuple[bool, str]:
            if not expect_pass:
                return (not _passed(result)), "a lossy encode must fail closed; got " + str(result.get("status"))
            if not _passed(result):
                return False, "runtime did not pass: " + str(result.get("status"))
            if not out.is_file():
                return False, "binary output not written"
            try:
                decoded = decoder(out.read_bytes())
            except Exception as exc:  # noqa: BLE001 - an undecodable artifact is a failure
                return False, "independent decoder rejected the output: " + type(exc).__name__ + ":" + str(exc)
            expected = json.loads(json.dumps(records))
            return (decoded == expected), f"decoded != source records ({str(decoded)[:120]})"
        return Case(family, goal, oracle, expect_pass, [out])
    return gen


gen_codec_msgpack = _gen_codec("CODEC_MSGPACK", "the msgpack python library", ".msgpack", msgpack_decode)
gen_codec_cbor = _gen_codec("CODEC_CBOR", "the dfinity cbor npm node library", ".cbor", cbor_decode, floats=False)
gen_codec_cbor_floats = _gen_codec("CODEC_CBOR_FLOATS_FAIL_CLOSED", "the dfinity cbor npm node library", ".cbor", cbor_decode, floats=True, expect_pass=False)


# ----------------------------------------------------------------------------- sqlite

def gen_sqlite(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    wanted, other = "ACTIVE", "RETIRED"
    records = {}
    expected_rows = []
    for k in range(rng.randint(2, 6)):
        key = f"r{k}_{_word(rng, 3)}"
        status = wanted if rng.random() < 0.7 or k == 0 else other
        rec = {"status": status, "owner": _word(rng, 5), "weight": str(rng.randint(1, 99))}
        records[key] = rec
        if status == wanted:
            expected_rows.append((rec["owner"], rec["weight"]))
    src = work / f"records_{i}_{_word(rng, 4)}.json"
    src.write_text(json.dumps({"items": records}), encoding="utf-8")
    out = work / f"db_{i}_{_word(rng, 4)}.sqlite"
    table = "t_" + _word(rng, 4)
    goal = (f"Create a sqlite database table named {table} from the {wanted} records in {_rel(src)} "
            f"and save it to {_rel(out)}, with columns owner, weight.")

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:120]
        if not out.is_file():
            return False, "database not written"
        conn = sqlite3.connect(str(out))
        try:
            rows = sorted(tuple(str(c) for c in r) for r in conn.execute(f'SELECT owner, weight FROM "{table}"'))
        except sqlite3.Error as exc:
            return False, "sqlite read failed: " + str(exc)
        finally:
            conn.close()
        return (rows == sorted(expected_rows)), f"expected {sorted(expected_rows)} got {rows}"
    return Case("SQLITE_FROM_RECORDS", goal, oracle, True, [out])


GENERATORS_V2: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "JQ_QUERY": gen_jq,
    "ARCHIVE_VERIFY_GNU": gen_archive_verify,
    "PYTHON_SOURCE_AUDIT": gen_source_audit,
    "PYTHON_TESTS_AUDIT": gen_tests_audit,
    "CODEC_MSGPACK": gen_codec_msgpack,
    "CODEC_CBOR": gen_codec_cbor,
    "CODEC_CBOR_FLOATS_FAIL_CLOSED": gen_codec_cbor_floats,
    "SQLITE_FROM_RECORDS": gen_sqlite,
}
