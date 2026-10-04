from __future__ import annotations

import copy
import unittest

from canonical.runtime import structural_mapping_prover_v1 as p
from canonical.runtime import unknown_domain_direct_adapter_v1 as a


def graph(nodes, edges):
    return {
        "nodes": [{"id": nid, "kind": kind, "label": "IGNORED_"+nid} for nid, kind in nodes],
        "edges": [{"source": s, "target": d, "type": t} for s, d, t in edges],
        "metadata": {"distractor": "must_not_matter"},
    }


SOURCE = graph(
    [("s0","INPUT"),("s1","PROCESS"),("s2","PROCESS"),("s3","OUTPUT")],
    [("s0","s1","FLOW"),("s0","s2","CONTROL"),("s1","s2","FLOW"),("s2","s3","FLOW")],
)
TARGET = graph(
    [("q9","PROCESS"),("q2","OUTPUT"),("q7","INPUT"),("q4","PROCESS")],
    [("q7","q4","FLOW"),("q7","q9","CONTROL"),("q4","q9","FLOW"),("q9","q2","FLOW")],
)


class StructuralMappingProverTests(unittest.TestCase):
    def test_unique_mapping_ignores_surface_labels(self):
        out=p.propose(SOURCE,TARGET)
        self.assertEqual(out["status"],"UNIQUE_STRUCTURAL_MAPPING")
        self.assertFalse(out["surface_labels_used"])
        self.assertEqual(out["mapping"],{"s0":"q7","s1":"q4","s2":"q9","s3":"q2"})

    def test_surface_metadata_change_does_not_change_mapping(self):
        target=copy.deepcopy(TARGET)
        for node in target["nodes"]:
            node["label"]="completely different " + node["id"]
        target["metadata"]={"distractor":"changed"}
        self.assertEqual(p.propose(SOURCE,target)["mapping"],p.propose(SOURCE,TARGET)["mapping"])

    def test_nonisomorphic_rejected(self):
        target=copy.deepcopy(TARGET)
        target["edges"][0]={"source":"q7","target":"q2","type":"FLOW"}
        out=p.propose(SOURCE,target)
        self.assertEqual(out["status"],"NO_STRUCTURAL_MAPPING")
        self.assertIsNone(out["mapping"])

    def test_symmetric_graph_abstains(self):
        source=graph(
            [("a","CENTER"),("b","LEAF"),("c","LEAF")],
            [("a","b","FLOW"),("a","c","FLOW")],
        )
        target=graph(
            [("x","CENTER"),("y","LEAF"),("z","LEAF")],
            [("x","y","FLOW"),("x","z","FLOW")],
        )
        out=p.propose(source,target)
        self.assertEqual(out["status"],"AMBIGUOUS_STRUCTURAL_MAPPING")
        route=a.propose_cross_domain_mapping(source_graph=source,target_graph=target)
        self.assertEqual(route["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")

    def test_verified_mapping_receipt_enables_reuse_without_rediscovery(self):
        proposal=p.propose(SOURCE,TARGET)
        receipt={
            "receipt_id":"hidden-evaluator-case-1",
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "mapping_digest":proposal["mapping_digest"],
            "source_primitive":"SRC_P",
            "target_primitive":"TGT_P",
        }
        out=a.apply_verified_cross_domain_transfer(
            goal="reuse source primitive in target domain",
            verified_coverage=True,
            source_primitive="SRC_P",
            target_primitive="TGT_P",
            source_graph=SOURCE,
            target_graph=TARGET,
            evaluator_receipt=receipt,
        )
        self.assertTrue(out["target_primitive_reused"],out)
        self.assertFalse(out["full_target_rediscovery_invoked"])
        self.assertEqual(out["route"],"USE_VERIFIED_CAPABILITY")

    def test_wrong_hidden_mapping_receipt_fails_closed(self):
        proposal=p.propose(SOURCE,TARGET)
        receipt={
            "receipt_id":"hidden-evaluator-case-bad",
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "mapping_digest":"sha256:"+"0"*64,
            "source_primitive":"SRC_P",
            "target_primitive":"TGT_P",
        }
        with self.assertRaisesRegex(a.UnknownDomainDirectAdapterError,"EVALUATOR_MAPPING_DIGEST_MISMATCH"):
            a.apply_verified_cross_domain_transfer(
                goal="reuse",
                verified_coverage=True,
                source_primitive="SRC_P",
                target_primitive="TGT_P",
                source_graph=SOURCE,
                target_graph=TARGET,
                evaluator_receipt=receipt,
            )

    def test_identifiable_common_action_does_not_blanket_abstain(self):
        out=a.calibrated_decision(
            goal="choose supported action",
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
                {"id":"h2","plausible":True,"best_action":"A","probability":"1/2"},
            ],
            actions=[],
        )
        self.assertEqual(out["route"],"DECISION_SUFFICIENT_UNVERIFIED_MODEL")
        self.assertEqual(out["recommended_action"],"A")

    def test_underspecified_selects_positive_gain_safe_discriminator(self):
        out=a.calibrated_decision(
            goal="request minimum useful discriminator",
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
                {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
            ],
            actions=[
                {"id":"useless","safe":True,"outcome_by_hypothesis":{"h1":"same","h2":"same"},"time":1},
                {"id":"probe","safe":True,"outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":1},
            ],
        )
        self.assertEqual(out["route"],"LEARN")
        self.assertEqual(out["next_action"]["id"],"probe")

    def test_nonidentifiable_without_safe_gain_abstains(self):
        out=a.calibrated_decision(
            goal="do not force unsupported conclusion",
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
                {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
            ],
            actions=[
                {"id":"unsafe","safe":False,"outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":1},
                {"id":"useless","safe":True,"outcome_by_hypothesis":{"h1":"same","h2":"same"},"time":1},
            ],
        )
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")
        self.assertIsNone(out["recommended_action"])


if __name__=="__main__":
    unittest.main(verbosity=2)
