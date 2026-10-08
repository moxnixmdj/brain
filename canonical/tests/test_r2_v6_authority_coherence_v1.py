from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class R2V6AuthorityCoherenceTests(unittest.TestCase):
    def test_current_r2_v6_authority_chain_is_content_coherent(self):
        pointer = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        scheduler_ref = pointer["scheduler_cut"]
        self.assertEqual(
            scheduler_ref["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V6.json",
        )
        scheduler_path = ROOT / scheduler_ref["path"]
        self.assertEqual(scheduler_ref["git_blob_sha"], git_blob_sha(scheduler_path))

        controller_ref = pointer["controller"]
        controller_path = ROOT / controller_ref["authority_kernel"]
        self.assertEqual(
            controller_ref["authority_kernel_git_blob_sha"],
            git_blob_sha(controller_path),
        )

        scheduler = load(scheduler_ref["path"])
        self.assertFalse(scheduler["single_live_primitive"]["general_mechanism_missing"])
        self.assertEqual(
            scheduler["live_mechanism"]["authority_kernel"]["git_blob_sha"],
            git_blob_sha(controller_path),
        )

        closure_ref = scheduler["live_mechanism"]["mechanism_closure"]
        closure_path = ROOT / closure_ref["path"]
        self.assertEqual(closure_ref["git_blob_sha"], git_blob_sha(closure_path))
        closure = load(closure_ref["path"])
        self.assertTrue(
            closure["closure_interpretation"]["universal_control_semantics_closed"]
        )
        self.assertFalse(
            closure["closure_interpretation"]["universal_positive_action_coverage_closed"]
        )
        self.assertFalse(
            closure["closure_interpretation"]["global_open_world_closure_claimed"]
        )

        frontier_ref = scheduler["live_mechanism"]["grounded_candidate_policy_frontier"]
        frontier_path = ROOT / frontier_ref["path"]
        self.assertEqual(frontier_ref["git_blob_sha"], git_blob_sha(frontier_path))

    def test_terminal_authority_binds_v6_without_claiming_omniscience(self):
        terminal = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
        ref = terminal["authoritative_sources"]["current_r2_decision_intelligence"][
            "scheduler_cut"
        ]
        self.assertEqual(
            ref["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V6.json",
        )
        self.assertEqual(ref["git_blob_sha"], git_blob_sha(ROOT / ref["path"]))
        live = terminal["live_truth"]
        self.assertEqual(
            live["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V6",
        )
        self.assertTrue(
            live["r2_general_control_mechanism_closed_as_adequacy_or_abstain"]
        )
        self.assertFalse(live["r2_open_world_positive_action_coverage_complete"])
        self.assertTrue(
            live["r2_decisive_unobservable_reality_requires_abstention_or_information_acquisition"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
