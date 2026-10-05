from __future__ import annotations

from canonical.runtime.root3_child_process_channel_registry_v1 import (
    _classify,
    compile_registry,
)


def test_current_astra_child_process_universe_is_exactly_eight():
    out = compile_registry()
    assert out["call_site_count"] == 8
    assert out["function_counts"] == {
        "run_shell": 1,
        "_ensure_pypi_dependency": 2,
        "_ensure_apt_dependencies": 3,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    }
    assert out["child_process_universe_closed_for_current_astra_bytes"] is True
    assert out["child_process_effect_totality_proved"] is False


def test_arbitrary_shell_is_never_mislabeled_read_only():
    row = _classify({
        "function": "run_shell",
        "lineno": 1,
        "command_literals": [],
        "has_dynamic_command": True,
    })
    assert row["channel_class"] == "ARBITRARY_SHELL_STEP"
    assert row["effect_class"] == "OPAQUE_MATERIAL_EFFECT_CAPABLE"


def test_package_install_children_are_material_mutations():
    row = _classify({
        "function": "_ensure_pypi_dependency",
        "lineno": 2,
        "command_literals": ["pip", "install"],
        "has_dynamic_command": True,
    })
    assert row["effect_class"] == "PACKAGE_ENV_MUTATION"


def test_unknown_subprocess_function_fails_closed():
    import pytest
    from canonical.runtime.root3_child_process_channel_registry_v1 import (
        ChildProcessRegistryError,
    )

    with pytest.raises(ChildProcessRegistryError, match="UNCLASSIFIED_SUBPROCESS_CALL"):
        _classify({
            "function": "surprise_child",
            "lineno": 3,
            "command_literals": ["anything"],
            "has_dynamic_command": True,
        })
