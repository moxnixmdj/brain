import unittest
from canonical.runtime import hle_wikipedia_bing_transport_v1 as w

class WikipediaBingTransportV1Tests(unittest.TestCase):
    def test_filters_to_articles_and_fetches(self):
        def search(q,**k):
            self.assertTrue(q.startswith("site:en.wikipedia.org/wiki "))
            return {"results":[
              {"url":"https://en.wikipedia.org/wiki/Alpha"},
              {"url":"https://en.wikipedia.org/wiki/Category:Wrong"},
              {"url":"https://example.org/No"},
              {"url":"https://en.wikipedia.org/wiki/Beta"},
            ],"attempts":[{"engine":"bing_rss","status":"OK"}]}
        def fetch(url,**k):
            return {"status":"PASS","body_excerpt":"<script>x</script><p>Hello &amp; world</p>"}
        out=w.retrieve(query="visible clue",search_fn=search,fetch_fn=fetch)
        self.assertEqual(out["candidate_url_count"],2)
        self.assertEqual(out["successful_page_count"],2)
        self.assertTrue(all(x["text"]=="Hello & world" for x in out["pages"]))
        self.assertFalse(out["gold_accessed"])
        self.assertEqual(out["external_model_calls"],0)

    def test_search_failure_retryable(self):
        def search(*a,**k):raise TimeoutError("x")
        out=w.retrieve(query="visible",search_fn=search,fetch_fn=lambda *a,**k:{})
        self.assertEqual(out["status"],"SEARCH_FAILED_RETRYABLE")
        self.assertTrue(out["retryable"])
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_page_failure_retryable(self):
        def search(*a,**k):return {"results":[{"url":"https://en.wikipedia.org/wiki/Alpha"}],"attempts":[]}
        def fetch(*a,**k):raise TimeoutError("x")
        out=w.retrieve(query="visible",search_fn=search,fetch_fn=fetch)
        self.assertEqual(out["status"],"PAGE_FETCH_FAILED_RETRYABLE")
        self.assertEqual(out["failed_retryable_page_count"],1)
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_empty_is_not_nonexistence(self):
        out=w.retrieve(query="visible",search_fn=lambda *a,**k:{"results":[],"attempts":[]},fetch_fn=lambda *a,**k:{})
        self.assertEqual(out["status"],"NO_WIKIPEDIA_CANDIDATES_YET")
        self.assertFalse(out["nonexistence_claim_authorized"])

if __name__=="__main__":unittest.main(verbosity=2)
