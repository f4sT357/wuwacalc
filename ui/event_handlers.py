"""
Event Handling Module (PySide6)

Provides event callbacks and debounce processing.
"""

import logging
import time
from typing import Any, Optional

from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QTimer
from utils.constants import (
    TIMER_SAVE_CONFIG_INTERVAL,
    TIMER_CROP_PREVIEW_INTERVAL,
    TIMER_RESIZE_PREVIEW_INTERVAL
)

class EventHandlers:
    """Class responsible for event handling."""
    
    def __init__(self, app: Any, ctx: Any) -> None:
        """
        Initialization
        
        Args:
            app: The main application window instance.
            ctx: The AppContext instance containing all managers.
        """
        self.app = app
        self.ui = ctx.ui
        self.config_manager = ctx.config_manager
        self.data_manager = ctx.data_manager
        self.tab_mgr = ctx.tab_mgr
        self.theme_manager = ctx.theme_manager
        self.character_manager = ctx.character_manager
        self.image_proc = ctx.image_proc
        self.score_calc = ctx.score_calc
        self.logic = ctx.logic
        
        self.logger = logging.getLogger(__name__)
        
        # Timer references for debouncing
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.actual_save_config)
        
        self._crop_preview_timer = QTimer()
        self._crop_preview_timer.setSingleShot(True)
        self._crop_preview_timer.timeout.connect(self.image_proc.perform_crop_preview)
        
        self._resize_preview_timer = QTimer()
        self._resize_preview_timer.setSingleShot(True)
        self._resize_preview_timer.timeout.connect(self.image_proc.perform_image_preview_update_on_resize)

    def setup_connections(self) -> None:
        """Set up all signal connections."""
        # Logic signals
        self.logic.log_message.connect(self.app.gui_log)
        self.logic.ocr_error.connect(self.app.show_ocr_error_message)
        self.logic.info_message.connect(self.app.show_info_message)

        # ScoreCalc signals
        self.score_calc.log_requested.connect(self.app.gui_log)
        self.score_calc.error_occurred.connect(self.app.show_error_message)
        self.score_calc.single_calculation_completed.connect(self.app.on_single_calc_completed)
        self.score_calc.batch_calculation_completed.connect(self.app.on_batch_calc_completed)

        # TabMgr signals
        self.tab_mgr.log_requested.connect(self.app.gui_log)
        self.tab_mgr.tabs_updated.connect(self.app.on_tabs_updated)

        # ImageProc signals
        self.image_proc.ocr_completed.connect(self.on_ocr_completed)
        self.image_proc.log_requested.connect(self.app.gui_log)
        self.image_proc.error_occurred.connect(self.app.show_error_message)
        self.image_proc.image_updated.connect(self.app.update_image_preview)
        self.image_proc.calculation_requested.connect(self.trigger_calculation)

        # UI signals
        self.app.notebook.currentChanged.connect(self.on_tab_changed)
        self.character_manager.profiles_updated.connect(self.on_profiles_updated)
        self.character_manager.character_registered.connect(self.on_character_registered)

        self.ui.config_combo.currentTextChanged.connect(self.on_config_change)
        self.ui.character_combo.currentIndexChanged.connect(self.on_character_change)
        self.ui.lang_combo.currentTextChanged.connect(self.on_language_change)
        self.ui.rb_manual.toggled.connect(lambda c: self.on_mode_change("manual") if c else None)
        self.ui.rb_ocr.toggled.connect(lambda c: self.on_mode_change("ocr") if c else None)
        self.ui.cb_auto_main.toggled.connect(self.on_auto_main_change)
        self.ui.rb_batch.toggled.connect(lambda c: self.on_score_mode_change("batch") if c else None)
        self.ui.rb_single.toggled.connect(lambda c: self.on_score_mode_change("single") if c else None)
        
        for method, cb in self.ui.method_checkboxes.items():
            cb.toggled.connect(self.on_calc_method_changed)

    def trigger_calculation(self) -> None:
        """Triggers the calculation logic."""
        try:
            if not self.app.character_var:
                self.app._waiting_for_character = True
                self.ui.result_text.setHtml(f"<h3 style='color: orange;'>{self.app.tr('waiting_for_character')}</h3>")
                return
            
            self.app._waiting_for_character = False
            self.app.show_duplicate_entries()
            
            enabled_methods = self.app.app_config.enabled_calc_methods
            if self.app.score_mode_var == "single":
                tab_name = self.tab_mgr.get_selected_tab_name()
                entry = self.tab_mgr.extract_tab_data(tab_name)
                if entry:
                    self.score_calc.calculate_single(self.app.character_var, tab_name, entry, enabled_methods)
            else:
                tabs_data = {n: self.tab_mgr.extract_tab_data(n) for n in self.tab_mgr.tabs_content.keys()}
                self.score_calc.calculate_batch(self.app.character_var, tabs_data, enabled_methods, self.app.language)
        except Exception as e:
            self.logger.exception(f"Calc error: {e}")

    def on_ocr_completed(self, result: Any) -> None:
        """Handles OCR completion, routing the result to the best tab."""
        from core.data_contracts import OCRResult, BatchItemResult
        
        # Check for character selection waiting state
        self.app.check_character_selected(quiet=True)
        
        if isinstance(result, OCRResult):
            for msg in result.log_messages:
                self.app.gui_log(msg)
            
            target_tab = self.tab_mgr.find_best_tab_match(result.cost, result.main_stat, self.app.character_var)
            if not target_tab:
                target_tab = self.tab_mgr.get_selected_tab_name()
            
            if target_tab:
                self._switch_to_tab(target_tab)
                self.tab_mgr.apply_ocr_result_to_tab(target_tab, result)
                self.tab_mgr.save_tab_image(target_tab, result.original_image, result.cropped_image)
                # Show overlay on the current display
                self.ui.display_ocr_overlay(result)
                
        elif isinstance(result, BatchItemResult):
            target_tab = self.tab_mgr.find_best_tab_match(result.result.cost, result.result.main_stat, self.app.character_var)
            if not target_tab:
                target_tab = self.tab_mgr.get_selected_tab_name()
            
            if target_tab:
                self.app.gui_log(f"Applying batch result to tab: {target_tab}")
                self.tab_mgr.apply_ocr_result_to_tab(target_tab, result.result)
                self.tab_mgr.save_tab_image(target_tab, result.original_image, result.cropped_image)
                # Note: For batch, overlay only shows if it's the current tab, 
                # but we'll focus on single first.

    def _switch_to_tab(self, tab_name: str) -> None:
        config_key = self.app.app_config.current_config_key
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        if tab_name in tab_names:
            idx = tab_names.index(tab_name)
            self.app.notebook.setCurrentIndex(idx)

    def on_tab_changed(self, index: int) -> None:
        if index < 0 or getattr(self.app, "_updating_tabs", False):
            return
        tab_name = self.tab_mgr.get_selected_tab_name()
        if tab_name:
            self.app.show_tab_image(tab_name)
            self.app.show_tab_result(tab_name)

    def open_char_settings_new(self) -> None:
        from ui.dialogs import CharSettingDialog
        CharSettingDialog(self.app, self.character_manager.register_character).exec()

    def open_char_settings_edit(self) -> None:
        from ui.dialogs import CharSettingDialog
        from PySide6.QtWidgets import QInputDialog
        
        target_char = self.app.character_var
        if not target_char:
            all_chars = self.character_manager.get_all_characters(self.app.language)
            if not all_chars: return
            items = [name for name, internal in all_chars]
            item, ok = QInputDialog.getItem(self.app, self.app.tr("select_character"), 
                                           self.app.tr("select_character_to_edit"), items, 0, False)
            if ok and item:
                target_char = next((internal for name, internal in all_chars if name == item), None)
            else: return

        p = self.character_manager.get_character_profile(target_char)
        if p: CharSettingDialog(self.app, self.character_manager.register_character, profile=p).exec()

    def open_display_settings(self) -> None:
        from ui.dialogs import DisplaySettingsDialog
        DisplaySettingsDialog(self.app).exec()

    def open_history(self) -> None:
        from ui.dialogs import HistoryDialog
        from managers.history_manager import HistoryManager # Double check if needed
        HistoryDialog(self.app, self.app.history_mgr).exec()

    def open_image_preprocessing_settings(self) -> None:
        from ui.dialogs import ImagePreprocessingSettingsDialog
        ImagePreprocessingSettingsDialog(self.app).exec()

    def import_image(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        self.app.check_character_selected(quiet=True)
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.app, self.app.tr("select_image_file"), "", 
            f"{self.app.tr('image_files')} (*.png *.jpg *.jpeg *.bmp *.gif);;{self.app.tr('all_files')} (*.*)"
        )
        if file_paths:
            self.image_proc.process_images_from_paths(file_paths)

    def paste_from_clipboard(self) -> None:
        self.app.check_character_selected(quiet=True)
        self.image_proc.paste_from_clipboard()

    def on_config_change(self, text: str) -> None:
        """Rebuild the tab configuration in response to a cost configuration change."""
        self.app.current_config_key = text # Update app state
        self.config_manager.update_app_setting('current_config_key', text)
        if not getattr(self.app, "_updating_tabs", False):
            self.tab_mgr.update_tabs()
            self.logger.info(f"Cost configuration changed: Tabs updated by {text}")
            self.tab_mgr.apply_character_main_stats(character=self.app.character_var)
            self.ui.filter_characters_by_config()
            self.save_config()
    
    def on_character_change(self, index: int) -> None:
        """Handle character change."""
        self.logger.info(f"on_character_change start: index={index}")
        if index < 0:
            self.logger.info("on_character_change: index < 0, returning")
            return

        # Retrieve the internal name directly from the UserData of the selected item
        internal_name = self.ui.character_combo.itemData(index)
        
        if internal_name: # Ensure internal_name is not empty
            self.logger.info(f"Character selected: {internal_name}")
            self.logger.info("on_character_change: setting app.character_var")
            self.app.character_var = internal_name
            
            # Automatically switch tab configuration if the character has a specific one
            new_config = self.character_manager.get_character_config_key(internal_name)
            if new_config and new_config != self.app.current_config_key:
                self.logger.info(f"Auto-switching tab configuration to {new_config} for {internal_name}")
                if self.ui.config_combo:
                    self.ui.config_combo.setCurrentText(new_config)
            else:
                self.logger.info("on_character_change: applying character main stats")
                t0 = time.monotonic()
                self.tab_mgr.apply_character_main_stats(character=internal_name)
                t1 = time.monotonic()
                self.logger.info(f"apply_character_main_stats duration: {t1 - t0:.4f}s")
            
            self.logger.info("on_character_change: saving config")
            self.save_config()

            # Trigger calculation if waiting or auto calculate is enabled, 
            # but ONLY if there is actual data to calculate (image or substats).
            should_calc = getattr(self.app, "_waiting_for_character", False) or self.app.app_config.auto_calculate
            if should_calc:
                score_mode = self.app.score_mode_var # "single" or "batch"
                self.logger.info(f"on_character_change: should_calc True, score_mode={score_mode}")
                t0 = time.monotonic()
                has_data = self.tab_mgr.has_calculatable_data(mode=score_mode)
                t1 = time.monotonic()
                self.logger.info(f"has_calculatable_data duration: {t1 - t0:.4f}s, result={has_data}")
                if has_data:
                    self.logger.info("on_character_change: has calculatable data, triggering calculation")
                    t0 = time.monotonic()
                    self.app.trigger_calculation()
                    t1 = time.monotonic()
                    self.logger.info(f"trigger_calculation returned in {t1 - t0:.4f}s")
                else:
                    self.logger.info("Character changed but no data to calculate. Skipping auto-calc.")
            self.logger.info("on_character_change end: internal_name branch complete")
        else:
            # If the empty item is selected, clear character_var
            self.logger.info("on_character_change: clearing character_var")
            self.app.character_var = ""
            self.logger.info("Character selection cleared.")
            self.logger.info("on_character_change: applying character main stats for cleared selection")
            self.tab_mgr.apply_character_main_stats() # Apply to clear any existing stats
            self.logger.info("on_character_change: saving config after clear")
            self.save_config()
        
        self.logger.info("on_character_change end")
    
    def on_language_change(self, text: str) -> None:
        """Handle language change."""
        self.logger.info(f"Language change requested: {text}")
        if text != self.app.app_config.language:
            self.app.language = text
            self.app.html_renderer.language = text
            self.config_manager.update_app_setting('language', text)
            self.save_config()
            
            # Instant UI Update
            self.logger.info("Retranslating UI and Tabs...")
            self.ui.retranslate_ui()
            self.tab_mgr.retranslate_tabs(text)
            
            # Update character list (names might be translated)
            self.ui.filter_characters_by_config()
            
            self.logger.info(f"Language change to {text} completed.")
            self.app.status_bar.showMessage(self.app.tr("settings_loaded"), 5000)
        else:
            self.logger.debug(f"Language already set to {text}, skipping update.")
    
    def on_mode_change(self, mode: str) -> None:
        """Handle input mode change."""
        self.app.mode_var = mode # Update app state
        self.config_manager.update_app_setting('mode_var', mode)
        self.ui.update_ui_mode()
        self.save_config()

    def on_mode_manual_toggled(self, checked: bool) -> None:
        if checked:
            self.on_mode_change("manual")

    def on_mode_ocr_toggled(self, checked: bool) -> None:
        if checked:
            self.on_mode_change("ocr")
    
    def on_auto_main_change(self, checked: bool) -> None:
        self.app.auto_apply_main_stats = checked # Update app state
        self.config_manager.update_app_setting('auto_apply_main_stats', checked)
        self.save_config()

    def on_auto_calculate_change(self, checked: bool) -> None:
        self.config_manager.update_app_setting('auto_calculate', checked)
        self.save_config()

    def on_score_mode_change(self, mode: str) -> None:
        self.app.score_mode_var = mode # Update app state
        self.config_manager.update_app_setting('score_mode_var', mode)
        self.save_config()

    def on_score_mode_batch_toggled(self, checked: bool) -> None:
        if checked:
            self.on_score_mode_change("batch")

    def on_score_mode_single_toggled(self, checked: bool) -> None:
        if checked:
            self.on_score_mode_change("single")
    
    def on_calc_method_changed(self) -> None:
        """Handle calculation method checkbox changes."""
        # Get current checkbox states
        enabled_methods = {
            "normalized": self.ui.cb_method_normalized.isChecked(),
            "ratio": self.ui.cb_method_ratio.isChecked(),
            "roll": self.ui.cb_method_roll.isChecked(),
            "effective": self.ui.cb_method_effective.isChecked(),
            "cv": self.ui.cb_method_cv.isChecked()
        }
        
        # Validate that at least one method is enabled
        if not any(enabled_methods.values()):
            # Show warning and re-enable the last unchecked method
            QMessageBox.warning(
                self.app,
                self.app.tr("warning"),
                self.app.tr("no_methods_selected")
            )
            # Re-enable the checkbox that was just unchecked
            sender = self.app.sender()
            if sender:
                sender.setChecked(True)
            return
        
        # Update config
        self.config_manager.update_app_setting('enabled_calc_methods', enabled_methods)
        self.save_config()
        self.logger.info(f"Calculation methods updated: {[k for k, v in enabled_methods.items() if v]}")

    def on_crop_mode_change(self, mode: str) -> None:
        self.app.crop_mode_var = mode
        self.config_manager.update_app_setting('crop_mode', mode)
        self.save_config()

    def on_crop_percent_change(self, text: str) -> None:
        try:
            sender = self.app.sender()
            value = float(text) if text else 0.0

            if sender == self.ui.entry_crop_l:
                self.app.crop_left_percent_var = value
                self.config_manager.update_app_setting('crop_left_percent', value)
                self.ui.slider_crop_l.setValue(int(value))
            elif sender == self.ui.entry_crop_t:
                self.app.crop_top_percent_var = value
                self.config_manager.update_app_setting('crop_top_percent', value)
                self.ui.slider_crop_t.setValue(int(value))
            elif sender == self.ui.entry_crop_w:
                self.app.crop_width_percent_var = value
                self.config_manager.update_app_setting('crop_width_percent', value)
                self.ui.slider_crop_w.setValue(int(value))
            elif sender == self.ui.entry_crop_h:
                self.app.crop_height_percent_var = value
                self.config_manager.update_app_setting('crop_height_percent', value)
                self.ui.slider_crop_h.setValue(int(value))
            
            self.save_config()
            self.schedule_crop_preview()
        except ValueError:
            pass # Ignore invalid float input

    def on_crop_slider_change(self, value: int) -> None:
        sender = self.app.sender()
        if not sender:
            return

        # Identify which slider sent the signal
        if sender.objectName() == "slider_crop_l":
            self.ui.entry_crop_l.setText(str(value))
        elif sender.objectName() == "slider_crop_t":
            self.ui.entry_crop_t.setText(str(value))
        elif sender.objectName() == "slider_crop_w":
            self.ui.entry_crop_w.setText(str(value))
        elif sender.objectName() == "slider_crop_h":
            self.ui.entry_crop_h.setText(str(value))
        
        # Changing the text in QLineEdit will trigger on_crop_percent_change,
        # which will then update the config and schedule the preview.


    def cycle_theme(self) -> None:
        """Cycle between light, dark, and clear themes."""
        current = self.theme_manager.get_current_theme()
        if current == "dark":
            new_theme = "light"
        elif current == "light":
            new_theme = "clear"
        else:
            new_theme = "dark"
            
        self.logger.info(f"Theme changed to {new_theme} mode.")
        self.theme_manager.apply_theme(new_theme)
        self.config_manager.update_app_setting('theme', new_theme) # Save theme setting
        self.save_config()
    
    def save_config(self) -> None:
        """Schedule config save with debounce."""
        self._save_timer.start(TIMER_SAVE_CONFIG_INTERVAL)
    
    def actual_save_config(self) -> None:
        """Save current settings to config.json."""
        try:
            # List of settings that are already tracked in config_manager
            # These are automatically saved when updated
            settings_to_save = [
                'language',
                'crop_mode',
                'crop_left_percent',
                'crop_top_percent',
                'crop_width_percent',
                'crop_height_percent',
                'current_config_key',
                'mode_var',
                'score_mode_var',
                'auto_apply_main_stats',
                'enabled_calc_methods'
            ]
            
            # Update character_var from app state (special case)
            self.config_manager.update_app_setting('character_var', self.app.character_var)
            # Update theme from theme_manager (special case)
            self.config_manager.update_app_setting('theme', self.theme_manager.get_current_theme())
            
            t0 = time.monotonic()
            saved = self.config_manager.save()
            t1 = time.monotonic()
            if saved:
                self.logger.info(f"Config saved. duration: {t1 - t0:.4f}s")
            else:
                self.app.gui_log("Failed to save config.json. Check logs for details.")
        except Exception as e:
            self.app.gui_log(f"Config save error: {e}")
            self.logger.error(f"Config save error: {e}")
    
    def schedule_crop_preview(self) -> None:
        """Schedule crop preview update."""
        self._crop_preview_timer.start(TIMER_CROP_PREVIEW_INTERVAL)
    
    def schedule_image_preview_update_on_resize(self, *args: Any) -> None:
        """Schedule image preview update on resize."""
        if hasattr(self, '_image_preview_timer'):
            self._image_preview_timer.stop()
        else:
            self._image_preview_timer = QTimer()
            self._image_preview_timer.setSingleShot(True)
            self._image_preview_timer.timeout.connect(self.image_proc.perform_image_preview_update_on_resize)
        
        self._image_preview_timer.start(TIMER_RESIZE_PREVIEW_INTERVAL)

    def on_profiles_updated(self):
        """
        Slot for when character profiles are loaded or updated.
        This triggers the UI to update the character list.
        """
        self.app.gui_log("Character profiles updated, refreshing UI.")
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, self.app.character_var)
        self.ui.filter_characters_by_config()

    def on_character_registered(self, internal_char_name: str):
        """Slot to handle UI updates after a new character is registered."""
        self.app.gui_log(f"New character '{internal_char_name}' registered. Updating UI.")
        
        # Repopulate combobox and select the new character
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, internal_char_name)
        
        # Update internal state and UI to reflect the new character
        self.app.character_var = internal_char_name
        
        # Update config key based on the new character and update the config combobox
        new_config_key = self.character_manager.get_character_config_key(internal_char_name)
        if new_config_key:
            self.app.current_config_key = new_config_key
            if self.app.ui.config_combo:
                idx = self.app.ui.config_combo.findText(new_config_key)
                if idx >= 0:
                    self.app.ui.config_combo.setCurrentIndex(idx)
        
        self.ui.filter_characters_by_config() # Re-filter to match the new config
        self.tab_mgr.apply_character_main_stats()
