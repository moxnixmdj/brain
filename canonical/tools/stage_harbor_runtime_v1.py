"""Build the cold Harbor producer mount, not an archive of the research repo.

The cycle route needs no registry/knowledge rows. Give open_model a separately
identified empty-store artifact; never mount the full artifact (it indexes
research results), .git, tests, evaluation data, caches or CI credentials.
Run from the Brain checkout: python -m canonical.tools.stage_harbor_runtime_v1 DEST
Stdout is a reproducible manifest for the *host* job, not a capability receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from canonical.runtime.brain_unified_model_v1 import DEFAULT_ARTIFACT, SCHEMA, artifact_digest

ROOT = Path(__file__).resolve().parents[2]
# Code used in the proposal, discovery, Python repair and patch-capture phases.
# Host Harbor adapters, other agent backends and optional solver portfolios do
# not belong in the producer. New dependencies must be reviewed at this seam.
SOURCES = (
    'canonical/runtime/brain_unified_model_v1.py',
    'canonical/runtime/harbor_command_policy.py',
    'canonical/runtime/harbor_container_solver_worker_v1.py',
    'canonical/runtime/harbor_process_cleanup_worker_v1.py',
    'canonical/runtime/harbor_pro_git_capture_v1.py',
    'canonical/runtime/tree_sitter_swe_kernel_v1.py',
    'canonical/swe_kernel/__init__.py',
    'canonical/swe_kernel/harbor_epistemic_controller_v1.py',
    'canonical/swe_kernel/harbor_in_container_runner_v1.py',
    'canonical/swe_kernel/causal_swe_repair_v1.py',
    'canonical/swe_kernel/first_principles_mental_cegis_v1.py',
    'canonical/swe_kernel/incremental_semantic_graph_v1.py',
    'canonical/swe_kernel/petri_cow_splicing_engine_v1.py',
    'canonical/swe_kernel/consistency_vs_equivalence_v1.py',
    'canonical/swe_kernel/effect_contract_composition_v1.py',
)


def stage(destination: Path, *, source_root: Path = ROOT) -> dict[str, str]:
    source_root = source_root.resolve(strict=True)
    destination.mkdir(exist_ok=False)  # Never inherit a previous run's memory or files.
    manifest: dict[str, str] = {}

    def put(name: str, data: bytes) -> None:
        out = destination / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        manifest[name] = hashlib.sha256(data).hexdigest()

    for name in SOURCES:
        source = source_root / name
        if source.resolve(strict=True) != source or not source.is_file():
            raise ValueError(f'not a regular source in the checkout: {name}')
        put(name, source.read_bytes())
    artifact = {'schema': SCHEMA, 'model_id': 'brain-harbor-cold', 'model_version': 1,
                'knowledge': [], 'skills': [], 'source_manifest_sha256': artifact_digest(manifest)}
    artifact['digest'] = {'value': artifact_digest(artifact)}
    put(DEFAULT_ARTIFACT, (json.dumps(artifact, sort_keys=True) + '\n').encode())
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    print(json.dumps(stage(parser.parse_args().destination), indent=2, sort_keys=True))
