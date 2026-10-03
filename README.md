# labo-quiz

らぼらとらい（JAIST）が掲示板に貼る問題（今は虫食い算）。答えと過去の問題: https://sora3141.github.io/labo-quiz/

## 新しい回を出す

1. 問題を選ぶ（`python3 make.py lv2` などで一覧の PDF を見られる。番号は `problems.json` の `no`）
2. `issues.json` に `{"no": 回, "problem": 問題番号, "date": "YYYY-MM-DD"}` を足す
3. `uv run poster.py <回>` → `posters/第<回>回.pdf`（印刷用）、`<回>/index.html`（QR の先の答え）、`index.html`（一覧）
4. commit して push（Pages に出てから貼る）

問題を足すときは `problems.json` の末尾に足し、`python3 solver.py <番号>` で Lv を測る。
