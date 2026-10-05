import tempfile,unittest
from pathlib import Path
from canonical.runtime import h100_verified_read_only_network_tool_registry_v1 as r

class H100ReadOnlyNetworkToolRegistryV1Tests(unittest.TestCase):
    def test_snapshot(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],2)
        self.assertEqual(s["persistent_learned_bytes"],0)
        self.assertEqual(s["caller_supplied_endpoints"],0)
        self.assertEqual(s["credentials_used"],0)

    def test_both_verified_network_tools_invoke(self):
        expected={
          "PINNED_HTTPS_JSON_FIXTURE_V2":"e137958584786b39f3cecbfccdff0343a734cda70c59bd4b86a8c55dffadd454",
          "PINNED_HTTPS_TEXT_FIXTURE_V2":"6bec09f262ae53e5b9c2098a262cb17e27e783c7cc25b38bf0c556fb22933657"
        }
        for tool_id,sha in expected.items():
            with tempfile.TemporaryDirectory() as td:
                out=r.invoke(tool_id,Path(td))
                self.assertEqual(out["status"],"VERIFIED_READ_ONLY_NETWORK_TOOL_INVOKED",out)
                self.assertEqual(out["sha256"],sha,out)
                self.assertEqual(out["raw_network_tool_acquisition_attempts_before_hit"],0)
                self.assertEqual(out["credentials_used"],0)

    def test_unknown_network_tool_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(r.ReadOnlyNetworkToolRegistryError,"NETWORK_TOOL_ID_NOT_VERIFIED"):
                r.invoke("GET_WHATEVER_URL_V1",Path(td))

if __name__=="__main__": unittest.main(verbosity=2)
