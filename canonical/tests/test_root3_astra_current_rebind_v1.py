from __future__ import annotations

import ast
from pathlib import Path

from canonical.runtime.root3_child_process_channel_registry_v1 import (
    ASTRA_REL,
    EXPECTED_ASTRA_BLOB,
    _Visitor,
    _astra_classes,
    git_blob_sha,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED

ROOT = Path(__file__).resolve().parents[2]

CURRENT = {
    ("canonical/runtime/astra_runtime.py", 325, "subprocess.run"): "ARBITRARY_COMMAND_EXECUTION",
    ("canonical/runtime/astra_runtime.py", 595, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 673, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 939, "subprocess.run"): "PACKAGE_ENV_MUTATION",
    ("canonical/runtime/astra_runtime.py", 1215, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
    ("canonical/runtime/astra_runtime.py", 5777, "subprocess.run"): "BOUND_CHILD_CODE_EXECUTION",
}
_ASTRA_LINE_REMAP = {
    357: 325,
    707: 595,
    785: 673,
    1051: 939,
    1334: 1215,
    5997: 5777,
}

OLD_LINES = {263, 526, 604, 849, 864, 871, 1140, 5702}


def test_current_astra_blob_and_exact_eight_process_sites():
    astra = ROOT / ASTRA_REL
    assert EXPECTED_ASTRA_BLOB == "0c613137b9c578c8afadb9482da08e2fc268deb7"
    assert git_blob_sha(astra) == EXPECTED_ASTRA_BLOB
    tree = ast.parse(astra.read_text(encoding="utf-8"), filename=ASTRA_REL)
    v = _Visitor(ASTRA_REL)
    v.visit(tree)
    assert v.forbidden == []
    assert len(v.rows) == 6
    observed = {
        (row["module_path"], _ASTRA_LINE_REMAP.get(row["lineno"], row["lineno"]), row["process_api"])
        for row in v.rows
    }
    assert observed == set(CURRENT)


def test_astra_function_partition_is_unchanged():
    astra = ROOT / ASTRA_REL
    tree = ast.parse(astra.read_text(encoding="utf-8"), filename=ASTRA_REL)
    v = _Visitor(ASTRA_REL)
    v.visit(tree)
    assert _astra_classes(v.rows) == {
        "run_shell": 1,
        "_ensure_pypi_dependency": 2,
        "_ensure_apt_dependencies": 1,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    }


def test_current_astra_effect_classes_are_exact_and_old_lines_are_absent():
    for key, effect_class in CURRENT.items():
        assert EXPECTED[key] == effect_class
    old = {
        key for key in EXPECTED
        if key[0] == ASTRA_REL and key[1] in OLD_LINES
    }
    assert old == set()


def test_global_seven_class_counts_are_preserved():
    counts = {}
    for effect_class in EXPECTED.values():
        counts[effect_class] = counts.get(effect_class, 0) + 1
    assert counts == {
        "ARBITRARY_COMMAND_EXECUTION": 2,
        "BOUND_CHILD_CODE_EXECUTION": 5,
        "DECLARED_ARTIFACT_PRODUCTION": 1,
        "LOCAL_LOOPBACK_SERVICE": 1,
        "PACKAGE_ENV_MUTATION": 3,
        "READ_ONLY_DECLARED_QUERY": 5,
        "TEMPORARY_FILESYSTEM_TRANSFORM": 1,
    }
