import unittest
from unittest.mock import patch
from model_independent_source_discovery import semantic_query, query_variants, parse_bing_rss, parse_ddg_html, aggregate, Hit, discover

BING=b'''<?xml version="1.0"?><rss><channel>
<item><title>Python 3 documentation</title><link>https://docs.python.org/3/library/tarfile.html?utm_source=x</link><description>tarfile module reference</description></item>
<item><title>NIST standard</title><link>https://csrc.nist.gov/publications/detail/fips/180/4/final</link><description>Secure Hash Standard</description></item>
</channel></rss>'''
DDG=b'''<html><body>
<a rel="nofollow" class="result-link" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Ftarfile.html">Python tarfile</a>
<a class="result__a" href="https://stackoverflow.com/questions/1">community answer</a>
</body></html>'''

class T(unittest.TestCase):
    def test_query_removes_instruction_noise(self):
        q=semantic_query("Determine whether Python tar archives preserve file metadata. Find and cite authoritative sources, perform a real experiment, and independently verify the result.")
        self.assertIn("python",q); self.assertIn("tar",q); self.assertIn("archives",q)
        self.assertNotIn("authoritative",q); self.assertNotIn("independently",q)
    def test_variants_are_generic(self):
        v=query_variants("Assess POSIX rename atomicity on one filesystem")
        self.assertEqual(len(v),4); self.assertTrue(v[1].endswith("official documentation"))
    def test_bing_rss(self):
        h=parse_bing_rss(BING,"q")
        self.assertEqual(len(h),2)
        self.assertEqual(h[0].url,"https://docs.python.org/3/library/tarfile.html")
    def test_ddg_unwrap(self):
        h=parse_ddg_html(DDG,"q")
        self.assertEqual(h[0].url,"https://docs.python.org/3/library/tarfile.html")
    def test_aggregation_rewards_consensus_and_penalizes_social(self):
        hits=parse_bing_rss(BING,"q")+parse_ddg_html(DDG,"q")
        out=aggregate("Python tarfile module reference",hits,10)
        self.assertEqual(out[0]["host"],"docs.python.org")
        self.assertEqual(out[0]["provider_count"],2)
        self.assertFalse(out[0]["authority_verified"])
        social=[x for x in out if x["host"]=="stackoverflow.com"][0]
        self.assertLess(social["discovery_score"],out[0]["discovery_score"])

    def test_malformed_bing_fails_closed(self):
        with self.assertRaises(RuntimeError):
            parse_bing_rss(b"<rss><broken>", "q")

    def test_host_diversity_cap(self):
        hits=[Hit("BING_RSS","q",i+1,f"https://docs.example.org/p{i}",f"p{i}","") for i in range(5)]
        hits += [Hit("BING_RSS","q",6,"https://other.example.net/x","other","")]
        out=aggregate("example technical reference",hits,10)
        self.assertLessEqual(sum(x["host"]=="docs.example.org" for x in out),2)
        self.assertTrue(any(x["host"]=="other.example.net" for x in out))

    def test_discover_survives_one_provider_failure_and_never_claims_authority(self):
        h=[Hit("BING_RSS","alpha",1,"https://csrc.nist.gov/pubs/fips/180-4/upd1/final","NIST FIPS","")]
        with patch("model_independent_source_discovery.search_bing_rss", return_value=h), \
             patch("model_independent_source_discovery.search_ddg_lite", side_effect=RuntimeError("blocked")):
            r=discover("Assess SHA-256 specification behavior", max_variants=1)
        self.assertEqual(r["status"],"CANDIDATES_DISCOVERED_AUTHORITY_UNVERIFIED")
        self.assertFalse(r["authority_claim"])
        self.assertFalse(r["candidates"][0]["authority_verified"])
        self.assertTrue(any(not a["ok"] for a in r["attempts"]))

    def test_instruction_heavy_goal_is_bounded(self):
        g=("Determine whether a system property holds. Find and cite authoritative primary technical sources. "
           "Perform a real executable experiment. Independently verify every material claim. Preserve provenance. "
           "Explain limitations and produce a decision-quality result with many additional procedural words.")
        q=semantic_query(g)
        self.assertLessEqual(len(q.split()),18)
        self.assertNotIn("provenance",q)

if __name__=='__main__': unittest.main()
