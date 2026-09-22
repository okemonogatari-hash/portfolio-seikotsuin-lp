# v10 QA — 2026-09-22

対象: homepage-world.html / homepage-world-study.html。公開版ではなく比較用の修正案。

- IAB direct 1280x720、比較iframe 1248px、スマホ幅390pxで画面確認。画像欠損0、横はみ出しなし（1248/scrollWidth1233、390/scrollWidth375）。実機端末・320pxは今回未確認。
- 8つの主要素材 + 7粒が別要素。全15要素の別時点transform変化を確認、主要素材周期8.6〜22秒。
- ポインター入力後 --mx=9.14px、--my=-3.51px。奥行き別にparallax transformの移動量が異なることを実測。
- 停止操作後、float + parallax計30transformが時間を離して一致。再開後15要素running。
- できることリンクでgatesへ移動後、motion-offscreenと15要素pausedを観測。
- v9/v10切替、スマホ幅/画面幅の復帰、直接リンクの切替を確認。
- reduced-motionはCSS/JSの静的確認のみ。OS設定変更による実測はしていない。
- 単独ページのconsole error/warnは0。比較画面にはMutationObserver.observeのNode型エラーが1件記録されたが、当該APIは比較HTML/サイトJSに存在せず、操作は正常。注入側由来の可能性はあるが出所未特定。比較切替・幅切替・停止再開はこの記録の後に再確認済み。

視覚修正: 大きなガラスが顔・白い服へ透けて見えたため、後景の中央をマスクし、人物の周囲に余白を確保。PC/スマホで再確認。画像原本の人物の顔は変更していない。

技術確認は本人の美的な満足や参考との差の解消を証明しない。採用は未確認。公開mainのv8は変更していない。
