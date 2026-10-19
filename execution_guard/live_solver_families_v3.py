"""Fresh-goal EXECUTION families, wave 3 (heartbeat).  Same contract as wave 2: fresh inputs,
one plain sentence, an oracle that judges the real artifact with the standard library only.

  CODEC_MSGPACK_NPM        auto.npm.msgpack-msgpack              hand-written msgpack reader
  CODEC_BSON               auto.pypi.bson-modern                 hand-written BSON reader
  SQLITE_VERIFY_RECORDS    sqlite.table.verify_against_json_records   db built with sqlite3; one
                                                                 in three has a tampered row and
                                                                 MUST be refused
  YAML_TO_JSON             yaml.to_json.yq                       YAML written by hand, JSON read
                                                                 back and compared to the source
                                                                 structure
  PDF_TEXT_EXTRACT         pdf.extract.text.pypdf                PDF assembled by hand; result text
                                                                 must contain every fresh word
  NUMERIC_EXPRESSION       math.numeric_expression.sympy         value recomputed with a restricted
                                                                 AST evaluator
  PYTHON_REPAIR_TEST_GUIDED python.software.repair.loop.test_guided.ast.v1
                                                                 a fresh single-point bug; the unit
                                                                 tests are re-run in a separate
                                                                 python process afterwards
"""
from __future__ import annotations

import ast
import json
import operator
import os
import random
import shutil
import sqlite3
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _gen_codec, _passed, msgpack_decode


# ----------------------------------------------------------------------------- BSON reader

def bson_decode(data: bytes):
    """Minimal independent BSON reader: double, string, document, array, bool, null, int32, int64."""
    pos = 0

    def rd(n: int) -> bytes:
        nonlocal pos
        chunk = data[pos:pos + n]
        if len(chunk) != n:
            raise ValueError("truncated")
        pos += n
        return chunk

    def cstring() -> str:
        nonlocal pos
        end = data.index(b"\x00", pos)
        s = data[pos:end].decode("utf-8")
        pos = end + 1
        return s

    def document() -> dict:
        nonlocal pos
        start = pos
        (length,) = struct.unpack("<i", rd(4))
        out: dict[str, Any] = {}
        while True:
            t = rd(1)[0]
            if t == 0:
                break
            name = cstring()
            if t == 0x01:
                (out[name],) = struct.unpack("<d", rd(8))
            elif t == 0x02:
                (n,) = struct.unpack("<i", rd(4))
                raw = rd(n)
                if raw[-1:] != b"\x00":
                    raise ValueError("string not terminated")
                out[name] = raw[:-1].decode("utf-8")
            elif t == 0x03:
                out[name] = document()
            elif t == 0x04:
                sub = document()
                out[name] = [sub[str(i)] for i in range(len(sub))]
            elif t == 0x08:
                b = rd(1)[0]
                if b not in (0, 1):
                    raise ValueError("bad boolean")
                out[name] = bool(b)
            elif t == 0x0A:
                out[name] = None
            elif t == 0x10:
                (out[name],) = struct.unpack("<i", rd(4))
            elif t == 0x12:
                (out[name],) = struct.unpack("<q", rd(8))
            else:
                raise ValueError("unsupported BSON element type 0x%02x" % t)
        if pos - start != length:
            raise ValueError("document length mismatch")
        return out

    out = document()
    if pos != len(data):
        raise ValueError("trailing bytes")
    return out


def _bson_envelope_decoder(data: bytes):
    doc = bson_decode(data)
    if set(doc) != {"__project_brain_payload__"}:
        raise ValueError("envelope key missing: " + ",".join(sorted(doc)))
    return doc["__project_brain_payload__"]


gen_codec_msgpack_npm = _gen_codec("CODEC_MSGPACK_NPM", "the msgpack npm node library", ".msgpack", msgpack_decode)
gen_codec_bson = _gen_codec("CODEC_BSON", "the bson modern python library", ".bson", _bson_envelope_decoder)


# ----------------------------------------------------------------------------- sqlite verify

def gen_sqlite_verify(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    wanted, other = "ACTIVE", "RETIRED"
    records: dict[str, dict[str, str]] = {}
    for k in range(rng.randint(2, 6)):
        status = wanted if rng.random() < 0.7 or k == 0 else other
        records[f"cap_{k}_{_word(rng, 3)}"] = {"status": status, "owner": _word(rng, 5), "weight": str(rng.randint(1, 99))}
    src = work / f"vrecords_{i}_{_word(rng, 4)}.json"
    src.write_text(json.dumps({"items": records}), encoding="utf-8")
    db = work / f"vdb_{i}_{_word(rng, 4)}.sqlite"
    table = "v_" + _word(rng, 4)
    tamper = (i % 3 == 2)
    conn = sqlite3.connect(str(db))
    conn.execute(f'CREATE TABLE "{table}" (capability_id TEXT, owner TEXT, weight TEXT)')
    rows = [(key, rec["owner"], rec["weight"]) for key, rec in records.items() if rec["status"] == wanted]
    if tamper:
        key, owner, weight = rows[0]
        rows[0] = (key, owner + "x", weight)  # one cell differs from the records
    conn.executemany(f'INSERT INTO "{table}" VALUES (?, ?, ?)', rows)
    conn.commit()
    conn.close()
    goal = rng.choice([
        f"Verify the sqlite database {_rel(db)} against the {wanted} records in {_rel(src)} for the table named {table}.",
        f"Check the sqlite database {_rel(db)} against the {wanted} records in {_rel(src)} for the table named {table}.",
        f"Verify, for the table named {table}, the sqlite database {_rel(db)} against the {wanted} records in {_rel(src)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if tamper:
            return (not _passed(result)), "a database with a changed cell must be refused; got " + str(result.get("status"))
        if not _passed(result):
            return False, "matching database refused: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        return True, ""
    return Case("SQLITE_VERIFY_RECORDS", goal, oracle, not tamper, [])


# ----------------------------------------------------------------------------- yaml -> json

def gen_yaml_to_json(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    data = {
        "name": _word(rng, 6),
        "count": rng.randint(0, 5000),
        "enabled": rng.random() < 0.5,
        "tags": [_word(rng, 4) for _ in range(rng.randint(1, 4))],
        "owner": {"id": rng.randint(1, 99), "handle": _word(rng, 5)},
    }
    lines = [f"name: {data['name']}", f"count: {data['count']}", f"enabled: {'true' if data['enabled'] else 'false'}", "tags:"]
    lines += [f"  - {t}" for t in data["tags"]]
    lines += ["owner:", f"  id: {data['owner']['id']}", f"  handle: {data['owner']['handle']}"]
    src = work / f"cfg_{i}_{_word(rng, 4)}.yaml"
    src.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = work / f"cfg_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f"Convert the yaml file {_rel(src)} to json with yq and save it to {_rel(out)}.",
        f"Convert the yaml file {_rel(src)} into json with yq and write it to {_rel(out)}.",
        f"With yq, convert the yaml file {_rel(src)} to json and save the result to {_rel(out)}.",
        f"Parse the yaml file {_rel(src)} into json with yq and save it to {_rel(out)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "json output not written"
        try:
            got = json.loads(out.read_text(encoding="utf-8"))
        except ValueError as exc:
            return False, "output is not JSON: " + str(exc)
        return (got == data), f"json differs from the yaml source ({str(got)[:120]})"
    return Case("YAML_TO_JSON", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- pdf text

def _minimal_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with Helvetica text, assembled by hand (valid xref table)."""
    content = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for k, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.append(("(" + safe + ") Tj") if k == 0 else ("T* (" + safe + ") Tj"))
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def gen_pdf_text(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    words = [_word(rng, rng.randint(5, 9)) for _ in range(rng.randint(3, 6))]
    lines = [" ".join(words[:2]), " ".join(words[2:])]
    pdf = work / f"paper_{i}_{_word(rng, 4)}.pdf"
    pdf.write_bytes(_minimal_pdf(lines))
    goal = rng.choice([
        f"Extract the text from the pdf document {_rel(pdf)} with pypdf.",
        f"Read the text out of the pdf document {_rel(pdf)} with pypdf.",
        f"Extract the text of the pdf document {_rel(pdf)} with pypdf.",
        f"With pypdf, extract the text from the pdf document {_rel(pdf)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        text = None
        for row in result.get("execution") or []:
            inner = row.get("result") if isinstance(row, dict) else None
            if isinstance(inner, dict) and isinstance(inner.get("text"), str):
                text = inner["text"]
        if text is None:
            return False, "no text field in the execution result"
        missing = [w for w in words if w not in text]
        return (not missing), f"words missing from extracted text: {missing} (text={text[:80]!r})"
    return Case("PDF_TEXT_EXTRACT", goal, oracle, True, [])


# ----------------------------------------------------------------------------- numeric expression

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}


def safe_eval(expression: str, variables: dict[str, float]) -> float:
    """Independent evaluator for + - * / ** with numeric literals and named variables only."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name):
            return variables[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("unsupported syntax: " + type(node).__name__)
    return ev(ast.parse(expression, mode="eval"))


def gen_numeric_expression(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    x, y, z = rng.randint(1, 12), rng.randint(1, 12), rng.randint(2, 9)
    a, b, c = rng.randint(2, 9), rng.randint(1, 30), rng.randint(1, 5)
    shape = rng.randrange(4)
    if shape == 0:
        expr = f"{a}*x**2 - y/{c} + {b}"
    elif shape == 1:
        expr = f"(x + y)*{a} - z**2"
    elif shape == 2:
        expr = f"x*y - {b}/z + {c}"
    else:
        expr = f"{a}*(x - y) + z*{c} - {b}"
    variables = {"x": x, "y": y, "z": z}
    expected = safe_eval(expr, variables)
    out = work / f"expr_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f'Evaluate the numeric expression "{expr}" with variables x = {x}, y = {y}, z = {z} using sympy and save the result to {_rel(out)}.',
        f'Using sympy, evaluate the numeric expression "{expr}" with variables x = {x}, y = {y}, z = {z} and save the result to {_rel(out)}.',
        f'Evaluate the expression "{expr}" with variables x = {x}, y = {y}, z = {z} using sympy and write the result to {_rel(out)}.',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "result file not written"
        payload = json.loads(out.read_text(encoding="utf-8"))
        value = payload.get("value") if isinstance(payload, dict) else None
        if not isinstance(value, (int, float)):
            return False, "no numeric value in result file"
        ok = abs(float(value) - expected) <= 1e-9 * max(1.0, abs(expected))
        return ok, f"expected {expected} got {value}"
    return Case("NUMERIC_EXPRESSION", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- python repair

def apply_unified_diff(original: str, diff: str) -> str:
    """Apply a unified diff to ``original`` (stdlib only); raises ValueError on any mismatch."""
    src = original.splitlines(keepends=True)
    out: list[str] = []
    pos = 0
    lines = diff.splitlines(keepends=True)
    k = 0
    while k < len(lines) and not lines[k].startswith("@@"):
        k += 1
    if k == len(lines):
        raise ValueError("no hunk")
    while k < len(lines):
        header = lines[k]
        if not header.startswith("@@"):
            k += 1
            continue
        inner = header.split("@@")[1].strip()
        old_spec = inner.split(" ")[0]
        old_start = int(old_spec[1:].split(",")[0])
        start = old_start - 1 if old_start > 0 else 0
        if start < pos:
            raise ValueError("overlapping hunks")
        out.extend(src[pos:start])
        pos = start
        k += 1
        while k < len(lines) and not lines[k].startswith("@@"):
            line = lines[k]
            k += 1
            if line.startswith("\\"):
                continue
            tag, body = line[:1], line[1:]
            if tag == " ":
                if pos >= len(src) or src[pos] != body:
                    raise ValueError("context mismatch at line %d" % (pos + 1))
                out.append(src[pos]); pos += 1
            elif tag == "-":
                if pos >= len(src) or src[pos] != body:
                    raise ValueError("removed line mismatch at line %d" % (pos + 1))
                pos += 1
            elif tag == "+":
                out.append(body)
            elif line.strip() == "":
                if pos < len(src) and src[pos].strip() == "":
                    out.append(src[pos]); pos += 1
            else:
                raise ValueError("bad diff line: " + line[:20])
    out.extend(src[pos:])
    return "".join(out)

class _FreshBug:
    def __init__(self, d: Path, src: Path, test_files: list[Path], source: str, tests: dict[Path, str], buggy_function: str):
        self.d, self.src, self.test_files, self.source, self.tests, self.buggy_function = d, src, test_files, source, tests, buggy_function

    def tests_phrase(self) -> str:
        return ", ".join(_rel(t) for t in self.test_files)

    @property
    def all_test(self) -> Path:
        return next(t for t in self.tests if t.name.endswith("_all.py"))


def fresh_bug(rng: random.Random, work: Path, i: int, prefix: str = "repair") -> _FreshBug:
    """A module with three functions, one carrying a fresh single-point bug (a flipped operator),
    and a unittest file that exposes exactly that bug."""
    d = work / f"{prefix}_{i}_{_word(rng, 4)}"
    d.mkdir(parents=True, exist_ok=True)
    mod = "calc_" + _word(rng, 5)
    f1, f2, f3 = (_word(rng, 6) for _ in range(3))
    k = rng.randint(2, 9)
    bug = rng.randrange(3)
    body1 = f"def {f1}(a, b):\n    return a + b * {k}\n"
    body2 = f"def {f2}(n):\n    total = 0\n    for v in range(n):\n        total = total + v\n    return total\n"
    body3 = f"def {f3}(v, limit):\n    if v < limit:\n        return 'low'\n    return 'high'\n"
    if bug == 0:
        buggy1, buggy2, buggy3, buggy_function = body1.replace("a + b", "a - b"), body2, body3, f1
    elif bug == 1:
        buggy1, buggy2, buggy3, buggy_function = body1, body2.replace("total + v", "total - v"), body3, f2
    else:
        buggy1, buggy2, buggy3, buggy_function = body1, body2, body3.replace("v < limit", "v <= limit"), f3
    source = "\n".join([buggy1, buggy2, buggy3])
    src = d / f"{mod}.py"
    src.write_text(source, encoding="utf-8")
    a, b = rng.randint(1, 20), rng.randint(1, 20)
    n = rng.randint(3, 9)
    lim = rng.randint(5, 50)
    head = ["import os, sys", "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))", f"import {mod} as m"]
    checks = {
        f1: [f"assert m.{f1}({a}, {b}) == {a + b * k}", f"assert m.{f1}(0, 1) == {k}"],
        f2: [f"assert m.{f2}({n}) == {sum(range(n))}", f"assert m.{f2}(1) == 0"],
        f3: [f"assert m.{f3}({lim - 1}, {lim}) == 'low'", f"assert m.{f3}({lim}, {lim}) == 'high'", f"assert m.{f3}({lim + 3}, {lim}) == 'high'"],
    }
    # plain assert scripts (the declared input class of the bound localizer and repair loops):
    # one per function so a failing-versus-passing spectrum exists, plus one that checks everything
    tests: dict[Path, str] = {}
    for fn, lines in checks.items():
        tests[d / f"test_{mod}_{fn}.py"] = "\n".join(head + lines) + "\n"
    # the strict-progress loop measures progress from unittest's "FAILED (failures=N)" line
    unit = ["import os, sys, unittest", "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))", f"import {mod} as m", "", "class T(unittest.TestCase):"]
    for fn, lines in checks.items():
        unit.append(f"    def test_{fn}(self):")
        unit += ["        " + c.replace("assert ", "self.assertTrue(") + ")" for c in lines]
    unit += ["", "if __name__ == '__main__':", "    unittest.main()", ""]
    tests[d / f"test_{mod}_all.py"] = "\n".join(unit)
    for path, text in tests.items():
        path.write_text(text, encoding="utf-8")
    return _FreshBug(d, src, sorted(t for t in tests if not t.name.endswith("_all.py")), source, tests, buggy_function)


def _patch_oracle(bug: _FreshBug, out: Path):
    d, src, source = bug.d, bug.src, bug.source

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        if not out.is_file():
            return False, "repair report not written"
        if src.read_text(encoding="utf-8") != source:
            return False, "the tool wrote to the source although it has no source-write authority"
        report = json.loads(out.read_text(encoding="utf-8"))
        patches = report.get("patches") if isinstance(report, dict) else None
        if not isinstance(patches, list) or not patches:
            return False, "report carries no patch"
        diffs = [str(p.get("unified_diff") or "") for p in patches if isinstance(p, dict) and p.get("source_path") == _rel(src)]
        if len(diffs) != 1:
            return False, f"expected one patch for the source, found {len(diffs)}"
        try:
            patched = apply_unified_diff(source, diffs[0])
        except ValueError as exc:
            return False, "patch does not apply cleanly: " + str(exc)
        if patched == source:
            return False, "patch is empty"
        trial = d / "_oracle_trial"
        shutil.rmtree(trial, ignore_errors=True)  # never let a stale __pycache__ of an earlier candidate answer
        trial.mkdir()
        (trial / src.name).write_text(patched, encoding="utf-8")
        for path, text in bug.tests.items():
            (trial / path.name).write_text(text, encoding="utf-8")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for path in bug.tests:
            proc = subprocess.run([sys.executable, "-B", path.name], cwd=str(trial), capture_output=True, text=True, timeout=60, env=env)
            if proc.returncode != 0:
                return False, f"{path.name} still fails with the proposed patch: " + (proc.stderr or proc.stdout)[-200:]
        return True, ""
    return oracle


def gen_python_repair(rng: random.Random, work: Path, i: int) -> Case:
    bug = fresh_bug(rng, work, i, "repair")
    src = bug.src
    out = work / f"repair_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f"Repair the python source {_rel(src)} with the test guided repair loop so that the unit tests in {bug.tests_phrase()} pass, "
        f"and save the repair report to {_rel(out)}.",
        f"Repair the python source {_rel(src)} with the test guided repair loop so that the unit tests in {bug.tests_phrase()} pass; "
        f"save the repair report to {_rel(out)}.",
        f"With the test guided repair loop, repair the python source {_rel(src)} so that the unit tests in {bug.tests_phrase()} pass, "
        f"and write the repair report to {_rel(out)}.",
    ])

    oracle = _patch_oracle(bug, out)
    return Case("PYTHON_REPAIR_TEST_GUIDED", goal, oracle, True, [out])


def gen_python_repair_strict(rng: random.Random, work: Path, i: int) -> Case:
    bug = fresh_bug(rng, work, i, "strict")
    out = work / f"strict_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f"Run the strict progress repair loop on the python source root {_rel(bug.d)} with the test {_rel(bug.all_test)} "
        f"and test command \"{sys.executable} {_rel(bug.all_test)}\", and save the repair report to {_rel(out)}.",
        f"Run the strict progress repair loop on the python source root {_rel(bug.d)} with the test {_rel(bug.all_test)} "
        f"and test command \"{sys.executable} {_rel(bug.all_test)}\", and write the repair report to {_rel(out)}.",
    ])
    return Case("PYTHON_REPAIR_STRICT_PROGRESS", goal, _patch_oracle(bug, out), True, [out])


def gen_python_fault_localize(rng: random.Random, work: Path, i: int) -> Case:
    bug = fresh_bug(rng, work, i, "fault")
    out = work / f"fault_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f"Localize the fault in the python source root {_rel(bug.d)} with the dynamic dataflow fault localizer "
        f"using the tests {bug.tests_phrase()}, and save the localization report to {_rel(out)}.",
        f"Localize the fault in the python source root {_rel(bug.d)} with the dynamic dataflow fault localizer "
        f"using the tests {bug.tests_phrase()}, and write the localization report to {_rel(out)}.",
    ])
    src_rel = _rel(bug.src)

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        if not out.is_file():
            return False, "localization report not written"
        report = json.loads(out.read_text(encoding="utf-8"))
        symbols = [x for x in (report.get("ranked_symbols") or []) if isinstance(x, dict) and x.get("path") == src_rel and x.get("kind") == "FunctionDef"]
        if not symbols:
            return False, "no ranked function in the source module"
        top = symbols[0]
        if top.get("symbol") != bug.buggy_function:
            return False, f"top-ranked function {top.get('symbol')!r} is not the buggy one {bug.buggy_function!r}"
        if report.get("failing_test_count") != 1:
            return False, f"expected exactly one failing test, report says {report.get('failing_test_count')}"
        return True, ""
    return Case("PYTHON_FAULT_LOCALIZE", goal, oracle, True, [out])


GENERATORS_V3: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "CODEC_MSGPACK_NPM": gen_codec_msgpack_npm,
    "CODEC_BSON": gen_codec_bson,
    "SQLITE_VERIFY_RECORDS": gen_sqlite_verify,
    "YAML_TO_JSON": gen_yaml_to_json,
    "PDF_TEXT_EXTRACT": gen_pdf_text,
    "NUMERIC_EXPRESSION": gen_numeric_expression,
    "PYTHON_REPAIR_TEST_GUIDED": gen_python_repair,
    "PYTHON_REPAIR_STRICT_PROGRESS": gen_python_repair_strict,
    "PYTHON_FAULT_LOCALIZE": gen_python_fault_localize,
}
