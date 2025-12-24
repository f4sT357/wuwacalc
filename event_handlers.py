"""
Event Handling Module (PyQt6)

Provides event callbacks and debounce processing.
"""

import logging
from typing import Any, Optional

from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QTimer
from constants import (
    TIMER_SAVE_CONFIG_INTERVAL,
    TIMER_CROP_PREVIEW_INTERVAL,
    TIMER_RESIZE_PREVIEW_INTERVAL
)

class EventHandlers:
    """Class responsible for event handling."""
    
    def __init__(self, app: Any, ui_components: Any, config_manager: Any, data_manager: Any, tab_manager: Any, theme_manager: Any, character_manager: Any, image_processor: Any) -> None:
        """
        Initialization
        
        Args:
            app: The main application instance.
            ui_components: UIComponents instance.
            config_manager: ConfigManager instance.
            data_manager: DataManager instance.
            tab_manager: TabManager instance.
            theme_manager: ThemeManager instance.
            character_manager: CharacterManager instance.
            image_processor: ImageProcessor instance.
        """
        self.app = app # This will be removed in a later step
        self.ui = ui_components
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.tab_mgr = tab_manager
        self.theme_manager = theme_manager
        self.character_manager = character_manager
        self.image_proc = image_processor
        
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
        """
        Set up any additional connections not handled in UI creation.
        Most connections are now done in UIComponents.
        """
        pass
    
    def on_config_change(self, text: str) -> None:
        """Rebuild the tab configuration in response to a cost configuration change."""
        self.config_manager.update_app_setting('current_config_key', text)
        if not getattr(self.app, "_updating_tabs", False):
            self.tab_mgr.update_tabs()
            self.logger.info(f"Cost configuration changed: Tabs updated by {text}")
            self.tab_mgr.apply_character_main_stats()
            self.ui.filter_characters_by_config()
            self.save_config()
    
    def on_character_change(self, index: int) -> None:
        """Handle character change."""
        if index < 0:
            return

        # Retrieve the internal name directly from the UserData of the selected item
        internal_name = self.ui.character_combo.itemData(index)
        
        if internal_name: # Ensure internal_name is not empty
            self.app.character_var = internal_name
            self.logger.info(f"Character selected: {internal_name}")
            
            # Automatically switch tab configuration if the character has a specific one
            new_config = self.character_manager.get_character_config_key(internal_name)
            if new_config and new_config != self.app.current_config_key:
                self.logger.info(f"Auto-switching tab configuration to {new_config} for {internal_name}")
                if self.ui.config_combo:
                    self.ui.config_combo.setCurrentText(new_config)
            else:
                self.tab_mgr.apply_character_main_stats()
            
            self.save_config()

            # Trigger calculation if waiting or auto calculate is enabled
            if getattr(self.app, "_waiting_for_character", False) or self.app.app_config.auto_calculate:
                self.app.trigger_calculation()
        else:
            # If the empty item is selected, clear character_var
            self.app.character_var = ""
            self.logger.info("Character selection cleared.")
            self.tab_mgr.apply_character_main_stats() # Apply to clear any existing stats
            self.save_config()
    
    def on_language_change(self, text: str) -> None:
        """Handle language change."""
        if text != self.app.app_config.language:
            self.app.language = text
            self.app.html_renderer.language = text
            self.config_manager.update_app_setting('language', text)
            self.save_config()
            
            # Instant UI Update
            self.ui.retranslate_ui()
            self.tab_mgr.retranslate_tabs()
            
            # Update character list (names might be translated)
            self.ui.filter_characters_by_config()
            
            self.logger.info(f"Language changed to: {text}")
            self.app.status_bar.showMessage(self.app.tr("settings_loaded"), 5000)
    
    def on_mode_change(self, mode: str) -> None:
        """Handle input mode change."""
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
        self.config_manager.update_app_setting('auto_apply_main_stats', checked)
        self.save_config()

    def on_auto_calculate_change(self, checked: bool) -> None:
        self.config_manager.update_app_setting('auto_calculate', checked)
        self.save_config()

    def on_score_mode_change(self, mode: str) -> None:
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


    def on_tab_changed(self, index: int) -> None:
        """Handle tab switch."""
        tab_name = self.tab_mgr.get_selected_tab_name()
        if tab_name:
            self.tab_mgr.show_tab_image(tab_name)
            self.tab_mgr.show_tab_result(tab_name)
    
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
            
            if self.config_manager.save():
                self.logger.info("Config saved.")
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
            if self.app.config_combo:
                idx = self.app.config_combo.findText(new_config_key)
                if idx >= 0:
                    self.app.config_combo.setCurrentIndex(idx)
        
        self.ui.filter_characters_by_config() # Re-filter to match the new config
        self.tab_mgr.apply_character_main_stats()
