from pathlib import Path

from canonical.runtime import reached_escape_live_no_bypass_guard_v1 as g

ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean_fixture(root: Path) -> None:
    _write(root, "canonical/runtime/reached_escape_state_kernel_v1.py")
    _write(
        root,
        "canonical/runtime/reached_escape_finite_totality_certificate_v1.py",
        "from canonical.runtime import reached_escape_state_kernel_v1 as kernel\n",
    )
    _write(
        root,
        "canonical/runtime/certified_reached_escape_state_constructor_v1.py",
        "from canonical.runtime import reached_escape_finite_totality_certificate_v1 as finite_totality\n"
        "from canonical.runtime import reached_escape_state_kernel_v1 as kernel\n",
    )
    _write(
        root,
        "canonical/runtime/live_brain_runtime_v1.py",
        'SURFACES=("CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1",)\n'
        "def f(payload):\n"
        "    from canonical.runtime.certified_reached_escape_state_constructor_v1 import construct\n"
        "    return construct(payload)\n",
    )
    _write(
        root,
        "canonical/runtime/unified_cognitive_fabric_v1.py",
        'DIRECT={"REACHED_ESCAPE_STATE": "certified_reached_escape_state_constructor_v1.construct"}\n'
        "def f(payload):\n"
        "    from canonical.runtime import certified_reached_escape_state_constructor_v1 as reached_escape_state\n"
        "    out = reached_escape_state.construct(payload)\n"
        "    return out\n",
    )


def test_current_repository_static_runtime_census_passes():
    out = g.scan_repo(ROOT)
    assert out["pass"] is True, out
    assert out["status"] == "PASS__STATIC_PYTHON_RUNTIME_NO_LOW_LEVEL_REACHED_ESCAPE_BYPASS"
    assert out["runtime_python_file_count"] >= 1
    assert len(out["live_entrypoints"]) == 2
    assert out["global_dynamic_no_bypass_proved"] is False
    assert out["terminal_credit_delta"] == 0


def test_clean_synthetic_runtime_passes(tmp_path):
    _clean_fixture(tmp_path)
    out = g.scan_repo(tmp_path)
    assert out["pass"] is True, out


def test_third_runtime_raw_kernel_reference_fails_closed(tmp_path):
    _clean_fixture(tmp_path)
    _write(
        tmp_path,
        "canonical/runtime/rogue_consumer.py",
        "from canonical.runtime.reached_escape_state_kernel_v1 import evaluate\n",
    )
    out = g.scan_repo(tmp_path)
    assert out["pass"] is False
    assert any(
        row["code"] == "UNTRUSTED_LOW_LEVEL_REACHED_ESCAPE_REFERENCE"
        and row["path"] == "canonical/runtime/rogue_consumer.py"
        for row in out["errors"]
    )


def test_live_surface_cannot_import_safe_constructor_and_still_reference_raw_kernel(tmp_path):
    _clean_fixture(tmp_path)
    live = tmp_path / "canonical/runtime/live_brain_runtime_v1.py"
    live.write_text(
        live.read_text(encoding="utf-8")
        + "from canonical.runtime.reached_escape_state_kernel_v1 import evaluate\n",
        encoding="utf-8",
    )
    out = g.scan_repo(tmp_path)
    assert out["pass"] is False
    assert any(row["code"] == "LIVE_ENTRYPOINT_LOW_LEVEL_BYPASS_PRESENT" for row in out["errors"])


def test_missing_live_constructor_call_shape_fails_closed(tmp_path):
    _clean_fixture(tmp_path)
    live = tmp_path / "canonical/runtime/live_brain_runtime_v1.py"
    live.write_text(
        'SURFACES=("CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1",)\n'
        "def f(payload):\n"
        "    from canonical.runtime.certified_reached_escape_state_constructor_v1 import construct\n"
        "    return {'pass': True}\n",
        encoding="utf-8",
    )
    out = g.scan_repo(tmp_path)
    assert out["pass"] is False
    assert any(row["code"] == "LIVE_ENTRYPOINT_CONSTRUCTOR_BINDING_INCOMPLETE" for row in out["errors"])
