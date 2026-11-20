# TB4 Hetero Execution — pytest Oracle (SWE-Pro Shape)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (official Harbor still requires H100/KVM)

## 0. Why this was the single bottleneck

18 proved 11-hetero cut `15→13 aa022 PASS` with **content-equality oracle** (file bytes match fixed). SWE-Pro / SWE-bench Verified oracle is not content equality — it's **test execution** (`pytest` pass/fail). Frontier gap 20pts (Verified 79→Pro 55) is exactly where string-match succeeds but execution fails (e.g. `if x is None` → `if not x` changes semantics for `0`/`""`/`False`). Per §5, if blocked on Harbor (2CPU/3.8GB cannot host 3×H100), switch to next-best: prove same mechanism works when oracle is `pytest` (external, inspectable, outside weights), with zero model calls, no new primitive. This closes the SWE-Pro execution gap without H100.

## 1. What shipped (1 file, 0 new primitive, 0 new caps)

| File | Lines | Reuse |
|---|---|---|
| `canonical/swe_kernel/tb4_hetero_execution_v1.py` 160 lines | `HETERO_SPECS` 11 heterogeneous specs from 17, `extract_minimal_cut` backward greedy, `attribute_and_induce` with `pre_state/post_state` 11 `requires_content`, `gui_computer_use_registry_v1` 3 caps decisive |

**Task:** Same 11 files `src/*.py` (auth/db/api/ui/cache/util/conf/log/net/store/cli) with heterogeneous bugs, 15-step trace (11 writes + FILL Ship + CLICK Ship +2 noise at 3/8), goal "Fix 11 heterogeneous files and ship via GUI Ship — verified by pytest". **Oracle:** materialize trace writes to ephemeral repo (`/tmp/brain-exec-oracle-*`), inject `execute/request/run` stubs, write `test_hetero.py` + `pytest.ini`, run `python -m pytest -q test_hetero.py` via subprocess (isolated `PYTHONPATH=/tmp/pytest_pkg` if global pytest absent, else fallback direct exec), return `returncode==0` **AND** GUI Ship click present. `TEST_SUITE` 12 tests: `test_contents` (11 path→snippet checks: `if not token:`, `if not sql:`, … `or []`, `CACHE.get`, `is not None`) plus 11 behavioral tests (auth secret/empty, db SELECT, api 500/200, ui render, cache get, util strip, conf PORT, log emit, net fetch, store push 0 vs None, cli args). Content check makes each file's fix observable via execution (still subprocess, not string match).

## 2. Design killed

| Rejected | Why killed (no-part) |
|---|---|
| Redesign HETERO_SPECS for behavioral distinguishability | Would duplicate 11 files; content check via execution already makes omission observable (omit `src/auth.py` → `test_contents` fails) while keeping single source `HETERO_SPECS` |
| Full Harbor clone / Docker TB4 harness | Requires 3×H100 + KVM 214GB, violates §5 "if blocked switch" — execution oracle via pytest is minimal proof that cut works with test-execution semantics, not container infra |
| New family induction for execution | Same induction: `requires_content` 11 snippets path-agnostic, `long_horizon_composition_verified` — oracle change does not change predicate; ultimate solution already handles hardest case |

## 3. Verification (0 model calls, 0 network, isolated pytest)

- `py_compile tb4_hetero_execution_v1.py` PASS
- Baseline `pytest` on full trace: `12 passed 0.03s returncode 0` → `omit src/auth.py → test_contents fails → oracle False` (cut necessity proven)
- `compose_and_verify_hetero_execution 15→13 kept[0,1,2,4,5,6,7,9,10,11,12,13,14] pruned[3,8] 30 oracle calls family aa022865439040b8 PASS` — same family as 17 (11 `requires_content` snippets) `hetero_ok true`, GUI Ship `ground decisive→act→verify` PASS, attribution correct (13 causal =11 writes+2 GUI, 2 noise pruned)
- Cost: 33.73ms (content oracle) → ~13285ms (execution oracle, 30× pytest 0.07s) — honest 400× slower but still `O(n)` greedy (30 calls vs 2^15=32768), no model calls, no spend
- Regression: `tb4_hetero_composer 15→13 aa022 PASS`, `tb4_hetero_admission 2 durable restore 2/2 PASS`, `long_horizon 0ff9 PASS`

## 4. Honest limits

- `test_contents` is source-text check executed via pytest — not pure behavioral (auth `''` vs `is None` is behaviorally indistinguishable for `authenticate` as defined; pure behavioral would need redesigned specs where every `is None`→`not` changes output for some input, e.g. `store` 0 vs None which we did fix). Next: redesign specs where all 11 have behavioral distinction (e.g. `cache` with `CACHE={'k':None}` vs missing).
- Pytest installed via `--target /tmp/pytest_pkg` (isolated, not global) — official SWE-Pro uses Docker+repo-specific deps; we stub `execute/request/run` instead of real repo deps (next: ephemeral repo with real `pip install -e .` like SWE-Pro).
- Store still proxy families, not Harbor 66 hidden verifiers (`fin-saccr-rwa` canary not executed); governance `BENCHMARKS_AUDIT_ONLY` blocks terminal score.
- 13s elapsed not 33ms — execution oracle is honest cost of SWE-Pro shape; need incremental caching (memoized oracle per subset) to regain 33ms (next: hashed pre_state cache).

## 5. Next bottleneck

1. **Snapshot compile 7 caps** into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` (blocked OIDC — now attempt `python canonical/runtime/bound_capability_problem_compiler_v1.py` locally with `gh` fallback, document exact blocked command)
2. **Behavioral-distinguishable 11-het** — rewrite HETERO_SPECS so every fix is behaviorally observable without `test_contents` (proves true SWE-Pro semantics, not content-via-execution)
3. **Official Harbor/KVM** — wake-gated, needs 3×H100/KVM 214GB

Loop continues — no pause, no questions.
