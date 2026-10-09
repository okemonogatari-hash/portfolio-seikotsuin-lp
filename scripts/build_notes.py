#!/usr/bin/env python3
"""おけもん便り / Notes のビルド（2026-10-09 あおい）

notes/_src/YYYY-MM-DD-slug.md を1枚置いて実行すると、次を作り直す。
  - notes/<slug>/index.html   記事ページ（<time datetime> と JSON-LD BlogPosting 付き）
  - notes/index.html          一覧ページ
  - index.html                トップの「おけもん便り」節（<!-- notes:start --> 〜 <!-- notes:end --> の間・新しい3本）
  - sitemap.xml               固定ページ＋全記事

標準ライブラリだけで動く（GitHub Actions でもローカルでも同じ出力になるよう、実行時刻は書き込まない）。
使い方:  python3 scripts/build_notes.py          # 作り直す
         python3 scripts/build_notes.py --check  # 作らずに検査だけ（文字数・画像の有無）
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SRC = SITE / "notes" / "_src"
IMG = SITE / "notes" / "images"
OUT = SITE / "notes"
BASE = "https://okemori.com"

# サイトマップに載せる固定ページ（noindex のページ・お客さまの提案用ページは載せない）
STATIC_PAGES = [
    ("/", "weekly", "1.0"),
    ("/works.html", "monthly", "0.6"),
    ("/okemon-claude-code-life.html", "monthly", "0.5"),
    ("/okemon-trisetsu.html", "monthly", "0.5"),
]

REQUIRED = ("title", "date", "image", "image_alt", "made")
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]*)\.md$")


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"[NG] {path.name}: 先頭の --- で囲んだ項目（title など）が見つからない")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    meta["body_md"] = m.group(2).strip()
    nm = NAME_RE.match(path.name)
    if not nm:
        raise SystemExit(f"[NG] {path.name}: ファイル名は 2026-10-16-hello.md の形（日付-英小文字とハイフン）にする")
    meta["slug"] = path.stem
    meta.setdefault("date", nm.group(1))
    for k in REQUIRED:
        if not meta.get(k):
            raise SystemExit(f"[NG] {path.name}: 「{k}:」が空")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        raise SystemExit(f"[NG] {path.name}: date は 2026-10-16 の形")
    if not (IMG / meta["image"]).is_file():
        raise SystemExit(f"[NG] {path.name}: 画像 notes/images/{meta['image']} が無い")
    return meta


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    def link(m):
        url = m.group(2)
        ext = url.startswith("http") and not url.startswith(BASE)
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        return f'<a href="{html.escape(url)}"{attrs}>{m.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)


def md_to_html(md: str) -> str:
    out = []
    for block in re.split(r"\n\s*\n", md.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if all(l.startswith(("- ", "・")) for l in lines):
            items = "".join(f"<li>{inline(l[2:] if l.startswith('- ') else l[1:])}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
        elif lines[0].startswith("## "):
            out.append(f"<h2>{inline(lines[0][3:])}</h2>")
            if lines[1:]:
                out.append(f"<p>{'<br>'.join(inline(l) for l in lines[1:])}</p>")
        else:
            out.append(f"<p>{'<br>'.join(inline(l) for l in lines)}</p>")
    return "\n".join(out)


def plain(md: str) -> str:
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    t = re.sub(r"[*#]|^- ", "", t, flags=re.M)
    t = re.sub(r"\s*\n\s*", "", t)
    return re.sub(r"[ \t\u3000]+", " ", t).strip()


def jp_date(d: str) -> str:
    y, m, dd = d.split("-")
    return f"{y}.{m}.{dd}"


def head(title, desc, canonical, prefix, og_image, og_type="article", extra=""):
    e = html.escape
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="{prefix}assets/homepage-v4/styles.css?v=8">
<link rel="stylesheet" href="{prefix}assets/notes/notes.css?v=3">
<link rel="icon" href="{prefix}assets/okemon-card-icon.png" type="image/png">
<link rel="alternate" type="application/atom+xml" title="おけもん便り" href="{BASE}/notes/feed.xml">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="ja_JP">
<meta property="og:site_name" content="おけもん（Okemon Company）">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@okemonogatari">
<meta name="theme-color" content="#fbf9f5">
{extra}</head>
<body class="notes-page">
<a class="skip" href="#main">本文へ移動</a>
<header class="site-header">
<div class="wrap header-in">
<a class="brand" href="{prefix}">おけもん<small>AIの導入と、強みの読み解き</small></a>
<nav class="nav notes-nav" aria-label="メインナビゲーション">
<a href="{prefix}notes/">おけもん便り</a>
<a href="{prefix}#built">Claudeで作る物</a>
<a href="{prefix}#company">事業者情報</a>
</nav>
</div>
</header>
<main id="main">
"""


FOOT = """</main>
<footer class="footer">
<div class="wrap footer-in">
<span>© 2026 Okemon Company（ワタシトリセツ）/ おけもん　Kobe, Japan</span>
<span><a href="mailto:hello@okemori.com">hello@okemori.com</a>　 /　 <a href="https://x.com/okemonogatari" target="_blank" rel="noopener">X @okemonogatari</a></span>
</div>
</footer>
</body>
</html>
"""

PUBLISHER = {
    "@type": "Organization",
    "name": "Okemon Company",
    "url": BASE + "/",
    "logo": {"@type": "ImageObject", "url": BASE + "/assets/okemon-card-icon.png"},
}
AUTHOR = {"@type": "Person", "name": "おけもん（Okemon）", "url": BASE + "/"}


def ld(obj) -> str:
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False) + "\n</script>\n"


def build_article(n: dict, prev: dict | None, nxt: dict | None) -> str:
    e = html.escape
    url = f"{BASE}/notes/{n['slug']}/"
    img_url = f"{BASE}/notes/images/{n['image']}"
    desc = n.get("description") or plain(n["body_md"])[:110] + "…"
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": n["title"],
        "datePublished": n["date"],
        "dateModified": n.get("updated", n["date"]),
        "image": [img_url],
        "description": desc,
        "inLanguage": "ja",
        "author": AUTHOR,
        "publisher": PUBLISHER,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "isPartOf": {"@type": "Blog", "name": "おけもん便り", "@id": BASE + "/notes/"},
    }
    made_link = n.get("made_link", "")
    made = inline(n["made"])
    if made_link:
        ext = made_link.startswith("http") and not made_link.startswith(BASE)
        tgt = ' target="_blank" rel="noopener"' if ext else ""
        made += f' <a class="made-link" href="{e(made_link)}"{tgt}>見る ↗</a>'
    cap = f"<figcaption>{e(n['caption'])}</figcaption>" if n.get("caption") else ""
    pager = []
    if nxt:
        pager.append(f'<a class="pager-newer" href="../{nxt["slug"]}/"><small>新しい便り</small>{e(nxt["title"])}</a>')
    if prev:
        pager.append(f'<a class="pager-older" href="../{prev["slug"]}/"><small>前の便り</small>{e(prev["title"])}</a>')
    return (
        head(f"{n['title']}｜おけもん便り", desc, url, "../../", img_url, extra=ld(data))
        + f"""<article class="note wrap-narrow">
<p class="eyebrow"><a href="../">おけもん便り / Notes</a></p>
<h1>{e(n['title'])}</h1>
<p class="note-meta"><time datetime="{n['date']}">{jp_date(n['date'])}</time><span>文・{e(n.get('author', 'おけもんカンパニー'))}</span></p>
<figure class="note-figure"><img src="../images/{e(n['image'])}" alt="{e(n['image_alt'])}" width="1200" height="675" loading="eager">{cap}</figure>
<div class="note-body">
{md_to_html(n['body_md'])}
</div>
<aside class="note-made" aria-label="今週 Claude で作った物">
<p class="note-made-label">今週 Claude で作った物</p>
<p>{made}</p>
</aside>
<nav class="note-pager" aria-label="ほかの便り">{''.join(pager)}<a class="pager-all" href="../">便りの一覧へ</a></nav>
</article>
"""
        + FOOT
    )


def build_index(notes: list[dict]) -> str:
    e = html.escape
    url = BASE + "/notes/"
    data = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "@id": url,
        "name": "おけもん便り",
        "url": url,
        "inLanguage": "ja",
        "publisher": PUBLISHER,
        "blogPost": [
            {"@type": "BlogPosting", "headline": n["title"], "datePublished": n["date"], "url": f"{BASE}/notes/{n['slug']}/"}
            for n in notes
        ],
    }
    items = "\n".join(
        f"""<li><a class="notes-item" href="{n['slug']}/">
<img src="images/{e(n['image'])}" alt="" width="1200" height="675" loading="lazy">
<span class="notes-item-text"><time datetime="{n['date']}">{jp_date(n['date'])}</time>
<strong>{e(n['title'])}</strong>
<small>今週 Claude で作った物：{e(plain(n['made']))}</small></span>
</a></li>"""
        for n in notes
    )
    desc = "おけもんカンパニーの週1の便り。毎週、その週に Claude で作った物を1つ、400字と写真1枚で。"
    og = f"{BASE}/notes/images/{notes[0]['image']}" if notes else BASE + "/assets/homepage-v4/social.jpg"
    return (
        head("おけもん便り / Notes｜おけもん（Okemon Company）", desc, url, "../", og, og_type="website", extra=ld(data))
        + f"""<section class="notes-list-page wrap-narrow">
<p class="eyebrow">OKEMON NOTES</p>
<h1>おけもん便り</h1>
<p class="notes-lead">毎週ひとつ、その週に Claude で作った物を、400字と写真1枚で残しています。<span lang="en">A weekly note on one thing we built with Claude.</span></p>
<ul class="notes-list">
{items}
</ul>
</section>
"""
        + FOOT
    )


def build_home_block(notes: list[dict]) -> str:
    e = html.escape
    items = "\n".join(
        f"""<li><a class="notes-item" href="notes/{n['slug']}/">
<img src="notes/images/{e(n['image'])}" alt="" width="1200" height="675" loading="lazy">
<span class="notes-item-text"><time datetime="{n['date']}">{jp_date(n['date'])}</time>
<strong>{e(n['title'])}</strong>
<small>今週 Claude で作った物：{e(plain(n['made']))}</small></span>
</a></li>"""
        for n in notes[:3]
    )
    return f"""<!-- notes:start（scripts/build_notes.py が書く。手で直さない） -->
<ul class="notes-list notes-list-home">
{items}
</ul>
<!-- notes:end -->"""


def build_feed(notes: list[dict]) -> str:
    e = html.escape
    updated = notes[0]["date"] if notes else "2026-10-09"
    entries = "\n".join(
        f"""<entry><title>{e(n['title'])}</title><link href="{BASE}/notes/{n['slug']}/"/><id>{BASE}/notes/{n['slug']}/</id><updated>{n.get('updated', n['date'])}T09:00:00+09:00</updated><summary>{e(plain(n['body_md'])[:140])}</summary></entry>"""
        for n in notes
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>おけもん便り</title>
<link href="{BASE}/notes/"/>
<link rel="self" href="{BASE}/notes/feed.xml"/>
<id>{BASE}/notes/</id>
<updated>{updated}T09:00:00+09:00</updated>
<author><name>Okemon Company</name></author>
{entries}
</feed>
"""


def build_sitemap(notes: list[dict]) -> str:
    latest = notes[0]["date"] if notes else None
    rows = []
    for path, freq, pri in STATIC_PAGES:
        lm = f"<lastmod>{latest}</lastmod>" if (path == "/" and latest) else ""
        rows.append(f"<url><loc>{BASE}{path}</loc>{lm}<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")
    if notes:
        rows.append(f"<url><loc>{BASE}/notes/</loc><lastmod>{latest}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    for n in notes:
        rows.append(f"<url><loc>{BASE}/notes/{n['slug']}/</loc><lastmod>{n.get('updated', n['date'])}</lastmod><priority>0.6</priority></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"


def main() -> int:
    check_only = "--check" in sys.argv
    srcs = sorted(p for p in SRC.glob("*.md") if not p.name.startswith("_"))
    notes = [parse(p) for p in srcs]
    notes.sort(key=lambda n: (n["date"], n["slug"]), reverse=True)
    for n in notes:
        c = len(re.sub(r"\s", "", plain(n["body_md"])))
        flag = "OK" if 300 <= c <= 520 else "WARN（目安は400字前後）"
        print(f"[{flag}] {n['slug']}: 本文 {c} 字 / 画像 {n['image']}")
    if check_only:
        return 0
    live = {n["slug"] for n in notes}
    for d in OUT.iterdir():
        if d.is_dir() and d.name not in ("_src", "images") and d.name not in live and (d / "index.html").is_file():
            (d / "index.html").unlink()
            d.rmdir()
            print(f"[消] notes/{d.name}/（元の .md が無いので記事ページを外した）")
    for i, n in enumerate(notes):
        nxt = notes[i - 1] if i > 0 else None
        prev = notes[i + 1] if i + 1 < len(notes) else None
        d = OUT / n["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(build_article(n, prev, nxt), encoding="utf-8")
    (OUT / "index.html").write_text(build_index(notes), encoding="utf-8")
    (OUT / "feed.xml").write_text(build_feed(notes), encoding="utf-8")
    home = SITE / "index.html"
    h = home.read_text(encoding="utf-8")
    new_h, k = re.subn(r"<!-- notes:start.*?<!-- notes:end -->", build_home_block(notes), h, flags=re.S)
    if k != 1:
        raise SystemExit("[NG] index.html に <!-- notes:start --> 〜 <!-- notes:end --> が1組見つからない")
    if new_h != h:
        home.write_text(new_h, encoding="utf-8")
    (SITE / "sitemap.xml").write_text(build_sitemap(notes), encoding="utf-8")
    print(f"[済] 記事 {len(notes)} 本 / notes/index.html / notes/feed.xml / index.html の便り節 / sitemap.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
