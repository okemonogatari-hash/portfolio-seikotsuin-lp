#!/usr/bin/env python3
"""
PMチャットへ翌日のZoom枠ブリーフを自動投稿するスクリプト（GitHub Actions cron用）
- Zoom APIから明日のZ①Z②会議を取得
- 被り検知（同時刻使用 / 15分未満連続）
- Chatwork API直叩きでPMチャットに投稿

環境変数:
  ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET
  CHATWORK_API_TOKEN / CHATWORK_ROOM_ID
オプション:
  --dry-run  Chatwork投稿をスキップして本文だけ出力
"""
import os
import sys
import base64
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
HOST_NAEO = "5jeFf8S-TWC2zwtYGtLxLg"
HOST_KOYAMA = "aAUji7r9QqWo-9JSS5yEFA"
DASHBOARD_URL = "https://okemonogatari-hash.github.io/portfolio-seikotsuin-lp/irodori-zoom-dashboard.html"


def get_token():
    account_id = os.environ["ZOOM_ACCOUNT_ID"]
    client_id = os.environ["ZOOM_CLIENT_ID"]
    client_secret = os.environ["ZOOM_CLIENT_SECRET"]
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}",
        method="POST", headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]


def fetch_meetings(token, user_id):
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings?type=upcoming_meetings&page_size=300"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get("meetings", [])


def parse_jst(start_time):
    return datetime.fromisoformat(start_time.replace("Z", "+00:00")).astimezone(JST)


def filter_target_date(meetings, target_date):
    out = []
    seen = set()
    for m in meetings:
        if not m.get("start_time"):
            continue
        key = (m.get("id"), m["start_time"])
        if key in seen:
            continue
        seen.add(key)
        st = parse_jst(m["start_time"])
        if st.date() == target_date:
            m["_jst_start"] = st
            m["_jst_end"] = st + timedelta(minutes=m.get("duration", 0))
            out.append(m)
    out.sort(key=lambda x: x["_jst_start"])
    return out


def detect_cross_overlaps(z1, z2):
    overlaps = []
    for a in z1:
        for b in z2:
            if a["_jst_start"] < b["_jst_end"] and b["_jst_start"] < a["_jst_end"]:
                overlaps.append((a, b))
    return overlaps


def detect_short_gap(meetings, threshold_min=15):
    issues = []
    for i in range(len(meetings) - 1):
        gap = (meetings[i + 1]["_jst_start"] - meetings[i]["_jst_end"]).total_seconds() / 60
        if 0 <= gap < threshold_min:
            issues.append((meetings[i], meetings[i + 1], int(gap)))
    return issues


def fmt_time(m):
    return f"{m['_jst_start'].strftime('%H:%M')}-{m['_jst_end'].strftime('%H:%M')}"


def build_message(target, z1, z2, generated_at):
    weekday = "月火水木金土日"[target.weekday()]
    lines = [
        f"📅 明日（{target.strftime('%Y-%m-%d')} {weekday}）のZoom枠ブリーフ",
        f"（前日{generated_at.strftime('%H:%M')}時点・自動生成）",
        "",
    ]

    lines.append("【Z①(菜緒さん枠)】")
    if z1:
        for m in z1:
            lines.append(f"・{fmt_time(m)}　{m['topic']}")
    else:
        lines.append("　なし")
    lines.append("")

    lines.append("【Z②(小山さん枠)】")
    if z2:
        for m in z2:
            lines.append(f"・{fmt_time(m)}　{m['topic']}")
    else:
        lines.append("　なし")
    lines.append("")

    lines.append("---")
    lines.append("🔍 検知結果")
    found = False
    overlaps = detect_cross_overlaps(z1, z2)
    if overlaps:
        found = True
        lines.append("⚠️ Z①/Z② 同時刻使用：")
        for a, b in overlaps:
            lines.append(f"　・{fmt_time(a)} Z①「{a['topic']}」 × Z②「{b['topic']}」")

    for label, ms in [("Z①", z1), ("Z②", z2)]:
        gaps = detect_short_gap(ms)
        if gaps:
            found = True
            lines.append(f"⚠️ {label} 15分未満連続：")
            for prev, nxt, gap in gaps:
                lines.append(
                    f"　・{prev['_jst_end'].strftime('%H:%M')}「{prev['topic']}」"
                    f"→{gap}分→{nxt['_jst_start'].strftime('%H:%M')}「{nxt['topic']}」"
                )

    if not found:
        lines.append("✅ 被り・隙間なし")

    lines.append("")
    lines.append("---")
    lines.append("📊 詳細はダッシュボードでも見られます")
    lines.append(f"→ {DASHBOARD_URL}")
    lines.append("")
    lines.append("※ 違和感・間違いがあれば おけもん（三又謙次郎）までお気軽にご報告ください🙏")

    return "\n".join(lines)


def post_to_chatwork(token, room_id, message):
    data = urllib.parse.urlencode({"body": message}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.chatwork.com/v2/rooms/{room_id}/messages",
        data=data, method="POST",
        headers={"X-ChatWorkToken": token})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    now = datetime.now(JST)
    target = (now + timedelta(days=1)).date()

    print(f"⏱ 実行時刻 (JST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 対象日: {target}")

    token = get_token()
    print("📥 Zoom会議取得中...")
    naeo = fetch_meetings(token, HOST_NAEO)
    koyama = fetch_meetings(token, HOST_KOYAMA)

    z1 = filter_target_date(naeo, target)
    z2 = filter_target_date(koyama, target)
    print(f"📊 取得結果: Z① {len(z1)}件 / Z② {len(z2)}件")

    message = build_message(target, z1, z2, now)
    print("\n--- 投稿内容プレビュー ---")
    print(message)
    print("--- ここまで ---\n")

    if "--dry-run" in sys.argv:
        print("🟡 --dry-run モード：Chatwork投稿はスキップしました")
        return

    cw_token = os.environ["CHATWORK_API_TOKEN"]
    cw_room = int(os.environ["CHATWORK_ROOM_ID"])

    print(f"📮 Chatwork投稿中（room_id={cw_room}）...")
    res = post_to_chatwork(cw_token, cw_room, message)
    print(f"✅ 投稿完了 message_id={res.get('message_id')}")


if __name__ == "__main__":
    main()
