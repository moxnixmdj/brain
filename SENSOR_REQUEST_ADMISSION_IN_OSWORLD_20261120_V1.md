# Computed sensor requests are admitted into OSWorld guest state ops — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No benchmark score, capability/acceptance/terminal credit,
independent verification, runtime model call or stored parameter.

## The bottleneck this round removes

Last round computed and verified a sensor request (`st_mode` field/value relation) but left it inside
a producer experiment. A request that no consumer can use is inert. The project's OSWorld 2.1 adapter
already accepts an injected `guest_controller`; that is the smallest real integration point.

Direct edits were rejected before implementation: `git hash-object` found byte pins for the state-op
compiler, the host guest bridge and the adapter in canonical verification receipts. So the new module
composes them instead of changing a byte.

## What was built

`canonical/runtime/osworld_sensor_request_bridge_v1.py` supplies `AdmittedSensorGuestOps`:

- re-measures the external request store on a fresh real filesystem; a stored row is never trusted;
- compiles one new read-only op, `ASSERT_SENSOR_REQUEST`, from the *freshly admitted* field/value;
- delegates all ordinary state ops to the pinned bridge unchanged;
- runs the exact assertion program through the benchmark-compatible guest controller;
- fails closed on stale store, wrong path kind, policy-supplied field/value, or bad guest receipt.

The policy supplies only a path. It cannot supply or override the field or value. No `is_dir`
predicate is written; the guest code reads the raw admitted `st_*` field from `lstat`.

## Measured result

Receipt: `canonical/verification/SENSOR_REQUEST_ADMISSION_IN_OSWORLD_20261120_V1.json`.

- 6 new tests passed in 0.77 s; 60 combined OSWorld state-op/adapter/bridge tests passed in 2.16 s.
- Real subprocess output: `SENSOR_REQUEST:PASS:st_mode:16877`.
- Fresh store admitted; stale store, regular file instead of directory, and policy-supplied field/value
  all failed closed.
- Ordinary `WRITE_TEXT` still delegated and its output appeared before the sensor assertion.
- `BrainOSWorldAgent(..., guest_controller=AdmittedSensorGuestOps())` accepted the bridge through its
  existing injection point and returned the verified guest receipt to its history.
- All three pinned kernel files are byte-identical to HEAD. A1–A10 true. 0 model calls, 0 parameters,
  $0 spend.

## Failures recorded

- The pre-build action intent was rejected because its evidence paths did not exist in HEAD. Fixed by
  citing existing canonical evidence before the build; the check then passed. This is an orientation
  defect, not a capability result.
- The first design considered was editing the pinned OSWorld kernels. The pin audit killed it before
  implementation.

## What remains

This is harness integration, not a full OSWorld 2.1 run. There is no zero-model policy solving a
108-task long-horizon workflow, no GUI/browser success, no unseen-environment learning score and no
independent verification. OSWorld 2.0's hardest failures are implicit state, multi-item tracking and
conflict disambiguation [1](https://osworld-v2.xlang.ai/); this round only makes one computed sensor
observable and checkable inside the guest. The next bottleneck is a zero-model policy that chooses
these admitted state ops from an unseen task and verifies the final state, then a full untouched task
run. §6 is not met.
