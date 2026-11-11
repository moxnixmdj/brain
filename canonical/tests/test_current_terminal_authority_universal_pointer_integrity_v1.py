import hashlib, json, pathlib, unittest

ROOT=pathlib.Path("/home/sprite")
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

def git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class CurrentTerminalAuthorityUniversalPointerIntegrityV1(unittest.TestCase):
    def test_universal_route_pointers_match_exact_repository_bytes(self):
        auth=json.loads(AUTH.read_text())
        refs=[
            ("primitive_u_frontier", auth["authoritative_sources"]["universal_escape_resolver_v2_active_planning_overlay"]["primitive_u_frontier"]),
            ("terminal_execution_root", {"path":auth["terminal_execution_root"]["path"],"git_blob_sha":auth["terminal_execution_root"]["git_blob_sha"]}),
            ("u_single_primitive", auth["zero_bureaucracy_truth_reconciliation_20261007_v2"]["theorem_source"]),
            ("gdpval_eval_law_cut", auth["gdpval_evaluation_law_minimum_information_cut_20261008_v1"]["governance"]),
            ("gdpval_quotient", auth["gdpval_evaluator_facing_quotient_u_route_20261008_v1"]["governance"]),
        ]
        mismatches=[]
        for name,ref in refs:
            actual=git_blob(ROOT/ref["path"])
            if actual != ref["git_blob_sha"]:
                mismatches.append((name,ref["git_blob_sha"],actual))
        self.assertEqual(mismatches,[])

if __name__=="__main__":
    unittest.main()
