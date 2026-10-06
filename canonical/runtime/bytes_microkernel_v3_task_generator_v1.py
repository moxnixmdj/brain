from __future__ import annotations
import hashlib, json

KERNEL_SHA256="5b7c4628ff640bc0dd2c43d7e32037e5f943a633def797d63caee6107714a8cb"
U=("neg","abs","square","sqrt_abs","log1p_abs","sat")
B=("add","sub","mul","stable_div")
COEF=(-1.35,-1.05,-0.72,-0.44,0.38,0.63,0.91,1.22,1.47)
BIAS=(-0.73,-0.41,-0.16,0.12,0.31,0.58,0.84)

class Stream:
    def __init__(self):
        self.i=0
    def n(self):
        x=hashlib.sha256((KERNEL_SHA256+":"+str(self.i)).encode()).digest()
        self.i+=1
        return int.from_bytes(x[:8],"big")
    def pick(self,x):
        return x[self.n()%len(x)]

def v(name):
    return ["var",name]

def unary(s,name,depth):
    t=v(name)
    for _ in range(depth):
        t=[s.pick(U),t]
    return t

def base(s,name):
    return v(name) if s.n()%3==0 else [s.pick(U),v(name)]

def truth1(s,expr):
    return ["add",s.pick(BIAS),["mul",s.pick(COEF),expr]]

def truth2(s,a,b):
    c1=s.pick(COEF); c2=s.pick(tuple(x for x in COEF if x!=c1))
    return ["add",s.pick(BIAS),["add",["mul",c1,a],["mul",c2,b]]]

def grids(two):
    if not two:
        return (
          {"x_start":-3.37,"x_step":0.283,"count":26},
          {"x_start":-3.11,"x_step":0.317,"count":19},
        )
    return (
      {"x_values":[-2.83,-1.71,-0.62,0.29,1.38,2.57],"z_values":[-2.14,-0.81,0.47,1.76]},
      {"x_values":[-2.41,-1.19,0.08,1.16,2.31],"z_values":[-1.67,-0.26,0.93,2.03]},
    )

def task(i,inputs,truth):
    tr,ho=grids(len(inputs)==2)
    return {"id":f"V3_T{i}","inputs":list(inputs),"truth_ast":truth,"train_grid":tr,"holdout_grid":ho}

def generate():
    s=Stream()
    t=[]
    t.append(task(1,("x",),truth1(s,unary(s,"x",1))))
    t.append(task(2,("x",),truth1(s,unary(s,"x",2))))
    t.append(task(3,("x","z"),truth2(s,base(s,"x"),base(s,"z"))))
    t.append(task(4,("x","z"),truth1(s,[s.pick(B),base(s,"x"),base(s,"z")])))
    t.append(task(5,("x",),truth1(s,unary(s,"x",2))))
    t.append(task(6,("x","z"),truth1(s,[s.pick(B),base(s,"x"),base(s,"z")])))
    return {
      "schema":"PROJECT_BRAIN_BYTES_MICROKERNEL_PROSPECTIVE_V3_TASKS",
      "kernel_sha256":KERNEL_SHA256,
      "derivation":"SHA256_COUNTER_STREAM_FROM_FROZEN_KERNEL_SHA256",
      "task_count":len(t),
      "tasks":t,
      "success":{"all_tasks_required":True,"fresh_holdout_max_abs_error_lte":1e-6},
    }

if __name__=="__main__":
    print(json.dumps(generate(),sort_keys=True,separators=(",",":")))
