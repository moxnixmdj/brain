from __future__ import annotations
import json, unittest
from pathlib import Path
from canonical.runtime import hle_tools_policy_kernel_v1 as k

P=k.load_policy()

class TestHLEToolsPolicyKernelV1(unittest.TestCase):
    def test_official_policy_fields_and_limits(self):
        self.assertEqual(k.MAX_SEARCH_RESULTS,20)
        self.assertEqual(k.MAX_FETCH_CHARS,60000)
        self.assertEqual(set(P),{
            "domains","url_prefixes","serp_url_patterns","url_patterns",
            "patterns_case_sensitive","answer_title_patterns","answer_title_allow_hosts"
        })

    def test_domain_and_subdomain_block(self):
        for u in ("https://huggingface.co/x","https://sub.huggingface.co/x"):
            with self.assertRaises(k.HLEPolicyBlocked):
                k.check_fetch_url(u,policy=P)

    def test_url_prefix_ignores_scheme_www_case(self):
        with self.assertRaises(k.HLEPolicyBlocked):
            k.check_fetch_url("HTTPS://WWW.NATURE.COM/articles/s41586-025-09962-4?x=1",policy=P)

    def test_serp_url_block(self):
        with self.assertRaises(k.HLEPolicyBlocked):
            k.check_fetch_url("https://www.google.com/search?q=abc",policy=P)

    def test_percent_encoded_proxy_embedded_block(self):
        embedded="https%253A%252F%252Fhuggingface.co%252Fdatasets%252Fcais%252Fhle"
        with self.assertRaises(k.HLEPolicyBlocked):
            k.check_fetch_url("https://example.org/proxy?url="+embedded,policy=P)

    def test_search_blocked_site_domain(self):
        with self.assertRaises(k.HLEPolicyBlocked):
            k.check_search_query(
                "site:huggingface.co difficult chemistry",
                question="different question words entirely",
                verbatim_threshold_words=8,policy=P
            )

    def test_unpublished_verbatim_threshold_fails_closed(self):
        with self.assertRaises(k.HLEPolicyBlocked) as cm:
            k.check_search_query("safe query",question="safe question",verbatim_threshold_words=None,policy=P)
        self.assertEqual(cm.exception.code,"UNPUBLISHED_VERBATIM_THRESHOLD_UNBOUND")

    def test_long_verbatim_span_with_explicit_threshold(self):
        q="alpha beta gamma delta epsilon"
        with self.assertRaises(k.HLEPolicyBlocked):
            k.check_search_query(q,question="zero alpha beta gamma delta epsilon omega",
                                 verbatim_threshold_words=5,policy=P)

    def test_search_caps_before_filter_and_filters_title_snippet(self):
        rows=[{"url":f"https://example{i}.org/x","title":"ordinary","snippet":"ordinary"} for i in range(25)]
        out=k.filter_search_results("safe query",rows,question="unrelated words here",
                                    verbatim_threshold_words=8,policy=P)
        self.assertEqual(out["pre_filter_count"],20)
        self.assertEqual(out["returned_count"],20)

        bad=[{"url":"https://example.org/x","title":"HLE answer key","snippet":"ordinary"}]
        out=k.filter_search_results("safe query",bad,question="unrelated words here",
                                    verbatim_threshold_words=8,policy=P)
        self.assertEqual(out["returned_count"],0)

    def test_answer_title_allow_host_exempts_only_answer_pattern(self):
        row=[{"url":"https://wikipedia.org/wiki/Test","title":"Puzzle answers","snippet":"ordinary"}]
        out=k.filter_search_results("safe query",row,question="unrelated words here",
                                    verbatim_threshold_words=8,policy=P)
        self.assertEqual(out["returned_count"],1)

    def test_fetch_post_content_scan_applies_to_cached_too(self):
        for cached in (False,True):
            with self.assertRaises(k.HLEPolicyBlocked):
                k.filter_fetch_result("https://example.org/x",title="ordinary",
                    markdown="Humanity's Last Exam answer dataset",cached=cached,policy=P)

    def test_fetch_cap_has_indicator_and_never_exceeds_limit(self):
        out=k.filter_fetch_result("https://example.org/x",title="ordinary",
                                  markdown="x"*70000,policy=P)
        self.assertTrue(out["truncated"])
        self.assertLessEqual(len(out["markdown"]),60000)
        self.assertTrue(out["markdown"].endswith("[TRUNCATED]"))

    def test_case_sensitive_rules_are_case_sensitive(self):
        # The official case-sensitive list contains HLE patterns.
        with self.assertRaises(k.HLEPolicyBlocked):
            k.filter_fetch_result("https://example.org/x",title="ordinary",
                                  markdown="HLE benchmark answers",policy=P)

    def test_preflight_names_exact_unpublished_residuals(self):
        out=k.policy_preflight(verbatim_threshold_words=None)
        self.assertEqual(out["status"],"FAIL_CLOSED__UNPUBLISHED_PARAMETERS_OPEN")
        self.assertIn("OFFICIAL_LONG_VERBATIM_SPAN_THRESHOLD",out["unresolved_exact_harness_parameters"])
        self.assertIn("OFFICIAL_TRAILING_SITE_NAME_STRIPPER_EXACT_ALGORITHM",out["unresolved_exact_harness_parameters"])

if __name__=="__main__":
    unittest.main()
