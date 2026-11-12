"""An invalid transport counter/timestamp must not abort or mutate valid learned memory."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore  # noqa: E402


@pytest.fixture
def bundle(tmp_path):
    store = VerifiedSkillStore(tmp_path / "teacher.sqlite", seed=False)
    taught = store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python", error_class="BOUNDARY")
    assert taught["crystallized"] is True
    return store.export_bundle()


BAD_METADATA = [
    ("verified_hits", "not-a-count", "INVALID_VERIFIED_HITS"),
    ("verified_hits", -1, "INVALID_VERIFIED_HITS"),
    ("verified_hits", True, "INVALID_VERIFIED_HITS"),
    ("verified_hits", 1.5, "INVALID_VERIFIED_HITS"),
    ("verified_hits", 1 << 63, "INVALID_VERIFIED_HITS"),
    ("verified_hits", None, "INVALID_VERIFIED_HITS"),
    ("created_ts", "not-a-time", "INVALID_CREATED_TS"),
    ("created_ts", -1, "INVALID_CREATED_TS"),
    ("created_ts", True, "INVALID_CREATED_TS"),
    ("created_ts", float("nan"), "INVALID_CREATED_TS"),
    ("created_ts", float("inf"), "INVALID_CREATED_TS"),
    ("created_ts", 10 ** 400, "INVALID_CREATED_TS"),
]


@pytest.mark.parametrize("field,value,reason", BAD_METADATA)
def test_bad_entry_is_refused_by_name_and_next_valid_entry_survives(tmp_path, bundle, field, value, reason):
    bad = copy.deepcopy(bundle["rules"][0])
    bad[field] = value
    mixed = {**bundle, "rules": [bad, bundle["rules"][0]]}
    target = VerifiedSkillStore(tmp_path / "receiver.sqlite", seed=False)
    result = target.import_bundle(mixed)
    assert result == {"accepted": 1, "merged": 0, "refused": 1,
                      "refusals": [{"skill_id": bad["skill_id"], "reason": reason}]}
    assert target.count() == 1
    # A new store object loads the actually retained lesson, not an import status string.
    reopened = VerifiedSkillStore(tmp_path / "receiver.sqlite", seed=False)
    hit = reopened.recall_and_apply_verified(
        source_text="def g(y):\n    return y <= 20\n", language="python", error_class="BOUNDARY",
        verifier=lambda candidate: "return y < 20" in candidate)
    assert hit is not None
    assert hit["patched_source"] == "def g(y):\n    return y < 20\n"


def test_bad_merge_cannot_invalidate_or_change_existing_rule(tmp_path, bundle):
    target = VerifiedSkillStore(tmp_path / "receiver.sqlite", seed=False)
    assert target.import_bundle(bundle)["accepted"] == 1
    before = target.export_bundle()["rules"]
    bad = copy.deepcopy(bundle)
    bad["rules"][0]["verified_hits"] = "not-a-count"
    bad["rules"][0]["rule"]["state"] = "INVALIDATED"
    result = target.import_bundle(bad)
    assert result["refused"] == 1
    assert target.export_bundle()["rules"] == before


def test_maximum_sqlite_counter_and_epoch_timestamp_survive_roundtrip(tmp_path, bundle):
    bundle["rules"][0].update(verified_hits=(1 << 63) - 1, created_ts=0)
    target = VerifiedSkillStore(tmp_path / "receiver.sqlite", seed=False)
    assert target.import_bundle(json.loads(json.dumps(bundle)))["accepted"] == 1
    entry = target.export_bundle()["rules"][0]
    assert entry["verified_hits"] == (1 << 63) - 1
    assert entry["created_ts"] == 0
    assert target.import_bundle(bundle)["merged"] == 1
    assert target.export_bundle()["rules"] == [entry]


def test_missing_legacy_numeric_metadata_keeps_defaults(tmp_path, bundle):
    bundle["rules"][0].pop("verified_hits")
    bundle["rules"][0].pop("created_ts")
    target = VerifiedSkillStore(tmp_path / "receiver.sqlite", seed=False)
    assert target.import_bundle(bundle)["accepted"] == 1
    entry = target.export_bundle()["rules"][0]
    assert entry["verified_hits"] == 1
    assert entry["created_ts"] > 0
