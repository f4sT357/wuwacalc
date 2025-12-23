# AI / 開発者向け実行ログ

作成日: 2025-12-24

目的: このリポジトリで AI（や人）が初見で「何が行われたか」を短時間で把握できるようにする。

重要な実行履歴（時系列・要点）
- 2025-12-24: PyInstaller を使って `wuwacalc17.py` を onefile ビルドし、動作確認。OCR（Tesseract）と `data/game_data.json` を exe に同梱できることを確認。
- 2025-12-24: `README.md` を `PROCESS_FLOW.md` に合わせて更新（目次、インストール手順、PyInstaller の注意などを追加）。
- 2025-12-24: Tesseract のライセンス（Apache-2.0）を確認し、`THIRD_PARTY_LICENSES.md` を作成・更新。
- 2025-12-24: `tools/collect_licenses.py` を追加 — `tesseract/` 内のライセンス候補を `licenses/` にコピーし、`THIRD_PARTY_LICENSES.md` に追記する自動化スクリプト。
- 2025-12-24: `licenses/` にライセンスファイルを収集し、`THIRD_PARTY_LICENSES.md` に本文を追記。
- 2025-12-24: `build.py` を更新して `licenses/` と `THIRD_PARTY_LICENSES.md` を `dist/` にコピーする処理を追加。
- 2025-12-24: ビルドを実行して `dist/` を生成。`dist` 内に `data/game_data.json`、`tesseract/`、`licenses/`、`THIRD_PARTY_LICENSES.md` が存在することを確認。
- 2025-12-24: `dist` を `wuwacalc17-distribution.zip` としてパッケージ化。
- 2025-12-24: コミット整理 — 直近コミットを分割（ソース／データ系とビルド成果物）し、ビルド成果物をリポジトリから除外するために `.gitignore` を更新。
- 2025-12-24: 履歴からビルド成果物を完全削除するために `git filter-branch` を実行し、`origin` に強制プッシュ（force push）。
  - 一時的にバックアップ用ブランチ `pre-split-2f63559` および `backup-before-purge` を作成後、最終的にこれらを削除済み（`backup-before-purge` と `pre-split-2f63559` をリモートから削除）。

主要変更ファイル（抜粋）
- 追加: `tools/collect_licenses.py`
- 追加: `licenses/` (収集済みの `LICENSE`, `README.md` 等)
- 変更: `build.py`（`licenses/` をコピーする処理を追加）
- 変更: `THIRD_PARTY_LICENSES.md`（ライセンス本文追記）
- 追加: `AI_ACTIONS.md`（このファイル）

Git 操作の注意
- 履歴を書き換えて force push したため、他のクローンがある場合は手動で同期が必要です（例: `git fetch --all` → `git reset --hard origin/main`）。
- 今回は `git filter-branch` を使用しました（警告あり）。より堅牢な方法は `git filter-repo` の使用です。

今後の推奨作業（短く）
- クリーン VM で exe 単体の動作テスト（Tesseract が未インストールの環境で）。
- 配布用にコード署名（Windows）とウイルススキャンの実施。ユーザー向け注意文（一時展開や初回起動遅延）を README に明記。
- 長期的に履歴操作の記録を残すため、今回の purge 操作の理由と日時を `RELEASE_NOTES.md` にも記載。

参照コマンド（主に使ったコマンドの抜粋）
```powershell
# PyInstaller ビルド例
pyinstaller --onefile --add-data "data;data" --add-data "tesseract;tesseract" wuwacalc17.py

# ライセンス収集スクリプト実行
python tools\collect_licenses.py

# ビルド実行（build.py）
python build.py

# 履歴からの削除（実行例）
git branch backup-before-purge HEAD
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch wuwacalc/wuwacalc17.exe wuwacalc17-distribution.zip test_run/wuwaclc17.exe test_run/wuwacalc17.exe" --prune-empty --tag-name-filter cat -- --all
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
git push origin --force --tags
```

保管場所
- 配布アーカイブ: `wuwacalc17-distribution.zip`（プロジェクトルート、`dist` から作成）
- ビルド成果物（履歴から削除済）: 以前は `wuwacalc/wuwacalc17.exe` と `wuwacalc17-distribution.zip` が含まれていましたが、現在は `.gitignore` に登録され履歴から削除済み。

問題発生時の復元手順（簡易）
1. 元の履歴が必要なら、`git fetch origin backup-before-purge` は既に削除済みのためローカルにバックアップが無ければ復元困難です。操作前のバックアップ（別リモートやアーカイブ）を常に残してください。 

---

このファイルは人間と AI がすばやく操作履歴を追えるように意図して短くまとめています。追記・修正は自由です。
