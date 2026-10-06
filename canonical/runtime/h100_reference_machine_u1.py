from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

OP={
 "HALT":0,"PUSH":1,"LOAD":2,"STORE":3,"ADD":4,"SUB":5,"MUL":6,"FDIV":7,"MOD":8,
 "EQ":9,"LT":10,"JZ":11,"JMP":12,"DUP":13,"SWAP":14,"READ":15,"WRITE":16
}
REV={v:k for k,v in OP.items()}

class U1Error(ValueError): pass

@dataclass(frozen=True)
class Instr:
    pc:int
    op:int
    imm:int|None
    next_pc:int

def encode_sleb(value:int)->bytes:
    if not isinstance(value,int) or isinstance(value,bool): raise U1Error("IMM_INVALID")
    out=bytearray()
    more=True
    while more:
        byte=value & 0x7f
        sign=byte & 0x40
        value >>= 7
        if (value==0 and sign==0) or (value==-1 and sign!=0):
            more=False
        else:
            byte |= 0x80
        out.append(byte)
    return bytes(out)

def decode_sleb(program:bytes,start:int)->tuple[int,int]:
    if not isinstance(program,(bytes,bytearray)): raise U1Error("PROGRAM_INVALID")
    result=0; shift=0; pc=start
    while True:
        if pc>=len(program): raise U1Error("IMMEDIATE_TRUNCATED")
        byte=program[pc]; pc+=1
        result |= (byte & 0x7f) << shift
        shift += 7
        if not (byte & 0x80):
            if byte & 0x40: result |= -(1 << shift)
            break
    # Canonicality: re-encode must match consumed bytes exactly.
    if encode_sleb(result)!=bytes(program[start:pc]): raise U1Error("IMMEDIATE_NONCANONICAL")
    return result,pc

def decode_program(program:bytes)->dict[int,Instr]:
    if not isinstance(program,(bytes,bytearray)) or not program: raise U1Error("PROGRAM_INVALID")
    program=bytes(program); out={}; pc=0
    while pc<len(program):
        here=pc; op=program[pc]; pc+=1
        if op not in REV: raise U1Error("OPCODE_INVALID")
        imm=None
        if op in (OP["PUSH"],OP["JZ"],OP["JMP"]):
            imm,pc=decode_sleb(program,pc)
        out[here]=Instr(here,op,imm,pc)
    return out

def run(program:bytes,input_values:Iterable[int]=(),*,max_steps:int=100000,max_stack_depth:int=10000,max_heap_cells:int=10000,max_output_values:int=10000):
    for name,val in [("MAX_STEPS",max_steps),("MAX_STACK_DEPTH",max_stack_depth),("MAX_HEAP_CELLS",max_heap_cells),("MAX_OUTPUT_VALUES",max_output_values)]:
        if not isinstance(val,int) or isinstance(val,bool) or val<1: raise U1Error(name+"_INVALID")
    inp=tuple(input_values)
    if any((not isinstance(x,int)) or isinstance(x,bool) for x in inp): raise U1Error("INPUT_VALUE_INVALID")
    ins=decode_program(program); boundaries=set(ins)
    stack=[]; heap={}; output=[]; pc=0; steps=0

    def need(n:int):
        if len(stack)<n: raise U1Error("STACK_UNDERFLOW")
    def push(v:int):
        stack.append(int(v))
        if len(stack)>max_stack_depth: raise U1Error("STACK_LIMIT")
    def binary(fn):
        need(2); b=stack.pop(); a=stack.pop(); push(fn(a,b))
    while True:
        if steps>=max_steps: raise U1Error("STEP_LIMIT")
        if pc not in ins: raise U1Error("FALL_OFF_OR_BAD_JUMP")
        i=ins[pc]; steps+=1; pc=i.next_pc; op=i.op
        if op==OP["HALT"]:
            return {"status":"HALT","output":output,"steps":steps,"stack":list(stack),"heap":dict(heap)}
        elif op==OP["PUSH"]: push(i.imm)
        elif op==OP["LOAD"]:
            need(1); addr=stack.pop(); push(heap.get(addr,0))
        elif op==OP["STORE"]:
            need(2); value=stack.pop(); addr=stack.pop()
            if addr not in heap and len(heap)>=max_heap_cells: raise U1Error("HEAP_LIMIT")
            heap[addr]=value
        elif op==OP["ADD"]: binary(lambda a,b:a+b)
        elif op==OP["SUB"]: binary(lambda a,b:a-b)
        elif op==OP["MUL"]: binary(lambda a,b:a*b)
        elif op==OP["FDIV"]:
            def f(a,b):
                if b==0: raise U1Error("DIV_ZERO")
                return a//b
            binary(f)
        elif op==OP["MOD"]:
            def f(a,b):
                if b==0: raise U1Error("MOD_ZERO")
                return a%b
            binary(f)
        elif op==OP["EQ"]: binary(lambda a,b:1 if a==b else 0)
        elif op==OP["LT"]: binary(lambda a,b:1 if a<b else 0)
        elif op==OP["JZ"]:
            need(1); cond=stack.pop()
            if cond==0:
                target=i.next_pc+i.imm
                if target not in boundaries: raise U1Error("JUMP_TARGET_INVALID")
                pc=target
        elif op==OP["JMP"]:
            target=i.next_pc+i.imm
            if target not in boundaries: raise U1Error("JUMP_TARGET_INVALID")
            pc=target
        elif op==OP["DUP"]:
            need(1); push(stack[-1])
        elif op==OP["SWAP"]:
            need(2); stack[-1],stack[-2]=stack[-2],stack[-1]
        elif op==OP["READ"]:
            need(1); idx=stack.pop()
            if idx<0 or idx>=len(inp): raise U1Error("READ_RANGE")
            push(inp[idx])
        elif op==OP["WRITE"]:
            need(1)
            if len(output)>=max_output_values: raise U1Error("OUTPUT_LIMIT")
            output.append(stack.pop())
        else:
            raise U1Error("UNREACHABLE_OPCODE")
