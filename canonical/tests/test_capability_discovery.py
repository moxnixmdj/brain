#!/usr/bin/env python3
import importlib.util
import io
import json
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = CANONICAL_ROOT / "runtime" / "capability_discovery.py"
spec = importlib.util.spec_from_file_location("capability_discovery_test_target", PATH)
discovery = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = discovery
spec.loader.exec_module(discovery)

FIXTURE = json.loads(r'''{
  "servers": [
    {
      "server": {
        "name": "io.example/free-filesystem",
        "description": "filesystem tools",
        "version": "1.0.0",
        "packages": [
          {
            "registryType": "npm",
            "identifier": "free-fs",
            "version": "1.0.0",
            "runtimeHint": "npx",
            "transport": {
              "type": "stdio"
            },
            "environmentVariables": [
              {
                "name": "WORKSPACE_ROOT",
                "isRequired": true
              }
            ]
          }
        ]
      },
      "_meta": {
        "io.modelcontextprotocol.registry/official": {
          "status": "active",
          "isLatest": true
        }
      }
    },
    {
      "server": {
        "name": "io.example/paid-filesystem",
        "description": "premium filesystem",
        "version": "1.0.0",
        "remotes": [
          {
            "type": "sse",
            "url": "https://example.invalid/sse",
            "headers": [
              {
                "name": "Payment-Signature",
                "isSecret": true,
                "description": "x402 payment in USDC"
              }
            ]
          }
        ]
      },
      "_meta": {
        "io.modelcontextprotocol.registry/official": {
          "status": "active",
          "isLatest": true
        }
      }
    }
  ]
}''')

class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return self.payload

def fake_open(req, timeout=0):
    return FakeResponse(FIXTURE)

class CapabilityDiscoveryTests(unittest.TestCase):
    def test_effect_query_is_deterministic(self):
        self.assertEqual(discovery.effect_queries("filesystem.read"), ["filesystem"])

    def test_zero_cost_candidate_ranks_before_paid_candidate(self):
        out = discovery.search_mcp_registry("filesystem.read", opener=fake_open)
        self.assertEqual(out["candidates"][0]["name"], "io.example/free-filesystem")
        self.assertTrue(out["candidates"][0]["zero_cost_eligible"])
        paid = [c for c in out["candidates"] if c["name"] == "io.example/paid-filesystem"][0]
        self.assertFalse(paid["zero_cost_eligible"])

    def test_discovery_never_binds_during_search(self):
        out = discovery.search_mcp_registry("filesystem.read", opener=fake_open)
        self.assertFalse(out["binding_performed"])

    def test_apt_discovery_keeps_late_split_compound_match(self):
        noise="\n".join(f"noise-{i} - unrelated package" for i in range(650))
        search_out=noise+"\nzbar-tools - QR code / bar code scanner and decoder (utilities)\n"
        def fake_run(argv, text=True, capture_output=True, timeout=None):
            class R:
                returncode=0
                stderr=""
                stdout=""
            r=R()
            if argv[:2]==["apt-cache","search"]:
                r.stdout=search_out
            elif argv[:2]==["apt-cache","policy"]:
                r.stdout="zbar-tools:\n  Candidate: 0.23.93-4build3\n"
            elif argv[:2]==["apt-cache","show"]:
                r.stdout="Package: zbar-tools\nSHA256: "+"a"*64+"\n"
            return r
        with mock.patch.object(discovery.sys.platform.__class__, "__str__", return_value="linux"):
            pass
        with mock.patch.object(discovery.shutil, "which", return_value="/usr/bin/apt-cache"), \
             mock.patch.object(discovery.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(discovery.sys, "platform", "linux"):
            out=discovery.search_apt_packages("decode barcode image", limit=50)
        names=[x["name"] for x in out["candidates"]]
        self.assertIn("zbar-tools",names)
        cand=[x for x in out["candidates"] if x["name"]=="zbar-tools"][0]
        self.assertIn("barcode",cand["matched_terms"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
