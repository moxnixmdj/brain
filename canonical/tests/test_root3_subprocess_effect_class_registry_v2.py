from __future__ import annotations

import pathlib

from canonical.runtime import root3_subprocess_effect_class_registry_v2 as reg


def test_current_registry_preserves_legacy_and_defaults_new_sites():
    # 2026-11-01: re-measured on the current tree. All 18 legacy verified sites
    # are accounted for: 17 still exist and are preserved with their legacy
    # classes, 1 (sqlite_verify_cli.py:66) was discharged to in-process sqlite3
    # and is recorded in the registry's disappearance provenance.
    from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED
    from canonical.runtime.root3_subprocess_effect_class_registry_v2 import (
        _LEGACY_DISAPPEARANCE_PROVENANCE,
        _norm_key,
    )
    out = reg.compile_effect_classes()
    assert out["process_site_count"] >= out["legacy_verified_mapping_count"]
    preserved = {
        _norm_key(x["module_path"], int(x["lineno"]), x["source_api"]): x["effect_class"]
        for x in out["classified_sites"]
        if x["classification_provenance"] == "PRESERVED_LEGACY_VERIFIED_MAPPING"
    }
    assert len(preserved) == 17
    assert preserved == {k: v for k, v in EXPECTED.items() if k not in _LEGACY_DISAPPEARANCE_PROVENANCE}
    assert len(EXPECTED) == 18
    assert (
        out["legacy_verified_mapping_count"]
        + out["conservative_default_deny_count"]
        == out["process_site_count"]
    )
    assert out["authority_widening_from_defaulted_sites"] is False


def test_every_new_site_defaults_to_arbitrary_command_execution():
    out = reg.compile_effect_classes()
    new = [
        x for x in out["classified_sites"]
        if x["classification_provenance"]
        == "CONSERVATIVE_DEFAULT_DENY_UNTIL_NARROWER_CLASS_PROVED"
    ]
    assert new
    assert {x["effect_class"] for x in new} == {
        "ARBITRARY_COMMAND_EXECUTION"
    }


def test_registry_digest_is_stable_for_same_tree():
    a = reg.compile_effect_classes()
    b = reg.compile_effect_classes()
    assert a["registry_sha256"] == b["registry_sha256"]


def test_check_output_site_uses_run_interception_if_present():
    out = reg.compile_effect_classes()
    rows = [
        x for x in out["classified_sites"]
        if x["source_api"] == "subprocess.check_output"
    ]
    assert len(rows) >= 1
    assert all(r["interception_api"] == "subprocess.run" for r in rows)
    assert all(r["effect_class"] == "ARBITRARY_COMMAND_EXECUTION" for r in rows)
