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

## Executable evidence for the metric finding

`test_score_livebench_if.py` has a layer that runs only when `LIVEBENCH_ROOT` points at a LiveBench checkout at the pinned commit. It calls the REAL upstream scorer on synthetic questions (three checkers that need no NLTK data) and executes the facts behind the defect finding: the per-question score is the mean of "all followed" and "fraction followed" (one of two instructions followed scores 0.25, not 0), `<solution>` tags are honoured, prompt-level accuracy never exceeds the official score, loose can be more lenient than strict, and prompt-level loose accuracy has no fixed order against the official score.

```text
LIVEBENCH_ROOT=/path/to/LiveBench@8f8e5c3 python -m pytest livebench_if_generation_v1/test_score_livebench_if.py
```

## Pre-flight on the public IFBench dev prompts (everything except the LLM)

IFBench's repository (code Apache-2.0, data ODC-BY-1.0, https://github.com/allenai/IFBench) ships `data/IFBench_test.jsonl`: 300 public prompts that exercise **all 58** checker types (about 1.15 constraints per prompt, against about 3 for LiveBench). It is a non-frozen development proxy and is retrievable from GitHub, so no HuggingFace access is needed.

```text
python livebench_if_generation_v1/ifbench_to_questions.py --input IFBench_test.jsonl --output dev_questions.jsonl
LIVEBENCH_ROOT=/path/to/LiveBench@8f8e5c3 IFBENCH_TEST_JSONL=/path/to/IFBench_test.jsonl NLTK_REAL_DIR=/path/to/unzipped_nltk_data \
  python -m pytest livebench_if_generation_v1/test_pipeline_preflight.py
```

What the pre-flight verified when it was run (a local mock stands in for the LLM and returns a fixed placeholder; every other stage is real): conversion of all 300 prompts; the generation kit (frozen policy, budget cap, hash-chained provenance); the repo's verified adapter and ID-set preflight (PASS, 300); LiveBench's own scorer with all 58 checkers and **zero scorer exceptions**; deterministic repeat scoring; no prompt text in any stored output. The pinned NLTK artifacts were fetched with git at the project's pinned `nltk_data` commit and their five blob SHAs equal the pins in `LIVEBENCH_IF_HERMETIC_INPUT_BINDING_V1.json`.

Two robustness findings about upstream, handled in the driver rather than hidden: (1) upstream calls `nltk.download('stopwords')` inside functions on every stop-word check and downloads `punkt` at import, which makes a scoring run network-dependent; the driver replaces `nltk.download` with a local-presence check that raises if a resource is missing. (2) upstream's exception handler indexes `turns[0].split('<instructions>')[1]` and would itself crash on prompts without those tags; the driver scores such a question 0 as upstream intends and reports every occurrence (`scorer_exceptions`, exit code 3 unless `--allow-scorer-exceptions`).

## Safety properties (each is tested and mutation-checked)

1. **Budget cap, fail closed.** A worst-case check (`estimated input + max_completion_tokens`) runs before every call; the run stops with exit code 4 rather than exceed `--max-total-tokens` or `--max-neurons-per-utc-day`. A failed attempt is never counted as spend.
2. **Zero spend by construction for Cloudflare.** `--api-style cf-run` refuses to start without both a neuron cap and a price table. `prices_workers_ai_v1.json` records the neuron prices from Cloudflare's pricing page (recomputed against the census in the test). Recommended cap: 9,000 neurons per UTC day (free allocation: 10,000, per account and shared with any other Workers AI use).
3. **Frozen-set protection, explicit and fail closed.** A frozen policy must be chosen: `--frozen-release` (comma-separated exact ISO dates), `--frozen-release-min DATE` (that release and every later one), or `--assert-no-frozen-questions`. A question is frozen if its release matches a rule **or its release date is unknown**. Frozen questions are refused with exit code 3 unless `--authorization` is a JSON file whose `frozen_rule`, questions-file hash, config-file hash and model id all match and which has `execution_authority: true`. The check happens before any network call. Do not create that file yourself: it must come from the project's own machine authorization of the one-shot run. Upstream treats questions released on or after **2025-11-25** as the current IFBench-format set (see below), so `--frozen-release-min 2025-11-25` is the natural rule for the real file.
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
  --prices livebench_if_generation_v1/prices_workers_ai_v1.json --max-neurons-per-utc-day 9000 \
  --assert-no-frozen-questions
#   needs CLOUDFLARE_API_TOKEN as --api-key-env (default BRAIN_GEN_API_KEY) and CLOUDFLARE_ACCOUNT_ID

# keyless alternative (the transport already verified for the AutomationBench gateway; models are NOT pinned):
python livebench_if_generation_v1/generate_responses.py ... --api-style plain \
  --base-url https://text.pollinations.ai/ --model openai-fast --max-total-tokens 2000000 --assert-no-frozen-questions

# 2. Score out_*/model_answers.json with LiveBench's OWN aggregator (not part of this kit):
#    livebench/process_results/instruction_following/utils.py -> ifbench_process_results at upstream
#    LiveBench/LiveBench commit 8f8e5c381a16e3f24257776edd53471fe86f8091. It uses the STRICT check, takes the
#    response from inside <solution>...</solution> when present, and scores each question as
#    0.5 * [all instructions followed] + 0.5 * [fraction of instructions followed]; the leaderboard shows the
#    task-averaged mean x 100. The public runner already carries the hermetic setup
#    (capsules/livebench_if_full_verifier, workflows verify-livebench-if-*).
#    Driver (calls upstream's own function; refuses unless --livebench-root is at the pinned commit and
#    unmodified; stores only ids and scores, never prompts or responses):
python livebench_if_generation_v1/score_livebench_if.py --questions q.jsonl --model-answers out_raw/model_answers.json \
  --livebench-root /path/to/LiveBench@8f8e5c381a16e3f24257776edd53471fe86f8091 --out scores_raw.json
#    It needs the packages upstream imports (pandas, nltk, emoji, syllapy, langdetect, immutabledict, absl-py)
#    and the project's hermetic setup for the two import-time downloads (spaCy is dead code; NLTK punkt).
#    CAUTION: canonical/governance/LIVEBENCH_IF_VERIFIER_BINDING_V1.json declares "prompt-level loose accuracy"
#    as the reported metric. That is the IFBench paper's metric, not LiveBench's leaderboard metric, so a
#    score computed that way is not comparable with the 65.7 bar (see the public-bar receipt, defect finding
#    LIVEBENCH_IF_METRIC_AND_RELEASE_ALIGNMENT).
```

**Dev data.** Upstream code routes IF questions released on or after 2025-11-25 to the new IFBench-format scorer (58 checker types) and older ones to an older IFEval-style path, and the leaderboard scores the current set. So older releases are a poor proxy for the frozen set. The non-frozen dev proxy is IFBench's own public prompts (section above); for LiveBench-format rows the loader's defaults (`question_id`, `turns[0]`, `livebench_release_date`) match the field names used by upstream code, but whether the exported rows carry them was not verified here (HuggingFace is unreachable from the authoring sandbox). Override with `--id-field`, `--prompt-field`, `--release-field` if needed. Illustrative export, **UNTESTED**:

```python
from datasets import load_dataset
ds = load_dataset("livebench/instruction_following", revision="0868379c4b5cf62aeacaf8be4f08fced815c81bb", split="test")
# write JSONL rows with question_id, turns and livebench_release_date; keep the frozen subset OUT of dev files
```

## Known limits and unverified points

- Cloudflare response shapes: both documented shapes (OpenAI-style `choices`/`usage` and `response`/`usage`) are parsed and tested against a mock; not verified live.
- Reasoning models count reasoning inside completion tokens: tune `max_completion_tokens` after a small pilot, because a budget exhausted by reasoning truncates the answer.
- Whether the candidate Workers AI models require the Workers Paid plan was not stated on the model pages read. If they do, the free-allocation route is unavailable and the cap here would be the only thing preventing spend.
- The registry labels the bar 'LiveBench 2026-06-25', but LiveBench's changelog at the pinned upstream commit has no such release (latest entry 2026-01-08; IF tasks last refreshed 2025-11-25). Comparability depends on the pinned dataset revision holding the same question set the leaderboard scored; check this from metadata (`livebench_release_date`) before any frozen run.
- The `plain` transport mirrors the request shape already verified for the AutomationBench gateway; its models are not pinned and report no usage (usage is estimated at 3 characters per token).
- Scope: a raw open model that already exceeds the bar would be an external capability provider under General Cognition Substrate Law V3 unless the Brain configuration measurably adds value. This kit makes that ablation runnable; it does not perform it.
