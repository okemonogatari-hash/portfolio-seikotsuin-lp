#!/usr/bin/env python3
"""
PMチャットへ翌日のZoom運行表（画像）を自動投稿するスクリプト（GitHub Actions cron用）
- generate_dashboard.py が生成した irodori-zoom-tomorrow.html を Chrome headless でスクショ
- Chatwork API /rooms/{room_id}/files へPOST（curl経由・multipart/form-data）

環境変数:
  CHATWORK_API_TOKEN / CHATWORK_ROOM_ID

オプション:
  --dry-run     Chatwork投稿をスキップしてメッセージと画像生成だけ
  --force       土日祝でも投稿
  --today       実行時刻に関係なく今日ぶん（旧運用：朝の手動運用）
  --tomorrow    実行時刻に関係なく翌日ぶん（夕方の手動運用）
  --room <id>   CHATWORK_ROOM_ID を上書き（テスト用：マイチャット等）
"""
import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
REPO_ROOT = Path(__file__).resolve().parent.parent
TOMORROW_HTML = REPO_ROOT / "irodori-zoom-tomorrow.html"
SCREENSHOT_PATH = Path("/tmp/zoom_tomorrow.png")
DASHBOARD_URL = "https://okemonogatari-hash.github.io/portfolio-seikotsuin-lp/irodori-zoom-dashboard.html"
WEEKDAY_JP = "月火水木金土日"


def find_chrome():
    """Mac / Linux 環境別に Chrome / Chromium のパスを返す"""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chrome"):
        try:
            result = subprocess.run(
                ["which", name], capture_output=True, text=True, check=True
            )
            path = result.stdout.strip()
            if path:
                return path
        except subprocess.CalledProcessError:
            pass
    raise RuntimeError("Chrome/Chromium not found in PATH or common locations")


def is_off_day(date_obj):
    """土日 or 日本祝日 ならTrue＋理由文字列を返す"""
    if date_obj.weekday() >= 5:
        return True, f"{date_obj} は{'土' if date_obj.weekday()==5 else '日'}曜日"
    try:
        import jpholiday
        if jpholiday.is_holiday(date_obj):
            holiday_name = jpholiday.is_holiday_name(date_obj) or "祝日"
            return True, f"{date_obj} は日本祝日（{holiday_name}）"
    except ImportError:
        print("⚠️ jpholiday未インストール → 祝日判定skip（土日のみ判定）")
    return False, ""


def screenshot_html(html_path: Path, output_path: Path):
    """Chrome headless で HTML を 1100x900 PNG に書き出す"""
    chrome = find_chrome()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--screenshot={output_path}",
        "--window-size=1100,900",
        "--hide-scrollbars",
        "--virtual-time-budget=2000",
        f"file://{html_path.resolve()}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not output_path.exists():
        print("--- Chrome stderr ---")
        print(result.stderr)
        raise RuntimeError(f"スクショ生成失敗: {output_path}")
    return output_path


def post_image_to_chatwork(token: str, room_id: str, image_path: Path, message: str):
    """curl で multipart/form-data POST"""
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.chatwork.com/v2/rooms/{room_id}/files",
        "-H", f"X-ChatWorkToken: {token}",
        "-F", f"file=@{image_path}",
        "-F", f"message={message}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return result.stdout


def resolve_target(now: datetime) -> tuple:
    """対象日（投稿対象の運行表の日付）を決定する"""
    if "--today" in sys.argv:
        return now.date(), "明示指定（--today）"
    if "--tomorrow" in sys.argv:
        return (now + timedelta(days=1)).date(), "明示指定（--tomorrow）"
    if now.hour >= 16:
        return (now + timedelta(days=1)).date(), "16時以降→翌日ぶん（定時運用）"
    return now.date(), "16時より前→当日ぶん（朝の手動運用）"


def resolve_room_id() -> str:
    """--room <id> で上書き可。無ければCHATWORK_ROOM_IDを使う"""
    if "--room" in sys.argv:
        idx = sys.argv.index("--room")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return os.environ["CHATWORK_ROOM_ID"]


def main():
    now = datetime.now(JST)
    target, rule = resolve_target(now)
    print(f"⏱ 実行時刻 (JST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 対象日: {target}（判定: {rule}）")

    off, reason = is_off_day(target)
    if off and "--force" not in sys.argv:
        print(f"🟡 対象日は休日（{reason}）→ 投稿スキップ")
        return

    if not TOMORROW_HTML.exists():
        print(f"❌ {TOMORROW_HTML} が存在しません。先に generate_dashboard.py を実行してください")
        sys.exit(1)

    print(f"📸 Chromeでスクショ生成中: {SCREENSHOT_PATH}")
    screenshot_html(TOMORROW_HTML, SCREENSHOT_PATH)
    size_kb = SCREENSHOT_PATH.stat().st_size / 1024
    print(f"✅ スクショ生成: {size_kb:.1f} KB")

    weekday = WEEKDAY_JP[target.weekday()]
    when_label = "明日" if target == now.date() + timedelta(days=1) else (
        "今日" if target == now.date() else target.strftime("%-m/%d")
    )
    message = (
        f"📅 {when_label}（{target.strftime('%Y-%m-%d')} {weekday}）のZoom運行表\n"
        f"（{now.strftime('%Y-%m-%d %H:%M')} JST 時点 ・ 自動生成）\n\n"
        f"詳細・他の日も見るなら → {DASHBOARD_URL}\n"
        f"※ 違和感・間違いがあれば おけもん（三又謙次郎）まで🙏"
    )

    print("\n--- メッセージプレビュー ---")
    print(message)
    print("--- ここまで ---\n")

    if "--dry-run" in sys.argv:
        print("🟡 --dry-run モード：Chatwork投稿はスキップしました")
        return

    token = os.environ["CHATWORK_API_TOKEN"]
    room_id = resolve_room_id()
    print(f"📮 Chatwork投稿中（room_id={room_id}）...")
    res = post_image_to_chatwork(token, room_id, SCREENSHOT_PATH, message)
    print(f"✅ 投稿完了: {res}")


if __name__ == "__main__":
    main()
