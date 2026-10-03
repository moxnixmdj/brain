from __future__ import annotations

import json
import urllib.parse
import unittest

from canonical.runtime import wikidata_language_bridge_v1 as bridge
from canonical.runtime import adaptive_retrieval_query_expansion_v1 as expandmod
from canonical.runtime import public_source_federation_v1 as federation
from canonical.runtime import retrieval_adversarial_recall_benchmark_v1 as bench


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return self.raw


class WikidataOpener:
    def __init__(self):
        self.urls = []
    def __call__(self, req, timeout=0):
        self.urls.append(req.full_url)
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
        action = qs.get("action", [""])[0]
        if action == "wbsearchentities":
            return FakeResponse({"search":[{"id":"Q123","label":"serializer"}]})
        if action == "wbgetentities":
            return FakeResponse({
                "entities":{
                    "Q123":{
                        "labels":{
                            "zh":{"language":"zh","value":"编码器"},
                            "ar":{"language":"ar","value":"محوّل"},
                            "ru":{"language":"ru","value":"сериализатор"},
                        },
                        "aliases":{
                            "zh":[{"language":"zh","value":"序列化器"}],
                            "ar":[],
                            "ru":[],
                        }
                    }
                }
            })
        raise AssertionError(req.full_url)


class RetrievalV3Tests(unittest.TestCase):
    def test_wikidata_bridge_generates_cross_script_variants_candidate_only(self):
        opener = WikidataOpener()
        out = bridge.expand(["serializer"], languages=["zh","ar","ru"], opener=opener)
        texts = {x["text"] for x in out["variants"]}
        self.assertIn("编码器", texts)
        self.assertIn("محوّل", texts)
        self.assertIn("сериализатор", texts)
        self.assertFalse(out["complete"])
        self.assertFalse(out["semantic_equivalence_verified"])
        self.assertEqual(out["authority"], "CANDIDATE_QUERY_EXPANSION_ONLY")

    def test_wikidata_no_match_is_unknown_not_nonexistence(self):
        class NoMatch:
            def __call__(self, req, timeout=0):
                return FakeResponse({"search":[]})
        out = bridge.expand(["opaque phrase"], languages=["zh"], opener=NoMatch())
        self.assertEqual(out["status"], "NO_ENTITY_MATCH__UNKNOWN_NOT_NONEXISTENCE")
        self.assertFalse(out["complete"])

    def test_adaptive_expansion_preserves_native_variants_and_harvests_unicode(self):
        program = {
            "query_lattice":[
                {"text":"UBJSON serializer","basis":"RESIDUAL_EFFECT"},
                {"text":"dumpb","basis":"OBSERVABLE_API_SYMBOLS"},
            ],
            "effect":"serialize binary data",
        }
        variants = [
            {"text":"编码器","language":"zh","source":"WIKIDATA","qid":"Q1"},
            {"text":"сериализатор","language":"ru","source":"WIKIDATA","qid":"Q1"},
        ]
        candidates = [
            {"source":"github","title":"UBJSON 高速编码器","path":"src/codec.py"},
            {"source":"gitlab","title":"сериализатор UBJSON","path":"lib/codec.py"},
        ]
        out = expandmod.expand(program, bridge_variants=variants, prior_candidates=candidates)
        texts = {x["text"] for x in out["new_queries"]}
        self.assertIn("编码器", texts)
        self.assertIn("сериализатор", texts)
        self.assertTrue(any("高速编码器" in x or "编码器" in x for x in texts))
        self.assertFalse(out["complete"])
        self.assertFalse(out["semantic_equivalence_verified"])

    def test_federation_has_orthogonal_hosts(self):
        out = federation.compile_federation(["UBJSON serializer"], max_queries_per_source=1)
        domains = {x["domain"] for x in out["requests"]}
        for expected in ("github.com","gitlab.com","gitee.com","codeberg.org","huggingface.co","pypi.org","npmjs.com","crates.io","arxiv.org","stackoverflow.com"):
            self.assertIn(expected, domains)
        self.assertFalse(out["complete"])
        self.assertTrue(all(x["authority"] == "CANDIDATE_ONLY" for x in out["requests"]))

    def test_finite_adversarial_observable_universe_has_perfect_recall(self):
        out = bench.run()
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["recall"], 1.0, out)
        self.assertEqual(out["misses"], [], out)
        self.assertFalse(out["unbridgeable_fixture"]["found"], out)
        self.assertEqual(out["unbridgeable_fixture"]["correct_state"], "UNKNOWN")
        self.assertFalse(out["unbridgeable_fixture"]["nonexistence_allowed"])

    def test_unbridgeable_fixture_not_smuggled_into_completeness_claim(self):
        out = bench.run()
        self.assertIn("NO_SYNTHETIC_FIXTURE_PASS_TO_OPEN_WORLD_COMPLETENESS_INFERENCE", out["hard_rules"])
        self.assertIn("UNBRIDGEABLE_OPEN_WORLD_ARTIFACT_MUST_REMAIN_UNKNOWN", out["hard_rules"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
