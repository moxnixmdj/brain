from __future__ import annotations

import copy
import unittest

from canonical.runtime import unknown_domain_direct_generator_v1 as g
from canonical.runtime import unknown_domain_direct_scorer_v1 as s


class UnknownDomainDirectFamilyFreezeTests(unittest.TestCase):
    def test_generation_is_deterministic_for_same_post_freeze_beacon(self):
        a=g.generate("0123456789abcdef-FROZEN-A")
        b=g.generate("0123456789abcdef-FROZEN-A")
        self.assertEqual(a,b)

    def test_different_beacons_change_case_ids(self):
        a=g.generate("0123456789abcdef-FROZEN-A")
        b=g.generate("fedcba9876543210-FROZEN-B")
        self.assertNotEqual(
            [x["case_id"] for x in a["cases"]],
            [x["case_id"] for x in b["cases"]],
        )

    def test_mode_counts_and_zero_learned_boundary(self):
        out=g.generate("0123456789abcdef-FROZEN-A")
        counts={}
        for c in out["cases"]:
            counts[c["hidden_evaluator"]["mode"]]=counts.get(c["hidden_evaluator"]["mode"],0)+1
        self.assertEqual(counts,{
            "IDENTIFIABLE_TRANSFER":24,
            "NONIDENTIFIABLE_ABSTAIN":12,
            "UNDERSPECIFIED_REQUEST_DISCRIMINATOR":12,
        })
        self.assertEqual(out["accounting"]["persistent_learned_bytes"],0)

    def test_candidate_visible_projection_contains_no_hidden_evaluator(self):
        out=g.generate("0123456789abcdef-FROZEN-A")
        for row in out["candidate_visible_projection"]:
            self.assertNotIn("hidden_evaluator",row)
            self.assertIn("visible",row)

    def test_identifiable_cases_exclude_distractor_at_generator_level(self):
        out=g.generate("0123456789abcdef-FROZEN-A")
        for c in out["cases"]:
            if c["hidden_evaluator"]["mode"]!="IDENTIFIABLE_TRANSFER":
                continue
            v=c["visible"]
            # Reconstruct generator-level survivor condition from public observations.
            surface=v["target_surface"]
            token_to_bit=[
                {tok:i for i,tok in enumerate(feature["tokens"])}
                for feature in surface["features"]
            ]
            out_to_bit={tok:i for i,tok in enumerate(surface["output_tokens"])}
            obs=[]
            for row in v["target_observations"]:
                bits=tuple(token_to_bit[i][row["input"][surface["features"][i]["name"]]] for i in range(2))
                obs.append((bits,out_to_bit[row["output"]]))
            surv=g._survivors(v["source_primitives"],obs)
            self.assertEqual({x[0] for x in surv},{c["hidden_evaluator"]["relevant_source_id"]})

    def test_scorer_fails_blanket_abstention_on_identifiable_case(self):
        case=next(c for c in g.generate("0123456789abcdef-FROZEN-A")["cases"] if c["hidden_evaluator"]["mode"]=="IDENTIFIABLE_TRANSFER")
        result={
            "verdict":"ABSTAIN","answer":None,
            "persistent_learned_bytes":0,
            "external_frontier_model_calls":0,
            "external_learned_capability_calls":0,
        }
        row=s.score_case(case,result)
        self.assertFalse(row["pass"])
        self.assertIn("IDENTIFIABLE_CASE_NOT_ANSWERED",row["reasons"])


if __name__=="__main__":
    unittest.main(verbosity=2)
