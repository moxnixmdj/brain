from __future__ import annotations
import json
from canonical.runtime import h100_text_axis_legend_parser_v1 as base

class ScaleNormalizeError(ValueError):
    pass

def _downsample(rows,scale,ox,oy):
    if scale<1: raise ScaleNormalizeError("SCALE_INVALID")
    if not rows: raise ScaleNormalizeError("ROWS_EMPTY")
    sampled=[]
    for y in range(oy,len(rows),scale):
        row=rows[y]
        sampled.append("".join(row[x] for x in range(ox,len(row),scale)))
    if not sampled or min(map(len,sampled))<4:
        raise ScaleNormalizeError("DOWNSAMPLE_TOO_SMALL")
    return sampled

def parse(rows):
    outputs={}
    successes=[]
    for scale in (1,2,3,4):
        for oy in range(scale):
            for ox in range(scale):
                try:
                    candidate=_downsample(rows,scale,ox,oy)
                    out=base.parse(candidate)
                except Exception:
                    continue
                key=json.dumps(out,sort_keys=True,separators=(",",":"))
                outputs[key]=out
                successes.append({"scale":scale,"ox":ox,"oy":oy,"key":key})
    if not successes:
        raise ScaleNormalizeError("NO_NORMALIZATION_PARSE")
    if len(outputs)!=1:
        raise ScaleNormalizeError("NORMALIZATION_DISAGREEMENT")
    return next(iter(outputs.values()))
