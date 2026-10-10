import hashlib, json

def freeze(o):
    if o is None or isinstance(o,(str,int,bool)):
        return o
    if isinstance(o,float):
        return ['pyfloat', o.hex()]
    if isinstance(o,(list,tuple)):
        return ['seq',[freeze(x) for x in o]]
    if isinstance(o,dict):
        items=[(freeze(k),freeze(v)) for k,v in o.items()]
        items.sort(key=lambda kv: json.dumps(kv[0],sort_keys=True,separators=(',',':')))
        return ['dict',items]
    cls=o.__class__
    mod=getattr(cls,'__module__','')
    name=getattr(cls,'__name__',type(o).__name__)
    if mod.startswith('sympy'):
        if name in ('Symbol','Dummy') and hasattr(o,'name'):
            extra=[o.name]
            if name=='Dummy' and hasattr(o,'dummy_index'): extra.append(int(o.dummy_index))
            return ['sym',mod,name,extra]
        if hasattr(o,'p') and hasattr(o,'q') and name in ('Integer','Rational'):
            return ['num',mod,name,int(o.p),int(o.q)]
        args=getattr(o,'args',None)
        if args is not None:
            if not args:
                return ['atom',mod,name,str(getattr(o,'name',name))]
            return ['basic',mod,name,[freeze(a) for a in args]]
    return ['py',mod,name,repr(o)]

def digest(o):
    b=json.dumps(freeze(o),sort_keys=False,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(b).hexdigest()
