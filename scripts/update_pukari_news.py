"""
プカリ司法書士法人HP の新着欄を note RSS から自動更新

入力: note RSS (https://note.com/{NOTE_USER}/rss)
出力: pukari-codex-v01/index.html の AUTO_NEWS_TOP / AUTO_NEWS_LIST マーカー間を置換

GitHub Actions cron で1時間おき実行を想定。差分があれば commit & push。
"""

import os
import re
import sys
import html as htmllib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HP_PATH = REPO_ROOT / 'pukari-codex-v01' / 'index.html'

NOTE_USER = os.environ.get('NOTE_USER', 'nice_gnu546')  # おけもんチャンネル
RSS_URL = f'https://note.com/{NOTE_USER}/rss'

TOP_LIMIT = 1   # ヒーロー下のミニ新着（1件）
LIST_LIMIT = 5  # メイン新着リスト（5件）


def fetch_rss(url: str) -> list[dict]:
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'pukari-news-bot/1.0 (+github actions)'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read()
    root = ET.fromstring(text)
    items = []
    for it in root.findall('.//item'):
        title = (it.findtext('title') or '').strip()
        link = (it.findtext('link') or '').strip()
        pub = (it.findtext('pubDate') or '').strip()
        try:
            dt = parsedate_to_datetime(pub)
        except Exception:
            dt = None
        items.append({'title': title, 'link': link, 'pub': pub, 'dt': dt})
    # 投稿日時 desc
    items.sort(key=lambda x: x['dt'] or datetime.min.replace(tzinfo=None), reverse=True)
    return items


def fmt_date(dt) -> str:
    if dt is None:
        return ''
    return dt.strftime('%Y.%m.%d')


def render_top(items: list[dict], limit: int) -> str:
    out = []
    for it in items[:limit]:
        date = fmt_date(it['dt'])
        title = htmllib.escape(it['title'])
        out.append(
            f'      <div class="top-news-item"><strong>{date}</strong>{title}</div>'
        )
    if not out:
        out.append('      <div class="top-news-item">最新記事はまだありません。</div>')
    return '\n'.join(out)


def render_list(items: list[dict], limit: int) -> str:
    out = []
    for i, it in enumerate(items[:limit]):
        date = fmt_date(it['dt'])
        title = htmllib.escape(it['title'])
        link = htmllib.escape(it['link'], quote=True)
        tag = '新着' if i == 0 else '日記'
        out.append(f'              <article class="news-item">')
        out.append(f'                <span class="news-date">{date}</span>')
        out.append(f'                <span class="news-tag">{tag}</span>')
        out.append(f'                <a href="{link}" target="_blank" rel="noopener">{title}</a>')
        out.append(f'              </article>')
    return '\n'.join(out) if out else '              <article class="news-item"><span class="news-date">—</span><a href="#">記事準備中</a></article>'


def replace_block(html: str, start_marker: str, end_marker: str, new_content: str) -> str:
    pattern = re.compile(
        re.escape(start_marker) + r'.*?' + re.escape(end_marker),
        re.DOTALL,
    )
    replacement = f'{start_marker}\n{new_content}\n      {end_marker}'
    return pattern.sub(replacement, html, count=1)


def main() -> int:
    print(f'[fetch] {RSS_URL}')
    items = fetch_rss(RSS_URL)
    print(f'[fetch] {len(items)} items')
    if not items:
        print('[skip] no items')
        return 0

    html = HP_PATH.read_text(encoding='utf-8')
    new_html = html

    # TOP（1件）
    new_html = replace_block(
        new_html,
        '<!-- AUTO_NEWS_TOP_START -->',
        '<!-- AUTO_NEWS_TOP_END -->',
        render_top(items, TOP_LIMIT),
    )

    # LIST（5件）
    list_block = replace_block(
        new_html,
        '<!-- AUTO_NEWS_LIST_START -->',
        '<!-- AUTO_NEWS_LIST_END -->',
        '\n' + render_list(items, LIST_LIMIT) + '\n',
    )
    # render_listの先頭にマーカーが入る形なので独自に再生成
    new_html = re.sub(
        r'<!-- AUTO_NEWS_LIST_START -->.*?<!-- AUTO_NEWS_LIST_END -->',
        '<!-- AUTO_NEWS_LIST_START -->\n' + render_list(items, LIST_LIMIT) + '\n              <!-- AUTO_NEWS_LIST_END -->',
        new_html,
        count=1,
        flags=re.DOTALL,
    )

    if new_html == html:
        print('[skip] no diff')
        return 0

    HP_PATH.write_text(new_html, encoding='utf-8')
    print(f'[update] {HP_PATH}')
    print('[summary] top items:')
    for it in items[:TOP_LIMIT]:
        print(f'  - {fmt_date(it["dt"])}  {it["title"]}')
    print('[summary] list items:')
    for it in items[:LIST_LIMIT]:
        print(f'  - {fmt_date(it["dt"])}  {it["title"]}  {it["link"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
