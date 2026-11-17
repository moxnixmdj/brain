# The judge cannot read the anchor

**Receipt:** `canonical/verification/VERDICT_ANCHOR_ADMISSION_20261117_V1.json`
**Mechanism:** `canonical/runtime/verdict_anchor_admission_v1.py`
**Tests:** `canonical/tests/test_verdict_anchor_admission_v1.py` — 11/11
**Rank:** 2 of `ranked_next_with_pass_fail` in `ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.json`
**Authority:** NONE — producer-run sandbox, $0, no model called.

## Why this exists

The verdict receipt named the loop axis's deepest station the
observation–verdict instrument, and its ranked plan's rank 2 is one sentence:
*anchor every self-judged verdict to data the judging loop cannot read
(suite/locked corpus)* — pass: always-pass collapse is detected at admission;
kill: the anchor is readable by the thing it judges. The repository's own
blocker lease says the same thing: `THE_LOOP_AXIS_NEEDS_AN_ANCHORED_OBSERVATION_VERDICT_INSTRUMENT`.

A loop that grades itself cannot see its own collapse. Who-Verifies the
Verifier (arXiv 2610.11464) measured it: strip the anchor guards and the
verifier becomes always-pass **while downstream skill training scores exactly
as well**. This tree measured the same asymmetry from the other side —
ungated replay of recorded plans was 53.5% stale and 31.1% silently corrupt
(228 real compositions), and the first-case instrument chose the wrong
observation on 81% of cases. A false pass is the expensive direction: it is
stored permanently; a false rejection only costs a capability the capability
metrics already charge for.

## What was built

`verdict_anchor_admission_v1.admission_errors(judge, anchor_cases,
judge_history)` refuses a self-judged verdict loop unless:

1. **Separation** — the judge's own source never names the label domain
   (`expected_verdict`, `replay_equals_live`, any replay `status` name);
   comments count. This is the plan's kill condition, made executable:
   `ANCHOR_READABLE_BY_JUDGE:<token>`.
2. **A real anchor** — runner-outcome ground truth the judge is invoked on in
   redacted form only. An anchor without both polarities cannot detect a
   constant judge and is itself refused
   (`ANCHOR_WITHOUT_NEGATIVE_CASE` / `ANCHOR_WITHOUT_POSITIVE_CASE`).
3. **Discrimination** — on the real known-false canaries:
   * passing **every** one → `ALWAYS_PASS_COLLAPSE` (the Who-Verifies
     failure, caught at admission);
   * passing **any** one → `ENDORSES_KNOWN_FALSE:<id>` (one endorsement of a
     known-false claim is already a refusal — the index keeps verdicts
     forever);
   * failing **everything** → `ALWAYS_FAIL_COLLAPSE`;
   * three or more prior verdicts with no failure ever →
     `NEVER_FAILS_HISTORY` (the production signature of a verifier that never
     vetoes anything).

Crashes, non-PASS/FAIL outputs, unreadable judge source, malformed anchors:
all fail closed.

## The anchor corpus is real

`canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json` —
**228 measured replay pairs** against this repository's own corpus at pinned
commit `c3a4c75e`, produced by the repository's own replay instrument
(model_calls 0, network_calls 0). Ground truth is the **runner's** outcome:
the recorded plan still holds on replay (110: `REPLAY_MATCHES_LIVE` 106 +
`REPLAY_DIFFERS_BUT_HOLDS` 4) or it does not (118: `REPLAY_DOES_NOT_PARSE` 47
+ `SILENT_CORRUPTION` 71). The judge never sees `status` or
`replay_equals_live`; its content carries site coordinates only. On these real
pairs the site separator `planned_line == live_line` holds **228 of 228** —
measured, not assumed, and pinned by the corpus test.

## Results (all on the real corpus)

| judge | what it is | admission |
|---|---|---|
| honest site instrument | PASS iff the site did not move | **admitted**, no errors |
| always pass | the collapse itself (2610.11464) | **refused** `ALWAYS_PASS_COLLAPSE` |
| label-reading judge | names `replay_equals_live` in its source | **refused** `ANCHOR_READABLE_BY_JUDGE` |
| never-fails history | honest, but 3 prior verdicts, zero failures | **refused** `NEVER_FAILS_HISTORY` |
| single false endorsement | honest except one known-false passed | **refused** `ENDORSES_KNOWN_FALSE` |
| constant fail / garbage / crash | non-discriminating or broken | **refused** `ALWAYS_FAIL_COLLAPSE` / `JUDGE_OUTPUT_INVALID` / `JUDGE_ERROR` |
| anchor with only one polarity | cannot detect a constant judge | **refused** `ANCHOR_WITHOUT_*_CASE` |

Pass condition of the ranked plan — *always-pass collapse is detected at
admission* — held: `ALWAYS_PASS_COLLAPSE` fired on 118 real known-false
canaries. Kill condition — *the anchor is readable by the thing it judges* —
held: the label-reading judge was refused by source separation.

## Honest limits

- Admission detects **collapse**; it does not certify judge accuracy beyond
  the anchor. The anchor is one real corpus (228 pairs), not every future
  case.
- The honest instrument's rule is measured on this corpus only; no
  generalisation past the pinned commit is claimed.
- Producer-run sandbox: tests re-read this receipt and the source receipt;
  independent re-execution still open.
- False rejections are deliberately not refusals (see asymmetry above); they
  surface in capability metrics instead.
- No benchmark, capability, family, terminal or weight credit; sentience not
  claimed; stdlib only.

## Sources

- Merged: `ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1.json` (ranked plan, two-axis
  bottleneck, three barriers), `PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json`
  (53.5%/31.1%), `THE_INSTRUMENT_NOT_THE_EXPERIENCE_20261117_V1.md` (81%),
  `ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json` (the corpus).
- External (read, not run): Who-Verifies the Verifier, arXiv 2610.11464 —
  anchor removal collapses the verifier to always-pass with unchanged
  downstream scores; EvoSkills arXiv 2604.01687 — surrogate-verifier ablation
  −30pp; VeriSkill arXiv 2607.27733 — verifier-evidenced revisions only.
