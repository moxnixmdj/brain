#!/usr/bin/env python3
import hashlib
import pathlib


def _safe_path(root, raw):
    p=(pathlib.Path(root)/str(raw or "")).resolve()
    root=pathlib.Path(root).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("PYPDF_IMPORT_FAILED:"+type(exc).__name__+":"+str(exc)) from exc

    src=_safe_path(root,args.get("path"))
    if not src.is_file():
        raise RuntimeError("PDF_NOT_FOUND")
    max_pages=max(1,min(int(args.get("max_pages",200)),1000))
    reader=PdfReader(str(src))
    chunks=[]
    processed=0
    for page in reader.pages[:max_pages]:
        chunks.append(page.extract_text() or "")
        processed+=1
    text="\n".join(chunks)
    data=text.encode("utf-8")
    return {
      "adapter":"bound_capability",
      "capability_id":"pdf.extract.text.pypdf",
      "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
      "pages_total":len(reader.pages),
      "pages_processed":processed,
      "text":text[:20000],
      "text_truncated":len(text)>20000,
      "text_sha256":hashlib.sha256(data).hexdigest(),
      "text_bytes":len(data)
    }
