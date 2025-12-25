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
#![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg) ![License](https://img.shields.io/badge/License-Custom-green.svg)

# Wuthering Waves Echo Score Calculator (鳴潮 音骸スコア計算機)

This repository contains a desktop application whose entrypoint is `wuwacalc17.py`.
Below is an implementation-focused README that reflects the current structure and process flow (see `PROCESS_FLOW.md` for details).

## Badges
- Python 3.8+ supported
- License: see `LICENSE.md`

## Table of Contents / 目次
- [Overview / 概要](#overview--概要)
- [Core Components / 主要コンポーネントと責務](#core-components--主要コンポーネントと責務)
- [Process Flow / 処理フロー（概要）](#process-flow--処理フロー概要)
- [Setup (Detailed) / セットアップ（詳細）](#setup-detailed--セットアップ詳細)
- [Run / 実行方法](#run--実行方法)
- [Distribution with PyInstaller / PyInstaller での配布（任意）](#distribution-with-pyinstaller--pyinstaller-での配布任意)
- [Packaging Notes / 配布時の注意点とサンプルコード](#packaging-notes--配布時の注意点とサンプルコード)
- [Troubleshooting / トラブルシューティング](#troubleshooting--トラブルシューティング)
- [Contributing / 貢献](#contributing--貢献)
- [License & Disclaimer / ライセンスと免責](#license--disclaimer--ライセンスと免責)

## Overview / 概要
This application calculates Echo scores for Wuthering Waves using OCR-assisted input, character-specific weighting presets, and multiple calculation methods.

## Core Components / 主要コンポーネントと責務
- `wuwacalc17.py` — Entrypoint and mediator for managers.
- `data_manager.py` — Loads and validates game data (e.g. `data/game_data.json`).
- `config_manager.py` — Persists and loads settings from `config.json`.
- `character_manager.py` — Manages per-character weighting presets.
- `tab_manager.py` — Manages dynamic tabs and applies OCR results.
- `ui_components.py`, `event_handlers.py` — UI construction and event wiring.
- `image_processor.py`, `worker_thread.py` — Image preprocessing and OCR workers.
- `score_calculator.py` — Score calculation and history insertion (uses `fingerprint` for deduplication).
- `history_manager.py` — Stores, filters, and searches history entries (modes: `all`, `latest`, `oldest`).

See `PROCESS_FLOW.md` for a complete description.

## Process Flow / 処理フロー（概要）
- Startup: `ScoreCalculatorApp` initializes managers and loads `config.json`.
- OCR: `ImageProcessor` performs percent-based cropping and `WorkerThread` runs Tesseract OCR; results are applied to tabs via `TabManager`.
- Calculation & History: `ScoreCalculator` computes scores and `HistoryManager` stores them with MD5 `fingerprint` based duplicate handling.

## Setup (Detailed) / セットアップ（詳細）
Prerequisites / 前提条件:
- Python 3.8+ (3.8+ recommended)
- On Windows, Visual C++ Redistributable may be required for some binary deps (PySide6, numpy, opencv).

Steps:
1. Create and activate a virtual environment (PowerShell example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Install Tesseract (for OCR):
- Download a Windows installer (e.g. UB-Mannheim builds) and install, recommended path `C:\Program Files\Tesseract-OCR`.
- During install, add Japanese (`jpn`) language data if you need Japanese OCR.
- Make sure `tesseract.exe` is on `PATH` or set `pytesseract.pytesseract.tesseract_cmd` in code.

Example (in code) to explicitly set tesseract path:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Optional: set `TESSDATA_PREFIX` environment variable to point to tessdata directory when bundling tessdata.

## Run / 実行方法
Run from source:

```powershell
python wuwacalc17.py
```

Run bundled exe (after PyInstaller build):

```powershell
.\dist\wuwacalc17.exe
```

Logs: the app writes runtime logs to console and `wuwacalc.log` in the working directory; build warnings are in `build/*/warn-*.txt`.

## Distribution with PyInstaller / PyInstaller での配布（任意）
Basic build (single-file):

```powershell
pip install --upgrade pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --onefile --noconfirm --clean wuwacalc17.py
```

Including data directories (example):

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --onefile --noconfirm --clean \
  --add-data "data;data" \
  --add-data "character_settings_jsons;character_settings_jsons" \
  --add-data "tesseract;tesseract" \
  wuwacalc17.py
```

Notes on `--add-data` and Windows paths:
- In the `--add-data` argument, separate source and destination with a semicolon (`;`) on Windows, and with a colon (`:`) on POSIX systems. Example above is for Windows.
- PyInstaller extracts bundled data to a temporary directory at runtime; use `sys._MEIPASS` (or `getattr(sys, 'frozen', False)`) to access files when frozen — see next section.

## Packaging Notes / 配布時の注意点とサンプルコード
When your application is bundled by PyInstaller, file layout changes. Use the following pattern to access bundled data reliably:

```python
import sys
import os

def resource_path(relative_path: str) -> str:
    """Return absolute path to resource, working for dev and for PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # When bundled by PyInstaller, files are extracted to _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

# Example: open bundled game_data.json
game_data_file = resource_path(os.path.join('data', 'game_data.json'))

```

When bundling Tesseract data (`tesseract/tessdata`), you may need to set `TESSDATA_PREFIX` to point to the extracted tessdata directory at runtime. Example:

```python
import os
os.environ['TESSDATA_PREFIX'] = resource_path('tesseract/tessdata')
```

## Distribution Checklist / 配布チェックリスト
- Include `data/` (game_data.json, calculation_config.json).
- Include `character_settings_jsons/` if you rely on bundled profiles.
- If you bundle tessdata, ensure `TESSDATA_PREFIX` is set to the extracted location.
- Verify Visual C++ Redistributable presence on target systems.
- Test exe on a clean Windows VM to catch missing runtime DLLs.

## Troubleshooting / トラブルシューティング
- Error "Game data file not found" on startup: rebuild with `--add-data "data;data"` or ensure `data/game_data.json` is placed next to the executable.
- OCR not working: ensure `tesseract.exe` is installed and reachable; check `pytesseract.pytesseract.tesseract_cmd` and `TESSDATA_PREFIX`.
- Check `build/*/warn-*.txt` for PyInstaller warnings about missing hooks or modules.
- Runtime logs: see `wuwacalc.log` in the current working directory and console output.

## Contributing / 貢献
- Bug reports and feature requests: open an Issue.
- Pull requests: target the `main` branch, include tests where appropriate.

## License & Disclaimer / ライセンスと免責
This is a fan-made, unofficial tool. `Wuthering Waves` and related rights belong to KURO GAMES.

If there are copyright concerns, contact the repository maintainers via Issues.

---
Source: `PROCESS_FLOW.md`

## Third-party licenses / 同梱ライセンス
See `THIRD_PARTY_LICENSES.md` for license texts and distribution notes for bundled third-party components (Tesseract, tessdata, DLLs等)。
