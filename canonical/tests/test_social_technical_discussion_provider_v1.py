from __future__ import annotations
import json, urllib.parse, unittest
from canonical.runtime import social_technical_discussion_provider_v1 as social
from canonical.runtime import social_technical_discussion_binding_candidate_v1 as binding
from canonical.runtime import residual_witness_backend_router_v1 as router

class FakeResponse:
    def __init__(self,payload): self.raw=json.dumps(payload,ensure_ascii=False).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return self.raw

class Opener:
    def __init__(self): self.urls=[]
    def __call__(self,req,timeout=0):
        self.urls.append(req.full_url)
        return FakeResponse({"hits":[{
            "objectID":"123","title":"中文 工具 讨论",
            "url":"https://example.org/tool","author":"alice"
        }]})

class SocialProviderTests(unittest.TestCase):
    def tearDown(self): router.clear_external_providers()

    def test_unicode_and_zero_credit(self):
        opener=Opener()
        out=social.search({
            "action":"QUERY","query_id":"Q000","query":"中文 工具",
            "surface":"SOCIAL_TECHNICAL_DISCUSSION",
        },opener=opener)
        self.assertEqual(out["candidate_count"],1,out)
        self.assertIn("中文 工具",urllib.parse.unquote_plus(opener.urls[0]))
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["complete"])
        self.assertFalse(out["independently_complete"])
        self.assertEqual(out["acceptance_credit"],0)

    def test_binding_candidate_is_explicit_and_zero_credit(self):
        rec=binding.bind()
        self.assertEqual(rec["status"],"BOUND_CANDIDATE_ONLY__ZERO_CREDIT")
        self.assertEqual(rec["surface"],"SOCIAL_TECHNICAL_DISCUSSION")
        self.assertFalse(rec["complete"])
        self.assertFalse(rec["independently_complete"])
        self.assertEqual(rec["acceptance_credit"],0)

if __name__=="__main__": unittest.main(verbosity=2)
