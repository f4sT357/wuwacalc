# 処理フロー (Process Flow) - 2025-12-25 修正完了

## 1. アプリケーション起動
- `wuwacalc17.py`: メインエントリーポイント。各マネージャーとUIコンポーネントを初期化。
- `DataManager`: 静的なゲームデータ（ステータスの最大値や選択肢）を `data/game_data.json` 等から読み込み保持。
- `CharacterManager`: 各キャラクターの個別プロファイルを `character_settings_jsons/*.json` から読み込み、重み設定や推奨メインステータスを管理。
- `ConfigManager`: アプリケーションの動作設定（言語、モード、クロップ比率など）を `config.json` から読み込み、状態を保持。
- `ThemeManager`: 外観のテーマや透明度を適用。

## 2. UI 構築とイベント接続
- `UIComponents`: PyQt6 を使用してレイアウトを構築。
- `TabManager`: コスト構成（43311等）に応じたタブの動的生成とデータ管理。
- `EventHandlers`: UI操作に対するコールバックを定義。**UIの変更は `ScoreCalculatorApp` の内部変数と `ConfigManager` の両方に即座に同期される。**

## 3. キャラクター選択とステータス反映
- キャラクターが選択されると `EventHandlers.on_character_change` が発火。
- `TabManager.apply_character_main_stats(character=internal_name)` が呼ばれ、最新の個別設定（JSON）に基づいて各タブのメインステータス候補が更新・自動選択される。

## 4. 画像読み込みとOCR
- `ImageProcessor`: 画像の取り込みとクロップ（切り抜き）を実行。
- `AppLogic`: `pytesseract` を用いてテキストを抽出し、`detect_metadata.py` を介してステータスデータを解析。解析結果は `TabManager` を通じて UI に自動入力される。

## 5. スコア計算ロジック
- `ScoreCalculator`: モード（個別/一括）に応じて計算を実行。
  - `calculate_single`: 選択中のタブのみを計算。`HtmlRenderer.render_single_score` を使用して詳細な評価を表示。
  - `calculate_batch`: 全てのタブを計算し、`HtmlRenderer.render_batch_score` を使用して平均スコアや総合評価を表示。
- **[不具合修正]**: 設定変更がロジックに反映されず常に一括計算の表示になる問題を、`EventHandlers` での内部状態同期処理の追加により解決。

## 6. 結果表示と履歴管理
- `HtmlRenderer`: 計算結果を HTML 形式で整形。
- `HistoryManager`: 結果を `history.json` に保存し、重複検知を行う。

---

# 既知の課題と改善案

## 修正済み (2025-12-25)
- [x] キャラクター選択時にメインステータスが反映されない不具合を修正。
- [x] 個別モード設定時でも一括計算の結果が表示されてしまう内部状態の同期不備を修正。
- [x] `TabManager` におけるメインステータス設定のキー照合ロジックの強化（`3_1` 形式への対応）。

## 今後の課題
- [ ] OCRの誤認（「0」と「O」など）に対する、音骸のステータス範囲（Max/Min）を用いたバリデーションの強化。
- [ ] 履歴画面での音骸同士の直接比較機能。
- [ ] ダークモード時の HTML 表示の視認性向上。