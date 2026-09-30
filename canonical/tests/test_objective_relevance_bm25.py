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

    def test_task_c_wrong_property_and_wrong_alloy_cannot_win_on_token_count(self):
        objective=(
          "Determine whether the room-temperature thermal conductivity of annealed "
          "6061 aluminum is greater than that of annealed 304 stainless steel "
          "under comparable bulk-material conditions."
        )
        candidates=[
          {
            "title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
            "record_title":"Ignition Temperature of Bulk 6061 Aluminum, 302 Stainless Steel and 1018 Carbon Steel in Oxygen",
            "snippet":"6061 aluminum 302 stainless steel bulk temperature oxygen ignition",
          },
          {
            "title":"Thermal conductivity and electrical resistivity of a sample of AISI type 304 stainless steel",
            "record_title":"Thermal conductivity and electrical resistivity of a sample of AISI type 304 stainless steel",
            "snippet":"National Bureau of Standards thermal conductivity 304 stainless steel",
          },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],1,out)
        self.assertEqual(out["verification_method"],"DETERMINISTIC_BM25_PLUS_DECISION_ROLE_ADMISSION",out)
        self.assertEqual(out["role_admissible_candidate_count"],1,out)
        self.assertTrue(out["top_candidate_admission"]["verified"],out)
        wrong=next(x for x in out["ranked_candidates"] if x["original_index"]==0)
        self.assertFalse(wrong["decision_role_admission"]["verified"],wrong)
        self.assertFalse(wrong["decision_role_admission"]["property"]["verified"],wrong)

    def test_exact_numeric_operand_discriminator_is_mandatory(self):
        objective=(
          "Determine whether the thermal conductivity of alloy 6061 aluminum "
          "is greater than that of alloy 304 stainless steel."
        )
        out=self.m.rank(objective,[
          {
            "title":"Thermal conductivity of alloy 302 stainless steel",
            "snippet":"thermal conductivity stainless steel alloy 302",
          }
        ])
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertEqual(out["reason"],"NO_DECISION_ROLE_ADMISSIBLE_CANDIDATE",out)
        role=out["ranked_candidates"][0]["decision_role_admission"]
        self.assertFalse(role["right_operand"]["verified"],role)
        self.assertIn("304",role["right_operand"]["missing_mandatory_discriminators"],role)

    def test_cross_domain_property_plus_operand_filtering(self):
        objective="Determine whether France population growth is higher than Germany population growth."
        candidates=[
          {"title":"France GDP growth outlook","snippet":"France economic growth forecast"},
          {"title":"France population growth","snippet":"France population growth demographic estimate"},
          {"title":"Germany population growth","snippet":"Germany population growth demographic estimate"},
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertIn(out["top_candidate_original_index"],{1,2},out)
        wrong=next(x for x in out["ranked_candidates"] if x["original_index"]==0)
        self.assertFalse(wrong["decision_role_admission"]["verified"],wrong)
        self.assertFalse(wrong["decision_role_admission"]["property"]["verified"],wrong)

    def test_single_character_operand_discriminator_survives_role_gate(self):
        objective=(
          "Determine whether the orbital period of Planet Kepler A is greater "
          "than that of Planet Kepler B."
        )
        out=self.m.rank(objective,[
          {"title":"Orbital period of Planet Kepler B","snippet":"Planet Kepler B orbital period measurement"},
          {"title":"Orbital period of Planet Kepler C","snippet":"Planet Kepler C orbital period measurement"},
        ])
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],0,out)
        bad=next(x for x in out["ranked_candidates"] if x["original_index"]==1)
        self.assertFalse(bad["decision_role_admission"]["verified"],bad)
        self.assertIn("label:b",bad["decision_role_admission"]["right_operand"]["missing_mandatory_discriminators"],bad)

    def test_explicit_comparison_with_unresolvable_property_fails_closed(self):
        out=self.m.rank("Determine whether France is greater than Germany.",[
          {"title":"France and Germany comparison","snippet":"France Germany"}
        ])
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertEqual(out["reason"],"DECISION_ROLE_SPEC_UNRESOLVED",out)

    def test_non_relation_objective_preserves_existing_bm25_admission(self):
        out=self.m.rank("find official python csv module documentation",[
          {"title":"Python csv module","snippet":"CSV file reading writing documentation"},
          {"title":"Python weather","snippet":"forecast"},
        ])
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],0,out)
        self.assertEqual(out["verification_method"],"DETERMINISTIC_BM25",out)
        self.assertEqual(out["top_candidate_admission"]["method"],"FOCUSED_QUERY_TOKEN_COVERAGE_V1",out)

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
