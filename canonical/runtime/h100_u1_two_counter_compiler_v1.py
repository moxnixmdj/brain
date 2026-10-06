from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_reference_machine_u1 as u1

class TwoCounterCompilerError(ValueError): pass

@dataclass(frozen=True)
class Asm:
    kind:str
    value:Any=None

def L(name:str)->Asm: return Asm("LABEL",str(name))
def I(name:str,imm:Any=None)->Asm: return Asm(str(name),imm)

def _item_len(item:Asm,jump_imm:int|None=None)->int:
    if item.kind=="LABEL": return 0
    if item.kind=="PUSH": return 1+len(u1.encode_sleb(int(item.value)))
    if item.kind in ("JZ","JMP"):
        imm=0 if jump_imm is None else int(jump_imm)
        return 1+len(u1.encode_sleb(imm))
    return 1

def assemble(items:Sequence[Asm])->bytes:
    if not items: raise TwoCounterCompilerError("EMPTY_ASSEMBLY")
    jump_offsets=[0]*len(items)
    last_layout=None
    for _ in range(100):
        pcs=[]; pc=0; labels={}
        for idx,item in enumerate(items):
            pcs.append(pc)
            if item.kind=="LABEL":
                if item.value in labels: raise TwoCounterCompilerError("DUPLICATE_LABEL")
                labels[item.value]=pc
            else:
                pc+=_item_len(item,jump_offsets[idx] if item.kind in ("JZ","JMP") else None)
        layout=(tuple(pcs),tuple(sorted(labels.items())),tuple(jump_offsets))
        if layout==last_layout:
            break
        last_layout=layout
        changed=False
        for idx,item in enumerate(items):
            if item.kind not in ("JZ","JMP"): continue
            label=str(item.value)
            if label not in labels: raise TwoCounterCompilerError("UNKNOWN_LABEL:"+label)
            imm_len=len(u1.encode_sleb(jump_offsets[idx]))
            for _fix in range(16):
                next_pc=pcs[idx]+1+imm_len
                off=labels[label]-next_pc
                new_len=len(u1.encode_sleb(off))
                if new_len==imm_len: break
                imm_len=new_len
            else:
                raise TwoCounterCompilerError("JUMP_IMMEDIATE_LENGTH_DID_NOT_STABILIZE")
            if jump_offsets[idx]!=off:
                jump_offsets[idx]=off; changed=True
        if not changed:
            break
    else:
        raise TwoCounterCompilerError("ASSEMBLY_DID_NOT_CONVERGE")

    # final labels/pcs with stable offsets
    pcs=[]; pc=0; labels={}
    for idx,item in enumerate(items):
        pcs.append(pc)
        if item.kind=="LABEL": labels[item.value]=pc
        else: pc+=_item_len(item,jump_offsets[idx] if item.kind in ("JZ","JMP") else None)

    out=bytearray()
    for idx,item in enumerate(items):
        if item.kind=="LABEL": continue
        if item.kind not in u1.OP: raise TwoCounterCompilerError("UNKNOWN_OPCODE:"+item.kind)
        out.append(u1.OP[item.kind])
        if item.kind=="PUSH": out.extend(u1.encode_sleb(int(item.value)))
        elif item.kind in ("JZ","JMP"): out.extend(u1.encode_sleb(jump_offsets[idx]))
    # ensure machine decoder accepts it before returning
    u1.decode_program(bytes(out))
    return bytes(out)

def validate_machine(machine:Mapping[str,Mapping[str,Any]],start:str)->None:
    if not isinstance(machine,Mapping) or not machine: raise TwoCounterCompilerError("MACHINE_INVALID")
    if start not in machine: raise TwoCounterCompilerError("START_UNKNOWN")
    for label,ins in machine.items():
        if not isinstance(label,str) or not isinstance(ins,Mapping): raise TwoCounterCompilerError("INSTRUCTION_INVALID")
        op=ins.get("op")
        if op=="HALT": continue
        if op=="INC":
            if ins.get("counter") not in (0,1) or ins.get("next") not in machine: raise TwoCounterCompilerError("INC_INVALID")
        elif op=="DECJZ":
            if ins.get("counter") not in (0,1): raise TwoCounterCompilerError("DECJZ_COUNTER_INVALID")
            if ins.get("nonzero") not in machine or ins.get("zero") not in machine: raise TwoCounterCompilerError("DECJZ_TARGET_INVALID")
        else:
            raise TwoCounterCompilerError("SOURCE_OPCODE_INVALID")

def compile_machine(machine:Mapping[str,Mapping[str,Any]],start:str)->bytes:
    validate_machine(machine,start)
    items=[
        P(0),P(0),I("READ"),I("STORE"),
        P(1),P(1),I("READ"),I("STORE"),
        I("JMP","Q_"+start),
    ]
    for label,ins in machine.items():
        items.append(L("Q_"+label))
        op=ins["op"]
        if op=="HALT":
            items += [P(0),I("LOAD"),I("WRITE"),P(1),I("LOAD"),I("WRITE"),I("HALT")]
        elif op=="INC":
            r=int(ins["counter"])
            items += [P(r),P(r),I("LOAD"),P(1),I("ADD"),I("STORE"),I("JMP","Q_"+str(ins["next"]))]
        elif op=="DECJZ":
            r=int(ins["counter"])
            zero="DEC_ZERO_"+str(label)
            items += [
                P(r),I("LOAD"),I("JZ",zero),
                P(r),P(r),I("LOAD"),P(1),I("SUB"),I("STORE"),I("JMP","Q_"+str(ins["nonzero"])),
                L(zero),I("JMP","Q_"+str(ins["zero"]))
            ]
    return assemble(items)

def P(v:int)->Asm: return I("PUSH",int(v))

def run_source(machine:Mapping[str,Mapping[str,Any]],start:str,c0:int,c1:int,max_steps:int=100000)->tuple[int,int]:
    validate_machine(machine,start)
    regs=[int(c0),int(c1)]; state=start
    if min(regs)<0: raise TwoCounterCompilerError("NEGATIVE_COUNTER")
    for _ in range(max_steps):
        ins=machine[state]; op=ins["op"]
        if op=="HALT": return tuple(regs)
        if op=="INC":
            regs[int(ins["counter"])]+=1; state=str(ins["next"]); continue
        r=int(ins["counter"])
        if regs[r]==0:
            state=str(ins["zero"])
        else:
            regs[r]-=1; state=str(ins["nonzero"])
    raise TwoCounterCompilerError("SOURCE_STEP_LIMIT")

def compare(machine,start,inputs,max_steps=100000):
    program=compile_machine(machine,start)
    rows=[]
    for c0,c1 in inputs:
        want=run_source(machine,start,c0,c1,max_steps=max_steps)
        got=tuple(u1.run(program,[c0,c1],max_steps=max_steps*20)["output"])
        rows.append({"input":[c0,c1],"source":list(want),"u1":list(got),"equal":want==got})
    return {"program_bytes":len(program),"rows":rows,"all_equal":all(x["equal"] for x in rows)}
