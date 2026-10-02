from __future__ import annotations

import inspect
import json
import unittest

from canonical.runtime import cad_orthographic_information_safe_candidate as candidate
from canonical.runtime import cad_orthographic_information_safe_proof as proof
from canonical.runtime.orthographic_visual_hull import reconstruct_visual_hull


class CadOrthographicInformationSafeTests(unittest.TestCase):
    def test_information_boundary(self):
        case=proof.generate_case(2026,0)
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        text=json.dumps(public).lower()
        for forbidden in ("principal_inertia","convex_hull_volume","euler_number","source_voxels"):
            self.assertNotIn(forbidden,text)
        src=inspect.getsource(candidate)
        self.assertNotIn("cad_orthographic_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_identifiable_and_ambiguous_population(self):
        out=proof.run_batch(2026,50,candidate.solve)
        self.assertTrue(out["all_pass"],out)

    def test_ambiguous_block_returns_constructive_alternative(self):
        case=proof.generate_case(77,4)
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"NONIDENTIFIABLE",out)
        verdict=proof.score_case(case,out)
        self.assertTrue(verdict["pass"],(out,verdict))
        self.assertNotEqual(
            {tuple(x) for x in out["alternative_voxels"]},
            {tuple(x) for x in case["_oracle"]["source_voxels"]},
        )

    def test_bounding_box_shortcut_fails_nonrectangular_slab(self):
        case=proof.generate_case(91,0)
        task=case["task"]
        x_cells=len(task["top"][0]);y_cells=len(task["top"]);z_cells=len(task["front"])
        bad={
            "status":"SOLID",
            "voxels":[[x,y,z] for z in range(z_cells) for y in range(y_cells) for x in range(x_cells)],
            "cell_size":task["cell_size"],
        }
        verdict=proof.score_case(case,bad)
        self.assertFalse(verdict["pass"],verdict)

    def test_forced_ambiguity_fails_identifiable_case(self):
        case=proof.generate_case(92,1)
        bad={
            "status":"NONIDENTIFIABLE",
            "witness_removed_voxel":[0,0,0],
            "alternative_voxels":[],
        }
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_visual_hull_single_answer_fails_ambiguous_case(self):
        case=proof.generate_case(93,4)
        task=case["task"]
        grid=reconstruct_visual_hull(task["top"],task["front"],task["right"])
        voxels=[]
        for z,slab in enumerate(grid):
            for y,row in enumerate(slab):
                for x,value in enumerate(row):
                    if value:
                        voxels.append([x,y,z])
        bad={"status":"SOLID","voxels":voxels,"cell_size":task["cell_size"]}
        self.assertFalse(proof.score_case(case,bad)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
