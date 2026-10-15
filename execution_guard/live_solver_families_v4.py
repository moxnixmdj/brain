from __future__ import annotations

import json
import random
import re
import zipfile
from pathlib import Path
from typing import Any, Callable
import xml.etree.ElementTree as ET

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _passed, gen_source_audit


_XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _xlsx_rows(path: Path) -> list[list[Any]]:
    """Read the first worksheet with stdlib OOXML parsing, independent of its producer."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(_XLSX_NS + "si")]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[Any]] = []
    data = sheet.find(_XLSX_NS + "sheetData")
    if data is None:
        return rows
    for row in data.findall(_XLSX_NS + "row"):
        values: list[Any] = []
        for cell in row.findall(_XLSX_NS + "c"):
            kind = cell.get("t")
            if kind == "inlineStr":
                inline = cell.find(_XLSX_NS + "is")
                value: Any = "" if inline is None else "".join(inline.itertext())
            else:
                node = cell.find(_XLSX_NS + "v")
                raw = "" if node is None or node.text is None else node.text
                if kind == "s" and raw:
                    value = shared[int(raw)]
                elif raw and re.fullmatch(r"-?\d+", raw):
                    value = int(raw)
                elif raw:
                    try:
                        value = float(raw)
                    except ValueError:
                        value = raw
                else:
                    value = ""
            values.append(value)
        rows.append(values)
    return rows


def gen_docx_create(rng: random.Random, tmp: Path, index: int) -> Case:
    out = tmp / f"wave4_doc_{index}.docx"
    title = f"Report {_word(rng).title()} {index}"
    paragraph = f"This document covers {_word(rng)} and {_word(rng)} analysis"
    table_item = _word(rng)
    table_score = rng.randint(10, 99)
    headers = ["item", "score"]
    rows = [[table_item, str(table_score)]]
    goal = (
        f"Create {_rel(out)} with title {title}, paragraph {paragraph}, "
        f"and a table with headers item and score containing {table_item} | {table_score}."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file() or out.stat().st_size == 0:
            return False, "DOCX output not written"
        from canonical.runtime.bound_capabilities import docx_verify_ooxml
        checked = docx_verify_ooxml.run(
            {
                "path": _rel(out),
                "expected": {"title": title, "paragraphs": [paragraph], "headers": headers, "rows": rows},
            },
            ROOT,
        )
        return bool(checked.get("verified")), "independent OOXML verification: " + str(checked)

    return Case("DOCX_CREATE", goal, oracle, True, [out, Path(str(out) + ".intent.json")])


def gen_xlsx_create(rng: random.Random, tmp: Path, index: int) -> Case:
    out = tmp / f"wave4_xlsx_output_{index}.xlsx"
    data_path = tmp / f"wave4_xlsx_input_{index}.json"
    headers = ["item", "count", "score"]
    rows = [
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
    ]
    records = [dict(zip(headers, row)) for row in rows]
    data_path.write_text(json.dumps({"records": records}), encoding="utf-8")
    goal = f"Create an XLSX spreadsheet workbook at {_rel(out)} from {_rel(data_path)} with columns item, count, score."

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file() or out.stat().st_size == 0:
            return False, "XLSX output not written"
        try:
            observed = _xlsx_rows(out)
        except Exception as exc:
            return False, "XLSX OOXML could not be read: " + type(exc).__name__ + ": " + str(exc)
        expected = [headers] + rows
        return observed == expected, f"expected rows {expected!r}, got {observed!r}"

    return Case("XLSX_CREATE", goal, oracle, True, [out])


def gen_xlsx_verify(rng: random.Random, tmp: Path, index: int) -> Case:
    from canonical.runtime.bound_capabilities import xlsx_table_xlsxwriter

    sheet_path = tmp / f"wave4_verify_output_{index}.xlsx"
    data_path = tmp / f"wave4_verify_input_{index}.json"
    headers = ["item", "count", "score"]
    rows = [
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
        [_word(rng), rng.randint(10, 50), rng.randint(70, 100)],
    ]
    records = [dict(zip(headers, row)) for row in rows]
    data_path.write_text(json.dumps({"records": records}), encoding="utf-8")
    create_goal = f"Create {_rel(sheet_path)} from {_rel(data_path)} with columns item, count, score."
    xlsx_table_xlsxwriter.run(
        {"json_path": _rel(data_path), "output_path": _rel(sheet_path), "goal": create_goal}, ROOT
    )
    expected_rows = [headers] + rows
    goal = (
        f"Verify the XLSX spreadsheet at {_rel(sheet_path)} against the JSON records at {_rel(data_path)} "
        "with columns item, count, score."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        execution = result.get("execution") or []
        verified = any(
            isinstance(row, dict)
            and isinstance(row.get("result"), dict)
            and row["result"].get("verified") is True
            for row in execution
        )
        if not verified:
            return False, "live route did not return a verified result"
        try:
            observed = _xlsx_rows(sheet_path)
        except Exception as exc:
            return False, "independent XLSX read failed: " + type(exc).__name__ + ": " + str(exc)
        return observed == expected_rows, f"expected rows {expected_rows!r}, got {observed!r}"

    return Case("XLSX_VERIFY", goal, oracle, True, [])


def gen_bm25_ranking(rng: random.Random, tmp: Path, index: int) -> Case:
    out_ranked = tmp / f"wave4_bm25_output_{index}.json"
    docs_path = tmp / f"wave4_bm25_input_{index}.json"
    docs = [
        {"id": "doc1", "title": "Quantum computing algorithms", "snippet": "Qubit algorithms and quantum computation methods"},
        {"id": "doc2", "title": "Neural networks", "snippet": "Transformer self-attention and deep learning systems"},
        {"id": "doc3", "title": "Cellular biology", "snippet": "Genetic sequencing and cell structures"},
        {"id": "doc4", "title": "Quantum cryptography", "snippet": "Key distribution security protocols"},
    ]
    docs_path.write_text(
        json.dumps({"objective": "Which source discusses quantum computing algorithms?", "candidates": docs}),
        encoding="utf-8",
    )
    goal = (
        f"Rank the source candidates in {_rel(docs_path)} by BM25 objective relevance "
        f"and save the rankings to {_rel(out_ranked)}."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out_ranked.is_file():
            return False, "ranking output not written"
        try:
            ranked = json.loads(out_ranked.read_text(encoding="utf-8"))
            candidates = ranked.get("ranked_candidates") or []
            winner = candidates[0].get("candidate", {}).get("id") if candidates else None
            ok = ranked.get("status") == "LEXICAL_RELEVANCE_RANKED" and winner == "doc1"
            return ok, "expected doc1 as lexical BM25 leader; got " + str(winner)
        except Exception as exc:
            return False, "ranking output invalid: " + type(exc).__name__ + ": " + str(exc)

    return Case("SOURCE_RANKING_BM25", goal, oracle, True, [out_ranked])


def gen_decision_synthesis(rng: random.Random, tmp: Path, index: int) -> Case:
    out_decision = tmp / f"wave4_decision_output_{index}.json"
    evidence_path = tmp / f"wave4_decision_input_{index}.json"
    evidence = {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": f"WAVE4-{index}-{rng.randint(1000, 9999)}",
        "question": "Which cache satisfies the durable clustered service requirements?",
        "alternatives": [
            {"id": "REDIS", "label": "Redis"},
            {"id": "MEMCACHED", "label": "Memcached"},
            {"id": "LOCAL", "label": "Local memory"},
        ],
        "constraints": [
            {"id": "redis-persistence", "alternative": "REDIS", "required": True, "state": "SATISFIED", "description": "Persistence is required and provided.", "provenance": [{"source": "test-fixture", "ref": "redis-persistence"}]},
            {"id": "redis-cluster", "alternative": "REDIS", "required": True, "state": "SATISFIED", "description": "Cluster support is required and provided.", "provenance": [{"source": "test-fixture", "ref": "redis-cluster"}]},
            {"id": "memcached-persistence", "alternative": "MEMCACHED", "required": True, "state": "VIOLATED", "description": "Persistence is required but unavailable.", "provenance": [{"source": "test-fixture", "ref": "memcached-persistence"}]},
            {"id": "local-persistence", "alternative": "LOCAL", "required": True, "state": "VIOLATED", "description": "Persistence is required but unavailable.", "provenance": [{"source": "test-fixture", "ref": "local-persistence"}]},
        ],
        "evidence": [
            {"id": "redis-support", "alternative": "REDIS", "relation": "SUPPORTS", "confidence": 0.95, "strength": 1.0, "independence_group": "redis-docs", "claim": "Redis supports persistence and clustering.", "provenance": [{"source": "test-fixture", "ref": "redis-evidence"}]},
            {"id": "memcached-support", "alternative": "MEMCACHED", "relation": "SUPPORTS", "confidence": 0.8, "strength": 1.0, "independence_group": "memcached-docs", "claim": "Memcached supports clustering.", "provenance": [{"source": "test-fixture", "ref": "memcached-evidence"}]},
            {"id": "local-support", "alternative": "LOCAL", "relation": "SUPPORTS", "confidence": 0.8, "strength": 1.0, "independence_group": "local-docs", "claim": "Local memory has low latency.", "provenance": [{"source": "test-fixture", "ref": "local-evidence"}]},
        ],
        "policy": {"minimum_support_ratio": 0.6, "maximum_conflict_ratio": 0.5, "minimum_independent_support_groups": 1, "minimum_net_margin": 0.1},
    }
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    goal = (
        f"Using typed decision evidence at {_rel(evidence_path)}, synthesize the decision "
        f"to {_rel(out_decision)}."
    )

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out_decision.is_file():
            return False, "decision output not written"
        try:
            decision = json.loads(out_decision.read_text(encoding="utf-8"))
            ok = decision.get("status") == "DECIDED" and decision.get("selected_alternative") == "REDIS"
            return ok, "expected DECIDED/REDIS; got " + str((decision.get("status"), decision.get("selected_alternative")))
        except Exception as exc:
            return False, "decision output invalid: " + type(exc).__name__ + ": " + str(exc)

    return Case("DECISION_SYNTHESIS", goal, oracle, True, [out_decision])


def gen_python_source_audit(rng: random.Random, tmp: Path, index: int) -> Case:
    case = gen_source_audit(rng, tmp, index)
    return Case(case.family, case.goal, case.oracle, case.expect_pass, case.artifacts)


GENERATORS_V4: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "DOCX_CREATE": gen_docx_create,
    "XLSX_CREATE": gen_xlsx_create,
    "XLSX_VERIFY": gen_xlsx_verify,
    "SOURCE_RANKING_BM25": gen_bm25_ranking,
    "DECISION_SYNTHESIS": gen_decision_synthesis,
    "PYTHON_SOURCE_AUDIT": gen_python_source_audit,
}
