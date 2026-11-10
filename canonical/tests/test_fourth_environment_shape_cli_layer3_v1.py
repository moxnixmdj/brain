"""Layer 3: a UI demonstration whose causal effect is a shell command.

    demonstrated   4 UI steps + one wc -l invocation
    elevated       1 step, layer=cli_exec, ALL UI steps pruned
    learned        argv ["wc","-l","?path0"]  --  the filename became a hole
    new goal       "count the lines in sales_q3.csv" -> {'?path0': 'sales_q3.csv'}
    executed       argv ["wc","-l","sales_q3.csv"]

TWO FACTS THAT MATTER, measured not assumed:

1. It runs under ADMITTED CONFINEMENT. The receipt says confined: true and
   live_workspace_untouched: true. A skill that can run arbitrary argv is a loaded gun; the
   carrier is what makes it a tool.

2. IT COSTS 95 ms AND THAT IS THE PRICE OF THE SAFETY.
       bare subprocess.run(["wc","-l","r.csv"])          2.0 ms
       execute_compiled_steps([...cli_exec...])        97-206 ms
   The layer is declared "Layer 3 (<50 ms)". The measured steady state is ~97 ms, so the
   declaration is optimistic by about 2x for a confined call. Recording the number instead of
   the promise.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402


def _env() -> pathlib.Path:
    env = pathlib.Path(tempfile.mkdtemp())
    (env / "report.csv").write_text("a,b\n1,2\n3,4\n5,6\n")
    return env


def test_a_cli_effect_elevates_and_prunes_the_ui():
    elev = TC.elevate_trace_to_fastest_layer({"steps": [
        {"layer": "screenshot"}, {"layer": "click", "x": 100, "y": 200},
        {"layer": "key", "text": "report.csv"}, {"layer": "click", "x": 300, "y": 260},
        {"layer": "cli_exec", "argv": ["wc", "-l", "report.csv"]}]})
    steps = elev["elevated_steps"]
    assert len(steps) == 1 and steps[0]["layer"] == "cli_exec"


def test_the_filename_becomes_a_hole_and_binds_from_a_new_goal():
    elev = TC.elevate_trace_to_fastest_layer(
        {"steps": [{"layer": "cli_exec", "argv": ["wc", "-l", "report.csv"]}]})
    sk = TC.anti_unify_workflow("count the lines in report.csv",
                                elev["elevated_steps"], {"exit": 0})
    assert "?path0" in json.dumps(sk["abstract_steps"])
    assert TC.bind_goal_parameters(sk, "count the lines in sales_q3.csv") == {
        "?path0": "sales_q3.csv"}


def test_it_executes_confined_and_reports_that_it_did():
    env = _env()
    elev = TC.elevate_trace_to_fastest_layer(
        {"steps": [{"layer": "cli_exec", "argv": ["wc", "-l", "report.csv"]}]})
    out = TC.execute_compiled_steps(elev["elevated_steps"], cwd=env)
    r = out["step_receipts"][0]
    assert r["exit"] == 0 and r["stdout"].strip().endswith("report.csv")
    assert r["confined"] is True and r["live_workspace_untouched"] is True


def test_the_declared_layer_budget_is_optimistic_and_that_is_recorded():
    """Layer 3 is documented as <50 ms. Measured ~97 ms for a confined call. A benchmark that
    quotes the declared budget instead of the measured one is quoting a wish."""
    doc = (ROOT / "canonical/governance/FOUR_ENVIRONMENT_SHAPES_MEASURED_20261109_V1.json")
    assert doc.exists()
    assert "97" in doc.read_text()
