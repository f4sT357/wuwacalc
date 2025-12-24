# アプリケーション処理フローと改善点分析

## 1. 処理フロー図 (Architecture & Data Flow)

```mermaid
graph TD
    subgraph UI_Layer [UI Layer (ui_components.py, tab_manager.py)]
        MainWin[ScoreCalculatorApp]
        Tabs[TabManager / QTabWidget]
        Settings[SettingsPanel]
    end

    subgraph Logic_Layer [Logic Layer]
        Events[EventHandlers]
        Calc[ScoreCalculator]
        ImgProc[ImageProcessor]
        AppLogic[AppLogic]
    end

    subgraph Data_Layer [Data & State Management]
        DM[DataManager]
        CM[ConfigManager]
        CharM[CharacterManager]
        HistM[HistoryManager]
    end

    %% Flow: Startup
    MainWin -->|Initializes| DM
    MainWin -->|Initializes| CM
    MainWin -->|Initializes| Events
    
    %% Flow: Interaction
    Settings -->|Signal| Events
    Events -->|Invoke| TabM[TabManager]
    Events -->|Invoke| ImgProc
    
    %% Flow: Image/OCR
    ImgProc -->|Request OCR| AppLogic
    AppLogic -->|OCR Result| ImgProc
    ImgProc -->|Signal: ocr_completed| MainWin
    MainWin -->|Update UI| TabM
    
    %% Flow: Calculation
    MainWin -->|Calculate Request| Calc
    Calc -->|Get Weights| CharM
    Calc -->|Get Data| DM
    Calc -->|Check Duplicates| HistM
    Calc -->|Render HTML| Renderer[HtmlRenderer]
    Renderer -->|Display| MainWin
```

## 2. 詳細プロセスフロー

1.  **起動フェーズ**:
    *   `wuwacalc17.py` がエントリーポイントとして各マネージャー（Data, Config, Character, History, Theme）をインスタンス化。
    *   `DataManager` が JSON データをロード。
    *   `UIComponents` がウィジェットを構築し、`EventHandlers` がシグナルを接続。
2.  **画像処理・OCRフェーズ**:
    *   ユーザーが画像を選択またはクリップボードから貼り付け。
    *   `ImageProcessor` がクロップ処理を行い、`AppLogic`（Tesseract）でテキスト抽出。
    *   抽出結果を正規化し、`ocr_completed` シグナルを発行。
    *   `TabManager` が結果を UI に反映。
3.  **スコア計算フェーズ**:
    *   `ScoreCalculator` が UI からステータス値を抽出。
    *   `CharacterManager` から選択中のキャラクターの重み付けを取得。
    *   `EchoData` クラスを用いて計算実行。
    *   `HistoryManager` で重複チェックを行い、履歴に保存。
    *   `HtmlRenderer` を介して結果を WebView に表示。

## 3. 現状分析 (Current Situation Analysis)

*   **アーキテクチャ**: メディエーターパターンを採用しており、`ScoreCalculatorApp` が全てのコンポーネントを保持している。
*   **コンポーネント分割**: 機能ごとにクラスが分割されており、一定の整理はなされている。
*   **通信方式**: 一部でシグナル（Signals/Slots）が使われているが、直接参照も多い。

## 4. 問題点抽出 (Problem Extraction)

1.  **タイトカップリング (Tight Coupling)**:
    *   `ScoreCalculator`, `TabManager`, `EventHandlers` などが `self.app` (メインウィンドウ) を直接保持し、そのプロパティや UI ウィジェットに直接アクセスしている。
    *   **影響**: ロジック単体でのテストが不可能であり、UI の構造変更がロジックを破壊するリスクが高い。
2.  **神オブジェクト (God Object)**:
    *   `ScoreCalculatorApp` が状態保持、UI管理、シグナル仲介の全てを担っており、責任が集中しすぎている。
3.  **依存関係の逆転原則 (DIP) の欠如**:
    *   上位モジュール（ロジック）が下位モジュール（UI）の具体的な実装に依存している。

## 5. 改善提案 (Improvement Proposal)

1.  **依存性注入 (Dependency Injection) の適用**:
    *   各クラスに `app` インスタンスを渡すのではなく、必要なマネージャー（`DataManager` 等）やロガーのみを渡すように変更する。
2.  **シグナルベースの通信への移行**:
    *   ロジック層から UI への直接操作を排除し、計算結果やログ出力は全てシグナルで行う。
3.  **データモデルの独立**:
    *   UI（ウィジェット）から直接データを読み取るのではなく、データクラス（`EchoEntry` 等）を介した通信に統一する。

## 6. 具体的な修正計画 (Action Plan)

## 7. 完了済みの疎結合化タスク



*   **`ScoreCalculator` のリファクタリング (2025/12/25)**:



    *   `ScoreCalculatorApp` (app) への直接参照を完全に排除。



    *   必要なコンポーネント（DataManager, CharacterManager, HistoryManager, ConfigManager, HtmlRenderer）をコンストラクタで注入する方式に変更。



    *   UI への通知をシグナル（`log_requested`, `error_occurred`, `single_calculation_completed`, `batch_calculation_completed`）に移行。



    *   この変更により、`ScoreCalculator` は GUI なしでユニットテストが可能になった。



    *   **バグ修正**: リファクタリングに伴い発生した `AttributeError` (calculate_all_scores 削除漏れ) を `ui_components.py`, `image_processor.py`, `event_handlers.py` で修正。呼び出しを `app.trigger_calculation()` に統合。
    *   **新機能**: キャラクター未選択時の計算待機ロジックを実装。画像取り込み時にキャラが未選択なら待機メッセージを表示し、キャラ選択後に自動で計算を実行するように改善。
    *   **改善**: 有効サブステータスカウントの精度向上。OCRテキストのノイズ除去、エイリアスの拡充（ダメージアップ系、共鳴効率）、および浮動小数点誤差を考慮した判定ロジックへの修正により、重み0.5のステータスを確実にカウントするように改善。
    *   **リファクタリング**: `TabManager` の疎結合化 (2025/12/25)。`ScoreCalculatorApp` への依存を排除し、依存性の注入方式へ移行。UI操作をシグナルベースに整理し、ロジックの独立性を向上。
    *   **リファクタリング**: `ImageProcessor` の疎結合化 (2025/12/25)。UI 操作（ファイルダイアログ、app 参照）をロジック層から排除し、シグナル駆動のアーキテクチャへ移行。画像読み込みフローを `ScoreCalculatorApp` に集約し、責務の分離を徹底。







## 8. 次の課題



*   **`TabManager` の疎結合化**: 現在 `TabManager` は UI ウィジェット（`QTabWidget`）を直接管理している。これを「タブデータモデル」と「タブビュー」に分離することを検討する。

*   **`EventHandlers` の整理**: 引き続き `self.app` への依存を減らし、各マネージャー間の仲介をシグナルベースに移行する。
