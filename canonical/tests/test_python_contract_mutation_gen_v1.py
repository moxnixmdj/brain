"""Tests for the Python contract-mutation generator.

The defect this exists to prevent: a generator that cycles moduli repeats a
handful of programs behind many instance ids.  The first version produced
**31 distinct programs behind 500 instance ids** -- so a capability "scored"
on 500 instances would in truth have been scored on 31, seventeen times each.

Under TRUE_CAPABILITY_TEST_LAW_V1 that is not 500 unseen instances, and the
proof would have been worth nothing.  These tests make that failure
impossible to repeat silently.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "capabilities" / "true" / "generators"))
sys.path.insert(0, str(ROOT / "canonical" / "runtime" / "bound_capabilities"))

import python_contract_mutation_gen_v1 as G  # noqa: E402


def test_generates_the_requested_count():
    assert len(G.generate(500)) == 500


def test_every_instance_is_a_distinct_program():
    """The anti-cycling invariant: 500 instances must mean 500 programs."""
    instances = G.generate(500)
    assert len({i["source"] for i in instances}) == 500


def test_generation_is_deterministic_and_replayable():
    a = G.generate(50)
    b = G.generate(50)
    assert [i["instance_id"] for i in a] == [i["instance_id"] for i in b]


def test_a_different_seed_gives_a_different_sequence():
    assert [i["instance_id"] for i in G.generate(10, seed=0)] != [
        i["instance_id"] for i in G.generate(10, seed=7)
    ]


def test_the_combination_space_covers_the_full_request():
    assert len(G._COMBINATIONS) >= 500


def test_every_instance_carries_its_own_specification():
    for inst in G.generate(500):
        assert inst["contract"].startswith("post:")
        assert inst["contract"] in inst["source"]
        assert "return " in inst["source"]


def test_the_oracle_detects_every_violation_in_a_sample():
    """The generator is only meaningful if a correct oracle flags every instance."""
    import crosshair_contract_oracle as ORACLE

    work = ROOT / "canonical" / "astra_runtime" / "tmp" / "gen_test"
    work.mkdir(parents=True, exist_ok=True)
    detected = 0
    for inst in G.generate(10):
        path = work / f"{inst['instance_id']}.py"
        path.write_text(inst["source"], encoding="utf-8")
        result = ORACLE.run(
            {
                "target_path": str(path.relative_to(ROOT)),
                "output_path": str((work / "o.json").relative_to(ROOT)),
                "allow_unsafe_host_execution": True,
            },
            str(ROOT),
        )
        if result["status"] == "CONTRACT_VIOLATION_FOUND":
            detected += 1
    assert detected == 10
