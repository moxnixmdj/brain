"""What instant learning can and cannot do, pinned by measurement.

Three findings are pinned here because each one contradicts the natural expectation and
each one is cheap to re-verify:

1. A warm skill store does not solve more bugs than a cold one. It finds the same repair
   with fewer candidates. Learning reduces the cost of the second time, not the cost of
   the first.

2. A learned skill does not transfer. Its matcher requires a literal token sequence in
   exact order. Measured transfer was 0 of 774 functions in the skill's own origin
   repository and 0 of 40 in unrelated repositories.

3. The store holds repair traces, not skills. A trace is a memorised token run; a skill
   would carry variables, a precondition and a postcondition.

If a future change makes the store genuinely generalise, test 2 will fail and that will be
the good news. The test is written so it fails loudly rather than silently passing.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as V  # noqa: E402


def _store_rows():
    db = V._default_db_path()
    if not Path(db).exists():
        pytest.skip("no skill store on this machine")
    c = sqlite3.connect(str(db))
    cols = [d[1] for d in c.execute("PRAGMA table_info(crystallized_skills)")]
    rows = [dict(zip(cols, r)) for r in c.execute("select * from crystallized_skills")]
    c.close()
    return rows


def test_a_learned_rule_is_a_literal_token_run_with_typed_holes():
    """The unit of learning is a token sequence, not a schema with a variable type."""
    rows = [r for r in _store_rows() if r.get("language") == "python"]
    if not rows:
        pytest.skip("no python skills yet")
    rule = json.loads(rows[0]["pattern_json"])
    toks = [k for k, _ in rule["pattern_tokens"]]
    literals = [v for k, v in rule["pattern_tokens"] if k not in {"hole_id", "hole_num", "ws"}]
    holes = [v for k, v in rule["pattern_tokens"] if k in {"hole_id", "hole_num"}]
    assert holes, "a rule with no holes could never generalise at all"
    assert literals, "a rule is anchored on literal tokens 'kw'/'op'"


def test_every_stored_rule_carries_a_skeleton_fingerprint():
    """The fingerprint is proof the unit is keyed to an exact code shape."""
    rows = _store_rows()
    if not rows:
        pytest.skip("no skills")
    for r in rows:
        rule = json.loads(r["pattern_json"])
        assert rule.get("skeleton_fp"), f"{r['skill_id']} has no skeleton fingerprint"


def test_the_store_contains_no_computer_or_action_skill():
    """Nothing has ever been learned from a computer action.

    If this test starts failing because such skills exist, the computer-use learning loop
    has been built. Until then the claim that one demonstration teaches a new environment
    is unsupported for GUI work.
    """
    rows = _store_rows()
    actiony = [r for r in rows
               if any(w in str(r.get("domain", "")).lower()
                      for w in ("action", "computer", "gui"))]
    assert actiony == [], (
        "computer/action skills now exist -- update the governance record "
        "IS_INSTANT_LEARNING_ENOUGH_20261109_V1 because its claim has changed")


def test_the_matcher_requires_an_exact_token_sequence():
    """A rewrite rule must not fire on code that merely looks similar."""
    rows = [r for r in _store_rows() if r.get("language") == "python"]
    if not rows:
        pytest.skip("no python skills")
    rule = json.loads(rows[0]["pattern_json"])
    unrelated = (
        "def handler(request, response):\n"
        "    payload = request.get_json()\n"
        "    if payload is None:\n"
        "        return response\n"
        "    return response\n"
    )
    fired = [c for c in V.iter_crystallized_code_rule_candidates(unrelated, rule)
             if c and c != unrelated]
    assert fired == [], "a memorised rule fired on unrelated code; that would be transfer"


def test_measured_transfer_rate_is_recorded_and_is_zero_in_the_governance_record():
    rec = ROOT / "canonical/governance/IS_INSTANT_LEARNING_ENOUGH_20261109_V1.json"
    assert rec.is_file()
    d = json.loads(rec.read_text())
    e2 = d["experiment_2__does_a_learned_skill_transfer_to_new_code"]
    assert e2["sample_b_the_skills_own_origin_repo"]["transfer_rate_pct"] == 0.0
    assert e2["sample_a_unrelated_repos"]["transfer_rate_pct"] == 0.0
    e1 = d["experiment_1__cold_vs_warm_on_the_real_corpus"]
    assert "solved ZERO additional bugs" in e1["conclusion"]
