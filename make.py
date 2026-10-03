# 先に python3 solver.py でレベルを測っておく（新しい問題を足したら solver.py <番号>）
# 使い方: python3 make.py            → mushikui.pdf（全問＋答え）
#         python3 make.py 7 11 24    → mushikui-7-11-24.pdf（指定した番号だけ）
#         python3 make.py lv3        → mushikui-lv3.pdf（レベルで選ぶ。番号と混ぜてもよい）
import json,re,sys,subprocess,math
P={p['no']:p for p in json.load(open('problems.json'))}
G={int(k):v['guess'] for k,v in json.load(open('levels.json')).items()}  # solver.py が書く
def level(p):  # ソルバーの当てずっぽうの回数で 5 段階
    return 1+sum(G[p['no']]>t for t in (2,20,200,3000))
nos=[]
for a in (sys.argv[1:] if __name__=='__main__' else []):
    nos+= [k for k in sorted(P) if level(P[k])==int(a[2:])] if a.lower().startswith('lv') else [int(a)]
nos=nos or sorted(P)
OPN={'+':'足し算','*':'掛け算','/':'割り算','/0':'割り算（割り切れる）','/r':'割り算（あまりあり）'}
H=1.2  # 行の高さ

def layout(p):
    """(cells[(x,row,digit)], lines[(x0,x1,row)], marks[tikz]) 。x はマスの左端"""
    op,r=p['op'],p['rows']; cells=[];lines=[];marks=[]
    def put(s,right,row):  # right = 一番右のマスの x
        for i,ch in enumerate(s): cells.append((right-len(s)+1+i,row,ch))
    if op in '+*':
        if op=='+':
            a,b,c=re.match(r'(\d+)\+(\d+)=(\d+)',r).groups(); parts=[]; sym='+'
        else:
            head,c=r.split(' → '); a,rest=head.split('×'); b,*parts=rest.split()
            offs=[int(t.split('@')[1]) for t in p['shape'].split(',') if '@' in t]; sym=r'\times'
        put(a,-1,0); put(b,-1,1)
        rows=[(c,0)] if not parts else list(zip(parts,offs))+[(c,0)]
        W=max([len(a),len(b)+1]+[len(s)+o for s,o in rows])
        marks.append(r'\node at (%.2f,%.2f) {$%s$};'%(-W-0.5,-H*1+0.5,sym))  # 記号はいちばん左の桁のさらに 1 つ左。線もその下まで
        lines.append((-W-1,0,1)); row=2
        for i,(s,o) in enumerate(rows):
            if parts and i==len(rows)-1: lines.append((-W-1,0,row-1))
            put(s,-1-o,row); row+=1
        return cells,lines,marks
    m=re.match(r'(\d+)÷(\d+)=(\d+)(?:…\d+)? \|(.*)',r); D,a,q,rest=m.groups(); steps=rest.split()
    rem=steps.pop() if op=='/r' else None
    put(q,len(D)-1,0); put(D,len(D)-1,1); put(a,-2,1)
    marks.append(r'\draw[thick] (-0.35,%.2f) -- (%d,%.2f);'%(-H+1.05,len(D),-H+1.05))
    marks.append(r'\draw[thick] (-0.35,%.2f) arc[start angle=70,end angle=-70,x radius=0.35,y radius=0.58];'%(-H+1.05))
    js=[t for t in p['shape'].split(',')[3:] if t[0]!='r']
    for i,(t,s) in enumerate(zip(js,steps)):
        j=int(t.split('@')[1]); put(s,j,2+i)
        if t[0]=='p': lines.append((j-len(s)+1,j+1,2+i))
    last=2+len(js); x=len(D)-1  # 最後のあまり 0
    if rem: put(rem,x,last)  # あまり（空欄）
    elif p['op']=='/0': cells.append((x,last,'0'))  # 空欄（数字の個数に入る）
    else: marks.append(r'\node at (%.2f,%.2f) {0};'%(x+.5,-H*last+.5))  # 枠なしで印刷
    return cells,lines,marks

def pic(p,ans,u):
    cells,lines,marks=layout(p); out=[r'\begin{tikzpicture}[x=%.3fcm,y=%.3fcm,font=\sffamily\large]'%(u,u)]
    for x,row,ch in cells:
        y=-H*row
        out.append(r'\draw (%.2f,%.2f) rectangle (%.2f,%.2f);'%(x+.08,y+.08,x+.92,y+.92))
        if ans: out.append(r'\node at (%.2f,%.2f) {%s};'%(x+.5,y+.5,ch))
    for x0,x1,row in lines: out.append(r'\draw[thick] (%.2f,%.2f) -- (%.2f,%.2f);'%(x0-.1,-H*row-.12,x1+.1,-H*row-.12))
    out+=marks+[r'\end{tikzpicture}']; return '\n'.join(out)

def width(p):
    xs=[c[0] for c in layout(p)[0]]; return max(xs)-min(xs)+2+(p['op'] in '+*')  # × と + の 1 マス

def block(p,ans,narrow):
    n,m=p['n'],p['m']; w=width(p); box=0.47 if narrow else 1.0
    u=min(0.62 if not ans else 0.42, (16.5*box-0.5)/w)
    head=(r'\footnotesize ' if narrow else '')+r'\textbf{No.%d}\ \ \textbf{Lv.%d}\quad %d 進数・%s\quad '%(p['no'],level(p),n,OPN[p['op']])+(r'1 を 1 個〜%d を %d 個（空欄 %d）'%(n-1,n-1,n*(n-1)//2) if m=='tri' else r'0〜%d を各 %d 個（空欄 %d）'%(n-1,m,n*m))
    return r'\begin{minipage}[t]{%.2f\linewidth}%s\par\medskip\centering %s\end{minipage}'%(box,head,pic(p,ans,u)), narrow

def section(ans):
    out=[];i=0
    while i<len(nos):  # 狭いものが 2 つ続いたら横に並べる
        if i+1<len(nos) and all(width(P[k])<=12 and P[k]['op'] in '+*/' for k in nos[i:i+2]):
            out.append('\n\n\\bigskip\\noindent'+block(P[nos[i]],ans,True)[0]+'\\hfill'+block(P[nos[i+1]],ans,True)[0]); i+=2
        else:
            out.append('\n\n\\bigskip\\noindent'+block(P[nos[i]],ans,False)[0]); i+=1
    return '\n'.join(out)

if __name__=='__main__':
    name='mushikui'+(''.join('-'+a.lower() for a in sys.argv[1:]))
    tex=r'''\documentclass[a4paper,11pt]{ltjsarticle}
    \usepackage[margin=18mm]{geometry}\usepackage{tikz}\pagestyle{plain}
    \begin{document}
    \section*{虫食い筆算（%s）}
    \noindent □ には $n$ 進数の数字 0〜$n-1$ が 1 つずつ入る。各数字はちょうど $m$ 個ずつ使う（空欄は $mn$ 個）。「1 を 1 個〜」の問題は、数字 $d$ をちょうど $d$ 個使い、0 は使わない。
    いちばん左の桁は 0 ではない。掛け算でかける数に 0 の桁があるとき、その部分積の行は書かない。
    割り算の最後の行はあまり。枠なしの 0 は数えない。枠つきなら空欄で、個数に入る。どの問題も答えは 1 つ。
    レベルは、計算と数字の個数だけで決めていくソルバーが、決まらずに仮に置いて試した回数で 5 段階に分けた（Lv.1: 2 回以下、Lv.2: 20 回まで、Lv.3: 200 回まで、Lv.4: 3000 回まで、Lv.5: それより上）。

    \medskip\noindent\begin{tabular}{@{}ll@{}}%s\end{tabular}
    %s
    \newpage\section*{答え}
    %s
    \end{document}'''%('No.'+', '.join(map(str,nos)) if sys.argv[1:] else '全 %d 問'%len(nos),
     ''.join(r'Lv.%d & No.\ %s\\'%(L,', '.join(str(k) for k in nos if level(P[k])==L)) for L in range(1,6) if any(level(P[k])==L for k in nos)),section(False),section(True))
    open(name+'.tex','w').write(tex)
    for _ in range(2): subprocess.run(['lualatex','-interaction=nonstopmode',name+'.tex'],check=True,capture_output=True)
    print(name+'.pdf')
