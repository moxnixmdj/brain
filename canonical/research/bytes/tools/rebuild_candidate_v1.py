import importlib, types, shutil, sys, os, json
from pathlib import Path
SRC=Path('/opt/pyvenv/lib/python3.13/site-packages')
DST=Path('/mnt/data/bytes_successor/cand_lazy')
if DST.exists(): shutil.rmtree(DST)
DST.mkdir(parents=True)
for pkg in ['sympy','mpmath']:
    shutil.copytree(SRC/pkg,DST/pkg)
for p in list(DST.rglob('__pycache__')): shutil.rmtree(p, ignore_errors=True)
for p in sorted(list(DST.rglob('tests')), reverse=True):
    if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
for p in list(DST.rglob('test_*.py')):
    try:p.unlink()
    except:pass

pkgs=['sympy','sympy.functions','sympy.polys','sympy.printing','sympy.matrices','sympy.solvers','sympy.integrals','sympy.series','sympy.utilities','sympy.calculus','sympy.polys.domains','sympy.polys.numberfields','sympy.tensor.array']

def replace_once(path, old, new):
    t=path.read_text()
    if old not in t:
        raise RuntimeError(f'missing patch target in {path}: {old[:80]}')
    path.write_text(t.replace(old,new,1))

p=DST/'mpmath/ctx_mp.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, '''        # XXX: automate
        try:
            ctx.bernoulli.im_func.func_doc = function_docs.bernoulli
            ctx.primepi.im_func.func_doc = function_docs.primepi
            ctx.psi.im_func.func_doc = function_docs.psi
            ctx.atan2.im_func.func_doc = function_docs.atan2
        except AttributeError:
            # python 3
            ctx.bernoulli.__func__.func_doc = function_docs.bernoulli
            ctx.primepi.__func__.func_doc = function_docs.primepi
            ctx.psi.__func__.func_doc = function_docs.psi
            ctx.atan2.__func__.func_doc = function_docs.atan2

        ctx.digamma.func_doc = function_docs.digamma
        ctx.cospi.func_doc = function_docs.cospi
        ctx.sinpi.func_doc = function_docs.sinpi
''', '')

p=DST/'mpmath/ctx_fp.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, '        f_wrapped.__doc__ = function_docs.__dict__.get(name, f.__doc__)\n', '')

p=DST/'mpmath/ctx_mp_python.py'
replace_once(p, 'from . import function_docs\n', '')
replace_once(p, "        a.__doc__ = getattr(function_docs, docname, '')\n", '')
replace_once(p, '        f.__doc__ = function_docs.__dict__.get(name, "Computes the %s of x" % doc)\n', '')
replace_once(p, '        f_wrapped.__doc__ = function_docs.__dict__.get(name, f.__doc__)\n', '')
(DST/'mpmath/function_docs.py').unlink()

p=DST/'sympy/integrals/trigonometry.py'
replace_once(p, 'from .integrals import integrate\n', '')
replace_once(p, "def trigintegrate(f, x, conds='piecewise'):\n", "def trigintegrate(f, x, conds='piecewise'):\n    from .integrals import integrate\n")

p=DST/'sympy/core/add.py'
replace_once(p, '        from sympy.tensor.tensor import TensExpr, TensAdd\n', '')
replace_once(p, '            elif isinstance(o, TensExpr):\n                coeff = TensAdd(o, coeff).doit(deep=False)\n                continue\n', "            elif o.__class__.__module__.startswith('sympy.tensor.'):\n                from sympy.tensor.tensor import TensExpr, TensAdd\n                if isinstance(o, TensExpr):\n                    coeff = TensAdd(o, coeff).doit(deep=False)\n                    continue\n")

p=DST/'sympy/polys/polyroots.py'
replace_once(p, 'from sympy.polys.polyquinticconst import PolyQuintic\n', '')
replace_once(p, 'from sympy.polys.specialpolys import cyclotomic_poly\n', '')
replace_once(p, '    quintic = PolyQuintic(f)\n', '    from sympy.polys.polyquinticconst import PolyQuintic\n    quintic = PolyQuintic(f)\n')
replace_once(p, '        g = cyclotomic_poly(n, f.gen, polys=True)\n', '        from sympy.polys.specialpolys import cyclotomic_poly\n        g = cyclotomic_poly(n, f.gen, polys=True)\n')

p=DST/'sympy/simplify/simplify.py'
replace_once(p, '    from sympy.physics.units import Quantity\n\n    if expr.has(Quantity):\n        from sympy.physics.units.util import quantity_simplify\n        expr = quantity_simplify(expr)\n\n', '')

p=DST/'sympy/polys/polytools.py'
replace_once(p, 'from sympy.polys.fglmtools import matrix_fglm\n', '')
replace_once(p, 'from sympy.polys.groebnertools import groebner as _groebner\n', '')
replace_once(p, 'def groebner(F, *gens, **args):\n', 'def groebner(F, *gens, **args):\n    from sympy.polys.groebnertools import groebner as _groebner\n')
replace_once(p, '        G = matrix_fglm(polys, _ring, dst_order)\n', '        from sympy.polys.fglmtools import matrix_fglm\n        G = matrix_fglm(polys, _ring, dst_order)\n')

summary={}
for pn in pkgs:
    p=importlib.import_module(pn)
    names=list(getattr(p,'__all__',[])) or [n for n in vars(p) if not n.startswith('_')]
    mp={}; const={}; unm=[]
    for n in names:
        if not hasattr(p,n): continue
        o=getattr(p,n)
        if isinstance(o, types.ModuleType):
            mp[n]=(o.__name__,None); continue
        mod=getattr(o,'__module__',None)
        cand_attrs=[]
        oname=getattr(o,'__name__',None)
        if oname: cand_attrs.append(oname)
        cand_attrs.append(n)
        found=False
        if mod:
            try:
                m=importlib.import_module(mod)
                for an in cand_attrs:
                    if hasattr(m,an) and getattr(m,an) is o:
                        mp[n]=(mod,an); found=True; break
            except Exception: pass
        if found: continue
        if isinstance(o,(str,int,float,bool,type(None))): const[n]=o; continue
        unm.append(n)
    if pn in ('sympy','sympy.functions') and 'ln' in unm:
        mp['ln']=('sympy.functions.elementary.exponential','log'); unm.remove('ln')
    target=DST.joinpath(*pn.split('.'))/'__init__.py' if pn!='sympy' else DST/'sympy/__init__.py'
    lines=[]
    lines.append('"""Brain bounded lazy facade derived from SymPy 1.14.0 public bindings."""')
    lines.append('import importlib as _importlib')
    if pn=='sympy':
        lines.append('__version__ = "1.14.0"')
        lines.append('SYMPY_DEBUG = False')
    for k,v in const.items():
        if k!='__version__': lines.append(f'{k} = {v!r}')
    lines.append('_BRAIN_LAZY_MAP = ' + repr(mp))
    lines.append('__all__ = ' + repr([n for n in names if n in mp or n in const]))
    lines.append('def __getattr__(name):')
    lines.append('    spec = _BRAIN_LAZY_MAP.get(name)')
    lines.append('    if spec is None: raise AttributeError(name)')
    lines.append('    mod, attr = spec')
    lines.append('    obj = _importlib.import_module(mod) if attr is None else getattr(_importlib.import_module(mod), attr)')
    lines.append('    globals()[name] = obj')
    lines.append('    return obj')
    target.write_text('\n'.join(lines)+'\n')
    summary[pn]={'mapped':len(mp),'unmapped':unm}
print(json.dumps(summary,indent=2))

_mpmath_root = '''"""Brain bounded mpmath facade for exact-symbolic route."""
__version__ = "1.3.0"
from contextlib import contextmanager
from .ctx_mp_python import PythonMPContext
from .libmp import finf, fninf, fnan, fzero, fone
class MPContext(PythonMPContext):
    def __init__(self):
        super().__init__()
        self.default()
        self.types = [self.mpf, self.mpc, self.constant]
        self.pretty = False
        self.zero = self.make_mpf(fzero)
        self.one = self.make_mpf(fone)
        self.inf = self.make_mpf(finf)
        self.ninf = self.make_mpf(fninf)
        self.nan = self.make_mpf(fnan)
        self._mp = self
    @contextmanager
    def workprec(self, n, normalize_output=False):
        old = self.prec
        self.prec = n
        try:
            yield self
        finally:
            self.prec = old
mp = MPContext()
mpf = mp.mpf
mpc = mp.mpc
make_mpf = mp.make_mpf
make_mpc = mp.make_mpc
workprec = mp.workprec
inf = mp.inf
nan = mp.nan
def _unsupported(*args, **kwargs):
    raise NotImplementedError("mpmath operation outside Brain bounded exact-symbolic contract")
mpi = findroot = besseljzero = nsum = quadts = quadosc = sqrt = _unsupported
def __getattr__(name):
    if hasattr(mp, name):
        return getattr(mp, name)
    if name.startswith("_"):
        raise AttributeError(name)
    return _unsupported
'''
(DST/'mpmath/__init__.py').write_text(_mpmath_root)

p = DST/'sympy/matrices/immutable.py'
replace_once(p, 'from mpmath.matrices.matrices import _matrix\n\n', '')
replace_once(p,
'''def sympify_mpmath_matrix(arg):
    mat = [_sympify(x) for x in arg]
    return ImmutableDenseMatrix(arg.rows, arg.cols, mat)


sympify_converter[_matrix] = sympify_mpmath_matrix


''', '')
