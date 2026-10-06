from __future__ import annotations
from canonical.runtime import h100_reference_machine_u1 as u1
class U4Error(ValueError): pass
def int_bits(v):
 if not isinstance(v,int) or isinstance(v,bool): raise U4Error("INT_REQUIRED")
 return 8*len(u1.encode_sleb(v))
def live_state_bits(stack,heap,output,pc,steps,input_len):
 return sum(map(int_bits,stack))+sum(int_bits(k)+int_bits(v) for k,v in heap.items())+sum(map(int_bits,output))+sum(map(int_bits,(len(stack),len(heap),len(output),pc,steps,input_len)))
def run(program,input_values=(),*,max_steps=100000,max_stack_depth=10000,max_heap_cells=10000,max_output_values=10000,max_live_bits=1000000):
 lim=(max_steps,max_stack_depth,max_heap_cells,max_output_values,max_live_bits)
 if any((not isinstance(x,int)) or isinstance(x,bool) or x<1 for x in lim): raise U4Error("RESOURCE_LIMIT_INVALID")
 inp=tuple(input_values)
 if any((not isinstance(x,int)) or isinstance(x,bool) for x in inp): raise U4Error("INPUT_VALUE_INVALID")
 ins=u1.decode_program(program); bounds=set(ins); st=[]; hp={}; out=[]; pc=0; steps=0; peak=0
 def need(n):
  if len(st)<n: raise U4Error("STACK_UNDERFLOW")
 def push(v):
  st.append(int(v))
  if len(st)>max_stack_depth: raise U4Error("STACK_LIMIT")
 def check():
  nonlocal peak
  b=live_state_bits(st,hp,out,pc,steps,len(inp)); peak=max(peak,b)
  if b>max_live_bits: raise U4Error("LIVE_BIT_LIMIT")
 def binary(f):
  need(2); b=st.pop(); a=st.pop(); push(f(a,b))
 check()
 while True:
  if steps>=max_steps: raise U4Error("STEP_LIMIT")
  if pc not in ins: raise U4Error("FALL_OFF_OR_BAD_JUMP")
  i=ins[pc]; steps+=1; pc=i.next_pc; op=i.op
  if op==u1.OP["HALT"]:
   check(); return {"status":"HALT","output":out,"steps":steps,"stack":list(st),"heap":dict(hp),"peak_live_bits":peak}
  if op==u1.OP["PUSH"]: push(i.imm)
  elif op==u1.OP["LOAD"]: need(1); push(hp.get(st.pop(),0))
  elif op==u1.OP["STORE"]:
   need(2); v=st.pop(); a=st.pop()
   if a not in hp and len(hp)>=max_heap_cells: raise U4Error("HEAP_LIMIT")
   hp[a]=v
  elif op==u1.OP["ADD"]: binary(lambda a,b:a+b)
  elif op==u1.OP["SUB"]: binary(lambda a,b:a-b)
  elif op==u1.OP["MUL"]: binary(lambda a,b:a*b)
  elif op==u1.OP["FDIV"]:
   def f(a,b):
    if b==0: raise U4Error("DIV_ZERO")
    return a//b
   binary(f)
  elif op==u1.OP["MOD"]:
   def f(a,b):
    if b==0: raise U4Error("MOD_ZERO")
    return a%b
   binary(f)
  elif op==u1.OP["EQ"]: binary(lambda a,b:int(a==b))
  elif op==u1.OP["LT"]: binary(lambda a,b:int(a<b))
  elif op==u1.OP["JZ"]:
   need(1); c=st.pop()
   if c==0:
    t=i.next_pc+i.imm
    if t not in bounds: raise U4Error("JUMP_TARGET_INVALID")
    pc=t
  elif op==u1.OP["JMP"]:
   t=i.next_pc+i.imm
   if t not in bounds: raise U4Error("JUMP_TARGET_INVALID")
   pc=t
  elif op==u1.OP["DUP"]: need(1); push(st[-1])
  elif op==u1.OP["SWAP"]: need(2); st[-1],st[-2]=st[-2],st[-1]
  elif op==u1.OP["READ"]:
   need(1); j=st.pop()
   if j<0 or j>=len(inp): raise U4Error("READ_RANGE")
   push(inp[j])
  elif op==u1.OP["WRITE"]:
   need(1)
   if len(out)>=max_output_values: raise U4Error("OUTPUT_LIMIT")
   out.append(st.pop())
  else: raise U4Error("UNREACHABLE_OPCODE")
  check()
