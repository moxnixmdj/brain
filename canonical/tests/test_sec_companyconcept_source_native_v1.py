from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime.bound_capabilities import sec_companyconcept_source_native as p
from canonical.runtime import sec_companyconcept_source_native_verify_v1 as v
from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir


def _payload():
    return {
        "cik": 320193,
        "taxonomy": "us-gaap",
        "tag": "GrossProfit",
        "label": "Gross Profit",
        "description": "Revenue less cost of goods and services sold.",
        "entityName": "Apple Inc.",
        "units": {
            "USD": [
                {
                    "start": "2025-09-29",
                    "end": "2026-09-26",
                    "val": 100,
                    "accn": "0000320193-26-000001",
                    "fy": 2026,
                    "fp": "FY",
                    "form": "10-K",
                    "filed": "2026-10-01",
                    "frame": "CY2026",
                }
            ]
        },
    }


def _config():
    return {
        "cik": 320193,
        "taxonomy": "us-gaap",
        "tag": "GrossProfit",
        "sec_user_agent": "ProjectBrain research@example.com",
    }


def _args():
    return {
        "config_path": "canonical/tmp/sec_companyconcept_config.json",
        "raw_output_path": "canonical/tmp/sec_companyconcept_raw.json",
        "semantic_output_path": "canonical/tmp/sec_companyconcept_semantic.json",
    }


def _fake_fetch(payload=None, *, final_url=None, content_type="application/json"):
    raw = json.dumps(payload or _payload(), separators=(",", ":")).encode("utf-8")

    def fetch(url, user_agent, timeout, max_bytes):
        return raw, final_url or url, content_type, 200

    return fetch


class SecCompanyConceptSourceNativeTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _write_config(self, config=None):
        path = self.root / "canonical/tmp/sec_companyconcept_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config or _config()), encoding="utf-8")
        return path

    def test_standard_concept_emits_source_traceable_semantics(self):
        self._write_config()
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            out = p.run(_args(), self.root)
        self.assertFalse(out["output_verified"])
        self.assertTrue(out["independent_verification_required"])
        self.assertEqual(out["concept_qname"], "us-gaap:GrossProfit")
        self.assertTrue(out["source_native_identity_extracted"])
        self.assertFalse(out["semantic_authority_claimed"])
        self.assertFalse(out["custom_taxonomy_covered"])
        self.assertFalse(out["raw_prose_wsd_claimed"])

        semantic = json.loads(
            (self.root / _args()["semantic_output_path"]).read_text(encoding="utf-8")
        )
        ir = compile_semantic_ir(semantic["semantic_contract"])
        self.assertEqual(ir["status"], "COMPILED", ir)

        check = v.verify(
            root=self.root,
            raw_path=_args()["raw_output_path"],
            semantic_path=_args()["semantic_output_path"],
        )
        self.assertTrue(check["verified"], check)
        self.assertEqual(check["concept_qname"], "us-gaap:GrossProfit")

    def test_custom_taxonomy_is_outside_v1(self):
        config = _config()
        config.update({"taxonomy": "aroc", "tag": "GrossMargin"})
        self._write_config(config)
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            with self.assertRaisesRegex(
                RuntimeError, "^TAXONOMY_OUTSIDE_V1_STANDARD_SCOPE$"
            ):
                p.run(_args(), self.root)

    def test_declared_sec_user_agent_contact_is_required(self):
        config = _config()
        config["sec_user_agent"] = "ProjectBrain"
        self._write_config(config)
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            with self.assertRaisesRegex(
                RuntimeError, "^SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED$"
            ):
                p.run(_args(), self.root)

    def test_payload_identity_mismatch_fails_closed(self):
        self._write_config()
        payload = _payload()
        payload["tag"] = "OperatingIncomeLoss"
        with mock.patch.object(p, "_fetch", _fake_fetch(payload)):
            with self.assertRaisesRegex(RuntimeError, "^PAYLOAD_TAG_MISMATCH$"):
                p.run(_args(), self.root)

    def test_redirect_away_from_canonical_endpoint_fails_closed(self):
        self._write_config()
        with mock.patch.object(
            p,
            "_fetch",
            _fake_fetch(final_url="https://www.sec.gov/not-the-companyconcept-endpoint"),
        ):
            with self.assertRaisesRegex(RuntimeError, "^SEC_FINAL_URL_MISMATCH$"):
                p.run(_args(), self.root)

    def test_verifier_rejects_semantic_identity_tamper(self):
        self._write_config()
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            p.run(_args(), self.root)
        semantic_path = self.root / _args()["semantic_output_path"]
        semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
        semantic["concept_qname"] = "us-gaap:OperatingIncomeLoss"
        semantic_path.write_text(json.dumps(semantic), encoding="utf-8")
        check = v.verify(
            root=self.root,
            raw_path=_args()["raw_output_path"],
            semantic_path=_args()["semantic_output_path"],
        )
        self.assertFalse(check["verified"], check)
        self.assertIn("SEMANTIC_FIELD_MISMATCH:concept_qname", check["errors"])

    def test_verifier_rejects_inner_fact_value_tamper(self):
        self._write_config()
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            p.run(_args(), self.root)
        semantic_path = self.root / _args()["semantic_output_path"]
        semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
        for fact in semantic["semantic_contract"]["facts"]:
            if fact.get("predicate") == "val":
                fact["object"] = 999999
                break
        semantic_path.write_text(json.dumps(semantic), encoding="utf-8")
        check = v.verify(
            root=self.root,
            raw_path=_args()["raw_output_path"],
            semantic_path=_args()["semantic_output_path"],
        )
        self.assertFalse(check["verified"], check)
        self.assertIn(
            "SEMANTIC_CONTRACT_NOT_EXACTLY_DERIVED_FROM_SOURCE_BYTES",
            check["errors"],
        )

    def test_verifier_rejects_relation_deletion(self):
        self._write_config()
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            p.run(_args(), self.root)
        semantic_path = self.root / _args()["semantic_output_path"]
        semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
        semantic["semantic_contract"]["relations"].pop()
        semantic_path.write_text(json.dumps(semantic), encoding="utf-8")
        check = v.verify(
            root=self.root,
            raw_path=_args()["raw_output_path"],
            semantic_path=_args()["semantic_output_path"],
        )
        self.assertFalse(check["verified"], check)
        self.assertIn(
            "SEMANTIC_CONTRACT_NOT_EXACTLY_DERIVED_FROM_SOURCE_BYTES",
            check["errors"],
        )

    def test_verifier_rejects_raw_byte_tamper(self):
        self._write_config()
        with mock.patch.object(p, "_fetch", _fake_fetch()):
            p.run(_args(), self.root)
        raw_path = self.root / _args()["raw_output_path"]
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        payload["entityName"] = "Tampered Entity"
        raw_path.write_text(json.dumps(payload), encoding="utf-8")
        check = v.verify(
            root=self.root,
            raw_path=_args()["raw_output_path"],
            semantic_path=_args()["semantic_output_path"],
        )
        self.assertFalse(check["verified"], check)
        self.assertIn("SEMANTIC_FIELD_MISMATCH:source_sha256", check["errors"])

    def test_fact_row_limit_fails_instead_of_truncating(self):
        self._write_config()
        payload = _payload()
        payload["units"]["USD"].append(
            dict(payload["units"]["USD"][0], accn="0000320193-26-000002")
        )
        args = _args()
        args["max_rows"] = 1
        with mock.patch.object(p, "_fetch", _fake_fetch(payload)):
            with self.assertRaisesRegex(RuntimeError, "^FACT_ROW_LIMIT_EXCEEDED$"):
                p.run(args, self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
