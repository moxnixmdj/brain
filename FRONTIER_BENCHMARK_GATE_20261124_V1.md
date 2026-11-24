# Frontier benchmark gate — 2026-11-24

## Current state

**Not qualified; do not execute task agents or claim a score.** The owner has
approved only isolated one-shot SWE worktree evaluation. This is not approval
for ordinary Harbor/Docker execution, other terminal tasks, a persistent worker,
host writes by task code, or production. The fixture collector is not qualified
for arbitrary code; it cannot express all Git changes, and its own checks do not
constitute independent authenticated attestation. Its producer-side SHA-256
recomputation is not proof of origin, isolation, correctness, or test success.
The Harbor agent now refuses before constructing a solver or executing an
environment command. The legacy SWE adapter also refuses before solver or
checkout. Neither accepts any real benchmark yet; the historical SWE-bench
Verified dataset is out of scope.

## Fixture-only effect expansion

The fixture collector now handles UTF-8, newline-terminated text additions,
modifications and deletions, including empty files, under its existing bounded
snapshot policy. Deleted effects carry baseline file bytes and their SHA-256;
new and modified effects carry resulting file bytes and their SHA-256. The
separate producer-built recomputation checks the effect set against a fresh
base checkout and replays the exact patch to compare file content, directories
and modes. The changed effect format is bound into its policy hash; old fixture
receipts were produced under the earlier policy and are not new-policy receipts.
Unsupported file types, paths, empty directories and mode changes are refused.
These are trusted-fixture tests, not admission for arbitrary tasks or an
independent authenticated receipt. The collector still has size limits and
unsupported Git effects; it must not be wired to execute real agents yet.

Five genuine SWE-bench Pro V2 HARD-51 task IDs were selected read-only at the
pinned commit in `qualification_results/frontier_five_discovery_20261124.json`.
The instruction and task configuration hashes enable identification, not
independent attestation. **0/5 executed; 0 patches collected or verified; no
scores.** During further preparation, the first selected task's public
`tests/config.json` verifier test names were displayed to the coding agent. No
gold patch was accessed, but that instance is no longer blind to this agent;
any later rollout must disclose this contamination. Neither the old Verified
refusals nor the Astropy trusted-fixture patches are frontier evaluations.
This machine has neither Docker nor Harbor,
no external VM, and no independent signing/verifier material has been supplied.

## Benchmark compatibility

* [SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md)
  supplies 642 Harbor tasks, including HARD-51. Its agent starts in an image
  with an existing base checkout, usually `/app`; grading replays the captured
  patch into a pristine image. The old Verified JSONL adapter does not implement
  this protocol. Locked runs have a 50-minute budget and no agent network except
  approved model endpoints. A Brain integration must capture and independently
  verify the exact patch before fresh-image regrading.
* [FrontierSWE v2](https://github.com/Proximal-Labs/frontier-swe-v2/tree/da83f84f8fbcec3cbf0f2b17c98ebc811355c2df)
  contains 34 diverse Harbor tasks, some requiring GPU resources; its artifacts
  and separate verifier are not generally representable as a Git diff against a
  known base. A worktree-patch carrier alone cannot implement that protocol.
  [px-eval](https://github.com/Proximal-Labs/px-eval/tree/ef9c4d1a6c69ce3e518bd11732dca109b1fc7919)
  orchestrates rollouts and separate grading. The reported benchmark uses a
  different, long-horizon protocol; a one-shot smoke run is not comparable.
* [Terminal-Bench 4.0](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.0.0)
  uses the dataset `terminal-bench/terminal-bench@4.0.0`. It also needs a task
  environment and verifier integration beyond this worktree carrier.
* [FrontierCode](https://cognition.com/blog/frontier-code): Cognition describes
  its tasks as not publicly released and offers evaluation to model creators.
  Do not invent a public self-run dataset, task, harness, or score; request the
  relevant FrontierCode 2.0 evaluation access from Cognition.

## Read-only HARD-51 preflight

`canonical.tools.pro_hard51_preflight_v1` checks the pinned upstream checksum
manifest, the exact 51-task ID list, and each selected instruction and task
configuration. It records Task #1's test-name disclosure without reading test
files, checks declared network mode and image identifiers, and writes only JSON
metadata; it does not run containers, solver, task code or a verifier. The full
51-task metadata and five-task subset were checked read-only locally; results
are in `qualification_results/pro_hard51_full_metadata_preflight_20261124.json`
and `qualification_results/pro_hard51_metadata_preflight_20261124.json`.
Checksums establish agreement with the pinned bytes, not authenticated origin,
runtime isolation, or receipt provenance. Docker and Harbor executable presence
is reported for information only; even `--allow-isolated-vm-eval` cannot admit
execution. The legacy adapter similarly records that flag but never acts on it.
The Harbor refusal trace records the disclosure globally because it cannot bind
a trustworthy task identity.

## External Ubuntu VM preparation (not executed here)

These are **preparation and inspection only**, not evaluation commands. Use a
separate disposable VM with adequate disk, and have its operator review the
upstream code, resource requirements, license and costs. Network access to the
image registry, package registry and model endpoint would also be necessary.
Do not put credentials in commands, source files, logs, or agent-visible task
environments. No task code, container, oracle solution or agent is run here.

```bash
set -euo pipefail
mkdir -p "$HOME/frontier-eval-prep"
cd "$HOME/frontier-eval-prep"
# Clone the session branch after it has been pushed; record its actual HEAD.
git clone --branch arena/d582a17b-brain --single-branch https://github.com/moxnixmdj/brain.git brain
git -C brain rev-parse HEAD
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git swe-pro
git -C swe-pro checkout --detach 66f92766bba642462d4bbe5479e83f91f9211862
git clone https://github.com/Proximal-Labs/frontier-swe-v2.git frontier-swe-v2
git -C frontier-swe-v2 checkout --detach da83f84f8fbcec3cbf0f2b17c98ebc811355c2df
git clone https://github.com/Proximal-Labs/px-eval.git px-eval
git -C px-eval checkout --detach ef9c4d1a6c69ce3e518bd11732dca109b1fc7919
(cd swe-pro/v2 && sha256sum -c SHA256SUMS)
python3 --version
command -v docker || echo 'Docker missing'
command -v uv || echo 'uv missing'
command -v harbor || echo 'Harbor missing'
mkdir -p reports
(cd brain && python3 -m canonical.tools.pro_hard51_preflight_v1 \
  --v2-root "$HOME/frontier-eval-prep/swe-pro/v2" --selection smoke5 \
  --allow-isolated-vm-eval) > reports/pro-smoke5-preflight.json
(cd brain && python3 -m canonical.tools.pro_hard51_preflight_v1 \
  --v2-root "$HOME/frontier-eval-prep/swe-pro/v2" --selection hard51 \
  --allow-isolated-vm-eval) > reports/pro-hard51-preflight.json
# Both reports intentionally say PREFLIGHT_ONLY_EXECUTION_BLOCKED.
```

px-eval specifies Python 3.12+, `uv`, an environment configuration and Modal
credentials; its example runtime uses Modal and may cost money. SWE-bench Pro V2
also documents Modal and public GHCR images. These upstream environments are
not themselves the approved Brain one-shot carrier. The above clones are other
repositories on the VM and do not alter this Arena branch.

**No executable Brain evaluation command is provided**: using the current
agent would only refuse, and claiming it is an integrated benchmark runner
would be misleading. After carrier qualification, authenticated verification,
protocol-specific integrations, the five-instance gate and any required scope
approval, follow the pinned upstream READMEs for image preflights, rollout and
separate grading. Terminal-Bench's upstream dataset selector is shown above;
FrontierCode access must be arranged separately. Before running other task
classes or harnesses, obtain explicit owner authorization for their actual
execution and effect model.

## Work remaining before admission

1. Engineer and adversarially qualify a one-shot OS boundary for arbitrary
   worker code, no host fallback, exact base checkout, immutable inaccessible
   `.git`, and robust descendant termination/quiescence. Address shared-kernel
   risk, races, mount escape and resource limits; a namespace smoke test alone
   is not proof.
2. Support or explicitly reject all relevant Git effect types; verify each
   changed file and exact unified diff against the base using SHA-256, including
   additions, deletions, modes, symlinks and binary content. Reject tampering,
   ambiguity and unsupported effects. Bind scope, base, task, policy and output.
3. Independently validate/sign attestation using pre-established trusted keys
   and independently held evidence, not producer booleans or generated keys.
   Wire the advisory localizer through the admitted boundary, not around it.
4. Implement separate protocol adapters for each actually authorized benchmark,
   including clean verifier replay as required. The two current wrappers are not
   those integrations. Then run the five pinned Pro instances and publish raw
   outcomes, receipt verification, independent review and resource/cost data.

## Reference scores, not our results

Anthropic's [Fable page](https://www.anthropic.com/claude/fable) reports 69.9%
FrontierSWE v2, 49.1% FrontierCode 2.0, and 74.6% Terminal-Bench-**Science**
0.1 for Fable 5.2; its [system card](https://www.anthropic.com/claude-fable-5-2-mythos-5-2-system-card)
reports 93.0% on SWE-bench Pro. The 74.6% is not Terminal-Bench 4.0. Reported
scores need their version, agent, trials, test conditions and metric; they do
not validate or measure this repository.
