from pathlib import Path

R=Path(__file__).resolve().parents[2]
startup=(R/"sitecustomize.py").read_text(encoding="utf-8")
runtime=(R/"canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")

assert "ASTRA_DISABLE_MODEL_PLANNER" in startup
assert "='1'" in startup or '="1"' in startup or '= "1"' in startup

start=runtime.index("def _planner_post(prompt, timeout_s=20):")
window=runtime[start:start+700]
assert "ASTRA_DISABLE_MODEL_PLANNER" in window
assert "MODEL_PLANNER_DISABLED_BY_POLICY" in window

print("EXTERNAL_COGNITION_RUNTIME_LOCK_PASS")
