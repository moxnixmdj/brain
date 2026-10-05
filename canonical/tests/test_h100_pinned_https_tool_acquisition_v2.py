import copy,json,unittest
from canonical.runtime import h100_pinned_https_tool_acquisition_v2 as n

class H100PinnedHTTPSToolV2Tests(unittest.TestCase):
    def test_policy_unchanged_and_negative_controls(self):
        pre=json.loads(n.PRE.read_text()); spec=pre["packs"][0]
        loaded=n.load_tool_pack(n.ROOT/spec["path"],spec["git_blob_sha"],pre["network_contract"])
        bad=copy.deepcopy(loaded["pack"]); bad["host"]="example.com"
        with self.assertRaisesRegex(n.PinnedHTTPSToolError,"HOST_NOT_ALLOWLISTED"):
            n._validate_pack_obj(bad,pre["network_contract"])
        bad=copy.deepcopy(loaded["pack"]); bad["path"]=bad["path"]+"?x=1"
        with self.assertRaisesRegex(n.PinnedHTTPSToolError,"REMOTE_PATH_HAS_FORBIDDEN_COMPONENT"):
            n._validate_pack_obj(bad,pre["network_contract"])

    def test_fresh_two_pack_gate(self):
        out=n.run()
        self.assertEqual(out["status"],"PASS__FRESH_PINNED_HTTPS_READ_ONLY_TOOL_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT",out)
        self.assertEqual(len(out["tools"]),2)
        self.assertTrue(all(x["pass"] for x in out["tools"]),out)
        self.assertEqual(out["caller_supplied_endpoints"],0)
        self.assertEqual(out["credentials_used"],0)
        self.assertEqual(out["redirects_followed"],0)
        self.assertEqual(out["shell_calls"],0)
        self.assertEqual(out["subprocess_calls"],0)
        self.assertEqual(out["arbitrary_code_execution"],0)
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__": unittest.main(verbosity=2)
