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

1. **Manual Input**: Enter stats and click "Calculate".
2. **OCR Mode**: Import images in the "OCR" tab to automatically fill stats.
    - *Tip*: Include the "Cost" display in your capture for better auto-classification.
3. **Character Settings**: Select or create character presets and adjust weights.

---

## 📊 計算方式の詳細 / Calculation Methods

| 方式 / Method | 概要 / Description |
| :--- | :--- |
| **正規化スコア (GameWith)** | メイン15点＋サブ最大100点の加点方式。 / Base 15 + Sub max 100 pts. |
| **比率重視方式 (Keisan)** | 最大値に対する比率に重みを掛けて合計。 / Weighted ratio relative to max values. |
| **ロール品質方式** | 各サブステの「引き」の強さを評価。 / Evaluates the quality of each roll. |
| **有効ステータス数** | 重み0.5以上の有効ステ数をカウント。 / Counts sub-stats with weight ≥ 0.5. |
| **CV換算方式** | 会心を重視したコミュニティ標準。 / Community standard emphasizing Crit. |

---

## ⚠️ 免責事項 / Disclaimer
本ツールはファンによる非公式ツールです。開発元（KURO GAMES）とは一切関係ありません。
This is an unofficial fan-made tool and is not affiliated with the developer (KURO GAMES).

## 📜 著作権とデータの帰属

### ゲームデータについて
本アプリケーションで使用されているゲームデータ（ステータス値、装備情報、ゲーム用語など）は、
「鳴潮（Wuthering Waves）」の公開情報およびコミュニティによって収集されたデータに基づいています。

**「鳴潮（Wuthering Waves）」および関連する全ての権利は KURO GAMES に帰属します。**

- ゲーム名:  鳴潮 / Wuthering Waves
- 開発元: KURO GAMES
- 公式サイト: https://wutheringwaves.kurogames.com/

### データソース
本アプリケーションで使用しているゲームデータは以下のソースから取得しています：
- ゲーム内公開情報
- コミュニティによって検証されたデータ
- 各種データベースサイト

### 使用許諾について
本ツールは非公式のファンメイドツールです。KURO GAMES からの公式な承認や支援は受けていません。
ゲームデータの使用は、ファンコミュニティの健全な活動の範囲内であることを意図しています。

もし著作権に関する問題がある場合は、直ちに対応いたしますので、リポジトリのIssueよりご連絡ください。

## 📜 Copyright and Data Attribution

### About Game Data
The game data used in this application (stat values, equipment information, game terminology, etc.)
is based on publicly available information from "Wuthering Waves" and data collected by the community.

**"Wuthering Waves" and all related rights belong to KURO GAMES.**

- Game Title: Wuthering Waves / 鳴潮
- Developer: KURO GAMES
- Official Website: https://wutheringwaves.kurogames.com/

### Data Sources
The game data used in this application is obtained from:
- Publicly available in-game information
- Community-verified data
- Various database websites

### Usage Permission
This tool is an unofficial fan-made project. It is not officially endorsed or supported by KURO GAMES.
The use of game data is intended to be within the scope of healthy fan community activities.

If there are any copyright concerns, we will address them immediately.  Please contact us via the repository's Issues.

---
本プロジェクトの開発には AI（Antigravity）による支援を受けています。
This project was developed with the assistance of AI (Antigravity).

Developed by f4sT357.
