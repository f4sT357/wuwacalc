import logging
import os
import sys
import webbrowser
import hashlib

from typing import Any, Callable, Optional, List, Tuple, Dict, Union

from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QComboBox, QStatusBar, QFileDialog, QTabWidget, QInputDialog)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QShortcut, QKeySequence, QPixmap

try:
    from PIL import Image, ImageQt
    is_pil_installed = True
except ImportError:
    is_pil_installed = False

from managers.config_manager import ConfigManager
from utils.constants import (
    LOG_FILENAME,
    CONFIG_FILENAME,
    DIR_DATA,
)
from utils.logger import logger
from ui.dialogs import CharSettingDialog, DisplaySettingsDialog, ImagePreprocessingSettingsDialog, CropDialog, HistoryDialog
from utils.languages import TRANSLATIONS
from utils.utils import get_app_path, get_resource_path, setup_tesseract, check_and_alert_environment
from managers.character_manager import CharacterManager

from managers.theme_manager import ThemeManager
from core.score_calculator import ScoreCalculator
from managers.tab_manager import TabManager
from ui.event_handlers import EventHandlers
from ui.ui_components import UIComponents
from core.image_processor import ImageProcessor
from core.app_logic import AppLogic
from core.app_setup import AppContext
from ui.ui_constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT
)

# Tesseract setup
setup_tesseract()

class ScoreCalculatorApp(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        # 1. Properties
        self._startup_messages = []
        self._last_displayed_image_hash = None
        self._last_image_preview = None
        self._updating_tabs = False
        self._waiting_for_character = False
        
        # 2. Setup Context
        self.ctx = AppContext(self)
        self.logger = self.ctx.logger
        self.logger.info("Initializing ScoreCalculatorApp...")

        # 3. Reference mapping (for convenience and backward compatibility)
        self.data_manager = self.ctx.data_manager
        self.config_manager = self.ctx.config_manager
        self.app_config = self.ctx.app_config
        self.character_manager = self.ctx.character_manager
        self.history_mgr = self.ctx.history_mgr
        self.theme_manager = self.ctx.theme_manager
        self.notebook = self.ctx.notebook
        self.ui = self.ctx.ui
        self.html_renderer = self.ctx.html_renderer
        self.score_calc = self.ctx.score_calc
        self.tab_mgr = self.ctx.tab_mgr
        self.logic = self.ctx.logic
        self.image_proc = self.ctx.image_proc

        # 4. Initialize Variables
        self._init_app_vars()

        # 5. Event Handlers
        self.events = EventHandlers(self, self.ctx)

        # 6. UI construction
        self.logger.info("Building UI components...")
        self.ui.create_main_layout()
        self.setCentralWidget(self.ui.main_widget)
        self.logger.info("UI layout created.")

        # 7. Signal Connections
        self.events.setup_connections()
        
        # 8. Final UI setup
        self.setWindowTitle("Wuthering Waves Echo Score Calculator")
        ui_config = self.config_manager.get_ui_config()
        self.resize(ui_config.window_width or WINDOW_WIDTH, ui_config.window_height or WINDOW_HEIGHT)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.theme_manager.apply_theme(self.app_config.theme)
        if self.app_config.transparent_frames:
            self.theme_manager.update_frame_transparency(True)

        QTimer.singleShot(100, self._post_init_setup)
        self._setup_shortcuts()

    def _init_app_vars(self) -> None:
        self.language = self.app_config.language
        self.current_config_key = self.app_config.current_config_key
        self.mode_var = self.app_config.mode_var
        self.character_var = ""
        self.auto_apply_main_stats = self.app_config.auto_apply_main_stats
        self.score_mode_var = self.app_config.score_mode_var
        self.crop_mode_var = self.app_config.crop_mode
        self._current_app_theme = self.app_config.theme

    def gui_log(self, message: str) -> None:
        if getattr(self, 'ui', None) and getattr(self.ui, 'log_text', None):
            self.ui.log_text.append(message)
        self.logger.info(message)

    def tr(self, key: str, *args: Any) -> str:
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["ja"]).get(key, key)
        return text.format(*args) if args else text

    def trigger_calculation(self) -> None:
        self.events.trigger_calculation()

    def on_single_calc_completed(self, html: str, tab_name: str, evaluation: object) -> None:
        self.ui.result_text.setHtml(html)
        self.tab_mgr.save_tab_result(tab_name, html)

    def on_batch_calc_completed(self, html: str, character: str) -> None:
        self.ui.result_text.setHtml(html)

    def on_tabs_updated(self) -> None:
        self.ui.update_ui_mode()
        self.tab_mgr.apply_character_main_stats(force=True)
        self.theme_manager.refresh_global_shadows()

    def show_tab_image(self, tab_name: str) -> None:
        data = self.tab_mgr.get_tab_image(tab_name)
        if data: self.update_image_preview(data.cropped)

    def show_tab_result(self, tab_name: str) -> None:
        html = self.tab_mgr.get_tab_result(tab_name)
        if html: self.ui.result_text.setHtml(html)
        else: self.ui.result_text.clear()

    def check_character_selected(self, quiet: bool = False) -> bool:
        """Checks if a character is selected. If not, sets waiting state."""
        if not self.character_var:
            if not quiet:
                self.ui.result_text.setHtml(f"<h3 style='color: orange;'>{self.tr('waiting_for_character')}</h3>")
            self._waiting_for_character = True
            return False
        return True

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self.events.paste_from_clipboard)
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self.events.trigger_calculation)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.events.trigger_calculation)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.export_result_to_txt)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.clear_all)

    def set_current_as_equipped(self) -> None:
        """Saves the current tab's data as the equipped echo for this character."""
        if not self.character_var:
            QMessageBox.warning(self, self.tr("warning"), self.tr("waiting_for_character"))
            return
            
        tab_name = self.tab_mgr.get_selected_tab_name()
        if not tab_name:
            return
            
        entry = self.tab_mgr.extract_tab_data(tab_name)
        if not entry or not entry.main_stat:
            QMessageBox.warning(self, self.tr("warning"), self.tr("main_stat_missing", tab_name))
            return
            
        self.character_manager.save_equipped_echo(self.character_var, tab_name, entry)
        self.gui_log(f"Set as Equipped: {self.character_var} - {tab_name}")
        QMessageBox.information(self, self.tr("info"), self.tr("save_msg", tab_name))
        
        # Re-trigger calculation to show the updated comparison (0.00%)
        self.trigger_calculation()

    def export_result_to_txt(self) -> None:
        if self.tab_mgr: self.tab_mgr.export_to_txt(self, self.ui.result_text.toPlainText())

    def clear_all(self) -> None:
        if self.tab_mgr:
            self.tab_mgr.clear_all()
            self.ui.result_text.clear()
            self.update_image_preview(None)

    def clear_current_tab(self) -> None:
        if self.tab_mgr:
            self.tab_mgr.clear_current_tab()
            self.ui.result_text.clear()

    def update_image_preview(self, image: Optional['Image.Image']) -> None:
        ui = getattr(self, 'ui', None)
        lbl = getattr(ui, 'image_label', None)
        
        if not is_pil_installed or lbl is None or image is None:
            if lbl: 
                lbl.setText(self.tr("no_image"))
                lbl.setPixmap(QPixmap())
            return
        qim = ImageQt.ImageQt(image)
        pixmap = QPixmap.fromImage(qim)
        scaled = pixmap.scaled(IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(scaled)

    def _post_init_setup(self) -> None:
        self.events.setup_connections()
        self.tab_mgr.update_tabs()
        self.events.on_profiles_updated()
        self.theme_manager.refresh_global_shadows()
        check_and_alert_environment(self.gui_log)

    def show_duplicate_entries(self) -> None:
        entries = self.tab_mgr.get_all_echo_entries()
        dup_ids = self.tab_mgr.find_duplicate_entries(entries)
        if dup_ids: self.gui_log(f"Duplicate detected: {dup_ids}")

    def show_ocr_error_message(self, title: str, message: str) -> None: QMessageBox.critical(self, title, message)
    def show_error_message(self, title: str, message: str) -> None: QMessageBox.critical(self, title, message)
    def show_info_message(self, title: str, message: str) -> None: QMessageBox.information(self, title, message)
    
    def _open_readme(self) -> None:
        """Refreshes the current HTML display and all stored tab results with latest styles."""
        import re
        new_style = self.html_renderer.common_style
        style_pattern = re.compile(r'<!-- STYLE_START -->.*?<!-- STYLE_END -->', re.DOTALL)
        current_html = self.ui.result_text.toHtml()
        if "<!-- STYLE_START -->" in current_html:
            self.ui.result_text.setHtml(style_pattern.sub(new_style, current_html))
        for tab_name, old_html in self.tab_mgr._tab_results.items():
            if old_html.content and "<!-- STYLE_START -->" in old_html.content:
                updated_tab_html = style_pattern.sub(new_style, old_html.content)
                self.tab_mgr.save_tab_result(tab_name, updated_tab_html)

    def update_shadow_params(self, ox: float, oy: float, blur: float, spread: float) -> None:
        self.app_config.shadow_offset_x, self.app_config.shadow_offset_y = ox, oy
        self.app_config.shadow_blur, self.app_config.shadow_spread = blur, spread
        self.html_renderer.set_shadow_params(ox, oy, blur, spread)
        self._refresh_ui_styles()

    def update_shadow_color(self, color: str) -> None:
        self.app_config.text_shadow_color = color
        self.html_renderer.set_shadow_color(color)
        self._refresh_ui_styles()

    def update_text_color(self, color: str) -> None:
        self.theme_manager.update_text_color(color)
        self.html_renderer.set_text_color(color)
        self._refresh_ui_styles()

    def update_background_image(self, path: str) -> None:
        self.theme_manager.update_background_image(path)
        self._refresh_ui_styles()

    def update_background_opacity(self, opacity: float) -> None:
        self.theme_manager.update_background_opacity(opacity)
        self.refresh_results_display()

    def apply_theme(self, theme_name: str) -> None:
        self.theme_manager.apply_theme(theme_name)
        self.html_renderer.set_text_color(self.app_config.text_color)
        self._refresh_ui_styles()

    def refresh_results_display(self) -> None:
        """Refreshes the current tab's result and image preview."""
        tab_name = self.tab_mgr.get_selected_tab_name()
        if tab_name:
            self.show_tab_result(tab_name)
            self.show_tab_image(tab_name)

    def _refresh_ui_styles(self) -> None:
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_input_bg_color(self, color: str) -> None:
        self.theme_manager.update_input_bg_color(color)

    def update_app_font(self, font: str) -> None:
        self.theme_manager.update_app_font(font)
        self.refresh_results_display()

    def update_frame_transparency(self, transparent: bool) -> None:
        self.theme_manager.update_frame_transparency(transparent)

    def cleanup_unused_images(self) -> None:
        self.theme_manager.cleanup_unused_images()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScoreCalculatorApp()
    window.show()
    sys.exit(app.exec())