# プロセスフロー

## 1. 現状分析（完了）
- プロジェクトを `PyQt6` から `PySide6` に完全に移行した。
- `requirements.txt` に基づき、コード内のインポート、シグナル定義、ビルド設定、ライセンス表示をすべて `PySide6` に統一した。

## 2. 実施した作業
1. **全ファイルから `PyQt6` のインポートを `PySide6` に置換:**
   - `core/`, `managers/`, `ui/dialogs/`, `test/` 以下のすべてのファイルを対象。
2. **シグナルの置換:**
   - `pyqtSignal` を `Signal` に置換。
3. **ビルド設定の更新:**
   - `wuwacalc.spec` 内の `hiddenimports` と `excludes` を `PySide6` に合わせて修正。
4. **ドキュメント・ライセンスの更新:**
   - `README.md`, `LICENSE.md`, `THIRD_PARTY_LICENSES.md` 内のライセンス情報を `PySide6` (LGPL v3) に更新。
5. **クリップボード処理の修正:**
   - `core/image_processor.py` 内の Qt クリップボード経由の画像取得処理を `PySide6` の仕様に合わせて調整。

## 3. 今後の課題・改善点
- **動作確認:** 主要な機能（OCR、スコア計算、設定変更、表示切り替え）が PySide6 環境で正しく動作することを確認する。
- **UI調整:** PyQt6 と PySide6 でウィジェットのデフォルト余白などが微妙に異なる場合があるため、レイアウトの微調整が必要になる可能性がある。
