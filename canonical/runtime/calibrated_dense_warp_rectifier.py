"""Generic calibrated dense-warp rectifier.

Brain does not guess an unknown local warp. If authorized calibration/JIT evidence
provides an inverse sampling map from rectified output pixels to observed source
coordinates, this mechanism applies it deterministically and verifies that the map is
finite, in-bounds, locally nondegenerate, and orientation-consistent.

This closes the capability side of local nonprojective registration; obtaining the
calibration map is evidence/knowledge. Without such evidence the identifiability
boundary remains fail-closed.
"""
from __future__ import annotations

from typing import Any
import math

import cv2
import numpy as np

SCHEMA="BRAIN_CALIBRATED_DENSE_WARP_RECTIFIER_V1"


def _validate_maps(
    image:np.ndarray[Any,Any],
    map_x:np.ndarray[Any,Any],
    map_y:np.ndarray[Any,Any],
    *,
    min_abs_jacobian:float,
    max_out_of_bounds_fraction:float,
)->dict[str,Any]:
    errors=[]
    if not isinstance(image,np.ndarray) or image.ndim not in (2,3):
        return {"valid":False,"errors":["IMAGE_INVALID"]}
    if not isinstance(map_x,np.ndarray) or not isinstance(map_y,np.ndarray):
        return {"valid":False,"errors":["MAPS_NOT_ARRAYS"]}
    if map_x.ndim!=2 or map_y.ndim!=2 or map_x.shape!=map_y.shape or map_x.size==0:
        return {"valid":False,"errors":["MAP_SHAPE_INVALID"]}
    if not np.isfinite(map_x).all() or not np.isfinite(map_y).all():
        errors.append("MAP_NONFINITE")
    h,w=image.shape[:2]
    in_bounds=(map_x>=0)&(map_x<=w-1)&(map_y>=0)&(map_y<=h-1)
    oob_fraction=1.0-float(in_bounds.mean())
    if oob_fraction>max_out_of_bounds_fraction:
        errors.append("MAP_TOO_FAR_OUT_OF_BOUNDS")

    # The inverse map p_out -> p_source must not fold or collapse locally.
    # Central finite differences yield Jacobian determinant where defined.
    if map_x.shape[0]>=3 and map_x.shape[1]>=3 and not errors:
        dx_du=(map_x[1:-1,2:]-map_x[1:-1,:-2])*0.5
        dx_dv=(map_x[2:,1:-1]-map_x[:-2,1:-1])*0.5
        dy_du=(map_y[1:-1,2:]-map_y[1:-1,:-2])*0.5
        dy_dv=(map_y[2:,1:-1]-map_y[:-2,1:-1])*0.5
        det=dx_du*dy_dv-dx_dv*dy_du
        interior_bounds=in_bounds[1:-1,1:-1]
        usable=det[interior_bounds]
        if usable.size:
            if np.any(np.abs(usable)<min_abs_jacobian):
                errors.append("LOCAL_MAP_DEGENERACY")
            pos=np.any(usable>min_abs_jacobian)
            neg=np.any(usable<-min_abs_jacobian)
            if pos and neg:
                errors.append("LOCAL_MAP_FOLDOVER_ORIENTATION_CHANGE")
        else:
            errors.append("NO_IN_BOUNDS_INTERIOR_FOR_JACOBIAN")
    elif min(map_x.shape)<3:
        errors.append("MAP_TOO_SMALL_FOR_LOCAL_INVERTIBILITY_CHECK")

    return {
        "valid":not errors,
        "errors":sorted(set(errors)),
        "out_of_bounds_fraction":oob_fraction,
    }


def rectify_with_inverse_map(
    image:np.ndarray[Any,Any],
    map_x:np.ndarray[Any,Any],
    map_y:np.ndarray[Any,Any],
    *,
    interpolation:str="linear",
    min_abs_jacobian:float=1e-3,
    max_out_of_bounds_fraction:float=0.01,
)->dict[str,Any]:
    if min_abs_jacobian<=0:
        raise ValueError("min_abs_jacobian must be positive")
    if not (0<=max_out_of_bounds_fraction<1):
        raise ValueError("max_out_of_bounds_fraction must be in [0,1)")
    flags={"nearest":cv2.INTER_NEAREST,"linear":cv2.INTER_LINEAR,"cubic":cv2.INTER_CUBIC}
    if interpolation not in flags:
        raise ValueError("unsupported interpolation")

    mx=np.asarray(map_x,dtype=np.float32)
    my=np.asarray(map_y,dtype=np.float32)
    verdict=_validate_maps(
        image,mx,my,
        min_abs_jacobian=min_abs_jacobian,
        max_out_of_bounds_fraction=max_out_of_bounds_fraction,
    )
    if not verdict["valid"]:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":verdict["errors"],
            "out_of_bounds_fraction":verdict.get("out_of_bounds_fraction"),
            "terminal_authority":False,
        }

    border=255 if image.ndim==2 else tuple([255]*image.shape[2])
    out=cv2.remap(
        image,mx,my,flags[interpolation],
        borderMode=cv2.BORDER_CONSTANT,borderValue=border
    )
    return {
        "schema":SCHEMA,"status":"REGISTERED",
        "registered_image":out,
        "output_shape":[int(x) for x in out.shape],
        "out_of_bounds_fraction":verdict["out_of_bounds_fraction"],
        "interpolation":interpolation,
        "terminal_authority":False,
        "scope":"ARBITRARY_LOCAL_NONPROJECTIVE_RECTIFICATION_WHEN_AN_AUTHORIZED_INVERSE_CALIBRATION_MAP_IS_SUPPLIED_AND_PASSES_INVERTIBILITY_CHECKS",
    }
