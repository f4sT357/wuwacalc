"""
Event Handling Module (PySide6)

Provides event callbacks and debounce processing.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING, Dict

from PySide6.QtWidgets import QMessageBox, QApplication, QInputDialog, QFileDialog
from PySide6.QtCore import QTimer

from utils.constants import (
    TIMER_SAVE_CONFIG_INTERVAL,
    TIMER_CROP_PREVIEW_INTERVAL,
    TIMER_RESIZE_PREVIEW_INTERVAL
)
from core.data_contracts import OCRResult, BatchItemResult

if TYPE_CHECKING:
    from core.app_setup import AppContext


class EventHandlers:
    """Class responsible for event handling and application-wide signal management."""

    def __init__(self, app: Any, ctx: AppContext) -> None:
        """
        Initialize event handlers.

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
        self._resize_preview_timer.timeout.connect(
            self.image_proc.perform_image_preview_update_on_resize
        )

        # State to track OCR trigger context
        self._ocr_trigger_character = None
        self._temp_ocr_result = None

    def setup_connections(self) -> None:
        """Set up all signal and slot connections for the application."""
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

        self.ui.image_label.selection_completed.connect(self.image_proc.set_manual_crop_rect)

        for method, cb in self.ui.method_checkboxes.items():
            cb.toggled.connect(self.on_calc_method_changed)

    def trigger_calculation(self) -> None:
        """Execute the calculation logic based on current score mode."""
        try:
            if not self.app.character_var:
                self.app._waiting_for_character = True
                self.ui.result_text.setHtml(
                    f"<h3 style='color: orange;'>{self.app.tr('waiting_for_character')}</h3>"
                )
                return

            self.app._waiting_for_character = False
            self.app.show_duplicate_entries()

            enabled_methods = self.app.app_config.enabled_calc_methods
            if self.app.score_mode_var == "single":
                tab_name = self.tab_mgr.get_selected_tab_name()
                entry = self.tab_mgr.extract_tab_data(tab_name)
                if entry:
                    self.score_calc.calculate_single(
                        self.app.character_var, tab_name, entry, enabled_methods
                    )
            else:
                tabs_data = {
                    n: self.tab_mgr.extract_tab_data(n)
                    for n in self.tab_mgr.tabs_content.keys()
                }
                self.score_calc.calculate_batch(
                    self.app.character_var, tabs_data, enabled_methods, self.app.language
                )
        except Exception as e:
            self.logger.exception(f"Calculation trigger error: {e}")

    def on_ocr_completed(self, result: Any) -> None:
        """Handle OCR process completion and route data to tabs."""
        # Visual Feedback: Show overlay immediately
        ocr_data = result if isinstance(result, OCRResult) else result.result
        self.ui.display_ocr_overlay(ocr_data)

        # Defer if no character selected
        if not self.app.character_var:
            self._temp_ocr_result = result
            self.app.gui_log("OCR data cached. Waiting for character selection.")
            QMessageBox.information(
                self.app, self.app.tr("info"),
                "OCR完了。適用先のキャラクターを選択してください。\n"
                "Please select a character to apply the data to the correct cost slot."
            )
            return

        # Prevent OCR from overwriting if character context changed during processing
        if (self._ocr_trigger_character is not None
                and self.app.character_var != self._ocr_trigger_character):
            msg = (
                f"OCR開始時と異なるキャラクターが選択されています。\n"
                f"(開始時: {self._ocr_trigger_character} → 現在: {self.app.character_var})\n\n"
                f"このOCR結果を現在のタブに適用しますか？"
            )
            reply = QMessageBox.question(
                self.app, self.app.tr("warning"), msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.No:
                self.app.gui_log(
                    f"OCR result discarded (Character changed: "
                    f"{self._ocr_trigger_character} -> {self.app.character_var})"
                )
                return
            else:
                self.app.gui_log("Applying OCR result despite character change (Confirmed).")

        if isinstance(result, OCRResult):
            self._apply_ocr_result(result, result.original_image, result.cropped_image)
        elif isinstance(result, BatchItemResult):
            self._apply_ocr_result(
                result.result, result.original_image, result.cropped_image, is_batch=True
            )

    def _apply_ocr_result(
        self, ocr_data: Any, original_img: Any, cropped_img: Any, is_batch: bool = False
    ) -> None:
        """Internal helper to apply structured OCR data to the correct UI tab."""
        for msg in ocr_data.log_messages:
            self.app.gui_log(msg)

        target_tab = self.tab_mgr.find_best_tab_match(
            ocr_data.cost, ocr_data.main_stat, self.app.character_var
        )
        if not target_tab:
            target_tab = self.tab_mgr.get_selected_tab_name()

        if target_tab:
            if not is_batch:
                self._switch_to_tab(target_tab)

            log_prefix = "batch " if is_batch else ""
            self.app.gui_log(f"Applying {log_prefix}result to tab: {target_tab}")
            self.tab_mgr.apply_ocr_result_to_tab(target_tab, ocr_data)
            self.tab_mgr.save_tab_image(target_tab, original_img, cropped_img)

            # Show overlay on the current display (from Incoming)
            if not is_batch:
                 self.ui.display_ocr_overlay(ocr_data)

            # Auto-calculate if enabled
            if self.app.app_config.auto_calculate:
                QTimer.singleShot(100, self.trigger_calculation)

    def _switch_to_tab(self, tab_name: str) -> None:
        """Switch the UI notebook to the specified tab name."""
        config_key = self.app.app_config.current_config_key
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        if tab_name in tab_names:
            idx = tab_names.index(tab_name)
            self.app.notebook.setCurrentIndex(idx)

    def on_tab_changed(self, index: int) -> None:
        """Slot triggered when the current echo tab is changed."""
        if index < 0 or getattr(self.app, "_updating_tabs", False):
            return
        tab_name = self.tab_mgr.get_selected_tab_name()
        if tab_name:
            self.app.show_tab_image(tab_name)
            self.app.show_tab_result(tab_name)

    def open_char_settings_new(self) -> None:
        """Open dialog to register a new character profile."""
        from ui.dialogs import CharSettingDialog
        CharSettingDialog(self.app, self.character_manager.register_character).exec()

    def open_char_settings_edit(self) -> None:
        """Open dialog to edit current or selected character profile."""
        from ui.dialogs import CharSettingDialog

        target_char = self.app.character_var
        if not target_char:
            all_chars = self.character_manager.get_all_characters(self.app.language)
            if not all_chars:
                return
            items = [name for name, internal in all_chars]
            item, ok = QInputDialog.getItem(
                self.app, self.app.tr("select_character"),
                self.app.tr("select_character_to_edit"), items, 0, False
            )
            if ok and item:
                target_char = next(
                    (internal for name, internal in all_chars if name == item), None
                )
            else:
                return

        p = self.character_manager.get_character_profile(target_char)
        if p:
            CharSettingDialog(self.app, self.character_manager.register_character, profile=p).exec()

    def open_display_settings(self) -> None:
        """Open the display and appearance settings dialog."""
        from ui.dialogs import DisplaySettingsDialog
        DisplaySettingsDialog(self.app).exec()

    def open_history(self) -> None:
        """Open the evaluation history dialog."""
        from ui.dialogs import HistoryDialog
        HistoryDialog(self.app, self.app.history_mgr).exec()

    def open_image_preprocessing_settings(self) -> None:
        """Open the image preprocessing configuration dialog."""
        from ui.dialogs import ImagePreprocessingSettingsDialog
        ImagePreprocessingSettingsDialog(self.app).exec()

    def import_image(self) -> None:
        """Open file dialog to import one or more images for OCR."""
        self.app.check_character_selected(quiet=True)
        # Capture character context when starting OCR
        self._ocr_trigger_character = self.app.character_var
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.app, self.app.tr("select_image_file"), "",
            f"{self.app.tr('image_files')} (*.png *.jpg *.jpeg *.bmp *.gif);;"
            f"{self.app.tr('all_files')} (*.*)"
        )
        if file_paths:
            self.image_proc.process_images_from_paths(file_paths)

    def paste_from_clipboard(self) -> None:
        """Paste an image from the system clipboard and trigger OCR."""
        self.app.check_character_selected(quiet=True)
        # Capture character context when starting OCR
        self._ocr_trigger_character = self.app.character_var
        self.image_proc.paste_from_clipboard()

    def on_config_change(self, text: str) -> None:
        """Handle cost configuration changes and rebuild UI tabs."""
        self.app.current_config_key = text
        self.config_manager.update_app_setting('current_config_key', text)
        if not getattr(self.app, "_updating_tabs", False):
            self.tab_mgr.update_tabs()
            self.logger.info(f"Configuration changed: Tabs updated to {text}")
            self.tab_mgr.apply_character_main_stats(character=self.app.character_var)
            self.ui.filter_characters_by_config()
            self.save_config()

    def on_character_change(self, index: int) -> None:
        """Handle character selection changes and load equipped echoes."""
        self.logger.debug(f"Character change triggered: index={index}")
        if index < 0:
            return

        internal_name = self.ui.character_combo.itemData(index)

        if internal_name:
            self.app.character_var = internal_name

            # Switch configuration if character has a specific preset
            new_config = self.character_manager.get_character_config_key(internal_name)
            if new_config and new_config != self.app.current_config_key:
                if self.ui.config_combo:
                    self.ui.config_combo.setCurrentText(new_config)
            else:
                self.tab_mgr.apply_character_main_stats(character=internal_name)

            # Apply dynamic element theme to UI
            self.theme_manager.apply_theme(self.app.app_config.theme)
            self.save_config()

            # --- Logic to load equipped echoes ---
            config_key = self.app.app_config.current_config_key
            tab_names = self.data_manager.tab_configs.get(config_key, [])
            all_equipped = self.character_manager.get_all_equipped_echoes(internal_name)
            used_keys = set()
            loaded_count = 0

            # Direct match pass
            for name in tab_names:
                if self.tab_mgr.is_tab_empty(name) and name in all_equipped:
                    equipped = all_equipped[name]
                    if equipped:
                        self.tab_mgr.load_entry_into_tab(name, equipped)
                        used_keys.add(name)
                        loaded_count += 1

            # Cost match pass
            for name in tab_names:
                if self.tab_mgr.is_tab_empty(name):
                    target_cost = name.split('_')[0]
                    for eq_key, eq_entry in all_equipped.items():
                        if eq_key in used_keys:
                            continue
                        eq_cost = str(eq_entry.cost) if eq_entry.cost else eq_key.split('_')[0]
                        if eq_cost == target_cost:
                            self.tab_mgr.load_entry_into_tab(name, eq_entry)
                            used_keys.add(eq_key)
                            loaded_count += 1
                            break

            if loaded_count > 0:
                self.app.gui_log(f"Auto-load complete: {loaded_count} echoes restored.")

            # Check and apply deferred OCR data
            if self._temp_ocr_result:
                result = self._temp_ocr_result
                self.app.gui_log("Applying cached OCR data to new character context...")
                if isinstance(result, OCRResult):
                    self._apply_ocr_result(result, result.original_image, result.cropped_image)
                elif isinstance(result, BatchItemResult):
                     self._apply_ocr_result(
                        result.result, result.original_image, result.cropped_image, is_batch=True
                    )
                self._temp_ocr_result = None

            # Auto-calculate
            should_calc = (getattr(self.app, "_waiting_for_character", False)
                           or self.app.app_config.auto_calculate)
            if should_calc:
                score_mode = self.app.score_mode_var
                if self.tab_mgr.has_calculatable_data(mode=score_mode):
                    self.app.trigger_calculation()
        else:
            self.app.character_var = ""
            self.tab_mgr.apply_character_main_stats()
            self.save_config()

    def on_language_change(self, text: str) -> None:
        """Update application language and refresh UI translations."""
        if text != self.app.app_config.language:
            self.app.language = text
            self.app.html_renderer.language = text
            self.config_manager.update_app_setting('language', text)
            self.save_config()
            self.ui.retranslate_ui()
            self.tab_mgr.retranslate_tabs(text)
            self.ui.filter_characters_by_config()
            self.app.status_bar.showMessage(self.app.tr("settings_loaded"), 5000)

    def on_mode_change(self, mode: str) -> None:
        """Handle change between manual input and OCR mode."""
        self.app.mode_var = mode
        self.config_manager.update_app_setting('mode_var', mode)
        self.ui.update_ui_mode()
        self.save_config()

    def on_auto_main_change(self, checked: bool) -> None:
        """Toggle automatic application of preferred main stats."""
        self.app.auto_apply_main_stats = checked
        self.config_manager.update_app_setting('auto_apply_main_stats', checked)
        self.save_config()

    def on_auto_calculate_change(self, checked: bool) -> None:
        """Toggle automatic score calculation after data entry/OCR."""
        self.config_manager.update_app_setting('auto_calculate', checked)
        self.save_config()

    def on_score_mode_change(self, mode: str) -> None:
        """Switch between batch calculation and single tab calculation."""
        self.app.score_mode_var = mode
        self.config_manager.update_app_setting('score_mode_var', mode)
        self.save_config()

    def on_calc_method_changed(self) -> None:
        """Update enabled calculation methods based on UI checkboxes."""
        enabled_methods = {
            "normalized": self.ui.cb_method_normalized.isChecked(),
            "ratio": self.ui.cb_method_ratio.isChecked(),
            "roll": self.ui.cb_method_roll.isChecked(),
            "effective": self.ui.cb_method_effective.isChecked(),
            "cv": self.ui.cb_method_cv.isChecked()
        }

        if not any(enabled_methods.values()):
            QMessageBox.warning(
                self.app, self.app.tr("warning"), self.app.tr("no_methods_selected")
            )
            sender = self.app.sender()
            if sender:
                sender.setChecked(True)
            return

        self.config_manager.update_app_setting('enabled_calc_methods', enabled_methods)
        self.save_config()

    def on_crop_mode_change(self, mode: str) -> None:
        """Change the image cropping mode (percent vs drag)."""
        self.app.crop_mode_var = mode
        self.config_manager.update_app_setting('crop_mode', mode)
        self.save_config()
        self.ui.image_label.set_drag_enabled(mode == "drag")

    def on_crop_percent_change(self, text: str) -> None:
        """Handle direct numeric input for crop percentage areas."""
        try:
            sender = self.app.sender()
            value = float(text) if text else 0.0
            if sender == self.ui.entry_crop_l:
                self.config_manager.update_app_setting('crop_left_percent', value)
                self.ui.slider_crop_l.setValue(int(value))
            elif sender == self.ui.entry_crop_t:
                self.config_manager.update_app_setting('crop_top_percent', value)
                self.ui.slider_crop_t.setValue(int(value))
            elif sender == self.ui.entry_crop_w:
                self.config_manager.update_app_setting('crop_width_percent', value)
                self.ui.slider_crop_w.setValue(int(value))
            elif sender == self.ui.entry_crop_h:
                self.config_manager.update_app_setting('crop_height_percent', value)
                self.ui.slider_crop_h.setValue(int(value))
            self.save_config()
            self.schedule_crop_preview()
        except ValueError:
            pass

    def on_crop_slider_change(self, value: int) -> None:
        """Handle slider movements for crop percentage areas."""
        sender = self.app.sender()
        if not sender:
            return
        obj_name = sender.objectName()
        if obj_name == "slider_crop_l":
            self.ui.entry_crop_l.setText(str(value))
        elif obj_name == "slider_crop_t":
            self.ui.entry_crop_t.setText(str(value))
        elif obj_name == "slider_crop_w":
            self.ui.entry_crop_w.setText(str(value))
        elif obj_name == "slider_crop_h":
            self.ui.entry_crop_h.setText(str(value))

    def cycle_theme(self) -> None:
        """Cycle through available application themes."""
        themes = ["dark", "light", "clear"]
        current = self.theme_manager.get_current_theme()
        new_theme = themes[(themes.index(current) + 1) % len(themes)] \
            if current in themes else "dark"
        self.theme_manager.apply_theme(new_theme)
        self.config_manager.update_app_setting('theme', new_theme)
        self.save_config()

    def save_config(self) -> None:
        """Request a delayed configuration save."""
        self._save_timer.start(TIMER_SAVE_CONFIG_INTERVAL)

    def actual_save_config(self) -> None:
        """Persist the current application configuration to disk."""
        self.config_manager.update_app_setting('character_var', self.app.character_var)
        self.config_manager.update_app_setting('theme', self.theme_manager.get_current_theme())
        self.config_manager.save()

    def schedule_crop_preview(self) -> None:
        """Schedule a delayed preview update for the cropped image."""
        self._crop_preview_timer.start(TIMER_CROP_PREVIEW_INTERVAL)

    def schedule_image_preview_update_on_resize(self, *args: Any) -> None:
        """Handle resizing of the image preview area."""
        self._resize_preview_timer.start(TIMER_RESIZE_PREVIEW_INTERVAL)

    def on_profiles_updated(self) -> None:
        """Refresh UI character selection after profiles are reloaded."""
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, self.app.character_var)
        self.ui.filter_characters_by_config()

    def on_character_registered(self, internal_char_name: str) -> None:
        """Update UI and select newly registered character."""
        self.app.gui_log(f"New character '{internal_char_name}' registered.")
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, internal_char_name)
        self.app.character_var = internal_char_name
        new_config = self.character_manager.get_character_config_key(internal_char_name)
        if new_config:
            self.ui.config_combo.setCurrentText(new_config)
        self.ui.filter_characters_by_config()
        self.tab_mgr.apply_character_main_stats()

    def generate_scoreboard(self) -> None:
        """Generate a build summary scoreboard image."""
        from core.scoreboard_generator import ScoreboardGenerator

        if not self.app.character_var:
            QMessageBox.warning(self.app, self.app.tr("warning"), self.app.tr("waiting_for_character"))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.app.character_var}_Build_{ts}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self.app, self.app.tr("save_scoreboard"), default_name, "Images (*.png)"
        )
        if not file_path:
            return

        try:
            generator = ScoreboardGenerator(logger=self.logger)
            success = self.tab_mgr.generate_scoreboard_image(
                character_name=self.app.character_var,
                output_path=file_path,
                generator=generator,
                score_calculator=self.score_calc,
                enabled_methods=self.app.app_config.enabled_calc_methods,
                language=self.app.language
            )
            if success:
                QMessageBox.information(
                    self.app, self.app.tr("info"), self.app.tr("save_success")
                )
        except Exception as e:
            self.logger.exception(f"Scoreboard generation error: {e}")
