import json
import logging
import os
import shutil
import sys
import webbrowser

from typing import Any, Callable, Optional, List, Tuple, Dict, Union

from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QStyleFactory, QComboBox, QStatusBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QShortcut, QKeySequence

from config_manager import ConfigManager
from constants import (
    THEME_COLORS,
    LOG_FILENAME,
    CONFIG_FILENAME,
    CHARACTER_STAT_WEIGHTS
)
from dialogs import CharSettingDialog, CropDialog, DisplaySettingsDialog, ImagePreprocessingSettingsDialog
from echo_data import EchoData
from languages import TRANSLATIONS
from utils import crop_image_by_percent, get_app_path, get_resource_path, get_substat_display, setup_tesseract, check_and_alert_environment
from data_contracts import EchoEntry, SubStat
from character_manager import CharacterManager


from theme_manager import ThemeManager
from score_calculator import ScoreCalculator
from tab_manager import TabManager
from event_handlers import EventHandlers
from ui_components import UIComponents
from image_processor import ImageProcessor
from app_logic import AppLogic
from data_manager import DataManager
from html_renderer import HtmlRenderer
from history_manager import HistoryManager
from dialogs import CharSettingDialog, CropDialog, DisplaySettingsDialog, ImagePreprocessingSettingsDialog, HistoryDialog
from ui_constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, RIGHT_TOP_HEIGHT,
    LOG_MIN_HEIGHT, LOG_DEFAULT_HEIGHT,
    IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT
)

# Tesseract setup
setup_tesseract()

class ScoreCalculatorApp(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.log_text = None
        self._startup_messages = []
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(get_app_path(), LOG_FILENAME), encoding='utf-8'),
                logging.StreamHandler()
            ])

        # Initialize DataManager
        try:
            self.data_manager = DataManager(get_resource_path("data"))
            self.data_manager.load_all()
        except Exception as e:
            # If critical data fails to load, show error and exit/disable features
            self.logger.critical(f"Failed to initialize DataManager: {e}")
            QMessageBox.critical(None, "Data Load Error", 
                               f"Critical game data could not be loaded.\nApp will close.\n\nError: {e}")
            sys.exit(1)

        self.character_manager = CharacterManager(self.logger, self.data_manager)
        self.history_mgr = HistoryManager()

        self.theme_manager = ThemeManager(self)
        self._init_config()
        self._init_vars()
        
        # Theme handling
        self._current_app_theme = self.app_config.theme
        self.theme_manager.apply_theme(self._current_app_theme)

        self.setWindowTitle("Wuthering Waves Echo Score Calculator")
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.tr("settings_loaded"), 5000)

        # Instantiate component modules
        self.html_renderer = HtmlRenderer(self.tr, self.language)
        self.score_calc = ScoreCalculator(self, self.html_renderer)
        self.tab_mgr = TabManager(self)
        self.logic = AppLogic(self.tr, self.data_manager, self.config_manager)
        self.image_proc = ImageProcessor(self, self.logic)
        self.ui = UIComponents(self)
        self.events = EventHandlers(
            self,
            self.ui,
            self.config_manager,
            self.data_manager,
            self.tab_mgr,
            self.theme_manager,
            self.character_manager,
            self.image_proc
        )
        
        # Connect signals from logic to slots in the main app
        self.logic.log_message.connect(self.gui_log)
        self.logic.ocr_error.connect(self.show_ocr_error_message)
        self.logic.info_message.connect(self.show_info_message)
        
        # Connect signals from CharacterManager
        self.character_manager.profiles_updated.connect(self.events.on_profiles_updated)
        self.character_manager.character_registered.connect(self.events.on_character_registered)

        # Connect signals from image processor
        self.image_proc.ocr_completed.connect(self.on_ocr_completed)
        
        # Timer references (using QTimer in PyQt6, handled in events or here)
        self._debounce_timers = {}

        # UI construction
        self.ui.create_main_layout()
        
        # Connect SettingsPanel signals to EventHandlers (Decoupling)
        settings = self.ui.settings_panel
        settings.configChanged.connect(self.events.on_config_change)
        settings.characterSelected.connect(self.events.on_character_change)
        settings.languageChanged.connect(self.events.on_language_change)
        settings.inputModeChanged.connect(self.events.on_mode_change)
        settings.autoMainChanged.connect(self.events.on_auto_main_change)
        settings.calcModeChanged.connect(self.events.on_score_mode_change)
        settings.calcMethodsChanged.connect(self.events.on_calc_method_changed)

        self.setCentralWidget(self.ui.main_widget)
        
        # Apply transparent frames setting if enabled
        if self.app_config.transparent_frames:
            self.theme_manager.update_frame_transparency(True)
        
        # Post-initialization setup
        QTimer.singleShot(100, self._post_init_setup)
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """Setup application-wide keyboard shortcuts."""
        try:
            # Ctrl + V: Paste from clipboard
            QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self.image_proc.paste_from_clipboard)
            
            # Ctrl + Enter or F5: Calculate
            QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self.score_calc.calculate_all_scores)
            QShortcut(QKeySequence("Ctrl+Enter"), self).activated.connect(self.score_calc.calculate_all_scores)
            QShortcut(QKeySequence("F5"), self).activated.connect(self.score_calc.calculate_all_scores)
            
            # Ctrl + S: Export to TXT
            QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.tab_mgr.export_result_to_txt)
            
            # Ctrl + R: Clear All
            QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.tab_mgr.clear_all)

            # Ctrl + H: History
            QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self.open_history)
            
            self.logger.info("Keyboard shortcuts initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize keyboard shortcuts: {e}")
            self.gui_log(f"Warning: Keyboard shortcuts could not be initialized.")

    def _init_config(self) -> None:
        """Initialize ConfigManager and load settings."""
        config_path = os.path.join(get_app_path(), CONFIG_FILENAME)
        self.config_manager = ConfigManager(config_path)
        self.config_manager.load()
        
        self.app_config = self.config_manager.get_app_config()
        self.theme_manager._migrate_background_image_path()  # Migrate legacy background image path
        ui_config = self.config_manager.get_ui_config()
        
        # Use constants from ui_constants module, but allow config override if needed
        self.WINDOW_WIDTH = ui_config.window_width if ui_config.window_width else WINDOW_WIDTH
        self.WINDOW_HEIGHT = ui_config.window_height if ui_config.window_height else WINDOW_HEIGHT
        self.RIGHT_TOP_HEIGHT = ui_config.right_top_height if ui_config.right_top_height else RIGHT_TOP_HEIGHT
        self.LOG_MIN_HEIGHT = ui_config.log_min_height if ui_config.log_min_height else LOG_MIN_HEIGHT
        self.LOG_DEFAULT_HEIGHT = ui_config.log_default_height if ui_config.log_default_height else LOG_DEFAULT_HEIGHT
        self.IMAGE_PREVIEW_MAX_WIDTH = ui_config.image_preview_max_width if ui_config.image_preview_max_width else IMAGE_PREVIEW_MAX_WIDTH
        self.IMAGE_PREVIEW_MAX_HEIGHT = ui_config.image_preview_max_height if ui_config.image_preview_max_height else IMAGE_PREVIEW_MAX_HEIGHT
        
        self.language = self.app_config.language
        self.crop_left_percent = self.app_config.crop_left_percent
        self.crop_top_percent = self.app_config.crop_top_percent
        self.crop_width_percent = self.app_config.crop_width_percent
        self.crop_height_percent = self.app_config.crop_height_percent

    def _init_vars(self) -> None:
        """Initialize UI-related variables."""
        app_config = self.app_config
        
        # Dictionary to store original frame properties for transparency toggle
        self._frame_original_properties: dict[int, dict[str, Any]] = {}
        
        # Replaced tk.StringVar with simple attributes. 
        # Updates will be handled via signals/slots in EventHandlers.
        self.current_config_key = app_config.current_config_key
        self.mode_var = app_config.mode_var
        
        # Always start with an empty character selection as per user request
        self.character_var = ""
        
        self.auto_apply_main_stats = app_config.auto_apply_main_stats
        self.score_mode_var = app_config.score_mode_var
        self._updating_tabs = False
        self.crop_mode_var = app_config.crop_mode
        self.crop_left_percent_var = app_config.crop_left_percent
        self.crop_top_percent_var = app_config.crop_top_percent
        self.crop_width_percent_var = app_config.crop_width_percent
        self.crop_height_percent_var = app_config.crop_height_percent
        
        self.loaded_image = None
        self.original_image = None
        self.image_label = None # Will be QLabel
        self._image_preview = None
        self._last_displayed_image_hash = None
        self._last_image_preview = None
        self._tab_images = {}
        
        # UI References (will be populated by UIComponents)
        self.result_text = None
        self.log_text = None
        self.notebook = None
        self.config_combo = None
        
    def update_app_font(self, font_family: str) -> None:
        """Update the application font."""
        self.app_config.app_font = font_family
        self.theme_manager.update_app_font(font_family)

    def apply_theme(self, theme_name: str) -> None:
        """Apply the specified theme."""
        self.theme_manager.apply_theme(theme_name)

    def tr(self, key: str, *args: Any) -> str:
        """Translate a key."""
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["ja"]).get(key, key)
        if args:
            try:
                return text.format(*args)
            except Exception as e:
                self.logger.warning(f"Failed to format translation string '{text}' with args {args}: {e}")
                return text
        return text
        
    def gui_log(self, msg: str) -> None:
        """Simple logging to GUI."""
        self.logger.info(msg)
        if self.status_bar:
            self.status_bar.showMessage(str(msg), 5000)
            
        if self.log_text is not None:
            try:
                self.log_text.append(str(msg))
                # Limit line count if needed, QTextEdit handles it reasonably well but good to prune
            except Exception as e:
                self.logger.debug(f"GUI log update failed: {e}")

    def show_ocr_error_message(self, title: str, message: str) -> None:
        """Slot to show a critical message box for OCR errors."""
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """Slot to show an informational message box."""
        QMessageBox.information(self, title, message)
        
    def on_ocr_completed(self, result: 'OCRResult') -> None:
        """Slot to handle the results of OCR processing."""
        self.tab_mgr.apply_ocr_result(result)

    def _open_readme(self) -> None:
        """Opens the README file."""
        try:
            readme_path = get_resource_path("README.md")
            if os.path.exists(readme_path):
                # Since it's .md, maybe open in browser or text editor
                webbrowser.open(readme_path)
            else:
                QMessageBox.critical(self, "Error", f"README file not found:\n{readme_path}")
        except Exception as e:
            self.logger.exception(f"README open error: {e}")
            QMessageBox.critical(self, "Error", f"Could not open README:\n{e}")

    def _post_init_setup(self) -> None:
        """Post-initialization setup."""
        self.events.setup_connections() 
        self.tab_mgr.update_tabs()
        self.ui.update_ui_mode()
        
        # Manually trigger update since initial signal might be missed
        self.events.on_profiles_updated()
        self.tab_mgr.apply_character_main_stats(force=True)
        
        check_and_alert_environment(self.gui_log)
        
        # Display any queued startup messages
        for title, message in self._startup_messages:
            QMessageBox.information(self, title, message)
        self._startup_messages.clear()
    
    def _open_dialog(self, dialog_class: type, dialog_name: str, *args: Any, **kwargs: Any) -> None:
        """Generic dialog opener with error handling."""
        try:
            dlg = dialog_class(self, *args, **kwargs)
            dlg.exec()
        except Exception as e:
            error_msg = f"Could not open {dialog_name}:\n{e}"
            QMessageBox.critical(self, "Error", error_msg)
            self.gui_log(f"{dialog_name} error: {e}")

    def open_char_settings_new(self) -> None:
        """Display the character settings dialog in New mode."""
        self._open_dialog(CharSettingDialog, "character settings", 
                         self.character_manager.register_character, profile=None)

    def open_char_settings_edit(self) -> None:
        """Display the character settings dialog in Edit mode."""
        if not self.character_var:
            QMessageBox.warning(self, self.tr("warning"), "No character selected to edit.")
            return
            
        profile = self.character_manager.get_character_profile(self.character_var)
        if not profile:
            QMessageBox.warning(self, self.tr("error"), f"Could not load data for '{self.character_var}'.")
            return
        
        self._open_dialog(CharSettingDialog, "character settings",
                         self.character_manager.register_character, profile=profile)

    def open_display_settings(self) -> None:
        """Display the display settings dialog."""
        self._open_dialog(DisplaySettingsDialog, "display settings")

    def open_image_preprocessing_settings(self) -> None:
        """Display the image preprocessing settings dialog."""
        self._open_dialog(ImagePreprocessingSettingsDialog, "image preprocessing settings")

    def open_history(self) -> None:
        """Display the history dialog."""
        self._open_dialog(HistoryDialog, "history", self.history_mgr)

    def update_background_image(self, new_path: str) -> None:
        """Update the background image."""
        self.theme_manager.update_background_image(new_path)

    def update_background_opacity(self, opacity: float) -> None:
        """Update the background opacity and re-apply theme."""
        self.theme_manager.update_background_opacity(opacity)

    def update_text_color(self, new_color: str) -> None:
        """Update the text color and re-apply theme."""
        self.theme_manager.update_text_color(new_color)

    def update_input_bg_color(self, new_color: str) -> None:
        """Update the custom background color for input fields."""
        self.theme_manager.update_input_bg_color(new_color)

    def cleanup_unused_images(self) -> None:
        """Scans the 'images' directory and deletes any images not currently in use."""
        self.theme_manager.cleanup_unused_images()

    def show_duplicate_entries(self) -> None:
        """
        全タブの完全一致重複個体を検出し、重複IDリストをログ出力する
        """
        entries = self.tab_mgr.get_all_echo_entries()
        dup_ids = self.tab_mgr.find_duplicate_entries(entries)
        if dup_ids:
            self.gui_log(f"重複個体検出: {dup_ids}")
        else:
            self.gui_log("重複個体はありません。")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = ScoreCalculatorApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        # Log the error before exiting
        logging.getLogger(__name__).critical(f"Critical unhandled exception during application startup: {e}", exc_info=True)
        QMessageBox.critical(None, "Fatal Error", f"An unhandled error occurred during application startup:\n{e}\n\nCheck the log file for more details.")
        sys.exit(1)
