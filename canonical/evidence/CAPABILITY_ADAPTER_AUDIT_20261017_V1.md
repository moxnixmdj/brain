# Capability adapter audit — 2026-10-17

Every one of the 68 bound capabilities was tested by actually importing its
adapter module and checking for a `run` entrypoint. Not a declaration read —
an import.

## Result

```
total 68 | RUNNABLE 64 | NOT RUNNABLE 4
```

| Capability | Declared adapter |
|---|---|
| `knowledge.consistency.assess` | `runtime_native_action` |
| `knowledge.json.fetch.external` | `runtime_native_action` |
| `knowledge.status.assert` | `runtime_native_action` |
| `knowledge.support.materialize` | `runtime_native_action` |

## The finding

**All four broken capabilities are the entire `knowledge.*` family.** The whole
declared Knowledge term points at one module, `runtime_native_action`, which
does not exist anywhere in the repository.

This is the precise reason the Knowledge term never ran. It was never a
network limitation and never a design problem. The term's entry point was
wired to a module that was never written.

## Two false alarms caught before reporting

The first pass reported **14** broken. That number was wrong twice over:

1. Ten of the fourteen raise `ModuleNotFoundError` for a **nested dependency**
   (`PIL`, `numpy`, `sympy`), not for the adapter. The adapter files exist and
   are fine. Importing `chart_raster_scene_graph_v1` fails on `import PIL`
   inside it. Attributing that to the adapter would have been a false defect
   report.
2. Those ten were then further confused by testing with the system `python3`
   while packages had been installed into the venv. Re-run against the venv
   interpreter, ten became zero.

`64/68` is the number after both corrections. `14` would have been wrong, and
so would `54`.

## Method

```
for cid, entry in registry.items():
    mod = importlib.import_module(entry["adapter_module"])
    runnable = hasattr(mod, "run")
```

Packages installed to settle the environment question: numpy, pillow, sympy.
No repository file was modified by this audit.

## Consequence

The Knowledge term has a working neighbour: `http.json.fetch_from_state`,
backed by `canonical/runtime/bound_capabilities/http_json_fetch.py`, which
executed a live fetch with provenance (see
`JIT_KNOWLEDGE_TERM_LIVE_20261017_V1.md`).

The four `knowledge.*` entries should either be repointed to real adapters or
`runtime_native_action` must be written. Under
`underlying_capability_invention: false` the preferred route is repointing,
not authoring new machinery.
