from canonical.runtime.current_authority_runtime_census_v1 import _runtime_paths


def test_runtime_path_extraction_is_recursive_and_exact():
    doc = {
        "a": {"runtime": {"path": "canonical/runtime/a.py"}},
        "b": [
            "canonical/runtime/b.py",
            "canonical/governance/not_runtime.json",
            {"nested": "canonical/runtime/c.py"},
        ],
        "noise": "canonical/runtime/not-python.txt",
    }
    assert _runtime_paths(doc) == {
        "canonical/runtime/a.py",
        "canonical/runtime/b.py",
        "canonical/runtime/c.py",
    }
