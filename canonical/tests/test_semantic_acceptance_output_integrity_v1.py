"""Semantic compilation must never replace an existing user file by accident."""
import pytest

from canonical.runtime.bound_capabilities import python_software_request_semantic_acceptance_v1 as semantic


@pytest.mark.parametrize("name", ["target.py", "existing.json"])
def test_compilation_does_not_overwrite_existing_files(tmp_path, name):
    target = tmp_path / name
    target.write_bytes(b"user data that must survive\n")
    with pytest.raises(semantic.SemanticAcceptanceError, match="OUTPUT_PATH_ALREADY_EXISTS"):
        semantic.run({"task_text": "Calling m.f with JSON arguments [] must equal 1.",
                      "output_path": name}, tmp_path)
    assert target.read_bytes() == b"user data that must survive\n"
