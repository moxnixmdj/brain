"""Finite native-extension risk classifier for current Root3 C1 capability surface.

The classifier intentionally distinguishes:
1. definite/reachable in-process native extension surfaces;
2. artifacts that are pure-wheel/architecture-independent at the packaging layer
   but still require source-level no-native-loader proof;
3. dependencies already executed through child/system-tool processes.

This is proof compression only. It grants no safety or acceptance credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_NATIVE_EXTENSION_SURFACE_OUTPUT_V1"
REGISTRY_SCHEMA="PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1"

# Exact current Ubuntu/PyPI facts, source-bound in the governance candidate.
APT_IN_PROCESS_NATIVE_REACHABLE={
    "docx.document.create_from_json_record":{
        "package":"python3-docx",
        "native_dependency":"python3-lxml",
        "adapter_module":"docx_report_from_json",
    },
    "docx.document.create.python_docx":{
        "package":"python3-docx",
        "native_dependency":"python3-lxml",
        "adapter_module":"python_document_builder",
    },
    "xlsx.table.verify_against_json_records":{
        "package":"python3-openpyxl",
        "native_dependency":"python3-lxml",
        "adapter_module":"xlsx_verify_openpyxl",
    },
}

EXPECTED_PYPI_NATIVE_WHEEL={
    "auto.pypi.msgpack":
        "msgpack-1.2.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl",
}

EXPECTED_PURE_WHEEL_CAPS={
    "auto.pypi.bson-modern",
    "pdf.extract.text.pypdf",
    "math.numeric_expression.sympy",
}

EXPECTED_ARCH_ALL_APT_PYTHON_CAPS={
    "xlsx.table.create_from_json_records",
}


class NativeSurfaceError(ValueError):
    pass


def _cap(registry: dict[str,Any], cid: str) -> dict[str,Any]:
    entry=(registry.get("capabilities") or {}).get(cid)
    if not isinstance(entry,dict):
        raise NativeSurfaceError("CAPABILITY_MISSING:"+cid)
    return entry


def classify(registry_path: str | Path) -> dict[str,Any]:
    p=Path(registry_path)
    registry=json.loads(p.read_text(encoding="utf-8"))
    if registry.get("schema")!=REGISTRY_SCHEMA:
        raise NativeSurfaceError("REGISTRY_SCHEMA_INVALID")

    definite=[]

    for cid, expected in EXPECTED_PYPI_NATIVE_WHEEL.items():
        entry=_cap(registry,cid)
        source=entry.get("source") or {}
        if source.get("type")!="pypi":
            raise NativeSurfaceError("PYPI_TYPE_DRIFT:"+cid)
        if source.get("wheel_filename")!=expected:
            raise NativeSurfaceError("PYPI_WHEEL_DRIFT:"+cid)
        definite.append({
            "capability_id":cid,
            "adapter_module":entry.get("adapter_module"),
            "reason":"PLATFORM_SPECIFIC_CPYTHON_WHEEL_IMPORTED_IN_PROCESS",
            "artifact":expected,
            "collapse_route":"EXECUTE_ADAPTER_IN_ISOLATED_CHILD_PROCESS",
        })

    for cid,fact in APT_IN_PROCESS_NATIVE_REACHABLE.items():
        entry=_cap(registry,cid)
        source=entry.get("source") or {}
        if source.get("type")!="apt":
            raise NativeSurfaceError("APT_TYPE_DRIFT:"+cid)
        packages={str(x.get("name")) for x in source.get("packages") or [] if isinstance(x,dict)}
        if fact["package"] not in packages:
            raise NativeSurfaceError("APT_PACKAGE_DRIFT:"+cid)
        if entry.get("adapter_module")!=fact["adapter_module"]:
            raise NativeSurfaceError("APT_ADAPTER_DRIFT:"+cid)
        definite.append({
            "capability_id":cid,
            "adapter_module":entry.get("adapter_module"),
            "reason":"APT_PYTHON_PACKAGE_HAS_NATIVE_LXML_RUNTIME_DEPENDENCY_REACHABLE_IN_PROCESS",
            "artifact":fact["package"]+" -> "+fact["native_dependency"],
            "collapse_route":"EXECUTE_ADAPTER_IN_ISOLATED_CHILD_PROCESS",
        })

    packaging_pure=[]
    for cid in sorted(EXPECTED_PURE_WHEEL_CAPS):
        entry=_cap(registry,cid)
        source=entry.get("source") or {}
        wheel=str(source.get("wheel_filename") or "")
        closure=source.get("dependency_closure")
        wheels=[wheel]
        if isinstance(closure,dict):
            wheels=[str(x.get("filename") or "") for x in closure.get("wheels") or []]
        if not wheels or any("-none-any.whl" not in x for x in wheels):
            raise NativeSurfaceError("PURE_WHEEL_CLASS_DRIFT:"+cid)
        packaging_pure.append({
            "capability_id":cid,
            "adapter_module":entry.get("adapter_module"),
            "reason":"ALL_PINNED_PYPI_WHEELS_ARE_PLATFORM_INDEPENDENT",
            "native_extension_packaging_present":False,
            "source_level_dynamic_native_loader_audit_still_required":True,
        })

    for cid in sorted(EXPECTED_ARCH_ALL_APT_PYTHON_CAPS):
        entry=_cap(registry,cid)
        source=entry.get("source") or {}
        if source.get("type")!="apt":
            raise NativeSurfaceError("ARCH_ALL_APT_TYPE_DRIFT:"+cid)
        packaging_pure.append({
            "capability_id":cid,
            "adapter_module":entry.get("adapter_module"),
            "reason":"OFFICIAL_UBUNTU_PACKAGE_IS_ARCHITECTURE_ALL_AND_HAS_NO_NATIVE_RUNTIME_DEPENDENCY_IN_FROZEN_PUBLIC_DEPENDENCY_FACT",
            "native_extension_packaging_present":False,
            "source_level_dynamic_native_loader_audit_still_required":True,
        })

    out_of_process=[]
    for cid,entry in sorted((registry.get("capabilities") or {}).items()):
        source=entry.get("source") or {}
        typ=source.get("type")
        adapter=str(entry.get("adapter_module") or "")
        if typ in {"npm","system_tool"}:
            out_of_process.append({
                "capability_id":cid,
                "adapter_module":adapter,
                "source_type":typ,
                "reason":"EXECUTION_ALREADY_CROSSES_NODE_OR_SYSTEM_TOOL_PROCESS_BOUNDARY",
            })
        elif typ=="apt" and adapter in {
            "cli_command","archive_verify_gnu_tar","pandoc_weasyprint",
            "pdf_ocr_tesseract","sqlite_verify_cli","jq_query","yq_yaml_json",
        }:
            out_of_process.append({
                "capability_id":cid,
                "adapter_module":adapter,
                "source_type":typ,
                "reason":"APT_TOOL_EXECUTED_BY_SUBPROCESS_NOT_IMPORTED_AS_PYTHON_EXTENSION",
            })

    definite=sorted(definite,key=lambda x:x["capability_id"])
    risky_adapters=sorted(set(x["adapter_module"] for x in definite))
    return {
        "schema":SCHEMA,
        "status":"FINITE_NATIVE_EXTENSION_RISK_SET_CLASSIFIED__ISOLATION_NOT_YET_INTEGRATED",
        "definite_or_reachable_in_process_native_capability_count":len(definite),
        "definite_or_reachable_in_process_native_capabilities":definite,
        "risky_adapter_modules":risky_adapters,
        "packaging_level_non_native_but_source_audit_open":packaging_pure,
        "already_out_of_process_capabilities":out_of_process,
        "reduction":{
            "before":"NATIVE_EXTENSION_INTERNAL_EFFECTS_OPEN_OVER_UNCLASSIFIED_NONREPO_DEPENDENCIES",
            "after":"ISOLATE_4_RISKY_ADAPTER_MODULES_OR_PROVE_THEIR_NATIVE_INTERNAL_EFFECTS__SOURCE_AUDIT_PACKAGING_PURE_MODULES",
            "preferred":"ISOLATE_RISKY_ADAPTERS_TO_COLLAPSE_NATIVE_EXTENSION_RESIDUAL_INTO_EXISTING_FINITE_CHILD_PROCESS_RESIDUAL",
        },
        "native_extension_internal_effect_totality_proved":False,
        "c1_native_extension_scope_complete":False,
        "hard_nonclaims":[
            "PLATFORM_INDEPENDENT_WHEEL_DOES_NOT_PROVE_SOURCE_CANNOT_USE_CTYPES_CFFI_OR_OTHER_NATIVE_LOADERS",
            "APT_ARCHITECTURE_ALL_DOES_NOT_BY_ITSELF_PROVE_TRANSITIVE_RUNTIME_DEPENDENCIES_ARE_NON_NATIVE",
            "ISOLATION_ROUTE_NOT_YET_IMPLEMENTED_OR_VERIFIED",
            "NO_FULL_C1_SCOPE_COMPLETENESS",
            "NO_ROOT3_PREDICATE_CLOSED",
        ],
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",default="canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
    ns=ap.parse_args()
    print(json.dumps(classify(ns.registry),indent=2,sort_keys=True))
