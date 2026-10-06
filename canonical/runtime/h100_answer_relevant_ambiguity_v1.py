from __future__ import annotations
import math

class AnswerAmbiguityError(ValueError): pass

def _classes(classes):
    if not isinstance(classes,list) or not classes:
        raise AnswerAmbiguityError("CLASSES_INVALID")
    out=[]
    for c in classes:
        if not isinstance(c,list) or not c:
            raise AnswerAmbiguityError("CLASS_INVALID")
        out.append(c)
    return out

def distinct_output_counts(classes:list[list[object]])->list[int]:
    return [len({repr(x) for x in c}) for c in _classes(classes)]

def exact_output_bits_lower_bound(classes:list[list[object]])->int:
    k=max(distinct_output_counts(classes))
    return 0 if k<=1 else math.ceil(math.log2(k))

def zero_bit_exact_possible(classes:list[list[object]])->bool:
    return exact_output_bits_lower_bound(classes)==0

def zero_bit_safe_coverage(classes:list[list[object]])->float:
    cs=_classes(classes)
    total=sum(len(c) for c in cs)
    safe=sum(len(c) for c in cs if len({repr(x) for x in c})==1)
    return safe/total

def zero_bit_selective_policy(classes:list[list[object]])->list[dict]:
    rows=[]
    for c in _classes(classes):
        labels={repr(x):x for x in c}
        if len(labels)==1:
            rows.append({"action":"CLASSIFY","output":next(iter(labels.values())),"class_size":len(c)})
        else:
            rows.append({"action":"ABSTAIN","distinct_output_count":len(labels),"class_size":len(c)})
    return rows
