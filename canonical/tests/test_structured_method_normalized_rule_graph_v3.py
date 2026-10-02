import copy, unittest
from canonical.runtime.structured_method_normalized_rule_graph_v3 import compile_graph

def base():
    return {
      "behavior_id":"STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
      "task":{
        "inputs":[
          {"id":"a","type":"number","dimension":"USD"},
          {"id":"b","type":"number","dimension":"USD"},
          {"id":"flag","type":"boolean","dimension":"dimensionless"}
        ],
        "requirements":[
          {"id":"R_SCHEMA","source_kind":"schema","status":"applicable"},
          {"id":"R_FORMULA","source_kind":"formula","status":"applicable"},
          {"id":"R_EX","source_kind":"constraint","status":"excluded","exclusion_reason":"NOT_APPLICABLE_UNDER_NORMALIZED_RULE_SELECTION"}
        ],
        "normalized_rules":[
          {
            "id":"RULE_X","operator":"arbitrary_domain_operator_alpha",
            "inputs":["a","b"],
            "input_contracts":[
              {"type":"number","dimension":"USD"},
              {"type":"number","dimension":"USD"}
            ],
            "output":"x","type":"number","dimension":"USD",
            "consumes_requirements":["R_SCHEMA","R_FORMULA"],
            "invariants":[{"kind":"nonnegative","statement":"x >= 0"}]
          },
          {
            "id":"RULE_Y","operator":"totally_different_operator_beta",
            "inputs":["x","flag"],
            "input_contracts":[
              {"type":"number","dimension":"USD"},
              {"type":"boolean","dimension":"dimensionless"}
            ],
            "output":"y","type":"string","dimension":"dimensionless",
            "consumes_requirements":[],
            "invariants":[]
          }
        ],
        "required_outputs":["y"]
      }
    }

class Tests(unittest.TestCase):
    def test_arbitrary_operator_identity_is_not_a_scope_limit(self):
        o=compile_graph(base())
        self.assertEqual(o["status"],"COMPILED",o)
        self.assertEqual([r["operator"] for r in o["rules"]],["arbitrary_domain_operator_alpha","totally_different_operator_beta"])
        self.assertEqual(o["operator_semantics_authority"],"UPSTREAM_NORMALIZED_RULE_CONTRACT__NOT_INFERRED_HERE")

    def test_requirement_lineage_and_exclusion_complete(self):
        o=compile_graph(base())
        self.assertEqual({x["requirement_id"] for x in o["requirement_lineage"]},{"R_SCHEMA","R_FORMULA"})
        self.assertEqual(o["justified_exclusions"][0]["requirement_id"],"R_EX")
        self.assertEqual(len(o["acceptance_checks"]),2)

    def test_missing_consumer_fails_closed(self):
        x=base(); x["task"]["normalized_rules"][0]["consumes_requirements"]=["R_SCHEMA"]
        o=compile_graph(x)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER",o["reason"])

    def test_excluded_requirement_cannot_be_consumed(self):
        x=base(); x["task"]["normalized_rules"][0]["consumes_requirements"].append("R_EX")
        o=compile_graph(x)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("RULE_CONSUMES_UNKNOWN_OR_EXCLUDED_REQUIREMENT",o["reason"])

    def test_type_dimension_mismatch_fails_closed(self):
        x=base(); x["task"]["normalized_rules"][0]["input_contracts"][0]["dimension"]="EUR"
        o=compile_graph(x)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("INPUT_TYPE_DIMENSION_MISMATCH",o["reason"])

    def test_cycle_fails_closed(self):
        x=base()
        x["task"]["normalized_rules"]=[
          {"id":"A","operator":"op","inputs":["z"],"input_contracts":[{"type":"number","dimension":"USD"}],"output":"x","type":"number","dimension":"USD","consumes_requirements":["R_SCHEMA"],"invariants":[]},
          {"id":"B","operator":"op2","inputs":["x"],"input_contracts":[{"type":"number","dimension":"USD"}],"output":"z","type":"number","dimension":"USD","consumes_requirements":["R_FORMULA"],"invariants":[]}
        ]
        x["task"]["required_outputs"]=["z"]
        o=compile_graph(x)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("UNRESOLVED_DEPENDENCY_OR_CYCLE",o["reason"])

    def test_untraced_output_fails_closed(self):
        x=base(); x["task"]["required_outputs"]=["ghost"]
        self.assertEqual(compile_graph(x)["status"],"FAIL_CLOSED")

    def test_rule_order_does_not_change_graph(self):
        a=compile_graph(base())
        x=base(); x["task"]["normalized_rules"].reverse()
        b=compile_graph(x)
        self.assertEqual(a,b)

    def test_duplicate_output_fails_closed(self):
        x=base(); x["task"]["normalized_rules"][1]["output"]="x"
        self.assertEqual(compile_graph(x)["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
