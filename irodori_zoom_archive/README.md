# irodori Zoom 文字起こし退避アーカイブ

GitHub Actions `zoom-daily.yml` が毎日 JST 16:00 頃に走り、Zoomクラウド側の文字起こし（VTT）を取得して MD で保存する。
GAS自動削除（12-13時／17-18時）に消される前に確保するのが目的。

- 取得対象：IRODORI Zoom アカウント全件（48時間ロールバック）
- 保存先：`irodori_zoom_archive/{YYYY-MM-DD}/` 配下に MDファイル
- 既処理 UUID 管理：`_processed.json`
- Notion自動投入は **オフ**（2026-05-23 おけちゃん判断）
- 旧暫定実装：`~/Library/LaunchAgents/com.okemon.zoom-rescue.plist`（PC起動必須・このCI安定後に廃止予定）

## どらさん要望（5/19 合意）
- 金曜15時の案件MTGを取りたい
- フィルター生成自体を絞ってOK
- 最終目標は IRODORI Google Drive 投入（→ 当面は GitHub Repo 経由）

## ユーザーPC側での Vault 反映運用
- `git pull` でこのフォルダがローカルに降りる
- 必要に応じて Vault `まなCSO/irodori/PJ_Zoom文字起こし自動Docs化/ローカル退避/` へ rsync or cp
