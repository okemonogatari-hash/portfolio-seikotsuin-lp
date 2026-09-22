# Homepage versions

- 公開トップ：index.html（A：本人写真とAI素材）。homepage-v4-public-20260922 / a3cd0c3453a514c7d81ab1713efb38cd8828b044。
- 追加版：homepage-coastal.html（海景・明朝体・余白）。homepage-v5-coastal-20260922。
- 初版：homepage-v1-20260922 → 7c8dc7b2745f87a9b75826ed5e5b2ed27afd1787。
- イラスト版：homepage-v2-20260922 → 4d7a635805110f6a957bdb40a876aa9a2beaaddc。
- 写真3案と比較画面：homepage-v3-patterns-20260922 → 94e1f3b80e742cc6fb38f2a2339bf3668f16680b。

## 戻し方

専用repoのcleanな作業フォルダで、既存作業と未コミット差分を先に確認する。タグの閲覧は `git worktree add --detach <別の空きパス> <タグ>` で現在の作業を変えずに可能。

トップだけ初版へ戻す場合：`git restore --source=homepage-v1-20260922 -- index.html` を専用ブランチで実行し、リンク・画像・画面を確認して新しいcommitとしてmainへ反映する。v4へ戻す場合はsourceをhomepage-v4-public-20260922へ変更する。force-pushや履歴削除は不要。タグの内容を変更しない。

公開元はGitHub Pages / main / root。反映後はPagesビルド結果だけでなく、公開URLと配信画像を匿名アクセスで読み戻す。
