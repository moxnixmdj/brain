from __future__ import annotations

import json
import pathlib
import tempfile

from canonical.runtime.bound_capabilities import image_ocr_tesseract

FONT={
"T":["11111","00100","00100","00100","00100","00100","00100"],
"E":["11111","10000","10000","11110","10000","10000","11111"],
"S":["01111","10000","10000","01110","00001","00001","11110"],
"O":["01110","10001","10001","10001","10001","10001","01110"],
"C":["01111","10000","10000","10000","10000","10000","01111"],
"R":["11110","10001","10001","11110","10100","10010","10001"],
" ":["00000"]*7,
}

def _write_fixture(path: pathlib.Path):
    text="TEST OCR TEST"
    scale=12
    margin=40
    char_w=6*scale
    w=margin*2+len(text)*char_w
    h=margin*2+7*scale
    pixels=bytearray([255])*(w*h)
    for ci,ch in enumerate(text):
        glyph=FONT[ch]
        ox=margin+ci*char_w
        oy=margin
        for gy,row in enumerate(glyph):
            for gx,bit in enumerate(row):
                if bit!="1":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        pixels[(oy+gy*scale+dy)*w+(ox+gx*scale+dx)]=0
    path.write_bytes(f"P5\n{w} {h}\n255\n".encode("ascii")+bytes(pixels))

def verify():
    dependency=image_ocr_tesseract.verify_dependency_surface()
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        image=root/"engineering_text.pgm"
        _write_fixture(image)
        out=image_ocr_tesseract.run({"path":image.name},root)
    passed=(
        dependency["eng_model_sha256"]==image_ocr_tesseract.EXPECTED_ENG_MODEL_SHA256
        and dependency["packages"]==image_ocr_tesseract.EXPECTED_PACKAGES
        and "TEST" in out["text"].upper()
        and out["terminal_semantic_authority"] is False
    )
    return {
        "schema":"PROJECT_BRAIN_PINNED_IMAGE_OCR_SURFACE_VERIFICATION_V1",
        "pass":passed,
        "dependency":dependency,
        "observed_text":out["text"],
        "selected_psm":out["selected_psm"],
        "scope":out["scope"],
        "new_reality_units_consumed":0,
        "terminal_semantic_authority":False,
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
