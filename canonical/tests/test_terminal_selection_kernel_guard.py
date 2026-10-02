from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.terminal_selection_kernel_guard import evaluate,KERNEL,GLOBAL,FIELDS

class Tests(unittest.TestCase):
    def test_live(self):
        self.assertTrue(evaluate(Path("."))["pass"])
    def test_semantic_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=json.loads(Path(KERNEL).read_text())
            glob={f:src[f] for f in FIELDS}
            (root/KERNEL).parent.mkdir(parents=True,exist_ok=True)
            (root/KERNEL).write_text(json.dumps(src))
            glob["seed_policy"]=dict(glob["seed_policy"]);glob["seed_policy"]["case_replacement"]=True
            (root/GLOBAL).write_text(json.dumps(glob))
            self.assertFalse(evaluate(root)["pass"])

if __name__=="__main__":unittest.main()
