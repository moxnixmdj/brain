"""Tests for the wave-2 execution families: independent decoders, generator oracles, and the
environment-blocker accounting of the heartbeat verdict.  No live solver run here."""
from __future__ import annotations

import json
import random
import sqlite3
import tarfile
from pathlib import Path

import pytest

from execution_guard import live_solver_end_to_end_measurement_v1 as h
from execution_guard import live_solver_families_v2 as v2


# --------------------------------------------------------------------------- decoders

@pytest.mark.parametrize("hex_bytes, expected", [
    ("00", 0), ("7f", 127), ("ff", -1), ("e0", -32), ("cc80", 128), ("cd0100", 256),
    ("ce00010000", 65536), ("d0e0", -32), ("d1ff00", -256), ("d2ffff0000", -65536),
    ("c0", None), ("c2", False), ("c3", True), ("a3616263", "abc"),
    ("cb3ff8000000000000", 1.5), ("93010203", [1, 2, 3]), ("81a16101", {"a": 1}),
    ("dc0010" + "01" * 16, [1] * 16), ("c403616263", b"abc"),
])
def test_msgpack_decoder_known_vectors(hex_bytes, expected):
    assert v2.msgpack_decode(bytes.fromhex(hex_bytes)) == expected


@pytest.mark.parametrize("hex_bytes, expected", [
    ("00", 0), ("17", 23), ("1818", 24), ("190100", 256), ("1a00010000", 65536), ("20", -1), ("3863", -100),
    ("f4", False), ("f5", True), ("f6", None), ("63616263", "abc"), ("fb3ff8000000000000", 1.5),
    ("f93e00", 1.5), ("83010203", [1, 2, 3]), ("a1616101", {"a": 1}), ("9f0102ff", [1, 2]),
    ("bf616101ff", {"a": 1}), ("43616263", b"abc"), ("c11a514b67b0", 1363896240),
])
def test_cbor_decoder_known_vectors(hex_bytes, expected):
    assert v2.cbor_decode(bytes.fromhex(hex_bytes)) == expected


def test_decoders_reject_truncated_and_trailing_bytes():
    with pytest.raises(ValueError):
        v2.msgpack_decode(bytes.fromhex("93 01 02"))
    with pytest.raises(ValueError):
        v2.msgpack_decode(bytes.fromhex("01 02"))
    with pytest.raises(ValueError):
        v2.cbor_decode(bytes.fromhex("83 01 02"))
    with pytest.raises(ValueError):
        v2.cbor_decode(bytes.fromhex("01 02"))


def test_cbor_decoder_catches_the_float_truncation_of_the_bound_library():
    # @dfinity/cbor 0.2.3 encodes [{"score": 1.5}] as 81 a1 65 73636f7265 01 - the float became 1.
    decoded = v2.cbor_decode(bytes.fromhex("81a16573636f726501"))
    assert decoded == [{"score": 1}]
    assert decoded != [{"score": 1.5}]


# --------------------------------------------------------------------------- generator oracles

def _work(tmp_path: Path) -> Path:
    # generators resolve goals relative to the repository root; keep fresh inputs under its tmp dir
    w = h.ROOT / "canonical" / "astra_runtime" / "tmp" / ("t_v2_" + tmp_path.name)
    w.mkdir(parents=True, exist_ok=True)
    return w


@pytest.fixture
def work(tmp_path):
    w = _work(tmp_path)
    yield w
    import shutil
    shutil.rmtree(w, ignore_errors=True)


def test_jq_oracle_requires_runtime_pass_and_exact_text(work):
    case = v2.gen_jq(random.Random(3), work, 0)
    assert case.family == "JQ_QUERY" and case.expect_pass is True
    assert "jq filter" in case.goal and case.goal.endswith(".")
    out = case.artifacts[0]
    assert case.oracle({"pass": False, "status": "FAIL__X"})[0] is False
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False  # nothing written
    doc = json.loads(next(work.glob("doc_0_*.json")).read_text())
    filt = case.goal.split('"')[1]
    if filt == ".a.b":
        expected = str(doc["a"]["b"])
    elif filt == ".items | length":
        expected = str(len(doc["items"]))
    elif filt == "[.items[].v] | add":
        expected = str(sum(x["v"] for x in doc["items"]))
    elif filt == ".tag":
        expected = doc["tag"]
    else:
        idx = int(filt.split("[")[1].split("]")[0])
        expected = doc["items"][idx]["name"]
    out.write_text("wrong\n")
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False
    out.write_text(expected + "\n")
    assert case.oracle({"pass": True, "status": "PASS"})[0] is True


def test_archive_verify_generator_builds_intact_and_tampered_bundles(work):
    intact = v2.gen_archive_verify(random.Random(5), work, 0)
    tampered = v2.gen_archive_verify(random.Random(5), work, 2)
    assert intact.expect_pass is True and tampered.expect_pass is False
    # the tampered archive really differs from the file on disk for its first member
    arc = next(work.glob("bundle_2_*.tar.gz"))
    with tarfile.open(arc) as tf:
        names = [m.name for m in tf.getmembers() if m.name.endswith(".txt")]
        member_bytes = tf.extractfile(names[0]).read()
    assert member_bytes != (h.ROOT / names[0]).read_bytes()
    assert tampered.oracle({"pass": True, "status": "PASS"})[0] is False   # a PASS on tampered bytes is wrong
    assert tampered.oracle({"pass": False, "status": "FAIL"})[0] is True
    assert intact.oracle({"pass": False, "status": "FAIL"})[0] is False
    assert intact.oracle({"pass": True, "status": "PASS"})[0] is True


def test_source_audit_oracle_checks_exact_counts(work):
    case = v2.gen_source_audit(random.Random(11), work, 0)
    pkg = next(work.glob("srcaudit_0_*"))
    files = sorted(pkg.glob("*.py"))
    functions = sum(p.read_text().count("\ndef fn_") for p in files)
    classes = sum(p.read_text().count("\nclass C_") for p in files)
    out = case.artifacts[0]
    out.write_text(json.dumps({"totals": {"files": len(files), "functions": functions + 1, "classes": classes}}))
    assert case.oracle({"pass": True})[0] is False
    out.write_text(json.dumps({"totals": {"files": len(files), "functions": functions, "classes": classes}}))
    assert case.oracle({"pass": True})[0] is True


def test_tests_audit_generator_marks_every_fourth_suite_failing(work):
    ok_case = v2.gen_tests_audit(random.Random(2), work, 0)
    bad_case = v2.gen_tests_audit(random.Random(2), work, 3)
    assert ok_case.expect_pass is True and bad_case.expect_pass is False
    bad_src = next(work.glob("testaudit_3_*/test_gen.py")).read_text()
    assert "assertEqual(1, 2)" in bad_src
    assert bad_case.oracle({"pass": True, "status": "PASS"})[0] is False
    assert bad_case.oracle({"pass": False, "status": "FAIL"})[0] is True
    n_pass = next(work.glob("testaudit_0_*/test_gen.py")).read_text().count("def test_ok_")
    ok_case.artifacts[0].write_text(json.dumps({"totals": {"passed": n_pass, "failed": 0, "errors": 0}}))
    assert ok_case.oracle({"pass": True, "status": "PASS"})[0] is True
    ok_case.artifacts[0].write_text(json.dumps({"totals": {"passed": n_pass - 1, "failed": 1, "errors": 0}}))
    assert ok_case.oracle({"pass": True, "status": "PASS"})[0] is False


def test_codec_oracles_use_the_independent_decoders(work):
    case = v2.gen_codec_cbor(random.Random(9), work, 0)
    records = json.loads(next(work.glob("codec_cbor_0_*.json")).read_text())
    assert not any("score" in r for r in records)  # integer-domain family carries no floats
    out = case.artifacts[0]
    out.write_bytes(bytes.fromhex("81a16573636f726501"))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False
    # hand-encode the records with the stdlib (definite-length CBOR) and the oracle accepts them
    out.write_bytes(_cbor_encode(records))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is True
    floats = v2.gen_codec_cbor_floats(random.Random(9), work, 1)
    assert floats.expect_pass is False
    recs = json.loads(next(work.glob("codec_cbor_floats_fail_closed_1_*.json")).read_text())
    assert any(isinstance(r.get("score"), float) and not float(r["score"]).is_integer() for r in recs)
    assert floats.oracle({"pass": True, "status": "PASS"})[0] is False
    assert floats.oracle({"pass": False, "status": "FAIL"})[0] is True


def _cbor_encode(value) -> bytes:
    import struct

    def head(major, n):
        if n < 24:
            return bytes([(major << 5) | n])
        if n < 256:
            return bytes([(major << 5) | 24, n])
        if n < 65536:
            return bytes([(major << 5) | 25]) + struct.pack(">H", n)
        return bytes([(major << 5) | 26]) + struct.pack(">I", n)

    if value is True:
        return b"\xf5"
    if value is False:
        return b"\xf4"
    if value is None:
        return b"\xf6"
    if isinstance(value, int):
        return head(0, value) if value >= 0 else head(1, -1 - value)
    if isinstance(value, float):
        return b"\xfb" + struct.pack(">d", value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return head(3, len(raw)) + raw
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(_cbor_encode(v) for v in value)
    if isinstance(value, dict):
        return head(5, len(value)) + b"".join(_cbor_encode(k) + _cbor_encode(v) for k, v in value.items())
    raise TypeError(type(value))


def test_sqlite_oracle_reads_rows_back_with_the_stdlib(work):
    case = v2.gen_sqlite(random.Random(4), work, 0)
    assert "with columns owner, weight." in case.goal
    data = json.loads(next(work.glob("records_0_*.json")).read_text())["items"]
    table = case.goal.split("table named ")[1].split(" ")[0]
    out = case.artifacts[0]
    conn = sqlite3.connect(str(out))
    conn.execute(f'CREATE TABLE "{table}" (owner TEXT, weight TEXT)')
    conn.executemany(f'INSERT INTO "{table}" VALUES (?, ?)', [(r["owner"], r["weight"]) for r in data.values() if r["status"] == "ACTIVE"])
    conn.commit(); conn.close()
    assert case.oracle({"pass": True, "status": "PASS"})[0] is True
    conn = sqlite3.connect(str(out))
    conn.execute(f'INSERT INTO "{table}" VALUES (?, ?)', ("extra", "1")); conn.commit(); conn.close()
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False


# --------------------------------------------------------------------------- verdict accounting

def test_all_generators_include_wave_two_families():
    gens = h.all_generators()
    for fam in ("JQ_QUERY", "ARCHIVE_VERIFY_GNU", "PYTHON_SOURCE_AUDIT", "PYTHON_TESTS_AUDIT", "CODEC_MSGPACK",
                "CODEC_CBOR", "CODEC_CBOR_FLOATS_FAIL_CLOSED", "SQLITE_FROM_RECORDS", "OUT_OF_SCOPE_MUST_FAIL_CLOSED"):
        assert fam in gens


def test_environment_blocker_detection():
    assert h.environment_blocker({"reason": "Blocker:BOUND_APT_METADATA_NOT_FOUND:jq"}) == "BOUND_APT_METADATA_NOT_FOUND"
    assert h.environment_blocker({"reason": "Blocker:BOUND_PYPI_INSTALL_FAILED:error: externally-managed-environment"}) == "BOUND_PYPI_INSTALL_FAILED"
    assert h.environment_blocker({"reason": "Blocker:ACTION_EXPECTATION_FAILED:output_verified"}) is None
    assert h.environment_blocker({}) is None


def _receipt(families):
    # `run_complete` is part of the receipt contract now: a run that stopped early
    # is reported MEASUREMENT_INCOMPLETE and never ALIVE.  These tests are about
    # blocker classification and annotations, so the fixture states a finished run.
    return {"run_complete": True,
            "measurements": {"new": {"families": families, "out_of_scope_fail_closed_rate": 1.0}},
            "reachability_from_one_entry": {"summary": {"NOT_REACHABLE": 0, "ROUTED_ELSEWHERE": 0}}}


def test_environment_blockers_are_excused_only_when_asked():
    rec = _receipt({"JQ_QUERY": {"instances": 6, "oracle_pass": 0, "environment_blocked_here": 6},
                    "SQLITE_FROM_RECORDS": {"instances": 6, "oracle_pass": 6, "environment_blocked_here": 0}})
    assert h.alive_errors(rec) == []
    assert h.alive_errors(rec, environment_blockers_are_failures=True) == ["FAMILY_NOT_FULLY_PASSING:JQ_QUERY:0/6"]
    partial = _receipt({"JQ_QUERY": {"instances": 6, "oracle_pass": 3, "environment_blocked_here": 2}})
    assert h.alive_errors(partial) == ["FAMILY_NOT_FULLY_PASSING:JQ_QUERY:3/6"]


def test_annotation_lines_carry_verdict_counts_and_reasons():
    rec = _receipt({"JQ_QUERY": {"instances": 6, "oracle_pass": 0, "environment_blocked_here": 6},
                    "SQLITE_FROM_RECORDS": {"instances": 6, "oracle_pass": 6, "environment_blocked_here": 0}})
    rec["measurements"]["new"]["failures_sample"] = [
        {"family": "JQ_QUERY", "status": "FAIL__X", "why": "ENVIRONMENT_BLOCKED_HERE:BOUND_APT_METADATA_NOT_FOUND", "goal": "Run jq\nline2"}]
    excused = h.annotation_lines(rec)
    assert excused[0].startswith("::notice title=Live Brain heartbeat ALIVE::")
    assert "JQ_QUERY 0/6 (env-blocked 6)" in excused[0] and "SQLITE_FROM_RECORDS 6/6" in excused[0]
    assert not any(l.startswith("::error") for l in excused)
    strict = h.annotation_lines(rec, environment_blockers_are_failures=True)
    assert strict[0].startswith("::notice title=Live Brain heartbeat NOT ALIVE::")
    assert "::error title=NOT ALIVE::FAMILY_NOT_FULLY_PASSING:JQ_QUERY:0/6" in strict
    warning = [l for l in strict if l.startswith("::warning title=first failure in JQ_QUERY::")]
    assert len(warning) == 1 and "%0A" in warning[0] and "\n" not in warning[0]
