#!/usr/bin/env python3
"""Route autonomous capability acquisition across supplier classes."""
from __future__ import annotations
import json
import re

import auto_apt_cli_acquisition
import auto_pypi_library_acquisition
import auto_npm_library_acquisition
import auto_python_source_codec_acquisition


class AutoAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def _required_supplier_class(goal):
    lower=str(goal or "").lower()
    if re.search(r"\bnpm\b",lower) or re.search(r"\bnode(?:\.js|js)?\b",lower) or "javascript library" in lower:
        return "npm_javascript_library"
    if "pypi" in lower or "python library" in lower:
        return "pypi_python_library"
    if re.search(r"\bapt\b",lower) or "ubuntu package" in lower or "debian package" in lower:
        return "apt_cli"
    return None


def _discovery_supplier_order(discovery):
    """Return supplier classes in the order supported by discovery evidence.

    Federated discovery already ranks concrete candidates by zero-cost
    eligibility, secret requirements, integration friction, relevance, and
    source. The router must preserve that evidence instead of discarding it and
    re-imposing a hard-coded ecosystem preference.
    """
    mapping={
      "apt":"apt_cli",
      "APT_CATALOG":"apt_cli",
      "pypi":"pypi_python_library",
      "PYPI":"pypi_python_library",
      "npm":"npm_javascript_library",
      "NPM":"npm_javascript_library",
      "content_addressed_python_source_tree":"content_addressed_python_source_tree",
      "GITHUB_SOURCE_TREE":"content_addressed_python_source_tree",
    }
    out=[]
    for candidate in (discovery or {}).get("candidates",[]) or []:
        if not isinstance(candidate,dict):
            continue
        raw=candidate.get("binding_kind") or candidate.get("discovery_source")
        supplier=mapping.get(str(raw))
        if supplier and supplier not in out:
            out.append(supplier)
    return out


def _fallback_supplier_order(goal):
    """Legacy heuristics retained only as a fallback when evidence is absent."""
    out=[]
    if auto_pypi_library_acquisition.supports(goal):
        out.append("pypi_python_library")
    if auto_npm_library_acquisition.supports_effect(goal):
        out.append("npm_javascript_library")
    if auto_python_source_codec_acquisition.supports(goal):
        out.append("content_addressed_python_source_tree")
    out.append("apt_cli")
    return out


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    attempts=[]
    required=_required_supplier_class(goal)

    suppliers={
      "pypi_python_library": auto_pypi_library_acquisition,
      "npm_javascript_library": auto_npm_library_acquisition,
      "apt_cli": auto_apt_cli_acquisition,
      "content_addressed_python_source_tree": auto_python_source_codec_acquisition,
    }
    if required is not None:
        module=suppliers[required]
        try:
            return module.dispatch(goal,mission_id,mission_path,root,discovery=discovery)
        except Exception as exc:
            attempts.append({
              "supplier_class":required,
              "selection_basis":"EXPLICIT_GOAL_CONSTRAINT",
              "error":type(exc).__name__+":"+str(exc),
            })
            raise AutoAcquisitionFailure(
                "NO_COMPATIBLE_REQUIRED_SUPPLIER_CONTRACT",
                json.dumps(attempts,sort_keys=True)[:4000]
            ) from exc

    order=[]
    discovered=_discovery_supplier_order(discovery)
    for supplier in discovered+_fallback_supplier_order(goal):
        if supplier not in order:
            order.append(supplier)

    for supplier in order:
        module=suppliers[supplier]
        try:
            return module.dispatch(
                goal,mission_id,mission_path,root,discovery=discovery
            )
        except Exception as exc:
            attempts.append({
              "supplier_class":supplier,
              "selection_basis":(
                  "FEDERATED_DISCOVERY_RANK" if supplier in discovered
                  else "LEGACY_FALLBACK"
              ),
              "discovery_rank":(
                  discovered.index(supplier) if supplier in discovered else None
              ),
              "error":type(exc).__name__+":"+str(exc),
            })

    raise AutoAcquisitionFailure(
        "NO_COMPATIBLE_SUPPLIER_CONTRACT",
        json.dumps(attempts,sort_keys=True)[:4000]
    )
