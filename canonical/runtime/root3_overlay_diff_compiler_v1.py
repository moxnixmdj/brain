from __future__ import annotations
import hashlib
import os
import pathlib
import stat

SCHEMA="PROJECT_BRAIN_ROOT3_OVERLAY_DIFF_COMPILER_V1"

class OverlayDiffError(RuntimeError):
    pass

def _sha(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def compile_upper_diff(lower,upper):
    lower=pathlib.Path(lower).resolve()
    upper=pathlib.Path(upper).resolve()
    rows=[]
    for p in sorted(upper.rglob("*"),key=lambda q:q.relative_to(upper).as_posix()):
        rel=p.relative_to(upper).as_posix()
        st=p.lstat()
        mode=st.st_mode
        try:
            attrs=sorted(os.listxattr(p,follow_symlinks=False))
        except OSError:
            attrs=[]
        overlay_attrs=[a for a in attrs if "overlay" in a]
        if overlay_attrs:
            raise OverlayDiffError(
                "UNMODELED_OVERLAY_XATTR:"+rel+":"+",".join(overlay_attrs)
            )
        lp=lower/rel
        if (
            stat.S_ISCHR(mode)
            and os.major(st.st_rdev)==0
            and os.minor(st.st_rdev)==0
        ):
            rows.append({
                "path":rel,
                "operation":"DELETE",
                "prior_exists":lp.exists() or lp.is_symlink(),
            })
        elif stat.S_ISREG(mode):
            rows.append({
                "path":rel,
                "operation":"MODIFY" if lp.exists() else "ADD",
                "kind":"file",
                "size":st.st_size,
                "sha256":_sha(p),
            })
        elif stat.S_ISLNK(mode):
            target=os.readlink(p)
            rows.append({
                "path":rel,
                "operation":"MODIFY" if lp.exists() or lp.is_symlink() else "ADD",
                "kind":"symlink",
                "target":target,
                "sha256":hashlib.sha256(target.encode()).hexdigest(),
            })
        elif stat.S_ISDIR(mode):
            if not lp.exists():
                rows.append({
                    "path":rel,
                    "operation":"ADD",
                    "kind":"directory",
                })
        else:
            raise OverlayDiffError("UNSUPPORTED_UPPER_ENTRY:"+rel)
    return {
        "schema":SCHEMA,
        "status":"PASS",
        "change_count":len(rows),
        "changes":rows,
        "accounting":{
            "acceptance_credit_delta":0,
            "new_reality_units_consumed":0,
        },
    }
