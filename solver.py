# 人の解き方をまねたソルバーで難しさを測る。
# 使うのは「列ごとの計算（繰り上がり・繰り下がり）」「1 桁を掛けた行」「同じ数字を写す」「各数字 m 個ずつ」だけ。
# それで決まらなければ仮に置いて試す（当てずっぽう）。その回数を数え、levels.json に書く。
# 使い方: python3 solver.py [番号...]
import json,re,sys,itertools,math

class CSP:
    def __init__(s,n,m):
        s.n,s.m=n,m; s.k=list(range(n)) if m=='tri' else [m]*n; s.dom=[]; s.cells=[]; s.cons=[]; s.cache={}
    def var(s,cell=True,dom=None):
        s.dom.append(set(range(s.n)) if dom is None else set(dom))
        if cell: s.cells.append(len(s.dom)-1)
        return len(s.dom)-1
    def num(s,L):  # 書いてある数。いちばん左は 0 でない
        v=[s.var() for _ in range(L)]; s.dom[v[0]].discard(0); return v
    def const0(s): return s.var(False,{0})

def build(p):
    n,m,op,r=p['n'],p['m'],p['op'],p['rows']; c=CSP(n,m)
    def col(inputs,out,cout):  # sum(inputs) = out + n*cout
        c.cons.append(('col',inputs,out,cout))
    def carry(k): return c.var(False,range(k+1))
    def addcols(rows,res):  # rows: [(vars, shift)] を足して res（右端そろえ）
        cin=c.const0()
        for k in range(len(res)):
            ins=[v[len(v)-1-(k-o)] for v,o in rows if 0<=k-o<len(v)]+[cin]
            cout=c.const0() if k==len(res)-1 else carry(len(ins))
            col(ins,res[len(res)-1-k],cout); cin=cout
    if op=='+':
        a,b,cc=re.match(r'(\d+)\+(\d+)=(\d+)',r).groups()
        A,B,C=c.num(len(a)),c.num(len(b)),c.num(len(cc)); addcols([(A,0),(B,0)],C); c.rows=[A,B,C]
        sol=lambda A_,B_:[A_,B_,A_+B_]
    elif op=='*':
        head,pp=r.split(' → '); a,rest=head.split('×'); b,*parts=rest.split()
        offs=[int(t.split('@')[1]) for t in p['shape'].split(',') if '@' in t]
        A,B=c.num(len(a)),c.num(len(b)); P=c.num(len(pp)); c.rows=[A,B]
        if parts:
            rows=[]
            for o,s in zip(offs,parts):
                R=c.num(len(s)); c.cons.append(('mul',A,B[len(B)-1-o],R)); rows.append((R,o)); c.rows.append(R)
            for o in range(len(B)):
                if o not in offs: c.dom[B[len(B)-1-o]]={0}
            addcols(rows,P)
        c.rows.append(P)
        if not parts:
            for v in B[1:]: c.dom[v]={0}
            o=len(B)-1
            for v in P[len(P)-o:]: c.dom[v]={0}
            c.cons.append(('mul',A,B[0],P[:len(P)-o]))
        def sol(A_,B_):
            out=[A_,B_]; bd=[int(x) for x in reversed(digits(B_,n))]
            if parts: out+=[A_*d for d in bd if d]
            return out+[A_*B_]
    else:
        m_=re.match(r'(\d+)÷(\d+)=(\d+)(?:…\d+)? \|(.*)',r); D,a,q,rest=m_.groups(); steps=rest.split()
        sh=p['shape'].split(',')[3:]; lD=len(D)
        if op=='/r': rem=steps.pop(); sh.pop()  # 最後の行はあまり
        Q=c.num(len(q)); A=c.num(len(a)); Dv=c.num(lD)
        qcol={lD-len(q)+i:Q[i] for i in range(len(q))}
        st=[]  # [(kind, vars, end)]
        for t,s in zip(sh,steps): st.append((t[0],c.num(len(s)),int(t.split('@')[1])))
        c.rows=[Q,A,Dv]+[v for _,v,_ in st]
        if op=='/0': c.rows.append([c.var(True,{0})])  # 最後のあまり 0 も空欄
        Rv=c.num(len(rem)) if op=='/r' else []
        if Rv: c.rows.append(Rv)
        ends=[e for k,_,e in st if k=='p']
        for col_,v in qcol.items():
            if col_ not in ends: c.dom[v]={0}
        prods=[(v,e) for k,v,e in st if k=='p']; works=[(v,e) for k,v,e in st if k=='w']
        W=[(Dv[:prods[0][1]+1],prods[0][1])]+works+([(Rv,lD-1)] if Rv else [])  # 引かれる数（最後はあまり）
        Z=c.const0()
        for i,((Pv,e),(Wv,_)) in enumerate(zip(prods,W)):
            c.cons.append(('mul',A,qcol[e],Pv))
            s0=e-len(Wv)+1
            nxt=W[i+1] if i+1<len(W) else None
            def Rat(cc_):
                if nxt is None: return Z
                Wn,en=nxt; sn=en-len(Wn)+1
                return Wn[cc_-sn] if cc_>=sn else Z
            bin_=c.const0()
            for cc_ in range(e,s0-1,-1):
                Pd=Pv[cc_-(e-len(Pv)+1)] if cc_>=e-len(Pv)+1 else Z
                bout=c.const0() if cc_==s0 else carry(2)
                col([Pd,bin_,Rat(cc_)],Wv[cc_-s0],bout); bin_=bout
            if nxt:  # おろしてくる数字
                Wn,en=nxt; sn=en-len(Wn)+1
                for cc_ in range(e+1,en+1):
                    if cc_>=sn: c.cons.append(('eq',Wn[cc_-sn],Dv[cc_]))
                    else: c.dom[Dv[cc_]]={0}
        if not Rv:
            for cc_ in range(prods[-1][1]+1,lD): c.dom[Dv[cc_]]={0}
        c.Rv=Rv
        A,B=A,Q  # 自由な 2 数: 割る数と商
        def sol(A_,B_,R_=0):
            Dn=A_*B_+R_; out=[B_,A_,Dn]; cur=0; first=True; ds=[int(x) for x in digits(Dn,n)]
            for j,dj in enumerate(ds):
                cur=cur*n+dj; qq=cur//A_
                if qq:
                    if not first: out.append(cur)
                    first=False; out.append(qq*A_); cur-=qq*A_
            return out+([0] if op=='/0' else [])+([R_] if op=='/r' else [])
    c.A,c.B,c.sol=A,B,sol
    if not hasattr(c,'Rv'): c.Rv=[]
    return c

def digits(x,n):
    s=''
    while x: s=str(x%n)+s; x//=n
    return s or '0'

def revise(c,con,dom):
    k=con[0]; n=c.n
    if k=='eq':
        _,x,y=con; t=dom[x]&dom[y]
        if t!=dom[x] or t!=dom[y]: dom[x]=set(t); dom[y]=set(t); return [x,y] if t else None
        return []
    if k=='col':
        _,ins,out,cout=con; sup=[set() for _ in ins]; so=set(); sc=set()
        for combo in itertools.product(*[sorted(dom[v]) for v in ins]):
            t=sum(combo); o,cy=t%n,t//n
            if o in dom[out] and cy in dom[cout]:
                for i,x in enumerate(combo): sup[i].add(x)
                so.add(o); sc.add(cy)
        ch=[]
        for v,sp in list(zip(ins,sup))+[(out,so),(cout,sc)]:
            if dom[v]-sp:
                dom[v]&=sp; ch.append(v)
                if not dom[v]: return None
        return ch
    if k=='mul':
        _,A,d,R=con
        key=('mul',tuple(A),d,tuple(R),tuple(frozenset(dom[v]) for v in A+[d]+R))
        if key in c.cache: res=c.cache[key]
        else:
            supA=[set() for _ in A]; sd=set(); sR=[set() for _ in R]; L=len(R)
            Rd=[dom[v] for v in R]
            for ad in itertools.product(*[sorted(dom[v]) for v in A]):
                av=0
                for x in ad: av=av*n+x
                for dv in dom[d]:
                    pv=av*dv; ok=True; rd=[]
                    for i in range(L-1,-1,-1):
                        x=pv%n; pv//=n
                        if x not in Rd[i]: ok=False; break
                        rd.append(x)
                    if not ok or pv: continue
                    if L>1 and rd[-1]==0: continue
                    for i,x in enumerate(ad): supA[i].add(x)
                    sd.add(dv)
                    for i,x in enumerate(reversed(rd)): sR[i].add(x)
            res=(supA,sd,sR); c.cache[key]=res
        supA,sd,sR=res; ch=[]
        for v,sp in list(zip(A,supA))+[(d,sd)]+list(zip(R,sR)):
            if dom[v]-sp:
                dom[v]&=sp; ch.append(v)
                if not dom[v]: return None
        return ch

def count(c,dom):  # 各数字ちょうど m 個（tri は d を d 個）
    ch=[]
    for d in range(c.n):
        fixed=[v for v in c.cells if dom[v]=={d}]; poss=[v for v in c.cells if d in dom[v] and len(dom[v])>1]
        k=c.k[d]
        if len(fixed)>k or len(fixed)+len(poss)<k: return None
        if len(fixed)==k:
            for v in poss: dom[v].discard(d); ch.append(v)
        elif len(fixed)+len(poss)==k:
            for v in poss: dom[v]={d}; ch.append(v)
    for v in ch:
        if not dom[v]: return None
    return ch

def propagate(c,dom):
    while True:
        changed=False
        for con in c.cons:
            r=revise(c,con,dom)
            if r is None: return False
            changed|=bool(r)
        r=count(c,dom)
        if r is None: return False
        if r: changed=True
        if not changed: return True

def val(vs,dom,n):
    x=0
    for v in vs: x=x*n+next(iter(dom[v]))
    return x

def solve(c):
    stats={'guess':0,'sol':0}
    def rec(dom):
        if not propagate(c,dom): return
        open_=[v for v in c.cells if len(dom[v])>1]
        if not open_:
            # 検算: 自由な 2 数から全部の行を作り直して比べる
            A_,B_=val(c.A,dom,c.n),val(c.B,dom,c.n)
            want=''.join(digits(x,c.n) for x in (c.sol(A_,B_,val(c.Rv,dom,c.n)) if c.Rv else c.sol(A_,B_)))
            got=''.join(str(next(iter(dom[v]))) for R in c.rows for v in R)
            if want==got: stats['sol']+=1
            return
        stats['guess']+=1
        v=min(open_,key=lambda v:len(dom[v]))
        for x in sorted(dom[v]):
            d2=[set(s) for s in dom]; d2[v]={x}; rec(d2)
    rec([set(s) for s in c.dom])
    return stats

if __name__=='__main__':
    ps=json.load(open('problems.json'))
    want=[int(a) for a in sys.argv[1:]]
    try: out=json.load(open('levels.json'))
    except FileNotFoundError: out={}
    for p in ps:
        if want and p['no'] not in want: continue
        c=build(p); st=solve(c)
        out[str(p['no'])]=st; json.dump(out,open('levels.json','w'),indent=1)
        print(p['no'],p['n'],p['op'],len(c.cells),st,flush=True)
