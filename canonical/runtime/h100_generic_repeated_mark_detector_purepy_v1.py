from __future__ import annotations
import struct,zlib,math
from collections import Counter

PNG=b"\x89PNG\r\n\x1a\n"

def _paeth(a,b,c):
    p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c)
    return a if pa<=pb and pa<=pc else b if pb<=pc else c

def read_png_rgb(path):
    data=open(path,"rb").read()
    if data[:8]!=PNG: raise ValueError("NOT_PNG")
    pos=8;idat=[];palette=None;trans=None
    width=height=ctype=bit=None
    while pos<len(data):
        n=struct.unpack(">I",data[pos:pos+4])[0];typ=data[pos+4:pos+8];chunk=data[pos+8:pos+8+n];pos+=12+n
        if typ==b"IHDR":
            width,height,bit,ctype,comp,filt,inter=struct.unpack(">IIBBBBB",chunk)
            if bit!=8 or comp!=0 or filt!=0 or inter!=0: raise ValueError("UNSUPPORTED_PNG")
        elif typ==b"PLTE":palette=[tuple(chunk[i:i+3]) for i in range(0,len(chunk),3)]
        elif typ==b"tRNS":trans=chunk
        elif typ==b"IDAT":idat.append(chunk)
        elif typ==b"IEND":break
    bpp={0:1,2:3,3:1,4:2,6:4}.get(ctype)
    if bpp is None: raise ValueError("UNSUPPORTED_COLOR")
    raw=zlib.decompress(b"".join(idat));stride=width*bpp;rows=[];prev=bytearray(stride);off=0
    for _ in range(height):
        ft=raw[off];off+=1;scan=bytearray(raw[off:off+stride]);off+=stride
        for i in range(stride):
            a=scan[i-bpp] if i>=bpp else 0;b=prev[i];c=prev[i-bpp] if i>=bpp else 0
            if ft==1:scan[i]=(scan[i]+a)&255
            elif ft==2:scan[i]=(scan[i]+b)&255
            elif ft==3:scan[i]=(scan[i]+((a+b)//2))&255
            elif ft==4:scan[i]=(scan[i]+_paeth(a,b,c))&255
            elif ft!=0:raise ValueError("BAD_FILTER")
        row=[]
        for x in range(width):
            p=x*bpp
            if ctype==2:rgb=tuple(scan[p:p+3])
            elif ctype==6:rgb=tuple(scan[p:p+3])
            elif ctype==0:rgb=(scan[p],)*3
            elif ctype==4:rgb=(scan[p],)*3
            elif ctype==3:
                idx=scan[p];rgb=palette[idx]
            row.append(rgb)
        rows.append(row);prev=scan
    return width,height,rows

def intervals(v,thr):
    out=[];s=None
    for i,b in enumerate([x>=thr for x in v]):
        if b and s is None:s=i
        if s is not None and (not b or i==len(v)-1):
            e=i if b and i==len(v)-1 else i-1;out.append((s,e));s=None
    return out

def detect_repeated_marks(path):
    w,h,rows=read_png_rgb(path)
    q=[[(r//16*16,g//16*16,b//16*16) for r,g,b in row] for row in rows]
    counts=Counter(px for row in q for px in row);cand=[]
    for color,count in counts.items():
        chroma=max(color)-min(color);bright=sum(color)/3
        if chroma<32 or bright>235 or count<0.001*h*w:continue
        rs=[sum(px==color for px in row) for row in q]
        cs=[sum(q[y][x]==color for y in range(h)) for x in range(w)]
        ri=[z for z in intervals(rs,max(8,int(.02*w))) if 2<=z[1]-z[0]+1<=max(80,int(.2*h))]
        ci=[z for z in intervals(cs,max(8,int(.02*h))) if 2<=z[1]-z[0]+1<=max(80,int(.2*w))]
        def score(z,vec):
            if len(z)<2 or len(z)>50:return 0.0
            widths=[b-a+1 for a,b in z];mean=sum(widths)/len(widths)
            var=sum((x-mean)**2 for x in widths)/len(widths);cv=math.sqrt(var)/max(mean,1e-9)
            occ=sum(sum(vec[a:b+1]) for a,b in z)
            return len(z)*(1/(1+cv))*occ/max(count,1)
        sr,sc=score(ri,rs),score(ci,cs);z=ri if sr>=sc else ci
        if max(sr,sc)>0:cand.append((max(sr,sc),len(z),z,color))
    cand.sort(reverse=True)
    return {"count":cand[0][1] if cand else None,"candidate_count":len(cand),"top":cand[:5]}
