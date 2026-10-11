import json
import urllib.parse
import unittest
from canonical.runtime.bound_capabilities.wikidata_entity_neighborhood_v1 import neighborhood, WikidataNeighborhoodError

def fake(url,timeout=15):
    q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    ids=(q.get("ids") or [""])[0].split("|")
    if "Q1" in ids:
        return json.dumps({"entities":{"Q1":{
          "labels":{"en":{"value":"Example Person"}},
          "descriptions":{"en":{"value":"test person"}},
          "claims":{"P69":[{"mainsnak":{"datavalue":{"value":{"entity-type":"item","id":"Q2","numeric-id":2},"type":"wikibase-entityid"}}}]}
        }}}).encode()
    ents={}
    if "P69" in ids: ents["P69"]={"labels":{"en":{"value":"educated at"}},"descriptions":{"en":{"value":"educational institution attended"}}}
    if "Q2" in ids: ents["Q2"]={"labels":{"en":{"value":"Example University"}},"descriptions":{"en":{"value":"university"}}}
    return json.dumps({"entities":ents}).encode()

class WikidataNeighborhoodV1Tests(unittest.TestCase):
    def test_resolves_linked_entity_and_property_labels(self):
        x=neighborhood(["Q1"],fetch_fn=fake)
        self.assertEqual(x["edge_count"],1)
        e=x["edges"][0]
        self.assertEqual(e["property_label"],"educated at")
        self.assertEqual(e["target_label"],"Example University")
        self.assertFalse(e["answer_authority"])

    def test_zero_cognition_and_authority(self):
        x=neighborhood(["Q1"],fetch_fn=fake)
        self.assertFalse(x["gold_accessed"])
        self.assertEqual(x["external_model_calls"],0)
        self.assertEqual(x["model_dependency_count"],0)
        self.assertFalse(x["correctness_authority"])
        self.assertFalse(x["nonexistence_claim_authorized"])

    def test_invalid_qid_fails(self):
        with self.assertRaises(ValueError): neighborhood(["P69"],fetch_fn=fake)

    def test_malformed_api_fails_closed(self):
        with self.assertRaises(WikidataNeighborhoodError):
            neighborhood(["Q1"],fetch_fn=lambda *a,**k:b'{}')

if __name__=="__main__":
    unittest.main(verbosity=2)
