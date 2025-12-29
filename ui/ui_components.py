"""
UI Components Module (PySide6)
"""

from typing import Any, Optional, List, Tuple, Dict, Union
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QPushButton, QGroupBox, QTextEdit, QSplitter, 
    QComboBox, QCheckBox, QRadioButton, QSlider, QMenu, QLineEdit, QTabWidget, QGridLayout, QCompleter,
    QButtonGroup
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, Signal, QRect

from ui.ui_constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, RIGHT_TOP_HEIGHT,
    LOG_MIN_HEIGHT, LOG_DEFAULT_HEIGHT,
    IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT,
    VALUE_ENTRY_WIDTH
)
from core.data_contracts import OCRResult

# Internal UI Constants
VALUE_ENTRY_WIDTH = 60

class OCRImageLabel(QLabel):
    """Custom label for drawing OCR bounding boxes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_result = None
        self.original_crop_size = None # (width, height)
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.setText("No Image")

    def set_ocr_result(self, result, original_size=None):
        self.ocr_result = result
        if original_size:
            self.original_crop_size = original_size
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.ocr_result or not self.pixmap():
            return

        painter = QPainter(self)
        
        # Determine scaling and offsets relative to the displayed pixmap
        # QLabel centers the pixmap by default if alignment is centered
        pix_size = self.pixmap().size()
        lbl_size = self.size()
        
        # Calculate offsets to draw within the actual image area
        self.offset_x = (lbl_size.width() - pix_size.width()) // 2
        self.offset_y = (lbl_size.height() - pix_size.height()) // 2
        
        # Calculate scale factor
        if self.original_crop_size:
            # We assume the pixmap is scaled maintaining aspect ratio
            self.scale_factor = pix_size.width() / self.original_crop_size[0]
        else:
            self.scale_factor = 1.0
        
        # Draw Main Stat / Cost boxes
        pen_main = QPen(QColor(0, 255, 0, 180), 2)
        painter.setPen(pen_main)
        for key in ["main_stat", "cost"]:
            box = self.ocr_result.boxes.get(key)
            if box:
                self._draw_box(painter, box)

        # Draw Substat boxes
        pen_sub = QPen(QColor(0, 120, 255, 180), 2)
        painter.setPen(pen_sub)
        for sub in self.ocr_result.substats:
            if sub.box:
                self._draw_box(painter, sub.box)

    def _draw_box(self, painter, box):
        x, y, w, h = box
        # Scale to match displayed pixmap (heuristic scaling)
        # Note: In a robust impl, we'd pass the original cropped image size.
        # Here we approximate.
        painter.drawRect(
            int(x * self.scale_factor + self.offset_x),
            int(y * self.scale_factor + self.offset_y),
            int(w * self.scale_factor),
            int(h * self.scale_factor)
        )

class UIComponents:
    def __init__(self, app: 'ScoreCalculatorApp') -> None:
        self.app = app
        self.action_buttons = {}
        
        # Pre-initialize core widgets
        self.config_combo = QComboBox()
        self.character_combo = QComboBox()
        self.lang_combo = QComboBox()
        
        self.character_combo.setEditable(True)
        self.character_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.character_combo.completer():
            self.character_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        
        self.rb_manual = QRadioButton()
        self.rb_ocr = QRadioButton()
        self.cb_auto_main = QCheckBox()
        self.rb_batch = QRadioButton()
        self.rb_single = QRadioButton()
        
        self.method_checkboxes: Dict[str, QCheckBox] = {
            "normalized": QCheckBox(),
            "ratio": QCheckBox(),
            "roll": QCheckBox(),
            "effective": QCheckBox(),
            "cv": QCheckBox()
        }
        
        # Attribute holders for labels and other widgets that need retranslation
        self.lbl_cost_config = QLabel()
        self.lbl_character = QLabel()
        self.lbl_language = QLabel()
        self.lbl_input_mode = QLabel()
        self.lbl_calc_mode = QLabel()
        self.lbl_methods = QLabel()
        
        self.btn_load = QPushButton()
        self.btn_paste = QPushButton()
        self.btn_crop = QPushButton()
        self.cb_auto_calculate = QCheckBox()
        self.lbl_crop_mode = QLabel()
        self.rb_crop_drag = QRadioButton()
        self.rb_crop_percent = QRadioButton()
        
        self.crop_labels: Dict[str, QLabel] = {}
        
        # Attribute holders for app-side reference
        self.main_widget = None
        self.settings_group = None
        self.image_group = None
        self.result_group = None
        self.log_group = None

    def create_main_layout(self) -> None:
        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left
        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        self._setup_settings_ui(left_l)
        
        # Use existing notebook instance from app
        left_l.addWidget(self.app.notebook)
        
        self._setup_result_ui(left_l)
        splitter.addWidget(left_w)
        
        # Right
        right_w = QWidget()
        right_l = QVBoxLayout(right_w)
        self._setup_image_ui(right_l)
        self._setup_log_ui(right_l)
        splitter.addWidget(right_w)
        
        splitter.setSizes([WINDOW_WIDTH // 2, WINDOW_WIDTH // 2])

    def _setup_settings_ui(self, layout: QVBoxLayout) -> None:
        self.settings_group = QGroupBox(self.app.tr("basic_settings"))
        vbox = QVBoxLayout(self.settings_group)
        layout.addWidget(self.settings_group)

        grid = QGridLayout()
        vbox.addLayout(grid)

        self.lbl_cost_config.setText(self.app.tr("cost_config"))
        grid.addWidget(self.lbl_cost_config, 0, 0)
        self.config_combo.addItems(list(self.app.data_manager.tab_configs.keys()))
        self.config_combo.setCurrentText(self.app.current_config_key)
        grid.addWidget(self.config_combo, 0, 1)

        self.lbl_character.setText(self.app.tr("character"))
        grid.addWidget(self.lbl_character, 0, 2)
        grid.addWidget(self.character_combo, 0, 3)

        self.lbl_language.setText(self.app.tr("language"))
        grid.addWidget(self.lbl_language, 1, 0)
        self.lang_combo.addItems(["ja", "en", "zh"])
        self.lang_combo.setCurrentText(self.app.language)
        grid.addWidget(self.lang_combo, 1, 1)

        self.lbl_input_mode.setText(self.app.tr("input_mode"))
        grid.addWidget(self.lbl_input_mode, 1, 2)
        mode_h = QHBoxLayout()
        self.rb_manual.setText(self.app.tr("manual"))
        self.rb_manual.setToolTip(self.app.tr("tooltip_manual_mode"))
        self.rb_ocr.setText(self.app.tr("ocr"))
        self.rb_ocr.setToolTip(self.app.tr("tooltip_ocr_mode"))
        
        # Group Input Mode Radio Buttons
        self.grp_input_mode = QButtonGroup(self.main_widget)
        self.grp_input_mode.addButton(self.rb_manual)
        self.grp_input_mode.addButton(self.rb_ocr)
        
        if self.app.mode_var == "ocr": self.rb_ocr.setChecked(True)
        else: self.rb_manual.setChecked(True)
        mode_h.addWidget(self.rb_manual); mode_h.addWidget(self.rb_ocr)
        grid.addLayout(mode_h, 1, 3)

        self.cb_auto_main.setText(self.app.tr("auto_main"))
        self.cb_auto_main.setChecked(self.app.auto_apply_main_stats)
        grid.addWidget(self.cb_auto_main, 2, 0, 1, 2)

        self.lbl_calc_mode.setText(self.app.tr("calc_mode"))
        grid.addWidget(self.lbl_calc_mode, 2, 2)
        calc_h = QHBoxLayout()
        self.rb_batch.setText(self.app.tr("batch")); self.rb_single.setText(self.app.tr("single_only"))
        self.rb_batch.setToolTip(self.app.tr("tooltip_batch_mode"))
        self.rb_single.setToolTip(self.app.tr("tooltip_single_mode"))
        
        # Group Calc Mode Radio Buttons
        self.grp_calc_mode = QButtonGroup(self.main_widget)
        self.grp_calc_mode.addButton(self.rb_batch)
        self.grp_calc_mode.addButton(self.rb_single)
        
        if self.app.score_mode_var == "batch": self.rb_batch.setChecked(True)
        else: self.rb_single.setChecked(True)
        calc_h.addWidget(self.rb_batch); calc_h.addWidget(self.rb_single)
        grid.addLayout(calc_h, 2, 3)

        methods_h = QHBoxLayout()
        self.lbl_methods.setText(self.app.tr("methods_label"))
        methods_h.addWidget(self.lbl_methods)
        enabled = self.app.app_config.enabled_calc_methods
        for m, cb in self.method_checkboxes.items():
            cb.setText(self.app.tr(f"method_{m}"))
            cb.setChecked(enabled.get(m, True))
            methods_h.addWidget(cb)
        vbox.addLayout(methods_h)

        btn_h = QHBoxLayout()
        self._setup_action_buttons(btn_h)
        vbox.addLayout(btn_h)

    def _setup_action_buttons(self, layout: QHBoxLayout) -> None:
        self.action_buttons = {}
        # key, slot, tooltip_key
        buttons = [("calculate", self.app.events.trigger_calculation, "tooltip_calculate"),
                   ("set_equipped", self.app.set_current_as_equipped, "tooltip_set_equipped"),
                   ("export_txt", self.app.export_result_to_txt, "tooltip_export_txt"),
                   ("clear_all", self.app.clear_all, "tooltip_clear_all"),
                   ("clear_tab", self.app.clear_current_tab, "tooltip_clear_tab")]
        for k, cmd, tooltip_key in buttons:
            btn = QPushButton(self.app.tr(k))
            btn.clicked.connect(cmd)
            btn.setToolTip(self.app.tr(tooltip_key))
            layout.addWidget(btn)
            self.action_buttons[k] = (btn, tooltip_key)
        
        self.btn_char_setting = QPushButton(self.app.tr("char_setting"))
        self.btn_char_setting.setToolTip(self.app.tr("tooltip_char_setting"))
        menu = QMenu(self.btn_char_setting)
        menu.addAction(self.app.tr("new")).triggered.connect(self.app.events.open_char_settings_new)
        menu.addAction(self.app.tr("edit")).triggered.connect(self.app.events.open_char_settings_edit)
        self.btn_char_setting.setMenu(menu)
        layout.addWidget(self.btn_char_setting)
        
        self.btn_display_settings = QPushButton(self.app.tr("display_settings"))
        self.btn_display_settings.setToolTip(self.app.tr("tooltip_display_settings"))
        self.btn_display_settings.clicked.connect(self.app.events.open_display_settings)
        layout.addWidget(self.btn_display_settings)
        
        self.btn_history = QPushButton(self.app.tr("history"))
        self.btn_history.setToolTip(self.app.tr("tooltip_history"))
        self.btn_history.clicked.connect(self.app.events.open_history)
        layout.addWidget(self.btn_history)

        self.btn_preprocess_settings = QPushButton(self.app.tr("preprocess_settings"))
        self.btn_preprocess_settings.setToolTip(self.app.tr("tooltip_preprocess"))
        self.btn_preprocess_settings.clicked.connect(self.app.events.open_image_preprocessing_settings)
        layout.addWidget(self.btn_preprocess_settings)
        
        self.btn_help = QPushButton(self.app.tr("help"))
        self.btn_help.setToolTip(self.app.tr("tooltip_help"))
        self.btn_help.setFixedWidth(60)
        self.btn_help.clicked.connect(self.app._open_readme)
        layout.addWidget(self.btn_help)
        layout.addStretch()

    def _setup_image_ui(self, layout: QVBoxLayout) -> None:
        self.image_group = QGroupBox(self.app.tr("ocr_image"))
        vbox = QVBoxLayout(self.image_group)
        layout.addWidget(self.image_group)
        
        btn_h = QHBoxLayout()
        self.btn_load.setText(self.app.tr("load_image"))
        self.btn_load.setToolTip(self.app.tr("tooltip_load_image"))
        self.btn_load.clicked.connect(self.app.events.import_image)
        
        self.btn_paste.setText(self.app.tr("paste_clipboard"))
        self.btn_paste.setToolTip(self.app.tr("tooltip_paste"))
        self.btn_paste.clicked.connect(self.app.events.paste_from_clipboard)
        
        self.btn_crop.setText(self.app.tr("perform_crop"))
        self.btn_crop.setToolTip(self.app.tr("tooltip_crop"))
        self.btn_crop.clicked.connect(self.app.image_proc.perform_crop)
        
        self.cb_auto_calculate.setText(self.app.tr("auto_calculate"))
        self.cb_auto_calculate.setToolTip(self.app.tr("tooltip_auto_calculate"))
        self.cb_auto_calculate.setChecked(self.app.app_config.auto_calculate)
        self.cb_auto_calculate.toggled.connect(self.app.events.on_auto_calculate_change)
        
        btn_h.addWidget(self.btn_load); btn_h.addWidget(self.btn_paste); btn_h.addWidget(self.btn_crop); btn_h.addWidget(self.cb_auto_calculate)
        vbox.addLayout(btn_h)
        
        crop_h = QHBoxLayout()
        self.lbl_crop_mode.setText(self.app.tr("crop_mode"))
        crop_h.addWidget(self.lbl_crop_mode)
        self.rb_crop_drag.setText(self.app.tr("drag"))
        self.rb_crop_percent.setText(self.app.tr("percent"))
        
        # Group Crop Mode Radio Buttons
        self.grp_crop_mode = QButtonGroup(self.image_group)
        self.grp_crop_mode.addButton(self.rb_crop_drag)
        self.grp_crop_mode.addButton(self.rb_crop_percent)
        
        if self.app.crop_mode_var == "drag": self.rb_crop_drag.setChecked(True)
        else: self.rb_crop_percent.setChecked(True)
        self.rb_crop_drag.toggled.connect(lambda c: self.app.events.on_crop_mode_change("drag") if c else None)
        self.rb_crop_percent.toggled.connect(lambda c: self.app.events.on_crop_mode_change("percent") if c else None)
        crop_h.addWidget(self.rb_crop_drag); crop_h.addWidget(self.rb_crop_percent)
        
        self.entry_crop_l, self.slider_crop_l, lbl_l = self._create_crop_item(crop_h, self.app.tr("left_percent"), self.app.app_config.crop_left_percent, "slider_crop_l")
        self.entry_crop_t, self.slider_crop_t, lbl_t = self._create_crop_item(crop_h, self.app.tr("top_percent"), self.app.app_config.crop_top_percent, "slider_crop_t")
        self.entry_crop_w, self.slider_crop_w, lbl_w = self._create_crop_item(crop_h, self.app.tr("width_percent"), self.app.app_config.crop_width_percent, "slider_crop_w")
        self.entry_crop_h, self.slider_crop_h, lbl_h = self._create_crop_item(crop_h, self.app.tr("height_percent"), self.app.app_config.crop_height_percent, "slider_crop_h")
        self.crop_labels["L"] = lbl_l; self.crop_labels["T"] = lbl_t; self.crop_labels["W"] = lbl_w; self.crop_labels["H"] = lbl_h

        vbox.addLayout(crop_h)
        
        self.image_label = OCRImageLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(IMAGE_PREVIEW_MAX_HEIGHT)
        vbox.addWidget(self.image_label)

    def _create_crop_item(self, layout: QHBoxLayout, label_text: str, val: float, name: str) -> Tuple[QLineEdit, QSlider, QLabel]:
        vbox = QVBoxLayout()
        lbl = QLabel(label_text)
        vbox.addWidget(lbl)
        e = QLineEdit(str(val)); e.setFixedWidth(40); e.textChanged.connect(self.app.events.on_crop_percent_change)
        vbox.addWidget(e)
        s = QSlider(Qt.Orientation.Horizontal); s.setRange(0, 100); s.setValue(int(val)); s.setObjectName(name); s.valueChanged.connect(self.app.events.on_crop_slider_change)
        vbox.addWidget(s)
        layout.addLayout(vbox)
        return e, s, lbl

    def _setup_result_ui(self, layout: QVBoxLayout) -> None:
        self.result_group = QGroupBox(self.app.tr("calc_result"))
        l = QVBoxLayout(self.result_group)
        self.result_text = QTextEdit(); self.result_text.setReadOnly(True)
        l.addWidget(self.result_text)
        layout.addWidget(self.result_group)

    def _setup_log_ui(self, layout: QVBoxLayout) -> None:
        self.log_group = QGroupBox(self.app.tr("log"))
        l = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        l.addWidget(self.log_text)
        layout.addWidget(self.log_group)

    def retranslate_ui(self) -> None:
        self.settings_group.setTitle(self.app.tr("basic_settings"))
        self.lbl_cost_config.setText(self.app.tr("cost_config"))
        self.lbl_character.setText(self.app.tr("character"))
        self.lbl_language.setText(self.app.tr("language"))
        self.lbl_input_mode.setText(self.app.tr("input_mode"))
        self.rb_manual.setText(self.app.tr("manual")); self.rb_ocr.setText(self.app.tr("ocr"))
        self.rb_manual.setToolTip(self.app.tr("tooltip_manual_mode"))
        self.rb_ocr.setToolTip(self.app.tr("tooltip_ocr_mode"))
        self.cb_auto_main.setText(self.app.tr("auto_main"))
        self.lbl_calc_mode.setText(self.app.tr("calc_mode"))
        self.rb_batch.setText(self.app.tr("batch")); self.rb_single.setText(self.app.tr("single_only"))
        self.rb_batch.setToolTip(self.app.tr("tooltip_batch_mode"))
        self.rb_single.setToolTip(self.app.tr("tooltip_single_mode"))
        self.lbl_methods.setText(self.app.tr("methods_label"))
        for m, cb in self.method_checkboxes.items(): cb.setText(self.app.tr(f"method_{m}"))
        for k, (btn, tooltip_key) in self.action_buttons.items():
            btn.setText(self.app.tr(k))
            btn.setToolTip(self.app.tr(tooltip_key))
            
        self.btn_char_setting.setText(self.app.tr("char_setting"))
        self.btn_char_setting.setToolTip(self.app.tr("tooltip_char_setting"))
        self.btn_display_settings.setText(self.app.tr("display_settings"))
        self.btn_display_settings.setToolTip(self.app.tr("tooltip_display_settings"))
        self.btn_history.setText(self.app.tr("history"))
        self.btn_history.setToolTip(self.app.tr("tooltip_history"))
        self.btn_preprocess_settings.setText(self.app.tr("preprocess_settings"))
        self.btn_preprocess_settings.setToolTip(self.app.tr("tooltip_preprocess"))
        self.btn_help.setText(self.app.tr("help"))
        self.btn_help.setToolTip(self.app.tr("tooltip_help"))
        
        # Update character combo first item (placeholder)
        self.character_combo.setItemText(0, f"-- {self.app.tr('character')} --")
        
        self.result_group.setTitle(self.app.tr("calc_result"))
        self.log_group.setTitle(self.app.tr("log"))
        
        self.image_group.setTitle(self.app.tr("ocr_image"))
        self.btn_load.setText(self.app.tr("load_image"))
        self.btn_load.setToolTip(self.app.tr("tooltip_load_image"))
        self.btn_paste.setText(self.app.tr("paste_clipboard"))
        self.btn_paste.setToolTip(self.app.tr("tooltip_paste"))
        self.btn_crop.setText(self.app.tr("perform_crop"))
        self.btn_crop.setToolTip(self.app.tr("tooltip_crop"))
        self.cb_auto_calculate.setText(self.app.tr("auto_calculate"))
        self.cb_auto_calculate.setToolTip(self.app.tr("tooltip_auto_calculate"))
        self.lbl_crop_mode.setText(self.app.tr("crop_mode"))
        self.rb_crop_drag.setText(self.app.tr("drag"))
        self.rb_crop_percent.setText(self.app.tr("percent"))
        
        self.crop_labels["L"].setText(self.app.tr("left_percent"))
        self.crop_labels["T"].setText(self.app.tr("top_percent"))
        self.crop_labels["W"].setText(self.app.tr("width_percent"))
        self.crop_labels["H"].setText(self.app.tr("height_percent"))
        
        if not self.app.image_proc.loaded_image:
            self.image_label.setText(self.app.tr("no_image"))

    def display_ocr_overlay(self, result: OCRResult) -> None:
        """Displays bounding boxes on the current image preview."""
        if hasattr(self, 'image_label') and isinstance(self.image_label, OCRImageLabel):
            if self.image_label.pixmap():
                # Get the size of the CROPPED image used for OCR
                orig_size = None
                if self.app.image_proc.loaded_image:
                    orig_size = self.app.image_proc.loaded_image.size
                self.image_label.set_ocr_result(result, original_size=orig_size)

    def update_ui_mode(self) -> None:
        is_ocr = (self.app.mode_var == "ocr")
        is_p = (self.app.crop_mode_var == "percent")
        for attr in ['entry_crop_l', 'slider_crop_l', 'entry_crop_t', 'slider_crop_t', 'entry_crop_w', 'slider_crop_w', 'entry_crop_h', 'slider_crop_h']:
            w = getattr(self, attr, None)
            if w: w.setEnabled(is_ocr and is_p)

    def filter_characters_by_config(self) -> None:
        key = getattr(self.app, 'current_config_key', "")
        profiles = self.app.character_manager.get_character_list_by_config(key)
        if not profiles: profiles = self.app.character_manager.get_all_characters(self.app.language)
        self.update_character_combo(profiles, self.app.character_var)

    def update_character_combo(self, profiles: List[Any], current: str = "") -> None:
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        
        lang = self.app.language
        formatted = []
        for p in profiles:
            if isinstance(p, dict):
                jp = p.get('name_jp', '')
                en = p.get('name_en', '')
                display_name = en if lang == 'en' else jp
                formatted.append((display_name, en))
            elif isinstance(p, tuple):
                # (display_name, internal_name)
                formatted.append(p)
        
        # Sort by display name
        formatted.sort(key=lambda x: x[0])
        
        self.character_combo.addItem(f"-- {self.app.tr('character')} --", userData="")
        for display_name, internal_name in formatted:
            self.character_combo.addItem(display_name, userData=internal_name)
        
        idx = self.character_combo.findData(current)
        if idx >= 0:
            self.character_combo.setCurrentIndex(idx)
        else:
            self.character_combo.setCurrentIndex(0)
            
        if self.character_combo.currentIndex() <= 0:
            self.character_combo.setEditText("")
            
        self.character_combo.blockSignals(False)
        self.app.logger.info(f"Populated character combo with {len(formatted)} items in {lang}.")
