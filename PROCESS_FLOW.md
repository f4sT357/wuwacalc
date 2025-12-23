# アプリケーション処理フローと改善点分析


このドキュメントは、[`wuwacalc17.py`](./wuwacalc17.py) を中心とした Wuthering Waves Echo Score Calculator の処理フロー、設計方針、改善点を記述します。

---
**AI向けプロンプト：**
このドキュメントはAIや開発者が「wuwacalc17」周辺の設計・実装・保守をスムーズに行うためのガイドです。AIがコード修正や新機能追加を行う際は、
・各セクションの「AI向け指示」や「注意点」を必ず参照してください。
・設計意図や責務分離、データフローの根拠を尊重し、既存の分割方針を崩さないようにしてください。
・新規処理や修正を加える場合は、関連する責務のクラス・モジュールに追記・修正し、責務の分散を維持してください。
・UI/ロジック/データ/イベント/テーマ/履歴/設定/画像処理/データ契約など、各レイヤの役割を明確に分離すること。
・AIによる自動修正やリファクタ時は、必ず「どの責務に属するか」を意識し、責務の肥大化・重複を避けること。
・AIが新たなデータ構造や型を導入する場合は、`data_contracts.py` で定義し、辞書型の乱用を避けること。
・AIがUI要素を追加・修正する場合は、`UIComponents`/`TabManager`/`EventHandlers`/`theme_manager.py` などの分担を守ること。
・AIがOCRや画像処理を拡張する場合は、`ImageProcessor`/`AppLogic`/`worker_thread.py` の責務分離を守ること。
・AIがショートカットや履歴、設定UIを拡張する場合は、既存の設計・分割方針を踏襲すること。
・AIがドキュメントを自動更新する場合は、`tools/doc_linker.py` の自動リンク機能を活用すること。
---

ユーザーの要求が満たされたら加筆修正してください。

## 1. アプリケーション起動フロー

### エントリーポイント ([`wuwacalc17.py`](./wuwacalc17.py))
1.  **起動**: `if __name__ == "__main__":` ブロックから `QApplication` が開始され、`ScoreCalculatorApp` がインスタンス化されます。
2.  **`ScoreCalculatorApp` の初期化**:
    *   **ログ設定**: ログファイル (`wuwacalc.log`) へ の出力を設定。
    *   **データロード**: `DataManager` が `data/` ディレクトリからJSONデータを読み込みます。
    *   **キャラクター管理**: `CharacterManager` が初期化され、`DataManager` を利用します。
    *   **設定ロード**: `ConfigManager` が [`config.json`](./config.json) を読み込みます。
    *   **テーマ適用**: `ThemeManager` が初期設定のテーマを適用します。
    *   **コンポーネント初期化**:
        *   `ScoreCalculator`: スコア計算ロジック。
        *   `TabManager`: タブ管理（保存・復元・クリア）。
        *   `AppLogic`: アプリケーションのコアロジック（OCR呼び出し、データ保存ラッパーなど）。
        *   `ImageProcessor`: 画像処理とOCRの実行フロー。
        *   `EventHandlers`: イベントシグナルの受信処理。
        *   `UIComponents`: UIの構築（レイアウト、ウィジェット作成）。
    *   **シグナル接続**: 各コンポーネント間のシグナル（OCR完了、ログメッセージなど）をメインウィンドウのスロット、または適切なマネージャーに接続します。
    *   **UI構築**: `self.ui.create_main_layout()` を呼び出し、画面全体を生成します。
    *   **初期化後処理**: `QTimer.singleShot` で `_post_init_setup` を遅延実行し、タブの更新やUIモードの反映、`EventHandlers` による初期化完了通知を行います。

## 2. 主要機能の処理フロー

### UI構築 ([`ui_components.py`](./ui_components.py))
*   **レイアウト**: メインウィンドウは左右の `QSplitter` で分割されます。
    *   **左ペイン**: 設定（コスト構成、キャラクター選択）、機能ボタン、タブ（`QTabWidget`）、計算結果表示エリア。
    *   **右ペイン**: 画像プレビューエリア（OCRモード時のみ表示）、ログ表示エリア。
*   **データ保持**:
    *   `UIComponents` は純粋なUI構築を担当します。
    *   タブごとのウィジェット情報 (`tabs_content`) は `TabManager` に移動されました。
    *   キャラクターコンボボックス (`charcombo`) はUI要素として `UIComponents` が保持していますが、ロジックからのアクセスは `app.ui.charcombo` を通じて行われます。

### タブ更新とコスト構成 ([`tab_manager.py`](./tab_manager.py))
*   `update_tabs()` メソッド (`TabManager` に移動) が [`config.json`](./config.json) やコンボボックスの選択に基づき、必要な数のタブを動的に生成します。
*   各タブにメインステータスとサブステータスの入力欄（`QComboBox`, `QLineEdit`）を生成し、`tabs_content` 辞書に参照を保存します。

### 画像処理とOCR ([`image_processor.py`](./image_processor.py), [`app_logic.py`](./app_logic.py))
1.  **画像読み込み**: `ImageProcessor.import_image()` でファイルを選択、またはクリップボードから読み込みます。
2.  **クロップ**: `perform_crop()` で設定に基づき画像を切り抜きます。
3.  **OCR実行**:
    *   `ImageProcessor` が `AppLogic._perform_ocr()` を呼び出します。
    *   `Tesseract` (pytesseract) を使用してテキストを取得します。
    *   `AppLogic.parse_substats_from_ocr()` でテキスト解析を行い、ステータスと数値を抽出します。
    *   抽出されたデータ (`substats`) を元に、`ImageProcessor._populate_tab_data()` が現在のタブ（またはCost設定で空いているタブ）のコンボボックスと入力欄に値をセットします。
    *   OCR処理が完了すると、`ScoreCalculatorApp.on_ocr_completed` 経由で `TabManager.fill_selected_tab_with_ocr_results()` が呼び出され、UIへの反映が実行されます。
    *   結果はログに表示され、必要に応じて `TabManager` を通じて画像も保存されます。

### スコア計算 ([`score_calculator.py`](./score_calculator.py))
1.  **入力取得**: 現在選択されているタブ（または全タブ）の入力ウィジェットから値を読み取ります (`extract_substats`)。
2.  **EchoData生成**: 読み取った値から `EchoData` オブジェクトを生成します。
3.  **評価実行**: `EchoData.evaluate_comprehensive()` を呼び出し、設定された重み付け (`CharacterManager` から取得) や計算方式（Normalized, Ratioなど）に基づいてスコアを算出します。
4.  **結果表示**: HTML形式でフォーマットされた結果を `ui.result_text` (`QTextEdit`) に表示します。

## 3. 気づいた点・改善案

コードベースを確認した結果、以下の点においてリファクタリングや修正の余地があります。

### 構造・設計面
    *   **進捗**: [`wuwacalc17.py`](./wuwacalc17.py) (`ScoreCalculatorApp`) にあった多くのロジック（透明度設定、OCR結果のUI反映、テストモードのバッチ処理、キャラクター更新時のUI処理など）を、それぞれの専門クラス（`ThemeManager`, `TabManager`, `ImageProcessor`, `EventHandlers`）へ分散させました。
    *   これにより、メインクラスはコンポーネントの初期化とシグナルの仲介に専念する「コントローラー」としての役割が明確になりました。
3.  **データとViewの混在 (`UIComponents.tabs_content`)** (対処済み):
    *   `tabs_content` の管理を `TabManager` に移動しました。これにより `UIComponents` はUI構築に専念し、状態管理責務が分離されました。
4.  **`ImageProcessor` と `AppLogic` の責務**:
    *   `AppLogic` がOCRの低レベル処理（Tesseract呼び出し）を担当し、`ImageProcessor` が高レベルのフロー（画像読み込み→OCR→UI反映・バッチ処理）を担当します。
    *   テストモードのロジックも `ImageProcessor.run_test_mode()` に統合されました。

### コード品質・実装詳細
1.  **型ヒントの不足**: 引数や戻り値に型ヒントがない箇所があり、可読性と安全性が低くなっています。
2.  **エラーハンドリング**: `try...except Exception` で包括的にキャッチし、ログに出力して処理を継続するパターンが多いです。以前は一部で例外を完全に握りつぶしていましたが、主要な箇所（保存処理やデータ解析など）において、ユーザーへの通知や警告ログの出力を行うように改善しました。

### バグ・不自然な挙動の可能性
1.  **OCR結果の適用**: メインステータスの自動判別ロジックが弱く、サブステータスのみの反映になりがちです。Cost判定と合わせてメインステータスも推測できるとUXが向上します。

### 安定性と変更への強さに関する課題 (今回の分析)
1.  **データ契約の強化 (改善済み)**:
    *   `AppLogic`, `ImageProcessor`, `WorkerThread`, `TabManager`, `ScoreCalculator` 間でやり取りされる主要なデータを、辞書型から `dataclasses`（`OCRResult`, `BatchItemResult`, `EvaluationResult` 等）に移行しました。
    *   これにより、ハードコードされたキー名への依存が排除され、静的解析の恩恵を受けられる堅牢な設計になりました。
2.  **エラーハンドリングの強化 (改善済み)**:
    *   以前は `DataManager` や `CharacterManager` での保存/読み込み失敗がサイレントに処理される箇所がありましたが、戻り値のチェックやUI通知（メッセージボックス、ステータスバー）を導入することで、ユーザーが異常を検知できる構成に改善しました。
    *   データパース時の `ValueError` など、致命的でないが注意が必要なエラーについては警告ログを出力するようにし、デバッグ性を向上させました。
3.  **型の安全性**:
    *   主要なロジッククラスで `Any` や緩い型ヒントが多用されており、静的解析やIDEの補完が効きにくい状態です。

## 4. 次のアクション
これまでのリファクタリングで主要な構造改善は進んでいますが、引き続き以下の改善を推奨します：
1.  **型ヒントの適用拡大**: [`image_processor.py`](./image_processor.py) 以外のモジュール ([`ui_components.py`](./ui_components.py), [`tab_manager.py`](./tab_manager.py) 等) にも型ヒントを適用し、安全性を向上させます。（現在着手可能）
2.  **定数化の推進**: ステータス名などの文字列リテラルを [`constants.py`](./constants.py) に移動し、変更に強いコードにします。

## 5. 完了済みのタスクリスト

*   **データとViewの混在解消**: `tabs_content` の管理を `UIComponents` から `TabManager` に移動しました。
*   **EventHandlers の依存関係整理 (Step 1)**: `EventHandlers` のコンストラクタで、`TabManager`, `ConfigManager` などのマネージャークラスを直接受け取るように変更し、`app` 経由のアクセスを削減しました。
*   **型ヒントの追加 ([`app_logic.py`](./app_logic.py), [`image_processor.py`](./image_processor.py))**: 安全性と可読性向上のため、タイプヒントを追加しました。
*   **マジックナンバーの排除**: `config_key` の "43311" を [`constants.py`](./constants.py) の `DEFAULT_COST_CONFIG` 定数に置き換えました。
*   **タブ初期化ロジックの簡略化**: `update_tabs` をリファクタリングし、`_create_and_add_tab_page`, `_restore_tab_data` などのヘルパーメソッドに分割することで初期化フローを整理・簡略化しました。
*   **データ構造の堅牢化**: [`data_contracts.py`](./data_contracts.py) を導入し、辞書型依存から `EchoEntry` クラスへの移行を開始しました。
*   **エラーハンドリングの強化**: `DataManager` にカスタム例外 `DataLoadError` を導入し、データ読み込み失敗時に安全にエラーダイアログを表示するようにしました。
*   **ロジックとUIの分離**: `ScoreCalculator` が UI ウィジェットを直接参照するのを止め、`TabManager.extract_tab_data` 経由でデータを取得するように変更しました。
*   **不要コードの削除**: `AppLogic` の未使用メソッド (`save_data`, `_load_data`) を整理しました。
*   **バグ修正 (リグレッション)**: `AttributeError: 'UIComponents' object has no attribute 'apply_character_main_stats'` を修正しました ([`event_handlers.py`](./event_handlers.py) の呼び出し先を `tab_mgr` に変更)。
*   **キャラクター設定の分離・堅牢化**:
    *   `CharacterProfile` データクラスの導入と `CharacterManager` へ の `get_character_profile` 実装。
    *   UI分離: 「新規作成」と「編集」メニューを追加し、意図しない上書きを防止しました。
*   **OCRエンジン切り替え機能の実装**: OpenCVとPillowの処理をユーザーが設定画面で切り替えられるようにしました。OpenCV未インストール時のUI制御とフォールバック処理も実装しました。
*   **`AppLogic.parse_substats_from_ocr` メソッドの型安全性の向上**: 戻り値の型を `List[Dict]` から `List[SubStat]` に変更し、[`data_contracts.py`](./data_contracts.py) で定義された `SubStat` データクラスを使用するように修正しました。また、ハードコードされていた `log_stat_map` を `DataManager.stat_translation_map` から取得するように変更しました。
*   **`ImageProcessor._populate_tab_data` の型安全性の向上**: 引数の `substats` の型を `List[Dict]` から `List[SubStat]` に変更し、`SubStat` データクラスの属性に直接アクセスするように修正しました。
*   **[`app_logic.py`](./app_logic.py) のコメントアウトされたデータ永続化メソッド全体を削除**: [`app_logic.py`](./app_logic.py) のコメントアウトされたデータ永続化メソッドブロック全体を削除し、インデントエラーを根本的に解決しました。
*   **[`app_logic.py`](./app_logic.py) の残存インデントエラーを修正 (再々度)**: [`app_logic.py`](./app_logic.py) のコメントアウトされたデータ永続化メソッド付近に残っていた行番号メタデータを削除しました。
*   **[`app_logic.py`](./app_logic.py) のデータ永続化メソッドを完全に削除**: [`app_logic.py`](./app_logic.py) からコメントアウトされた `save_data` および `_load_data` メソッド全体と関連するメタデータを完全に削除し、繰り返されるインデントエラーを根本的に解決しました。
*   **[`app_logic.py`](./app_logic.py) のインデントエラー修正 (さらに再々々度)**: [`app_logic.py`](./app_logic.py) のコメントアウトされたデータ永続化メソッドの最終的な削除後に残っていた余分な行番号メタデータを削除しました。
*   **[`detect_metadata.py`](./detect_metadata.py) に自動修正機能を追加し、[`app_logic.py`](./app_logic.py) のメタデータを自動削除**: [`detect_metadata.py`](./detect_metadata.py) に自動修正機能を追加し、それを使用して [`app_logic.py`](./app_logic.py) から残存していた行番号メタデータを自動的に削除しました。
*   **バグ修正 ([`wuwacalc17.py`](./wuwacalc17.py) の `on_ocr_completed` 関数)**: `SubStat` オブジェクトの属性に直接アクセスするよう修正しました。(`substat_data.get("stat", "")` -> `substat_data.stat`, `substat_data.get("value", "")` -> `substat_data.value`)
*   **UI改善 ([`ui_components.py`](./ui_components.py) のラジオボタン)**: 「入力モード」と「計算モード」のラジオボタンに `QButtonGroup` を導入し、排他的な選択を保証するように修正しました。
*   **UI改善 ([`ui_components.py`](./ui_components.py) のラジオボタン接続)**: 不要な `QGroupBox` を削除し、ラジオボタンの `toggled` シグナル接続を `lambda` 形式から `EventHandlers` 内の専用メソッドに切り替えました。
*   **OCR設定のUI分離**: OCR設定を `DisplaySettingsDialog` から `ImagePreprocessingSettingsDialog` に分離し、[`ui_components.py`](./ui_components.py) に「画像事前処理」ボタンを追加してそこから開けるようにしました。
*   **EventHandlers の分離強化**: `EventHandlers` のコンストラクタに `ui_components` を追加し、`self.app.ui.*` への直接参照を `self.ui.*` に変更しました。また、`self.app.tab_mgr.*` への直接参照を `self.tab_mgr.*` に変更しました。さらに、`self.app` の他の属性（`current_config_key`, `character_var`, `language`, `mode_var`, `score_mode_var`, `auto_apply_main_stats`, `crop_mode_var`, `crop_left_percent_var`, `crop_top_percent_var`, `crop_width_percent_var`, `crop_height_percent_var`, `app_config.enabled_calc_methods`, `_current_app_theme`, `apply_theme`）への参照を、`ConfigManager`, `CharacterManager`, `ThemeManager` の各マネージャーを介するように変更しました。これに伴い、[`wuwacalc17.py`](./wuwacalc17.py) における `EventHandlers` のインスタンス化も修正しました。
*   **`dialogs.py` のインデント修正 (CharSettingDialog部分)**: `CharSettingDialog` クラスの `__init__` メソッド、`init_ui` メソッド、および関連する内部ブロックのインデントを修正しました。
*   **`dialogs.py` のインデント修正 (CharSettingDialog._load_profile_data部分)**: `CharSettingDialog._load_profile_data` メソッド内の `if` および `for` ループのインデントを修正しました。
*   **[`constants.py`](./constants.py) に不足していた定数を追加** (2025-12-18):
    *   `DEFAULT_COST_CONFIG = "43311"`: デフォルトのコスト構成を定義。
    *   `OCR_ENGINE_PILLOW = "pillow"`, `OCR_ENGINE_OPENCV = "opencv"`: OCRエンジンの識別子を定義。
    *   JSON key constants: `KEY_SUBSTATS`, `KEY_STAT`, `KEY_VALUE`, `KEY_CHARACTER`, `KEY_CHARACTER_JP`, `KEY_CONFIG`, `KEY_AUTO_APPLY`, `KEY_SCORE_MODE`, `KEY_ECHOES`, `KEY_MAIN_STAT`, `KEY_CHARACTER_WEIGHTS`, `KEY_CHARACTER_MAINSTATS` を追加し、データ構造のキー名をハードコードから定数化しました。
*   **`dialogs.py` の大量のインデントエラーを修正** (2025-12-18):
    *   `DisplaySettingsDialog` クラスの `init_ui` メソッドおよび複数のヘルパーメソッド（`_pick_text_color`, `_select_background_image`, `_cleanup_images`, `_clear_background_image`, `_update_selected_theme`, `_update_opacity_label`, `_apply_settings`, `_pick_input_bg_color`, `_reset_input_bg_color`, `_full_reset`, `_get_compatible_fonts`, `_update_selected_font`, `_open_help`）のインデントを修正。
    *   `ImagePreprocessingSettingsDialog` クラスの `init_ui` メソッドおよび `_apply_settings` メソッドのインデントを修正。
    *   `_open_help` メソッド内の `ff"file:..."` のタイプミスを `f"file:..."` に修正。
    *   これにより、`dialogs.py` のPython構文エラーがすべて解消され、正常にインポート可能になりました。
*   **[`wuwacalc17.py`](./wuwacalc17.py) の初期化順序を修正** (2025-12-18):
    *   `self.ui = UIComponents(self)` の初期化を `EventHandlers` のインスタンス化の前に移動し、`AttributeError: 'ScoreCalculatorApp' object has no attribute 'ui'` エラーを解消しました。
*   **[`event_handlers.py`](./event_handlers.py) の存在しないメソッド呼び出しを修正** (2025-12-18):
    *   `CharacterManager` に存在しない `set_selected_character()` メソッドの呼び出しを `self.app.character_var` へ の直接代入に置き換えました。
    *   `CharacterManager` に存在しない `get_selected_character()` メソッドの呼び出しを `self.app.character_var` へ の直接参照に置き換えました。
    *   これにより、`AttributeError: 'CharacterManager' object has no attribute 'set_selected_character'` エラーを解消しました。
*   **[`wuwacalc17.py`](./wuwacalc17.py) の `SubStat` オブジェクトアクセスを修正** (2025-12-18):
    *   `on_ocr_completed` メソッド内で、`SubStat` データクラスの属性に辞書形式の `.get()` メソッドでアクセスしていたのを、直接属性アクセス（`substat_data.stat`, `substat_data.value`）に修正しました。
    *   これにより、`AttributeError: 'SubStat' object has no attribute 'get'` エラーを解消しました。
*   **[`wuwacalc17.py`](./wuwacalc17.py) の包括的なリファクタリング** (2025-12-18):
    *   **インポート順序の整理**: 不要な空行を削除し、標準ライブラリのインポートを統一された順序に整理しました。
    *   **重複コメント削除**: `CharacterManager` シグナル接続時の重複するコメント（"Connect signals from CharacterManager"）を1つに統合し、コード読みやすさを向上させました。
    *   **設定値の二重読み込み削除**: `_init_config()` メソッド内で、`app_config` を複数回読み込んでいた冗長な処理を削除し、`self.app_config` への一度の代入に統一しました。
    *   **`tr()` メソッドの改善**: フォーマット失敗時のエラーハンドリングを統一し、`exc_info=True` フラグを削除してログレベルを一貫させました。エラー詳細はより簡潔に出力するようにしました。
    *   **ダイアログ開閉メソッドの統合**: `open_char_settings_new()`, `open_char_settings_edit()`, `open_display_settings()`, `open_image_preprocessing_settings()` の4つのダイアログ開閉メソッドで重複していたエラーハンドリングコードを `_open_dialog()` ヘルパーメソッドに統合し、DRY原則を適用しました。これにより、ダイアログ開閉時の例外処理が統一され、保守性が大幅に向上しました。
    *   **`_init_vars()` の整理**: `_frame_original_properties` の初期化をメソッド内で行うことで、初期化ロジックを統一しました。
*   **ハードコード値の constants 化** (2025-12-18):
    *   **UI定数の定義**: ウィンドウ、ダイアログ、イメージプレビュー、タイマー間隔などのハードコードされた数値を [`constants.py`](./constants.py) に集約しました。
        *   `DEFAULT_WINDOW_WIDTH`, `DEFAULT_WINDOW_HEIGHT`: メインウィンドウのデフォルトサイズ (1000x950)
        *   `DIALOG_CHAR_SETTING_WIDTH`, `DIALOG_CHAR_SETTING_HEIGHT`: キャラクター設定ダイアログのサイズ (600x600)
        *   `DIALOG_CROP_WIDTH`, `DIALOG_CROP_HEIGHT`: 画像クロップダイアログのサイズ (900x700)
        *   `IMAGE_PREVIEW_MAX_WIDTH`, `IMAGE_PREVIEW_MAX_HEIGHT`: プレビュー画像の最大寸法 (600x260)
        *   `TIMER_SAVE_CONFIG_INTERVAL`, `TIMER_CROP_PREVIEW_INTERVAL`, `TIMER_RESIZE_PREVIEW_INTERVAL`: タイマー間隔(ms)
    *   **[`config_manager.py`](./config_manager.py) の UIConfig を constants 参照に更新**: デフォルト値を constants から参照するように変更し、単一の真実の源（SSOT）を実現しました。
    *   **dialogs.py でダイアログサイズを constants から参照**: ハードコードされた `resize(600, 600)` と `resize(900, 700)` を定数に置き換えました。
    *   **[`event_handlers.py`](./event_handlers.py) でタイマー間隔を constants から参照**: `save_config()` の 500ms、`schedule_crop_preview()` の 100ms などをタイマー定数に置き換えました。
    *   **[`event_handlers.py`](./event_handlers.py) の actual_save_config() を簡素化**: 冗長な `get` してから `update` する処理を削除し、必要な設定値のリスト化により保守性を向上させました。
    *   **バグ修正**: `_init_config()` 内で `self.app_config` ではなく `app_config` というローカル変数を参照していたエラー（`NameError: name 'app_config' is not defined`）を修正し、`self.app_config` への統一参照に変更しました。
*   **大規模なメインクラスのリファクタリング** (2025-12-21):
    *   `ScoreCalculatorApp` ([`wuwacalc17.py`](./wuwacalc17.py)) の責務を分散。
    *   フレーム透明度制御を `ThemeManager` へ移動。
    *   OCR結果のタブ反映ロジックを `TabManager` へ移動。
    *   テストモードのバッチ処理フローを `ImageProcessor` へ移動。
    *   キャラクタープロファイル更新・登録時のUI更新ロジックを `EventHandlers` へ移動。
    *   これにより、各クラスの関心が分離され、保守性が向上しました。
*   **`dialogs.py` のパッケージ化** (2025-12-21):
    *   850行を超えていた `dialogs.py` を解体し、`dialogs/` ディレクトリ配下にクラスごとのモジュール（[`char_setting.py`](./dialogs/char_setting.py), [`crop.py`](./dialogs/crop.py) 等）を配置。
    *   `dialogs/[`__init__.py`](./dialogs/__init__.py) を利用して旧来のインポート形式を維持しつつ、保守性を向上。
*   **スコア計算と表示ロジックの分離** (2025-12-21):
    *   `ScoreCalculator` から HTML 生成コードを排除し、表示担当の `HtmlRenderer` クラスを新設。
    *   計算ロジック（Model/Logic）と表示ロジック（View/Renderer）の責務を分離。
*   **`UIComponents` のさらなる細分化** (2025-12-21):
    *   100行を超える巨大なレイアウト作成メソッドを、目的別の小さなプライベートメソッド（`_setup_basic_settings_row` 等）に分解。
    *   コードの可読性が向上し、UIの特定箇所のデバッグが容易になりました。
*   **コードベースのリファクタリング** (2025-12-21):
    *   **重複コードの削除**:
        *   [`tab_manager.py`](./tab_manager.py) から重複した `on_character_change` メソッドを削除（[`event_handlers.py`](./event_handlers.py) に既存）
        *   [`tab_manager.py`](./tab_manager.py) から重複インポート（`QPixmap`, `QImage`, `Qt`）を削除
        *   [`tab_manager.py`](./tab_manager.py) の `_restore_tab_data` メソッドから重複した `setCurrentText` 呼び出しを削除
        *   [`ui_components.py`](./ui_components.py), [`app_logic.py`](./app_logic.py) からコメントアウトされた不要なコードを削除
    *   **バグ修正**:
        *   [`image_processor.py`](./image_processor.py) (164行目): 未定義変数 `cost` を `result.cost` に修正
        *   [`event_handlers.py`](./event_handlers.py) (322行目): 属性名の不一致 `self.tab_manager` を `self.tab_mgr` に修正
    *   **定数の一元化**:
        *   新規モジュール [`ui_constants.py`](./ui_constants.py) を作成し、UI関連の定数を集約
        *   ウィンドウサイズ、レイアウト高さ、画像プレビューサイズ、ウィジェット幅、サブステータス数などを定数化
        *   [`wuwacalc17.py`](./wuwacalc17.py), [`ui_components.py`](./ui_components.py), [`image_processor.py`](./image_processor.py) で `ui_constants` モジュールから定数をインポート
    *   **マジックナンバーの定数化**:
        *   [`ui_components.py`](./ui_components.py): `60` → `VALUE_ENTRY_WIDTH`, `50` → `CROP_ENTRY_WIDTH`, `5` → `NUM_SUBSTATS`
        *   設定値がない場合のフォールバック処理として定数を使用（[`wuwacalc17.py`](./wuwacalc17.py)）
    *   **保守性の向上**: 定数の一元管理により、値の変更が容易になり、複数ファイルでの重複定義を解消
    *   **検証**: 全てのPythonファイルが構文チェック（`python -m py_compile`）を通過
*   **パフォーマンス改善と非同期処理 (OCR Worker)** (2025-12-21):
    *   **バックグラウンド処理**: [`worker_thread.py`](./worker_thread.py) を作成し、`OCRWorker` クラス (QThread) を実装しました。
    *   **UIフリーズの解消**: [`image_processor.py`](./image_processor.py) のバッチ処理 (`process_batch_images`) を非同期化し、OCR処理をメインスレッドから分離しました。
    *   **シグナル連携**: ワーカーからの進捗、結果、エラー通知をシグナル/スロットで安全にメインスレッドに伝達する仕組みを構築しました。
*   **テストカバレッジの向上** (2025-12-21):
    *   [`test_echo_data.py`](./test_echo_data.py) を作成し、`EchoData` クラスの主要な計算ロジック (`calculate_score_normalized`, `calculate_score_cv_based`, `evaluate_comprehensive`) のユニットテストを追加しました。
    *   `EchoData` の計算ロジックにおける日本語キー依存（CV計算等）を特定し、テストケースで対応しました。
*   **コード品質改善とリファクタリング** (2025-12-21):
    *   **EchoData の言語依存解消**: [`echo_data.py`](./echo_data.py) 内のハードコードされた日本語ステータス名（CV計算ロジック等）を、[`constants.py`](./constants.py) に定義した定数を使用するように変更し、保守性を向上させました。
    *   **OCRパースロジックの抽出**: [`app_logic.py`](./app_logic.py) の `parse_substats_from_ocr` メソッドから、1行分の解析ロジックを `_parse_single_line` メソッドとして抽出しました。
    *   **AppLogic テストの追加**: [`test_app_logic.py`](./test_app_logic.py) を作成し、抽出したOCRパースロジック (`_parse_single_line`) のユニットテストを追加しました。
    *   **ScoreCalculator の簡略化**: [`score_calculator.py`](./score_calculator.py) の `calculate_batch_scores` メソッドから、単一タブの評価ロジックを `_evaluate_tab_for_batch` に抽出し、可読性を向上させました。
    *   **命名規則の統一 (リファクタリング)** (2025-12-21):
        *   [`ui_components.py`](./ui_components.py), [`event_handlers.py`](./event_handlers.py), [`tab_manager.py`](./tab_manager.py) において、可読性向上のため `charcombo` を `character_combo` に、`update_char_combobox` を `update_character_combo` にリネームしました。
*   **UX改善 (ステータスバーとツールチップ)** (2025-12-21):
    *   **ステータスバーの導入**: `ScoreCalculatorApp` ([`wuwacalc17.py`](./wuwacalc17.py)) に `QStatusBar` を追加し、ログメッセージ (`gui_log`) をステータスバーにも表示するように変更しました。これにより、ユーザーへのフィードバック性が向上しました。
    *   **ツールチップの追加**: `UIComponents` ([`ui_components.py`](./ui_components.py)) の計算手法選択チェックボックスにツールチップを追加し、マウスホバー時に各手法の説明 (`normalized_score_desc` 等) が表示されるようにしました。
*   **コード品質と堅牢性の向上** (2025-12-21):
    *   **TabManager の型安全性向上**: `TabManager` ([`tab_manager.py`](./tab_manager.py)) に型ヒント (`List`, `Tuple`, `SubStat` 等) を全面的に追加し、開発時の安全性と可読性を向上させました。
    *   **DataManager のデータ検証強化**: `DataManager` ([`data_manager.py`](./data_manager.py)) に `validate_data` メソッドを追加し、JSONロード後に必須キー (`substat_max_values`, `tab_configs` 等) の存在を確認するロジックを実装しました。
*   **exe化に向けた最適化 (2025-12-21)**:
    *   **パス管理の改善**: [`utils.py`](./utils.py) に `get_resource_path()` を導入し、PyInstallerでパッケージングされたリソース (`data/`, `character_settings_jsons/`, `tesseract/`) へのアクセスを確実なものにしました。
    *   **ユーザーデータの分離**: 設定ファイル ([`config.json`](./config.json)) やログ、ユーザーが作成したキャラクター設定などは、実行ファイルと同じディレクトリ（`get_app_path()`）に保存・読み込みされるように分離しました。
    *   **キャラクターロードの堅牢化**: `CharacterManager` が内蔵のキャラクター設定と、ユーザーが後から追加した設定の両方を適切にマージして読み込めるように修正しました。
    *   **Specファイルの作成**: アイコン設定、コンソール非表示、不要ライブラリの除外、リソースの同梱設定を含む `wuwacalc.spec` を作成しました。
*   **例外ハンドリングの強化と「握りつぶし」の解消 (2025-12-21)**:
    *   **[`tab_manager.py`](./tab_manager.py)**: タブラベル生成失敗時に `pass` していたのを警告ログ出力に変更。
    *   **[`score_calculator.py`](./score_calculator.py)**: サブステータスの数値解析失敗時にサイレントにスキップしていたのを警告ログ出力に変更。
    *   **[`character_manager.py`](./character_manager.py) / [`dialogs/char_setting.py`](./dialogs/char_setting.py)**: キャラクター保存処理の成否を戻り値で返し、UI側で保存失敗時にエラーメッセージを表示するように改善。
    *   **[`event_handlers.py`](./event_handlers.py)**: 設定の自動保存失敗時に `gui_log` (ステータスバー) を通じてユーザーに通知するように変更。
*   **キーボードショートカットの導入 (2025-12-21)**:
    *   `Ctrl+V`: クリップボードから貼り付け。
    *   `Ctrl+Enter` / `F5`: スコア計算実行。
    *   `Ctrl+S`: 計算結果をテキストファイルに出力。
    *   `Ctrl+R`: 全アイテムをクリア（リセット）。
    *   UIボタンにショートカット情報のツールチップを追加しました。
*   **メインステータスOCR判別機能の強化 (2025-12-21)**:
    *   `OCRResult` に `main_stat` フィールドを追加。
    *   [`app_logic.py`](./app_logic.py) に `detect_main_stat_from_ocr` を実装。コストに応じた候補絞り込みと、エイリアスマッチングを導入。
    *   [`image_processor.py`](./image_processor.py) を更新し、検知されたメインステータスをタブのコンボボックスに自動セットする機能を実装。
    *   これにより、コスト・メイン・サブすべてのOCR自動入力が大幅に強化されました。
*   **キャラクター選択の検索・フィルタリング機能の導入 (2025-12-21)**:
    *   キャラクター選択コンボボックスを編集可能（Editable）にし、インライン検索機能を実装。
    *   大文字小文字を区別しない部分一致フィルタリングロジックを追加。
    *   検索結果がない場合の「該当なし」メッセージ表示に対応。
    *   フィルタリング中の誤作動を防ぐため、シグナル接続を `activated` に最適化。
*   **簡易履歴機能の導入 (2025-12-21)**:
    *   `history.json` を使用した最大100件の履歴保存機能を実装。
    *   `HistoryManager` を新設し、計算実行時に「キャラクター名」「コスト」「評価結果」を自動記録。
    *   `HistoryDialog` を作成し、テーブル形式での表示と、キャラクター・コスト・キーワード・日付による高度なフィルタリング（比較用）を実現。
    *   `Ctrl+H` ショートカットおよびUIボタンを追加。
*   **データ契約（Data Contracts）の全面導入 (2025-12-21)**:
    *   [`data_contracts.py`](./data_contracts.py) を拡張し、`BatchItemResult`, `CropConfig`, `EvaluationResult`, `TabImageData`, `TabResultData` などのデータクラスを定義。
    *   [`echo_data.py`](./echo_data.py): `evaluate_comprehensive` の戻り値を `EvaluationResult` に変更。
    *   [`worker_thread.py`](./worker_thread.py) / [`image_processor.py`](./image_processor.py): ワーカースレッド通信をデータクラス化し、ハードコードされた辞書キーを排除。
    *   [`tab_manager.py`](./tab_manager.py): タブごとの画像・結果保持をデータクラスに変更。
    *   [`score_calculator.py`](./score_calculator.py) / [`html_renderer.py`](./html_renderer.py): 計算結果の受け渡しと表示ロジックをデータクラス属性ベースに刷新。

### 安定性と変更への強さに関する課題 (今回の分析)
1.  **データ契約の欠如**: `AppLogic` と UI 間でやり取りされるデータ（OCR結果、保存データ）が `dict` 型で、キー名がハードコードされています。
2.  **エラーハンドリングの脆弱性**:
    *   `AppLogic` の一部（例：`save_data`）が UI ウィジェット構造（`tabs_content` の中身）に依存しており、UI 変更がロジックを破壊する可能性があります。
3.  **型の安全性**:
    *   主要なロジッククラスで `Any` や緩い型ヒントが多用されており、静的解析やIDEの補完が効きにくい状態です（一部改善済み）。

## 6. メンテナンスツール

### ドキュメント自動リンク (`tools/[`doc_linker.py`](./tools/doc_linker.py))
*   **機能**: `PROCESS_FLOW.md` 内に記述されたファイル名を検出し、自動的にリポジトリ内の該当ファイルへの Markdown リンク (`[`filename`](./path/to/file)`) に変換します。
*   **使用方法**: 新しいファイルを作成したり、ドキュメントにファイル名を追記した後に実行してください。
    ```bash
    python tools/[`doc_linker.py`](./tools/doc_linker.py)
    ```

