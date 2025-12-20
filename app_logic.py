"""
Application Logic Module (PyQt6)

Provides core application logic including OCR, data loading/saving, and character profile management.
"""

import os
import logging
import json
import re
import shutil
import time
from typing import Optional, Any, Dict, List, Tuple, Callable, Union
from data_contracts import SubStat, OCRResult
from pytesseract import Output

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from constants import OCR_ENGINE_OPENCV

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageQt
    is_pil_installed = True
except ImportError:
    is_pil_installed = False

try:
    import pytesseract
    is_pytesseract_installed = True
except ImportError:
    is_pytesseract_installed = False
try:
    import numpy as np
    import cv2
    is_opencv_installed = True
except ImportError:
    is_opencv_installed = False

from constants import (
    DEFAULT_COST_CONFIG,
    KEY_CHARACTER, KEY_CHARACTER_JP, KEY_CONFIG, KEY_AUTO_APPLY, 
    KEY_SCORE_MODE, KEY_ECHOES, KEY_MAIN_STAT, KEY_SUBSTATS, 
    KEY_STAT, KEY_VALUE, KEY_CHARACTER_WEIGHTS, KEY_CHARACTER_MAINSTATS,
)
from utils import get_app_path

class AppLogic(QObject):
    log_message = pyqtSignal(str)
    ocr_error = pyqtSignal(str, str)
    info_message = pyqtSignal(str, str)
    


    def __init__(self, tr_func: Callable, data_manager: Any, config_manager: Any) -> None:
        super().__init__()
        self.tr = tr_func
        self.data_manager = data_manager
        self.config_manager = config_manager

    def _perform_ocr(self, image: 'Image.Image') -> Optional[str]:
        start_time = time.time()
        if not is_pytesseract_installed:
            self.log_message.emit(self.tr("pytesseract_not_installed"))
            return None

        # Try to use the path set in pytesseract or find it via shutil if not set
        if not getattr(pytesseract.pytesseract, "tesseract_cmd", None) or \
           not os.path.isfile(str(pytesseract.pytesseract.tesseract_cmd)):
            found = shutil.which("tesseract")
            if found:
                pytesseract.pytesseract.tesseract_cmd = found
                self.log_message.emit(self.tr("tesseract_found_path", found))
            else:
                self.log_message.emit(self.tr("tesseract_not_found_sys"))
                return None

        try:
            processed = self._preprocess_for_ocr(image)
            self.log_message.emit(f"Image for Tesseract OCR - size: {processed.size}, mode: {processed.mode}")
            custom_config = "--oem 3 --psm 6" # に戻す
            
            # Tesseractの出力を生バイト列として取得
            output_bytes = pytesseract.image_to_string(processed, lang="jpn", config=custom_config, output_type=Output.BYTES)
            
            # 生バイト列をUTF-8でデコード。デコードエラーは無視する。
            ocr_text = output_bytes.decode('utf-8', errors='ignore') 
            end_time = time.time()
            self.log_message.emit(f"OCR process took {end_time - start_time:.2f} seconds.")
            self.log_message.emit(f"OCR Raw Text:\n{ocr_text.strip()}") # ここで生テキストを出力
            return ocr_text
        except pytesseract.TesseractError as te:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_lang_data_error", te))
            self.log_message.emit(self.tr("ocr_lang_data_error_log", te))
        except FileNotFoundError as fnf:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("tesseract_exec_not_found", fnf))
            self.log_message.emit(self.tr("tesseract_exec_error_log", fnf))
        except Exception as ocr_error:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_process_error", ocr_error))
            self.log_message.emit(self.tr("ocr_process_error_log", ocr_error))
        return None

    def _preprocess_for_ocr(self, image: 'Image.Image') -> 'Image.Image':
        if not is_pil_installed or image is None:
            return image
        
        # Determine which engine to use
        engine = self.config_manager.get_app_config().ocr_engine
        
        # If OpenCV is selected and available, use it
        if engine == OCR_ENGINE_OPENCV:
            if is_opencv_installed:
                self.log_message.emit("Using OpenCV for advanced image preprocessing.")
                # 1. Grayscale conversion and resizing (using Pillow)
                processed_pil = image.convert("L")
                max_side = max(processed_pil.size)
                if max_side < 1600:
                    scale = 2
                    processed_pil = processed_pil.resize(
                        (processed_pil.width * scale, processed_pil.height * scale),
                        Image.Resampling.LANCZOS
                    )
                
                # 2. Convert Pillow image to OpenCV format (NumPy array)
                open_cv_image = np.array(processed_pil)
                
                # 3. Apply noise reduction (Median Blur)
                open_cv_image = cv2.medianBlur(open_cv_image, 3) # Kernel size 3
                
                # 4. Apply adaptive thresholding
                processed_cv = cv2.adaptiveThreshold(
                    open_cv_image,
                    maxValue=255,
                    adaptiveMethod=cv2.ADAPTIVE_THRESH_MEAN_C,
                    thresholdType=cv2.THRESH_BINARY,
                    blockSize=21,
                    C=4
                )
                
                # 5. Convert back to Pillow image for Tesseract
                final_image = Image.fromarray(processed_cv)
                return final_image
            else:
                 self.log_message.emit("OpenCV engine selected but not installed/available. Fallback to Pillow.")
        
        # --- Default Pillow-based preprocessing ---
        self.log_message.emit("Using standard Pillow image preprocessing.")
        processed = image.convert("L")
        max_side = max(processed.size)
        if max_side < 1600:
            scale = 2
            processed = processed.resize(
                (processed.width * scale, processed.height * scale),
                Image.Resampling.LANCZOS
            )
        processed = ImageOps.autocontrast(processed)
        processed = ImageEnhance.Contrast(processed).enhance(2.0)
        processed = ImageEnhance.Sharpness(processed).enhance(1.5)
        threshold = 150
        processed = processed.point(lambda p: 255 if p > threshold else 0)
        return processed

    def perform_ocr_workflow(self, image: 'Image.Image', language: str) -> OCRResult:
        """
        Performs the full OCR workflow: image processing, text recognition,
        and parsing of substats and cost.
        """
        raw_text = self._perform_ocr(image)
        if not raw_text:
            return OCRResult(substats=[], log_messages=[self.tr("ocr_failed_no_text")], cost=None, raw_text="")

        substats, log_messages = self.parse_substats_from_ocr(raw_text, language)
        cost = self.detect_cost_from_ocr(raw_text)

        return OCRResult(substats=substats, log_messages=log_messages, cost=cost, raw_text=raw_text)


    def parse_substats_from_ocr(self, ocr_text: str, language: str) -> tuple[list[SubStat], list[str]]:
        """Parses substats from OCR text and returns data and log messages."""
        if not ocr_text or not ocr_text.strip():
            return [], []

        cleaned_lines = []
        for line in ocr_text.strip().splitlines():
            if not line.strip():
                continue
            
            # 行頭の「・」や不要な空白、ピリオドを除去
            cleaned_line = re.sub(r'^\s*[\・\.]*\s*', '', line.strip())
            
            # ステータス名と数値の間の不規則な空白を正規化
            cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
            
            # 数字とパーセント記号の間のスペースを削除（例：10.8 % -> 10.8%）
            cleaned_line = re.sub(r'(\d)\s*%', r'\1%', cleaned_line)
            
            # 最終的なトリム
            cleaned_line = cleaned_line.strip()
            
            cleaned_lines.append(cleaned_line)
        lines = cleaned_lines
        self.log_message.emit(f"Parsed Lines after cleaning: {lines}") # 追加

        last_five = lines[-5:] if len(lines) >= 5 else lines
        self.log_message.emit(f"Last five lines for parsing: {last_five}") # 追加
        
        alias_pairs = []
        stat_aliases = self.data_manager.stat_aliases
        for stat, aliases in stat_aliases.items():
            for alias in aliases:
                alias_pairs.append((stat, alias))
        
        found_substats = []
        log_messages = []

        for i, line in enumerate(last_five):
            stat_found = ""
            num_found = ""
            is_percent = False
            
            # ステータス名と数値部分を分離するパターンを試す
            # 例: "防御力 13.8%" -> "防御力", "13.8%"
            # ステータス名 + 複数の空白 + 数字 + オプションの % または ％
            match = re.search(r'(.+?)\s+([\d\.]+(?:\s*[%％])?)', line)
            
            if match:
                stat_text_from_line = match.group(1).strip()
                num_text_from_line = match.group(2).strip()
                
                # エイリアスチェック
                # より具体的なエイリアスからチェックするために、alias_pairsをソートすることも検討
                # ただし、現在のalias_pairsは長さでソートされているのでそのまま使用
                for stat, alias in alias_pairs:
                    # stat_text_from_line がエイリアスと直接一致するか、エイリアスが stat_text_from_line に含まれるか
                    if stat_text_from_line == stat or stat_text_from_line == alias: 
                        stat_found = stat
                        # 数値部分から純粋な数字を抽出
                        nums = re.findall(r"[\d\.]+", num_text_from_line.replace('％', '%'))
                        if nums:
                            num_found = nums[0]
                            if "%" in num_text_from_line or "％" in num_text_from_line:
                                is_percent = True
                        break # マッチしたらループを抜ける
            
            # 以前のロジックでパースできなかった場合、stat_aliases全体で再チェックする
            # これは、OCRノイズによって分離パターンが失敗した場合のフォールバック
            if not stat_found:
                for stat, alias in alias_pairs:
                    if alias in line: # 行全体にエイリアスが含まれるか
                        stat_found = stat
                        nums = re.findall(r"[\d\.]+", line.replace('％', '%'))
                        if nums:
                            num_found = nums[0]
                            if "%" in line or "％" in line:
                                is_percent = True
                        break
            
            if stat_found:
                found_substats.append(SubStat(stat=stat_found, value=num_found))
                
                stat_name_for_log = stat_found
                if language == "en":
                    stat_name_for_log = self.data_manager.stat_translation_map.get(stat_found, stat_found)
                
                log_messages.append(f"OCR auto-fill: Sub{i+1} -> {stat_name_for_log} {num_found}{'%' if is_percent else ''}")
        
        self.log_message.emit(f"Found substats: {found_substats}") # 追加
        self.log_message.emit(f"Generated log messages: {log_messages}") # 追加
        
        return found_substats, log_messages

    def detect_cost_from_ocr(self, ocr_text: str) -> Optional[str]:
        """
        Detects the cost (4, 3, 1) from the first line of the OCR text.
        """
        if not ocr_text:
            return None
        
        # Get the first non-empty line
        first_line = ""
        for line in ocr_text.splitlines():
            stripped_line = line.strip()
            if stripped_line:
                first_line = stripped_line
                break
        
        if not first_line:
            return None

        self.log_message.emit(f"Searching for cost in first line: '{first_line}'")
        
        # 1. Search for explicit "Cost" text on the first line only
        cost_pattern = re.compile(r'(?:COST|Cost|cost|コスト)[\s:.]*([134])')
        match = cost_pattern.search(first_line)
        if match:
            cost_found = match.group(1)
            self.log_message.emit(f"Cost '{cost_found}' detected on first line.")
            return cost_found
            
        # Per user request, do not fall back to other lines or class names if not found on first line.
        self.log_message.emit("No cost detected on the first line as per strict requirement.")
        return None

