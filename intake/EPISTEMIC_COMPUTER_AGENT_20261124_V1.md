# Zero-Model Epistemic Computer-Use & Software-Engineering Agent (2026-11-24)

## 1. Bound Problem & Contradiction Resolution

- **Runtime invariants enforced**: `model_calls = 0`, `api_spend_usd = 0.0`, `parameters_stored = 0`, `raw_coordinates_saved = 0`, `raw_trajectories_saved = 0`.
- **Persistence vs. Zero-Knowledge-House resolution**:
  - **Code / mechanism layer (zero world facts)**: Holds only general computed laws — content-signature set separation, Laplace-smoothed value-of-information (`p_useful / (1 + cost)`), execution-verified contrast/victim screening (`exit_on_real == 0` AND `exit_on_decoy != 0` AND runner-canary failure preservation), W3C Core-AAM role-to-action type compatibility + post-action state-diff (`ACCEPTED_INERT`), and dynamic Ochiai + call-tail + frame-predicate causal localization/synthesis.
  - **External inspectable, human-editable, execution-refutable JSON store (`EpistemicStore`)**: Stores only earned structural schemas (`judges.json`, `cli_grammars.json`, `gui_workflows.json`, `swe_operators.json`, `ignorance_ledger.json`). Editing or deleting any entry on disk takes immediate effect on `reload_all()`, and any schema that fails to change state or violates postconditions on a new instance is automatically refuted in-place (`refutations += 1`).

## 2. Empirical Verdict on One-Shot Learning & Action Exposure

1. **Is instant one-shot learning already solved?** **No.** From information theory and repository receipts (`DOES_EXPERIENCE_COMPOUND_20261124_V1`, `PERFECT_ALGORITHM_MODEL_VERDICT_20261122_V1`), a single uncontrasted positive trace removes ~`0.1`–`1.0` bit of a ~`5.4`-bit step ambiguity because infinitely many hypotheses (`(x, y)` pixels, DOM IDs, literal filenames, semantic role+slot predicates) agree on one positive run. Generalization in few/one episodes requires **active contrast & victim screening** (`earn_a_judge`, `ACCEPTED_INERT` state-diff, `verify_runner_canary`) to falsify overbroad and surface-specific hypotheses before admission.
2. **Why exposing advanced coding actions once does NOT solve SWE or computer use**: Knowing the syntax of `edit_file` or `pyautogui.click(x, y)` is an ungrounded action space, not the environment's transition function. Across 61 real open-source bug-fix commits, the bottleneck is not knowing how to write Python AST edits — it is (a) **cross-file causal localization** and (b) **domain/protocol semantics** (PEP 427 regex `\Z`, HTTP/WSGI state machines, TOML grammar rules) that are not derivable from generic edit operators alone.
3. **Goal-directed active learning vs. upfront "learn everything"**: Blind upfront probing wastes probes on distractors and risks cognitive interference (*AgentCL*, arXiv:2606.02461; *Studying Without a Syllabus*, arXiv:2609.10824). In Experiment 1 across 8 heterogeneous 10-file rooms, passive header/signature diffing + `IgnoranceLedger` goal-directed earning spent **6 probes in 3.13s** (`0` probes on warm episodes 3–8) vs. **24 probes in 6.54s** (**4.0x fewer probes, 2.09x faster**) for upfront room-wide learning, while catching `8/8` corrupt decoys and refusing `3/3` lazy stdlib traps (`bz2.open`, `lzma.open`, `sqlite3.connect`).
4. **What transfers vs. what dies**:
   - **Never save**: Raw `(x, y)` coordinates (`0/6` transfer, `6/6` triggered `Factory Wipe` on redesigned V2 UIs), raw CLI paths/argv (`0/4` transfer on renamed directories), unscreened single-file patches (`pluggy@4326ced299` suppressed `pytest` assertions until caught by `verify_runner_canary`).
   - **Save (with refutation counters)**: Contrast-earned content judges, content-addressed (`sha256[:16]:invoked_name`) CLI flag/synopsis grammars + refusal switches, W3C ARIA `(role, slot_tokens, verb)` causal workflow steps (`6/6` V2 redesign transfer), and empirical SWE operator family utility/cost priors.

## 3. Unified Architecture Built (Not Rebuilt)

Reusing `scan_and_diff_against_memory_v1`, `earn_a_judge_v1`, `ignorance_ledger_v1`, `jit_knowledge_v1`, and `the_guide_is_an_action_grammar_v1` without mutating byte-pinned `canonical/runtime/` modules:

1. `canonical/swe_kernel/auto_judge_discovery_v1.py` — Automatic CLI + Python stdlib content-judge discovery (`15` kinds earned; lazy-open traps refused; exclusive judge refutation on false-positive probes).
2. `canonical/swe_kernel/interface_action_grammar_v1.py` — Content-addressed CLI grammar memory (`0` warm `--help` subprocesses) + HTML/DOM -> W3C Core-AAM Accessibility Tree action grammar, role-type compatibility, `ACCEPTED_INERT` broken-ARIA detection/bypass, OSWorld `pyautogui` lowering, and generalized `(role, slot_tokens, verb)` workflow memory with active refutation.
3. `canonical/swe_kernel/causal_swe_repair_v1.py` — Zero-leakage `sys.settrace` Ochiai + call-tail + crash-frame fault localizer, 5-family causal AST/frame repair synthesizer, non-contradictory guard law, two-stage test verification, and dual `pytest`+`unittest` `verify_runner_canary` anti-lobotomy gate.
4. `canonical/swe_kernel/epistemic_computer_agent_v1.py` — Unified zero-model agent (`EpistemicStore` + deterministic NL goal parser + out-of-world refusal + all 4 surfaces).

## 4. Honest Measured Results & Remaining Gaps (§6 Status: NOT Terminal)

| Surface / Experiment | Epistemic Agent (Zero-Model) | Baselines / Controls | Honest Limits |
| :--- | :--- | :--- | :--- |
| **Exp 1: Unseen Mixed OS Rooms (8 eps)** | `8/8` valid + `8/8` corrupt caught; `6` probes (`3.13s`); `0` warm probes | Empty memory: `100%` unread; Upfront-all: `24` probes (`6.54s`) | Formats without local CLI/stdlib validator stay `OPEN__JUDGE_UNEARNED` |
| **Exp 2: Unseen CLI Toolchains** | Cold `1/1` (`0.15s`), Warm `4/4` (`0` `--help` calls), Out-of-world `REFUSED` | Raw path/argv replay: `0/4` | Interactive TUI/REPL CLIs (`vim`, `less`) not covered by batch synopsis grammar |
| **Exp 3: W3C ARIA / OSWorld Multi-App (6 apps)** | Cold V1 `6/6` (`6` lying ARIA traps bypassed); Unseen V2 redesign `6/6` (`5.0` vs `6.0` steps) | Naive ARIA (no state-diff): `0/6`; Raw `(x, y)` replay: `0/6` (`6/6` hit `Factory Wipe`) | Canvas/WebGL pixel-only UIs without DOM/AT-SPI accessibility nodes require external OCR/AT-SPI bridge |
| **Exp 4: Blind Real Git-Stripped SWE Commits (57 unseen + 4 calibration, 13 repos)** | Top-5 file localization: `40/49` (`81.6%`) unseen (`44/53 = 83.0%` total); Genuine verified unseen repairs: `2/49` (`4.1%`; `2/24 = 8.3%` Round-1 single-line: `packaging@b80e6eb0a6` exact human match passing `61,705` tests + `packaging@8af75907bf` passing `61,541` tests) + `1/4` `attrs@3b0378dd66` exact human match; `0` fake repairs | Prior repo engine: `0/41` (`0.0%`) on unseen non-attrs even when handed exact `git show` diff line | `95.9%` of unseen real commits remain `OPEN`: multi-line protocol/API synthesis, regex/RFC domain rules, and child-process/thread tracing (`tqdm`, WSGI servers); Docker/Harbor/OSWorld VM suites remain unrun in this container |
