# /// script
# dependencies = ["segno", "pillow"]
# ///
# 掲示用の PDF と Web ページを作る
# 使い方: issues.json に {"no": 回, "title": "虫食い算", "problem": 問題番号, "date": "YYYY-MM-DD"} を足してから
#         uv run poster.py 3    → posters/第3回.pdf と 3/index.html、一覧の index.html
#         uv run poster.py      → 全部の回を作り直す
import itertools, json, os, re, subprocess, sys, html, segno
from make import P, pic, width, layout, OPN, H

URL = 'https://sora3141.github.io/labo-quiz/'
CLUB = 'らぼらとらい'
issues = json.load(open('issues.json'))
os.makedirs('build', exist_ok=True); os.makedirs('posters', exist_ok=True); os.makedirs('img', exist_ok=True)

def tex(name, body):
    open(f'build/{name}.tex', 'w').write(body)
    subprocess.run(['lualatex', '-interaction=nonstopmode', '-output-directory=build', f'build/{name}.tex'], check=True, capture_output=True)
    return f'build/{name}.pdf'

def rule(p):  # ルール文 (日本語, 英語)。LaTeX の数式で書く（Web では uni() で Unicode にする）
    n, m, op = p['n'], p['m'], p['op']
    D = '$' + ','.join(str(i) if i < 10 else r'\mathrm{%s}' % 'ABCDEF'[i - 10] for i in range(1 if m == 'tri' else 0, n)) + '$'  # 使う数字を全部並べる（例: 0,1,…,6）
    ja = (f'{D} を 1 つずつ □ に入れ、' if m == 1 else f'各 □ に {D} のどれかを入れ、') + f'{n} 進法で正しい{ {"+": "足し算の筆算", "*": "掛け算の筆算", "/": "割り算の筆算", "x": "掛け算の式"}[op[0]] }を完成させよ。'
    en = (f'Place each of {D} in one □' if m == 1 else f'Fill each □ with one of {D}') + f' so that the { {"+": "addition", "*": "long multiplication", "/": "long division", "x": "multiplication"}[op[0]] } is correct in base {n}. '
    if op == 'x':
        ja += '掛ける数は左から小さい順に並ぶ。'; en += 'The factors are in increasing order from left to right. '
    if m == 'tri':
        ja += f'数字 $d$ はちょうど $d$ 回使う（$1 \\le d \\le {n-1}$）。'; en += f'Each digit $d$ is used exactly $d$ times ($1 \\le d \\le {n-1}$). '
    elif m != 1:
        ja += f'各数字をちょうど {m} 回ずつ使う。'; en += f'Each digit is used exactly {m} times. '
    if op[0] == '/':
        ja += '最下行は剰余。枠のない 0 は □ に数えない。'; en += 'The bottom row is the remainder; an unboxed 0 is not a box. '
    return ja + '解は一意である。', en + 'The solution is unique.'

def uni(t):  # Web 用に LaTeX の数式を Unicode に
    t = re.sub(r'\\mathrm\{(\w)\}', r'\1', t)
    for a, b in [(r'\{', '{'), (r'\}', '}'), (r'\dots', '…'), (r'\le', '≤'), (r'\times', '×'), ('$', '')]: t = t.replace(a, b)
    return html.escape(t)

def svg(name, p, ans):  # 問題・答えの図を SVG に
    svgtex(name, pic(p, ans, 0.6))

def svgtex(name, code):  # TikZ の図を SVG に
    # standalone.cls が無いので、図の箱の大きさにページを合わせて直接出す
    pdf = tex(name, r'''\documentclass{article}\usepackage{luatexja,tikz}\begin{document}\sffamily
\setbox0\hbox{\kern4pt\vbox{\kern4pt\hbox{%s}\kern4pt}\kern4pt}
\pagewidth=\wd0 \pageheight=\dimexpr\ht0+\dp0\relax \hoffset=-1in \voffset=-1in \shipout\box0
\end{document}''' % code)
    subprocess.run(['pdftocairo', '-svg', pdf, f'img/{name}.svg'], check=True)

# オセロの回（issues.json で "kind": "othello"）。最短手数と手順は solver で確かめた（9 手、黒 13・白 0）
OTH_RULE = ('オセロ（リバーシ）を下の初期配置から始める。黒が先手。どちらも石を置けなくなったら対局は終わる。'
            '対局が終わるまでに、最短で何手かかるか。',
            'An Othello (Reversi) game starts from the position below, with Black to move first. '
            'The game ends when neither player can place a disc. What is the fewest number of moves in which a game can end?')
OTH_MOVES = 'f5 f6 f7 f4 f3 e3 d3 g7 h8'.split()

def board(unit):  # 初期配置の盤（unit はマスの大きさ mm）
    discs = ''.join(r'\filldraw[fill=%s,draw=black,line width=.8pt] (%.1f,%.1f) circle (.4);' % (c, x + .5, y + .5)
                    for c, x, y in [('white', 3, 3), ('black', 4, 3), ('black', 3, 4), ('white', 4, 4)])
    return r'''\begin{tikzpicture}[x=%smm,y=-%smm]
\fill[green!55!black] (0,0) rectangle (8,8);
\foreach \i in {1,...,7} {\draw[line width=.6pt] (\i,0)--(\i,8); \draw[line width=.6pt] (0,\i)--(8,\i);}
\draw[line width=1.6pt] (0,0) rectangle (8,8);
\foreach \x/\y in {2/2,6/2,2/6,6/6} \fill (\x,\y) circle (.07);
\foreach \c [count=\i from 0] in {a,b,c,d,e,f,g,h} \node at (\i+.5,-.4) {\c};
\foreach \i in {1,...,8} \node at (-.4,\i-.5) {\i};
%s\end{tikzpicture}''' % (unit, unit, discs)

def othello_web(no):  # 答えのページ: 手順を盤の上で再生できる。途中から自分で打つこともできる
    return f'''
<details><summary>Answer</summary>
<p class="ans"><b>9 手</b>（黒 13・白 0 で黒の勝ち）</p>
<p>9 手目で白の石が盤からなくなり、どちらも置けなくなります。手順の一例: {' '.join(OTH_MOVES)}</p>
<p lang="en"><b>9 moves</b>. Black wins 13–0: after the 9th move no white discs remain, so neither player can move.</p>
<div id="oth"><svg id="bd" viewBox="-30 -30 830 830" role="img" aria-label="オセロの盤"></svg>
<p id="st" aria-live="polite"></p>
<p class="ctl"><button id="b0">⏮</button><button id="bp">◀</button><button id="pl">▶ 再生</button><button id="bn">▶|</button><button id="b9">⏭</button></p>
<ol id="mv"></ol>
<p class="meta">点（・）のマスをクリックすると、そこから自分で打てます。⏮ で最初に戻ります。</p></div>
</details>
<script>
const SOL={OTH_MOVES!r}, N=8, D=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
let hist=[], timer=null;
function init(){{const b=Array.from({{length:N}},()=>Array(N).fill(0));b[3][3]=b[4][4]=2;b[3][4]=b[4][3]=1;return b;}}
function flips(b,x,y,c){{if(b[y][x])return[];let r=[];for(const[dx,dy]of D){{let t=[],i=x+dx,j=y+dy;while(i>=0&&i<N&&j>=0&&j<N&&b[j][i]===3-c){{t.push([i,j]);i+=dx;j+=dy;}}if(t.length&&i>=0&&i<N&&j>=0&&j<N&&b[j][i]===c)r=r.concat(t);}}return r;}}
function legal(b,c){{let r=[];for(let y=0;y<N;y++)for(let x=0;x<N;x++)if(flips(b,x,y,c).length)r.push([x,y]);return r;}}
function state(ms){{let b=init(),c=1;for(const m of ms){{if(!legal(b,c).length)c=3-c;const x=m.charCodeAt(0)-97,y=+m[1]-1;for(const[i,j]of flips(b,x,y,c))b[j][i]=c;b[y][x]=c;c=3-c;}}if(!legal(b,c).length)c=3-c;return{{b,c,over:!legal(b,1).length&&!legal(b,2).length}};}}
let moves=[...SOL], k=0;
function draw(){{const{{b,c,over}}=state(moves.slice(0,k)),L=over?[]:legal(b,c),last=moves[k-1];let s='<rect width="800" height="800" fill="#1f8a4c"/>';
for(let i=0;i<=N;i++)s+=`<line x1="${{i*100}}" y1="0" x2="${{i*100}}" y2="800" stroke="#000" stroke-width="${{i%8?2:5}}"/><line x1="0" y1="${{i*100}}" x2="800" y2="${{i*100}}" stroke="#000" stroke-width="${{i%8?2:5}}"/>`;
for(let i=0;i<N;i++)s+=`<text x="${{i*100+50}}" y="-8" text-anchor="middle" font-size="28">${{'abcdefgh'[i]}}</text><text x="-15" y="${{i*100+60}}" text-anchor="middle" font-size="28">${{i+1}}</text>`;
let nb=0,nw=0;for(let y=0;y<N;y++)for(let x=0;x<N;x++){{const v=b[y][x];if(!v)continue;v===1?nb++:nw++;s+=`<circle cx="${{x*100+50}}" cy="${{y*100+50}}" r="40" fill="${{v===1?'#111':'#fff'}}" stroke="#000" stroke-width="2"/>`;}}
if(last){{const x=last.charCodeAt(0)-97,y=+last[1]-1;s+=`<circle cx="${{x*100+50}}" cy="${{y*100+50}}" r="9" fill="#e33"/>`;}}
for(const[x,y]of L)s+=`<circle cx="${{x*100+50}}" cy="${{y*100+50}}" r="10" fill="${{c===1?'#000':'#fff'}}" opacity=".45"/><rect class="hit" data-m="${{'abcdefgh'[x]+(y+1)}}" x="${{x*100}}" y="${{y*100}}" width="100" height="100" fill="transparent"/>`;
bd.innerHTML=s;
st.textContent=`${{k}} 手目　黒 ${{nb}}・白 ${{nw}}　`+(over?'対局終了':`${{c===1?'黒':'白'}}の番`);
mv.innerHTML=moves.map((m,i)=>`<li class="${{i<k?'done':''}}${{i===k-1?' cur':''}}">${{i%2?'白':'黒'}} ${{m}}</li>`).join('');}}
function go(n){{k=Math.max(0,Math.min(moves.length,n));draw();}}
function stop(){{clearInterval(timer);timer=null;pl.textContent='▶ 再生';}}
b0.onclick=()=>{{stop();moves=[...SOL];go(0);}};bp.onclick=()=>{{stop();go(k-1);}};bn.onclick=()=>{{stop();go(k+1);}};b9.onclick=()=>{{stop();go(moves.length);}};
pl.onclick=()=>{{if(timer)return stop();if(k>=moves.length)go(0);pl.textContent='❚❚ 停止';timer=setInterval(()=>{{if(k>=moves.length)return stop();go(k+1);}},900);}};
bd.onclick=e=>{{const m=e.target.dataset&&e.target.dataset.m;if(!m)return;stop();moves=moves.slice(0,k).concat(m);go(k+1);}};
draw();
</script>'''

# 一様乱数の和の回（"kind": "uniform"）。答えは e。P(N > n) = P(U1+…+Un ≤ 1) = 1/n! を足し合わせる
UNI_RULE = ('区間 $[0,1]$ の一様乱数を 1 つずつ足していき、和が初めて 1 を超えたら止める。'
            '足した乱数の個数の期待値はいくらか。',
            'Add random numbers drawn independently and uniformly from $[0,1]$ one at a time, '
            'and stop as soon as the sum exceeds 1. What is the expected number of random numbers added?')
def simplex(unit):  # 答えの図: 和が 1 以下になる部分（n=2 は三角形、n=3 は三角錐）
    return r'''\begin{tikzpicture}[x=%smm,y=%smm]
\draw (0,0) rectangle (1,1); \fill[blue!35] (0,0)--(1,0)--(0,1)--cycle; \draw[blue!70!black,line width=1pt] (1,0)--(0,1);
\node[below] at (.5,0) {$U_1$}; \node[left] at (0,.5) {$U_2$}; \node at (.3,.3) {$\frac12$};
\node[below] at (.5,-.25) {$n=2$};
\begin{scope}[xshift=%smm,x={(%smm,0)},y={(0,%smm)},z={(-%smm,-%smm)}]
\draw[gray] (1,0,0)--(1,1,0)--(0,1,0) (0,0,1)--(1,0,1)--(1,1,1)--(0,1,1)--cycle (1,0,0)--(1,0,1) (1,1,0)--(1,1,1) (0,1,0)--(0,1,1);
\fill[blue!35,opacity=.85] (1,0,0)--(0,1,0)--(0,0,1)--cycle; \draw[blue!70!black,line width=1pt] (1,0,0)--(0,1,0)--(0,0,1)--cycle;
\draw[blue!70!black,dashed] (0,0,0)--(1,0,0) (0,0,0)--(0,1,0) (0,0,0)--(0,0,1);
\node[right] at (1,0,0) {$U_1$}; \node[above] at (0,1,0) {$U_2$}; \node[left] at (0,0,1) {$U_3$}; \node at (.3,.3,.3) {$\frac16$};
\node[below] at (.5,-.08,1) {$n=3$};
\end{scope}\end{tikzpicture}''' % (unit, unit, 2.1 * unit, unit, unit, .45 * unit, .3 * unit)

def uniform_web(no):  # 答えのページ: 解説と、ブラウザで試せるシミュレーション
    return f'''
<details><summary>Answer</summary>
<p class="ans"><b><i>e</i> = 2.71828…</b></p>
<p lang="en">The expected number is <i>e</i>.</p>
<h2>解説</h2>
<p>足した個数を <i>N</i> とします。「<i>n</i> 個足してもまだ止まらない」のは「<i>n</i> 個の和が 1 以下」のときなので</p>
<p class="eq"><i>P</i>(<i>N</i> &gt; <i>n</i>) = <i>P</i>(<i>U</i><sub>1</sub> + … + <i>U</i><sub><i>n</i></sub> ≤ 1)</p>
<p>この確率は、<i>n</i> 次元の立方体のうち和が 1 以下の部分の体積です。<i>n</i> = 2 なら三角形で 1/2、<i>n</i> = 3 なら三角錐で 1/6。</p>
<img src="../img/{no}-a.svg" alt="n=2 の三角形（面積 1/2）と n=3 の三角錐（体積 1/6）">
<p>一般の <i>n</i> では、部分和 <i>y<sub>k</sub></i> = <i>U</i><sub>1</sub> + … + <i>U<sub>k</sub></i> に置きかえると（体積は変わらない）、条件は 0 ≤ <i>y</i><sub>1</sub> ≤ <i>y</i><sub>2</sub> ≤ … ≤ <i>y<sub>n</sub></i> ≤ 1 になります。[0,1] の <i>n</i> 個の数の並び方 <i>n</i>! 通りはどれも同じ確率なので、小さい順に並ぶ確率は 1/<i>n</i>!。</p>
<p class="eq"><i>P</i>(<i>N</i> &gt; <i>n</i>) = 1/<i>n</i>!</p>
<p>0 以上の整数をとる確率変数では <i>E</i>[<i>N</i>] = Σ<sub><i>n</i>≥0</sub> <i>P</i>(<i>N</i> &gt; <i>n</i>) なので</p>
<p class="eq"><i>E</i>[<i>N</i>] = 1/0! + 1/1! + 1/2! + 1/3! + … = <i>e</i></p>
<p>おまけ: <i>P</i>(<i>N</i> = <i>n</i>) = 1/(<i>n</i>−1)! − 1/<i>n</i>! = (<i>n</i>−1)/<i>n</i>!。2 個で止まる確率は 1/2、3 個は 1/3、4 個は 1/8。</p>
<h2>試してみる</h2>
<p class="ctl"><button id="one">1 回</button><button id="many">1000 回</button><button id="rs">リセット</button></p>
<p id="last" class="eq"></p>
<p id="avg" class="eq" aria-live="polite"></p>
</details>
<script>
let n=0, tot=0;
function run(){{let s=0,u=[];while(s<=1){{const x=Math.random();u.push(x);s+=x;}}n++;tot+=u.length;return u;}}
function show(u){{if(u)last.textContent=u.map(x=>x.toFixed(3)).join(' + ')+' = '+u.reduce((a,b)=>a+b).toFixed(3)+'  →  '+u.length+' 個';
avg.textContent=n?`${{n}} 回の平均: ${{(tot/n).toFixed(4)}}（e = 2.7183）`:'';}}
one.onclick=()=>show(run()); many.onclick=()=>{{let u;for(let i=0;i<1000;i++)u=run();show(u);}}; rs.onclick=()=>{{n=tot=0;last.textContent='';show();}};
</script>'''

# ひとり UNO の回（"kind": "uno"）。出し切る順番の数を問う（2 枚の青 3 は区別しない、逆順は別に数える）
UNO_HAND = 'R3 B2 B3 B3 B4 G2 G4 Y1 Y3'.split()
UNO_ALL = sorted({p for p in itertools.permutations(UNO_HAND) if all(a[0] == b[0] or a[1] == b[1] for a, b in zip(p, p[1:]))})
assert len(UNO_ALL) == 28
UNO_COL = {'R': ('赤', 'red!75!black', '#bf0000'), 'B': ('青', 'blue!70!cyan!80!black', '#003dcc'),
           'G': ('緑', 'green!50!black', '#008000'), 'Y': ('黄', 'yellow!85!orange', '#fde203')}
UNO_RULE = ('下の 9 枚の手札を 1 枚ずつ場に出していく。最初の 1 枚は何でもよいが、2 枚目からは直前に出したカードと'
            '色か数字が同じカードしか出せない。手札を全部出し切る順番は何通りあるか。',
            'Play the nine cards below one at a time. The first card can be any card; after that, each card must match '
            'the previous one in color or number. In how many orders can you play the whole hand?')

def cards(unit):  # 手札の図（色の名前も下に書く。白黒で印刷しても分かるように）
    t = ''
    for k, c in enumerate(UNO_HAND):
        x = k * 1.15; name, col, _ = UNO_COL[c[0]]
        t += (r'\filldraw[fill=%s,draw=black,line width=.8pt,rounded corners=1.2mm] (%.2f,0) rectangle +(1,1.5);'
              r'\filldraw[fill=white,draw=black,line width=.5pt,rotate around={30:(%.2f,.75)}] (%.2f,.75) ellipse (.36 and .58);'
              r'\node[font=\bfseries\fontsize{%d}{%d}\selectfont] at (%.2f,.75) {%s};\node at (%.2f,-.3) {%s};'
              % (col, x, x + .5, x + .5, round(unit * 1.5), round(unit * 1.5), x + .5, c[1], x + .5, name))
    return r'\begin{tikzpicture}[x=%smm,y=%smm]%s\end{tikzpicture}' % (unit, unit, t)

def uno_web(no):  # 答えのページ: 数え方の解説と 14 通りの一覧、カードを押して自分で探す遊び
    cs = {c: v[2] for c, v in UNO_COL.items()}; nm = {c: v[0] for c, v in UNO_COL.items()}
    row = lambda p: '<li>' + '　'.join(nm[c[0]] + c[1] for c in p) + '</li>'
    y1 = [p for p in UNO_ALL if p[0] == 'Y1']
    red = [p for p in y1 if p[2] == 'R3']; blue = [p for p in y1 if p[2] == 'B3']
    return f'''
<details><summary>Answer</summary>
<p class="ans"><b>{len(UNO_ALL)} 通り</b></p>
<p>2 枚の青 3 を区別すると、入れかえの分が 2 倍になって {2 * len(UNO_ALL)} 通りです。</p>
<p lang="en"><b>{len(UNO_ALL)}</b> orders ({2 * len(UNO_ALL)} if the two blue 3s are told apart).</p>
<h2>解説</h2>
<p>カードを点、続けて出せる 2 枚を線で結ぶと、「全部出し切る」は「すべての点を 1 回ずつ通る道（ハミルトン路）」になります。点が増えると探すのも数えるのも一気に難しくなる、有名な難問です。この手札は、カードのつながり方に目をつけると手で数えられます。</p>
<p><b>1. 黄 1 は端。</b>黄 1 とつながるのは黄 3 だけ（ほかに 1 も黄色もない）。だから黄 1 は最初か最後で、その隣は黄 3。黄 1 から始まる順番を数えて 2 倍すればよい。</p>
<p><b>2. 緑 2 と緑 4 は必ず隣どうし。</b>緑 2 は緑 4 と青 2、緑 4 は緑 2 と青 4 としかつながらない。</p>
<p><b>3. 赤 3 は 3 としかつながらない。</b>黄 3 のすぐ次に出すか、青 3 の隣に置くしかない。</p>
<p>黄 1・黄 3 のあと、3 枚目が赤 3 か青 3 かで分けます。</p>
<p><b>3 枚目が赤 3：{len(red)} 通り</b></p><ol class="seq">{''.join(map(row, red))}</ol>
<p><b>3 枚目が青 3：{len(blue)} 通り</b>（赤 3 は 2 枚の青 3 の間か、いちばん最後）</p><ol class="seq">{''.join(map(row, blue))}</ol>
<p class="eq">（{len(red)} + {len(blue)}）× 2 = {len(UNO_ALL)}</p>
<p>× 2 は、それぞれを逆から出す順番（黄 1 で終わる）の分です。</p>
<h2>やってみる</h2>
<div id="hand" class="uno"></div>
<p id="st" aria-live="polite"></p>
<div id="pile" class="uno"></div>
<p class="ctl"><button id="rs">やり直す</button></p>
<p id="fd" class="eq"></p>
</details>
<script>
const H={UNO_HAND!r}, C={cs!r}, NM={nm!r}, ALL={len(UNO_ALL)}, found=new Set();
let used=[], seq=[];
const ok=i=>!used[i]&&(!seq.length||H[seq.at(-1)][0]===H[i][0]||H[seq.at(-1)][1]===H[i][1]);
const card=(i,b)=>`<button style="background:${{C[H[i][0]]}}" aria-label="${{NM[H[i][0]]}} ${{H[i][1]}}" data-n="${{NM[H[i][0]]}}" ${{b?'':'disabled'}} data-i="${{i}}"><span>${{H[i][1]}}</span></button>`;
function draw(){{hand.innerHTML=H.map((_,i)=>used[i]?'':card(i,ok(i))).join('');pile.innerHTML=seq.map(i=>card(i,false)).join('');
const left=H.length-seq.length,key=seq.map(i=>H[i]).join(' ');let msg=`残り ${{left}} 枚。出せるカードを押してください`;
if(!left){{msg=found.has(key)?'出し切った！（もう見つけた順番）':'出し切った！ 新しい順番です';found.add(key);}}else if(!H.some((_,i)=>ok(i)))msg=`残り ${{left}} 枚。もう出せません`;
st.textContent=msg;fd.textContent=`見つけた順番: ${{found.size}} / ${{ALL}}`;}}
hand.onclick=e=>{{const b=e.target.closest('button');if(!b)return;const i=+b.dataset.i;used[i]=true;seq.push(i);draw();}};
rs.onclick=()=>{{used=[];seq=[];draw();}};
draw();
</script>'''

def crop(name):  # ロゴの描画部分だけを切り抜く（logos/ の元画像はそのまま）
    from PIL import Image
    im = Image.open(f'logos/{name}.png').convert('RGBA')
    flat = Image.alpha_composite(Image.new('RGBA', im.size, 'white'), im).convert('RGB')
    flat.crop(flat.convert('L').point(lambda v: 255 if v < 245 else 0).getbbox()).save(f'build/{name}.png')
    return f'build/{name}.png'

def kind(i):  # 一覧などに出す種類の名前
    return {'othello': 'オセロ', 'uniform': '確率', 'uno': 'UNO'}.get(i.get('kind')) or OPN[P[i['problem']]['op']]

def poster(i):
    no = i['no']; url = f'{URL}{no}/'; oth = i.get('kind') == 'othello'; unf = i.get('kind') == 'uniform'; uno = i.get('kind') == 'uno'
    qr = segno.make(url, error='m'); qr.save(f'build/qr-{no}.pdf', scale=10, border=4)  # まわりの白 4 マスは規格で要る
    qz = 40 * 4 / qr.symbol_size(border=4)[0]  # 白 4 マスの幅（mm）。黒い部分の端を余白線にそろえるのに使う
    if oth:
        ja, en = OTH_RULE; s, fig = 1, board(13)  # 盤は 1 マス 13mm（幅 10.4cm）
    elif uno:
        ja, en = UNO_RULE; s, fig = 1, cards(15)  # カード 1 枚 15mm（9 枚で幅 16cm）
    elif unf:
        ja, en = UNI_RULE; fig = None  # 図は載せない（文だけで足りる）
    else:
        p = P[i['problem']]; ja, en = rule(p); fig = pic(p, False, 1)
        rows = max(r for _, r, _ in layout(p)[0]) + 1
        s = min(16 / width(p), 12 / (rows * H))  # 図全体（× も）を幅 16cm・高さ 12cm に収まるまで拡大（説明文が 6 行でも 1 枚に入る高さ）
    mid = (r'{\large %s\par\medskip %s\par}\vspace{8mm}\begin{center}\scalebox{%.2f}{%s}\end{center}' % (ja, en, s, fig) if fig else
           r'{\LARGE %s\par\bigskip %s\par}' % (ja, en))  # 図のない回は文を大きくする
    body = r'''\documentclass[a4paper]{ltjsarticle}
\usepackage[margin=15mm]{geometry}\usepackage{tikz,graphicx}\pagestyle{empty}
\begin{document}\sffamily\setlength{\parindent}{0pt}
%% 上: 回の番号と答えの QR（N の左の隙間 1.15mm を詰める）。文字の上端と QR の黒い部分の上端・右端を余白線にそろえる
\vspace*{-\topskip}\leavevmode\kern-1.15mm\raisebox{-\height}{\bfseries{\fontsize{48}{56}\selectfont No.%d}\quad{\fontsize{30}{36}\selectfont %s}}\hfill
\raisebox{\dimexpr-\height+%.2fmm}{\begin{minipage}[t]{40mm}\centering
\includegraphics[width=40mm]{build/qr-%d.pdf}\par\vspace{-%.2fmm}\vspace{1.5mm}{\large\bfseries Answer}\end{minipage}}\hspace{-%.2fmm}

\vfill
%% 中: ルール文と問題
%s

\vfill
%% 下: 出した側の帯。2 つのロゴは見た目の重さが合う高さ、縦の中心をそろえる
\rule{\linewidth}{0.4pt}\par\vspace{6mm}
\leavevmode\raisebox{-.5\height}{\includegraphics[height=36mm]{%s}}\hfill
\raisebox{-.5\height}{\begin{tabular}[b]{@{}c@{}}\small 過去の問題と答え\\[1mm]\footnotesize %s\end{tabular}}\hfill
\raisebox{-.5\height}{\includegraphics[height=13mm]{%s}}\par\kern0pt  %% 下に出る深さも本文の高さに入れて、下の余白にはみ出さない
\end{document}''' % (no, i['title'], qz, no, qz, qz, mid, crop('labo'), URL, crop('jaist'))
    os.replace(tex(f'poster-{no}', body), f'posters/第{no}回.pdf')
    if oth: svgtex(f'{no}-q', board(7))
    elif uno: svgtex(f'{no}-q', cards(9))
    elif unf: svgtex(f'{no}-a', simplex(30))
    else: svg(f'{no}-q', p, False); svg(f'{no}-a', p, True)
    ans = othello_web(no) if oth else uno_web(no) if uno else uniform_web(no) if unf else f'<details><summary>Answer</summary><img src="../img/{no}-a.svg" alt="No.{no} の答え"></details>'
    os.makedirs(str(no), exist_ok=True)
    open(f'{no}/index.html', 'w').write(page(f'No.{no} {i["title"]}', f'''
<p class="meta">{i["date"]} ・ {kind(i)}</p>
<p>{uni(ja)}</p><p lang="en">{uni(en)}</p>{'' if unf else f'<img src="../img/{no}-q.svg" alt="No.{no} の問題">'}
{ans}
<p><a href="../">過去の問題一覧へ</a></p>''', '../'))

def page(title, body, root):
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | {CLUB}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#222;background:#fff}}
header{{display:flex;justify-content:space-between;align-items:center;gap:16px}}header img{{height:56px}}
img{{max-width:100%;height:auto}}img[src$=".svg"]{{display:block;width:min(100%,360px);margin:16px auto}}a{{color:#c00}}.meta{{color:#666}}
li{{margin:12px 0}}summary{{display:inline-block;margin:24px 0 12px;padding:12px 24px;border-radius:8px;background:#c00;color:#fff;font-weight:bold;cursor:pointer;list-style:none}}summary::-webkit-details-marker{{display:none}}details[open] summary{{background:#888}}ul{{list-style:none;padding:0}}
#bd{{display:block;width:min(100%,420px);margin:16px auto;user-select:none}}#bd .hit{{cursor:pointer}}#st,.ctl,.ans,.eq{{text-align:center}}.eq{{font-size:1.1em;overflow-wrap:anywhere}}h2{{font-size:1.2em;margin-top:28px}}.ans{{font-size:1.4em}}
.ctl button{{font-size:1.1em;margin:0 3px;padding:6px 12px;border:1px solid #c00;border-radius:6px;background:#fff;color:#c00;cursor:pointer}}
#mv{{display:flex;flex-wrap:wrap;gap:4px 14px;justify-content:center;padding:0;list-style:none;color:#999}}#mv li{{margin:0}}#mv .done{{color:#222}}#mv .cur{{color:#c00;font-weight:bold}}
.uno{{display:flex;flex-wrap:wrap;gap:24px 6px;justify-content:center;min-height:96px;margin:12px 0}}.seq{{padding-left:2em}}.seq li{{margin:4px 0}}#pile{{border-top:1px dashed #aaa;padding-top:12px}}
.uno button{{position:relative;width:48px;height:72px;border:2px solid #000;border-radius:6px;cursor:pointer;padding:0;display:flex;align-items:center;justify-content:center}}.uno button:disabled{{cursor:default;opacity:.35}}#pile button:disabled{{opacity:1}}
.uno button::before{{content:"";position:absolute;width:35px;height:56px;border:1px solid #000;border-radius:50%;background:#fff;transform:rotate(-30deg)}}
.uno button::after{{content:attr(data-n);position:absolute;top:100%;margin-top:3px;font-size:13px;color:#222}}
.uno span{{position:relative;font:bold 26px system-ui,sans-serif;color:#000}}</style></head><body>
<header><img src="{root}logos/labo.png" alt="{CLUB}"><img src="{root}logos/jaist.png" alt="JAIST" style="height:28px"></header>
<h1>{title}</h1>{body}</body></html>'''

for i in issues:
    if not sys.argv[1:] or str(i['no']) in sys.argv[1:]:
        poster(i); print(f'posters/第{i["no"]}回.pdf')
items = ''.join(f'<li><a href="{i["no"]}/">No.{i["no"]} {i["title"]}</a>　<span class="meta">{i["date"]} ・ {kind(i)}</span></li>'
                for i in reversed(issues))
open('index.html', 'w').write(page('過去の問題', f'<p>{CLUB}（JAIST）が掲示板に貼っている問題の一覧です。</p><ul>{items}</ul>', ''))
