"""End-to-end bounded numeric science pipeline: compile, solve, optionally materialize."""
from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import scientific_numeric_task_compiler_v1 as compiler
from canonical.runtime import general_scientific_capability_controller_v1 as controller
from canonical.runtime import scientific_artifact_contract_v1 as artifacts

SCHEMA="PROJECT_BRAIN_SCIENTIFIC_NUMERIC_PIPELINE_V1"

def solve_numeric_task(instruction:str,rows:Any)->dict[str,Any]:
 compiled=compiler.compile_numeric_task(instruction,rows)
 if compiled.get("status")!="COMPILED":return compiled
 solved=controller.solve(compiled["task_problem"])
 return {"schema":SCHEMA,
         "status":"PASS__NUMERIC_TASK_COMPILED_AND_VERIFIED" if solved.get("verified") is True else "SCIENTIFIC_RESULT_NOT_VERIFIED",
         "compiled":compiled,"solution":solved,"verified":solved.get("verified") is True,
         "terminal_authority":False}

def solve_and_materialize(instruction:str,rows:Any,specs:Sequence[Mapping[str,Any]],output_root:str|Path)->dict[str,Any]:
 solved=solve_numeric_task(instruction,rows)
 if solved.get("verified") is not True:return solved
 made=artifacts.materialize_artifacts(solved["solution"],specs,output_root)
 ok=str(made.get("status") or "").startswith("PASS__")
 return {"schema":SCHEMA,
         "status":"PASS__NUMERIC_TASK_SOLVED_AND_ARTIFACTS_VERIFIED" if ok else "ARTIFACT_MATERIALIZATION_FAILED",
         "compiled":solved["compiled"],"solution":solved["solution"],"artifacts":made,
         "verified":ok,"terminal_authority":False}
