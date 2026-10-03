#!/usr/bin/env python3
from __future__ import annotations
import json
import urllib.parse
import unittest

from canonical.runtime import github_public_retrieval_provider_v1 as g
from canonical.runtime import residual_witness_backend_router_v1 as router


class FakeResponse:
    def __init__(self,payload):
        self.raw=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return self.raw


class RecordingOpener:
    def __init__(self):
        self.urls=[]
    def __call__(self,req,timeout=0):
        self.urls.append(req.full_url)
        path=urllib.parse.urlsplit(req.full_url).path
        if path=="/search/repositories":
            return FakeResponse({"items":[{
                "full_name":"例子/无描述仓库",
                "html_url":"https://github.com/example/repo",
                "description":None,
                "language":"Python",
                "default_branch":"main",
                "archived":False,
                "fork":False,
            }]})
        if path=="/search/code":
            return FakeResponse({"items":[{
                "name":"codec.py",
                "path":"src/codec.py",
                "sha":"a"*40,
                "html_url":"https://github.com/example/repo/blob/main/src/codec.py",
                "repository":{"full_name":"example/repo"},
            }]})
        if path=="/search/issues":
            return FakeResponse({"items":[{
                "html_url":"https://github.com/example/repo/issues/1",
                "repository_url":"https://api.github.com/repos/example/repo",
                "title":"编解码器 failure",
                "state":"open",
            }]})
        if path=="/search/commits":
            return FakeResponse({"items":[{
                "sha":"b"*40,
                "html_url":"https://github.com/example/repo/commit/"+"b"*40,
                "repository":{"full_name":"example/repo"},
                "commit":{"message":"修复 UBJSON 编码"},
            }]})
        raise AssertionError(req.full_url)


class GitHubPublicRetrievalProviderTests(unittest.TestCase):
    def action(self,surface,query="中文 UBJSON 编解码器"):
        return {
            "action":"QUERY",
            "query_id":"Q000",
            "query":query,
            "surface":surface,
        }

    def test_unicode_query_reaches_github_without_ascii_collapse(self):
        opener=RecordingOpener()
        out=g.search(self.action("CODE_CONTENT"),opener=opener)
        self.assertEqual(out["candidate_count"],1,out)
        decoded=urllib.parse.unquote(opener.urls[0])
        self.assertIn("中文 UBJSON 编解码器",decoded)
        self.assertFalse(out["complete"])
        self.assertFalse(out["independently_complete"])
        self.assertEqual(out["acceptance_credit"],0)

    def test_descriptionless_repository_is_not_filtered_out(self):
        opener=RecordingOpener()
        out=g.search(self.action("REPOSITORY_METADATA"),opener=opener)
        self.assertEqual(out["candidate_count"],1,out)
        self.assertIsNone(out["candidates"][0]["description"])
        self.assertEqual(out["candidates"][0]["authority_status"],"UNVERIFIED")

    def test_code_content_does_not_depend_on_repo_description_or_stars(self):
        opener=RecordingOpener()
        out=g.search(self.action("CODE_CONTENT","dumpb UBJSON"),opener=opener)
        candidate=out["candidates"][0]
        self.assertEqual(candidate["repository"],"example/repo")
        self.assertEqual(candidate["path"],"src/codec.py")
        self.assertNotIn("stars",candidate)
        self.assertNotIn("description",candidate)

    def test_manifest_and_test_surfaces_use_code_search_qualifiers(self):
        for surface,needle in (("MANIFESTS","filename:"),("TESTS_EXAMPLES","path:")):
            opener=RecordingOpener()
            out=g.search(self.action(surface,"ubjson"),limit=2,opener=opener)
            self.assertGreaterEqual(out["candidate_count"],1,out)
            decoded="\n".join(urllib.parse.unquote(x) for x in opener.urls)
            self.assertIn(needle,decoded)

    def test_issue_and_history_surfaces_are_candidates_only(self):
        opener=RecordingOpener()
        issue=g.search(self.action("ISSUES_PRS"),opener=opener)
        history=g.search(self.action("COMMITS_RELEASES_BRANCHES_TAGS"),opener=opener)
        self.assertEqual(issue["candidates"][0]["repository"],"example/repo")
        self.assertEqual(history["candidates"][0]["repository"],"example/repo")
        self.assertIn("COMMIT_SEARCH_ONLY",history["coverage_detail"])
        self.assertFalse(history["complete"])

    def test_router_binds_all_github_surfaces_except_social(self):
        bound=set(router.default_providers())
        expected={
            "REPOSITORY_METADATA","CODE_CONTENT","SYMBOLS","MANIFESTS",
            "TESTS_EXAMPLES","ISSUES_PRS","COMMITS_RELEASES_BRANCHES_TAGS",
        }
        self.assertTrue(expected.issubset(bound),bound)
        self.assertNotIn("SOCIAL_TECHNICAL_DISCUSSION",bound)

    def test_backend_contract_never_self_awards_sufficiency(self):
        opener=RecordingOpener()
        out=g.search(self.action("CODE_CONTENT"),opener=opener)
        self.assertNotIn("verified_sufficient",out)
        self.assertEqual(out["sufficiency_status"],"UNVERIFIED")
        self.assertEqual(out["incremental_spend_usd"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
