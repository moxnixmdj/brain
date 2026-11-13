# Observation identity is part of the model — 2026-11-12

Status: producer-run sandbox measurement and runtime reliability repair. Authority: NONE. No capability, benchmark, family, ownership, terminal, or sentience credit is claimed. `truth.achieved` remains `false`.

Base measured before repair: `e432b2ea85e3e98aed72ddc61ed4972e78e688f4`. Main synced during the work: `7c58f1234f7bee6cd870fcec1c6cffa2bae48039`.

## The defect

`environment_learning_v1.state_key` used `str()` for hashable observations and `json.dumps(..., default=str)` for unhashable ones. That made different observations share a model row:

- `7` and `"7"`;
- `True` and `"True"`;
- `None` and `"None"`;
- `(1, 2)` and `"(1, 2)"`;
- `b"ab"` and `"b'ab'"`;
- mapping keys such as `1` and `"1"` after projection.

A carried model is only meaningful under the observation identity that wrote it. The old transfer path could rank, walk, and relearn with legacy rows without declaring that identity.

## What shipped

- `environment_learning_v1.STATE_KEY_SCHEMA = PROJECT_BRAIN_ENVIRONMENT_STATE_KEY_V2`.
- `state_key` now hashes a type- and structure-tagged canonical form with the prefix `el-state-v2:`. Scalars, container kind/order, mapping keys, sets, bytes, and opaque hashable objects are encoded explicitly. Cycles and unsupported unhashable objects fail closed.
- Volatile computer-noise projection is preserved. `project_computer_observation` gained an explicit `preserve_key_types=False` default; identity calls it with `True`. CNF predicate names remain strings.
- `learn_model` and `drive` reject a carried prior unless `prior_schema` matches V2, and report `state_key_schema`, `prior_states`, and `prior_rejected_states`.
- `systematic_exploration_v1.explore_to_goal` applies the same gate under the shared identity. A custom `key_of` remains the caller's own identity and is not silently reinterpreted. `drive` persists the explored model with the schema returned by exploration.
- `transfer_learning_v1.remember` stores `model_schema`; plan-only repetition preserves a stored model; a declared model can upgrade a legacy row; an undeclared model cannot downgrade a declared row; a new declared model refreshes the row. Recall gives the model bonus only to V2 models. `drive` and `walk_carried_model` reject legacy priors before using them.

The MiniWoB measurement tool passes its own `key_of=state_key` at the carried-model call sites, so those caller-owned rows are not rejected by the shared-identity gate.

## Measured effect

Fixed alias corpus: 20 observations, 190 unordered pairs.

| Measurement | Legacy | V2 |
|---|---:|---:|
| Alias-pair collisions | 10 | 0 |
| Mixed-type environment traces | 188 | 188 |
| Trace rows disagreeing with the environment's typed transition table | 66 | 0 |
| Distinct mixed-type states observed | 4 | 7 |
| Targeted three-suite tests | 78 passed | 99 passed |

The mixed environment starts at integer `0`; `quote` returns `str(s)`, `inc` returns `int(s)+1` saturated at 10, and `reset` returns integer `0`. The oracle is the environment's own transition definition, not the learner's key.

Depth/budget control, all at budget 40 / max_depth 8 / seed 0:

- mixed environment, reachable goal `s == 3`: PASS, plan `["inc", "inc", "inc"]`;
- mixed environment, deep goal `s == 10`: `FAIL_CLOSED__GOAL_NEVER_OBSERVED`;
- pure-integer no-alias control: goals 3 and 4 PASS; goals 5 and 10 fail closed with 5 observed states.

The deep-goal failure is therefore not counted as an identity win. The identity claim is the collision reduction and typed-oracle row agreement.

Compatibility five-suite run, legacy and repaired:

- 262 passed;
- 4 failed;
- 27 skipped;
- 0 new failures by JUnit test-case comparison.

The four failures are pre-existing at the measured base: one real-transfer prior-transition assertion and three computer-env confinement assertions. They were not weakened.

An additional four-wave/skill-scope consumer probe ran 124 passed / 2 failed. Both failures are `TREE_SITTER_SUBSTRATE_MISSING:python` in this sandbox, not observation-identity assertions.

Unified model verifier: 33/33 PASS, sandbox measurement, not independent verification. Repo-integrity static guard: PASS.

## Honest limits

- This repairs observation identity and carried-model schema admission. It does not create hidden state, settle stochastic transitions, or prove goal reachability beyond the explored budget/depth.
- The tabular environment model remains a single-successor hypothesis; stochastic conflicts are preserved in traces, not solved.
- Opaque hashable objects keep a type-qualified caller-visible string identity. Callers needing a finer quotient must project or supply `key_of`.
- Legacy rows are rejected, not migrated by guessing. They must be relearned or explicitly declared under the identity that wrote them.
- No weight training, cross-domain compounding, universal computer use, or sentience is measured here.

## Reproduction

```bash
PYTHONPATH=/home/user/.brain-test-deps python3 -m pytest -q -p no:cacheprovider \
  canonical/tests/test_environment_learning_v1.py \
  canonical/tests/test_transfer_learning_v1.py \
  canonical/tests/test_systematic_exploration_v1.py

PYTHONPATH=/home/user/.brain-test-deps python3 -m pytest -q -p no:cacheprovider \
  canonical/tests/test_miniwob_one_success_generalisation_v1.py \
  canonical/tests/test_zero_llm_awake_mastery_upgrades_v1.py \
  canonical/tests/test_real_environments_v1.py \
  canonical/tests/test_computer_env_v1.py \
  canonical/tests/test_transfer_learning_off_control_v1.py

python3 canonical/runtime/compile_brain_unified_model_v1.py \
  --output canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json
python3 canonical/runtime/verify_brain_unified_model_v1.py \
  --seed 20261112 --artifact canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json
python3 execution_guard/repo_integrity_guard_v1.py --static-only --json
```

The pre-registration was written before runtime edits. One amendment was added after the first repaired probe and before this report: the deep mixed-type goal needed a depth-matched no-alias control, because goal 10 still failed closed after typed-oracle errors fell to zero.
