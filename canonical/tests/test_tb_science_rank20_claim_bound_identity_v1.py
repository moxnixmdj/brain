from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime.tb_science_rank20_claim_bound_identity_v1 import (
    ATTEMPT_ID,
    AUTHORITY,
    BINDING,
    CLAIM_DIGEST,
    LEDGER,
    ROOT,
    SEED,
    verify,
    verify_documents,
)

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class Rank20ClaimBoundIdentityTests(unittest.TestCase):
    def test_current_branch_passes_zero_exposure(self):
        out=verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["logical_attempt_id"],ATTEMPT_ID)
        self.assertEqual(out["execution_claim_binding_digest"],CLAIM_DIGEST)
        self.assertFalse(out["legacy_v1_fallback_allowed"])
        self.assertFalse(out["task_read"])
        self.assertFalse(out["execution_authority_effective"])
        self.assertEqual(out["benchmark_trials_consumed"],0)

    def test_preclaim_seed_cannot_mint_identity_or_authority(self):
        seed=load(SEED); binding=load(BINDING); authority=load(AUTHORITY); ledger=load(LEDGER)
        seed["identity_state"]["logical_attempt_id"]="0"*64
        seed["execution_authority"]=True
        errors=verify_documents(seed,binding,authority,ledger)
        self.assertIn("PRECLAIM_IDENTITY_WAS_PREMATURELY_MINTED",errors)
        self.assertIn("SEED_AUTHORITY_OR_EXPOSURE_PRESENT:execution_authority",errors)

    def test_claim_binding_mutation_breaks_content_addressed_identity(self):
        seed=load(SEED); binding=load(BINDING); authority=load(AUTHORITY); ledger=load(LEDGER)
        binding["activation_filename"]="ACTIVATE_WRONG.json"
        errors=verify_documents(seed,binding,authority,ledger)
        self.assertIn("CLAIM_CANONICAL_SHA256_DRIFT",errors)

    def test_pre_reseal_task_read_authority_fails_closed(self):
        seed=load(SEED); binding=load(BINDING); authority=load(AUTHORITY); ledger=load(LEDGER)
        authority["task_read_authority"]=True
        ledger["task_read_authority"]=True
        errors=verify_documents(seed,binding,authority,ledger)
        self.assertIn("PRE_RESEAL_AUTHORITY_PRESENT:task_read_authority",errors)
        self.assertIn("LEDGER_PRE_RESEAL_AUTHORITY_PRESENT:task_read_authority",errors)

if __name__=="__main__":
    unittest.main(verbosity=2)
