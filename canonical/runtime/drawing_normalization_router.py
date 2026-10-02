"""Fail-closed routing choke point for engineering-drawing normalization.

Exactly one registration route is selected from explicit evidence:
- NONE
- GLOBAL_ROTATION
- PROJECTIVE_EXPLICIT
- PROJECTIVE_AUTO
- CALIBRATED_DENSE

Optional post-deskew is explicit. Every successful route then passes through the
verified multi-route preprocessing consensus gate.
"""
from __future__ import annotations

from typing import Any, Mapping
import numpy as np

from canonical.runtime.drawing_view_registration import register_global_axis_deskew
from canonical.runtime.drawing_perspective_registration import rectify_perspective
from canonical.runtime.calibrated_dense_warp_rectifier import rectify_with_inverse_map
from canonical.runtime.drawing_preprocess_consensus import consensus_ink_mask

SCHEMA="BRAIN_DRAWING_NORMALIZATION_ROUTER_V1"
_MODES={"NONE","GLOBAL_ROTATION","PROJECTIVE_EXPLICIT","PROJECTIVE_AUTO","CALIBRATED_DENSE"}

def normalize_drawing(
    image:np.ndarray[Any,Any],
    registration:Mapping[str,Any],
    *,
    post_deskew:bool=False,
    consensus_min_iou:float=0.60,
)->dict[str,Any]:
    if not isinstance(registration,Mapping):
        raise ValueError("registration must be an object")
    mode=str(registration.get("mode","")).upper()
    if mode not in _MODES:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"REGISTRATION_MODE_INVALID"}

    current=image
    receipts=[]

    if mode=="NONE":
        receipts.append({"stage":"registration","mode":"NONE","status":"SKIPPED_BY_EXPLICIT_EVIDENCE"})
    elif mode=="GLOBAL_ROTATION":
        out=register_global_axis_deskew(
            current,
            max_abs_angle_deg=float(registration.get("max_abs_angle_deg",15.0)),
        )
        if out.get("status")!="REGISTERED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GLOBAL_ROTATION_FAILED","detail":out}
        current=out["registered_image"]
        receipts.append({"stage":"registration","mode":mode,"estimated_rotation_deg":out["estimated_rotation_deg"]})
    elif mode in {"PROJECTIVE_EXPLICIT","PROJECTIVE_AUTO"}:
        corners=registration.get("corners") if mode=="PROJECTIVE_EXPLICIT" else None
        out=rectify_perspective(
            current,
            corners=corners,
            min_area_fraction=float(registration.get("min_area_fraction",0.20)),
        )
        if out.get("status")!="REGISTERED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"PROJECTIVE_REGISTRATION_FAILED","detail":out}
        current=out["registered_image"]
        receipts.append({"stage":"registration","mode":mode,"route":out.get("route"),"output_size":out.get("output_size")})
    elif mode=="CALIBRATED_DENSE":
        mx=registration.get("map_x"); my=registration.get("map_y")
        if not isinstance(mx,np.ndarray) or not isinstance(my,np.ndarray):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"CALIBRATION_MAP_MISSING"}
        out=rectify_with_inverse_map(
            current,mx,my,
            interpolation=str(registration.get("interpolation","linear")),
            max_out_of_bounds_fraction=float(registration.get("max_out_of_bounds_fraction",0.01)),
        )
        if out.get("status")!="REGISTERED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"CALIBRATED_DENSE_REGISTRATION_FAILED","detail":out}
        current=out["registered_image"]
        receipts.append({"stage":"registration","mode":mode,"out_of_bounds_fraction":out["out_of_bounds_fraction"]})

    if post_deskew and mode!="GLOBAL_ROTATION":
        out=register_global_axis_deskew(current)
        if out.get("status")!="REGISTERED":
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"POST_DESKEW_FAILED","detail":out}
        current=out["registered_image"]
        receipts.append({"stage":"post_deskew","estimated_rotation_deg":out["estimated_rotation_deg"]})

    cons=consensus_ink_mask(current,min_pairwise_iou=consensus_min_iou)
    if cons.get("status")!="CONSENSUS":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"PREPROCESS_CONSENSUS_FAILED","detail":cons,"receipts":receipts}
    receipts.append({
        "stage":"preprocess_consensus",
        "cluster":cons["cluster"],
        "cluster_size":cons["cluster_size"],
        "mean_pairwise_iou":cons["mean_pairwise_iou"],
    })
    return {
        "schema":SCHEMA,"status":"NORMALIZED",
        "registered_image":current,
        "ink_mask":cons["mask"],
        "receipts":receipts,
        "terminal_authority":False,
        "scope":"EXPLICIT_EVIDENCE_SELECTED_REGISTRATION_PLUS_VERIFIED_PREPROCESSING_CONSENSUS",
    }
