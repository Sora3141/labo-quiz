# /// script
# dependencies = ["segno", "pillow"]
# ///
# 掲示用の PDF と Web ページを作る
# 使い方: issues.json に {"no": 回, "title": "虫食い算", "problem": 問題番号, "date": "YYYY-MM-DD"} を足してから
#         uv run poster.py 3    → posters/第3回.pdf と 3/index.html、一覧の index.html
#         uv run poster.py      → 全部の回を作り直す
import json, os, subprocess, sys, html, segno
from make import P, pic, width, layout, OPN, H

URL = 'https://sora3141.github.io/labo-quiz/'
CLUB = 'らぼらとらい'
issues = json.load(open('issues.json'))
os.makedirs('build', exist_ok=True); os.makedirs('posters', exist_ok=True); os.makedirs('img', exist_ok=True)

def tex(name, body):
    open(f'build/{name}.tex', 'w').write(body)
    subprocess.run(['lualatex', '-interaction=nonstopmode', '-output-directory=build', f'build/{name}.tex'], check=True, capture_output=True)
    return f'build/{name}.pdf'

def rule(p):
    n, m = p['n'], p['m']
    digits = f'1〜{n-1} を、数字 $d$ はちょうど $d$ 個ずつ使う（0 は使わない）' if m == 'tri' else f'0〜{n-1} を各 {m} 個ずつ使う'
    base = '' if n == 10 else f'{n} 進数の筆算。'
    extra = ''
    if p['op'][0] == '/': extra = '最後の行はあまり。枠のない 0 は数えない。'
    if p['op'] == '*' and '@' in p['shape']: extra = 'かける数に 0 の桁があるとき、その部分積の行は書かない。'
    return f'{base}□ には数字が 1 つずつ入る。{digits}。いちばん左の桁は 0 ではない。{extra}答えは 1 つ。'

def svg(name, p, ans):  # 問題・答えの図を SVG に
    # standalone.cls が無いので、図の箱の大きさにページを合わせて直接出す
    pdf = tex(name, r'''\documentclass{article}\usepackage{tikz}\begin{document}
\setbox0\hbox{\kern4pt\vbox{\kern4pt\hbox{%s}\kern4pt}\kern4pt}
\pagewidth=\wd0 \pageheight=\dimexpr\ht0+\dp0\relax \hoffset=-1in \voffset=-1in \shipout\box0
\end{document}''' % pic(p, ans, 0.6))
    subprocess.run(['pdftocairo', '-svg', pdf, f'img/{name}.svg'], check=True)

def crop(name):  # ロゴの描画部分だけを切り抜く（logos/ の元画像はそのまま）
    from PIL import Image
    im = Image.open(f'logos/{name}.png').convert('RGBA')
    flat = Image.alpha_composite(Image.new('RGBA', im.size, 'white'), im).convert('RGB')
    flat.crop(flat.convert('L').point(lambda v: 255 if v < 245 else 0).getbbox()).save(f'build/{name}.png')
    return f'build/{name}.png'

def poster(i):
    p = P[i['problem']]; no = i['no']; url = f'{URL}{no}/'
    qr = segno.make(url, error='m'); qr.save(f'build/qr-{no}.pdf', scale=10, border=4)  # まわりの白 4 マスは規格で要る
    qz = 40 * 4 / qr.symbol_size(border=4)[0]  # 白 4 マスの幅（mm）。黒い部分の端を余白線にそろえるのに使う
    rows = max(r for _, r, _ in layout(p)[0]) + 1
    s = min(16 / width(p), 14 / (rows * H))  # 図全体（× も）を幅 16cm・高さ 14cm に収まるまで拡大
    body = r'''\documentclass[a4paper]{ltjsarticle}
\usepackage[margin=15mm]{geometry}\usepackage{tikz,graphicx}\pagestyle{empty}
\begin{document}\sffamily\setlength{\parindent}{0pt}
%% 上: 回の番号と答えの QR（N の左の隙間 1.15mm を詰める）。文字の上端と QR の黒い部分の上端・右端を余白線にそろえる
\vspace*{-\topskip}\leavevmode\kern-1.15mm\raisebox{-\height}{\bfseries{\fontsize{48}{56}\selectfont No.%d}\quad{\fontsize{30}{36}\selectfont %s}}\hfill
\raisebox{\dimexpr-\height+%.2fmm}{\begin{minipage}[t]{40mm}\centering
\includegraphics[width=40mm]{build/qr-%d.pdf}\par\vspace{-%.2fmm}\vspace{1.5mm}{\large\bfseries 答えはこちら}\end{minipage}}\hspace{-%.2fmm}

\vfill
%% 中: ルール文と問題
{\large %s}\par\vspace{8mm}
\begin{center}\scalebox{%.2f}{%s}\end{center}

\vfill
%% 下: 出した側の帯。2 つのロゴは見た目の重さが合う高さ、縦の中心をそろえる
\rule{\linewidth}{0.4pt}\par\vspace{6mm}
\leavevmode\raisebox{-.5\height}{\includegraphics[height=36mm]{%s}}\hfill
\raisebox{-.5\height}{\begin{tabular}[b]{@{}c@{}}\small 過去の問題と答え\\[1mm]\footnotesize %s\end{tabular}}\hfill
\raisebox{-.5\height}{\includegraphics[height=13mm]{%s}}\par\kern0pt  %% 下に出る深さも本文の高さに入れて、下の余白にはみ出さない
\end{document}''' % (no, i['title'], qz, no, qz, qz, rule(p), s, pic(p, False, 1), crop('labo'), URL, crop('jaist'))
    os.replace(tex(f'poster-{no}', body), f'posters/第{no}回.pdf')
    svg(f'{no}-q', p, False); svg(f'{no}-a', p, True)
    os.makedirs(str(no), exist_ok=True)
    open(f'{no}/index.html', 'w').write(page(f'No.{no} {i["title"]}', f'''
<p class="meta">{i["date"]} ・ {OPN[p["op"]]}</p>
<p>{html.escape(rule(p).replace("$", ""))}</p><img src="../img/{no}-q.svg" alt="No.{no} の問題">
<details><summary>答えを見る</summary><img src="../img/{no}-a.svg" alt="No.{no} の答え"></details>
<p><a href="../">過去の問題一覧へ</a></p>''', '../'))

def page(title, body, root):
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | {CLUB}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;color:#222;background:#fff}}
header{{display:flex;justify-content:space-between;align-items:center;gap:16px}}header img{{height:56px}}
img{{max-width:100%;height:auto}}img[src$=".svg"]{{display:block;width:min(100%,360px);margin:16px auto}}a{{color:#c00}}.meta{{color:#666}}
li{{margin:12px 0}}summary{{display:inline-block;margin:24px 0 12px;padding:12px 24px;border-radius:8px;background:#c00;color:#fff;font-weight:bold;cursor:pointer;list-style:none}}summary::-webkit-details-marker{{display:none}}details[open] summary{{background:#888}}ul{{list-style:none;padding:0}}</style></head><body>
<header><img src="{root}logos/labo.png" alt="{CLUB}"><img src="{root}logos/jaist.png" alt="JAIST" style="height:28px"></header>
<h1>{title}</h1>{body}</body></html>'''

for i in issues:
    if not sys.argv[1:] or str(i['no']) in sys.argv[1:]:
        poster(i); print(f'posters/第{i["no"]}回.pdf')
items = ''.join(f'<li><a href="{i["no"]}/">No.{i["no"]} {i["title"]}</a>　<span class="meta">{i["date"]} ・ {OPN[P[i["problem"]]["op"]]}</span></li>'
                for i in reversed(issues))
open('index.html', 'w').write(page('過去の問題', f'<p>{CLUB}（JAIST）が掲示板に貼っている問題の一覧です。</p><ul>{items}</ul>', ''))
