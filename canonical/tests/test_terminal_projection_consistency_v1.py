from __future__ import annotations
import copy,unittest
from canonical.runtime.terminal_projection_consistency_v1 import load,git_blob_sha,evaluate_documents,evaluate_live

class Tests(unittest.TestCase):
    def fixture(self):
        authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        calpath=authority["sources"]["acceptance_calibration"]["path"]
        residual_path=authority["atomic_acceptance_frontier"]["source"]
        paths={
            "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
            "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
            "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
            "calibration":calpath,
            "residual":residual_path,
            "plan":"canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_MINIMUM_PROOF_PLAN_V1.json",
            "kernel":"canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_PROOF_KERNEL_V2.json",
        }
        docs={k:load(v) for k,v in paths.items()}
        all_paths=set(paths.values())
        for row in authority["sources"].values():
            if isinstance(row,dict) and isinstance(row.get("path"),str):
                all_paths.add(row["path"])
        shas={}
        for x in all_paths:
            try: shas[x]=git_blob_sha(x)
            except FileNotFoundError: pass
        return docs,shas

    def run_docs(self,docs,shas):
        return evaluate_documents(
            docs["authority"],docs["closure"],docs["matrix"],docs["calibration"],
            docs["residual"],docs["plan"],docs["kernel"],shas,
        )

    def test_live_projection_is_consistent(self):
        out=evaluate_live()
        self.assertTrue(out["pass"],out)

    def test_stale_closure_count_fails_closed(self):
        docs,shas=self.fixture(); docs=copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_family_count"]-=1
        out=self.run_docs(docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH",out["errors"])

    def test_stale_authority_blob_pointer_fails_closed(self):
        docs,shas=self.fixture(); docs=copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"]="0"*40
        out=self.run_docs(docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest",out["errors"])

    def test_authority_count_lag_fails_closed(self):
        docs,shas=self.fixture(); docs=copy.deepcopy(docs)
        docs["authority"]["truth"]["opus55_acceptance"]="0/19_PASS__19/19_OPEN"
        out=self.run_docs(docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_COUNT_MISMATCH",out["errors"])

    def test_action_set_drift_fails_closed(self):
        docs,shas=self.fixture(); docs=copy.deepcopy(docs)
        docs["authority"]["atomic_acceptance_frontier"]["authorized_acceptance_case_actions"]=["BAD"]
        out=self.run_docs(docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACTION_SET_MISMATCH",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
