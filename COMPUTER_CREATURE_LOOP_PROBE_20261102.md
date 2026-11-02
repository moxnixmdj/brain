# Real-file learning probe and safety blockers

2026-11-02. Local research measurement, not independent personnel verification or a claim of general computer use, sentience, or permanent mastery.

## Follow-up: complete compression comparison and safer publication

The earlier wrong-content example below now refuses instead of reporting success. The direct `apply` path stages a copy of the input, refuses an existing destination or unsafe output name, requires a zero exit status, and verifies the completed artifact before a no-overwrite hard-link publication. For gzip, bzip2 and xz (including the corresponding tar wrappers), it streams the **entire** decompressed data against the staged input and reads through EOF, catching truncation and checksum errors. It also checks staged and original input digests before publishing. The chain path checks its completed staged artifact before a no-overwrite publication rather than deleting a caller's pre-existing or concurrently created target.

These changes do not make arbitrary code safe. A staging directory is **not an OS security sandbox**: a recipe or discovered program can access absolute paths, the network and other processes, write outside staging, exhaust resources or race checks; there is no general rollback of such effects. Format checks for other output types do not establish that their content fulfills the goal. The tar chain still does not independently verify every member of a directory against the complete source tree, and does not provide crash-atomicity or comprehensive concurrency protection. Use trusted programs and genuine OS isolation; do not infer safe general computer use.

The separate real-file probe still shows direct gzip teaching, cold execution and warm fresh-process recall with full-byte external checks; the raw-goal front door still fails closed and does not perform the task. Its direct cold arm starts with empty memory, **not** learning disabled. Connecting the learner to the public front door remains blocked by this missing security boundary, lack of a true learning-off control, the unadmitted action intent and the other authority/verification issues. No admission gate was bypassed.

The new local regressions cover wrong-but-valid output, truncated gzip/bzip2/xz, large and empty input, nonzero exits, staged input modification, existing destinations, symlinks, destination creation during execution and real tar→gzip execution. The affected safety, route and real-file probe suites ran **24 tests, all passed**; the existing `RealFileCase` suite ran **8 tests, all passed** in a disposable checkout with a restricted PATH and network namespace. These are same-producer local tests, not independent personnel verification; no full-suite pass is claimed.

## What was tried

`python3 computer_goal_reuse_probe_20261102.py` runs the real unified `RAW_GOAL` front door and, separately, the existing `computer_env_v1.perform` route on a small file-compression task. Each call is a fresh Python process. The teaching file and target file have different names and contents. Cold and warm direct targets have the same bytes; warm gets a copy of the direct teaching state and cold gets an initially empty state. Only `gzip` is visible on PATH.

The direct cold arm has an empty transfer store, **not** a learning-disabled switch: `perform` may learn during that run. The fabric cold request passes `learn=False`, but this is not a claim that all other learning stores are disabled. These routes use different inputs, so this is not a controlled capability comparison. Checking full decompression and input equality is a separate authored outcome audit, not a separate human verifier.

The probe uses a disposable copy of the checkout, temporary user files and state, restricted PATH, and a Linux network namespace. It is **not a filesystem or hostile-code sandbox**; run only trusted checkouts. It fails rather than running without the requested namespace if that facility is unavailable. No source data or state outside the copy is intentionally targeted.

## Observed outcomes

Before the narrow guard, teaching, cold and warm RAW_GOAL runs all selected `archive.tar_gz.create_from_manifest`, reported `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`, and left the requested `lesson.txt.gz` or `report.txt.gz` absent. They instead created an unrelated generated tar archive under the disposable checkout's `canonical/astra_runtime/tmp`. The producer's reported semantic acceptance was therefore false for these requests; the external audit found no target. The enabled teaching run queued a success observation but explicitly said `permanent_reuse_authorized: false`; a queued observation is not a verified learned skill.

The current narrow pre-execution guard refuses this specific incompatible selected tar-manifest route when an explicit single-file gzip compression request names a different `.gz` output. After the guard, all three RAW_GOAL cases fail closed, no generated archive appears, and their source and neighboring `_verify.py` files remain unchanged. **The requested task still does not complete through the unified front door.** This is a narrow guard, not a general proof that all goal-to-artifact bindings are correct, nor a connection of the computer learner to the front door.

The direct computer path produced a gzip containing the entire correct source in teaching, cold and warm fresh processes. Teaching and cold discovered the tool; warm reported `PASS__RECALLED_AND_REVERIFIED` and `from_memory: true`. A missing-input control refused and did not create the target. In one measurement, direct cold took 0.088 s and warm 0.093 s inside their workers; this single restricted-PATH experiment shows no speedup, and excludes teaching and process startup.

## Safety defect fixed, and an additional unfixed blocker

Before this change `program_synthesis_v1.verify_round_trip` wrote its helper to the fixed filename `_verify.py` in the output directory, then deleted it. A disposable reproduction destroyed an existing file on both good and bad gzip verification; a symlink caused the linked file's bytes to be overwritten. The change passes the same fixed snippet to a new Python process via `-c`, with the output path as a distinct argument, so the verifier creates no helper file next to the user's output. Tests cover an existing file, symlink, invalid artifact, absent neighbor and even the artifact itself named `_verify.py`.

**Historical observation before the follow-up above:** the direct route's `ROUND_TRIP_OK` gzip verifier read only one decompressed byte and did not compare the result to the original file. In a disposable local test, an explicitly supplied recipe that wrote a valid gzip of `wrong data` returned `PASS__APPLIED_TO_REAL_FILE` for a source containing `actual user data`; full decompression showed different bytes. This was a deliberately supplied bad recipe, not evidence that normal discovery always learns that recipe. It showed why format-readability alone is insufficient. The follow-up now checks full decompression for supported compression formats; other semantics and arbitrary subprocess side effects remain open.

Minimal reproduction (uses only a temporary directory and the Python standard library):

```python
import gzip, sys, tempfile
from pathlib import Path
from canonical.runtime.computer_env_v1 import apply
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    src = root / 'data.txt'
    src.write_bytes(b'actual user data')
    recipe = {'argv': [sys.executable, '-c',
                       'import gzip,sys; sys.stdout.buffer.write(gzip.compress(b"wrong data"))'],
              'target': 'data.txt.gz', 'stdout_to': 'data.txt.gz'}
    result = apply(recipe, src, output_name='data.txt.gz')
    target = root / 'data.txt.gz'
    print(result['pass'], target.is_file() and gzip.decompress(target.read_bytes()) == src.read_bytes())
    # Before the follow-up: True False. Current draft: False False (not published).
```

## Validation and remaining work

- 52 targeted tests passed, including five neighboring-file tests, three routing-guard tests, existing format tests and the real-file probe regression. Another 27 existing/new coding-route, gap and ledger tests passed. In a disposable copy, archive-compound acceptance, typed-SWE planning and live-integrated-brain suites passed 13, 18 and 11 tests respectively; those runs emitted subprocess/file `ResourceWarning`s. These are local producer-run tests, not independent verification. No full-suite pass is claimed.
- The official unified-model compiler regenerated its tracked projection. Its verifier in a disposable checkout reported 33/33 with seed `computer-goal-20261102` and digest `b07cf47a646a9a774680f94f2f07c93f3ce75d31b2207719e3589497916921ea`; it explicitly says `AUTHORITY NONE -- SANDBOX MEASUREMENT, NOT INDEPENDENT VERIFICATION`.
- Static integrity guard passed (11 rules, zero violations); `git diff --check` passed. The action intent remains an unadmitted draft and its orientation check reports `ORIENTATION_PROGRESS_CLASS_INVALID`; the full action/OBS gate has not passed. The earlier R1 fabric authority-blob drift remains unresolved.
- The coding front-door loop still stops at the independent-verification gate and its frozen template drops retained-learning inputs. A distinct verifier and legitimate admission/contract review remain necessary; no flags, pins or authority were fabricated.

The above records the earlier snapshot; see the follow-up at the top for subsequent compression and output-safety changes. Next: establish a real execution isolation boundary, legitimate admission and a true learning-disabled control before connecting the existing learner to the front door. Repeat with genuinely different tasks and held-out independent audits. The tiny gzip probe is neither a general benchmark nor an independently verified gain.
