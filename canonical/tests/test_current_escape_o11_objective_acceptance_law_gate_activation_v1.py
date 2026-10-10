from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
ACT=ROOT/"canonical/governance/CURRENT_ESCAPE_O11_OBJECTIVE_ACCEPTANCE_LAW_GATE_ACTIVATION_20261010_V1.json"
OQ=ROOT/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"


def load(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


class O11ActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=load(ACT)
        cls.oq=load(OQ)

    def test_exact_runtime_test_and_verification_hashes(self):
        for key in ("runtime","tests","verification"):
            row=self.a[key]
            self.assertEqual(blob(ROOT/row["path"]),row["git_blob_sha"])

    def test_current_frontier_binding_is_exact_o11_q2(self):
        row=self.a["current_frontier"]
        self.assertEqual(blob(ROOT/row["path"]),row["git_blob_sha"])
        self.assertEqual(row["o_rows"],11)
        self.assertEqual(row["q_rows"],2)
        self.assertEqual(self.oq["reduction"]["O_OBJECTIVE_ACCEPTANCE"],11)
        self.assertEqual(self.oq["reduction"]["Q_QUALITATIVE_RELATIVE_ORDER"],2)

    def test_reused_kernel_hashes_are_exact(self):
        k=self.a["reused_kernel"]
        self.assertEqual(blob(ROOT/k["path"]),k["git_blob_sha"])
        self.assertEqual(
            blob(ROOT/k["proof_certificate_kernel"]["path"]),
            k["proof_certificate_kernel"]["git_blob_sha"],
        )
        self.assertEqual(
            blob(ROOT/k["scope_cover"]["path"]),
            k["scope_cover"]["git_blob_sha"],
        )

    def test_law_preserves_current_identity_and_mystery_strengthening(self):
        law=self.a["law"]
        self.assertIn("CURRENT_TARGET_IDENTITY_FRESHNESS_MUST_PASS",law["currentness"])
        self.assertEqual(
            set(law["proof_modes"]),
            {"THRESHOLD_LOWER_BOUND","TASK_CONDITIONED_DOMINANCE","SCOPE_SUPERSET"},
        )
        self.assertIn("REMAINS_ITS_OWN_PREDICATE",law["mysterymechanism"])
        self.assertIn("NO_ALIAS",law["mysterymechanism"])


    def test_shared_o_law_authority_is_exact_and_precedes_row_gate(self):
        row=self.a["shared_o_law_authority"]
        self.assertEqual(blob(ROOT/row["activation_path"]),row["activation_git_blob_sha"])
        self.assertEqual(blob(ROOT/row["runtime_path"]),row["runtime_git_blob_sha"])
        self.assertEqual(blob(ROOT/row["frozen_theorem_path"]),row["frozen_theorem_git_blob_sha"])
        self.assertIn("ROW_INSTANTIATIONS_STILL_OPEN",row["role"])
        self.assertTrue(self.a["current_frontier"]["shared_o_law_bound"])
        self.assertEqual(self.a["current_frontier"]["current_o_row_acceptance_closed_count"],0)

    def test_activation_grants_zero_row_or_terminal_credit(self):
        self.assertEqual(self.a["current_frontier_effect"]["real_o_row_proofs"],0)
        self.assertEqual(self.a["current_frontier_effect"]["real_o_rows"],11)
        for key in ("acceptance_credit_delta","capability_credit_delta","ownership_credit_delta","terminal_credit_delta"):
            self.assertEqual(self.a["accounting"][key],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
