"""
Application Logic Module (PySide6)

Provides core application logic including OCR, data loading/saving, and character profile management.
"""

import os
import logging
import re
import shutil
import time
from typing import Optional, Any, Dict, List, Tuple, Callable, Union
from core.data_contracts import SubStat, OCRResult
from pytesseract import Output

from PySide6.QtCore import Qt, QObject, Signal
from utils.constants import OCR_ENGINE_OPENCV

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

from utils.constants import (
    DEFAULT_COST_CONFIG,
    KEY_CHARACTER, KEY_CHARACTER_JP, KEY_CONFIG, KEY_AUTO_APPLY, 
    KEY_SCORE_MODE, KEY_ECHOES, KEY_MAIN_STAT, KEY_SUBSTATS, 
    KEY_STAT, KEY_VALUE, KEY_CHARACTER_WEIGHTS, KEY_CHARACTER_MAINSTATS,
)
from utils.utils import get_app_path

class AppLogic(QObject):
    log_message = Signal(str)
    ocr_error = Signal(str, str)
    info_message = Signal(str, str)
    


    def __init__(self, tr_func: Callable, data_manager: Any, config_manager: Any) -> None:
        super().__init__()
        self.tr = tr_func
        self.data_manager = data_manager
        self.config_manager = config_manager

    def _perform_ocr(self, image: 'Image.Image', language: str = "ja") -> Optional[str]:
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
            
            # Use both jpn and eng to support Japanese screenshots regardless of UI language
            tess_lang = "jpn+eng"

            # Tesseractの出力を生バイト列として取得
            output_bytes = pytesseract.image_to_string(processed, lang=tess_lang, config=custom_config, output_type=Output.BYTES)
            
            # 生バイト列をUTF-8でデコード。デコードエラーは無視する。
            ocr_text = output_bytes.decode('utf-8', errors='ignore') 
            
            # クリーンアップ: 記号や不要な空白を除去してマッピング精度を上げる
            ocr_text = re.sub(r'[|｜・°º«»〝〟"\'‘] ', '', ocr_text)
            
            end_time = time.time()
            self.log_message.emit(f"OCR process took {end_time - start_time:.2f} seconds. Language: {tess_lang}")
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

    def _parse_ocr_text(self, ocr_text: str) -> OCRResult:
        """
        Parses raw OCR text into a structured OCRResult.
        """
        app_config = self.config_manager.get_app_config()
        language = app_config.language
        
        substats, log_messages = self.parse_substats_from_ocr(ocr_text, language)
        cost = self.detect_cost_from_ocr(ocr_text)
        main_stat = self.detect_main_stat_from_ocr(ocr_text, cost)

        if main_stat:
            log_messages.append(f"OCR auto-fill: Main Stat -> {self.tr(main_stat)}")

        return OCRResult(substats=substats, log_messages=log_messages, cost=cost, main_stat=main_stat, raw_text=ocr_text)

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
        raw_text = self._perform_ocr(image, language)
        if not raw_text:
            return OCRResult(substats=[], log_messages=[self.tr("ocr_failed_no_text")], cost=None, main_stat=None, raw_text="")

        substats, log_messages = self.parse_substats_from_ocr(raw_text, language)
        cost = self.detect_cost_from_ocr(raw_text)
        main_stat = self.detect_main_stat_from_ocr(raw_text, cost)

        if main_stat:
            log_messages.append(f"OCR auto-fill: Main Stat -> {self.tr(main_stat)}")

        return OCRResult(substats=substats, log_messages=log_messages, cost=cost, main_stat=main_stat, raw_text=raw_text)

    def detect_main_stat_from_ocr(self, ocr_text: str, cost: Optional[str]) -> Optional[str]:
        """
        Detects the main stat from the OCR text.
        """
        if not ocr_text:
            return None

        # Determine which main stats are possible based on cost
        possible_stats = []
        if cost and cost in self.data_manager.main_stat_options:
            possible_stats = self.data_manager.main_stat_options[cost]
        else:
            # Flatten all possible main stats from all costs
            for stats in self.data_manager.main_stat_options.values():
                possible_stats.extend(stats)
            possible_stats = list(set(possible_stats)) # Unique values

        # Prepare aliases for matching
        stat_aliases = self.data_manager.stat_aliases
        
        # Pre-clean the text for matching
        cleaned_lines = []
        for line in ocr_text.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            # Remove symbols and normalize spaces
            line_clean = re.sub(r'^\s*[\・\.\:\*]\s*', '', line_clean)
            line_clean = re.sub(r'\s+', ' ', line_clean)
            line_clean = re.sub(r'(\d)\s*%', r'\1%', line_clean)
            cleaned_lines.append(line_clean)

        # Scan the first half of the OCR text (where the main stat usually resides)
        search_limit = min(len(cleaned_lines), 10)
        search_lines = cleaned_lines[:search_limit]

        self.log_message.emit(f"Searching for main stat in first {search_limit} lines using {len(possible_stats)} candidates.")

        for line in search_lines:
            for stat in possible_stats:
                # 1. Direct match (Full name)
                if stat in line:
                    self.log_message.emit(f"Main stat detected via direct match: {stat}")
                    return stat
                
                # 2. Alias match
                aliases = stat_aliases.get(stat, [])
                for alias in aliases:
                    if alias in line:
                        self.log_message.emit(f"Main stat detected via alias match: {stat} (alias: {alias})")
                        return stat
                
                # 3. Flexible match (Stat name without trailing %)
                # Useful for Cost 1 stats like "攻撃力%" appearing as "攻撃力 18.0%"
                if stat.endswith('%'):
                    base_name = stat.rstrip('%')
                    if base_name in line:
                        self.log_message.emit(f"Main stat detected via flexible match: {stat} (matched: {base_name})")
                        return stat

        return None

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
        self.log_message.emit(f"Parsed Lines after cleaning: {lines}")

        last_five = lines[-5:] if len(lines) >= 5 else lines
        self.log_message.emit(f"Last five lines for parsing: {last_five}")
        
        alias_pairs = self.data_manager.get_alias_pairs()
        
        found_substats = []
        log_messages = []

        for i, line in enumerate(last_five):
            result = self._parse_single_line(line, alias_pairs)
            
            if result:
                substat, is_percent = result
                found_substats.append(substat)
                
                stat_name_for_log = self.tr(substat.stat)
                
                log_messages.append(f"OCR auto-fill: Sub{i+1} -> {stat_name_for_log} {substat.value}{'%' if is_percent else ''}")
        
        self.log_message.emit(f"Found substats: {found_substats}")
        self.log_message.emit(f"Generated log messages: {log_messages}")
        
        return found_substats, log_messages

    def _parse_single_line(self, line: str, alias_pairs: List[Tuple[str, str]]) -> Optional[Tuple[SubStat, bool]]:
        """
        Parses a single line of text to extract a SubStat.
        Returns: (SubStat, is_percent) or None if no match found.
        """
        stat_found = ""
        num_found = ""
        is_percent = False
        
        # 1. Try pattern: "Stat Name 12.3%"
        match = re.search(r'(.+?)\s+([\d\.]+(?:\s*[%％])?)', line)
        
        if match:
            stat_text_from_line = match.group(1).strip()
            num_text_from_line = match.group(2).strip()
            
            for stat, alias in alias_pairs:
                if stat_text_from_line == stat or stat_text_from_line == alias: 
                    stat_found = stat
                    nums = re.findall(r"[\d\.]+", num_text_from_line.replace('％', '%'))
                    if nums:
                        num_found = nums[0]
                        if "%" in num_text_from_line or "％" in num_text_from_line:
                            is_percent = True
                    break
        
        # 2. Fallback: Full line search
        if not stat_found:
            for stat, alias in alias_pairs:
                if alias in line:
                    stat_found = stat
                    nums = re.findall(r"[\d\.]+", line.replace('％', '%'))
                    if nums:
                        num_found = nums[0]
                        if "%" in line or "％" in line:
                            is_percent = True
                    break
        
        if stat_found and num_found:
            # --- Auto-correction and Validation ---
            corrected_stat, corrected_val, was_percent = self.validate_and_correct_substat(stat_found, num_found, is_percent)
            return SubStat(stat=corrected_stat, value=corrected_val), was_percent
            
        return None

    def validate_and_correct_substat(self, stat_name: str, raw_value: str, is_percent: bool) -> Tuple[str, str, bool]:
        """
        Validates the OCR value against game data and corrects common errors.
        """
        try:
            val = float(raw_value)
        except ValueError:
            return stat_name, raw_value, is_percent

        # Get max value for this stat from game data
        # Note: stat_name might not have '%' yet
        search_name = stat_name if stat_name in self.data_manager.substat_max_values else f"{stat_name}%"
        max_val = self.data_manager.substat_max_values.get(search_name)
        
        if not max_val:
            return stat_name, raw_value, is_percent

        # Logic for Stats that have both Flat and Percent (ATK, HP, DEF)
        if stat_name in ["攻撃力", "HP", "防御力"]:
            # If value is small (e.g. 6.4 - 14.7) but detected as Flat, it's likely Percent
            if not is_percent and val < 20.0:
                is_percent = True
                stat_name = f"{stat_name}%"
            # If value is large (e.g. 30 - 580) but detected as Percent, it's likely Flat
            elif is_percent and val > 20.0:
                is_percent = False
                stat_name = stat_name.replace("%", "")
        
        # Correction for missing decimal points (Common OCR error: 10.5 -> 105)
        # If value > max_val * 1.5, it's highly likely a missing decimal
        if val > max_val * 1.5:
            # Try inserting a decimal point before the last digit
            # e.g., 105 -> 10.5, 74 -> 7.4
            new_val = val / 10.0
            if new_val <= max_val * 1.1:
                self.log_message.emit(f"Correcting {stat_name}: {val} -> {new_val} (assuming missing decimal point)")
                val = new_val
        
        # Final clamping/rounding to 1 decimal place for UI consistency
        formatted_val = f"{val:.1f}" if is_percent or "." in raw_value else str(int(val))
        
        return stat_name, formatted_val, is_percent

    def detect_cost_from_ocr(self, ocr_text: str) -> Optional[str]:
        """
        Detects the cost (4, 3, 1) from the first few lines of the OCR text.
        """
        if not ocr_text:
            return None
        
        # Get all non-empty lines
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        
        if not lines:
            return None

        # Check first 3 lines
        check_count = min(len(lines), 3)
        self.log_message.emit(f"Searching for cost in first {check_count} lines.")
        
        # 1. Search for explicit "Cost" text
        cost_pattern = re.compile(r'(?:COST|Cost|cost|コスト)[\s:.]*([134])')
        
        for i in range(check_count):
            line = lines[i]
            match = cost_pattern.search(line)
            if match:
                cost_found = match.group(1)
                self.log_message.emit(f"Cost '{cost_found}' detected on line {i+1}: '{line}'")
                return cost_found
            
        self.log_message.emit("No cost detected in the first few lines.")
        return None

