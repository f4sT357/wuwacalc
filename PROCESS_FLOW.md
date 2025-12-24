# アプリケーション処理フローと改善点分析

このドキュメントは、[`wuwacalc17.py`](./wuwacalc17.py) を中心とした Wuthering Waves Echo Score Calculator の処理フロー、設計方針、改善点を記述します。

## 1. アプリケーション構成と責務分離

| コンポーネント | 責務 |
| :--- | :--- |
| **[`wuwacalc17.py`](./wuwacalc17.py)** | エントリーポイント。各マネージャーの初期化とシグナルの仲介（Mediator）。 |
| **`DataManager`** | ゲームデータ（ステータス名、エイリアス等）のロードと検証。 |
| **`ConfigManager`** | アプリケーション設定（`config.json`）の永続化。 |
| **`CharacterManager`** | キャラクターごとの重み付け設定の管理。 |
| **`TabManager`** | タブの動的生成、データの抽出・復元、OCR結果のUI反映。 |
| **`UIComponents`** | UIレイアウトの構築。ロジックを持たず、ウィジェット生成に専念。 |
| **`EventHandlers`** | UIイベントの制御とマネージャー間の連携。 |
| **`ImageProcessor`** | 画像の読み込み、クロップ、OCR Worker の管理。 |
| **`ScoreCalculator`** | スコア計算の実行。履歴追加時の重複挙動（all/latest/oldest）の制御。 |
| **`HistoryManager`** | 計算履歴の保存・検索・フィルタリング。`fingerprint` による同一性判定。 |
| **`ThemeManager`** | テーマ、フォント、背景画像、透明度の制御。 |
| **`DataContracts`** | クラス間を流れるデータの型定義（`HistoryEntry`, `EchoEntry` 等）。 |

## 2. 主要な処理フロー

### 2.1 起動フロー
1. `ScoreCalculatorApp` が起動し、各マネージャーを初期化。
2. `ConfigManager` から前回終了時の設定をロード。
3. `DataManager` が `game_data.json` と `calculation_config.json` をロード。
4. `CharacterManager` が `character_settings_jsons/` 内の個別設定を読み込む。
5. `UIComponents` が UI を構築し、`EventHandlers` がシグナルを接続。

### 2.2 画像処理・OCRフロー
1. `ImageProcessor` が画像を取得（ファイル選択、一括、またはクリップボード）。
2. 設定に基づき自動クロップを適用。
3. `WorkerThread` (一括時) または `AppLogic` (単一操作時) が OCR を実行。
4. 結果（コスト、メイン、サブステ）を `ImageProcessor` または `TabManager` が適切なタブに反映。

### 2.3 スコア計算・履歴保存フロー
1. `ScoreCalculator` がタブからデータを抽出し、スコアを算出。
2. **重複チェック**: `EchoData.get_fingerprint()` による同一性判定。
3. **履歴追加**: `HistoryManager` が設定された重複モード（all/latest/oldest）に基づき保存。
4. 結果を `HtmlRenderer` で整形して表示。

## 3. 完了済みの主要タスク（直近の改善・バグ修正）

- **OCR反映ロジックの修正**: 翻訳テキスト（`findText`）ではなく内部キー（`findData`）を使用してメインステータスを反映するように改善（`image_processor.py`）。
- **クリップボード処理の堅牢化**: `ImageGrab` が失敗した場合に Qt の `QImage` から直接変換するフォールバック処理を実装（`image_processor.py`）。
- **履歴検索の精度向上**: 履歴データに評価ランクの内部キー（`rating_key`）を保持するようにし、検索時に優先的に使用するように改善。古いデータへの互換性も維持（`score_calculator.py`, `history_manager.py`）。
- **タブ構成変更時のデータ引き継ぎ改善**: タブ名に依存せず「コストと出現順序」をキーにしてデータを移行する方式に変更。構成変更時のデータ消失リスクを低減（`tab_manager.py`）。
- **重複検出ログの最適化**: 重複個体が検出された場合のみログを出力するようにし、通常の計算時のノイズを削減（`wuwacalc17.py`）。
- **OCR言語設定の整理**: 冗長な言語マッピングを削除し、内部処理を簡素化（`app_logic.py`）。
- **疎結合化**: `SettingsPanel` のシグナル化、`ImageProcessor` のシグナル化による UI とロジックの分離。

## 4. 現在の課題とネクストアクション

