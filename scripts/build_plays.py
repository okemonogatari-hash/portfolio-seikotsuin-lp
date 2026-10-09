#!/usr/bin/env python3
"""日々、AIで遊んでます / Made with AI, daily のビルド（2026-10-09 あおい）

plays/plays.json（森の台帳から作られて push される）を読んで、次を作り直す。
  - plays/index.html   一覧ページ（全件・新しい順。JSON-LD CollectionPage＋ItemList）
  - index.html         トップの「日々、AIで遊んでます」節（<!-- plays:start --> 〜 <!-- plays:end --> の間・新しい6件）
sitemap.xml は scripts/build_notes.py が plays.json を読んで /plays/ を足す（この後に回す）。

標準ライブラリだけ。実行時刻は書かない（同じ plays.json なら何度回しても同じ出力）。
使い方:  python3 scripts/build_plays.py && python3 scripts/build_notes.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DATA = SITE / "plays" / "plays.json"
BASE = "https://okemori.com"
HOME_N = 6
e = html.escape


def jp_date(d: str) -> str:
    return d.replace("-", ".")


def card(it: dict, prefix: str, heading: str) -> str:
    """1枚のカード。サムネを押すとその場で再生（JS が無ければ作品のページへ）"""
    playable = bool(it.get("video") or it.get("youtube"))
    attrs = ""
    if it.get("video"):
        attrs = f' data-video="{e(it["video"])}"'
    elif it.get("youtube"):
        attrs = f' data-yt="{e(it["youtube"])}"'
    vertical = it.get("aspect", "").startswith("9:16")
    cls = "play-thumb" + (" is-tall" if vertical else "")
    label = ("再生する：" if playable else "開く：") + it["title"]
    badge = '<span class="play-btn" aria-hidden="true"></span>' if playable else '<span class="play-open" aria-hidden="true">↗</span>'
    return f"""<li class="play-card" id="p-{e(it['id'])}">
<a class="{cls}" href="{e(it['open'])}" target="_blank" rel="noopener"{attrs} aria-label="{e(label)}">
<img src="{prefix}plays/thumbs/{e(it['id'])}.jpg" alt="" width="640" height="360" loading="lazy" decoding="async">{badge}
</a>
<div class="play-text">
<p class="play-meta"><time datetime="{it['date']}">{jp_date(it['date'])}</time><span>{e(it['kind_label'])}</span></p>
<{heading} class="play-title"><a href="{e(it['open'])}" target="_blank" rel="noopener">{e(it['title'])}</a></{heading}>
<p class="play-line">{e(it['line'])}</p>
<p class="play-en" lang="en">{e(it['en'])}</p>
</div>
</li>"""


def build_home_block(items: list[dict], count: int) -> str:
    cards = "\n".join(card(it, "", "h3") for it in items[:HOME_N])
    return f"""<!-- plays:start（scripts/build_plays.py が書く。手で直さない） -->
<ul class="play-grid">
{cards}
</ul>
<div class="work-more">
<a class="text-link" href="plays/">ぜんぶ見る（{count}件） <span class="arrow" aria-hidden="true">↗</span>
</a>
</div>
<!-- plays:end -->"""


def ld_item(it: dict, pos: int) -> dict:
    thumb = f"{BASE}/plays/thumbs/{it['id']}.jpg"
    if it.get("video") or it.get("youtube"):
        obj = {"@type": "VideoObject", "name": it["title"], "description": f"{it['line']} / {it['en']}",
               "thumbnailUrl": thumb, "uploadDate": it["date"], "url": it["open"]}
        if it.get("video"):
            obj["contentUrl"] = it["video"]
        else:
            obj["embedUrl"] = f"https://www.youtube-nocookie.com/embed/{it['youtube']}"
    else:
        obj = {"@type": "CreativeWork", "name": it["title"], "description": f"{it['line']} / {it['en']}",
               "image": thumb, "dateCreated": it["date"], "url": it["open"]}
    return {"@type": "ListItem", "position": pos, "item": obj}


def build_page(data: dict) -> str:
    items = data["items"]
    url = BASE + "/plays/"
    desc = f"おけもんカンパニーが毎日のように AI で作っている物の棚。動く絵、あそべるページ、短い動画を新しい順に{len(items)}件。Made with AI, daily."
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": url,
        "name": "日々、AIで遊んでます / Made with AI, daily",
        "url": url,
        "inLanguage": "ja",
        "dateModified": data.get("updated", ""),
        "publisher": {"@type": "Organization", "name": "Okemon Company", "url": BASE + "/"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(items),
                       "itemListElement": [ld_item(it, i + 1) for i, it in enumerate(items)]},
    }
    og = f"{BASE}/plays/thumbs/{items[0]['id']}.jpg" if items else BASE + "/assets/homepage-v4/social.jpg"
    kinds = []
    for it in items:
        if it["kind_label"] not in kinds:
            kinds.append(it["kind_label"])
    tally = sorted(((sum(1 for i in items if i["kind_label"] == k), k) for k in kinds), key=lambda x: -x[0])
    counts = "、".join(f"{k} {n}" for n, k in tally)
    cards = "\n".join(card(it, "../", "h2") for it in items)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>日々、AIで遊んでます / Made with AI, daily｜おけもん（Okemon Company）</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="stylesheet" href="../assets/homepage-v4/styles.css?v=8">
<link rel="stylesheet" href="../assets/notes/notes.css?v=3">
<link rel="stylesheet" href="../assets/plays/plays.css?v=1">
<script defer src="../assets/plays/plays.js?v=1"></script>
<link rel="icon" href="../assets/okemon-card-icon.png" type="image/png">
<meta property="og:type" content="website">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="おけもん（Okemon Company）">
<meta property="og:title" content="日々、AIで遊んでます / Made with AI, daily">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@okemonogatari">
<meta name="theme-color" content="#fbf9f5">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False)}
</script>
</head>
<body class="notes-page plays-page">
<a class="skip" href="#main">本文へ移動</a>
<header class="site-header">
<div class="wrap header-in">
<a class="brand" href="../">おけもん<small>AIの導入と、強みの読み解き</small></a>
<nav class="nav notes-nav" aria-label="メインナビゲーション">
<a href="./" aria-current="page">日々の遊び</a>
<a href="../notes/">おけもん便り</a>
<a href="../#built">Claudeで作る物</a>
<a href="../#company">事業者情報</a>
</nav>
</div>
</header>
<main id="main">
<section class="plays-list-page wrap">
<p class="eyebrow">MADE WITH AI, DAILY</p>
<h1>日々、AIで遊んでます</h1>
<p class="notes-lead">仕事の合間に、毎日のように AI で何かを作っています。動く絵、あそべるページ、短い動画。サムネを押すと、その場で動きます。<span lang="en">Something new, made with AI, almost every day. Tap a thumbnail to play it here.</span></p>
<p class="plays-count">いま{len(items)}件（{e(counts)}）</p>
<ul class="play-grid play-grid-all">
{cards}
</ul>
</section>
</main>
<footer class="footer">
<div class="wrap footer-in">
<span>© 2026 Okemon Company（ワタシトリセツ）/ おけもん　Kobe, Japan</span>
<span><a href="mailto:hello@okemori.com">hello@okemori.com</a>　 /　 <a href="https://x.com/okemonogatari" target="_blank" rel="noopener">X @okemonogatari</a></span>
</div>
</footer>
</body>
</html>
"""


def main() -> int:
    if not DATA.is_file():
        print("[--] plays/plays.json が無いので何もしない")
        return 0
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = data["items"]
    for it in items:
        if not (SITE / "plays" / "thumbs" / f"{it['id']}.jpg").is_file():
            raise SystemExit(f"[NG] サムネが無い：plays/thumbs/{it['id']}.jpg")
    (SITE / "plays" / "index.html").write_text(build_page(data), encoding="utf-8")
    home = SITE / "index.html"
    h = home.read_text(encoding="utf-8")
    new_h, k = re.subn(r"<!-- plays:start.*?<!-- plays:end -->", build_home_block(items, len(items)), h, flags=re.S)
    if k != 1:
        raise SystemExit("[NG] index.html に <!-- plays:start --> 〜 <!-- plays:end --> が1組見つからない")
    if new_h != h:
        home.write_text(new_h, encoding="utf-8")
    print(f"[済] 棚 {len(items)} 件 / plays/index.html / index.html の遊び節（新しい{HOME_N}件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
