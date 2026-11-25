# Hidden capability surfacing

Three files, three jobs. Nothing here promotes anything.

| file | job |
| --- | --- |
| `canonical/tools/harvest_hidden_capabilities_v1.py` | census: classify every module in the tree by invocation shape, subtract everything already declared, emit the remainder |
| `canonical/tools/harvest_capability_receipts_v1.py` | drive candidates through the receipt lane and stage the results in the projection (additive) |
| `canonical/runtime/harvested_capability_runtime_v1.py` | execute one discovered surface by id, through the lane, and return its receipt |

## Why the registries could not see them

`capability_receipt_lane_v1.discover()` — the only producer of execution receipts —
walks the **registries**. A candidate must own a row in the bound or extended
registry before it can be probed. So a module that was written, documented and
measured but never declared is invisible to the receipt lane, and the compiled
model lists it (when it lists it at all) as `SOURCE_ADDRESSABLE_MODULE` with
`capability: false`.

`source_index` in the compiled model walks only `canonical/runtime`. On this
checkout **506 of the 626 discovered surfaces live outside it** —
`canonical/tools` 322, `canonical/swe_kernel` 94, `execution_guard` 25, plus 46
at the repository root — so for most of them the model had no row at all.

## What the census measures

* invocation shape, read from the AST: `contract` (`run(args, root) -> dict`) or
  `cli` (a `main`/`__main__` entry);
* declaration, read from the live artefacts: registry ids, registry source paths,
  and the capability id a module names in its own docstring header. A module
  declared by id but never linked by path is **not** hidden — `adapter_module`
  resolves it — and counting it would inflate the number;
* the module's own declared contract: `capability_id`, `inputs`, `result_fields`.

## What execution actually yields

Blind execution is not the mechanism, and the census proves it rather than
assuming it. On a sample of 80 contract surfaces called with `{}`:

```
  7  returned a dict
 73  refused with a typed reason -- MISSING_REQUIRED_ARGUMENTS,
     PATH_INVALID:None, INPUT_FILE_MISSING, ORACLE_TARGET_MISSING,
     BROWSER_URL_INVALID, {"capability": ..., "error": true, ...}
```

Those are not broken modules. They are complete adapters that validate their
inputs, which is why the runtime takes `args` from the caller and refuses
(`HARVESTED_SURFACE_DID_NOT_RUN__NO_STRUCTURED_RESULT`) instead of inventing
them. With their documented inputs they execute: `jq_query.py` answered a real
jq query and returned `output_verified: true`; `concrete_execution_oracle.py`
ran and reported `NO_POSTCONDITION_PARSED` for a snippet with no postcondition.

## How to use it

```bash
python3 canonical/tools/harvest_hidden_capabilities_v1.py          # census JSON
python3 canonical/runtime/harvested_capability_runtime_v1.py --list
python3 canonical/runtime/harvested_capability_runtime_v1.py \
  --capability-id canonical.runtime.bound_capabilities.jq_query.hidden.v1 \
  --args-json '{"input_path":"x.json","filter":".a","output_path":"out.json"}'
```

## The line this does not cross

A successful call writes a **producer** receipt. The loader admits a capability
only when a different identity re-runs it and the run reference carries signed
GitHub OIDC claims (`capability-receipt-verification.yml`). This code path has no
ability to flip a status, write a registry, or set `admitted: true`; the verifier
checks that every harvested row still says `admitted: false`, that no harvested id
or path collides with an admitted capability, and that every row's `sha256` still
matches its file.
