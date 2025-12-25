# プロセスフローと改善点

## アプリケーションの概要
「Wuthering Waves Echo Score Calculator」は、ゲーム「鳴潮 (Wuthering Waves)」の音骸 (Echo) のスクリーンショットをOCRで読み取り、ステータスを自動入力してスコア計算を行うPyQt6ベースのデスクトップアプリケーションです。

## プロジェクト構造（パッケージ構成）

アプリケーションは以下のパッケージに分割され、責務が明確化されています。

*   **`ui/`**: ユーザーインターフェース関連 (`ui_components.py`, `html_renderer.py`, `dialogs/`)
*   **`core/`**: アプリケーションの中核ロジック (`app_logic.py`, `score_calculator.py`, `image_processor.py`)
*   **`managers/`**: データおよび状態管理 (`data_manager.py`, `config_manager.py`, `character_manager.py`)
*   **`utils/`**: ユーティリティと共通定数 (`utils.py`, `logger.py`, `constants.py`)

## 処理フロー

### 1. 起動と初期化 (`wuwacalc17.py`)
1.  `wuwacalc17.py` がエントリポイントとして実行される。
2.  各パッケージ (`managers`, `ui`, `core`, `utils`) からクラスがインポートされる。
3.  `ScoreCalculatorApp` クラスがインスタンス化される。
4.  `managers.DataManager` がゲームデータを読み込む。
5.  `managers.ConfigManager` が設定を読み込む。
6.  `ui.UIComponents` がインスタンス化され、`create_main_layout` でUIが構築される。
7.  `core.AppLogic`, `core.ImageProcessor`, `core.ScoreCalculator` などのロジックモジュールが初期化される。
8.  シグナルとスロットが接続される (`_setup_connections`)。
9.  アプリケーションのイベントループが開始される。

### 2. 画像読み込みとOCR (`core/image_processor.py`, `core/app_logic.py`)
1.  ユーザーが画像をロード、またはクリップボードから貼り付ける。
    -   *改善済み*: 画像取り込み前にキャラクターが選択されているかバリデーションが行われる。
2.  `core.ImageProcessor` が画像を受け取り、設定された範囲でクロップを行う。
3.  OCRモードの場合、`core.AppLogic._perform_ocr` が呼び出される。
4.  画像の前処理（グレースケール、二値化など）が行われる。
5.  Tesseract OCR が実行され、テキストが抽出される。
6.  抽出されたテキストがパースされ、コスト、メインステータス、サブステータスが特定される。
    -   *改善済み*: コスト検出はOCR結果の最初の数行（3行）をスキャンして行われる。
7.  結果がUI（`managers.TabManager` 経由）に反映される。
    -   *改善済み*: キャラクター未選択時でもコストに基づいた適切なタブへの割り振りが行われるよう `find_best_tab_match` が修正された。

### 3. スコア計算 (`core/score_calculator.py`)
1.  ユーザーが「計算」ボタンを押す、または自動計算がトリガーされる。
2.  `ScoreCalculator` がUI（`TabManager`経由）から入力データを取得する。
3.  選択されたキャラクターの重み付けデータに基づき、スコアが計算される。
4.  計算結果がHTMLとしてレンダリングされ、結果表示エリアに表示される。

## 既知の問題点と改善案

### 1. ハードコードされた検証ロジック
-   **場所**: `core/app_logic.py` の `validate_and_correct_substat`
-   **問題**: 実数値とパーセント値の判定に `20.0` というマジックナンバーを使用している。
-   **理由**: 将来的なゲームバランスの調整や、低レベルの音骸において誤判定の原因となる可能性がある。
-   **改善案**: 可能であればデータ駆動のアプローチにするか、閾値を設定ファイルから読み込むようにする（現状は優先度低）。

### 2. UIコードの肥大化
-   **場所**: `ui/ui_components.py`
-   **問題**: ファイルサイズが大きく、多くの責務を担っている。
-   **理由**: 将来的な機能追加に伴い、さらに肥大化しメンテナンス性が低下する恐れがある。
-   **改善案**: レイアウト設定、スタイル定義、シグナル接続ロジックなどをさらに細分化することを検討する。
