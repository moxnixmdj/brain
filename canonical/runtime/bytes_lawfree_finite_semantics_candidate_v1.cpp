#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <unordered_set>
#include <unordered_map>
#include <vector>
using namespace std;
struct A{int n;int x[4];};
static const char* OP="RSu<>NADI2PMEO";
A ap(int o,A a){
 char c=OP[o];
 if(c=='R') reverse(a.x,a.x+a.n);
 else if(c=='S') sort(a.x,a.x+a.n);
 else if(c=='u'){int m=0,y[4];for(int i=0;i<a.n;i++){bool q=0;for(int j=0;j<m;j++)q|=y[j]==a.x[i];if(!q)y[m++]=a.x[i];}a.n=m;for(int i=0;i<m;i++)a.x[i]=y[i];}
 else if((c=='<'||c=='>')&&a.n){if(c=='<')rotate(a.x,a.x+1,a.x+a.n);else rotate(a.x,a.x+a.n-1,a.x+a.n);}
 else if(c=='N')for(int i=0;i<a.n;i++)a.x[i]=-a.x[i];
 else if(c=='A')for(int i=0;i<a.n;i++)a.x[i]=abs(a.x[i]);
 else if(c=='D')for(int i=0;i<a.n;i++)a.x[i]--;
 else if(c=='I')for(int i=0;i<a.n;i++)a.x[i]++;
 else if(c=='2')for(int i=0;i<a.n;i++)a.x[i]*=2;
 else if(c=='P'||c=='M'||c=='E'||c=='O'){int m=0;for(int i=0;i<a.n;i++){int v=a.x[i];bool q=c=='P'?v>0:c=='M'?v<0:c=='E'?(v%2==0):(v%2!=0);if(q)a.x[m++]=v;}a.n=m;}
 return a;
}
int cx(int x){if(x<-2)return 0;if(x==-2)return 1;if(x<-1)return 2;if(x==-1)return 3;if(x<0)return 4;if(x==0)return 5;if(x<1)return 6;if(x==1)return 7;if(x<2)return 8;if(x==2)return 9;return 10;}
int cs(int s){if(s<-2)return 0;if(s==-2)return 1;if(s<0)return 2;if(s==0)return 3;if(s<2)return 4;if(s==2)return 5;return 6;}
uint64_t rs(const A&a){
 uint64_t z=a.n,m=5;
 for(int i=0;i<a.n;i++){z+=(uint64_t)(cx(a.x[i])*2+(a.x[i]&1?1:0))*m;m*=22;}
 for(int i=0;i<a.n;i++)for(int j=i+1;j<a.n;j++){int d=(a.x[i]>a.x[j])-(a.x[i]<a.x[j]);z+=(uint64_t)((d+1)*7+cs(a.x[i]+a.x[j]))*m;m*=21;}
 return z;
}
uint64_t oc(const A&a){uint64_t z=a.n;int sh=3;for(int i=0;i<a.n;i++){int v=a.x[i]+512;if(v<0||v>=1024){cerr<<"RANGE\n";exit(2);}z|=(uint64_t)v<<sh;sh+=10;}return z;}
void allout(const A&in,vector<A>&o){
 o[0]=in;int b1=1,b2=15,b3=211;
 for(int a=0;a<14;a++)o[b1+a]=ap(a,in);
 for(int a=0;a<14;a++)for(int b=0;b<14;b++)o[b2+a*14+b]=ap(b,o[b1+a]);
 for(int a=0;a<14;a++)for(int b=0;b<14;b++)for(int c=0;c<14;c++)o[b3+(a*14+b)*14+c]=ap(c,o[b2+a*14+b]);
}
void recgen(int n,int p,A&a,unordered_set<uint64_t>&seen,vector<A>&r){
 if(p==n){auto s=rs(a);if(seen.insert(s).second)r.push_back(a);return;}
 for(int v=-18;v<=18;v++){a.x[p]=v;recgen(n,p+1,a,seen,r);}
}
int main(){
 auto t0=chrono::steady_clock::now();
 vector<A> seed;A a{};a.n=0;seed.push_back(a);
 for(int n=1;n<=3;n++){a.n=n;vector<int> idx(n,-4);while(1){for(int i=0;i<n;i++)a.x[i]=idx[i];seed.push_back(a);int k=n-1;while(k>=0&&idx[k]==4)k--;if(k<0)break;idx[k]++;for(int j=k+1;j<n;j++)idx[j]=-4;}}
 int e[3][4]={{-4,-4,-4,-3},{-4,-3,-4,-2},{-4,-3,-2,-3}};for(auto &v:e){a.n=4;for(int i=0;i<4;i++)a.x[i]=v[i];seed.push_back(a);}
 if(seed.size()!=823){cerr<<"SEED "<<seed.size()<<"\n";return 3;}
 const int N=2955;vector<int> cl(N,0),rep;vector<A> o(N);vector<uint64_t> out(N);
 int C=1;
 for(auto &x:seed){
  allout(x,o);for(int i=0;i<N;i++)out[i]=oc(o[i]);
  struct H{size_t operator()(uint64_t x)const{return x^(x>>31);}};unordered_map<uint64_t,int,H> m;vector<int> nc(N);int ncx=0;
  for(int i=0;i<N;i++){uint64_t k=((uint64_t)cl[i]<<48)|out[i];auto it=m.find(k);if(it==m.end()){m[k]=ncx;nc[i]=ncx++;}else nc[i]=it->second;}
  cl.swap(nc);C=ncx;
 }
 cout<<"seed_classes="<<C<<"\n";if(C!=809)return 4;
 rep.assign(C,-1);for(int i=0;i<N;i++)if(rep[cl[i]]<0)rep[cl[i]]=i;
 unordered_set<uint64_t> seen;vector<A> r;seen.reserve(100000);r.reserve(100000);
 a.n=0;seen.insert(rs(a));r.push_back(a);
 for(int n=1;n<=4;n++){a.n=n;recgen(n,0,a,seen,r);}
 cout<<"relation_types="<<r.size()<<"\n";
 if(r.size()!=92457)return 5;
 long long checked=0;
 for(auto &x:r){
  allout(x,o);for(int i=0;i<N;i++)out[i]=oc(o[i]);
  for(int i=0;i<N;i++)if(out[i]!=out[rep[cl[i]]]){cerr<<"SPLIT class="<<cl[i]<<" prog="<<i<<"\n";return 6;}
  checked++;
 }
 auto ms=chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now()-t0).count();
 cout<<"PASS programs=2955 classes=809 inputs="<<checked<<" ms="<<ms<<"\n";
}