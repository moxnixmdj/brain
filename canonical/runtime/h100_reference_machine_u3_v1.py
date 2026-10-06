from __future__ import annotations
MASK=(1<<64)-1
SIGN=1<<63
OPCODES={"HALT":0,"PUSH":1,"LOAD":2,"STORE":3,"LOADIND":4,"STOREIND":5,"ADD":6,"SUB":7,"MUL":8,"FDIV":9,"MOD":10,"EQ":11,"LT":12,"JZ":13,"JMP":14,"DUP":15,"SWAP":16,"READ":17,"INLEN":18,"WRITE":19}
NAMES={v:k for k,v in OPCODES.items()}
IMM={"PUSH","LOAD","STORE","JZ","JMP"}
class U3Error(ValueError): pass

def _s64(x):
 x&=MASK
 return x-(1<<64) if x&SIGN else x

def _sleb128(n):
 if not isinstance(n,int) or isinstance(n,bool): raise U3Error("IMM_NOT_INT")
 out=bytearray()
 while True:
  b=n&0x7f; sign=b&0x40; n>>=7
  done=(n==0 and sign==0) or (n==-1 and sign!=0)
  out.append(b if done else b|0x80)
  if done:return bytes(out)

def _read_sleb128(data,pos):
 result=0;shift=0
 while True:
  if pos>=len(data): raise U3Error("TRUNCATED_IMMEDIATE")
  b=data[pos];pos+=1;result|=(b&0x7f)<<shift;shift+=7
  if not b&0x80:
   if b&0x40:result|=-(1<<shift)
   return result,pos
  if shift>4096: raise U3Error("IMMEDIATE_TOO_LONG")

def encode(program):
 out=bytearray()
 for inst in program:
  if not isinstance(inst,(list,tuple)) or not inst: raise U3Error("INSTRUCTION_INVALID")
  name=str(inst[0])
  if name not in OPCODES: raise U3Error("OPCODE_UNKNOWN")
  out.append(OPCODES[name])
  if name in IMM:
   if len(inst)!=2: raise U3Error("IMMEDIATE_ARITY")
   out.extend(_sleb128(inst[1]))
  elif len(inst)!=1: raise U3Error("NO_IMMEDIATE_ARITY")
 if not out: raise U3Error("PROGRAM_EMPTY")
 return bytes(out)

def decode(data):
 if not isinstance(data,(bytes,bytearray)) or not data: raise U3Error("PROGRAM_NOT_BYTES")
 data=bytes(data);pos=0;out=[]
 while pos<len(data):
  op=data[pos];pos+=1
  if op not in NAMES: raise U3Error("OPCODE_BYTE_UNKNOWN")
  name=NAMES[op]
  if name in IMM:
   imm,pos=_read_sleb128(data,pos);out.append((name,imm))
  else: out.append((name,))
 return out

def execute(program,input_vector=(),*,step_limit=100000,memory_cells=1024,stack_limit=1024,output_limit=1024):
 insts=decode(program) if isinstance(program,(bytes,bytearray)) else [tuple(x) for x in program]
 limits=(step_limit,memory_cells,stack_limit,output_limit)
 if any((not isinstance(x,int)) or isinstance(x,bool) or x<1 for x in limits): raise U3Error("RESOURCE_LIMIT_INVALID")
 inp=list(input_vector)
 if any((not isinstance(x,int)) or isinstance(x,bool) or x<-(1<<63) or x>=(1<<63) for x in inp): raise U3Error("INPUT_NOT_S64")
 stack=[];mem=[0]*memory_cells;out=[];ip=0;read_pos=0;steps=0
 def push(v):
  if len(stack)>=stack_limit: raise U3Error("STACK_LIMIT")
  stack.append(_s64(v))
 def pop():
  if not stack: raise U3Error("STACK_UNDERFLOW")
  return stack.pop()
 def addr(i):
  if not 0<=i<memory_cells: raise U3Error("MEMORY_LIMIT")
  return i
 def jump(i):
  if not 0<=i<len(insts): raise U3Error("IP_OUT_OF_RANGE")
  return i
 while True:
  if steps>=step_limit: raise U3Error("STEP_LIMIT")
  if not 0<=ip<len(insts): raise U3Error("IP_OUT_OF_RANGE")
  inst=insts[ip];name=inst[0];steps+=1
  if name=="HALT": break
  if name=="PUSH": push(inst[1]);ip+=1
  elif name=="LOAD": push(mem[addr(inst[1])]);ip+=1
  elif name=="STORE": mem[addr(inst[1])]=_s64(pop());ip+=1
  elif name=="LOADIND": push(mem[addr(pop())]);ip+=1
  elif name=="STOREIND":
   val=pop();address=pop();mem[addr(address)]=_s64(val);ip+=1
  elif name=="ADD": b=pop();a=pop();push(a+b);ip+=1
  elif name=="SUB": b=pop();a=pop();push(a-b);ip+=1
  elif name=="MUL": b=pop();a=pop();push(a*b);ip+=1
  elif name=="FDIV":
   b=pop();a=pop()
   if b==0: raise U3Error("DIV_ZERO")
   push(a//b);ip+=1
  elif name=="MOD":
   b=pop();a=pop()
   if b==0: raise U3Error("MOD_ZERO")
   push(a%b);ip+=1
  elif name=="EQ": b=pop();a=pop();push(1 if a==b else 0);ip+=1
  elif name=="LT": b=pop();a=pop();push(1 if a<b else 0);ip+=1
  elif name=="JZ": c=pop();ip=jump(inst[1]) if c==0 else ip+1
  elif name=="JMP": ip=jump(inst[1])
  elif name=="DUP":
   if not stack: raise U3Error("STACK_UNDERFLOW")
   push(stack[-1]);ip+=1
  elif name=="SWAP":
   if len(stack)<2: raise U3Error("STACK_UNDERFLOW")
   stack[-1],stack[-2]=stack[-2],stack[-1];ip+=1
  elif name=="READ":
   if read_pos>=len(inp): raise U3Error("INPUT_EXHAUSTED")
   push(inp[read_pos]);read_pos+=1;ip+=1
  elif name=="INLEN": push(len(inp));ip+=1
  elif name=="WRITE":
   if len(out)>=output_limit: raise U3Error("OUTPUT_LIMIT")
   out.append(pop());ip+=1
  else: raise U3Error("UNREACHABLE_OPCODE")
 return {"output":tuple(out),"memory":tuple(mem),"stack":tuple(stack),"steps":steps}

def program_bytes(program): return len(encode(program))
def program_bits(program): return 8*program_bytes(program)
