import unittest
from canonical.runtime.prewave_anti_circularity_compiler import SCHEMA, classify

class Tests(unittest.TestCase):
    def test_terminal_result_moves_postwave(self):
        out=classify({"schema":SCHEMA,"predicates":[
            {"id":"RESULT","fact_class":"TERMINAL_RESULT","terminal_result_dependent":True,"prewave_required":False},
            {"id":"ORACLE","fact_class":"ORACLE","terminal_result_dependent":False,"prewave_required":True},
        ]})
        self.assertTrue(out["pass"])
        self.assertEqual(out["prewave_predicates"],["ORACLE"])
        self.assertEqual(out["postwave_predicates"],["RESULT"])

    def test_circular_precondition_rejected(self):
        out=classify({"schema":SCHEMA,"predicates":[
            {"id":"PARITY","fact_class":"TERMINAL_COMPARISON","terminal_result_dependent":True,"prewave_required":True}
        ]})
        self.assertFalse(out["pass"])
        self.assertIn("CIRCULAR_PREWAVE_REQUIREMENT:PARITY",out["errors"])

    def test_safety_cannot_be_demoted(self):
        out=classify({"schema":SCHEMA,"predicates":[
            {"id":"CLEAN","fact_class":"CONTAMINATION","terminal_result_dependent":False,"prewave_required":False}
        ]})
        self.assertFalse(out["pass"])
        self.assertIn("UNSAFE_PREWAVE_CLASS_DEMOTED:CLEAN",out["errors"])

if __name__=="__main__":
    unittest.main()
