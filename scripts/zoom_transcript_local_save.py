"""
Zoom録画 → VTT文字起こし → ローカル(Vault)に MD で退避保存
（ゴミ箱行き前に "とりあえず全部" 拾うための退避スクリプト・2026-05-19 はるか作成）

CI/cron 想定ではなく、手動実行する。

環境変数:
  ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET   - Zoom OAuth (S2S)
  TRANSCRIPT_LOOKBACK_HOURS - 何時間前まで遡るか (default 48)
  SAVE_DIR                  - 保存先（default: Vault内）
  PROCESSED_FILE            - 退避済 uuid 一覧
  DRY_RUN                   - 'true' なら実取得しない
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))

DEFAULT_SAVE_DIR = Path(
    "/Users/monoke/Library/CloudStorage/GoogleDrive-okemonogatari@gmail.com"
    "/マイドライブ/000 おけ森/まなCSO/irodori/PJ_Zoom文字起こし自動Docs化/ローカル退避"
)
DEFAULT_PROCESSED = DEFAULT_SAVE_DIR / "_processed.json"

# Notion投入先（🎤 Zoom文字起こしアーカイブ ページ・おけもん情報保管箱配下）
DEFAULT_NOTION_PARENT = "3652acd6-dbc8-81c1-876c-dfd4c40e4eec"
NOTION_VERSION = "2022-06-28"


def zoom_token() -> str:
    acc = os.environ["ZOOM_ACCOUNT_ID"]
    cid = os.environ["ZOOM_CLIENT_ID"]
    sec = os.environ["ZOOM_CLIENT_SECRET"]
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    body = urllib.parse.urlencode(
        {"grant_type": "account_credentials", "account_id": acc}
    ).encode()
    req = urllib.request.Request(
        "https://zoom.us/oauth/token",
        data=body,
        headers={"Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def zoom_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"https://api.zoom.us/v2{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def list_active_users(token: str) -> list[dict]:
    return zoom_get("/users?status=active&page_size=100", token).get("users", [])


def list_recordings_for_user(user_id: str, token: str, lookback_hours: int) -> list[dict]:
    today = datetime.now(JST).date()
    frm = (today - timedelta(days=max(1, lookback_hours // 24 + 1))).isoformat()
    to = (today + timedelta(days=1)).isoformat()
    data = zoom_get(
        f"/users/{user_id}/recordings?from={frm}&to={to}&page_size=50",
        token,
    )
    return data.get("meetings", [])


def fetch_vtt(download_url: str, token: str) -> str:
    req = urllib.request.Request(
        download_url, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_vtt(vtt: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    cue_time = ""
    speaker = ""
    text_lines: list[str] = []

    def flush() -> None:
        if cue_time and text_lines:
            out.append((cue_time, speaker, " ".join(text_lines).strip()))

    for raw in vtt.splitlines():
        line = raw.strip()
        if not line:
            flush()
            cue_time = ""
            speaker = ""
            text_lines = []
            continue
        if line == "WEBVTT" or line.isdigit():
            continue
        if "-->" in line:
            cue_time = line.split(" --> ")[0].split(".")[0]
            continue
        if line.startswith("<v "):
            end = line.find(">")
            if end > 0:
                speaker = line[3:end]
                text_lines.append(line[end + 1:].rstrip("</v>"))
                continue
        text_lines.append(line)
    flush()
    return out


def safe_filename(s: str) -> str:
    """ファイル名に使えない文字を _ に置換"""
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]  # 長さ制限


def classify(topic: str, host_email: str) -> str:
    """internal / client / unknown のざっくり判定"""
    internal_kw = ["IRODORI", "irodori", "朝礼", "社内", "MTG", "PJ", "勉強会"]
    # ホスト名で「内部Zoomアカウント」かどうか
    is_irodori_host = "irodori" in host_email.lower() or "1121" in host_email
    if any(k in topic for k in ["1on1", "様", "さん：", "ミーティング", "定例"]):
        # クライアント色強い言葉が入ってる場合は client 寄り判定
        # ただし「IRODORI Zoom」みたいな内部ものは別
        if "IRODORI" in topic or "朝礼" in topic:
            return "internal"
        return "client"
    if any(k in topic for k in internal_kw):
        return "internal"
    return "unknown"


def save_md(save_dir: Path, m: dict, segments: list[tuple[str, str, str]],
            host_email: str, start_jst: str, category: str) -> Path:
    topic = m.get("topic", "Untitled")
    fname = f"{start_jst.replace(':', '-').replace(' ', '_')}_{safe_filename(topic)}.md"
    out_path = save_dir / fname

    body_lines = []
    body_lines.append("---")
    body_lines.append(f"取得日時: {datetime.now(JST).isoformat()}")
    body_lines.append(f"meeting_topic: {topic}")
    body_lines.append(f"meeting_id: {m.get('id')}")
    body_lines.append(f"uuid: {m.get('uuid')}")
    body_lines.append(f"host_email: {host_email}")
    body_lines.append(f"start_time: {start_jst}")
    body_lines.append(f"duration_min: {m.get('duration')}")
    body_lines.append(f"category: {category}")
    body_lines.append(f"notion_status: 未投入")
    body_lines.append(f"合意取得: -")
    body_lines.append("---")
    body_lines.append("")
    body_lines.append(f"# 📝 {topic}")
    body_lines.append("")
    body_lines.append(f"- 開始: {start_jst}")
    body_lines.append(f"- duration: {m.get('duration')} min")
    body_lines.append(f"- host: {host_email}")
    body_lines.append(f"- category: **{category}**")
    body_lines.append(f"- segments: {len(segments)}")
    body_lines.append("")
    body_lines.append("## 文字起こし")
    body_lines.append("")
    for ts, sp, tx in segments:
        if sp:
            body_lines.append(f"[{ts}] **{sp}**: {tx}")
        else:
            body_lines.append(f"[{ts}] {tx}")
        body_lines.append("")

    out_path.write_text("\n".join(body_lines), encoding="utf-8")
    return out_path


# ---------- Notion投入対象判定 ----------

def is_notion_target(topic: str, start_jst_dt: datetime) -> bool:
    """Notion投入対象か判定する

    2026-05-19 どらさん希望ベース：
    - 金曜開催 × topic に「案件」を含む → 投入対象

    将来追加候補（合意後）：
    - 朝礼／イベントごと（おけもん人事評価用素材）
    """
    # 金曜 = weekday() == 4
    if start_jst_dt.weekday() == 4 and "案件" in topic:
        return True
    return False


# ---------- Notion API ----------

def notion_request(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ["NOTION_IRODORI_TOKEN"]
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def make_paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def make_heading_3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def upload_to_notion(
    parent_page_id: str,
    title: str,
    header_lines: list[str],
    segments: list[tuple[str, str, str]],
) -> tuple[str, str]:
    """親ページの子としてNotion新規ページ作成、本文に header + transcript を流す"""
    page = notion_request(
        "POST",
        "/pages",
        {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "icon": {"type": "emoji", "emoji": "📝"},
            "properties": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
        },
    )
    page_id = page["id"]
    page_url = page.get("url", "")

    blocks: list[dict] = []
    blocks.append(make_heading_3("📌 メタデータ"))
    for line in header_lines:
        blocks.append(make_paragraph(line))
    blocks.append(make_heading_3("📝 文字起こし"))

    for ts, sp, tx in segments:
        line = f"[{ts}] {sp}: {tx}" if sp else f"[{ts}] {tx}"
        if len(line) <= 2000:
            blocks.append(make_paragraph(line))
        else:
            for i in range(0, len(line), 2000):
                blocks.append(make_paragraph(line[i:i + 2000]))

    # Notion APIは1リクエスト最大100ブロック→バッチで投入
    for i in range(0, len(blocks), 95):
        notion_request(
            "PATCH",
            f"/blocks/{page_id}/children",
            {"children": blocks[i:i + 95]},
        )

    return page_id, page_url


# ---------- 処理済管理 ----------

def load_processed(path: Path) -> dict:
    if not path.exists():
        return {"processed": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_processed(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    lookback = int(os.environ.get("TRANSCRIPT_LOOKBACK_HOURS", "48"))
    # 日付フォルダを動的生成（毎日新しいディレクトリ）
    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    save_dir = Path(os.environ.get("SAVE_DIR", str(DEFAULT_SAVE_DIR / today_str)))
    processed_path = Path(os.environ.get("PROCESSED_FILE", str(DEFAULT_PROCESSED)))
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    notion_upload = os.environ.get("NOTION_AUTO_UPLOAD", "").lower() == "true"
    notion_parent = os.environ.get("NOTION_PARENT_PAGE_ID", DEFAULT_NOTION_PARENT)

    save_dir.mkdir(parents=True, exist_ok=True)
    state = load_processed(processed_path)
    seen: set[str] = set(state.get("processed", []))
    notion_seen: set[str] = set(state.get("notion_uploaded", []))

    token = zoom_token()
    users = list_active_users(token)
    print(f"[info] users: {len(users)} / lookback {lookback}h / processed {len(seen)} / notion_uploaded {len(notion_seen)} / save_dir={save_dir} / dry_run={dry_run} / notion_upload={notion_upload}")

    saved: list[dict] = []
    notion_uploaded: list[dict] = []

    for u in users:
        user_id = u["id"]
        user_email = u.get("email", "")
        try:
            meetings = list_recordings_for_user(user_id, token, lookback)
        except Exception as e:
            print(f"[warn] user {user_email}: {e}")
            continue
        for m in meetings:
            uuid = m.get("uuid")
            if not uuid or uuid in seen:
                continue

            tr = next(
                (
                    f
                    for f in m.get("recording_files", [])
                    if f.get("file_type") == "TRANSCRIPT"
                    and f.get("status") == "completed"
                ),
                None,
            )
            if not tr or not tr.get("download_url"):
                continue

            topic = m.get("topic", "Untitled")
            category = classify(topic, user_email)
            start_jst_dt = datetime.fromisoformat(m["start_time"].replace("Z", "+00:00")).astimezone(JST)
            start_jst = start_jst_dt.strftime("%Y-%m-%d %H:%M JST")

            # Notion投入対象判定（金曜開催×「案件」含む等）
            is_target = is_notion_target(topic, start_jst_dt)
            notion_mark = "🎯Notion対象" if is_target else "-"

            print(f"[work] {start_jst}  [{category}]  {notion_mark}  {topic[:50]}  uuid={uuid}")

            if dry_run:
                continue

            vtt = fetch_vtt(tr["download_url"], token)
            segments = parse_vtt(vtt)

            out = save_md(save_dir, m, segments, user_email, start_jst, category)
            print(f"[saved] {out.name}  ({len(segments)} segments)")

            saved_entry = {
                "uuid": uuid,
                "topic": topic,
                "category": category,
                "host_email": user_email,
                "start_time": start_jst,
                "file": str(out),
                "segments": len(segments),
                "notion_target": is_target,
                "notion_url": None,
            }

            # Notion投入（対象＆有効化フラグ＆未投入 のみ）
            if notion_upload and is_target and uuid not in notion_seen:
                try:
                    notion_title = f"{start_jst.split()[0]} {topic}"
                    header_lines = [
                        f"meeting_topic: {topic}",
                        f"meeting_id: {m.get('id')}",
                        f"uuid: {uuid}",
                        f"host_email: {user_email}",
                        f"start_time: {start_jst}",
                        f"duration_min: {m.get('duration')}",
                        f"category: {category}",
                        f"local_file: {out.name}",
                    ]
                    page_id, page_url = upload_to_notion(
                        notion_parent, notion_title, header_lines, segments
                    )
                    saved_entry["notion_url"] = page_url
                    notion_seen.add(uuid)
                    notion_uploaded.append({
                        "uuid": uuid,
                        "topic": topic,
                        "url": page_url,
                        "start_time": start_jst,
                    })
                    print(f"[notion] uploaded → {page_url}")
                except Exception as e:
                    print(f"[error] Notion投入失敗 ({topic[:30]}): {e}")

            saved.append(saved_entry)
            seen.add(uuid)

    if not dry_run and saved:
        state["processed"] = sorted(seen)
        state["notion_uploaded"] = sorted(notion_seen)
        state["last_run"] = datetime.now(JST).isoformat()
        state.setdefault("history", []).extend(saved)
        save_processed(processed_path, state)
        print(f"[save] processed list updated: {processed_path}")

    print(f"[summary] saved files: {len(saved)}  /  notion uploaded: {len(notion_uploaded)}")
    for s in saved:
        nu = f" → Notion: {s['notion_url']}" if s.get('notion_url') else ""
        print(f"  - [{s['category']}] {s['topic'][:40]}{nu}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
