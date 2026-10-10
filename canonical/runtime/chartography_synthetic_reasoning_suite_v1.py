#!/usr/bin/env python3
"""Deterministic zero-terminal synthetic chart-reasoning qualification suite.

No benchmark/terminal Chartography case, external dataset, OCR dependency, or
model judge is used. Ground truth is generated from exact geometry.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Callable

W, H = 256, 192
WHITE=(255,255,255); BLACK=(0,0,0); RED=(255,0,0); GREEN=(0,180,0); BLUE=(0,80,255)
CYAN=(0,190,190); YELLOW=(240,190,0); PURPLE=(145,70,200); ORANGE=(240,120,20)

EXPECTED = {
    1: ("BLUE", "c68d78abd05fc9101fe8112d35f2af95fb29be783ac6751d3bb44d0aa1ff7144"),
    2: ("2", "554d3a72a1b14e267fe36233a6c0a45486823436a39911cc2287648ee2f3479c"),
    3: ("INCREASE", "0c76e5f3157425f155acdc5a02f271f9706ae8e4d154aa74782a0da939dc4c9a"),
    4: ("BLUE", "ff92368272340426cce84c6db1d30868fe7b24c8daac7fc413800e8b27693ea1"),
    5: ("5", "dad9460416cd783a1205e061e471fe09fbae0007629adc03c04a1e43d634dbb2"),
    6: ("RIGHT", "33099ac52b5b17f0b5071cf1db02fb1c27a5001c3f0546fbcb54a26aa209f57c"),
}

def _canvas():
    return [[WHITE for _ in range(W)] for __ in range(H)]

def _rect(im,x0,y0,x1,y1,c):
    for y in range(max(0,y0),min(H,y1)):
        for x in range(max(0,x0),min(W,x1)):
            im[y][x]=c

def _line(im,x0,y0,x1,y1,c,t=3):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        _rect(im,x0-t//2,y0-t//2,x0+t//2+1,y0+t//2+1,c)
        if x0==x1 and y0==y1:
            return
        e2=2*err
        if e2>=dy:
            err+=dy; x0+=sx
        if e2<=dx:
            err+=dx; y0+=sy

def _dot(im,x,y,c,r=5):
    for yy in range(y-r,y+r+1):
        for xx in range(x-r,x+r+1):
            if (xx-x)**2+(yy-y)**2<=r*r and 0<=xx<W and 0<=yy<H:
                im[yy][xx]=c

def _axes(im):
    _line(im,28,160,232,160,BLACK,2)
    _line(im,28,20,28,160,BLACK,2)

def _bmp_bytes(im):
    row=((W*3+3)//4)*4
    pix=bytearray()
    for y in range(H-1,-1,-1):
        raw=bytearray()
        for x in range(W):
            r,g,b=im[y][x]
            raw += bytes((b,g,r))
        raw += bytes(row-len(raw))
        pix += raw
    size=54+len(pix)
    return (
        b"BM"
        + struct.pack("<IHHI",size,0,0,54)
        + struct.pack("<IIIHHIIIIII",40,W,H,1,24,0,len(pix),2835,2835,0,0)
        + pix
    )

def _case1():
    im=_canvas(); _axes(im)
    _rect(im,55,120,90,160,RED); _rect(im,110,80,145,160,GREEN); _rect(im,165,40,200,160,BLUE)
    return im,"Which colored bar is tallest? Answer exactly one word: RED, GREEN, or BLUE.","BLUE","BAR_ORDERING"

def _case2():
    im=_canvas(); _axes(im)
    _rect(im,75,64,115,160,CYAN); _rect(im,150,112,190,160,YELLOW)
    return im,"The cyan and yellow bars start at the same baseline. Cyan is how many times as tall as yellow? Answer exactly 2.","2","BAR_RATIO"

def _case3():
    im=_canvas(); _axes(im)
    pts=[(48,140),(85,120),(122,96),(159,70),(205,46)]
    for a,b in zip(pts,pts[1:]): _line(im,*a,*b,RED,4)
    for p in pts: _dot(im,*p,RED,4)
    return im,"From left to right, does the red line increase or decrease in plotted value? Answer exactly INCREASE or DECREASE.","INCREASE","LINE_TREND"

def _case4():
    im=_canvas(); _axes(im)
    _line(im,48,50,210,135,RED,4); _line(im,48,135,210,50,BLUE,4)
    return im,"At the right side of the chart, which line is higher in plotted value? Answer exactly RED or BLUE.","BLUE","LINE_CROSSING"

def _case5():
    im=_canvas(); _axes(im); _line(im,130,25,130,160,BLACK,1)
    for p in [(50,55),(70,80),(88,108),(105,65),(116,130)]: _dot(im,*p,GREEN,6)
    for p in [(155,75),(183,112),(214,52)]: _dot(im,*p,RED,6)
    return im,"How many green data points are left of the vertical divider? Answer exactly one digit.","5","SCATTER_COUNT"

def _case6():
    im=_canvas(); _axes(im)
    _rect(im,60,100,85,160,PURPLE); _rect(im,88,75,113,160,ORANGE)
    _rect(im,155,55,180,160,PURPLE); _rect(im,183,95,208,160,ORANGE)
    return im,"There are two groups of purple/orange bars. In which group is the PURPLE bar taller than the ORANGE bar? Answer exactly LEFT or RIGHT.","RIGHT","GROUPED_BAR_COMPARISON"

CASES: tuple[Callable, ...]=(_case1,_case2,_case3,_case4,_case5,_case6)

def generate_suite(output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for i,fn in enumerate(CASES,1):
        im,prompt,expected,skill=fn()
        data=_bmp_bytes(im)
        path=output_dir/f"case_{i}.bmp"
        path.write_bytes(data)
        record={
            "case_id":i,"skill":skill,"file":path.name,
            "sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
            "prompt":prompt,"expected":expected,
        }
        manifest.append(record)
    (output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest

def verify_generated(manifest: list[dict]) -> dict:
    errors=[]
    if len(manifest)!=6:
        errors.append("CASE_COUNT_NOT_6")
    if len({x.get("skill") for x in manifest})!=6:
        errors.append("SKILL_COVERAGE_NOT_6_DISTINCT")
    for row in manifest:
        cid=row.get("case_id")
        if cid not in EXPECTED:
            errors.append(f"UNKNOWN_CASE:{cid}")
            continue
        expected,sha=EXPECTED[cid]
        if row.get("expected")!=expected:
            errors.append(f"EXPECTED_DRIFT:{cid}")
        if row.get("sha256")!=sha:
            errors.append(f"HASH_DRIFT:{cid}")
        if row.get("bytes")!=147510:
            errors.append(f"BYTE_SIZE_DRIFT:{cid}")
    return {
        "pass":not errors,
        "errors":sorted(errors),
        "case_count":len(manifest),
        "distinct_skill_count":len({x.get("skill") for x in manifest}),
        "terminal_cases_consumed":0,
        "judge_calls":0,
        "incremental_spend_usd":0,
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="chartography-synthetic-suite-v1")
    args=ap.parse_args()
    manifest=generate_suite(Path(args.output_dir))
    result=verify_generated(manifest)
    print(json.dumps({"manifest":manifest,"verification":result},indent=2))
    raise SystemExit(0 if result["pass"] else 1)
