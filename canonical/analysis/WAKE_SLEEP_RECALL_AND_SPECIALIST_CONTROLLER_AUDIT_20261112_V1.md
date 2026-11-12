# Wake/Sleep Recall Latency & Structured Specialist Controller Audit (2026-11-12)

## 1. Falsification of the Unverified Claim in `YOU_WERE_RIGHT_ALL_ALONG.md` / `THE_SYSTEM_ALREADY_WORKS.md`

`YOU_WERE_RIGHT_ALL_ALONG.md` and `THE_SYSTEM_ALREADY_WORKS.md` claimed that calling:

```python
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
res = solve_or_learn("Add two numbers in Python", learn=True)
```

learns a Python addition skill in Tier 2 (`tier2_python_whitebox_introspection`) and recalls it in `< 5 ms` in Tier 0 (`tier0_compiled_skill_recall`).

Executing that call against the repository returns:

- `pass`: `False`
- `status`: `"FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"`
- `failure_class`: `"COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"`
- `tier_used`: `"tier2_unconfined_documentation_execution_refused"`

Why: `computer_execution_boundary_v1` and `canonical/tests/test_computer_unconfined_route_guard_v1.py` enforce that unconfined host Python/CLI execution (`documentation_mining_v1`, `computer_env_v1`, `acquisition_v1`, or unconfined `cli_exec`/`python_eval` workflow steps) must refuse execution unless running inside an admitted confinement boundary. That refusal is a deliberate safety invariant and is preserved intact.

---

## 2. Two Real Defects Uncovered on the Legitimate Confined & Zero-Host-Exec Paths

Auditing `solve_or_learn` (`canonical/swe_kernel/closed_loop_autonomous_controller_v1.py`), `SentientCognitiveCore.record_wake_episode` (`canonical/swe_kernel/sentient_cognitive_core_v1.py`), `MetaCircularOrganGraph.record_transition` (`canonical/swe_kernel/meta_circular_organ_graph_v1.py`), and `CompoundingConceptLibrary.sleep_abstract` (`canonical/swe_kernel/concept_library_v1.py`) uncovered two critical defects that broke legitimate zero-host-exec and specialist paths:

### Defect A: `8,851.72 ms` Synchronous `sleep_abstract` Explosion Inside `< 50 ms` Tier 0 Skill Recall

In `canonical/tests/test_acquisition_to_execution_engine_v1.py::AcquisitionToExecutionEngineTests::test_phase2_semantic_web_form_to_direct_http_generalization`:

1. Call #1 (`solve_or_learn("Submit service=billing_api and env=staging to http://127.0.0.1:<p1>/console")`) discovered the HTML `<form>`, elevated it to a direct `http_request` workflow skill, qualified it against an ephemeral twin server, and recorded transition #1 on `shared_cognitive_core(None)` in `52.68 ms`.
2. Call #2 (`solve_or_learn("Submit service=auth_gateway and env=prod to http://127.0.0.1:<p2>/console")`) recalled and executed the compiled `http_request` skill in **`5.57 ms`** inside `_solve_or_learn_impl`, but the outer `solve_or_learn` wrapper then called `shared_cognitive_core(None).record_wake_episode(...)` -> `organ_graph.record_transition(...)`.
3. Because `len(self._world_transitions)` reached `2` (`len % 2 == 0`), `MetaCircularOrganGraph.record_transition` (`canonical/swe_kernel/meta_circular_organ_graph_v1.py` line 4214) unconditionally executed `self.evolve_policy_from_traces()`, even when an incumbent policy already existed, no live policy boards were present, and all transitions had uniform outcomes (`failed=False`, `value=1.0`).
4. `evolve_policy_from_traces()` invoked `CompoundingConceptLibrary.sleep_abstract(...)` twice (`8,656.14 ms` total). Profiling `sleep_abstract` with `cProfile` revealed **`44,818,099` function calls** and **`3,167,697` `copy.deepcopy` calls** per invocation (`3,871.62 ms` unprofiled / `15,805 ms` profiled) caused by:
   - Running `copy.deepcopy(parsed_programs)` and `ast.NodeTransformer` across all programs for every candidate expression in Stage 1 *before* checking the cheap substring guard `any(f"_v{i}[" in expr_src ...)` or the upper-bound Stitch node-savings inequality, and evaluating all 75 viable candidates instead of the top 24.
   - Calling `copy.deepcopy(tree)` inside `executable_ast_bytes` on a freshly parsed `ast.parse(source_text)` AST.
   - Running pairwise `higher_order_plotkin_lgg` across 86 un-deduplicated loop functions (`3,655` pairs) in Stage 2B without first deduplicating identical ASTs or checking function arity/statement-count equality before `_normalize_function_for_plotkin_lgg`.

**Fix & Measured Result:**

| Metric | Before Fix | After Fix | Speedup |
| :--- | ---: | ---: | ---: |
| `CompoundingConceptLibrary.sleep_abstract` (8-organ policy corpus) | `3,871.62 ms` | `1,048.25 ms` | **3.69x** |
| `SentientCognitiveCore.record_wake_episode` (Call #2, even transition) | `8,958.48 ms` | `11.36 ms` | **788.60x** |
| Tier 0 HTTP Skill Recall wall clock (`solve_or_learn` Call #2) | `8,851.72 ms` (FAIL `> 50 ms`) | `< 20.00 ms` (PASS `< 50 ms`) | **> 440x** |

### Defect B: Severed `ROUND-0 PATHOLOGY PRECHECK` + `TIER 0-SEMANTIC` Specialist Block in `closed_loop_autonomous_controller_v1.py`

In `canonical/swe_kernel/closed_loop_autonomous_controller_v1.py`:

1. Lines 511–534 computed `_has_structured_specialist` over 19 structured specialist keys (`ambiguity_problem`, `sense_problem`, `semantic_relation_problem`, `domain_mapping_problem`, `polytope_problem`, `cross_document_problem`, `r2_adequacy_request`, `policy_adequacy_problem`, `policy_cover_payload`, `escape_repair_state`, `scientific_discovery_problem`, `ooxml_preflight_target`, `trace_capsule_problem`, `tool_schemas`, `api_endpoints`, `dom_action`, `dom_elements`, `perf_target`, `repair_command`), and `canonical/runtime/brain_unified_model_v1.py` (line 1135, `0C. Direct specialist routes`) forwarded those keys directly to `solve_or_learn`.
2. However, the `ROUND-0 PATHOLOGY PRECHECK` (`round0_meta`, `_credit_assoc_memory`) and `TIER 0-SEMANTIC` dispatch block from commit `d4b2ed90` had been dropped during a subsequent merge, while leaving `"round0_precheck": round0_meta` at lines 638 and 788.
3. As a result:
   - Every passing `byte_verified_bridge` execution raised `NameError: name 'round0_meta' is not defined` inside `try ... except Exception: pass`, silently discarding the verified 2-step bridge result.
   - All 12 structured specialist problem types fell through to `live_brain_route_admission_v1.solve()` and failed with `FAIL__RAW_GOAL_COMPILATION_GAP`.
   - Tier 1 composer routing called `routed = croute.route(goal, g=_cached_composer_graph())` and immediately overwrote it on the next line with `routed = croute.route(goal)` (rebuilding the capability graph from scratch).
   - In `canonical/swe_kernel/autonomous_awake_loop_v1.py` (line 1932), `AwakeAgencyDaemon.pulse()` with an explicit `r3_state_path` on an already-converged workspace reported `"IDLE_ALREADY_CONVERGED"` instead of `"VERIFIED_R3_FIXED_POINT_REACHED"`.

**Fix & Measured Result:**

- Restored the `ROUND-0 PATHOLOGY PRECHECK` (`round0_meta`, `_credit_assoc_memory`) and `TIER 0-SEMANTIC` specialist dispatch block in `canonical/swe_kernel/closed_loop_autonomous_controller_v1.py`, added `"byte_verified_bridge"` to `_has_structured_specialist`, removed the duplicate un-cached `croute.route(goal)` call, and aligned `AwakeAgencyDaemon.pulse()`'s converged R3 fixed-point status when `_r3_explicit` is set.
- Verified across:
  - `canonical/tests/test_wake_sleep_recall_and_specialist_controller_v1.py` (`6/6 passed`)
  - `canonical/tests/test_computer_unconfined_route_guard_v1.py` (`14/14 passed`)
  - `canonical/tests/test_post_066e8df_workspace_speed_and_r2_scientific_fabric_v1.py` (`5/5 passed`)
  - `canonical/tests/test_unified_awake_cognitive_fabric_v1.py` (`3/3 passed`)
  - `canonical/tests/test_optimal_unified_creature_and_prc2_v1.py` (`12/12 passed`)
  - `canonical/tests/test_meta_circular_global_sentient_creature_v1.py` (`35/35 passed`)
  - `canonical/tests/test_sentient_cognitive_core_v1.py` (`22/22 passed`)
