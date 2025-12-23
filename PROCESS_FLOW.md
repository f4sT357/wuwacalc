# アプリケーション処理フローと改善点分析

このドキュメントは、[`wuwacalc17.py`](./wuwacalc17.py) を中心とした Wuthering Waves Echo Score Calculator の処理フロー、設計方針、改善点を記述します。

## 1. アプリケーション構成と責務分離

現在のプロジェクトは、以下の主要コンポーネントに分離され、保守性が高められています。

| コンポーネント | 責務 |
| :--- | :--- |
| **[`wuwacalc17.py`](./wuwacalc17.py)** | エントリーポイント。各マネージャーの初期化とシグナルの仲介（Mediator）。 |
| **`DataManager`** | ゲームデータ（ステータス名、エイリアス等）のロードと検証。 |
| **`ConfigManager`** | アプリケーション設定（`config.json`）の永続化。 |
| **`CharacterManager`** | キャラクターごとの重み付け設定の管理。 |
| **`TabManager`** | タブの動的生成、データの抽出・復元、OCR結果のUI反映。 |
| **`UIComponents`** | UIレイアウトの構築。ロジックを持たず、ウィジェットの生成に専念。 |
| **`EventHandlers`** | UIイベント（クリック、値変更）の制御とマネージャー間の連携。 |
| **`ImageProcessor`** | 画像の読み込み、クロップ、OCR Worker の管理。 |
| **`AppLogic`** | OCRテキストのパースなど、低レベルなビジネスロジック。 |
| **`ScoreCalculator`** | スコア計算の実行。 |
| **`HtmlRenderer`** | スコア計算結果の HTML フォーマット。 |
| **`HistoryManager`** | 計算履歴の保存と検索（`history.json`）。 |
| **`ThemeManager`** | テーマ、フォント、背景画像、透明度の制御。 |
| **`DataContracts`** | クラス間を流れるデータの型定義（`EchoEntry`, `SubStat`, `OCRResult` 等）。 |

## 2. 主要な処理フロー

### 2.1 起動フロー
1. `ScoreCalculatorApp` がインスタンス化され、`DataManager` が基本データをロード。
2. 各マネージャー（`Config`, `Theme`, `Character`, `History`）が初期化される。
3. `UIComponents` が UI を構築し、`EventHandlers` がシグナルを接続。
4. `_post_init_setup` で前回保存されたタブ状態や設定が復元される。

### 2.2 画像処理・OCRフロー
1. `ImageProcessor` が画像をインポート（ファイル/クリップボード）。
2. `WorkerThread` (`OCRWorker`) がバックグラウンドで OCR を実行し、UIフリーズを防止。
3. OCR 結果が `SubStat` オブジェクトとして返され、`TabManager` が現在のタブに値をセット。
4. メインステータスはコスト設定と OCR テキストから自動推論して適用される。

### 2.3 スコア計算フロー
1. `ScoreCalculator` が `TabManager` からタブ内のデータを `EchoEntry` として抽出。
2. `EchoData` クラスが重み付け設定に基づき、Normalized/CV 等のスコアを算出。
3. `HtmlRenderer` が結果を生成し、右ペインに表示。
4. 同時に `HistoryManager` が計算結果を履歴に追加。

## 3. 完了済みの主要タスク（簡略版）

これまでの開発で以下の大規模な改善が完了しています。

- **アーキテクチャの刷新**: 巨大なメインクラスから各マネージャーへの責務分散。
- **データ安全性の向上**: `DataContracts` による型定義の導入と、辞書型依存の排除。
- **非同期処理の導入**: OCR 処理を `QThread` 化し、UI の応答性を確保。
- **UI/UX の強化**: 
    - キャラクター検索・フィルタリング機能。
    - キーボードショートカット（Ctrl+V, Ctrl+Enter, Ctrl+H 等）。
    - 詳細な履歴管理ダイアログ。
    - テーマ・背景画像の高度なカスタマイズ。
- **コード品質の改善**: 型ヒントの適用、定数の一元管理（`ui_constants.py` 等）、ユニットテストの導入。

## 4. 現在の課題とネクストアクション

### ロジック・構造面
1.  **エイリアスマッチングの整理**: `ScoreCalculatorApp` にキャッシュされている `_ALIAS_PAIRS_CACHED` は、`DataManager` または `AppLogic` に移譲すべき。
2.  **型ヒントの徹底**: 一部のダイアログクラスや古いロジックで型ヒントが不足している箇所がある。
3.  **OCR 適合率の向上**: 特定の条件下での数値誤認（「.」と「,」の混同など）に対するポストプロセスの強化。

### UI/UX 面
1.  **一括計算・一括保存**: OCR バッチ処理の結果を効率的に管理・保存するフローの検討。
2.  **設定画面の整理**: 設定項目が増えているため、より直感的なタブ分けやグルーピング。

## 5. メンテナンスツール

- **[`doc_linker.py`](./tools/doc_linker.py)**: 本ドキュメント内のファイル名に自動でリンクを付与します。