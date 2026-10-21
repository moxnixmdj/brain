"""The frontier guard froze a snapshot of the frontier and so rejected a newer one.

``capability_parallel_frontier_post_composition_v2._r2`` demanded that the
scheduler's primary cell be exactly ``FINANCE_SEMANTIC_ADEQUACY_TAIL`` with
exactly **one** internally-unsolved cell. That was a true statement about the
frontier on the day it was written. The governance file has since advanced to
V91, where the finance tail is closed and that count is **0** -- so the guard
rejected a strictly more advanced frontier, and with it the one-shot sky-impact
planner behind it, which could not be compiled at all.

Measured before this change: ``compile_sky_impact_plan()`` raised
``PostCompositionFrontierV2Error: R2_SCHEDULER``. After: it returns
``PASS__ONE_SHOT_8_STEP_MATHEMATICAL_AND_UNCERTAINTY_RESOLUTION_PLAN_VERIFIED``.

The guard was not loosened. It still fails closed when the scheduler's declared
count disagrees with the cells the file actually classifies -- the invariant
worth enforcing -- and it still fails closed on the boundary conditions. What it
no longer does is assert one historical cell name and one historical count.
"""

import copy
import json
import pathlib
import shutil
import tempfile
import unittest

REPO_ROOT=pathlib.Path(__file__).resolve().parents[2]

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))

from canonical.runtime import capability_parallel_frontier_post_composition_v2 as pc  # noqa: E402
from canonical.runtime.one_shot_sky_impact_planner_v1 import compile_sky_impact_plan  # noqa: E402

R2_REL=pc.R2
STATE="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"


def _frontier():
    """A real frontier dict, shaped the way the guards expect."""
    from canonical.runtime import capability_parallel_frontier_v2 as core
    return json.loads(json.dumps(core.load_current_frontier()))


class ThePlannerIsReachableAgain(unittest.TestCase):
    def test_the_one_shot_plan_compiles_and_passes(self):
        out=compile_sky_impact_plan(REPO_ROOT)
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"],
            "PASS__ONE_SHOT_8_STEP_MATHEMATICAL_AND_UNCERTAINTY_RESOLUTION_PLAN_VERIFIED",
        )
        self.assertEqual(len(out["steps"]),8)
        # The plan must stay honest: no terminal authority, no spend, no
        # external cognition.
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["summary"]["incremental_spend_usd"],0.0)
        self.assertEqual(out["summary"]["external_runtime_cognition_count"],0)

    def test_the_frontier_plan_itself_is_ready(self):
        out=pc.plan_current_post_composition_frontier()
        self.assertEqual(out.get("status"),"PARALLEL_FRONTIER_PLAN_READY")


class TheGuardStillFailsClosed(unittest.TestCase):
    """Negative controls. Deriving must not become permissive."""

    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads((REPO_ROOT/R2_REL).read_text(encoding="utf-8"))

    def _run_r2_with(self, mutate):
        tmp=tempfile.mkdtemp(prefix="r2_guard_")
        try:
            root=pathlib.Path(tmp)
            target=root/R2_REL
            target.parent.mkdir(parents=True,exist_ok=True)
            doc=copy.deepcopy(self.doc)
            mutate(doc)
            target.write_text(json.dumps(doc,indent=2)+"\n",encoding="utf-8")
            # The rest of the governance set is read by sibling guards, not by
            # _r2, so only this one file needs to exist.
            return pc._r2(_frontier(),root)
        finally:
            shutil.rmtree(tmp,ignore_errors=True)

    def test_a_declared_count_that_disagrees_with_the_cells_still_raises(self):
        # The core invariant: the scheduler's declared count must equal the
        # number of cells the file actually classifies as internally unsolved.
        def mutate(doc):
            sr=doc["scheduler_result"]
            actual=sum(
                1 for v in (doc.get("current_cell_classifications") or {}).values()
                if isinstance(v,dict) and v.get("state")==STATE
            )
            sr["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"]=actual+1
        with self.assertRaises(pc.PostCompositionFrontierV2Error) as ctx:
            self._run_r2_with(mutate)
        self.assertEqual(str(ctx.exception),"R2_SCHEDULER")

    def test_a_missing_primary_cell_still_raises(self):
        def mutate(doc):
            doc["scheduler_result"]["primary_cell"]=""
        with self.assertRaises(pc.PostCompositionFrontierV2Error) as ctx:
            self._run_r2_with(mutate)
        self.assertEqual(str(ctx.exception),"R2_SCHEDULER")

    def test_a_non_integer_count_still_raises(self):
        def mutate(doc):
            doc["scheduler_result"][
                "primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"
            ]="1"
        with self.assertRaises(pc.PostCompositionFrontierV2Error) as ctx:
            self._run_r2_with(mutate)
        self.assertEqual(str(ctx.exception),"R2_SCHEDULER")

    def test_a_count_above_zero_with_a_mismatched_cell_still_raises(self):
        # If anything is internally unsolved, the named primary cell must be the
        # one carrying that state -- otherwise the scheduler is inconsistent.
        # The declared count is kept equal to the real one so the scheduler
        # check passes and the cell-level check is the one that fires.
        def mutate(doc):
            cells=doc["current_cell_classifications"]
            cells["REAL_UNSOLVED_CELL"]={
                "state":STATE,
                "information_theoretic_externality_proved":False,
            }
            cells["SOME_OTHER_CELL"]={
                "state":"SOMETHING_ELSE_ENTIRELY",
                "information_theoretic_externality_proved":False,
            }
            actual=sum(
                1 for v in cells.values()
                if isinstance(v,dict) and v.get("state")==STATE
            )
            doc["scheduler_result"]["primary_cell"]="SOME_OTHER_CELL"
            doc["scheduler_result"][
                "primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"
            ]=actual
        with self.assertRaises(pc.PostCompositionFrontierV2Error) as ctx:
            self._run_r2_with(mutate)
        self.assertEqual(str(ctx.exception),"R2_CELL")

    def test_the_boundary_conditions_are_untouched(self):
        def mutate(doc):
            doc["general_mechanism_missing"]=True
        with self.assertRaises(pc.PostCompositionFrontierV2Error) as ctx:
            self._run_r2_with(mutate)
        self.assertEqual(str(ctx.exception),"R2_BOUNDARY")


class TheLiveFrontierIsSelfConsistent(unittest.TestCase):
    def test_the_declared_count_equals_the_cells_actually_classified(self):
        doc=json.loads((REPO_ROOT/R2_REL).read_text(encoding="utf-8"))
        sr=doc["scheduler_result"]
        cells=doc.get("current_cell_classifications") or {}
        actual=sum(
            1 for v in cells.values()
            if isinstance(v,dict) and v.get("state")==STATE
        )
        self.assertEqual(
            sr["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            actual,
        )


if __name__=="__main__":
    unittest.main()
