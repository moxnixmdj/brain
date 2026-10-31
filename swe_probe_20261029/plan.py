import sys, json, pathlib
sys.path.insert(0,'.')
from canonical.runtime import swe_typed_plan_v1 as p
from canonical.runtime import capability_selection_retrieval_v1 as sel
D='/tmp/swe12'
root=pathlib.Path(D)
goals={
 "repair_full": f"Repair the python source {D}/repair_full/pkg/calc.py so that the unit test in {D}/repair_full/pkg/test_calc.py passes, and save the repair report to {D}/repair_full/a.json.",
 "fix_broken": f"the add function in {D}/fix_broken/pkg/calc.py is broken, fix it so its tests pass",
 "rename_param": f"Rename the parameter a to x in the python module {D}/rename_param/pkg/util.py and save the report to {D}/rename_param/r.json.",
 "find_callers": f"Find every caller of the function add in {D}/find_callers/pkg/util.py",
 "write_unit_test": f"Write a unit test for {D}/write_unit_test/pkg/util.py",
 "type_check": f"Type-check the file {D}/type_check/pkg/util.py",
 "lint": f"Lint the python file {D}/lint/pkg/util.py",
}
for k,g in goals.items():
    print(k, '|', json.dumps(p.plan_report(g, root))[:300])
