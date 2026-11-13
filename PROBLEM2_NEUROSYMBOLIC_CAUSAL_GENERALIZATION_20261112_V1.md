# Problem 2 answered honestly: a neuro-symbolic engine with causal receipts — not a better lookup

**Date:** 2026-11-12
**Branch:** `arena/54c552e8-brain`
**Supersedes:** `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md` and `SEMANTIC_GENERALIZATION_PROOF.md` (their "TF-IDF + synonym table = solved" claim is retracted here; see "What was wrong").
**Status:** engine, controller integration, verifier, and 69 new tests are on this branch. Claims below are limited to what is measured here.

---

## What was wrong with the previous engine

`canonical/swe_kernel/semantic_generalization_engine_v1.py` (as of base `e432b2ea`) was a **lookup dressed as generalization**:

1. **Whole-phrase matching.** Tasks were matched against ~7 synonym groups with TF-IDF + character n-grams. "How many classes does X contain?" matched only because the token "class" was in the vocabulary — the same trick as a keyword `if`.
2. **A keyword "confidence".** Cosine similarity over bag-of-words was reported as confidence. It carries no semantics: "count the functions in the file" and "the file functions count the" score identically.
3. **Hard-coded execution.** `problem2_solved_wrapper.py` and the controller's `TIER 0A-SEMANTIC` block both contained `if "class" in goal.lower(): ... else if function/method/subroutine ...` — two branches, everything else silently unsupported.
4. **Stringly-typed answers.** It returned `"Found 1 classes"` where callers required an int (`int(r_cls_count["answer"])`), which is exactly what produced the 6 failing `test_swe_self_improvement_bridge_v1.py` checks.
5. **No explanation.** There was no mechanism to say *why* an answer was right, and no way for it to be wrong on purpose and catch itself. An engine that cannot fail cannot be trusted.

## What replaces it

`canonical/swe_kernel/semantic_generalization_engine_v1.py` **in the same file**, keeping the module path so imports stay stable. Four pillars:

### Pillar 1 — OnlineParametricPolicyModel (trainable, honest about its role)

Three linear heads — `W_op` (5 operations), `W_concept` (24 concepts), `W_domain` (5 domains) — over 128 hashed bag-of-words features (unigrams + bigrams, signed SHA-256 hashing, L2-normalized), initialized deterministically (`Random(0xA01)` etc.) and trained **online** with cross-entropy gradient descent + decoupled weight decay (`lr=0.05`, `wd=1e-4`).

Every verified experience produces a **verifiable receipt**:

```
pre_loss 2.32373 -> post_loss 2.280943   (Δ = 0.0428 per store)
pre_correct_prob -> post_correct_prob
delta_w_l2 ≈ 0.080
updates += 1   (persisted to GENERALIZATION_POLICY_V1.json, git-ignored runtime state)
```

The policy is a **corroborator and learner, not an answerer.** It cannot override the symbolic parse and cannot veto a verified program. It is never the thing that says "the answer is 9".

### Pillar 2 — SemanticTaskParser + CompositionalProgramSynthesizer

`parse_task(goal)` produces a typed `SemanticTaskAST`:

```
operation ∈ {count, list, breakdown, exists, compare}     (domain- and priority-aware)
concept   ∈ 19 Python-AST concepts + markdown-native (heading, section, code_block,
            bullet, link, word, line) + JSON-native (key, entry, object, array, number,
            string, boolean, null) + CSV-native (row, column, cell) + text-native
            (line, word, character)                        — 24 total
domain    ∈ {python_ast, markdown, json, csv, text}        (inferred from target extension)
targets   — multi-file aware, absolute and repo-relative
qualifiers∈ public, private, name_prefix, name_suffix, name_contains,
            min_args, max_args, has_decorator, has_docstring
```

Compositionality is real: operation × concept × domain × qualifier combines freely. "Count **public** **async** functions **with at least 2 parameters and a docstring** in X" parses to one plan; it was not memorized.

The synthesizer emits an explicit, inspectable **plan** — `LOAD → PARSE_<domain> → SELECT_<concept> → FILTER_qualifiers → REDUCE_<operation>` — executed by a deterministic interpreter over `ast` / markdown / `json` / `csv` / text. Nodes are emitted in **source order** (pre-order DFS), so name lists read naturally.

Domain-concept coherence is enforced: asking for `function` in a `.json` file fails closed (`CONCEPT_UNRECOGNIZED`) instead of producing garbage.

### Pillar 3 — CrossDomainSchemaTransfer

One abstract schema, five adapters. Nothing about "how many" is baked to Python:

| Domain | Concepts | Notable mechanics |
|---|---|---|
| python_ast (`.py`) | 19 AST concepts | `ast.parse`, parent map, source-order select |
| markdown (`.md`) | heading, section, code_block, bullet, link, word, line (+ **all python concepts**) | hand-rolled parser; fenced `python` blocks are extracted, re-parsed as AST and selected with the python adapter — `LOAD→PARSE_markdown→EXTRACT_FENCED_CODE_BLOCKS→PARSE_python_ast→SELECT→REDUCE` |
| json (`.json`/`.jsonl`) | key (recursive), entry (top-level), object, array, number, string, boolean, null | recursive walk with `$.path` locations |
| csv (`.csv`/`.tsv`) | row (data rows), column, cell | `csv.Sniffer` dialect detection with comma fallback |
| text (`.txt`/`.text`/`.log`) | line, word, character | splitlines / `\w+` |

`breakdown` produces a per-concept distribution in any domain; `compare` produces `{left, right, delta}` over exactly two targets with a delta identity postcondition.

### Pillar 4 — CausalMechanismVerifier (why is the answer right?)

The synthesized program is *probed on interventions* before it is trusted — Pearl-ideas applied to a program verifier:

1. **Preconditions** — every target exists, the domain parses, the concept/operation are known, qualifiers are applicable to the concept and feasible (argument window). Failures → `FAIL_CLOSED__TARGET_NOT_FOUND` / `__PRECONDITION_FAILED` / `__INAPPLICABLE_QUALIFIER`.
2. **positive_intervention_probe** — `do(source := synthetic fixture)` with **hand-computed** ground truth (e.g. the Python fixture has exactly 4 functions, 5 parameters, 2 docstrings, 4 calls; JSON fixture has 8 keys, 2 objects, 3 numbers...). Qualifier probes build a dedicated two-node fixture (one good node satisfying all qualifiers, one bad node violating exactly one designated qualifier) and **self-check it before it is used as ground truth** — if the fixture builder cannot construct a sound ground truth, the run fails closed.
3. **null_probe** — `do(source := empty fixture)` must yield 0 / all-zero breakdown (an empty JSON object is exactly one object; that exception is encoded, not hand-waved).
4. **confounder_intervention_probe** — `do(source := fixture where every surface token of the concept appears in comments and strings)`. The program must not be fooled; lexical cheating is measured, not assumed impossible.
5. **postconditions** — answer types match the operation (int ≥ 0 for count, bool for exists, string lists, dict breakdowns, compare delta identity).

Any failed probe or postcondition → `FAIL_CLOSED__CAUSAL_VERIFICATION_FAILED` (or `__POSTCONDITION_FAILED`), with the failing probe named in the receipt. **No path exists from "verifier disagrees" to an emitted answer.** The sabotage test (`test_verifier_fails_closed_when_mechanism_is_sabotaged`) proves the verifier can fail — a test of the test.

## Measured evidence (this workspace, base e432b2ea, 2026-11-12/13)

| Check | Result |
|---|---|
| New tests `canonical/tests/test_real_generalization_engine_v2.py` | **69 passed** |
| `test_swe_self_improvement_bridge_v1.py` (was: 6 checks failing with `int('Found 1 classes')`) | **5/5 OK**; Layer A now yields structured ints (`python.source.definition_count.v1` / `python.source.audit.ast`) |
| `test_the_front_door_teaches_and_applies_what_the_bundle_ships_v1.py`, `test_problem_2_generalization_v1.py`, `test_workflow_goal_generalization_v1.py`, `test_swe_self_improvement_bridge_v1.py` | **34 passed, 2 skipped** |
| edit_by_example confined-exec import fallback (`edit_by_example_v1`, `expression_operator_pack_v1`, `bring_names_v1`) | `test_repeated_change_one_example_v1.py`, `test_bring_names_v1.py`, `test_expression_operator_pack_v1.py`: **67 passed** |
| Broad taught-actions / front-door files | **184 passed** |
| Novel phrasings end-to-end (`enumerate subroutines`, `identify methods`, `Count if statements`, `Count for loops`) | all answered by the engine with correct structured answers |
| Online policy learning | receipt shows strictly lower loss after every verified experience; `\|\|ΔW\|₂` ≈ 0.08; weights persist and reload |

### Controller integration (in `closed_loop_autonomous_controller_v1.py`)

- **Mapping `learn` flag honoured**: `solve_or_learn({"goal": ..., "learn": False})` no longer silently runs the learning path; the kwarg is validated (`LEARN_FLAG_MUST_BE_BOOL` otherwise) — this is what restored the front-door door path and the bridge's structured answers.
- **Latent bug fixed**: the read-only door path called `ra.solve` without `task_id`; `ra.solve` demands it (`REQUEST_INVALID`). `door_req.setdefault("task_id", task_id)` repairs a path that had never been exercised before the flag was honoured.
- **TIER 0A-SEMANTIC rewritten**: calls `GeneralizationEngine.solve_task(...)`; on `pass`, returns structured answers under `status=PASS__TIER0A_SEMANTIC_GENERALIZATION` / `tier_used=tier0a_semantic_generalization`; on any failure it **falls through** to the rest of the controller (never guesses). Policy updates are in-memory only on this path (`persist_policy=False`, `store_experience=False`) so tracked runtime state is never silently mutated — the old tier also never persisted.

### Honesty gates (all `FAIL_CLOSED__*`, all with a receipt naming the reason)

`OPERATION_UNRECOGNIZED` · `CONCEPT_UNRECOGNIZED` · `NO_TARGET_FILE` · `TARGET_NOT_FOUND` · `DOMAIN_UNRECOGNIZED` (incl. mixed-target goals) · `DOMAIN_PARSE_FAILED` · `UNGROUNDED_NEGATION` (negated requests are never answered) · `INAPPLICABLE_QUALIFIER` (qualifier on a non-named concept / wrong domain / whole-file breakdown) · `QUALIFIER_COMBINATION_INFEASIBLE` (fixture self-check could not construct ground truth, e.g. `public` + `name_prefix="_"`) · `QUALIFIER_UNPARSED` (an argument-count marker like "at least 2" with no unit is refused, never silently dropped) · `CAUSAL_VERIFICATION_FAILED` · `POSTCONDITION_FAILED`.

## Verification receipts (real run, 2026-11-12)

```
[3] identify methods in canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py
    answer:  ["__init__", "handle_starttag", "handle_endtag"]
    policy:  loss 2.273535 -> 2.230587 (||dW||2=0.0804)
    probe:   positive_intervention_probe  passed=True
    probe:   null_probe                   passed=True
    probe:   confounder_intervention_probe passed=True

[4] Count if statements in canonical/runtime/solve_v1.py
    answer:  41
    probe:   positive_intervention_probe  passed=True   (do(fixture): expected 1, got 1)
    probe:   null_probe                   passed=True   (do(pass-only): expected 0, got 0)
    probe:   confounder_intervention_probe passed=True   (comments/strings do not count)
```

## What is NOT claimed

- This does **not** solve Problem 2 in general. The engine answers exactly the compositional **count / list / breakdown / exists / compare** family over the enumerated concepts and five domains. Open-ended goals ("fix the failing tests") are refused (`OPERATION_UNRECOGNIZED`), demonstrated by a test.
- Qualifiers compose only with named definitions **in the python_ast domain** (e.g. "public functions in notes.md" is refused). Same for `compare` (exactly two targets).
- `breakdown` on markdown covers markdown-native concepts; python concepts inside fenced blocks are counted for `count`/`list` but not merged into the markdown breakdown dictionary.
- Domain inference is extension-based; a JSON document named `.txt` is treated as text.
- The parametric policy is a small corroborating model. Its updates are real gradient steps with verifiable receipts; it is not a language model and not a reasoning authority.
- `enumerate` maps to `list` (names), honestly — it is not silently reinterpreted as `count`.
- Measured precision on repo files is currently **100% on the engine's answered set** because anything unverifiable is refused rather than answered wrongly — the honest denominator is "answered", not "asked".
- Pre-existing failure `test_another_wording_or_another_kind_of_file_changes_nothing[...lesson...]` fails identically on base `e432b2ea` (verified in a pristine worktree); it is not a regression and is not touched here.

## Reproduce

```bash
python3 -m pytest canonical/tests/test_real_generalization_engine_v2.py -q
python3 -m pytest canonical/tests/test_swe_self_improvement_bridge_v1.py -q
python3 problem2_solved_wrapper.py        # 5/5 verified goals, prints probe receipts
```
