# The system cannot yet do one ordinary thing (0 of 8), and now we can see exactly why

**2026-11-24 · branch `arena/0964738f-brain` · authority: NONE (producer-run sandbox)**

This iteration stopped counting surfaces and asked the only question that matters for §6:
*given an ordinary sentence and a real file, does the artifact afterwards hold what was
asked for?* The answer is **no, 0 of 8**, and the gate that answers it is now part of the
tree so the number cannot drift back into anecdote.

---

## 1. Requirements bound, and the §2 boundary re-checked

Zero model calls, zero knowledge in weights, knowledge and skills in an external inspectable
store, everything computed, *best part is no part*, insanely fast, research project-then-web
before any design, honesty separating verified / unverified / failed, tests on the hardest
available problems.

§2 boundary, tested rather than restated: the two things built this iteration hold **no
parameters at all** (`task_gate_v1` is a harness; the deliverable of the previous iteration
learns into a plain JSON ledger). The boundary stands: weights hold mechanisms (0 here),
the store holds what was learned, world facts are never stored in either.

---

## 2. Research first: the artifacts this prompt names do not exist

Searched the tree by name, twice, before designing anything:

| Named in the prompt | Files in this tree |
|---|---|
| `typed_invention_v1.py` | **0** |
| `epistemic_scan_acquire_compress_v1.py` | **0** |
| `BRAIN_POLYGLOT_CST_SKILL_STORE_V1` | **0** |
| `verified_skill_crystallizer_ir_bridge_v1` | **0** |
| `CUMentalWorldModel` | **0** |
| "Iteration 75", commit `209bbc6c` | **0** |
| `same_identity_supervisor.py` | present (53 files reference it) |
| `HONEST_SUITE_BASELINE`, "344 failing" | present |

The real analogs of the four "leaps": `operand_invention_v1.py` +
`egraph_and_deductive_synthesizer_v1.py` (invention), `language_neutral_skill_bridge_v1.py` +
`tree_sitter_cst_skill_skeleton_v1.py` (semantic equivalence), `causal_dependency_repair_v1.py`
(data flow), `environment_learning_v1.py` (executable mental model). The design below is
about the tree that exists, not the one the narrative describes.

Frontier cross-check (Nov 2026): Terminal-Bench 2.0's dominant execution failure is
"command not found" at 24.1% of all failures and 35.1% of execution errors; the benchmark
has been superseded by 3.0/4.0, SWE-bench Pro's public split tops out near 61.5%, and the
original OSWorld was retired once agents beat its 72.36% human baseline. Those are the
instruments §6 names, and none of them can be run in this sandbox (no Docker, no display,
no network to images). What *can* be run is the thing they all measure — an instruction, a
real file, an independent check — which is what this iteration built.

---

## 3. Two designs tested and killed before they were built

**Typed artifacts for openssl.** Hypothesis: openssl's 4,391 operations fail because the
machine lacks certificates and keys, so let the machine build its own (genrsa → req -x509 →
x509 -outform DER → pkcs12), and hand them to the search as typed witnesses.

Measured on a 300-operation slice: **21 → 24 addressable.** The failures are not witness
failures; they are composition failures ("No operation option specified", 42 of them) and
input-lack failures ("Error: offset out of range" from reading closed stdin). **Killed.**
openssl is a *composition* surface, not a *witness* surface, and buying it needs a planner,
not a bigger alphabet.

**A learned global search order** (last iteration) — already killed at 344 < 358.

---

## 4. The measurement that replaces surface counting

`canonical/runtime/task_gate_v1.py`: eight ordinary instructions, each in a fresh temporary
workspace, each judged by a verifier written against the OS's own tools (`gzip -dc`, `tar`,
`sqlite3`, `json`, `hashlib`). The verifier never looks at the plan. A task passes only if
the artifact is right.

```
  ESCAPED  line_count        python.source.definition_count.v1
  COMPILE  gzip_copy         GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH
  ESCAPED  tar_gz_bundle     python.refactor.inline_helper.v1
  COMPILE  rename_logs       GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH
  ESCAPED  adults_from_json  auto.pypi.msgpack
  ESCAPED  sqlite_row        docx.document.create.python_docx
  ESCAPED  count_error_files python.source.definition_count.v1
  ESCAPED  digest_report     python.source.definition_count.v1

  passed 0 / 8   (ESCAPED 6, COMPILE 2, WRONG 0, PASS 0)
```

Three findings, in order of severity:

**4.1 Every compiled plan would have written into our own repository.** All six compile
successes bound their output to `canonical/astra_runtime/tmp/brain_out__<capability>__<hash>.json`
— inside this repository, not inside the workspace the task provided — while binding
`source_root: "."`. Run without a guard, "write the number of lines to count.json" would have
scattered artifacts through the repository. The gate refuses before execution and reports
`ESCAPED`, which is why the first run of it (before the escape rule existed) showed six
`WRONG` and none of them had run either.

**4.2 Selection is vocabulary overlap, and it repeats itself.** One capability,
`python.source.definition_count.v1`, was chosen for three unrelated sentences (*count lines*,
*count files mentioning error*, *write a digest*) — because "count" is the only word that
overlaps. `docx.document.create.python_docx` was chosen for *create a sqlite table*.

**4.3 The registry cannot express the tasks.** 447 capabilities; **zero** of them are
gzip/compress; 65 are `python.*` developer-tooling. The compiler is not "failing to find" a
capability for `gzip` — there is none to find. Ceiling explained.

---

## 5. What this says about the core hypothesis

The standing hypothesis: *instant learning in new environments is solved, so a single
experience plus strong coding ability solves computer use.*

- **Instant learning of forms: real, and measured.** Last iteration's ledger turned 157
  searches into 70 on the second run of the same machine.
- **Instant learning of tasks: not demonstrated, and the blocker is upstream of learning.**
  You cannot learn from an experience that never verifies. Six of eight plans here are
  wrong before anything runs; a system that records them as successes poisons its own store.
  **Soundness must precede learning** — otherwise the compounding loop the design depends on
  is a loop that compounds error.
- **The real limiting factor is the sentence → grounded action mapping.** It is currently
  7,554 lines of hand-written English keyword rules (`goal_compiler.py`, ~100 `_`-helpers:
  `_path_named_by_role`, `_path_named_after_output_verb`, `_goal_surface_flags`, …), with a
  documented unsoundness in its own benchmark (2 of 23 compile against the wrong capability)
  and a binding path that ignores workspace-relative objects.

---

## 6. The single next mechanism (chosen, minimal)

**A grounded binder: a capability is applicable to a sentence only if its declared inputs
bind to objects that exist in the workspace AND the artifact the sentence names is what the
capability produces there.**

This is one mechanism, not a feature list, and it replaces the keyword layer's decision rule
rather than adding to it:

1. **Objects come from the workspace.** The named nouns of the sentence are matched against
   the workspace's actual files (not the repository's), and a sentence that names `data.txt`
   cannot bind `source_root: "."`.
2. **Effects come from the declaration.** Each capability already declares its inputs and
   its produced artifact; the requested artifact (`count.json`) must be among what the plan
   writes, *inside the workspace*.
3. **Failure is refusal.** No capability satisfying both is `GOAL_COMPILATION_UNGROUNDED`,
   never a substitution.
4. **Coverage comes from the machine.** The 447-capability registry has no gzip capability
   while `gzip` is on the machine and last iteration's ledger already knows which of its
   doors actually run. Deriving routable capabilities from *those* doors — not from a list I
   write by hand — is the only route to ordinary-task coverage that is not rule accumulation.

Rejected: writing eight capabilities for the eight gate tasks (hand-holding, and the first
unseen sentence would defeat it); extending the keyword rules (the failure is the method);
a model call for the mapping (forbidden, and the whole point).

---

## 7. State of the five expansions

| Expansion | Status after this iteration | Evidence |
|---|---|---|
| GUIs / browsers | unmeasured; no display in this sandbox | — |
| Natural-language input | **the binding constraint**, 0/8 with zero model calls | §4 |
| Cross-session learning | real for forms (157→70 searches); blocked for tasks by unsoundness | §5 |
| Auto-discovered counterfactuals | not reached | — |
| New arbitrary environments | action surface +86% (last iteration); binding still local-only | prior receipt |

## 8. Not done

No benchmark score is claimed. The gate's 0/8 is not a regression — it is the first honest
statement of where this system stands on ordinary work. What changed this iteration: the
tree can no longer report a surface number without an artifact number next to it, and the
three specific reasons ordinary tasks fail are measured rather than guessed.

### Files

| Path | Role |
|---|---|
| `canonical/runtime/task_gate_v1.py` | 8 ordinary tasks, fresh workspace, independent verifiers, escape refusal |
| `canonical/tests/test_task_gate_v1.py` | 13 tests, including each verifier's ability to fail |
| `canonical/verification/TASK_GATE_BASELINE_20261124_V1.json` | the 0/8 run |
