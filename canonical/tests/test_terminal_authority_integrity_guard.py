from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_authority_integrity_guard import REQUIRED, evaluate, git_blob_sha


class TerminalAuthorityIntegrityGuardTests(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj) -> str:
        p=root/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        raw=(json.dumps(obj,indent=2)+"\n").encode()
        p.write_bytes(raw)
        return git_blob_sha(raw)

    def _fixture(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root=Path(td.name)
        shas={}
        for i,rel in enumerate(REQUIRED):
            shas[rel]=self._write(root,rel,{"v":i})
        receipt={
            "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TEST",
            "live_verdict":{"pass":True,"execution_authority":True},
            "exact_brain_blobs":shas,
        }
        self._write(root,"canonical/verification/TERMINAL_PREQUALIFICATION_AUTHORIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",receipt)
        authority={
            "execution_authority":True,
            "terminal_results_observed":0,
            "fresh_terminal_evidence_consumed":0,
            "conditions":[
                "CURRENT_ACTIVE_CONTRACT_REGISTRY_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
                "CURRENT_ACTIVE_TERMINAL_PROOF_BASIS_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
                "CURRENT_TERMINAL_POPULATION_PROTOCOL_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
                "CURRENT_PREQUALIFICATION_MANIFEST_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
            ],
        }
        self._write(root,"canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json",authority)
        return root

    def test_exact_authorized_world_passes(self):
        out=evaluate(self._fixture())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["launch_integrity"])

    def test_single_byte_drift_fails_closed(self):
        root=self._fixture()
        p=root/REQUIRED[-1]
        p.write_bytes(p.read_bytes()+b" ")
        out=evaluate(root)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("BOUND_BLOB_DRIFT:") for x in out["errors"]))

    def test_missing_exact_binding_condition_fails_closed(self):
        root=self._fixture()
        p=root/"canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json"
        a=json.loads(p.read_text())
        a["conditions"]=a["conditions"][:-1]
        p.write_text(json.dumps(a,indent=2)+"\n")
        out=evaluate(root)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_EXACT_BINDING_CONDITIONS_MISSING",out["errors"])

if __name__=="__main__":
    unittest.main()
