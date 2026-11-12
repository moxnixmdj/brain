"""One demonstration does not identify a rule; chosen questions do.

Pins the measurement in `one_shot_identifiability_probe_20261112.py` so the number cannot drift
away from the code, and so the counterfactual that carries the argument -- *the same example
against a narrower space decides differently* -- is asserted rather than described.

The interesting assertions here are the ones that would fail if someone quietly widened the
hypothesis space, narrowed it to the targets, or let the "ask" protocol peek at the held-out
inputs. Each is a real property of the protocol, not a restatement of its output.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "one_shot_identifiability_probe_20261112.py"

sys.path.insert(0, str(ROOT))

from one_shot_identifiability_probe_20261112 import (  # noqa: E402
    HELD_OUT,
    PROBE_POOL,
    TRUTHS,
    build_space,
    protocol_fixed,
)


def _run(tmp_path: Path) -> dict:
    out = tmp_path / "probe.json"
    completed = subprocess.run(
        [sys.executable, str(PROBE), "--json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_every_target_is_a_member_of_the_space():
    """Held-out accuracy is meaningless unless the truth is expressible. Fails closed."""
    keys = {h.key for h in build_space()}
    assert sorted(set(TRUTHS) - keys) == []
    assert len(build_space()) == 47


def test_no_target_is_identified_by_one_demonstration(tmp_path):
    result = _run(tmp_path)
    s = result["summary"]
    assert s["targets_exact_after_one"] == 0
    assert s["mean_survivors_after_one"] > 5.0
    assert s["mean_leader_accuracy_after_one"] < 0.5


def test_the_leader_from_one_example_is_usually_wrong_where_the_caller_lives(tmp_path):
    """The single number the claim rests on: one try buys a rule that is mostly wrong."""
    result = _run(tmp_path)
    s = result["summary"]
    assert s["mean_leader_accuracy_after_one"] == 0.1
    # And three demonstrations do not rescue every target either: mod 5 and mod 7 are still
    # indistinguishable from the evidence 1,2,3 alone. That is insufficiency, not noise.
    insufficient = [r for r in result["rows"] if r["THREE"]["survivors"] > 1]
    assert {r["target"] for r in insufficient} == {"mod:5", "mod:7", "const:0", "floordiv:2",
                                                   "threshold:0"}


def test_survivors_shrink_and_never_grow():
    for key, truth in sorted(TRUTHS.items()):
        one = protocol_fixed(truth, [1])
        three = protocol_fixed(truth, [1, 2, 3])
        assert three["survivors"] <= one["survivors"], key


def test_chosen_questions_close_the_gap_that_one_example_leaves(tmp_path):
    result = _run(tmp_path)
    s = result["summary"]
    assert s["targets_settled_after_one_then_ask"] == s["targets"]
    assert s["mean_accuracy_after_one_then_ask"] == 1.0
    assert 0 < s["mean_queries_to_settle_after_one"] <= 4


def test_the_prior_is_what_generalises_not_the_example(tmp_path):
    """Same one observation, two spaces, two different answers. Only the space changed."""
    rows = _run(tmp_path)["rows"]
    wrong_from_one = [r for r in rows if r["ONE"]["leader_held_out_accuracy"] < 1.0]
    # Nine of ten targets pick a rule that is wrong somewhere on the caller's domain.
    assert len(wrong_from_one) == 9
    # The identical observation, against a two-hypothesis space, is right on every one of them.
    assert all(r["NARROW_PRIOR_ONE"]["leader_held_out_accuracy"] == 1.0 for r in rows)
    assert all(r["NARROW_PRIOR_ONE"]["survivors"] == 1 for r in rows)


def test_the_scorer_is_held_out_of_the_evidence_and_the_probe_pool():
    assert not set(HELD_OUT) & {1, 2, 3}
    assert set(HELD_OUT) <= {p[0] for p in PROBE_POOL}


def test_the_run_is_deterministic(tmp_path):
    first = _run(tmp_path / "a")
    second = _run(tmp_path / "b")
    assert first["summary"] == second["summary"]
