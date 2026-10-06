from __future__ import annotations

OPCODES={
"HALT":0,"PUSH":1,"LOAD":2,"STORE":3,"ADD":4,"SUB":5,"MUL":6,"FDIV":7,"MOD":8,
"EQ":9,"LT":10,"JZ":11,"JMP":12,"DUP":13,"SWAP":14,"READ":15,"WRITE":16,
}
NAMES={v:k for k,v in OPCODES.items()}
IMM={"PUSH","LOAD","STORE","JZ","JMP"}

class U1Error(ValueError): pass

def _sleb128(n:int)->bytes:
    if not isinstance(n,int) or isinstance(n,bool): raise U1Error("IMM_NOT_INT")
    out=bytearray()
    more=True
    while more:
        byte=n & 0x7f
        sign=byte & 0x40
        n >>= 7
        if (n==0 and sign==0) or (n==-1 and sign!=0):
            more=False
        else:
            byte|=0x80
        out.append(byte)
    return bytes(out)

def _read_sleb128(data:bytes,pos:int):
    result=0; shift=0
    while True:
        if pos>=len(data): raise U1Error("TRUNCATED_IMMEDIATE")
        byte=data[pos]; pos+=1
        result|=(byte & 0x7f)<<shift
        shift+=7
        if not (byte & 0x80):
            if byte & 0x40: result|=-(1<<shift)
            return result,pos
        if shift>4096: raise U1Error("IMMEDIATE_TOO_LONG")

def encode(program):
    out=bytearray()
    for inst in program:
        if not isinstance(inst,(tuple,list)) or not inst: raise U1Error("INSTRUCTION_INVALID")
        name=str(inst[0])
        if name not in OPCODES: raise U1Error("OPCODE_UNKNOWN")
        out.append(OPCODES[name])
        if name in IMM:
            if len(inst)!=2: raise U1Error("IMMEDIATE_ARITY")
            out.extend(_sleb128(inst[1]))
        elif len(inst)!=1:
            raise U1Error("NO_IMMEDIATE_ARITY")
    return bytes(out)

def decode(data:bytes):
    if not isinstance(data,(bytes,bytearray)): raise U1Error("PROGRAM_NOT_BYTES")
    data=bytes(data); pos=0; out=[]
    while pos<len(data):
        op=data[pos]; pos+=1
        if op not in NAMES: raise U1Error("OPCODE_BYTE_UNKNOWN")
        name=NAMES[op]
        if name in IMM:
            imm,pos=_read_sleb128(data,pos)
            out.append((name,imm))
        else:
            out.append((name,))
    return out

def execute(program,input_vector=(),*,step_limit:int=100000):
    insts=decode(program) if isinstance(program,(bytes,bytearray)) else [tuple(x) for x in program]
    if not isinstance(step_limit,int) or step_limit<1: raise U1Error("STEP_LIMIT_INVALID")
    inp=list(input_vector)
    if any((not isinstance(x,int)) or isinstance(x,bool) for x in inp): raise U1Error("INPUT_NOT_INT")
    stack=[]; mem={}; out=[]; ip=0; read_pos=0; steps=0
    def pop():
        if not stack: raise U1Error("STACK_UNDERFLOW")
        return stack.pop()
    while True:
        if steps>=step_limit: raise U1Error("STEP_LIMIT")
        if not (0<=ip<len(insts)): raise U1Error("IP_OUT_OF_RANGE")
        steps+=1
        inst=insts[ip]; name=inst[0]
        if name=="HALT": break
        elif name=="PUSH": stack.append(inst[1]); ip+=1
        elif name=="LOAD": stack.append(mem.get(inst[1],0)); ip+=1
        elif name=="STORE": mem[inst[1]]=pop(); ip+=1
        elif name=="ADD":
            b=pop(); a=pop(); stack.append(a+b); ip+=1
        elif name=="SUB":
            b=pop(); a=pop(); stack.append(a-b); ip+=1
        elif name=="MUL":
            b=pop(); a=pop(); stack.append(a*b); ip+=1
        elif name=="FDIV":
            b=pop(); a=pop()
            if b==0: raise U1Error("DIV_ZERO")
            stack.append(a//b); ip+=1
        elif name=="MOD":
            b=pop(); a=pop()
            if b==0: raise U1Error("MOD_ZERO")
            stack.append(a%b); ip+=1
        elif name=="EQ":
            b=pop(); a=pop(); stack.append(1 if a==b else 0); ip+=1
        elif name=="LT":
            b=pop(); a=pop(); stack.append(1 if a<b else 0); ip+=1
        elif name=="JZ":
            cond=pop(); ip=inst[1] if cond==0 else ip+1
        elif name=="JMP": ip=inst[1]
        elif name=="DUP":
            if not stack: raise U1Error("STACK_UNDERFLOW")
            stack.append(stack[-1]); ip+=1
        elif name=="SWAP":
            if len(stack)<2: raise U1Error("STACK_UNDERFLOW")
            stack[-1],stack[-2]=stack[-2],stack[-1]; ip+=1
        elif name=="READ":
            if read_pos>=len(inp): raise U1Error("INPUT_EXHAUSTED")
            stack.append(inp[read_pos]); read_pos+=1; ip+=1
        elif name=="WRITE": out.append(pop()); ip+=1
        else: raise U1Error("UNREACHABLE_OPCODE")
    return {"output":out,"memory":mem,"stack":stack,"steps":steps}

def program_bytes(program)->int:
    return len(encode(program))
