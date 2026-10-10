from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import r2_bound_source_information_provider_v1 as p


POLICY = b"Total exposure means exposure_amount."
FACT = b'{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{"exposure_amount":{"type":"decimal","value":"10"}}}'


def _request():
    return {
        "schema": p.REQUEST_SCHEMA,
        "acquisition_plan": {
            "pass": True,
            "action": p.ACTION,
            "source_id": "bound.finance",
            "external_research_authorized": False,
        },
        "source_scope": {
            "kind": p.BOUND_SOURCE,
            "source_id": "bound.finance",
            "policy_url": "https://evidence.example/policy.txt",
            "policy_source_id": "policy:bound",
            "policy_sha256": sha256(POLICY).hexdigest(),
            "fact_url": "https://evidence.example/facts.json",
            "fact_source_id": "facts:bound",
            "fact_sha256": sha256(FACT).hexdigest(),
        },
    }


class Tests(unittest.TestCase):
 def test_bound_source_provider_emits_raw_material_without_truth_authority(self):
    calls = []
    blobs = {
        "https://evidence.example/policy.txt": POLICY,
        "https://evidence.example/facts.json": FACT,
    }

    def fetch(url, *, max_bytes):
        calls.append((url, max_bytes))
        return blobs[url]

    out = p.provide(_request(), fetcher=fetch)
    assert out["kind"] == p.raw_material.KIND
    assert out["source_text"] == POLICY.decode()
    assert out["source_id"] == "policy:bound"
    assert out["fact_source"] == FACT
    assert out["fact_source_id"] == "facts:bound"
    assert "predicate_truth" not in out
    assert "semantic_truth_authority" not in out
    assert len(calls) == 2


 def test_bound_source_provider_rejects_hash_drift_and_non_https(self):
    req = _request()
    req["source_scope"]["policy_sha256"] = "0" * 64

    def fetch(url, *, max_bytes):
        return POLICY if url.endswith("policy.txt") else FACT

    out = p.provide(req, fetcher=fetch)
    assert out["pass"] is False
    assert "SHA256_MISMATCH" in out["reason"]

    req = _request()
    req["source_scope"]["policy_url"] = "http://evidence.example/policy.txt"
    out = p.provide(req, fetcher=fetch)
    assert out["pass"] is False
    assert "MUST_BE_HTTPS" in out["reason"]


 def test_bound_source_provider_refuses_unbound_or_research_requests(self):
    req = _request()
    req["acquisition_plan"]["action"] = "RESEARCH_MINIMUM_AUTHENTICATED_FACT"
    assert p.provide(req, fetcher=lambda *a, **k: POLICY) is None

    req = _request()
    req["source_scope"]["kind"] = "UNBOUND_SOURCE"
    assert p.provide(req, fetcher=lambda *a, **k: POLICY) is None


if __name__ == "__main__":
    unittest.main(verbosity=2)
