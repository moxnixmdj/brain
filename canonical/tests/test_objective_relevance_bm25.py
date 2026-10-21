#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
def load():
    s=importlib.util.spec_from_file_location("objective_relevance_bm25",P)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

class ObjectiveRelevanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def test_relevant_candidate_beats_search_rank(self):
        c=[
          {"title":"Generic database news","snippet":"release notes and community announcements","rank":0},
          {"title":"SQLite Online Backup API","snippet":"online backup source database modified concurrently destination consistent backup","rank":5},
          {"title":"Cooking with databases","snippet":"recipes and storage","rank":1},
        ]
        out=self.m.rank("Can SQLite online backup remain consistent while the source database is modified concurrently?",c)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],1,out)
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertEqual(out["semantic_entailment_status"],"UNVERIFIED")
        self.assertEqual(out["model_dependency_count"],0)

    def test_cross_domain_climate(self):
        c=[
          {"title":"Mauna Loa CO2 trends","snippet":"monthly atmospheric carbon dioxide observations growth rate"},
          {"title":"Volcano hiking guide","snippet":"trails lodging summit"},
          {"title":"Ocean salinity data","snippet":"sea surface salinity observations"},
        ]
        out=self.m.rank("Compare atmospheric CO2 growth rates at Mauna Loa across two decades",c)
        self.assertEqual(out["top_candidate_original_index"],0,out)

    def test_no_overlap_fails_closed(self):
        out=self.m.rank("quantum entanglement photon Bell inequality",[
          {"title":"banana bread recipe","snippet":"flour sugar butter"},
          {"title":"football standings","snippet":"league match points"},
        ])
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertFalse(out.get("output_verified",False))

    def test_stopword_only_objective_fails_closed(self):
        out=self.m.rank("what is the and whether", [{"title":"anything"}])
        self.assertEqual(out["reason"],"NO_DISCRIMINATIVE_OBJECTIVE_TOKENS")

    def test_deterministic_tie_uses_original_order(self):
        c=[{"title":"alpha beta"},{"title":"alpha beta"}]
        out=self.m.rank("alpha",c)
        self.assertEqual([x["original_index"] for x in out["ranked_candidates"]],[0,1])

    def test_title_weight_can_discriminate(self):
        c=[
          {"title":"sqlite backup consistency","snippet":"miscellaneous words"},
          {"title":"sqlite","snippet":"backup mentioned once"},
        ]
        out=self.m.rank("sqlite backup consistency",c)
        self.assertEqual(out["top_candidate_original_index"],0,out)

    def test_run_writes_narrow_claim(self):
        inp=ROOT/"canonical/astra_runtime/tmp/relevance_input.json"
        outp=ROOT/"canonical/astra_runtime/tmp/relevance_output.json"
        inp.parent.mkdir(parents=True,exist_ok=True)
        inp.write_text(json.dumps({
          "objective":"find official python csv module documentation",
          "candidates":[
            {"title":"Python csv module","snippet":"CSV file reading writing documentation"},
            {"title":"Python weather","snippet":"forecast"},
          ]
        }),encoding="utf-8")
        out=self.m.run({"input_path":str(inp.relative_to(ROOT)),"output_path":str(outp.relative_to(ROOT))},ROOT)
        self.assertTrue(out["output_verified"],out)
        self.assertEqual(out["relevance_claim_scope"],"LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY")
        self.assertEqual(out["primary_source_status"],"UNVERIFIED")
        self.assertTrue(outp.is_file())

class InputTypeGuardTests(unittest.TestCase):
    """A slot named input_path states no type, so anything can arrive.

    Measured: the word "source" in source.objective_relevance.rank.bm25 made
    kind_keys_for announce python.source, world binding handed this adapter a
    .py file for input_path, and json.loads died with a bare JSONDecodeError
    that surfaced as an unexplained FAIL__LIVE_CONTROLLER_EXECUTION. The
    binding defect is recorded separately; what is pinned here is that the
    adapter says what is wrong instead of leaking a decoder exception.
    """

    @classmethod
    def setUpClass(cls): cls.m = load()

    def _run_on(self, name, body):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / name).write_text(body, encoding="utf-8")
            return self.m.run(
                {"input_path": name, "output_path": "out.json",
                 "objective": "sqlite backup consistency"},
                root,
            )

    def test_python_source_is_reported_not_parsed(self):
        with self.assertRaises(ValueError) as ctx:
            self._run_on("tool.py", "def f():\n    return 1\n")
        self.assertIn("RELEVANCE_INPUT_NOT_JSON", str(ctx.exception.args[0]))

    def test_empty_file_is_reported_not_parsed(self):
        with self.assertRaises(ValueError) as ctx:
            self._run_on("empty.json", "")
        self.assertIn("RELEVANCE_INPUT_NOT_JSON", str(ctx.exception.args[0]))

    def test_json_that_is_not_an_object_is_reported(self):
        with self.assertRaises(ValueError) as ctx:
            self._run_on("list.json", "[1, 2, 3]")
        self.assertIn("RELEVANCE_INPUT_NOT_AN_OBJECT", str(ctx.exception.args[0]))

    def test_a_real_object_still_ranks(self):
        out = self._run_on("ok.json", json.dumps({
            "objective": "sqlite backup consistency",
            "candidates": [{"title": "SQLite backup", "snippet": "sqlite backup consistency", "rank": 0}],
        }))
        self.assertEqual(out["status"], "LEXICAL_RELEVANCE_RANKED", out)


if __name__=="__main__": unittest.main(verbosity=2)
