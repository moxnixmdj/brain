import unittest
from canonical.runtime import h100_three_axis_persistent_accounting_v1 as a

class H100ThreeAxisAccountingTests(unittest.TestCase):
    def test_weights_and_lossless_source_recode_stay_fit_state(self):
        w=a.Artifact("weights",4096,True,machine_fit_or_selected=True)
        s=a.recoded_fit_artifact("weights_as_source",4096)
        self.assertEqual(a.classify(w)["m_fit_bytes"],4096)
        self.assertEqual(a.classify(s)["m_fit_bytes"],4096)

    def test_engineered_algorithm_is_dev_not_fit(self):
        x=a.Artifact("solver.py",12000,True,engineered_after_capability_evidence=True)
        row=a.classify(x)
        self.assertEqual(row["m_fit_bytes"],0)
        self.assertEqual(row["m_dev_bytes"],12000)
        self.assertEqual(row["m_cap_bytes"],12000)

    def test_preexposure_generic_algorithm_is_capability_only(self):
        x=a.Artifact("generic_search.py",9000,True)
        row=a.classify(x)
        self.assertEqual(row["m_fit_bytes"],0)
        self.assertEqual(row["m_dev_bytes"],0)
        self.assertEqual(row["m_cap_bytes"],9000)

    def test_runtime_task_state_is_not_capability_state(self):
        x=a.Artifact("event_log",50000,False,runtime_task_state_only=True)
        row=a.classify(x)
        self.assertEqual(row["m_fit_bytes"],0)
        self.assertEqual(row["m_dev_bytes"],0)
        self.assertEqual(row["m_cap_bytes"],0)
        self.assertEqual(row["excluded_runtime_task_state_bytes"],50000)

    def test_raw_external_knowledge_is_separate(self):
        x=a.Artifact("dictionary",1000000,False,raw_external_knowledge_only=True)
        row=a.classify(x)
        self.assertEqual(row["m_cap_bytes"],0)
        self.assertEqual(row["excluded_raw_external_knowledge_bytes"],1000000)

    def test_compiled_search_selection_is_fit_state(self):
        x=a.Artifact("compiled_opcode",1,True,machine_fit_or_selected=True)
        row=a.classify(x)
        self.assertEqual(row["m_fit_bytes"],1)
        self.assertEqual(row["m_cap_bytes"],1)

    def test_ledger_keeps_axes_separate(self):
        out=a.ledger([
            a.Artifact("fit",2,True,machine_fit_or_selected=True),
            a.Artifact("dev",3,True,engineered_after_capability_evidence=True),
            a.Artifact("base",5,True),
            a.Artifact("task",7,False,runtime_task_state_only=True),
            a.Artifact("knowledge",11,False,raw_external_knowledge_only=True),
        ])
        self.assertEqual(out["m_fit_bytes"],2)
        self.assertEqual(out["m_dev_bytes"],3)
        self.assertEqual(out["m_cap_bytes"],10)
        self.assertEqual(out["excluded_runtime_task_state_bytes"],7)
        self.assertEqual(out["excluded_raw_external_knowledge_bytes"],11)
        self.assertFalse(out["claims"]["zero_fit_state"])

if __name__=="__main__":
    unittest.main(verbosity=2)
