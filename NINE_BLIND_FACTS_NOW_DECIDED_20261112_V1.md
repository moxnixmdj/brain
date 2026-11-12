# Nine blind facts become decidable; the machine can now ask nine more questions

**2026-11-12.** Branch `arena/156d21d6-brain`. Base `05c9d45ff` (#6707). Follows
`A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md` (the corrected ordering) and
`WHAT_A_SUCCESS_TEACHES_20261112_V1.md` (the registry section D). Authority: NONE — sandbox
measurement, `$0`, zero model dependency, `truth.achieved` stays `false`.

## 0. The owner's question, and where this round sits

The owner asks again whether one try in every new environment teaches everything permanently.
The quantifier answer is unchanged and re-verified this session (one demo: held-out accuracy
**0.10**; one demo + chosen questions: **1.00**; one success: **0/200** identified). This
round attacks a *prerequisite* of the "arbitrary environments" claim: a try is only
informative if the machine can tell whether it FAILED BECAUSE IT CANNOT ACT HERE. Round 3's
audit found 11 facts (by today's tree, 10) where the registry could not even ASK that
question — `BLIND`: no capability produces the fact, no sensor reads it. A capability held by
a blind premise is auto-refused with no evidence, indistinguishable from "I have no idea".

The field measures the same gap: GroundAct (arXiv 2508.05614) shows agents drop from 85–96%
to **29–53%** exactly when action feasibility depends on environmental state the instruction
does not mention; environment-probing memory curation (arXiv 2609.11060) raises pass rate
39%→73% by giving the curator read-only world probes. Sensing the world before acting is the
accepted lever; this round installs it for nine more facts.

**Placement, honestly stated.** The corrected ordering in
`A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md` measured that binding (54
capabilities, 37%) dominates premise failure (12, 8%), and demoted blind-premise closure from
"highest-gain" to its true rank. This round therefore claims **prerequisite work, not the
gain item**: the front door consults the SAME sensor (`world_probe_v1`) for
`PRECONDITION_NOT_TRUE_OF_WORLD`, so no premise repair can show its value until the facts
decide. Binding repair (54) remains the next round's dominant target.

## 1. What was built

`canonical/runtime/world_probe_v1.py` — the sensor tables gain the missing subjects, each
instrument honest by the module's own rules (answer yes or no, never guess; absence is
information; zero learned bytes, zero inference):

| fact(s) | instrument | this machine's answer |
|---|---|---|
| `git.repository.available` | `git` binary on PATH (the operate adapter shells out to it) | **True** (`path_executable`) |
| `pypi.live_metadata.available`, `pypi.selection.available` | TCP connect to pypi.org:443 — the same instrument convention as `network.http.available`; decides the *route*, never "may I fetch" | **True** (`pypi_tcp_reachable`) |
| `structured.release_claim.available` | the claim arrives over HTTP from the official source → the network route is the machine-level precondition; content stays the adapter's job | **True** (`network_tcp_reachable`) |
| five `chart.*.available` facts | the raster-chart subsystem: `PIL` importable AND `tesseract` on PATH — the imports the adapters actually make, the binary they actually call | **False**, evidence names BOTH missing pieces (`missing module:PIL, executable:tesseract`) — decided, not blind |
| `source.candidate.provenance.verified` | **none — stays BLIND on purpose** | `UNDECIDABLE__NOT_ESTABLISHED` |

The last row is the honesty test of the round: nothing produces that fact (the enumerate
adapter's `output_verified` is only "file written and non-empty"), and a file-existence scan
would fabricate "verified". A fabricated closure would be worse than blindness; it stays
blind, with the reason recorded. Two capabilities remain honestly premise-blocked by it.

## 2. Measurements (predictions written before each run; first run missed 2 of 10, cause found, fix was data not a hack)

`canonical/tests/test_world_probe_senses_the_nine_blind_facts_v1.py` — 9 tests; registry
totals and fate-shift receipts:

| # | measurement | result |
|---|---|---|
| 1 | registry fact classes | `{PROVIDED: 100, SENSED: 24, BLIND: 1}` — was `{100, 15, 10}` on this tree, `{100, 14, 11}` in the pinned doc |
| 2 | capabilities blocked by a blind premise | **2** (both `source.*`, held by the deliberately-blind fact) — was 10 at round 3, 9 this morning |
| 3 | capabilities fully decidable now | **143 of 145** — was 135 |
| 4 | front-door fate, premises now True | `git.repository.operate.v1` → `ACTION_FAILED` (past the premise gate, into execution/binding), `pypi.provenance.audit_live_artifact` → `ACTION_FAILED`, `web.release.verify.independent_http` → `AMBIGUOUS` — none rejected with `PRECONDITION_NOT_TRUE_OF_WORLD` any more |
| 5 | front-door fate, chart premises now False-with-evidence | 4 chart capabilities reject with the premise *answered* (named missing dependencies), no longer with an undecidable shrug |
| 6 | fail-closed unchanged | `warp.drive.available` → `UNDECIDABLE__NOT_ESTABLISHED` — unknown facts are never guessed |

First-run honesty: the two `chart.question.*` facts stayed UNDECIDABLE in run 1 because
`chart.question.binary_phase_solvus` does not END with `.question` (the strip loop strips
endings only). The fix was explicit subject rows in the table — reviewable data — not a
suffix hack. Updated pins in `test_what_a_success_teaches_v1.py` also fix a **pre-existing
stale-pin failure on main** (the tree measured BLIND 10 / SENSED 15 while the test pinned
11/14 — a prior round closed one fact without updating the pins; that test failed on this
base before this round touched anything).

## 3. What is real and what is not, after this round

**Real (measured):** 9 more facts decidable by honest instruments; 143/145 capabilities with
checkable applicability; 3 capabilities past the premise gate at the front door; chart
absences reported with named missing pieces; the one unfakeable fact left blind on purpose;
fail-closed behaviour untouched (39 tests across the four sensor-adjacent suites).

**Not real (unchanged, pinned):** one-try identification (0.10); one-success applicability
(0/200); cross-kind compounding (0/5); binding — **54 capabilities still cannot be called
with what a goal supplies, the dominant measured blocker**; permanence under drift;
sentience.

**Pre-existing failures found and recorded, not caused by this round** (both reproduced on
the clean base with the round's change stashed): `test_raw_goal_pathology_memory_v1.py` (2
fixture/suppression failures — the OCR run on this box records
`BOUND_SYSTEM_TOOL_MISSING:tesseract`, not the label the fixture pins) and
`test_gate_accepts_a_failed_repair_v1.py::test_the_repairable_fixture_really_is_repairable_and_really_is_broken`
(1). Both are environment-dependent suites; fixing the fixture/oracle mismatch is a separate
honest round.

## 4. Smartest next steps (by the corrected ordering, re-measured)

1. **Binding repair — 54 capabilities.** The front door identifies them correctly, their
   premises are now checkable, and it still cannot supply their arguments (arity
   over-specification, selector defaults, unbound slots). This is the dominant measured
   blocker between "the capability exists" and "the creature can act".
2. **The 2 honestly-blocked source capabilities**: a real producer for
   `source.candidate.provenance.verified` (a verification step in the source pipeline), not a
   sensor fake.
3. **Chart subsystem restoration**: install PIL + tesseract where charts matter and the same
   probes flip to True by themselves — the sensor already measures it.
4. Chosen-question settlement at the front door (last round's gate) now has 143 decidable
   premises to consult.

## 5. Reproduction

```bash
python3 -m pytest canonical/tests/test_world_probe_senses_the_nine_blind_facts_v1.py -q   # 9 passed
python3 -m pytest canonical/tests/test_what_a_success_teaches_v1.py -q                    # 15 passed (pins updated)
python3 what_a_success_teaches_20261112.py --json /tmp/wast.json                          # fact_classes {100, 24, 1}
```
