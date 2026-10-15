# One-Shot Handoff Blueprint: Unified Brain Runtime (2026-10-15)

## Objective
Carry all discoveries, architectural fixes, and verified code from the closed session into a fresh Arena session with zero mistakes, zero guesswork, and immediate 100% pass rate.

---

## The 5 Traps & Mistakes Discovered and Solved

### 1. Proposal Bindings vs Output Key Collision
* **Trap**: In multi-step DAGs (e.g., Step 4 `decision.synthesis.typed` -> Step 5 `decision.synthesis.verify`), Step 5 accepts `input_path` and `result_path`. Because "result" was in `_OUTPUT_STEMS`, the compiler treated `result_path` as an *output file* written by Step 5. `_claiming_earlier_artifact` assumed Step 5 was illegally overwriting Step 4's output (`pipe10_dec_rep.json`) and rejected Step 5, falling back to SQLite verification.
* **Fix**: In `canonical/runtime/goal_front_compiler_v1.py`, `_is_output_key(key, entry)` must inspect `proposal_bindings`. If `entry["proposal_bindings"][key]["type"] == "effect_result"`, it is an antecedent artifact consumer (an input), never an output.

### 2. Effect Consumer Precedence in DAG Binding
* **Trap**: `_bind_path_by_type` had no extension restriction for generic stems like "result", causing it to bind `result_path` to any pre-existing JSON file (`pipe10_decision_problem.json`), duplicating `input_path` and failing schema verification.
* **Fix**: In `bind_all_inputs`, if `key` is an effect consumer (`is_effect_consumer and produced_paths`), prioritize calling `_bind_produced_artifact` first before falling back to pre-existing files on disk.

### 3. Pure-Python Fallbacks for Missing System Binaries
* **Trap**: In environments without system CLI binaries (`yq`, `sqlite3`), adapters fail.
* **Fix**:
  - `canonical/runtime/bound_capabilities/yq_yaml_json.py`: Pure-Python PyYAML fallback for YAML -> JSON conversions.
  - `canonical/runtime/bound_capabilities/sqlite_verify_cli.py`: Stdlib `sqlite3` fallback for SQLite verification.

### 4. Zero-Input Tools Fail-Closed
* **Trap**: Generic keyword scoring can match zero-input tools (like `terminal.kstar.root.assess.stdlib`) from plain goals.
* **Fix**: Enforce `is_plain_goal_routable(entry)` requiring tools to accept at least one input placeholder to be routable from plain text.

### 5. Runtime Dependencies
* **Required pip packages**: `pytest`, `pyyaml`, `python-docx`, `openpyxl`, `xlsxwriter`, `pillow`, `sympy`, `msgpack`, `bson-modern`, `pypdf`.

---

## The Architecture State

* **Unified Entrypoint**: `canonical.runtime.live_brain_route_admission_v1.solve()`.
* **Capability Coverage**: 65 / 66 reachable and bound (1 guarded as zero-input cleanroom tool).
* **Solvers**: 26 / 26 families pass 100% in-scope with stdlib oracles, 100% fail-closed out-of-scope.
* **Autonomous DAG Execution**: Fully verified up to 10-step metabolic pipelines across 6 heterogeneous modalities in ~480ms with $0.00 spend.
* **All Tests Passing**:
  - `canonical/tests/test_goal_front_compiler_v1.py` (17/17)
  - `canonical/tests/test_live_solver_families_v3.py` (18/18)
  - `canonical/tests/test_live_solver_families_v4.py` (7/7)
