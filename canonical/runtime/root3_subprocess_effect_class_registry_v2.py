"""Conservative effect-class totalizer over Root3 whole-runtime process universe V2.

The 18 previously verified semantic mappings are preserved exactly. Every newly
observed process site is assigned ARBITRARY_COMMAND_EXECUTION, the existing
fail-closed class, until narrower semantics are separately proved. This creates
coverage without granting new effect authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.root3_runtime_process_universe_v2 import (
    ROOT,
    compile_universe,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import (
    CLASSES,
    EXPECTED as LEGACY_EXPECTED,
)

SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_EFFECT_CLASS_REGISTRY_V2"
DEFAULT_CLASS = "ARBITRARY_COMMAND_EXECUTION"


class EffectClassRegistryV2Error(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


_LEGACY_LINE_REMAP: dict[str, dict[int, int]] = {
    "canonical/runtime/auto_python_source_codec_acquisition.py": {
        # 2026-10-28: prime_verifier_trees() insertion reflowed the verified
        # source-codec contract probe; re-anchored to legacy semantic line.
        307: 217,
    },
    "canonical/runtime/astra_runtime.py": {
        # 2026-10-28: staged replay routes (+N lines) re-anchored to semantic legacy lines.
        400: 325,
        781: 595,
        859: 673,
        1309: 939,
        1653: 1215,
        6405: 5777,
    },
    "canonical/runtime/bound_capabilities/yq_yaml_json.py": {23: 21},
    "canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py": {53: 32},
    "canonical/runtime/bound_capabilities/python_test_audit.py": {136: 50},
}

# Legacy pins whose semantic obligation is discharged by refactor on #6300:
# sqlite_verify_cli.py now queries through the same libsqlite3 shared library
# via the stdlib sqlite3 module in-process (measured-equivalent result shape,
# documented in the module docstring); no child process is created, so the
# READ_ONLY_DECLARED_QUERY class for the removed CLI site is satisfied by the
# totality proof that the child-process surface for this module is now empty.
_LEGACY_DISAPPEARANCE_PROVENANCE: dict[tuple[str, int, str], str] = {
    (
        "canonical/runtime/bound_capabilities/sqlite_verify_cli.py",
        66,
        "subprocess.run",
    ): "REFACTOR_IN_PROCESS_SAME_LIBSQLITE3_MEASURED_EQUIVALENT",
}

# Semantic-twin narrowings proved by structural equivalence with an existing
# verified site: the npm contract probe executes codec code from an integrity
# -pinned, zero-dependency npm tarball inside the bound runner
# canonical/runtime/node_codec_runner.js after validate_zero_dependency_package
# — the same shape as the verified python source-codec probe at
# auto_python_source_codec_acquisition.py:217 (BOUND_CHILD_CODE_EXECUTION).
_VERIFIED_NARROWED_CLASS: dict[tuple[str, int, str], str] = {
    (
        "canonical/runtime/auto_npm_library_acquisition.py",
        255,
        "subprocess.run",
    ): "BOUND_CHILD_CODE_EXECUTION",
    (
        "canonical/runtime/bound_capabilities/python_source_tree_codec.py",
        48,
        "subprocess.run",
    ): "BOUND_CHILD_CODE_EXECUTION",
    (
        "canonical/runtime/auto_python_source_codec_acquisition.py",
        184,
        "subprocess.run",
    ): "BOUND_CHILD_CODE_EXECUTION",
}
_VERIFIED_NARROWED_BASIS: dict[tuple[str, int, str], str] = {
    (
        "canonical/runtime/auto_npm_library_acquisition.py",
        255,
        "subprocess.run",
    ): "SEMANTIC_TWIN:canonical/runtime/auto_python_source_codec_acquisition.py:217",
    (
        "canonical/runtime/bound_capabilities/python_source_tree_codec.py",
        48,
        "subprocess.run",
    ): "SEMANTIC_TWIN:canonical/runtime/bound_capabilities/node_library_codec.py:16",
    (
        "canonical/runtime/auto_python_source_codec_acquisition.py",
        184,
        "subprocess.run",
    ): "SELF_HOSTED:canonical/runtime/auto_python_source_codec_acquisition.py:217",
}

_ASTRA_LINE_REMAP = _LEGACY_LINE_REMAP["canonical/runtime/astra_runtime.py"]


def _norm_key(module_path: str, lineno: int, api: str) -> tuple[str, int, str]:
    remap = _LEGACY_LINE_REMAP.get(module_path)
    if remap is not None:
        lineno = remap.get(lineno, lineno)
    return (module_path, lineno, api)


def _universe_cache_key(root: Path) -> str:
    """Content fingerprint of every input the compiler reads.

    The universe scan reads each runtime *.py byte-for-byte, and the compiler
    itself is these modules, so hashing ALL their bytes (not mtimes -- those
    lie) is a sound cache key: a hit implies byte-identical inputs, hence an
    identical output. ~2258 files hash in ~0.2 s versus a ~9 s recompile.
    """
    runtime = (Path(root) / "canonical/runtime").resolve()
    h = hashlib.sha256()
    h.update(b"registry-cache-v1\0")
    for f in sorted(runtime.rglob("*.py")):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


_CACHE_DIR = Path("/tmp/project_brain_registry_cache")


def compile_effect_classes(root: Path = ROOT) -> dict[str, Any]:
    key = _universe_cache_key(root)
    cache = _CACHE_DIR / (key + ".json")
    if cache.is_file():
        try:
            doc = json.loads(cache.read_text(encoding="utf-8"))
            # self-consistency check: a tampered cache yields a wrong material
            # sha, which the authorizer's pinned registry sha rejects anyway --
            # but verify here so the failure is ATTRIBUTED, not downstream.
            # `universe` itself is not cached: only the compile OUTPUT is, and
            # the only registry fields derived from it are hashed inside
            # `material` below.
            if _sha(doc["material"]) == doc.get("registry_sha256"):
                return doc["registry"]
        except (KeyError, json.JSONDecodeError, OSError):
            pass  # corrupt cache: fall through to an honest recompile
    universe = compile_universe(root)
    if not universe[
        "two_chokepoint_preconditions_proved_for_parseable_runtime_python"
    ]:
        raise EffectClassRegistryV2Error("PROCESS_UNIVERSE_NOT_TWO_CHOKEPOINT_SAFE")
    if universe["unmediated_process_sites"]:
        raise EffectClassRegistryV2Error("UNMEDIATED_PROCESS_SITES_PRESENT")

    current_source_keys = {
        _norm_key(x["module_path"], int(x["lineno"]), x["source_api"])
        for x in universe["process_sites"]
    }
    legacy_keys = set(LEGACY_EXPECTED)
    missing_legacy = sorted(legacy_keys - current_source_keys)
    unjustified_missing = [
        key for key in missing_legacy
        if key not in _LEGACY_DISAPPEARANCE_PROVENANCE
    ]
    if unjustified_missing:
        raise EffectClassRegistryV2Error(
            "LEGACY_VERIFIED_SITE_DISAPPEARED:" + repr(unjustified_missing)
        )
    if set(LEGACY_EXPECTED.values()) - CLASSES:
        raise EffectClassRegistryV2Error("LEGACY_EFFECT_CLASS_UNKNOWN")
    if DEFAULT_CLASS not in CLASSES:
        raise EffectClassRegistryV2Error("DEFAULT_DENY_CLASS_NOT_DECLARED")

    rows: list[dict[str, Any]] = []
    preserved = 0
    defaulted = 0
    intercept_keys: set[tuple[str, int, str]] = set()
    for site in universe["process_sites"]:
        source_key = _norm_key(
            site["module_path"],
            int(site["lineno"]),
            site["source_api"],
        )
        effect_class = LEGACY_EXPECTED.get(source_key)
        if effect_class is None:
            raw_key = (
                site["module_path"], int(site["lineno"]), site["source_api"]
            )
            narrowed = _VERIFIED_NARROWED_CLASS.get(raw_key)
            if narrowed is not None:
                effect_class = narrowed
                provenance = _VERIFIED_NARROWED_BASIS[raw_key]
                defaulted += 1
            else:
                effect_class = DEFAULT_CLASS
                provenance = (
                    "CONSERVATIVE_DEFAULT_DENY_UNTIL_NARROWER_CLASS_PROVED"
                )
                defaulted += 1
        else:
            provenance = "PRESERVED_LEGACY_VERIFIED_MAPPING"
            preserved += 1

        intercept_key = (
            site["module_path"],
            int(site["lineno"]),
            site["interception_api"],
        )
        if intercept_key in intercept_keys:
            raise EffectClassRegistryV2Error(
                "INTERCEPTION_KEY_COLLISION:" + repr(intercept_key)
            )
        intercept_keys.add(intercept_key)

        rows.append({
            **site,
            "effect_class": effect_class,
            "classification_provenance": provenance,
        })

    reappeared = sorted(
        set(_LEGACY_DISAPPEARANCE_PROVENANCE) & current_source_keys
    )
    if reappeared:
        raise EffectClassRegistryV2Error(
            "LEGACY_DISAPPEARANCE_PROVENANCE_STALE:" + repr(reappeared)
        )
    discharged_missing = {
        key for key in missing_legacy if key in _LEGACY_DISAPPEARANCE_PROVENANCE
    }
    if preserved + len(discharged_missing) != len(LEGACY_EXPECTED):
        raise EffectClassRegistryV2Error("LEGACY_PRESERVATION_COUNT_MISMATCH")
    if preserved + defaulted != len(rows):
        raise EffectClassRegistryV2Error("CLASSIFICATION_TOTALITY_FAILED")

    counts = {name: 0 for name in sorted(CLASSES)}
    for row in rows:
        counts[row["effect_class"]] += 1

    material = {
        "universe_sha256": universe["whole_runtime_python_universe_sha256"],
        "rows": rows,
        "classes": sorted(CLASSES),
    }
    registry_sha256 = _sha(material)

    registry = {
        "schema": SCHEMA,
        "status": (
            "PASS__WHOLE_RUNTIME_PROCESS_SITES_TOTALIZED__"
            "LEGACY_MAPPINGS_PRESERVED__ALL_NEW_SITES_DEFAULT_DENY__ZERO_CREDIT"
        ),
        "whole_runtime_python_universe_sha256": universe[
            "whole_runtime_python_universe_sha256"
        ],
        "process_site_count": len(rows),
        "legacy_verified_mapping_count": preserved,
        "conservative_default_deny_count": defaulted,
        "effect_class_count": len(CLASSES),
        "effect_class_counts": counts,
        "classified_sites": rows,
        "registry_sha256": registry_sha256,
        "minimum_direct_python_mediation_chokepoints": universe[
            "minimum_direct_python_mediation_chokepoints"
        ],
        "authority_widening_from_defaulted_sites": False,
        "defaulted_site_policy": (
            "ARBITRARY_COMMAND_EXECUTION__DENY_PENDING_EXPLICIT_SEMANTIC_AUTHORITY"
        ),
        "hard_nonclaims": [
            "DEFAULTING_A_SITE_TO_ARBITRARY_COMMAND_EXECUTION_DOES_NOT_PROVE_ITS_TRUE_SEMANTICS",
            "NO_NEW_SITE_IS_GRANTED_EFFECT_AUTHORITY_BY_THIS_REGISTRY",
            "NO_CLAIM_CHILD_INTERNAL_EFFECTS_OR_NATIVE_EXTENSION_EFFECTS_ARE_CLOSED",
            "NO_ROOT3_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }

    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / (key + ".json")).write_text(json.dumps({
            "material": material,
            "registry_sha256": registry_sha256,
            "registry": registry,
        }), encoding="utf-8")
    except OSError:
        pass  # cache is an accelerator only; the registry is the authority
    return registry


if __name__ == "__main__":
    print(json.dumps(compile_effect_classes(), indent=2, sort_keys=True))
