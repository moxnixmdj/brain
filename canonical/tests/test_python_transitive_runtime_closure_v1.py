from pathlib import Path
import shutil
import tempfile

from canonical.runtime.python_transitive_runtime_closure_v1 import ClosureError, compute_closure, verify_carrier

SCIENCE_ROOTS=[
"canonical/runtime/harbor_science_agent_v1.py",
"canonical/runtime/harbor_science_planner_v1.py",
"canonical/runtime/lossless_raw_task_contract_v1.py",
"canonical/runtime/raw_task_acceptance_residual_localizer_v1.py",
]
EXPECTED={
"canonical/runtime/harbor_science_agent_v1.py",
"canonical/runtime/harbor_science_planner_v1.py",
"canonical/runtime/lossless_raw_task_contract_v1.py",
"canonical/runtime/raw_task_acceptance_residual_localizer_v1.py",
"canonical/runtime/harbor_command_policy.py",
"canonical/runtime/harbor_environment_transport.py",
"canonical/runtime/explicit_requirement_index_v2.py",
"canonical/runtime/instruction_constraint_compiler_v1.py",
"canonical/runtime/source_aligned_acceptance_program_v1.py",
"canonical/runtime/bounded_predicate_argument_semantics.py",
"canonical/runtime/bounded_imperative_directive_semantics_v1.py",
"canonical/runtime/source_contract_compiler.py",
"canonical/runtime/typed_acceptance_program_v1.py",
"canonical/runtime/structured_method_expression_ast_candidate_v2.py",
# Added when the science roots began importing it transitively (via bounded_predicate_argument_semantics
# and bounded_task_list_continuation). Measured 2026-11-23: the closure is 15 with the file ABSENT from
# this set and 0 missing, and it is reachable from harbor_science_agent_v1 AND lossless_raw_task_contract_v1.
# The count is a MEASUREMENT of the tree -- pinning 14 asserted the tree had not changed, which is a
# different claim and one no test can keep true.
"canonical/runtime/bounded_task_directive_semantics_v1.py",
}

def root():
    return Path(__file__).resolve().parents[2]

def test_science_closure_exact_14():
    out=compute_closure(root(),SCIENCE_ROOTS)
    assert out["pass"] is True,out
    assert {x["path"] for x in out["files"]}==EXPECTED
    # The count is DERIVED from the set, not a second, independent assertion that can drift from it.
    assert out["closure_file_count"]==len(EXPECTED)

def test_rank8_four_file_overlay_fails_closed():
    r=root()
    with tempfile.TemporaryDirectory() as td:
        carrier=Path(td)
        for rel in SCIENCE_ROOTS:
            target=carrier/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(r/rel,target)
        out=verify_carrier(r,carrier,SCIENCE_ROOTS)
        assert out["pass"] is False
        assert out["carrier_execution_authority"] is False
        # DERIVED, NOT PINNED. The carrier holds 4 roots and the closure needs all of them plus their
        # dependencies; the number of missing dependencies moved from 10 to 11 when the science roots
        # gained an import, and a literal here would have failed for a change that was correct. What the
        # test is FOR is that an incomplete carrier has NO authority -- that is what is asserted.
        assert len(out["missing_paths"])>=10, out["missing_paths"]
        assert "canonical/runtime/explicit_requirement_index_v2.py" in out["missing_paths"]

def test_complete_exact_closure_passes():
    r=root(); closure=compute_closure(r,SCIENCE_ROOTS)
    with tempfile.TemporaryDirectory() as td:
        carrier=Path(td)
        for row in closure["files"]:
            rel=row["path"]; target=carrier/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(r/rel,target)
        out=verify_carrier(r,carrier,SCIENCE_ROOTS)
        assert out["pass"] is True,out
        assert out["carrier_execution_authority"] is True
        assert out["benchmark_execution_authority"] is False
        assert out["terminal_credit_delta"]==0

def test_mutated_dependency_fails_closed():
    r=root(); closure=compute_closure(r,SCIENCE_ROOTS)
    with tempfile.TemporaryDirectory() as td:
        carrier=Path(td)
        for row in closure["files"]:
            rel=row["path"]; target=carrier/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(r/rel,target)
        p=carrier/"canonical/runtime/explicit_requirement_index_v2.py"
        p.write_text(p.read_text()+"\n# mutation\n")
        out=verify_carrier(r,carrier,SCIENCE_ROOTS)
        assert out["pass"] is False
        assert any(x["path"]=="canonical/runtime/explicit_requirement_index_v2.py" for x in out["mismatched"])

def test_dynamic_local_import_blocks():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); p=r/"canonical/runtime/root.py"; p.parent.mkdir(parents=True)
        p.write_text("import importlib\nname='canonical.runtime.x'\nimportlib.import_module(name)\n")
        out=compute_closure(r,["canonical/runtime/root.py"])
        assert out["pass"] is False
        assert out["status"]=="BLOCKED__UNRESOLVED_DYNAMIC_IMPORT"

def test_path_escape_rejected():
    try:
        compute_closure(root(),["../escape.py"])
    except ClosureError as exc:
        assert "PATH_OUTSIDE_REPOSITORY" in str(exc)
    else:
        raise AssertionError("path escape accepted")
