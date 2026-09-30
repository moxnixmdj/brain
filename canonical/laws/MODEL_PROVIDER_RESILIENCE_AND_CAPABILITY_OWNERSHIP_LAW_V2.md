# MODEL PROVIDER RESILIENCE AND CAPABILITY OWNERSHIP LAW V2

Status: CANONICAL / MANDATORY

Supersedes:
- canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md

Authority:
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_OWNERSHIP_MISSION_LOCK_V5.md

## Core law

Project Brain does not impose model-independence as a terminal requirement.

A model, solver, tool, runtime, library, algorithm, or composition may be part of an acquired capability when the final configured Brain capability meets or exceeds the Opus 5.5 useful-capability bar and is durably packaged for reuse.

The distinction is not "model versus non-model."

The distinction is:
- external/JIT knowledge; versus
- permanently configured Brain capability.

## Capability ownership with model components

If a model is part of a capability:
- its role must be explicit;
- configuration and routing must be saved;
- provider/artifact/version dependencies must be declared;
- invocation and verification contracts must be durable;
- failure/recovery behavior must be recorded;
- capability credit belongs to the configured Brain system only when the whole configured capability meets the target bar.

A one-off model call discovered during a task is not permanent capability ownership.

## Resilience

Provider independence remains desirable for robustness, but it is an optimization/reliability dimension, not a categorical prohibition on model cognition.

Where practical, preserve fallbacks or portable configuration so loss of one provider does not erase Brain's capability. If no equivalent fallback exists, record the dependency honestly rather than pretending the capability is model-independent.

## Knowledge boundary

Using a model to retrieve or supply transient factual knowledge is still external/JIT knowledge unless that behavior is part of a durably configured capability package.

## Forbidden claims

Do not:
- reject a faster sufficient Opus-5.5-or-better capability merely because it uses a model;
- claim model-independence when the configured route depends on a model;
- count an unconfigured one-off external model response as permanent capability ownership.
