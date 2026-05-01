#!/usr/bin/env python3
"""
irodori Zoom運行管理ダッシュボード 自動生成スクリプト
- Zoom APIから菜緒さん（Z①）/ 小山さん（Z②）の会議一覧を取得
- 過去5日 + 今日 + 未来7日の範囲で日付別カード生成
- 被り検知（時間帯重複） / 短い隙間（15分未満）検出
- HTMLファイルを完全再生成 → ../irodori-zoom-dashboard.html

環境変数: ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET
"""
import os
import sys
import base64
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
HOST_NAEO = "5jeFf8S-TWC2zwtYGtLxLg"
HOST_KOYAMA = "aAUji7r9QqWo-9JSS5yEFA"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "irodori-zoom-dashboard.html"

WEEKDAY_JP = "月火水木金土日"


# ────────── Zoom API ──────────

def get_access_token():
    account_id = os.environ["ZOOM_ACCOUNT_ID"]
    client_id = os.environ["ZOOM_CLIENT_ID"]
    client_secret = os.environ["ZOOM_CLIENT_SECRET"]
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
    req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]


def fetch_meetings(token, user_id, meeting_type):
    """meeting_type: 'scheduled' / 'previous_meetings' など"""
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings?type={meeting_type}&page_size=300"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get("meetings", [])


def parse_jst(start_time):
    s = start_time.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(JST)


def normalize(meetings, host_label):
    """{date: [meeting_dict, ...]} の形に整形（id+start_timeで重複排除）"""
    by_date = {}
    seen = set()
    for m in meetings:
        if not m.get("start_time"):
            continue
        # scheduled / previous_meetings の両方に同じ会議が含まれることがあるので重複排除
        key = (m.get("id"), m["start_time"])
        if key in seen:
            continue
        seen.add(key)
        st = parse_jst(m["start_time"])
        end = st + timedelta(minutes=m.get("duration", 0))
        d = st.date()
        by_date.setdefault(d, []).append({
            "id": m.get("id"),
            "topic": m.get("topic", "(無題)"),
            "start": st,
            "end": end,
            "duration": m.get("duration", 0),
            "type": m.get("type", 2),  # 2=scheduled / 8=recurring fixed
            "host": host_label,
        })
    for d in by_date:
        by_date[d].sort(key=lambda x: x["start"])
    return by_date


def merge_dates(z1_by_date, z2_by_date, target_dates):
    """指定日付ごとに { 'z1': [...], 'z2': [...] } を返す"""
    out = []
    for d in target_dates:
        out.append({
            "date": d,
            "z1": z1_by_date.get(d, []),
            "z2": z2_by_date.get(d, []),
        })
    return out


# ────────── 検知ロジック ──────────

def detect_overlap_intra(meetings):
    """同じZoom内の時間帯重複（完全被り）"""
    pairs = []
    for i in range(len(meetings)):
        for j in range(i + 1, len(meetings)):
            a, b = meetings[i], meetings[j]
            if a["start"] < b["end"] and b["start"] < a["end"]:
                pairs.append((a, b))
    return pairs


def detect_short_gap(meetings, threshold_min=15):
    """連続予定の準備時間がthreshold分以内"""
    issues = []
    for i in range(len(meetings) - 1):
        gap = (meetings[i + 1]["start"] - meetings[i]["end"]).total_seconds() / 60
        if 0 <= gap < threshold_min:
            issues.append((meetings[i], meetings[i + 1], int(gap)))
    return issues


def day_status(z1, z2):
    """その日のZ①Z②それぞれのステータス: ('green'/'yellow'/'red', メモ)"""
    def one_zoom(meetings, label):
        overlaps = detect_overlap_intra(meetings)
        gaps = detect_short_gap(meetings)
        if overlaps:
            notes = []
            if overlaps:
                t = overlaps[0][0]["start"].strftime("%H:%M")
                notes.append(f"{t} 完全被り")
            if gaps:
                p, n, g = gaps[0]
                notes.append(f"{p['end'].strftime('%H:%M')}→{n['start'].strftime('%H:%M')} 準備{g}分")
            return "red", " ／ ".join(notes)
        if gaps:
            p, n, g = gaps[0]
            return "yellow", f"{p['end'].strftime('%H:%M')}→{n['start'].strftime('%H:%M')} 準備{g}分"
        return "green", "通常運行"
    s1, n1 = one_zoom(z1, "Z①")
    s2, n2 = one_zoom(z2, "Z②")
    return (s1, n1), (s2, n2)


# ────────── セルフチェック ──────────

def validate(z1_dict, z2_dict, today, raw_counts):
    """生成データの整合性をチェック。
    致命的（FATAL）→ SystemExitで中止 / 警告（WARN）→ stderrに出して続行"""
    fatal = []
    warn = []

    # ① id + start_time の重複（今回の犯人）
    for label, dict_data in [("Z①", z1_dict), ("Z②", z2_dict)]:
        for d, meetings in dict_data.items():
            keys = [(m["id"], m["start"]) for m in meetings]
            if len(keys) != len(set(keys)):
                fatal.append(f"❌ [重複] {label} {d}: id+start_time が重複")

    # ② 同一topic + 同一開始時刻 の実質重複（id違いで内容同じ）
    for label, dict_data in [("Z①", z1_dict), ("Z②", z2_dict)]:
        for d, meetings in dict_data.items():
            sigs = [(m["topic"], m["start"]) for m in meetings]
            seen_sigs = set()
            dup_sigs = []
            for s in sigs:
                if s in seen_sigs:
                    dup_sigs.append(s)
                seen_sigs.add(s)
            if dup_sigs:
                warn.append(f"⚠️ [実質重複] {label} {d}: 同一topic+同時刻 {dup_sigs[0]}")

    # ③ 取得件数が0件（API失敗の可能性）
    total_z1 = raw_counts["z1_scheduled"] + raw_counts["z1_past"]
    total_z2 = raw_counts["z2_scheduled"] + raw_counts["z2_past"]
    if total_z1 == 0:
        warn.append("⚠️ [件数異常] Z①取得件数0（API失敗の可能性）")
    if total_z2 == 0:
        warn.append("⚠️ [件数異常] Z②取得件数0（API失敗の可能性）")

    # ④ JSTと現実のズレ
    now = datetime.now(JST)
    if now.date() != today:
        fatal.append(f"❌ [JSTズレ] today={today} != 現在JST={now.date()}")

    # ⑤ 同一日に同一(host, topic, start) が2件以上
    for label, dict_data in [("Z①", z1_dict), ("Z②", z2_dict)]:
        for d, meetings in dict_data.items():
            sig = [(m["host"], m["topic"], m["start"]) for m in meetings]
            if len(sig) != len(set(sig)):
                fatal.append(f"❌ [表示重複] {label} {d}: (host,topic,start)が重複")

    print("\n🔍 セルフチェック結果")
    if not fatal and not warn:
        print("  ✅ 異常なし（5項目すべて通過）")
    else:
        for w in warn:
            print(f"  {w}")
        for f in fatal:
            print(f"  {f}")

    if fatal:
        print("\n🚨 致命的な問題を検知。HTML生成を中止しました（古いHTMLが残ります）")
        sys.exit(1)


# ────────── HTML 生成 ──────────

def html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_slot(m, css_class):
    recurring = ' <span class="recurring">🔁定期</span>' if m["type"] in (8, 3) else ""
    topic = html_escape(m["topic"])
    return (
        f'<span class="slot {css_class}">'
        f'{m["start"].strftime("%H:%M")}-{m["end"].strftime("%H:%M")} {topic}'
        f'<span class="duration">({m["duration"]}分)</span>{recurring}</span>'
    )


def render_day_card(day_data, today):
    d = day_data["date"]
    z1 = day_data["z1"]
    z2 = day_data["z2"]

    # 被り・隙間判定
    overlaps_z1 = detect_overlap_intra(z1)
    overlaps_z2 = detect_overlap_intra(z2)
    gaps_z1 = detect_short_gap(z1)
    gaps_z2 = detect_short_gap(z2)
    overlap_ids_z1 = {id(m) for pair in overlaps_z1 for m in pair}
    overlap_ids_z2 = {id(m) for pair in overlaps_z2 for m in pair}
    gap_ids_z1 = set()
    for prev, nxt, _ in gaps_z1:
        gap_ids_z1.add(id(prev)); gap_ids_z1.add(id(nxt))
    gap_ids_z2 = set()
    for prev, nxt, _ in gaps_z2:
        gap_ids_z2.add(id(prev)); gap_ids_z2.add(id(nxt))

    # クラス: past / today
    past_class = " past" if d < today else ""
    badge = ""
    if d == today:
        badge = '<span class="today-badge">今日</span>'
    elif d < today:
        badge = '<span class="past-badge">過去</span>'

    # アラート
    alerts = []
    for pair in overlaps_z1 + overlaps_z2:
        zlabel = "Zoom①" if pair[0]["host"] == "Z①" else "Zoom②"
        alerts.append(
            f'<div class="alert">🚨 被り検知: {zlabel} '
            f'{pair[0]["start"].strftime("%H:%M")}-{pair[0]["end"].strftime("%H:%M")} ⇄ '
            f'{pair[1]["start"].strftime("%H:%M")}-{pair[1]["end"].strftime("%H:%M")}</div>'
        )
    for prev, nxt, gap in gaps_z1 + gaps_z2:
        zlabel = "Zoom①" if prev["host"] == "Z①" else "Zoom②"
        alerts.append(
            f'<div class="alert-warn">⚠️ 準備時間が短めです: {zlabel} '
            f'{prev["end"].strftime("%H:%M")}終了 → {nxt["start"].strftime("%H:%M")}開始'
            f'（{gap}分しか空いていません）</div>'
        )

    # 時間軸：会議のあった時間帯 + 7-18時 を統合
    hours = set(range(7, 19))
    for m in z1 + z2:
        hours.add(m["start"].hour)
    hours = sorted(hours)

    rows = []
    for h in hours:
        # その時間に開始する会議
        z1_cells = [m for m in z1 if m["start"].hour == h]
        z2_cells = [m for m in z2 if m["start"].hour == h]

        def cell(cells, ids_overlap, ids_gap, default_class):
            if not cells:
                return '<span class="slot free">—</span>'
            parts = []
            for m in cells:
                if id(m) in ids_overlap:
                    cls = "warn"
                elif id(m) in ids_gap:
                    cls = "warn-soft"
                else:
                    cls = default_class
                parts.append(render_slot(m, cls))
            return "".join(parts)

        z1_html = cell(z1_cells, overlap_ids_z1, gap_ids_z1, "ok-z1")
        z2_html = cell(z2_cells, overlap_ids_z2, gap_ids_z2, "ok-z2")
        rows.append(
            f'<tr><td class="time">{h:02d}:00</td>'
            f'<td>{z1_html}</td><td>{z2_html}</td></tr>'
        )

    legend = (
        '<div class="legend">'
        '<div class="legend-item"><span class="legend-dot" style="background:#e8f0fe;border:1px solid #4a8cf7"></span>Zoom①予定</div>'
        '<div class="legend-item"><span class="legend-dot" style="background:#e8f4ec;border:1px solid #3a8a5f"></span>Zoom②予定</div>'
        '<div class="legend-item"><span class="legend-dot" style="background:#fff8e1;border:1px solid #d4a017"></span>準備時間短め（15分以内）</div>'
        '<div class="legend-item"><span class="legend-dot" style="background:#fdecec;border:1px solid #d64545"></span>被り検知</div>'
        '</div>'
    )

    return (
        f'<div class="day-card{past_class}">'
        f'<div class="day-head"><div class="date">{d.strftime("%Y-%m-%d")} ({WEEKDAY_JP[d.weekday()]})</div>{badge}</div>'
        + "".join(alerts)
        + '<table class="sheet"><thead><tr><th class="time">時間</th><th>Zoom①（菜緒さん側）</th><th>Zoom②（小山さん側）</th></tr></thead>'
        + f'<tbody>{"".join(rows)}</tbody></table>'
        + legend
        + '</div>'
    )


def render_summary(today, day_list):
    """今日の運行状況サマリ + 週間表"""
    today_data = next((d for d in day_list if d["date"] == today), None)
    if today_data is None:
        today_html = (
            f'<div class="tp-title">📍 今日の運行状況（{today.strftime("%-m/%-d")} {WEEKDAY_JP[today.weekday()]}）</div>'
            f'<div class="zoom-line"><span class="signal green">●</span><span class="label">Zoom①</span><span class="status-text"><span class="ok">予定なし</span></span></div>'
            f'<div class="zoom-line"><span class="signal green">●</span><span class="label">Zoom②</span><span class="status-text"><span class="ok">予定なし</span></span></div>'
        )
    else:
        (s1, n1), (s2, n2) = day_status(today_data["z1"], today_data["z2"])
        signal_map = {"green": "green", "yellow": "yellow", "red": "red"}
        text_class_map = {"green": "ok", "yellow": "warn", "red": "ng"}
        today_html = (
            f'<div class="tp-title">📍 今日の運行状況（{today.strftime("%-m/%-d")} {WEEKDAY_JP[today.weekday()]}）</div>'
            f'<div class="zoom-line"><span class="signal {signal_map[s1]}">●</span><span class="label">Zoom①</span><span class="status-text"><span class="{text_class_map[s1]}">{n1}</span></span></div>'
            f'<div class="zoom-line"><span class="signal {signal_map[s2]}">●</span><span class="label">Zoom②</span><span class="status-text"><span class="{text_class_map[s2]}">{n2}</span></span></div>'
        )

    rows = []
    for dd in day_list:
        d = dd["date"]
        (s1, n1), (s2, n2) = day_status(dd["z1"], dd["z2"])
        text_class_map = {"green": "ok", "yellow": "warn", "red": "ng"}
        signal_map = {"green": "green", "yellow": "yellow", "red": "red"}
        if d == today:
            mark = '<span class="today-mark">今日</span>'
        elif d < today:
            mark = '<span class="past-mark">過去</span>'
        else:
            mark = ""
        rows.append(
            f'<tr><td class="day-cell">{d.strftime("%-m/%d")} ({WEEKDAY_JP[d.weekday()]}){mark}</td>'
            f'<td><span class="signal {signal_map[s1]}">●</span><span class="{text_class_map[s1]}">{n1}</span></td>'
            f'<td><span class="signal {signal_map[s2]}">●</span><span class="{text_class_map[s2]}">{n2}</span></td></tr>'
        )

    return (
        '<section class="status-board">'
        '<div class="sb-head"><span class="sb-icon">🚦</span>運行状況サマリ</div>'
        f'<div class="today-panel">{today_html}</div>'
        '<table class="week-table">'
        '<thead><tr><th>日付</th><th>Zoom①（菜緒さん側）</th><th>Zoom②（小山さん側）</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></section>'
    )


def render_html(today, day_list, generated_at):
    # 既存HTMLからCSSを抽出して流用するか、ハードコードするか。
    # ここでは安全に既存HTMLからCSSを読み出す（無ければハードコード）。
    css = _load_css()

    summary_html = render_summary(today, day_list)
    cards_html = "".join(render_day_card(dd, today) for dd in day_list)

    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>irodori Zoom運行管理ボード v0.3 (本物データ版)</title>
<style>{css}</style></head><body>
<div class="container">

<header>
<h1>irodori Zoom運行管理ボード</h1>
<p class="lead">Zoom①／Zoom② の予約状況がここに自動で並びます（v0.3 ためし版）</p>
</header>

<section class="big-callout">
<div class="callout-mark">📋</div>
<div class="callout-body">
<div class="callout-tag">v0.3</div>
<h2 class="callout-title">
このダッシュボードで<span class="hl">わかること</span>
</h2>
<p class="callout-sub">
・<strong>Zoom①／Zoom②の予定</strong>が日付ごとに一覧で並びます<br>
・どちらの予定も<strong>まとめて1画面</strong>で見えるので、朝の確認が1回で済みます<br>
・同じ時間に予定が重なっている「被り」を<strong>赤色</strong>で自動でお知らせします<br>
・予定の間が15分以内など「ギリギリ」も<strong>黄色</strong>でやさしく注意します<br>
・<strong>朝礼や参加者情報</strong>も自動で表示します
</p>
<div class="callout-points">
<span class="callout-chip">📅 Zoom①／②の予定一覧</span>
<span class="callout-chip">👯 1画面でまとめて確認</span>
<span class="callout-chip">⚠️ ギリギリは黄色で注意</span>
<span class="callout-chip">🚨 被りは赤色でお知らせ</span>
</div>
</div>
</section>

{summary_html}

<h2 class="section-title">📅 今日〜来週ぶんの予約状況</h2>
<p class="meta">当日が一番上、これから先の予定が並びます。被りがあった場合は赤背景で表示します。</p>
{cards_html}
<div class="note-box">
<strong>📡 このダッシュボードで確認できたこと</strong><br>
1. Zoomの予定がここに自動で並ぶようになりました<br>
2. <strong>Zoom①の鍵ひとつで Zoom②（小山さん側）の予定も見えます</strong> — 鍵を2つ作る必要はありませんでした<br>
3. 同じZoom枠で時間が重なる「被り」を自動で見つけて赤色でお知らせできます<br>
4. 過去ぶんも含めて表示できます（ただし修正後に削除された予定は出てきません）<br>
<br>
<strong>📌 次にやること</strong><br>
・このダッシュボードを毎日自動で更新する仕組みづくり（GitHub Actions cron 検討中💭）<br>
・「今日のZoom予約一覧」を自動で投稿してくれる専用ルーム（PMチャットへ自動通知運用テスト中）
</div>

<div class="footer">
📡 Zoomから直接予定を取ってきて表示しています<br>
取得時刻: {generated_at.strftime("%Y-%m-%d %H:%M:%S")} JST<br>
irodori スケジュール管理・Zoom被り検知 v0.3 本物データ版 ／ おけもんカンパニー 制作
</div>

</div></body></html>
"""


def _load_css():
    """既存HTMLから<style>...</style>の中身だけ抜き出す"""
    if not OUT_PATH.exists():
        return ""
    text = OUT_PATH.read_text(encoding="utf-8")
    start = text.find("<style>")
    end = text.find("</style>")
    if start < 0 or end < 0:
        return ""
    return text[start + len("<style>"):end]


# ────────── main ──────────

def main():
    now = datetime.now(JST)
    today = now.date()

    # 範囲：今日 + 未来9日 = 計10日（過去は表示しない・今日が常に一番上）
    target_dates = [today + timedelta(days=i) for i in range(0, 10)]

    print(f"⏱ 実行時刻 (JST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 対象範囲: {target_dates[0]} 〜 {target_dates[-1]}")

    print("🔑 Zoomトークン取得中...")
    token = get_access_token()

    # upcoming_meetings は定期会議の各occurrenceまで展開してくれる正しいタイプ
    # scheduled だと type=8 の親レコードしか取れず、各回が抜け落ちる
    print("📥 Zoom会議取得中（菜緒さん）...")
    naeo_scheduled = fetch_meetings(token, HOST_NAEO, "upcoming_meetings")
    naeo_past = fetch_meetings(token, HOST_NAEO, "previous_meetings")

    print("📥 Zoom会議取得中（小山さん）...")
    koyama_scheduled = fetch_meetings(token, HOST_KOYAMA, "upcoming_meetings")
    koyama_past = fetch_meetings(token, HOST_KOYAMA, "previous_meetings")

    z1 = normalize(naeo_scheduled + naeo_past, "Z①")
    z2 = normalize(koyama_scheduled + koyama_past, "Z②")

    raw_counts = {
        "z1_scheduled": len(naeo_scheduled),
        "z1_past": len(naeo_past),
        "z2_scheduled": len(koyama_scheduled),
        "z2_past": len(koyama_past),
    }
    print(f"📊 過去会議: 菜緒 {raw_counts['z1_past']}件 / 小山 {raw_counts['z2_past']}件")
    print(f"📊 今後会議: 菜緒 {raw_counts['z1_scheduled']}件 / 小山 {raw_counts['z2_scheduled']}件")

    # 🔍 セルフチェック（致命的問題があればここでexit）
    validate(z1, z2, today, raw_counts)

    day_list = merge_dates(z1, z2, target_dates)

    html = render_html(today, day_list, now)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"\n✅ 生成完了: {OUT_PATH}")

    # 📋 日付別会議件数（消失検知の手がかり）
    print("\n📋 日付別会議件数（参考）")
    total_z1 = total_z2 = 0
    for d in target_dates:
        c1 = len(z1.get(d, []))
        c2 = len(z2.get(d, []))
        total_z1 += c1
        total_z2 += c2
        marker = " ← 今日" if d == today else ""
        print(f"  {d} ({WEEKDAY_JP[d.weekday()]}): Z① {c1}件 / Z② {c2}件{marker}")
    print(f"  ─────────────────────────")
    print(f"  合計: Z① {total_z1}件 / Z② {total_z2}件（範囲内）")


if __name__ == "__main__":
    main()
