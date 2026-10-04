"""Pre-production falsification tests for Unknown-Domain V3."""
import copy
import hashlib

import unittest

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as gen_v2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as gen_v3


def _run_packet(packet):
    rows=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
        out=harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        rows.append(out)
    return rows


def test_v3_closes_exact_v2_add2_counterexample():
    secret=hashlib.sha256(b"secret0").digest()
    beacon="beacon-qualification-0000000000000000"
    visible,hidden=gen_v2._transfer_case(secret,beacon,4,namespace="REVOCATION")
    out=harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"] == hidden["gold_terminal_consequence"]
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(hidden["transfer_relevant_feature_ids"])
    assert out["probe_count"] <= 2


def test_v3_qualification_sweep_exact_pass():
    # Content is hidden from the candidate; these are non-production qualification
    # fixtures generated from deterministic test-only secrets.
    for i in range(32):
        packet=gen_v3.generate_qualification_fixture_population(
            beacon=f"V3-QUALIFICATION-{i:08d}-POSTFREEZE"
        )
        assert packet["identifier_totality_verified"] is True
        rows=_run_packet(packet)
        assert len(rows)==27
        assert all(x["scorer_result"]["pass"] is True for x in rows)
        assert all(x["probe_count"] <= 2 for x in rows)


def test_v3_identifier_totality_rejects_target_collision():
    packet=gen_v2.generate_qualification_fixture_population(
        beacon="V3-COLLISION-TARGET-QUALIFICATION"
    )
    bad=copy.deepcopy(packet)
    h=next(x for x in bad["hidden_records"] if x["leaf_id"]==gen_v2.v1.TRANSFER)
    assert len(h["transfer_relevant_feature_ids"])==2
    h["transfer_relevant_feature_ids"][1]=h["transfer_relevant_feature_ids"][0]
    with unittest.TestCase().assertRaises(gen_v3.GeneratorError):
        gen_v3._assert_identifier_totality(bad)


def test_v3_identifier_totality_rejects_source_binding_collision():
    packet=gen_v2.generate_qualification_fixture_population(
        beacon="V3-COLLISION-SOURCE-QUALIFICATION"
    )
    bad=copy.deepcopy(packet)
    v=next(x for x in bad["visible_cases"] if x["leaf_id"]==gen_v2.v1.TRANSFER and len(x["domain_a"]["earned_receipts"][0]["source_role_binding"])==2)
    binding=v["domain_a"]["earned_receipts"][0]["source_role_binding"]
    binding["r1"]=binding["r0"]
    with unittest.TestCase().assertRaises(gen_v3.GeneratorError):
        gen_v3._assert_identifier_totality(bad)


def test_v3_identifier_totality_rejects_cross_domain_collision():
    packet=gen_v2.generate_qualification_fixture_population(
        beacon="V3-COLLISION-CROSSDOMAIN-QUALIFICATION"
    )
    bad=copy.deepcopy(packet)
    idx=next(i for i,x in enumerate(bad["visible_cases"]) if x["leaf_id"]==gen_v2.v1.TRANSFER)
    v=bad["visible_cases"][idx]
    h=bad["hidden_records"][idx]
    source_id=next(iter(v["domain_a"]["earned_receipts"][0]["source_role_binding"].values()))
    h["transfer_relevant_feature_ids"][0]=source_id
    with unittest.TestCase().assertRaises(gen_v3.GeneratorError):
        gen_v3._assert_identifier_totality(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
