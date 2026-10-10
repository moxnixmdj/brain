from canonical.runtime.current_authority_runtime_census_v1 import (
    RUNTIME_PATH_RE,
    _runtime_paths,
)


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


def test_runtime_path_regex_accepts_real_paths_and_rejects_noise():
    assert RUNTIME_PATH_RE.fullmatch(
        "canonical/runtime/universal_escape_resolver_v1.py"
    )
    assert RUNTIME_PATH_RE.fullmatch(
        "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"
    )
    for value in (
        "canonical/governance/x.py",
        "canonical/runtime/not-python.txt",
        "canonical/runtime/has space.py",
        'canonical/runtime/has"quote.py',
        "canonical/runtime/has'quote.py",
    ):
        assert RUNTIME_PATH_RE.fullmatch(value) is None
