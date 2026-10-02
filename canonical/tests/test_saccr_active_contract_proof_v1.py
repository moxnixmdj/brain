import inspect, unittest
from canonical.runtime.saccr_active_contract_proof_v1 import generate_case,public_task,score_case
from canonical.runtime.saccr_active_contract_candidate_v1 import solve

class Tests(unittest.TestCase):
    def test_information_boundary(self):
        c=generate_case(1); p=public_task(c)
        self.assertNotIn("_oracle",p)
        import canonical.runtime.saccr_active_contract_proof_v1 as oracle
        import canonical.runtime.saccr_active_contract_candidate_v1 as candidate
        self.assertNotIn("saccr_credit_kernel",inspect.getsource(oracle))
        self.assertNotIn("saccr_active_contract_proof",inspect.getsource(candidate))
    def test_dev_population(self):
        for seed in range(1000,1256):
            c=generate_case(seed); out=solve(public_task(c))
            self.assertTrue(score_case(c,out)["pass"],(seed,score_case(c,out),out))
if __name__=="__main__": unittest.main(verbosity=2)
