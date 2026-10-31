"""jq filters must not receive ambient secrets or consume extra input documents."""
import base64
import json
import shutil

import pytest

from canonical.runtime.bound_capabilities import jq_query
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as replay

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq executable not installed")


@pytest.mark.parametrize("program", [
    "env", "env | keys", 'env["BRAIN_JQ_TEST_MARKER"]',
    "env | .BRAIN_JQ_TEST_MARKER",
])
def test_environment_primitives_are_refused(tmp_path, monkeypatch, program):
    monkeypatch.setenv("BRAIN_JQ_TEST_MARKER", "synthetic-test-marker-only")
    (tmp_path / "input.json").write_text('{}\n')
    with pytest.raises(RuntimeError, match="JQ_FILTER_FORBIDDEN"):
        jq_query.run({"input_path": "input.json", "output_path": "out.json", "filter": program}, tmp_path)
    assert not (tmp_path / "out.json").exists()


def test_child_has_empty_environment_even_if_filter_guard_is_bypassed(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_JQ_TEST_MARKER", "synthetic-test-marker-only")
    monkeypatch.setattr(jq_query, "FORBIDDEN_FILTER_PATTERNS", ())
    (tmp_path / "input.json").write_text('{}\n')
    jq_query.run({"input_path": "input.json", "output_path": "out.json", "filter": "env"}, tmp_path)
    assert json.loads((tmp_path / "out.json").read_text()) == {}


def test_bare_input_primitive_is_refused(tmp_path):
    (tmp_path / "input.json").write_text('{}\n{"second":"synthetic"}\n')
    with pytest.raises(RuntimeError, match="JQ_FILTER_FORBIDDEN"):
        jq_query.run({"input_path": "input.json", "output_path": "out.json", "filter": "input"}, tmp_path)
    assert not (tmp_path / "out.json").exists()


@pytest.mark.parametrize("program,expected", [('.env', '"ok"\n'), ('.input', '"value"\n')])
def test_object_fields_remain_usable(tmp_path, program, expected):
    (tmp_path / "input.json").write_text(json.dumps({"env": "ok", "input": "value"}))
    result = jq_query.run({"input_path": "input.json", "output_path": "out.json", "filter": program,
                           "raw_output": False}, tmp_path)
    assert result["output_verified"] is True
    assert (tmp_path / "out.json").read_text() == expected


def test_jq_callsite_accepts_only_empty_custom_environment(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{}')
    context = {"effect_class": replay.EFFECT_CLASS,
               "callsite": {"module_path": "canonical/runtime/bound_capabilities/jq_query.py",
                            "lineno": 41, "process_api": "subprocess.run"},
               "args": [["jq", "-r", ".", str(source)]],
               "kwargs": {"cwd": str(tmp_path), "capture_output": True, "text": True,
                          "timeout": 60, "env": {}}}
    prepared = replay._prepare(context)
    assert prepared["profile"] == "JQ"
    encoded = prepared["policy"]["argv"][-1]
    spec = json.loads(base64.urlsafe_b64decode(encoded))
    assert spec["empty_env"] is True
    for forbidden in ("env", "input"):
        context["args"][0][-2] = forbidden
        with pytest.raises(replay.ReadOnlyQueryDenied, match="JQ_FILTER_FORBIDDEN"):
            replay._prepare(context)
    context["args"][0][-2] = "."
    context["kwargs"]["env"] = {"BRAIN_JQ_TEST_MARKER": "not-allowed"}
    with pytest.raises(replay.ReadOnlyQueryDenied, match="CUSTOM_ENV_FORBIDDEN"):
        replay._prepare(context)
