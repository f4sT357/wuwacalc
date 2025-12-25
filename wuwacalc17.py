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
from managers.data_manager import DataManager
from ui.html_renderer import HtmlRenderer
from managers.history_manager import HistoryManager
from ui.ui_constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, RIGHT_TOP_HEIGHT,
    LOG_MIN_HEIGHT, LOG_DEFAULT_HEIGHT,
    IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT
)

# Tesseract setup
setup_tesseract()

class ScoreCalculatorApp(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        # 1. Basic properties
        self._startup_messages = []
        self._last_displayed_image_hash = None
        self._last_image_preview = None
        
        # 2. Logger setup
        # 2. Logger setup
        self.logger = logger
        self.logger.info("Initializing ScoreCalculatorApp...")

        # 3. Data & Config
        try:
            self.data_manager = DataManager(get_resource_path("data"))
            self.data_manager.load_all()
        except Exception as e:
            self.logger.critical(f"Failed to initialize DataManager: {e}")
            QMessageBox.critical(None, "Data Load Error", f"Critical game data could not be loaded.\nApp will close.\n\nError: {e}")
            sys.exit(1)

        self._init_config()
        self.character_manager = CharacterManager(self.logger, self.data_manager)
        self.history_mgr = HistoryManager()
        self.theme_manager = ThemeManager(self)
        self._init_vars()

        # 4. UI Framework (Create notebook here to ensure reference is valid)
        self.notebook = QTabWidget()
        self.ui = UIComponents(self)
        
        # 5. Logic Modules
        self.html_renderer = HtmlRenderer(
            self.tr, 
            self.language, 
            self.app_config.show_text_shadow, 
            self.app_config.text_shadow_color, 
            self.app_config.text_color,
            self.app_config.shadow_offset_x,
            self.app_config.shadow_offset_y,
            self.app_config.shadow_blur,
            self.app_config.shadow_spread
        )
        self.score_calc = ScoreCalculator(
            self.data_manager,
            self.character_manager,
            self.history_mgr,
            self.html_renderer,
            self.config_manager
        )
        self.tab_mgr = TabManager(
            self.notebook,
            self.data_manager,
            self.config_manager,
            self.tr,
            self.character_manager
        )
        self.logic = AppLogic(self.tr, self.data_manager, self.config_manager)
        self.image_proc = ImageProcessor(self.logic, self.config_manager)

        # 6. UI construction
        self.logger.info("Building UI components...")
        self.ui.create_main_layout()
        self.setCentralWidget(self.ui.main_widget)
        self.logger.info("UI layout created.")

        # 7. Event Handlers
        self.events = EventHandlers(
            self, self.ui, self.config_manager, self.data_manager,
            self.tab_mgr, self.theme_manager, self.character_manager, self.image_proc
        )

        # 8. Signal Connections
        self._setup_connections()
        
        # 9. Final UI setup
        self.setWindowTitle("Wuthering Waves Echo Score Calculator")
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.theme_manager.apply_theme(self.app_config.theme)
        if self.app_config.transparent_frames:
            self.theme_manager.update_frame_transparency(True)

        QTimer.singleShot(100, self._post_init_setup)
        self._setup_shortcuts()

    def _setup_connections(self) -> None:
        # Logic signals
        self.logic.log_message.connect(self.gui_log)
        self.logic.ocr_error.connect(self.show_ocr_error_message)
        self.logic.info_message.connect(self.show_info_message)

        # ScoreCalc signals
        self.score_calc.log_requested.connect(self.gui_log)
        self.score_calc.error_occurred.connect(self.show_error_message)
        self.score_calc.single_calculation_completed.connect(self.on_single_calc_completed)
        self.score_calc.batch_calculation_completed.connect(self.on_batch_calc_completed)

        # TabMgr signals
        self.tab_mgr.log_requested.connect(self.gui_log)
        self.tab_mgr.tabs_updated.connect(self.on_tabs_updated)

        # ImageProc signals
        self.image_proc.ocr_completed.connect(self.on_ocr_completed)
        self.image_proc.log_requested.connect(self.gui_log)
        self.image_proc.error_occurred.connect(self.show_error_message)
        self.image_proc.image_updated.connect(self.update_image_preview)
        self.image_proc.calculation_requested.connect(self.trigger_calculation)

        # UI signals
        self.notebook.currentChanged.connect(self.on_tab_changed)
        self.character_manager.profiles_updated.connect(self.events.on_profiles_updated)
        self.character_manager.character_registered.connect(self.events.on_character_registered)

        self.ui.config_combo.currentTextChanged.connect(self.events.on_config_change)
        self.ui.character_combo.currentIndexChanged.connect(self.events.on_character_change)
        self.ui.lang_combo.currentTextChanged.connect(self.events.on_language_change)
        self.ui.rb_manual.toggled.connect(lambda c: self.events.on_mode_change("manual") if c else None)
        self.ui.rb_ocr.toggled.connect(lambda c: self.events.on_mode_change("ocr") if c else None)
        self.ui.cb_auto_main.toggled.connect(self.events.on_auto_main_change)
        self.ui.rb_batch.toggled.connect(lambda c: self.events.on_score_mode_change("batch") if c else None)
        self.ui.rb_single.toggled.connect(lambda c: self.events.on_score_mode_change("single") if c else None)
        
        for method, cb in self.ui.method_checkboxes.items():
            cb.toggled.connect(self._on_method_toggled_wrapper)

    def _init_config(self) -> None:
        config_path = os.path.join(get_app_path(), CONFIG_FILENAME)
        self.config_manager = ConfigManager(config_path)
        self.config_manager.load()
        self.app_config = self.config_manager.get_app_config()
        ui_config = self.config_manager.get_ui_config()
        self.WINDOW_WIDTH = ui_config.window_width or WINDOW_WIDTH
        self.WINDOW_HEIGHT = ui_config.window_height or WINDOW_HEIGHT
        self.language = self.app_config.language

    def _init_vars(self) -> None:
        self.current_config_key = self.app_config.current_config_key
        self.mode_var = self.app_config.mode_var
        self.character_var = ""
        self.auto_apply_main_stats = self.app_config.auto_apply_main_stats
        self.score_mode_var = self.app_config.score_mode_var
        self.crop_mode_var = self.app_config.crop_mode
        self._updating_tabs = False
        self._waiting_for_character = False
        self._current_app_theme = self.app_config.theme
        self._frame_original_properties = {}

    def gui_log(self, message: str) -> None:
        if getattr(self, 'ui', None) and getattr(self.ui, 'log_text', None):
            self.ui.log_text.append(message)
        self.logger.info(message)

    def tr(self, key: str, *args: Any) -> str:
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["ja"]).get(key, key)
        return text.format(*args) if args else text

    def trigger_calculation(self) -> None:
        try:
            if not self.character_var:
                self._waiting_for_character = True
                self.ui.result_text.setHtml(f"<h3 style='color: orange;'>{self.tr('waiting_for_character')}</h3>")
                return
            self._waiting_for_character = False
            self.show_duplicate_entries()
            enabled_methods = self.app_config.enabled_calc_methods
            if self.score_mode_var == "single":
                tab_name = self.tab_mgr.get_selected_tab_name()
                entry = self.tab_mgr.extract_tab_data(tab_name)
                if entry: self.score_calc.calculate_single(self.character_var, tab_name, entry, enabled_methods)
            else:
                tabs_data = {n: self.tab_mgr.extract_tab_data(n) for n in self.tab_mgr.tabs_content.keys()}
                self.score_calc.calculate_batch(self.character_var, tabs_data, enabled_methods, self.language)
        except Exception as e: self.logger.exception(f"Calc error: {e}")

    def on_single_calc_completed(self, html: str, tab_name: str, evaluation: object) -> None:
        self.ui.result_text.setHtml(html)
        self.tab_mgr.save_tab_result(tab_name, html)

    def on_batch_calc_completed(self, html: str, character: str) -> None:
        self.ui.result_text.setHtml(html)

    def on_tabs_updated(self) -> None:
        self.ui.update_ui_mode()
        self.tab_mgr.apply_character_main_stats(force=True)
        self.theme_manager.refresh_global_shadows()

    def on_tab_changed(self, index: int) -> None:
        if index < 0 or self._updating_tabs: return
        tab_name = self.tab_mgr.get_selected_tab_name()
        if tab_name:
            self.show_tab_image(tab_name)
            self.show_tab_result(tab_name)

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

    def import_image(self) -> None:
        self.check_character_selected(quiet=True)
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("select_image_file"), "", f"{self.tr('image_files')} (*.png *.jpg *.jpeg *.bmp *.gif);;{self.tr('all_files')} (*.*)")
        if file_paths: self.image_proc.process_images_from_paths(file_paths)

    def paste_from_clipboard(self) -> None:
        self.check_character_selected(quiet=True)
        self.image_proc.paste_from_clipboard()

    def on_ocr_completed(self, result: object) -> None:
        from core.data_contracts import OCRResult, BatchItemResult
        
        # Check for character but don't block tab assignment
        has_char = self.check_character_selected()
        
        if isinstance(result, OCRResult):
            for msg in result.log_messages: self.gui_log(msg)
            
            # Find the best tab for this result (cost-based matching works without character)
            cost = result.cost
            main_stat = result.main_stat
            target_tab = self.tab_mgr.find_best_tab_match(cost, main_stat, self.character_var)
            
            if not target_tab:
                target_tab = self.tab_mgr.get_selected_tab_name()
            
            if target_tab:
                # Auto-switch to the target tab for better UX
                config_key = self.app_config.current_config_key
                tab_names = self.data_manager.tab_configs.get(config_key, [])
                if target_tab in tab_names:
                    idx = tab_names.index(target_tab)
                    self.notebook.setCurrentIndex(idx)
                
                self.gui_log(f"Applying OCR result to tab: {target_tab}")
                self.tab_mgr.apply_ocr_result_to_tab(target_tab, result)
                self.tab_mgr.save_tab_image(target_tab, result.original_image, result.cropped_image)
                
        elif isinstance(result, BatchItemResult):
            # Batch mode: Route to best matching tab
            cost = result.result.cost
            main_stat = result.result.main_stat
            
            target_tab = self.tab_mgr.find_best_tab_match(cost, main_stat, self.character_var)
            
            if not target_tab:
                target_tab = self.tab_mgr.get_selected_tab_name()
            
            if target_tab:
                self.gui_log(f"Applying batch result to tab: {target_tab} (Cost {cost}, Stat {main_stat})")
                self.tab_mgr.apply_ocr_result_to_tab(target_tab, result.result)
                self.tab_mgr.save_tab_image(target_tab, result.original_image, result.cropped_image)
            else:
                self.gui_log("Could not find a suitable tab for batch result.")

    def _on_method_toggled_wrapper(self) -> None:
        if self.events and self.ui:
            states = {m: cb.isChecked() for m, cb in self.ui.method_checkboxes.items()}
            self.events.on_calc_method_changed(states)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+V"), self).activated.connect(self.paste_from_clipboard)
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self.trigger_calculation)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.trigger_calculation)
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
        """Open the help.html file in default browser."""
        help_path = get_resource_path("help.html")
        if os.path.exists(help_path):
            try:
                os.startfile(help_path)
            except AttributeError:
                import webbrowser
                webbrowser.open(f"file:///{help_path}")
        else:
            # Fallback to README.md if help.html is missing
            readme_path = get_resource_path("README.md")
            try:
                os.startfile(readme_path)
            except AttributeError:
                import webbrowser
                webbrowser.open(f"file:///{readme_path}")

    def cycle_theme(self) -> None: self.events.cycle_theme()
    def on_auto_calculate_change(self, c: bool) -> None: self.events.on_auto_calculate_change(c)
    def on_crop_percent_change(self, t: str) -> None: self.events.on_crop_percent_change(t)
    def on_crop_slider_change(self, v: int) -> None: self.events.on_crop_slider_change(v)
    def open_char_settings_new(self) -> None: CharSettingDialog(self, self.character_manager.register_character).exec()
    def open_char_settings_edit(self) -> None:
        target_char = self.character_var
        
        if not target_char:
            # Determine display language for the list
            all_chars = self.character_manager.get_all_characters(self.language)
            if not all_chars:
                QMessageBox.information(self, self.tr("info"), self.tr("no_characters_found"))
                return

            items = [name for name, internal in all_chars]
            item, ok = QInputDialog.getItem(self, self.tr("select_character"), 
                                           self.tr("select_character_to_edit"), items, 0, False)
            if ok and item:
                # Find internal name for selected item
                for name, internal in all_chars:
                    if name == item:
                        target_char = internal
                        break
            else:
                return

        p = self.character_manager.get_character_profile(target_char)
        if p: CharSettingDialog(self, self.character_manager.register_character, profile=p).exec()

    def open_display_settings(self) -> None:
        DisplaySettingsDialog(self).exec()

    def open_history(self) -> None:
        HistoryDialog(self, self.history_mgr).exec()

    def open_image_preprocessing_settings(self) -> None:
        ImagePreprocessingSettingsDialog(self).exec()

    def refresh_results_display(self) -> None:
        """Refreshes the current HTML display and all stored tab results with latest styles."""
        import re
        new_style = self.html_renderer.common_style
        style_pattern = re.compile(r'<!-- STYLE_START -->.*?<!-- STYLE_END -->', re.DOTALL)

        # 1. Update current display
        current_html = self.ui.result_text.toHtml()
        if "<!-- STYLE_START -->" in current_html:
            updated_html = style_pattern.sub(new_style, current_html)
            self.ui.result_text.setHtml(updated_html)

        # 2. Update all stored results in TabManager
        for tab_name in self.tab_mgr._tab_results:
            old_html = self.tab_mgr.get_tab_result(tab_name)
            if old_html and "<!-- STYLE_START -->" in old_html:
                updated_tab_html = style_pattern.sub(new_style, old_html)
                self.tab_mgr.save_tab_result(tab_name, updated_tab_html)

    def update_shadow_params(self, ox: float, oy: float, blur: float, spread: float) -> None:
        """Update shadow parameters and refresh display."""
        self.app_config.shadow_offset_x = ox
        self.app_config.shadow_offset_y = oy
        self.app_config.shadow_blur = blur
        self.app_config.shadow_spread = spread
        self.html_renderer.set_shadow_params(ox, oy, blur, spread)
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_shadow_color(self, color: str) -> None:
        """Update shadow color and refresh display."""
        self.app_config.text_shadow_color = color
        self.html_renderer.set_shadow_color(color)
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_text_color(self, color: str) -> None:
        self.theme_manager.update_text_color(color)
        self.html_renderer.set_text_color(color)
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_background_image(self, path: str) -> None:
        self.theme_manager.update_background_image(path)
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_background_opacity(self, opacity: float) -> None:
        self.theme_manager.update_background_opacity(opacity)
        self.refresh_results_display()

    def apply_theme(self, theme_name: str) -> None:
        self.theme_manager.apply_theme(theme_name)
        # Sync text color to renderer if theme changes it
        self.html_renderer.set_text_color(self.app_config.text_color)
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