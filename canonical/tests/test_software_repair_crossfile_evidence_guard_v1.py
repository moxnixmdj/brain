"""Imports must not be mistaken for a verified cross-file repair."""
import json

import pytest

from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as composer


@pytest.mark.parametrize("source_root", ["missing", "empty", "src", "."])
def test_no_repair_is_verified_by_importing_kernels(tmp_path, source_root):
    (tmp_path / "empty").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    result = composer.run({"source_root": source_root, "output_path": "out/result.json"}, tmp_path)
    artifact = json.loads((tmp_path / result["output_path"]).read_text(encoding="utf-8"))
    assert result["verified"] is False
    assert result["output_verified"] is False
    assert result["choreography_verified"] is False
    assert artifact["verified"] is False
    assert artifact["choreography_verified"] is False
    assert artifact["reason"] == "REPAIR_AND_VERIFICATION_NOT_EXECUTED"
