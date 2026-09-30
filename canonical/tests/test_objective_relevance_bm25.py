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

    def test_comparative_admission_rejects_wrong_property_or_operand(self):
        objective=(
          "Determine whether the room-temperature thermal conductivity of annealed Alloy 6061 "
          "is greater than that of annealed Steel 304."
        )
        candidates=[
          {
            "title":"Thermal ignition temperature of annealed Alloy 6061 and Steel 302",
            "snippet":"room-temperature alloy 6061 annealed stainless steel ignition temperature measurements",
          },
          {
            "title":"Thermal conductivity of annealed Alloy 6061 and Steel 304",
            "snippet":"room-temperature conductivity measurements for annealed alloy 6061 and steel 304",
          },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertIsNotNone(out["decision_role_spec"],out)
        rows={x["original_index"]:x for x in out["ranked_candidates"]}
        self.assertFalse(rows[0]["decision_role_admission"]["verified"],rows[0])
        self.assertTrue(rows[1]["decision_role_admission"]["verified"],rows[1])
        self.assertEqual(out["top_candidate_original_index"],1,out)
        self.assertTrue(out["top_candidate_admission"]["verified"],out)

    def test_comparative_admission_requires_both_distinct_entities_cross_domain(self):
        objective="Determine whether France population growth is greater than Germany population growth."
        candidates=[
          {
            "title":"France and Spain population growth comparison",
            "snippet":"population growth France Spain annual demographic rates",
          },
          {
            "title":"France and Germany population growth comparison",
            "snippet":"population growth France Germany annual demographic rates",
          },
        ]
        out=self.m.rank(objective,candidates)
        rows={x["original_index"]:x for x in out["ranked_candidates"]}
        self.assertFalse(rows[0]["decision_role_admission"]["verified"],rows[0])
        self.assertTrue(rows[1]["decision_role_admission"]["verified"],rows[1])
        self.assertEqual(out["top_candidate_original_index"],1,out)

    def test_noncomparison_objective_preserves_legacy_coverage_contract(self):
        out=self.m.rank(
          "find official python csv module documentation",
          [
            {"title":"Python csv module","snippet":"CSV reading writing documentation"},
            {"title":"Weather forecast","snippet":"rain"},
          ],
        )
        self.assertIsNone(out["decision_role_spec"],out)
        self.assertFalse(out["top_candidate_admission"]["decision_role_coverage"]["applicable"])
        self.assertTrue(out["top_candidate_admission"]["verified"])

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

if __name__=="__main__": unittest.main(verbosity=2)
