import unittest
from canonical.runtime.harbor_adapter_transport_preflight import run_preflight

class Tests(unittest.TestCase):
    def test_transport_preflight(self):
        out=run_preflight()
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["terminal_task_content_consumed"])
        self.assertFalse(out["controller_zero_cost_certified"])

if __name__=="__main__":
    unittest.main()
