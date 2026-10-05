from __future__ import annotations

import pytest

from canonical.runtime.root3_child_process_channel_registry_v1 import (
    ChildProcessRegistryError,
    compile_registry,
)


def test_current_whole_runtime_child_process_universe_is_exactly_29():
    out = compile_registry()
    whole = out["whole_runtime"]
    assert whole["scanned_python_file_count"] == 48
    assert whole["child_process_call_site_count"] == 29
    assert whole["subprocess_run_count"] == 27
    assert whole["subprocess_popen_count"] == 2
    assert whole["os_system_or_unregistered_subprocess_api_count"] == 0
    assert whole["modules_with_child_processes_count"] == 13
    assert out["child_process_universe_closed_for_bound_current_runtime_bytes"] is True
    assert out["child_process_effect_totality_proved"] is False


def test_astra_subset_remains_exactly_eight_with_known_partition():
    out = compile_registry()
    assert out["astra_subset"]["call_site_count"] == 8
    assert out["astra_subset"]["function_counts"] == {
        "run_shell": 1,
        "_ensure_pypi_dependency": 2,
        "_ensure_apt_dependencies": 3,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    }


def test_arbitrary_shell_call_site_is_present_and_explicit():
    out = compile_registry()
    rows = out["whole_runtime"]["call_sites"]
    matches = [
        x for x in rows
        if x["module_path"] == "canonical/runtime/astra_runtime.py"
        and x["function"] == "run_shell"
    ]
    assert len(matches) == 1
    assert matches[0]["process_api"] == "subprocess.run"


def test_new_unregistered_process_api_would_be_a_fail_closed_class():
    # The compiler accepts only subprocess.run and subprocess.Popen. Any other
    # subprocess.* call or os.system is accumulated in the forbidden set and
    # causes ChildProcessRegistryError. Keep the exception type load-bearing.
    assert issubclass(ChildProcessRegistryError, RuntimeError)
