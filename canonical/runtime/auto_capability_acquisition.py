#!/usr/bin/env python3
"""Route autonomous capability acquisition across supplier classes."""
from __future__ import annotations
import json

import auto_apt_cli_acquisition
import auto_pypi_library_acquisition


class AutoAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    attempts=[]
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
