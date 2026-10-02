from __future__ import annotations
import copy, inspect, random, unittest

from canonical.runtime.structured_method_normalized_rule_graph_v3 import compile_graph
from canonical.runtime.structured_method_normalized_rule_oracle_v3 import score

def make(seed:int,n:int=8):
    r=random.Random(seed)
    inputs=[
      {"id":"x0","type":"number","dimension":"USD"},
      {"id":"flag","type":"boolean","dimension":"dimensionless"},
    ]
    reqs=[
      {"id":"R_SCHEMA","source_kind":"schema","status":"applicable"},
      {"id":"R_FORMULA","source_kind":"formula","status":"applicable"},
      {"id":"R_UNUSED","source_kind":"constraint","status":"excluded","exclusion_reason":"NORMALIZED_NOT_APPLICABLE"},
    ]
    rules=[]
    prior="x0"
    for i in range(n):
        out=f"x{i+1}"
        rules.append({
          "id":f"RULE_{i}",
          "operator":f"domain_specific_operator_{seed}_{r.randrange(10**9)}",
          "inputs":[prior],
          "input_contracts":[{"type":"number","dimension":"USD"}],
          "output":out,
          "type":"number",
          "dimension":"USD",
          "consumes_requirements":(["R_SCHEMA","R_FORMULA"] if n==1 and i==0 else (["R_SCHEMA"] if i==0 else (["R_FORMULA"] if i==1 else []))),
          "invariants":[{"kind":"domain_invariant","statement":f"I_{seed}_{i}({out})"}],
        })
        prior=out
    return {
      "behavior_id":"STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
      "task":{"inputs":inputs,"requirements":reqs,"normalized_rules":rules,"required_outputs":[prior]},
    }

class Tests(unittest.TestCase):
    def test_oracle_is_independent(self):
        import canonical.runtime.structured_method_normalized_rule_oracle_v3 as oracle
        src=inspect.getsource(oracle)
        self.assertNotIn("structured_method_normalized_rule_graph_v3",src)

    def test_arbitrary_operator_identity_grid(self):
        for seed in range(100):
            public=make(seed,1+(seed%13))
            out=compile_graph(public)
            verdict=score(public,out)
            self.assertTrue(verdict["pass"],(seed,verdict,out))

    def test_edge_deletion_is_rejected(self):
        public=make(1); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["edges"]=bad["edges"][1:]
        self.assertFalse(score(public,bad)["pass"])

    def test_edge_rewire_is_rejected(self):
        public=make(2); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["edges"][0]["source"]="flag"
        self.assertFalse(score(public,bad)["pass"])

    def test_type_dimension_mutation_is_rejected(self):
        public=make(3); out=compile_graph(public); bad=copy.deepcopy(out)
        next(x for x in bad["nodes"] if x["id"]=="x1")["dimension"]="EUR"
        self.assertFalse(score(public,bad)["pass"])

    def test_requirement_lineage_mutation_is_rejected(self):
        public=make(4); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["requirement_lineage"][0]["consumer_rule_ids"]=[]
        self.assertFalse(score(public,bad)["pass"])

    def test_exclusion_mutation_is_rejected(self):
        public=make(5); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["justified_exclusions"]=[]
        self.assertFalse(score(public,bad)["pass"])

    def test_required_output_mutation_is_rejected(self):
        public=make(6); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["required_outputs"]=["x1"]
        self.assertFalse(score(public,bad)["pass"])

    def test_invariant_declaration_mutation_is_rejected(self):
        public=make(7); out=compile_graph(public); bad=copy.deepcopy(out)
        bad["rules"][0]["invariants"]=[]
        self.assertFalse(score(public,bad)["pass"])

    def test_unknown_operator_is_not_interpreted_or_rejected(self):
        public=make(8)
        public["task"]["normalized_rules"][0]["operator"]="opaque::future_method::Ω::v999"
        out=compile_graph(public)
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertTrue(score(public,out)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
