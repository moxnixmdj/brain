from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from canonical.runtime import r2_v45_residual_top_authority_verify_v1 as v


class R2V45ResidualTopAuthorityVerifyV1Tests(unittest.TestCase):
    def test_current_branch_authority_is_coherent(self):
        out=v.verify()
        self.assertTrue(out["verified"],out)
        self.assertEqual(
            out["status"],
            "PASS__R2_V45_RESIDUAL_TOP_AUTHORITY_COHERENT",
        )
        self.assertEqual(out["terminal_credit_delta"],0)
        self.assertFalse(out["terminal_authority"])

    def test_terminal_route_count_drift_is_rejected(self):
        source_root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in v.EXPECTED.values():
                src=source_root/rel
                dst=root/rel
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst)

            terminal_path=root/v.EXPECTED["terminal"]
            terminal=json.loads(terminal_path.read_text(encoding="utf-8"))
            terminal["live_truth"]["r2_direct_adequacy_route_count"]=30
            terminal_path.write_text(
                json.dumps(terminal,indent=2,sort_keys=True)+"\n",
                encoding="utf-8",
            )

            out=v.verify(repo_root=root)
            self.assertFalse(out["verified"])
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertTrue(
                any(x.startswith("TERMINAL_ROUTE_COUNT:") for x in out["errors"]),
                out,
            )


if __name__=="__main__":
    unittest.main()
