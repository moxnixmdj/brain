import ast, inspect, unittest
from canonical.runtime.saccr_active_contract_proof_v1 import generate_case,public_task,score_case
from canonical.runtime.saccr_active_contract_candidate_v1 import solve

def imported_modules(obj):
    tree=ast.parse(inspect.getsource(obj))
    names=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            module=node.module or ""
            names.add(module)
            names.update(module+"."+alias.name for alias in node.names)
    return names

class Tests(unittest.TestCase):
    def test_information_boundary(self):
        c=generate_case(1); p=public_task(c)
        self.assertNotIn("_oracle",p)
        import canonical.runtime.saccr_active_contract_proof_v1 as oracle
        import canonical.runtime.saccr_active_contract_candidate_v1 as candidate
        self.assertFalse(any(x=="canonical.runtime.saccr_credit_kernel" or x.endswith(".saccr_credit_kernel") for x in imported_modules(oracle)))
        self.assertFalse(any(x=="canonical.runtime.saccr_active_contract_proof_v1" or x.endswith(".saccr_active_contract_proof_v1") for x in imported_modules(candidate)))
    def test_dev_population(self):
        for seed in range(1000,1256):
            c=generate_case(seed); out=solve(public_task(c))
            self.assertTrue(score_case(c,out)["pass"],(seed,score_case(c,out),out))
if __name__=="__main__": unittest.main(verbosity=2)
