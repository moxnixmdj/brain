# Xapian downstream interface audit

Date: 2026-09-29 UTC  
Status: reproduced interface defects; evidence preservation only  
Scope: `TOOL_DISCOVERY_SELECTION_AND_LEARNING` prerequisite evidence for the current `MULTI_TOOL_ORCHESTRATION_AND_PLANNING` frontier  
Session: `c5683b191923`

## Decision

Keep the first authoritative HELDOUT-005 discovery PASS intact. It proves the frozen supplier-retrieval gate; it does not prove acquisition, contract learning, execution, or independent verification.

Two existing consumer filters reject the new route's candidate representation. The acquisition-source defect corroborates the findings already recorded in PR107/PR110. The independent-verifier matched-term defect is an additional downstream blocker that survives a source-label-only fix.

This document preserves observed evidence. It neither changes the selected frontier nor authorizes a runtime repair or a held-out replay.

## Exact provenance

The producer was retrieved from the exact tested PR89 commit `48c53d0f1b2474c334fcfbb87bd6946c1dc850bb`. Consumers were retrieved from main `33d607338ebf300b00465ddb40a911bf87c3bc02`. Before preservation, the repository trees at `db298bb4363266ef9e91ec9ec114b5f1c7bcf1fd` and `d22f5012df9a32e073e0bed8fe7da7af4a60441b` confirmed that all three relevant blobs were still identical.

| Component | Git blob |
| --- | --- |
| `canonical/runtime/capability_discovery.py` | `b9e7423ab24bf2da98869b02d782e791a779892a` |
| `canonical/runtime/auto_apt_cli_acquisition.py` | `786f7de7df853cfaec2826f9471942b001e7eadc` |
| `canonical/runtime/verify_pending_cli_binding.py` | `8ec4da92080e885a15266389c0318688e6408d43` |
| `canonical/runtime/cli_contract_inference.py` | `009c3c45040178844d84eaa15b0d47ca2e1f259f` |
| `canonical/runtime/apt_cli_probe.py` | `3f3a8f6a0154e1ed3f87fc97b99840598297b119` |
| `canonical/runtime/goal_compiler.py` | `195d5dd5f4fabb8a897fb6407433e691a8fdaf26` |

Local bytes were checked using Git's blob hash definition before execution. All six comparisons matched.

## Reproduced findings

| Boundary | Actual producer field | Consumer requirement | Observed result |
| --- | --- | --- | --- |
| Discovery → acquisition | `discovery_source = APT_FULL_METADATA_XAPIAN` | `_viable_candidates` admits only `APT_CATALOG` | `NO_LOW_FRICTION_APT_CLI_CANDIDATE` |
| Discovery → independent verifier | `matched_terms = []` for every full-metadata candidate | `_acquire_and_run_semantic_verifier` skips candidates with fewer than two terms | `SEMANTIC_VERIFIER_ACQUISITION_FAILED:[]`; zero probe calls |

The first reproduction used the real producer function with a deterministic synthetic search match of weight 100 and a verified executable-owner fixture. Version, hash, cost, secret and friction fields satisfied the consumer's other checks. Changing only that in-memory record's source label to the legacy value admitted the candidate. This isolates source admission; it is not a proposed repair.

The second reproduction executed the exact independent-verifier function extracted from its source AST. The same new-route candidate produced zero probe calls. Changing only its in-memory matched-term list to two fixture terms reached the probe stub exactly once. The stub stopped before any installation or binary execution. This isolates the matched-term filter; it does not justify fabricating matched terms in production.

### Additional risk, not a measured real-task failure

The acquisition filter also requires legacy `score >= 12`. The new route supplies raw Xapian match weights. A source-normalized synthetic score of 1 is rejected. This demonstrates the uncalibrated interface assumption; it does not establish that any actual HELDOUT-005 candidate had a score below 12.

The federated sorter recognizes `APT_CATALOG` and `PYPI` as preferred local sources but does not include the new full-metadata source in that priority tier. This is visible in source; this audit did not measure an actual recall loss from the ordering.

## Existing components and remaining limits

The Brain already has APT probing, contract inference, pending bindings, producer execution, independent-verifier acquisition and promotion/replay. Rebuilding that pipeline is unnecessary to diagnose this interface.

Even after candidate admission is corrected, the current APT contract compiler/binder remains limited to the `text + output_path` shape. The semantic-verifier help recognizer is specifically a barcode/image decoding shape. Their broader sufficiency is not established by supplier discovery.

The preserved orthogonal portfolio already records failures in generic invocation-contract shape and output coverage. Those results remain relevant; this audit does not spend their probes or authorize their replay.

## Execution limits and outcome

- One pure synthetic interface-diagnosis invocation completed with exit code 0.
- No held-out cases, package installations or candidate binaries were executed.
- No runtime source was changed.
- No external network call was needed during the diagnosis.
- No user-laptop execution, Val Town operation or incremental cash spend occurred.
- Xapian search-match generation was stubbed; retrieval quality and latency were not retested.
- The independent verifier was executed as the original function AST with controlled dependencies; the whole runtime was not launched.
- Passing diagnostic assertions mean the incompatibilities were reproduced, not that the capability passed.

Observed diagnostic values:

```json
{
  "classification": "REPRODUCED_INTERFACE_INCOMPATIBILITY_NO_HELDOUT_EXECUTION",
  "source_gate_error": "NO_LOW_FRICTION_APT_CLI_CANDIDATE",
  "source_only_control": "ADMITTED",
  "semantic_verifier_error": "SEMANTIC_VERIFIER_ACQUISITION_FAILED:[]",
  "semantic_verifier_probe_calls": 0,
  "two_matched_terms_only_control_probe_calls": 1,
  "conditional_score_1_error": "NO_LOW_FRICTION_APT_CLI_CANDIDATE",
  "heldout_cases_executed": 0,
  "runtime_mutations": 0,
  "incremental_spend_usd": 0
}
```

## Consequence for the active frontier

Orchestration work may reuse previously verified bound capabilities. It must not infer that arbitrary newly discovered APT tools can already enter a complete verified learning/execution loop.

Preserve both downstream interface findings when the parent frontier is next reconciled. Any later repair should address the producer-consumer contract explicitly, retain source provenance and evidence requirements, and test downstream admission with non-held-out fixtures. Do not relabel provenance or fabricate term matches merely to pass existing filters.

No claim of end-to-end tool-learning obsolescence or frontier-model parity follows from this audit.

## Exact reproduction used

Place the following script at the repository root alongside `canonical/`, using the exact source blobs above. It is a diagnosis, not an acceptance gate. This is the script already executed for this record; preserving it is not an instruction to rerun any spent case.

```python
#!/usr/bin/env python3
"""Pure integration diagnosis. No held-out cases, installs, network, or runtime writes."""
import ast, copy, hashlib, importlib, json, pathlib, sys, types
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = ROOT / "canonical/runtime"
sys.path.insert(0, str(RUNTIME))
discovery = importlib.import_module("capability_discovery")
acquisition = importlib.import_module("auto_apt_cli_acquisition")

class Document:
    def get_data(self):
        return b"opaque-fixture-cli"

class Match:
    document = Document()
    weight = 100.0

class Enquire:
    def __init__(self, db):
        pass
    def set_query(self, query):
        pass
    def get_mset(self, start, size):
        return [Match()]

state = {
    "module": types.SimpleNamespace(Enquire=Enquire),
    "query_parser": types.SimpleNamespace(parse_query=lambda query: query),
    "db": object(),
    "records": {"opaque-fixture-cli": {
        "name": "opaque-fixture-cli",
        "description": "A neutral transformation utility",
        "version": "1.0",
        "archive_sha256": "a" * 64,
        "tags": "interface::commandline, role::program",
    }},
}
with mock.patch.object(discovery, "_apt_xapian_index", return_value=state), \
     mock.patch.object(discovery, "_apt_contents_executable_owners",
                       return_value={"opaque-fixture-cli": ["/usr/bin/opaque-fixture-cli"]}), \
     mock.patch.object(discovery.subprocess, "run", side_effect=AssertionError("NO_PROCESS_ALLOWED")), \
     mock.patch.object(discovery.urllib.request, "urlopen", side_effect=AssertionError("NO_NETWORK_ALLOWED")):
    result = discovery._search_apt_packages_full_metadata("neutral transformation", limit=12)

assert result["candidates"][0]["discovery_source"] == "APT_FULL_METADATA_XAPIAN"
assert result["candidates"][0]["matched_terms"] == []
try:
    acquisition._viable_candidates(result, "neutral transformation")
except acquisition.AutoAcquisitionFailure as exc:
    source_failure = str(exc)
else:
    raise AssertionError("New route unexpectedly admitted")

control = copy.deepcopy(result)
control["candidates"][0]["discovery_source"] = "APT_CATALOG"
admitted = acquisition._viable_candidates(control, "neutral transformation")
assert len(admitted) == 1

# Execute the exact verifier function via AST extraction so importing the
# whole runtime cannot perform unrelated initialization or need more modules.
tree = ast.parse((RUNTIME / "verify_pending_cli_binding.py").read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "_acquire_and_run_semantic_verifier")
module = ast.Module(body=[function], type_ignores=[])
attempts = []
class ProbeReached(Exception):
    pass
def probe(*args):
    attempts.append(args[:3])
    raise ProbeReached("fixture endpoint reached; never installed")
env = {
    "json": json, "re": importlib.import_module("re"), "ROOT": ROOT,
    "capability_discovery": types.SimpleNamespace(search_apt_packages=lambda *a, **k: result),
    "_semantic_verifier_query": lambda goal: "neutral verifier",
    "apt_cli_probe": types.SimpleNamespace(probe=probe),
}
exec(compile(module, "exact_verifier_function", "exec"), env)
pending = {
    "goal": "neutral transformation",
    "selected_supplier": {"name": "different-producer"},
    "semantic_verification": {"expected_text": "neutral-fixture"},
}
try:
    env["_acquire_and_run_semantic_verifier"](pending, "/unused/fixture")
except RuntimeError as exc:
    verifier_failure = str(exc)
else:
    raise AssertionError("Verifier unexpectedly succeeded")
assert attempts == []
original = result["candidates"][0]["matched_terms"]
result["candidates"][0]["matched_terms"] = ["neutral", "transformation"]
try:
    env["_acquire_and_run_semantic_verifier"](pending, "/unused/fixture")
except RuntimeError:
    pass
assert len(attempts) == 1
result["candidates"][0]["matched_terms"] = original

# Conditional legacy-score incompatibility, distinct from the proven source bug.
low_score = copy.deepcopy(control)
low_score["candidates"][0]["score"] = 1.0
try:
    acquisition._viable_candidates(low_score, "neutral transformation")
except acquisition.AutoAcquisitionFailure as exc:
    low_score_result = str(exc)
else:
    raise AssertionError("Legacy threshold unexpectedly absent")

report = {
    "schema": "PROJECT_BRAIN_PR89_READ_ONLY_INTEGRATION_DELTA_V1",
    "classification": "REPRODUCED_INTERFACE_INCOMPATIBILITY_NO_HELDOUT_EXECUTION",
    "tested_discovery_blob": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "inherited_main_commit": "33d607338ebf300b00465ddb40a911bf87c3bc02",
    "source_gate": {
        "new_source": result["candidates"][0]["discovery_source"],
        "observed_error": source_failure,
        "same_record_only_source_changed_to_APT_CATALOG": "ADMITTED",
        "interpretation": "All candidates from the full-metadata route are rejected by the inherited acquisition source filter.",
    },
    "semantic_verifier_gate": {
        "new_route_matched_terms": [],
        "observed_error": verifier_failure,
        "probe_calls": 0,
        "same_record_only_two_terms_added_probe_calls": len(attempts),
        "interpretation": "All candidates from the full-metadata route are skipped by the inherited verifier matched-term filter.",
    },
    "conditional_risk": {
        "legacy_score_threshold": 12,
        "source_normalized_fixture_score_1": low_score_result,
        "actual_heldout_BM25_scores_examined": False,
        "interpretation": "BM25 scores and legacy lexical scores lack an established shared threshold; real-case loss not measured here.",
    },
    "network_calls": 0,
    "package_installs": 0,
    "candidate_binaries_executed": 0,
    "heldout_cases_executed": 0,
    "runtime_mutations": 0,
    "incremental_spend_usd": 0,
    "scope": "Pure producer-consumer interface diagnosis; neither candidate performance nor end-to-end capability acceptance.",
}
print(json.dumps(report, indent=2))
```
