import json
import struct
import tempfile
from pathlib import Path

from canonical.runtime.chartography_synthetic_reasoning_suite_v1 import EXPECTED, generate_suite, verify_generated


def test_exact_six_case_suite_recomputes():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        manifest=generate_suite(root)
        out=verify_generated(manifest)
        assert out["pass"] is True, out
        assert out["case_count"] == 6
        assert out["distinct_skill_count"] == 6
        assert out["terminal_cases_consumed"] == 0
        assert out["judge_calls"] == 0
        for row in manifest:
            expected,sha=EXPECTED[row["case_id"]]
            assert row["expected"] == expected
            assert row["sha256"] == sha
            data=(root/row["file"]).read_bytes()
            assert data[:2] == b"BM"
            width,height=struct.unpack_from("<II",data,18)
            assert (width,height)==(256,192)


def test_hash_mutation_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        manifest=generate_suite(Path(td))
        bad=json.loads(json.dumps(manifest))
        bad[0]["sha256"]="0"*64
        out=verify_generated(bad)
        assert out["pass"] is False
        assert "HASH_DRIFT:1" in out["errors"]


def test_suite_source_has_no_external_dataset_or_model_judge():
    source=(Path(__file__).resolve().parents[1]/"runtime"/"chartography_synthetic_reasoning_suite_v1.py").read_text()
    for forbidden in ("requests", "huggingface", "ChartQA", "PlotQA", "gemini", "openai", "anthropic"):
        assert forbidden not in source
