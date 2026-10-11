import json
import unittest
from canonical.runtime.bound_capabilities.wikidata_entity_search_v1 import search, WikidataSearchError

def fake(url,timeout=15):
    return json.dumps({
      "search":[
        {"id":"Q60","label":"New York City","description":"largest city in the United States",
         "concepturi":"http://www.wikidata.org/entity/Q60","url":"//www.wikidata.org/wiki/Q60",
         "match":{"type":"label","language":"en","text":"New York City"}},
        {"id":"BAD","label":"bad"},
        {"id":"Q60","label":"duplicate"},
      ]
    }).encode()

class WikidataEntitySearchV1Tests(unittest.TestCase):
    def test_normalizes_and_filters_entities(self):
        x=search("  New   York  ",limit=5,fetch_fn=fake)
        self.assertEqual(x["candidate_count"],1)
        self.assertEqual(x["candidates"][0]["entity_id"],"Q60")
        self.assertEqual(x["query"],"New York")
        self.assertFalse(x["candidates"][0]["answer_authority"])
        self.assertFalse(x["nonexistence_claim_authorized"])

    def test_zero_external_cognition(self):
        x=search("x",fetch_fn=fake)
        self.assertFalse(x["gold_accessed"])
        self.assertEqual(x["external_model_calls"],0)
        self.assertEqual(x["external_reasoning_model_calls"],0)
        self.assertEqual(x["model_dependency_count"],0)

    def test_empty_is_not_nonexistence(self):
        x=search("x",fetch_fn=lambda *a,**k:b'{"search":[]}')
        self.assertEqual(x["status"],"NO_CANDIDATES")
        self.assertFalse(x["nonexistence_claim_authorized"])

    def test_malformed_response_fails_closed(self):
        with self.assertRaises(WikidataSearchError):
            search("x",fetch_fn=lambda *a,**k:b'{}')

    def test_input_bounds(self):
        with self.assertRaises(ValueError): search("",fetch_fn=fake)
        with self.assertRaises(ValueError): search("x"*601,fetch_fn=fake)

if __name__=="__main__":
    unittest.main(verbosity=2)
