# 🌊 鳴潮 音骸スコア計算機 / Wuthering Waves Echo Score Calculator

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Custom-green.svg)](LICENSE.md)

鳴潮（Wuthering Waves）の音骸（Echo）のスコアを計算・評価するためのデスクトップアプリケーションです。
OCR機能による自動入力、キャラクター別の重み付け設定、多彩な計算方式に対応しています。

A desktop application to calculate and evaluate Echo scores for Wuthering Waves.
Supports automatic input via OCR, character-specific weighting presets, and multiple calculation methods.

---

## 📖 目次 / Table of Contents
- [機能 / Features](#-機能--features)
- [セットアップ / Setup](#-セットアップ--setup)
- [使用方法 / Usage](#-使用方法--usage)
- [計算方式の詳細 / Calculation Methods](#-計算方式の詳細--calculation-methods)
- [免責事項 / Disclaimer](#-免責事項--disclaimer)

---

## ✨ 機能 / Features

### 日本語 (JP)
- **OCR自動入力**: スクリーンショットやクリップボードの画像からステータスを自動認識。
- **5つの計算方式**: 正規化、比率重視、ロール品質、有効ステータス数、CV換算に対応。
- **キャラクタープリセット**: 各キャラに合わせた有効ステータスと重み付けを保存可能。
- **外観カスタマイズ**: テーマ変更や背景画像の個別設定が可能。
- **一括計算**: 複数の音骸をまとめて評価。

### English (EN)
- **OCR Auto-Input**: Automatically recognize stats from screenshots or clipboard images.
- **5 Calculation Methods**: Supports Normalization, Ratio, Roll Quality, Effective Stats Count, and Crit Value (CV).
- **Character Presets**: Save effective stats and weighting settings for each character.
- **Appearance Customization**: Customize themes and background images.
- **Batch Calculation**: Evaluate multiple Echoes at once.

---

## 🛠️ セットアップ / Setup

### 1. Python環境の準備 / Python Environment
Python 3.8以上が必要です。
Requires Python 3.8 or higher.

```bash
pip install -r requirements.txt
```

### 2. Tesseract OCRのインストール / Tesseract OCR Installation
OCR機能を使用するには、Tesseract OCRのインストールが必要です。
To use the OCR feature, you must install Tesseract OCR.

1. [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラーをダウンロード。
2. インストール時、「Additional Language Data」で **Japanese** を必ず選択してください。
3. デフォルトの場所 (`C:\Program Files\Tesseract-OCR`) にインストールすることを推奨します。

1. Download the installer from the [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
2. During installation, make sure to select **Japanese** in "Additional Language Data".
3. Recommended installation path: `C:\Program Files\Tesseract-OCR`.

---

## 🚀 使用方法 / Usage

```bash
python wuwacalc17.py
```

1. **手動入力**: 各ステータスを入力して「計算」をクリック。
2. **OCRモード**: 「OCR」タブで画像を読み込み、ステータスを反映。
    - *Tip*: 一括読み込み時は「コスト」表示を含めてキャプチャすると自動分類が働きます。
3. **キャラ設定**: 使用するキャラクターを選択または新規作成し、重みを調整。

# Wuthering Waves Echo Score Calculator (鳴潮 音骸スコア計算機)

このリポジトリは、`wuwacalc17.py` をエントリーポイントとするデスクトップアプリケーションです。
本 README は現在の実装構造と処理フロー（`PROCESS_FLOW.md` に基づく）を要約します。

## 目次 / Table of Contents
- [主要コンポーネントと責務](#主要コンポーネントと責務)
- [処理フロー（概要）](#処理フロー概要)
- [セットアップ（詳細）](#セットアップ詳細)
- [実行方法](#実行方法)
- [PyInstaller での配布（任意）](#pyinstaller-での配布任意)
- [トラブルシューティング](#トラブルシューティング)
- [貢献と連絡先](#貢献と連絡先)
- [ライセンスと免責](#ライセンスと免責)

## 主要コンポーネントと責務
- **`wuwacalc17.py`** — エントリーポイント。各マネージャー初期化とシグナル仲介（Mediator）。
- **`data_manager.py`** — ゲームデータ、エイリアス、検証ロジック。
- **`config_manager.py`** — `config.json` による設定の永続化と読み込み。
- **`character_manager.py`** — キャラクター別重み付け設定の管理。
- **`tab_manager.py`** — タブ生成、OCR結果の反映、データ抽出/復元。
- **`ui_components.py` / `event_handlers.py`** — UI ビルドとイベント制御（ロジック非混入を目標）。
- **`image_processor.py` / `worker_thread.py`** — 画像前処理、クロップ、OCR ワーカーの管理。
- **`score_calculator.py`** — スコア算出と履歴追加ロジック（`fingerprint` による重複判定）。
- **`history_manager.py`** — 履歴保存・検索・フィルタリング。重複モード（`all` / `latest` / `oldest`）を実装。

詳細は `PROCESS_FLOW.md` を参照してください。

## 処理フロー（概要）
- 起動: `ScoreCalculatorApp` が各マネージャーを初期化し、`config.json` の設定を反映します。
- 画像/OCR: `ImageProcessor` が自動クロップを行い、`WorkerThread` で OCR を実行。結果は `TabManager` を通じて UI に反映されます。
- 計算/履歴: `ScoreCalculator` が統合データからスコアを算出し、`fingerprint`（MD5）で重複チェックを行った上で `HistoryManager` に保存します。

## セットアップ（手短に）
### 前提条件 / Prerequisites
- Python 3.8 以上（3.8+ 推奨）
- Windows 環境の場合は Visual C++ 再頒布可能パッケージが必要になる場合があります（特に PyQt6 / numpy / cv2 使用時）。

### 仮想環境と依存関係のインストール
1. リポジトリのルートで仮想環境を作成・有効化します（PowerShell の例）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 依存関係をインストールします。

```powershell
pip install -r requirements.txt
```

### Tesseract OCR のインストール（OCR 機能を使う場合）
1. Windows 向けのインストーラ（UB-Mannheim など）をダウンロードしてインストールします。
    - 推奨パス: `C:\Program Files\Tesseract-OCR`。
2. インストール時に日本語データ（`jpn`）を追加してください。
3. PATH に Tesseract のインストール先を追加するか、アプリ内で `pytesseract.pytesseract.tesseract_cmd` に明示的なパスを設定します。

```python
import pytesseract
# 例: Windows の標準インストール先を指定
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

4. 代替: `TESSDATA_PREFIX` 環境変数を使って tessdata の場所を指定できます。

### (任意) 追加の手順
- 設定ファイル: `config.json` を編集して初期設定を変更できます。
- キャラクタープリセット: `character_settings_jsons/` 配下に JSON ファイルとして保存されます。

## 実行方法
```powershell
python wuwacalc17.py
```

## PyInstaller での配布（任意）
1. 仮想環境を有効化した状態で PyInstaller をインストールします（未インストールの場合）。

```powershell
pip install --upgrade pyinstaller
```

2. 単一ファイル exe を作る基本コマンド:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --onefile --noconfirm --clean wuwacalc17.py
```

3. データファイル（`tessdata` や `character_settings_jsons`、`images` 等）を同梱する場合は `--add-data` を使うか、生成される `.spec` を編集してください。

```powershell
# 例: tessdata を同梱（Windows のパス区切りは ";" ではなく ":" を使用）
.\.venv\Scripts\python.exe -m PyInstaller --onefile --add-data "tesseract/tessdata;tesseract/tessdata" wuwacalc17.py
```

4. ビルド後の成果物は `dist/` に入ります。実行時にログやエラーが出る場合は `build/` 下のログや `warn-*.txt` を確認してください。

## 現在の機能と重点改善点
- 履歴管理: `history_duplicate_mode`（`all`/`latest`/`oldest`）を持ち、`fingerprint` による同一性判定を行います。
- 検索: 評価ランク（SSS〜C）を区別する正規表現ベースのフィルタ。
- 改善予定: エイリアスマッチングの整理、OCR の後処理強化、履歴統計の可視化。

## 開発・メンテナンス
- ドキュメントリンク自動生成: `tools/doc_linker.py` を利用。
- 主要設定: `config.json`、キャラクター設定は `character_settings_jsons/` 配下。

## ライセンスと免責
本ツールはファンメイドの非公式ツールです。`Wuthering Waves` および関連権利は KURO GAMES に帰属します。

問題や改善提案は Issue を立ててください。

---
更新元ドキュメント: `PROCESS_FLOW.md`
