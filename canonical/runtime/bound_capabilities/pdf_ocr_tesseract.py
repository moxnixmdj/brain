#!/usr/bin/env python3
import hashlib
import pathlib
import subprocess
import tempfile


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    src=_safe_path(root,args.get("path"))
    if not src.is_file():
        raise RuntimeError("PDF_NOT_FOUND")
    max_pages=max(1,min(int(args.get("max_pages",50)),500))
    dpi=max(72,min(int(args.get("dpi",300)),600))
    language=str(args.get("language") or "eng")
    if not language.replace("+","").isalnum():
        raise RuntimeError("OCR_LANGUAGE_INVALID")
    texts=[]
    page_hashes=[]
    with tempfile.TemporaryDirectory(prefix="project-brain-ocr-") as td:
        prefix=pathlib.Path(td)/"page"
        render=subprocess.run(
            ["pdftoppm","-f","1","-l",str(max_pages),"-r",str(dpi),"-png",str(src),str(prefix)],
            text=True,capture_output=True,timeout=180
        )
        if render.returncode!=0:
            raise RuntimeError("PDF_RASTERIZE_FAILED:"+render.stderr[-1200:])
        images=sorted(pathlib.Path(td).glob("page-*.png"))
        if not images:
            raise RuntimeError("PDF_RASTERIZE_NO_PAGES")
        for image in images:
            raw=image.read_bytes()
            page_hashes.append(hashlib.sha256(raw).hexdigest())
            ocr=subprocess.run(
                ["tesseract",str(image),"stdout","-l",language,"--psm","6"],
                text=True,capture_output=True,timeout=180
            )
            if ocr.returncode!=0:
                raise RuntimeError("TESSERACT_FAILED:"+ocr.stderr[-1200:])
            texts.append(ocr.stdout.strip())
    text="\n".join(texts).strip()
    data=text.encode("utf-8")
    return {
      "adapter":"bound_capability",
      "capability_id":"pdf.extract.ocr.tesseract",
      "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
      "pages_processed":len(texts),
      "dpi":dpi,
      "language":language,
      "page_image_sha256":page_hashes,
      "text":text[:20000],
      "text_truncated":len(text)>20000,
      "text_sha256":hashlib.sha256(data).hexdigest(),
      "text_bytes":len(data)
    }
