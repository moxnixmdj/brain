# One more advanced-coding action is now admitted to the confined seam — and four were rejected as inert

**2026-11-13.** Branch `arena/024b7a7c-brain`. Base `20a4cbe3` (#6840). Authority: **NONE**.
`truth.achieved` stays `false`. $0. No tolerance widened, no refusal lifted, no capability registered.
This is a measured round note, not a capability claim.

## The question this answers (the owner asked, again, whether the most advanced coding actions can just be experienced once)

The priced answer in `WHY_NOT_JUST_GIVE_IT_THE_TRY_20261112_V1.md` names the missing link for the
advanced-coding wall: the actions exist, the second binding surface reaches them, `confinement_v1`
(admitted, 9/9) + `confined_dispatch_v1` (the wiring, merged in the same round) exist — but the
**declarations file** (`canonical/runtime/CONFINED_EFFECT_DECLARATIONS_V1.json`, the reviewed
surface) admitted only 11 capabilities. The 2026-11-13 fresh run of
`canonical/tools/realistic_goal_reach_probe_v1.py` ("Realistic-goal reach probe", disposable clone,
this tree) reports **12** of 38 advanced-coding goals still dying with
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` (down from the documented 19 —
the tree moved), plus 3 EXECUTED (git.repository.operate.v1, python.refactor.rename_symbol.v1,
software.review.synthesis.supercomposer.v1).

## What changed — exactly one row

`python.software.repair.apply.verified.v1` added to `CONFINED_EFFECT_DECLARATIONS_V1.json`
(`effect_args: ["output_path"]`, budget 600s). It is the one confinement-refused capability whose
effect the boundary actually needs confinement for (`boundary.refuses_execution` → **True**; the
others it refuses locally are boundary-allowed). Verified directly, in a fresh disposable clone of
this repository with fixtures committed inside the clone only:

* `run_confined_capability` runs the adapter on the clone, `host_untouched: True`, receipt attached,
  host git status byte-identical — ran for 81.6 s and failed closed
  (`CONFINED_RUN_DID_NOT_PRODUCE_A_RESULT`) because my synthetic goal names no failing test to
  reproduce and no repair artifact to apply — **fail-closed, with a receipt, by design**, not a hang
  and not a wrong answer.
* It is dispatch-eligible now: when a sentence compiles and binds to this capability and the boundary
  refuses local execution, the confined route is tried; no declaration → identical refusal as before.

## What was deliberately NOT changed, and why

* **`file.copy.v1` and `file.rename.v1`: rejected.** `boundary.refuses_execution` → **False**
  (pure in-process `pathlib` adapters; no confinement needed). Rows would be inert data, and
  `file.copy.v1` is pinned absent from the file by `test_confined_dispatch_v1.py` (`test_a_copy_names_
  its_destination` pins its door behavior; AGENTS.md names the same choreography). Adding them would
  be decoration masquerading as progress.
* **`code.index.tree_sitter.incremental.v1` and `evidence.oracle.concrete_execution.v1`: rejected.**
  Same reason — `boundary.refuses_execution` → **False**; declaring them changes nothing at the door
  (measured directly: effect verified in 9.4 s / 5.4 s confined runs, `host_untouched: True`, but the
  seam is never consulted for them). Noted as verified-ready rows, not added.
* **`file.rename.v1` end-to-end** was verified working confined (byte_count check, effect sha256) —
  and still not declared, for the same reason.
* The remaining 11 rows are unchanged (all fail-closed identically; `test_confined_dispatch_v1.py`: 5/5).

## What this does NOT do

No realistic probe row flips yet: the corpus sentence for this capability ("Repair the defect … and
apply the verified patch.") does not compile/bind — `compiled_capability_id: null` observed in a
fresh clone after the change. The confinement refusal for it happens **before** capability dispatch,
so the row is a prerequisite for the measured flow (compile + bind → confined apply), not a demo of
it. Claiming more than that would be fabricating a result.

## Receipts

```bash
python3 -m pytest canonical/tests/test_confined_dispatch_v1.py -q       # 5 passed
python3 -m pytest canonical/tests/test_swe_self_improvement_bridge_v1.py \
   canonical/tests/test_the_front_door_teaches_and_applies_what_the_bundle_ships_v1.py -q   # 12 passed
python3 canonical/runtime/verify_brain_unified_model_v1.py              # 33/33 PASS (artifact unchanged by this edit)
```

Next honest step (unchanged from the priced chain): door compile/bind for the advanced-coding
sentences — `FAIL__RAW_GOAL_COMPILATION_GAP` (3) and `STATED_SWE_EFFECT_UNSERVED` (6) from the
2026-11-13 probe — one cause at a time, each behind the same fail-closed doctrine.
