# Mission status, 2026-11-24

**Branch:** `arena/3fc9b5f0-brain`. **No merge.** **§6 is not met.** This is a status record, not a completion claim.

## §2 contradiction resolved

Parameters hold computed mechanisms only. An external, inspectable, editable typed knowledge/skill store is allowed, and one experience may write an abstracted rule to it. Memorized world facts and runtime model calls are forbidden. Web/models may be used while building; nothing from them is a runtime dependency or counted as our capability.

## §3 direct verdict

| class | verdict on today's evidence |
|---|---|
| real | retention/replay; parameter-free literal generation from a failing input; 16-way CoW dispatch with correct global winner attribution and sibling cancellation; computed path/truthiness filters that reject vacuous test twins; line-level splicing that passes the union of two counterexample partitions on a controlled repository |
| false | "show the action once and the rule is learned"; "a better guard expression solves repair"; "a FAIL→PASS twin manufactured by one input literal is a contrast"; "16-way forks are faster than sequential on this 2-CPU sandbox" |
| unproven / missing | multi-hole, name and structural edits; transfer across environments; GUI/browser control; unseen-environment acquisition; full public benchmarks; independent verification; §6 completion |

**Overall:** the claim "fully solves computer use and advanced software engineering" is **unproven and contradicted on every hard slice actually run**. On 12 fresh click commits: 0/12 repairs. On one runnable public SWE-bench Lite instance: 0/1. GUI/browser tasks have not been executed.

## Generated repairs on five logged real failures (new)

The earlier rounds recorded 0/5 three times. A generator that composes source-derived transitions now verifies:

- click `c53d373`: normalize an observed empty `envvar`, tighten the compound guard, serialize the hint with quoted joining — `676 passed`;
- click `05f6fd0`: complete an early `return None` from the tuple the same function returns later, filling the observed empty member with `''` — `116 passed`;
- werkzeug `884437ae`: add the observed complement arm to two boolean clauses — `150 passed`;
- werkzeug `051fd663`: `.rstrip()` on the observed trailing-whitespace return — `124 passed`;
- click `fc518e4`: enumerated pass-or-retry policies for each fenced call in an exception handler — `8 passed`.

Authoritative receipts: `canonical/verification/EMPTY_PAYLOAD_SUPPRESSION_20261124_V1.json` (0/5, guard only), `MULTI_PRODUCER_NORMALIZATION_20261124_V5.json` (1/5), `MULTI_PRODUCER_NORMALIZATION_20261124_V7.json` (3/5). `MULTI_PRODUCER_NORMALIZATION_20261124_V9.json` records **5/5**, and `INDEPENDENT_REPLAY_FIVE_20261124_V1.json` reproduces **5/5** with a separate runner in fresh worktrees. All rounds: zero model calls, network calls, stored parameters, or gold-patch reads.

## Today's hard results

- Repo-native mining: FAIL 0/12; wiring splicing into it produced 0 partial candidates, so the splicing branch never fired on real data (`SPLICING_IS_WIRED_BUT_HAS_NOTHING_TO_SPLICE_20261124_V1.md`).
- pytest parameter acquisition: FAIL 0/12; most failures have no parametrized case (`PYTEST_KNOWS_THE_PARAMETERS_BUT_NOT_THE_CONTRAST_20261124_V1.md`).
- Manufactured contrasts: input-only 2/12 pairs, +path filter 1/12, +truthiness filter 0/12; 0/12 verified throughout. The two early pairs were vacuous (`THE_PASSING_TWIN_CAN_LIE_20261124_V1.md`).
- Parallel CoW rollouts: mechanism gates PASS, but 16 forks are **0.377×** the sequential speed on 2 CPUs and 2 forks are ~1.0× (`PARALLEL_COW_ROLLOUTS_20261124_V1.md`).
- Public benchmark probe: 1/1 FAIL, no gold patch read (`ONE_PUBLIC_BENCHMARK_INSTANCE_20261124_V1.md`).
- All receipts: zero parameters, zero model calls, zero network calls during solve. Quoted frontier names, iteration counts, hashes and benchmark scores from the request remain unverified and are not credited to this system.

## The single plan (what survives)

1. Represent every observation as a typed, source-traceable semantic IR: state, effect, precondition, postcondition, and the executable check that confirms it.
2. Treat a goal as a quotient of traces: retain only distinctions that change verification outcome. Scan for unknowns by residual/error, not by a learned world model.
3. Acquire missing structure at **build time** from primary sources and the project's own APIs; distill into the external typed store. At runtime, compute from the environment only.
4. Permit a contrast only when the passing case preserves the specification, preserves truthiness, and executes the same source path. Use it to constrain a structural edit at a real seat; never accept a verdict flip alone.
5. Verify with the project's own runner on the whole relevant test file. Splice complementary partial repairs; run CoW rollouts with `min(16, usable CPUs)` and record when oversubscription is measured.
6. Test only hard, ungated tasks: full public SWE instances, GUI/browser workflows, and unseen environments, with an independent verifier and ablation of each store/mechanism.

## Rejected ideas

- Runtime model calls, knowledge house, memorized world facts, raw action transcripts as learning.
- Scaling mutation count or parser breadth after strict filters found zero admissible contrasts.
- Mutating assertion literals to create a "passing twin".
- Fixed 16-way forking without measuring CPU capacity.
- Counting frontier-model outputs, aggregator benchmark snapshots, or gold patches as our capability.

## Immediate next work

The five-commit probe is now closed at 5/5 with independent replay, but an unchanged-generator probe on two unseen click commits is 0/2 (`UNSEEN_COMMIT_F67C2BB_20261124_V1.json`, `UNSEEN_COMMIT_7996A89_20261124_V1.json`): no transfer has been demonstrated. §6 still requires HONEST (if materialized), memory ablations, single-experience transfer, an unseen environment, GUI/browser, and full public benchmarks. None of those has passed; §6 remains open.
