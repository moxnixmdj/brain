# LiveBench-IF generation kit (PROVISIONAL tooling, zero progress credit)

**Authority status:** `PROVISIONAL_ANALYSIS`. No action intent, no current-base OBS, no independent verification yet. It lives outside `canonical/` on purpose, so it needs no frontier-sensitive intent. Moving it into `canonical/runtime/` is the owner pipeline's step (intent, OBS, public-runner verification).

**Why it exists:** `canonical/reasoning/2026-10-02_ZERO_COST_SUBSTRATE_ROUTE_CENSUS_V1.json` (P13, P14) records that, on the official LiveBench leaderboard, at least ten open-weights models score above the Opus 5.5 Instruction-Following bar (65.7), and that one pass is about 0.4M tokens. The scorer, the response adapter and the ID-set preflight are already independently verified in the repo. The only executable piece missing is *generate one response per question, safely, from a pinned generator*. This kit is that piece and nothing more.

**Tested against a mock endpoint only.** No real Workers AI, Pollinations or OpenAI-compatible call has been made by this code.

## What it does

`generate_responses.py` reads a local questions file, asks one endpoint for one response per question, and writes:

| File | Content |
|---|---|
| `responses.jsonl` | `{question_id, response}` records (the adapter's input contract) |
| `provenance.jsonl` | hash-chained: request/response digests, usage, neurons, model ids, config hash |
| `ledger.json` | per-UTC-day neurons, total tokens, calls |
| `summary.json` | status, counts, `execution_authority: false`, zero credit and spend |
| `model_answers.json` | only when complete: the LiveBench structure built by the existing adapter, after its ID-set preflight passes |

It does **not** score, read results, authorize anything, or claim capability.

## Safety properties (each is tested and mutation-checked)

1. **Budget cap, fail closed.** A worst-case check (`estimated input + max_completion_tokens`) runs before every call; the run stops with exit code 4 rather than exceed `--max-total-tokens` or `--max-neurons-per-utc-day`. A failed attempt is never counted as spend.
2. **Zero spend by construction for Cloudflare.** `--api-style cf-run` refuses to start without both a neuron cap and a price table. `prices_workers_ai_v1.json` records the neuron prices from Cloudflare's pricing page (recomputed against the census in the test). Recommended cap: 9,000 neurons per UTC day (free allocation: 10,000, per account and shared with any other Workers AI use).
3. **Frozen-release protection.** Rows whose release equals `--frozen-release` (the registry pins the bar to `2026-06-25`) are refused with exit code 3 unless `--authorization` is a JSON file matching the exact questions file hash, config file hash, model id and release, with `execution_authority: true`. The check happens before any network call. Do not create that file yourself: it must come from the project's own machine authorization of the one-shot run.
4. **Provenance.** Every call appends a hash-chained line; tampering, deletion or reordering breaks the chain and the next run refuses to resume.
5. **Secrets.** API keys come from environment variables, are never written, and the test greps every output for the key.
6. **Resume.** Answered ids are skipped; nothing is asked twice.

## Runbook (a machine with network access, for example the public runner)

```text
# 1. Arms: RAW is the bare "use model X" control; POLICY is a generic candidate Brain policy.
#    The marginal value of POLICY over RAW is UNMEASURED. Ownership credit needs that ablation.
python livebench_if_generation_v1/generate_responses.py \
  --questions dev_questions.jsonl --config livebench_if_generation_v1/brain_if_config_raw_v1.json \
  --out out_raw --model @cf/qwen/qwen3.8-27b --api-style cf-run \
  --prices livebench_if_generation_v1/prices_workers_ai_v1.json --max-neurons-per-utc-day 9000
#   needs CLOUDFLARE_API_TOKEN as --api-key-env (default BRAIN_GEN_API_KEY) and CLOUDFLARE_ACCOUNT_ID

# keyless alternative (the transport already verified for the AutomationBench gateway; models are NOT pinned):
python livebench_if_generation_v1/generate_responses.py ... --api-style plain \
  --base-url https://text.pollinations.ai/ --model openai-fast --max-total-tokens 2000000

# 2. Score out_*/model_answers.json with the pinned, independently verified scorer (not part of this kit).
#    Scorer: livebench.if_runner.ifbench.evaluation_lib (test_instruction_following_loose; declared metric =
#    prompt-level loose accuracy) at upstream LiveBench/LiveBench commit 8f8e5c381a16e3f24257776edd53471fe86f8091,
#    bound in canonical/governance/LIVEBENCH_IF_VERIFIER_BINDING_V1.json. The public runner already carries the
#    hermetic setup (capsules/livebench_if_full_verifier, workflows verify-livebench-if-*). A driver that walks a
#    questions file and aggregates the metric is NOT included: the dataset's field names are unverified here.
```

Use **non-frozen** questions for development (earlier LiveBench releases, if present in the dataset). One way to export them, **UNTESTED** (HuggingFace is not reachable from the authoring sandbox, and the field names may differ; override with `--id-field`, `--prompt-field`, `--release-field`):

```python
from datasets import load_dataset
ds = load_dataset("livebench/instruction_following", revision="0868379c4b5cf62aeacaf8be4f08fced815c81bb", split="test")
# keep only rows whose livebench_release_date is earlier than the frozen release, write JSONL with question_id and turns
```

## Known limits and unverified points

- Cloudflare response shapes: both documented shapes (OpenAI-style `choices`/`usage` and `response`/`usage`) are parsed and tested against a mock; not verified live.
- Reasoning models count reasoning inside completion tokens: tune `max_completion_tokens` after a small pilot, because a budget exhausted by reasoning truncates the answer.
- Whether the candidate Workers AI models require the Workers Paid plan was not stated on the model pages read. If they do, the free-allocation route is unavailable and the cap here would be the only thing preventing spend.
- The leaderboard release behind the 65.7 figure is unrecorded; the registry pins `2026-06-25`. Do not compare across releases.
- The `plain` transport mirrors the request shape already verified for the AutomationBench gateway; its models are not pinned and report no usage (usage is estimated at 3 characters per token).
- Scope: a raw open model that already exceeds the bar would be an external capability provider under General Cognition Substrate Law V3 unless the Brain configuration measurably adds value. This kit makes that ablation runnable; it does not perform it.
