"""
Image Processing and OCR Module (PyQt6)

Provides image loading, cropping, OCR processing, and automatic input.
"""

import re
import os
import hashlib
from typing import Optional, Any, List, Set, Tuple, Dict

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QObject, pyqtSignal

try:
    from PIL import Image, ImageQt, ImageGrab
    is_pil_installed = True
except ImportError:
    is_pil_installed = False

from dialogs import CropDialog
from utils import crop_image_by_percent
from data_contracts import SubStat, BatchItemResult, CropConfig
from ui_constants import IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT
from worker_thread import OCRWorker

class ImageProcessor(QObject):
    """Class responsible for image processing and OCR."""
    
    ocr_completed = pyqtSignal(object) # OCRResult
    
    def __init__(self, app: 'ScoreCalculatorApp', logic: 'AppLogic') -> None:
        """
        Initialization
        
        Args:
            app: The main application instance.
            logic: The application logic instance.
        """
        super().__init__()
        self.app = app
        self.logic = logic
    
    def import_image(self) -> None:
        """Load one or multiple images for OCR."""
        if not is_pil_installed:
            QMessageBox.critical(self.app, "Error", "Pillow is not installed. Image operations require Pillow.")
            return
        
        # Use getOpenFileNames to allow multiple selection
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.app,
            "Select Image File(s)",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)"
        )
        if not file_paths:
            self.app.gui_log("Image selection was cancelled.")
            return
            
        try:
            if len(file_paths) == 1:
                # Single image - standard behavior
                file_path = file_paths[0]
                if not os.path.isfile(file_path):
                    QMessageBox.critical(self.app, "Error", f"File not found:\n{file_path}")
                    return
                
                image = Image.open(file_path)
                self.process_loaded_image(image, file_path)
            else:
                # Multiple images - batch processing
                self.process_batch_images(file_paths)
            
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Failed to load image(s):\n{e}")
            self.app.logger.exception(f"Image load error: {e}")
            self.app.gui_log(f"Image load error: {e}")

    def process_batch_images(self, file_paths: List[str]) -> None:
        """
        Process multiple images sequentially in a background thread.
        """
        self.app.gui_log(f"Starting batch processing of {len(file_paths)} images...")
        
        # Capture current crop settings
        # Use percent mode if auto_calculate is enabled
        crop_mode = self.app.crop_mode_var
        if self.app.app_config.auto_calculate:
            crop_mode = "percent"

        crop_config = CropConfig(
            mode=crop_mode,
            left_p=self.app.crop_left_percent_var,
            top_p=self.app.crop_top_percent_var,
            width_p=self.app.crop_width_percent_var,
            height_p=self.app.crop_height_percent_var
        )
        
        # Initialize tracking for batch
        self._batch_assigned_tabs = set()
        self._batch_successful_count = 0
        
        # Create and start worker
        self.worker = OCRWorker(self.logic, file_paths, crop_config, self.app.language)
        self.worker.signals.result.connect(self._on_worker_result)
        self.worker.signals.finished.connect(self._on_worker_finished)
        self.worker.signals.error.connect(self._on_worker_error)
        self.worker.signals.progress.connect(self._on_worker_progress)
        self.worker.signals.log.connect(self.app.gui_log)
        
        self.worker.start()

    def _on_worker_progress(self, current: int, total: int) -> None:
        """Handle progress updates from worker."""
        self.app.gui_log(f"Progress: {current}/{total}")

    def _on_worker_error(self, err: tuple) -> None:
        """Handle errors from worker."""
        exctype, value, traceback_str = err
        self.app.gui_log(f"Worker Error: {value}")
        self.app.logger.error(f"Worker Error: {traceback_str}")

    def _on_worker_result(self, data: BatchItemResult) -> None:
        """
        Handle a single OCR result from the worker.
        Running in Main Thread.
        """
        try:
            file_path = data.file_path
            result = data.result
            image = data.original_image
            cropped_img = data.cropped_image
            filename = os.path.basename(file_path)
            
            target_tab = None
            if result.cost:
                self.app.gui_log(f"[{filename}] Detected Cost: {result.cost}")
                target_tab = self._find_free_tab_for_cost(result.cost, self._batch_assigned_tabs)
            else:
                self.app.gui_log(f"[{filename}] Cost not detected. Attempting to assign to first available empty slot.")
                target_tab = self._find_any_free_tab(self._batch_assigned_tabs)
            
            if target_tab:
                self.app.gui_log(f"[{filename}] Assigning to tab: {target_tab}")
                self._batch_assigned_tabs.add(target_tab)
                
                # Populate Tab (UI Update)
                self._populate_tab_data(target_tab, result.substats, result.main_stat)
                
                # Save Image to Tab
                self.app.tab_mgr.save_tab_image(target_tab, image.copy(), cropped_img.copy())
                
                # Update active image state if we are verifying this tab
                current_tab = self.app.tab_mgr.get_selected_tab_name()
                if current_tab and current_tab == target_tab:
                    self.app.original_image = image.copy()
                    self.app.loaded_image = cropped_img.copy()
                    self.display_image_preview(self.app.loaded_image)
                
                self._batch_successful_count += 1
            else:
                 self.app.gui_log(f"[{filename}] No suitable free tab found (Cost: {result.cost if result.cost else 'Unknown'}). Skipping.")
                 
        except Exception as e:
            self.app.gui_log(f"Error applying batch result for {getattr(data, 'file_path', 'unknown')}: {e}")
            self.app.logger.exception(f"Error applying batch result: {e}")

    def _on_worker_finished(self) -> None:
        """Handle worker completion."""
        self.app.gui_log(f"Batch processing completed. {self._batch_successful_count} images processed successfully.")
        
        # Trigger auto calculation if enabled and character is selected
        if self.app.app_config.auto_calculate and self.app.character_var:
            self.app.score_calc.calculate_all_scores()
            
        # self.app.set_ui_enabled(True) # Re-enable UI

    def _is_tab_empty(self, tab_key: str) -> bool:
        """Checks if a given tab is considered empty."""
        if tab_key not in self.app.tab_mgr.tabs_content:
            return True # If content doesn't exist, it's conceptually empty
            
        content = self.app.tab_mgr.tabs_content[tab_key]
        
        # Check main stat combo box
        main_combo = content.get("main_widget")
        if main_combo and main_combo.currentIndex() != 0:
            return False # Main stat selected
            
        # Check substat entries
        sub_entries = content.get("sub_entries")
        if sub_entries:
            for stat_widget, val_widget in sub_entries:
                if stat_widget.currentIndex() != 0 or val_widget.text().strip() != "":
                    return False # Substat selected or has value
        
        return True

    def _find_free_tab_for_cost(self, cost: str, exclude_tabs: Set[str]) -> Optional[str]:
        """Finds the first tab matching the cost that isn't excluded and is empty."""
        if self.app.notebook is None:
            return None
            
        config_key = self.app.current_config_key
        # from constants import TAB_CONFIGS # Removed
        tab_configs = self.app.data_manager.tab_configs
        if config_key not in tab_configs:
             return None
             
        tab_keys = tab_configs[config_key]
        
        for key in tab_keys:
            if key in exclude_tabs:
                continue
            
            # Extract cost from key (e.g., "cost4_echo" -> "4")
            key_cost_match = re.search(r'cost(\d+)_echo', key)
            if not key_cost_match:
                continue # Malformed key, skip
            
            extracted_key_cost = key_cost_match.group(1)
            
            if extracted_key_cost != cost:
                continue # Cost doesn't match
            
            if self._is_tab_empty(key):
                return key # Found an empty tab for this cost
            
        return None

    def _find_any_free_tab(self, exclude_tabs: Set[str]) -> Optional[str]:
        """Fallback: find any tab not yet assigned that is empty."""
        config_key = self.app.current_config_key
        # from constants import TAB_CONFIGS # Removed
        tab_configs = self.app.data_manager.tab_configs
        if config_key not in tab_configs:
             return None
        
        for key in tab_configs[config_key]:
            if key not in exclude_tabs:
                if self._is_tab_empty(key):
                    return key
        return None

    def _populate_tab_data(self, tab_name: str, substats: List[SubStat], main_stat: Optional[str] = None) -> None:
        """Directly updates the widgets for the given tab."""
        if tab_name not in self.app.tab_mgr.tabs_content:
            return
            
        content = self.app.tab_mgr.tabs_content[tab_name]
        sub_entries = content["sub_entries"]
        main_combo = content.get("main_widget")
        
        # Update Main Stat if detected
        if main_stat and main_combo:
            translated_main = self.app.tr(main_stat)
            idx = main_combo.findText(translated_main)
            if idx >= 0:
                main_combo.setCurrentIndex(idx)
                self.app.gui_log(f"Auto-selected main stat for {tab_name}: {translated_main}")
        
        # Clear existing substats in the widget first
        for stat_widget, val_widget in sub_entries:
            stat_widget.setCurrentIndex(0) # Blank
            val_widget.clear()
            
        for i, substat_data in enumerate(substats):
            if i < len(sub_entries):
                stat_found = substat_data.stat
                num_found = substat_data.value
                
                translated_stat = self.app.tr(stat_found)
                sub_entries[i][0].setCurrentText(translated_stat)
                sub_entries[i][1].setText(num_found)

    
    def paste_from_clipboard(self) -> None:
        """Load image from the clipboard."""
        if not is_pil_installed:
            QMessageBox.critical(self.app, "Error", "Pillow is not installed. Image operations require Pillow.")
            return
        
        try:
            # Try getting image from Qt clipboard first
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasImage():
                qimage = clipboard.image()
                # Convert QImage to PIL Image
                # This is a bit roundabout but keeps consistency with PIL usage elsewhere
                # Alternatively, use ImageGrab.grabclipboard()
                image = ImageGrab.grabclipboard()
                if isinstance(image, Image.Image):
                    self.process_loaded_image(image, "clipboard image")
                else:
                    # Fallback if ImageGrab fails but Qt has image
                    # Convert QImage to PIL
                    buffer = qimage.bits().asstring(qimage.sizeInBytes())
                    # This conversion is complex, let's stick to ImageGrab for now as it was working
                    self.app.gui_log("No compatible image found on clipboard via PIL.")
            else:
                self.app.gui_log("No image found on the clipboard.")
        except Exception as e:
            self.app.logger.exception(f"Error loading image from clipboard: {e}")
            self.app.gui_log(f"Error loading image from clipboard: {e}")
    
    def process_loaded_image(self, image: 'Image.Image', source_name: str) -> None:
        """Common image loading process."""
        tab_name = self.app.tab_mgr.get_selected_tab_name()
        if not tab_name:
            QMessageBox.warning(self.app, "Warning", "Please select a tab to associate the image with.")
            return

        self.app.original_image = image.copy()
        
        # If auto calculate is enabled, apply percent crop automatically
        if self.app.app_config.auto_calculate:
            try:
                left_p = self.app.crop_left_percent_var
                top_p = self.app.crop_top_percent_var
                width_p = self.app.crop_width_percent_var
                height_p = self.app.crop_height_percent_var
                
                cropped = crop_image_by_percent(self.app.original_image, left_p, top_p, width_p, height_p)
                self.app.gui_log(f"Auto-applied percent crop: L={left_p}%, T={top_p}%, W={width_p}%, H={height_p}%")
                self.apply_cropped_image(cropped)
            except Exception as e:
                self.app.logger.error(f"Auto-crop error: {e}")
                self.apply_cropped_image(image) # Fallback to original
        else:
            # Use the entire image by default without cropping
            self.apply_cropped_image(image)
            
        self.app.gui_log(f"Image loaded: {source_name}")
    
    def perform_crop(self) -> None:
        """Perform cropping based on the current mode."""
        if self.app.original_image is None:
            QMessageBox.warning(self.app, "Warning", "No image loaded.")
            return

        # If auto calculate is enabled, prioritize percent crop to avoid dialog interruption
        mode = self.app.crop_mode_var
        if mode == "percent" or self.app.app_config.auto_calculate:
            self.apply_percent_crop()
        else:
            self.open_crop_dialog()
    
    def apply_percent_crop(self) -> None:
        """Perform cropping by percentage."""
        try:
            left_p = self.app.crop_left_percent_var
            top_p = self.app.crop_top_percent_var
            width_p = self.app.crop_width_percent_var
            height_p = self.app.crop_height_percent_var
            
            cropped = crop_image_by_percent(self.app.original_image, left_p, top_p, width_p, height_p)
            
            self.app.gui_log(f"Applied percent crop: L={left_p}%, T={top_p}%, W={width_p}%, H={height_p}%")
            self.apply_cropped_image(cropped)
            
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Error applying percent crop: {e}")
            self.app.logger.exception(f"Percent crop error: {e}")
            self.app.gui_log(f"Percent crop error: {e}")
    
    def open_crop_dialog(self) -> None:
        """Open a crop dialog for the current original image."""
        if self.app.original_image is None:
            QMessageBox.warning(self.app, "Warning", "No image loaded.")
            return
            
        try:
            crop_dialog = CropDialog(self.app, self.app.original_image)
            if crop_dialog.exec():
                if crop_dialog.crop_result:
                    if crop_dialog.crop_result[0] == 'coords':
                        _, left, top, right, bottom = crop_dialog.crop_result
                        try:
                            cropped_img = self.app.original_image.crop((left, top, right, bottom))
                            self.app.gui_log(f"Cropped with coordinates: ({left},{top}) - ({right},{bottom})")
                            self.apply_cropped_image(cropped_img)
                        except Exception as ve:
                            QMessageBox.critical(self.app, "Error", f"Failed to crop with coordinates:\n{ve}")
                            self.app.logger.exception(f"Coordinate crop error: {ve}")
                            self.app.gui_log(f"Coordinate crop error: {ve}")
                    elif crop_dialog.crop_result[0] == 'percent':
                        _, left_p, top_p, width_p, height_p = crop_dialog.crop_result
                        try:
                            cropped = crop_image_by_percent(self.app.original_image, left_p, top_p, width_p, height_p)
                            self.app.gui_log(f"Cropped by percent: L={left_p}%, T={top_p}%, W={width_p}%, H={height_p}%")
                            self.apply_cropped_image(cropped)
                        except Exception as perr:
                            QMessageBox.critical(self.app, "Error", f"Failed to crop by percent:\n{perr}")
                            self.app.logger.exception(f"Percent crop error: {perr}")
                            self.app.gui_log(f"Percent crop error: {perr}")
            else:
                self.app.gui_log("Crop cancelled.")
        except Exception as e:
            self.app.logger.exception(f"Crop dialog error: {e}")
            self.app.gui_log(f"Crop dialog error: {e}")
    
    def apply_cropped_image(self, cropped_img: 'Image.Image') -> None:
        """Save, display, and run OCR on the cropped image."""
        current_selected_tab_name = self.app.tab_mgr.get_selected_tab_name()
        if not current_selected_tab_name:
            # This should ideally not happen if a tab is always selected, but for safety
            QMessageBox.warning(self.app, "Warning", "No tab is currently selected. Cannot process image.")
            return

        stored_original = self.app.original_image.copy()
        stored_cropped = cropped_img.copy()
        self.app.loaded_image = stored_cropped.copy()
        
        self.display_image_preview(self.app.loaded_image)
        
        # Run OCR Workflow
        result = self.logic.perform_ocr_workflow(cropped_img, self.app.language)
        
        target_tab_name = current_selected_tab_name # Default to current tab
        
        if result.substats or result.cost:
            if result.cost:
                self.app.gui_log(f"Detected Cost: {result.cost}")
                # Try to find a free tab for this specific cost
                found_tab_for_cost = self._find_free_tab_for_cost(result.cost, set())
                
                if found_tab_for_cost:
                    target_tab_name = found_tab_for_cost
                    self.app.gui_log(f"Automatically assigning to tab: {target_tab_name} (Cost {result.cost})")
                    
                    # Populate data and switch tab
                    self._populate_tab_data(target_tab_name, result.substats, result.main_stat)
                    
                    # Find the index of the target_tab_name in the notebook
                    tab_index_to_activate = -1
                    # from constants import TAB_CONFIGS # Removed
                    config_key = self.app.current_config_key
                    tab_configs = self.app.data_manager.tab_configs
                    if config_key in tab_configs:
                        tab_keys_in_order = tab_configs[config_key]
                        try:
                            tab_index_to_activate = tab_keys_in_order.index(target_tab_name)
                        except ValueError:
                            self.app.gui_log(f"Warning: Target tab '{target_tab_name}' not found in current TAB_CONFIGS order.")
                            
                    if tab_index_to_activate != -1:
                        self.app.notebook.setCurrentIndex(tab_index_to_activate)
                    else:
                        self.app.gui_log(f"Could not switch to tab '{target_tab_name}'. Staying on current tab.")
                else:
                    self.app.gui_log(f"No empty tab found for Cost {result.cost}. Populating current tab: {current_selected_tab_name}.")
                    self._populate_tab_data(current_selected_tab_name, result.substats, result.main_stat) # Populate current tab
            else:
                self.app.gui_log(f"No cost detected. Populating current tab: {current_selected_tab_name}.")
                self._populate_tab_data(current_selected_tab_name, result.substats, result.main_stat) # Populate current tab
            
            # Save image to the (potentially new) target tab
            self.app.tab_mgr.save_tab_image(target_tab_name, stored_original, stored_cropped)
            
            # Emit signal for the tab that was actually populated
            self.ocr_completed.emit(result)
        else:
            self.app.gui_log("OCR failed: No text detected.")
            # If OCR fails, still save the image to the current tab for reference
            self.app.tab_mgr.save_tab_image(current_selected_tab_name, stored_original, stored_cropped)
            # Trigger auto calculation if enabled and character is selected
        if self.app.app_config.auto_calculate and self.app.character_var:
            self.app.score_calc.calculate_all_scores()
    
    def display_image_preview(self, image: Optional['Image.Image']) -> None:
        """Update the image preview label."""
        if not is_pil_installed or self.app.image_label is None or image is None:
            return
        
        try:
            image_hash_data = (image.mode, image.size, hashlib.md5(image.tobytes()).hexdigest())
            
            if image_hash_data == self.app._last_displayed_image_hash and self.app._last_image_preview is not None:
                self.app.image_label.setPixmap(self.app._last_image_preview)
                self.app.image_label.setText("")
                return
            
            # Convert PIL to QPixmap
            # ImageQt.ImageQt(image) returns a QImage-compatible object
            qim = ImageQt.ImageQt(image)
            pixmap = QPixmap.fromImage(qim)
            
            # Scale for preview
            scaled_pixmap = pixmap.scaled(
                IMAGE_PREVIEW_MAX_WIDTH, 
                IMAGE_PREVIEW_MAX_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.app._image_preview = scaled_pixmap
            self.app._last_displayed_image_hash = image_hash_data
            self.app._last_image_preview = scaled_pixmap
            
            self.app.image_label.setPixmap(scaled_pixmap)
            self.app.image_label.setText("")
        except Exception as e:
            self.app.logger.exception(f"Image preview update error: {e}")
            self.app.gui_log(f"Image preview update error: {e}")
    
    def perform_crop_preview(self) -> None:
        """Preview the image with the current crop settings."""
        if self.app.original_image is None or self.app.image_label is None:
            return
        try:
            left_p = self.app.crop_left_percent_var
            top_p = self.app.crop_top_percent_var
            width_p = self.app.crop_width_percent_var
            height_p = self.app.crop_height_percent_var
            
            cropped = crop_image_by_percent(self.app.original_image, left_p, top_p, width_p, height_p)
            
            self.display_image_preview(cropped)
        except Exception as e:
            self.app.logger.debug(f"Crop preview error: {e}")
    
    def perform_image_preview_update_on_resize(self) -> None:
        """Update the image preview on resize."""
        if self.app.loaded_image is not None:
            self.display_image_preview(self.app.loaded_image)


