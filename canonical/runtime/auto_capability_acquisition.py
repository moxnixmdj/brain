#!/usr/bin/env python3
"""Route autonomous capability acquisition across supplier classes."""
from __future__ import annotations
import json
import re

import auto_apt_cli_acquisition
import auto_pypi_library_acquisition
import auto_npm_library_acquisition
import auto_github_source_acquisition


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


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    attempts=[]
    required=_required_supplier_class(goal)
    if required=="npm_javascript_library":
        try:
            return auto_npm_library_acquisition.dispatch(
                goal,mission_id,mission_path,root,discovery=discovery
            )
        except Exception as exc:
            attempts.append({
              "supplier_class":"npm_javascript_library",
              "error":type(exc).__name__+":"+str(exc),
            })
            raise AutoAcquisitionFailure(
                "NO_COMPATIBLE_REQUIRED_SUPPLIER_CONTRACT",
                json.dumps(attempts,sort_keys=True)[:4000]
            ) from exc
    if auto_pypi_library_acquisition.supports(goal):
        try:
            return auto_pypi_library_acquisition.dispatch(
                goal,mission_id,mission_path,root,discovery=discovery
            )
        except Exception as exc:
            attempts.append({
              "supplier_class":"pypi_python_library",
              "error":type(exc).__name__+":"+str(exc),
            })
    if auto_github_source_acquisition.supports(goal):
        try:
            return auto_github_source_acquisition.dispatch(
                goal,mission_id,mission_path,root,discovery=discovery
            )
        except Exception as exc:
            attempts.append({
              "supplier_class":"github_source_python",
              "error":type(exc).__name__+":"+str(exc),
            })
    try:
        return auto_apt_cli_acquisition.dispatch(
            goal,mission_id,mission_path,root,discovery=discovery
        )
    except Exception as exc:
        attempts.append({
          "supplier_class":"apt_cli",
          "error":type(exc).__name__+":"+str(exc),
        })
    raise AutoAcquisitionFailure(
        "NO_COMPATIBLE_SUPPLIER_CONTRACT",
        json.dumps(attempts,sort_keys=True)[:4000]
    )
