# 総合ホームページのバージョン

## 2026-09-22

| 版 | Gitタグ | 内容 |
|---|---|---|
| v1 | `homepage-v1-20260922` | 改善前の公開版。基点commit `7c8dc7b2745f87a9b75826ed5e5b2ed27afd1787`。公開HTMLとファイル一致を確認。 |
| v2 | `homepage-v2-20260922` | 森のアトリエの生成イラスト＋編集可能な見出し。本人写真を自己紹介へ。入口・余白・配色を調整。試作、本人採用・本番反映前。 |

試作ブランチ：`codex/homepage-visual-refresh-20260922`

`homepage-review.html` で「変更前 v1」「改善版 v2」「スマホ幅390px」を切り替える。比較はローカルプレビュー用。`main` がGitHub Pages公開元。

## 過去の版を見る

既存の作業中ファイルを保つため、別worktreeへ開く。

```sh
git worktree add --detach ../homepage-v1-preview homepage-v1-20260922
# 新しい版を見る場合は v2 のタグを指定する。
```

## 採用・戻す時

- 本番反映は本人が試作を採用してから。公開ブランチへの変更は別commitで残す。
- 公開後に戻す場合は、対象の公開commitを `git revert` する。履歴を消す `reset --hard` やforce-pushを使わない。
- 将来ほかのページも変わった後は、その変更を巻き戻さない。必要なら指定版から `index.html` と対象版の `assets/homepage-v2/` だけを復元して新commitにする。
- v1はindex.htmlが元の画像・内蔵CSSを使うため、index.htmlの復元で表示を戻せる。

## 素材と実装

- `assets/homepage-v2/hero-original.png`：ChatGPT内蔵画像生成の原本。
- `assets/homepage-v2/hero.webp`：約300KBの表示用画像。
- `assets/homepage-v2/PROMPT.md`：生成指示と素材の由来。
- `assets/homepage-v2/refresh.css`：今回の調整。
- `homepage-before-20260922.html`：当日の公開HTMLを保持した比較用。

採用した工程：森のRefero/DESIGN.mdメモを踏まえ、先に参考の色・余白・情景の役割を整理。キャラクター画像を生成した後、文字とリンクをHTMLで組み、スマホ・PCで確認。参考： https://styles.refero.design/ 、 https://toirostudio.com/ 、 https://www.vill.tenkawa.nara.jp/tourism/ 。特定サイトのコードや画像は流用していない。

## 写真・風景の参考調査（同日追記）

本人の補足に合わせ、写真風画像・風景が効くX原投稿とInspoの実例を調査。`homepage-photo-references.html` に出典・画像・TTPする構図を保存。v1/v2のタグは維持し、追加の画像生成や本番更新は行っていない。

## v3：写真の3パターン（2026-09-22）

本人がまとさんの方向を選び、複数パターン制作を依頼。比較入口は `homepage-lab.html`。過去のv1/v2にも切り替えられる。

| 案 | ファイル | 見せ方 |
|---|---|---|
| A / Studio | `homepage-studio.html` | 中央見出し、小さなボタン、本人写真をもとにしたAI素材との合成。まとさんの構図が起点。 |
| B / Landscape | `homepage-landscape.html` | 森のアトリエを写真風に描き、画面全体に。 |
| C / Editorial | `homepage-editorial.html` | 自然光の机の写真と大きな文字を左右に分ける。 |

3案一式のタグ：`homepage-v3-patterns-20260922`。画像原本・圧縮画像・生成指示・設計・QAは `assets/homepage-experiments/`。本番mainはこの作業の対象外。

## 2026-09-22 公開版と海景版

- Aの公開版：`homepage-public.html`（比較用コピー）。本番はmainの`index.html`、タグ`homepage-v4-public-20260922`。
- Dの追加版：`homepage-coastal.html`、タグ`homepage-v5-coastal-20260922`。わどさん指定記事の写真・明朝体・余白を参考に、新規生成2画像で構成。
- 比較画面`homepage-lab.html`にDを追加。A/Dはローカルの同一オリジンで表示し、「ページだけ開く」は各公開URLへ。
- 公開作業は別worktree `release/` / branch `codex/homepage-publish-20260922`。v4 commit a3cd0c3、v5 commit 77efa53。公開HTML・画像とローカルの一致、公開ブラウザー表示を確認済み。
- 版を戻す手順はmainの`HOMEPAGE-RELEASES.md`。既存v1/v2/v3タグは不変。

- Aのv8：homepage-v8-atmosphere-20260922 / 公開commit b11f21e。人物を囲む写真・キャラ・ガラス・紙・風の軌道を重ねた版。比較用homepage-public.htmlも同内容。

- 質感・構図の修正案 v9：homepage-craft.html / 比較入口 homepage-quality-study.html。セージ・アイボリー・真鍮でまとめ、小さな陶器のキャラをノートとコンパスに配置。homepage-v9-craft-study-20260922として保存。本人の採用未確認、公開トップのv8は変更なし。
