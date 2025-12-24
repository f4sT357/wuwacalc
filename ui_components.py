from typing import Union, Tuple, Optional, TYPE_CHECKING
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QScrollArea, QTextEdit, QLabel, QPushButton, QComboBox, QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QSplitter, QFrame, QSizePolicy, QLineEdit, QSlider, QMenu
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from ui_constants import (
    RIGHT_TOP_HEIGHT, LOG_MIN_HEIGHT, LOG_DEFAULT_HEIGHT,
    VALUE_ENTRY_WIDTH, CROP_ENTRY_WIDTH, NUM_SUBSTATS
)

if TYPE_CHECKING:
    from wuwacalc17 import ScoreCalculatorApp


class SettingsPanel:
    """Class responsible for the settings UI (Settings Frame)."""
    def __init__(self, app: 'ScoreCalculatorApp', ui: 'UIComponents'):
        self.app = app
        self.ui = ui # Back reference if needed, though app should suffice
        self.settings_group: Optional[QGroupBox] = None
        
        # Widgets
        self.character_combo = QComboBox()
        self.character_combo.setEditable(True)
        self.character_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.character_combo.lineEdit().setPlaceholderText(self.app.tr("search_character_placeholder"))
        self.character_combo.setObjectName("CharComboBox")
        
        self.mode_button_group = QButtonGroup(self.app)
        self.calc_mode_button_group = QButtonGroup(self.app)
        
        # Other widgets will be created in setup_ui methods
        self.lbl_cost_config: Optional[QLabel] = None
        self.lbl_character: Optional[QLabel] = None
        self.lbl_language: Optional[QLabel] = None
        self.lang_combo: Optional[QComboBox] = None
        
        self.lbl_input_mode: Optional[QLabel] = None
        self.rb_manual: Optional[QRadioButton] = None
        self.rb_ocr: Optional[QRadioButton] = None
        self.cb_auto_main: Optional[QCheckBox] = None
        
        self.lbl_calc_mode: Optional[QLabel] = None
        self.rb_batch: Optional[QRadioButton] = None
        self.rb_single: Optional[QRadioButton] = None
        
        self.lbl_calc_methods: Optional[QLabel] = None
        self.cb_method_normalized: Optional[QCheckBox] = None
        self.cb_method_ratio: Optional[QCheckBox] = None
        self.cb_method_roll: Optional[QCheckBox] = None
        self.cb_method_effective: Optional[QCheckBox] = None
        self.cb_method_cv: Optional[QCheckBox] = None

    def setup_ui(self, parent_layout: QVBoxLayout) -> None:
        self.settings_group = QGroupBox(self.app.tr("basic_settings"))
        settings_layout = QGridLayout(self.settings_group)
        parent_layout.addWidget(self.settings_group)
        
        self._setup_basic_settings_row(settings_layout)
        self._setup_input_mode_row(settings_layout)
        self._setup_calc_mode_row(settings_layout)
        self._setup_calc_methods_row(settings_layout)

    def _setup_basic_settings_row(self, layout: QGridLayout) -> None:
        self.lbl_cost_config = QLabel(self.app.tr("cost_config"))
        layout.addWidget(self.lbl_cost_config, 0, 0)
        
        self.app.config_combo = QComboBox()
        self.app.config_combo.addItems(list(self.app.data_manager.tab_configs.keys()))
        self.app.config_combo.blockSignals(True)
        self.app.config_combo.setCurrentText(self.app.current_config_key)
        self.app.config_combo.blockSignals(False)
        self.app.config_combo.currentTextChanged.connect(self.app.events.on_config_change)
        layout.addWidget(self.app.config_combo, 0, 1)
        
        self.lbl_character = QLabel(self.app.tr("character"))
        layout.addWidget(self.lbl_character, 0, 2)
        self.character_combo.activated.connect(self.app.events.on_character_change)
        layout.addWidget(self.character_combo, 0, 3)
        
        self.lbl_language = QLabel(self.app.tr("language"))
        layout.addWidget(self.lbl_language, 0, 4)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ja", "en"])
        self.lang_combo.setCurrentText(self.app.language)
        self.lang_combo.currentTextChanged.connect(self.app.events.on_language_change)
        layout.addWidget(self.lang_combo, 0, 5)

    def _setup_input_mode_row(self, layout: QGridLayout) -> None:
        self.lbl_input_mode = QLabel(self.app.tr("input_mode"))
        layout.addWidget(self.lbl_input_mode, 1, 0)
        mode_layout = QHBoxLayout()
        
        self.rb_manual = QRadioButton(self.app.tr("manual"))
        self.rb_ocr = QRadioButton(self.app.tr("ocr"))
        
        mode_layout.addWidget(self.rb_manual)
        mode_layout.addWidget(self.rb_ocr)
        
        self.mode_button_group.addButton(self.rb_manual)
        self.mode_button_group.addButton(self.rb_ocr)
        
        if self.app.mode_var == "manual":
            self.rb_manual.setChecked(True)
        else:
            self.rb_ocr.setChecked(True)
            
        self.rb_manual.toggled.connect(self.app.events.on_mode_manual_toggled)
        self.rb_ocr.toggled.connect(self.app.events.on_mode_ocr_toggled)
        
        layout.addLayout(mode_layout, 1, 1, 1, 3)
        
        self.cb_auto_main = QCheckBox(self.app.tr("auto_main"))
        self.cb_auto_main.setChecked(self.app.auto_apply_main_stats)
        self.cb_auto_main.toggled.connect(self.app.events.on_auto_main_change)
        layout.addWidget(self.cb_auto_main, 1, 4, 1, 2)

    def _setup_calc_mode_row(self, layout: QGridLayout) -> None:
        self.lbl_calc_mode = QLabel(self.app.tr("calc_mode"))
        layout.addWidget(self.lbl_calc_mode, 2, 0)
        calc_mode_layout = QHBoxLayout()
        self.rb_batch = QRadioButton(self.app.tr("batch"))
        self.rb_single = QRadioButton(self.app.tr("single_only"))
        
        if self.app.score_mode_var == "batch":
            self.rb_batch.setChecked(True)
        else:
            self.rb_single.setChecked(True)
            
        self.rb_batch.toggled.connect(self.app.events.on_score_mode_batch_toggled)
        self.rb_single.toggled.connect(self.app.events.on_score_mode_single_toggled)
        
        calc_mode_layout.addWidget(self.rb_batch)
        calc_mode_layout.addWidget(self.rb_single)
        
        self.calc_mode_button_group.addButton(self.rb_batch)
        self.calc_mode_button_group.addButton(self.rb_single)
        layout.addLayout(calc_mode_layout, 2, 1, 1, 3)

    def _setup_calc_methods_row(self, layout: QGridLayout) -> None:
        self.lbl_calc_methods = QLabel(self.app.tr("calc_methods"))
        layout.addWidget(self.lbl_calc_methods, 3, 0)
        
        methods_layout = QHBoxLayout()
        
        self.cb_method_normalized = QCheckBox(self.app.tr("method_normalized"))
        self.cb_method_ratio = QCheckBox(self.app.tr("method_ratio"))
        self.cb_method_roll = QCheckBox(self.app.tr("method_roll"))
        self.cb_method_effective = QCheckBox(self.app.tr("method_effective"))
        self.cb_method_cv = QCheckBox(self.app.tr("method_cv"))

        self.cb_method_normalized.setToolTip(self.app.tr("normalized_score_desc"))
        self.cb_method_ratio.setToolTip(self.app.tr("ratio_score_desc"))
        self.cb_method_roll.setToolTip(self.app.tr("roll_quality_desc"))
        self.cb_method_effective.setToolTip(self.app.tr("effective_stat_desc"))
        self.cb_method_cv.setToolTip(self.app.tr("cv_score_desc"))
        
        enabled_methods = self.app.app_config.enabled_calc_methods
        self.cb_method_normalized.setChecked(enabled_methods.get("normalized", True))
        self.cb_method_ratio.setChecked(enabled_methods.get("ratio", True))
        self.cb_method_roll.setChecked(enabled_methods.get("roll", True))
        self.cb_method_effective.setChecked(enabled_methods.get("effective", True))
        self.cb_method_cv.setChecked(enabled_methods.get("cv", True))
        
        self.cb_method_normalized.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.cb_method_ratio.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.cb_method_roll.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.cb_method_effective.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.cb_method_cv.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        
        methods_layout.addWidget(self.cb_method_normalized)
        methods_layout.addWidget(self.cb_method_ratio)
        methods_layout.addWidget(self.cb_method_roll)
        methods_layout.addWidget(self.cb_method_effective)
        methods_layout.addWidget(self.cb_method_cv)
        methods_layout.addStretch()
        
        layout.addLayout(methods_layout, 3, 1, 1, 5)

    def retranslate_ui(self) -> None:
        self.settings_group.setTitle(self.app.tr("basic_settings"))
        self.lbl_cost_config.setText(self.app.tr("cost_config"))
        self.lbl_character.setText(self.app.tr("character"))
        self.lbl_language.setText(self.app.tr("language"))
        self.character_combo.lineEdit().setPlaceholderText(self.app.tr("search_character_placeholder"))
        
        self.lbl_input_mode.setText(self.app.tr("input_mode"))
        self.rb_manual.setText(self.app.tr("manual"))
        self.rb_ocr.setText(self.app.tr("ocr"))
        self.cb_auto_main.setText(self.app.tr("auto_main"))
        
        self.lbl_calc_mode.setText(self.app.tr("calc_mode"))
        self.rb_batch.setText(self.app.tr("batch"))
        self.rb_single.setText(self.app.tr("single_only"))
        
        self.lbl_calc_methods.setText(self.app.tr("calc_methods"))
        self.cb_method_normalized.setText(self.app.tr("method_normalized"))
        self.cb_method_ratio.setText(self.app.tr("method_ratio"))
        self.cb_method_roll.setText(self.app.tr("method_roll"))
        self.cb_method_effective.setText(self.app.tr("method_effective"))
        self.cb_method_cv.setText(self.app.tr("method_cv"))
        
        self.cb_method_normalized.setToolTip(self.app.tr("normalized_score_desc"))
        self.cb_method_ratio.setToolTip(self.app.tr("ratio_score_desc"))
        self.cb_method_roll.setToolTip(self.app.tr("roll_quality_desc"))
        self.cb_method_effective.setToolTip(self.app.tr("effective_stat_desc"))
        self.cb_method_cv.setToolTip(self.app.tr("cv_score_desc"))


class UIComponents:
    """Class responsible for UI construction."""
    
    def __init__(self, app: 'ScoreCalculatorApp'):
        """
        Initialization
        
        Args:
            app: The main application instance.
        """
        self.app = app
        self.main_widget: Optional[QWidget] = None
        
        self.settings_panel = SettingsPanel(app, self)

        # self.character_combo etc are now in settings_panel
        # We need to maintain _all_char_items for filtering logic which stays here (or moves to SettingsPanel?
        # Let's move filtering logic to SettingsPanel later, but for now access via property
        self._all_char_items: list[tuple[str, str]] = [] 
        self._is_filtering = False

    # Properties to maintain backward compatibility
    @property
    def character_combo(self): return self.settings_panel.character_combo
    @property
    def mode_button_group(self): return self.settings_panel.mode_button_group
    @property
    def calc_mode_button_group(self): return self.settings_panel.calc_mode_button_group
    @property
    def settings_group(self): return self.settings_panel.settings_group
    @property
    def lbl_cost_config(self): return self.settings_panel.lbl_cost_config
    @property
    def lbl_character(self): return self.settings_panel.lbl_character
    @property
    def lbl_language(self): return self.settings_panel.lbl_language
    @property
    def lang_combo(self): return self.settings_panel.lang_combo
    @property
    def lbl_input_mode(self): return self.settings_panel.lbl_input_mode
    @property
    def rb_manual(self): return self.settings_panel.rb_manual
    @property
    def rb_ocr(self): return self.settings_panel.rb_ocr
    @property
    def cb_auto_main(self): return self.settings_panel.cb_auto_main
    @property
    def lbl_calc_mode(self): return self.settings_panel.lbl_calc_mode
    @property
    def rb_batch(self): return self.settings_panel.rb_batch
    @property
    def rb_single(self): return self.settings_panel.rb_single
    @property
    def lbl_calc_methods(self): return self.settings_panel.lbl_calc_methods
    @property
    def cb_method_normalized(self): return self.settings_panel.cb_method_normalized
    @property
    def cb_method_ratio(self): return self.settings_panel.cb_method_ratio
    @property
    def cb_method_roll(self): return self.settings_panel.cb_method_roll
    @property
    def cb_method_effective(self): return self.settings_panel.cb_method_effective
    @property
    def cb_method_cv(self): return self.settings_panel.cb_method_cv

    
    def _filter_character_combo(self, text: str) -> None:
        """Filter the character combobox items based on input text."""
        if self._is_filtering:
            return
            
        self._is_filtering = True
        self.character_combo.blockSignals(True)
        
        try:
            search_text = text.lower()
            filtered_items = [
                (disp, internal) for disp, internal in self._all_char_items 
                if search_text in disp.lower() or search_text in internal.lower()
            ]
            
            self.character_combo.clear()
            
            if not filtered_items:
                if text: # Only show "Not found" if there's actually search text
                    self.character_combo.addItem(self.app.tr("no_matching_characters"), userData="")
            else:
                # Add a blank option at the top if not searching or if search is empty
                if not text:
                    self.character_combo.addItem("", userData="")
                
                for disp, internal in filtered_items:
                    self.character_combo.addItem(disp, userData=internal)
            
            # Restore the cursor position in the line edit
            self.character_combo.lineEdit().setText(text)
            
            # Show the popup only if there's search text or if we want to show the full list
            if text:
                self.character_combo.showPopup()
            else:
                self.character_combo.hidePopup()
            
        finally:
            self.character_combo.blockSignals(False)
            self._is_filtering = False

    def create_main_layout(self) -> None:
        """Create the main window's entire UI."""
        self.main_widget = QWidget()
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Main Splitter (Left: Settings/Tabs, Right: Image/Log/Result)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left Container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.create_left_pane(left_layout)
        self.main_splitter.addWidget(left_container)
        
        # Right Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.create_right_pane(right_layout)
        self.main_splitter.addWidget(right_container)
        
        # Set initial sizes (approximate)
        self.main_splitter.setSizes([500, 400])
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

    def create_left_pane(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the left pane (settings/input)."""
        self.settings_panel.setup_ui(parent_layout)
        self.create_buttons_frame(parent_layout)
        
        # Tabs
        self.app.notebook = QTabWidget()
        self.app.notebook.blockSignals(True) # Block signals during initial setup
        self.app.notebook.currentChanged.connect(self.app.events.on_tab_changed)
        self.app.notebook.blockSignals(False) # Unblock signals after setup
        parent_layout.addWidget(self.app.notebook)
        
        self.create_result_frame(parent_layout)
    


    def create_buttons_frame(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the button area."""
        self.app.button_frame = QFrame()
        btn_layout = QHBoxLayout(self.app.button_frame)
        btn_layout.setContentsMargins(0, 5, 0, 5)
        parent_layout.addWidget(self.app.button_frame)
        
        # Decompose into individual button group setups
        self._add_action_buttons(btn_layout)
        self._add_char_setting_button(btn_layout)
        self._add_app_utility_buttons(btn_layout)
        
        btn_layout.addStretch() # Push buttons to left

    def _add_action_buttons(self, layout: QHBoxLayout) -> None:
        """Add main action buttons: Calculate, Export, Clear."""
        self.action_buttons = {}
        buttons = [
            ("calculate", self.app.score_calc.calculate_all_scores, " (Ctrl+Enter / F5)"),
            ("export_txt", self.app.tab_mgr.export_result_to_txt, " (Ctrl+S)"),
            ("clear_all", self.app.tab_mgr.clear_all, " (Ctrl+R)"),
            ("clear_tab", self.app.tab_mgr.clear_current_tab, "")
        ]
        for key, command, shortcut_text in buttons:
            btn = QPushButton(self.app.tr(key))
            btn.clicked.connect(command)
            btn.setToolTip(self.app.tr(key) + shortcut_text)
            layout.addWidget(btn)
            self.action_buttons[key] = (btn, shortcut_text)

    def _add_char_setting_button(self, layout: QHBoxLayout) -> None:
        """Add Character Setting button with its dropdown menu."""
        self.btn_char_setting = QPushButton(self.app.tr("char_setting"))
        self.char_menu = QMenu(self.btn_char_setting)
        
        # New Action
        self.action_new = self.char_menu.addAction(self.app.tr("new"))
        if self.action_new.text() == "new": # Fallback
            self.action_new.setText(self.app.tr("char_setting") + " (New)")
        self.action_new.triggered.connect(self.app.open_char_settings_new)

        # Edit Action
        self.action_edit = self.char_menu.addAction(self.app.tr("edit"))
        if self.action_edit.text() == "edit": # Fallback
            self.action_edit.setText(self.app.tr("char_setting") + " (Edit)")
        self.action_edit.triggered.connect(self.app.open_char_settings_edit)
        
        self.btn_char_setting.setMenu(self.char_menu)
        layout.addWidget(self.btn_char_setting)

    def _add_app_utility_buttons(self, layout: QHBoxLayout) -> None:
        """Add utility buttons: Help, Settings, Test Mode, History."""
        self.utility_buttons = {}
        buttons_others = [
            ("help", self.app._open_readme),
            ("display_settings", self.app.open_display_settings),
            ("image_preprocessing", self.app.open_image_preprocessing_settings),
            ("history_title", self.app.open_history)
        ]
        for key, command in buttons_others:
            btn = QPushButton(self.app.tr(key))
            if key == "history_title":
                btn.setToolTip(self.app.tr(key) + " (Ctrl+H)")
            btn.clicked.connect(command)
            layout.addWidget(btn)
            self.utility_buttons[key] = btn

    def create_right_pane(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the right pane (results, log, image)."""
        # Vertical Splitter for Image vs Log
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        parent_layout.addWidget(right_splitter)
        
        # Image Area
        self.image_container = QWidget()
        image_layout = QVBoxLayout(self.image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.create_image_frame(image_layout)
        right_splitter.addWidget(self.image_container)
        
        # Log Area
        self.log_group = QGroupBox(self.app.tr("log"))
        log_layout = QVBoxLayout(self.log_group)
        self.app.log_text = QTextEdit()
        self.app.log_text.setReadOnly(True)
        log_layout.addWidget(self.app.log_text)
        right_splitter.addWidget(self.log_group)
        
        right_splitter.setSizes([RIGHT_TOP_HEIGHT, LOG_DEFAULT_HEIGHT])

    def create_image_frame(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the image preview area."""
        self.app.image_frame = QGroupBox(self.app.tr("ocr_image"))
        layout = QVBoxLayout(self.app.image_frame)
        parent_layout.addWidget(self.app.image_frame)
        
        # Decompose into image actions and crop settings
        self._setup_image_action_buttons(layout)
        self._setup_crop_settings_row(layout)
        
        # Image Label (Scroll Area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.image_label_container = QWidget()
        self.image_label_vbox = QVBoxLayout(self.image_label_container)
        self.image_label_vbox.setContentsMargins(0, 0, 0, 0)
        self.image_label_vbox.setSpacing(0)
        self.app.image_label = QLabel(self.app.tr("no_image"))
        self.app.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ocr_completed_label = QLabel("")
        self.ocr_completed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.ocr_completed_label.font()
        font.setPointSize(24)
        font.setBold(True)
        self.ocr_completed_label.setFont(font)
        self.ocr_completed_label.setStyleSheet("color: #FFB300; margin-top: 16px;")
        self.ocr_completed_label.hide()
        self.image_label_vbox.addWidget(self.app.image_label)
        self.image_label_vbox.addWidget(self.ocr_completed_label)
        scroll.setWidget(self.image_label_container)
        layout.addWidget(scroll)

    def _setup_image_action_buttons(self, layout: QVBoxLayout) -> None:
        """Add image action buttons: Load, Paste, Crop."""
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton(self.app.tr("load_image"))
        self.btn_load.clicked.connect(self.app.image_proc.import_image)
        self.btn_paste = QPushButton(self.app.tr("paste_clipboard"))
        self.btn_paste.clicked.connect(self.app.image_proc.paste_from_clipboard)
        self.btn_paste.setToolTip(self.app.tr("paste_clipboard") + " (Ctrl+V)")
        self.btn_crop = QPushButton(self.app.tr("perform_crop"))
        self.btn_crop.clicked.connect(self.app.image_proc.perform_crop)
        
        self.cb_auto_calc = QCheckBox(self.app.tr("auto_calculate"))
        self.cb_auto_calc.setChecked(self.app.app_config.auto_calculate)
        self.cb_auto_calc.toggled.connect(self.app.events.on_auto_calculate_change)
        self.cb_auto_calc.setToolTip(self.app.tr("auto_calculate"))

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_paste)
        btn_layout.addWidget(self.btn_crop)
        btn_layout.addWidget(self.cb_auto_calc)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _setup_crop_settings_row(self, layout: QVBoxLayout) -> None:
        """Add crop mode selection and 4-value percent crop sliders/entries."""
        crop_layout = QHBoxLayout()
        self.lbl_crop_mode = QLabel(self.app.tr("crop_mode"))
        crop_layout.addWidget(self.lbl_crop_mode)
        
        self.rb_crop_drag = QRadioButton(self.app.tr("drag"))
        self.rb_crop_percent = QRadioButton(self.app.tr("percent"))
        
        if self.app.crop_mode_var == "drag":
            self.rb_crop_drag.setChecked(True)
        else:
            self.rb_crop_percent.setChecked(True)
            
        self.rb_crop_drag.toggled.connect(lambda c: self.app.events.on_crop_mode_change("drag") if c else None)
        self.rb_crop_percent.toggled.connect(lambda c: self.app.events.on_crop_mode_change("percent") if c else None)
        
        crop_layout.addWidget(self.rb_crop_drag)
        crop_layout.addWidget(self.rb_crop_percent)
        
        # 4-value percent crop
        self.app.entry_crop_l, self.app.slider_crop_l = self._create_crop_entry(crop_layout, "L %", self.app.app_config.crop_left_percent, "entry_crop_l", "slider_crop_l")
        self.app.entry_crop_t, self.app.slider_crop_t = self._create_crop_entry(crop_layout, "T %", self.app.app_config.crop_top_percent, "entry_crop_t", "slider_crop_t")
        self.app.entry_crop_w, self.app.slider_crop_w = self._create_crop_entry(crop_layout, "W %", self.app.app_config.crop_width_percent, "entry_crop_w", "slider_crop_w")
        self.app.entry_crop_h, self.app.slider_crop_h = self._create_crop_entry(crop_layout, "H %", self.app.app_config.crop_height_percent, "entry_crop_h", "slider_crop_h")
        
        crop_layout.addStretch()
        layout.addLayout(crop_layout)

    def _create_crop_entry(self, parent_layout: QHBoxLayout, label_text: str, value: Union[int, float], entry_name_base: str, slider_name_base: str) -> Tuple[QLineEdit, QSlider]:
        layout = QVBoxLayout()
        layout.setSpacing(0)
        
        # Label and QLineEdit
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(QLabel(label_text))
        
        entry = QLineEdit(str(value))
        entry.setFixedWidth(VALUE_ENTRY_WIDTH)
        entry.setObjectName(entry_name_base) # Set object name to identify later
        entry.textChanged.connect(self.app.events.on_crop_percent_change)
        h_layout.addWidget(entry)
        h_layout.addStretch()
        
        layout.addLayout(h_layout)

        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(value))
        slider.setObjectName(slider_name_base) # Set object name to identify later
        slider.valueChanged.connect(self.app.events.on_crop_slider_change)
        layout.addWidget(slider)

        parent_layout.addLayout(layout)
        return entry, slider


    def create_result_frame(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the result display area."""
        self.result_group = QGroupBox(self.app.tr("calc_result"))
        layout = QVBoxLayout(self.result_group)
        parent_layout.addWidget(self.result_group)
        
        self.app.result_text = QTextEdit()
        self.app.result_text.setReadOnly(True)
        layout.addWidget(self.app.result_text)

    def retranslate_ui(self) -> None:
        """Update all UI text based on the current language."""
        self.settings_panel.retranslate_ui()
        
        # Action Buttons
        for key, (btn, shortcut) in self.action_buttons.items():
            btn.setText(self.app.tr(key))
            btn.setToolTip(self.app.tr(key) + shortcut)
            
        self.btn_char_setting.setText(self.app.tr("char_setting"))
        self.action_new.setText(self.app.tr("new"))
        self.action_edit.setText(self.app.tr("edit"))
        
        # Utility Buttons
        for key, btn in self.utility_buttons.items():
            btn.setText(self.app.tr(key))
            if key == "history_title":
                btn.setToolTip(self.app.tr(key) + " (Ctrl+H)")
                
        # Right Pane
        self.log_group.setTitle(self.app.tr("log"))
        self.result_group.setTitle(self.app.tr("calc_result"))
        self.app.image_frame.setTitle(self.app.tr("ocr_image"))
        
        # Image Actions
        self.btn_load.setText(self.app.tr("load_image"))
        self.btn_paste.setText(self.app.tr("paste_clipboard"))
        self.btn_paste.setToolTip(self.app.tr("paste_clipboard") + " (Ctrl+V)")
        self.btn_crop.setText(self.app.tr("perform_crop"))
        self.cb_auto_calc.setText(self.app.tr("auto_calculate"))
        self.cb_auto_calc.setToolTip(self.app.tr("auto_calculate"))
        
        # Crop Settings
        self.lbl_crop_mode.setText(self.app.tr("crop_mode"))
        self.rb_crop_drag.setText(self.app.tr("drag"))
        self.rb_crop_percent.setText(self.app.tr("percent"))
        
        if self.app.image_label and not self.app.loaded_image:
            self.app.image_label.setText(self.app.tr("no_image"))

    def update_ui_mode(self) -> None:
        """Update the UI mode (OCR vs Manual)."""
        mode = self.app.mode_var
        if mode == "ocr":
            self.app.image_frame.setVisible(True)
        else:
            self.app.image_frame.setVisible(False)
    
    def update_character_combo(self, items_to_add: list[tuple[str, str]], current_internal_name: str = "") -> None:
        """
        Updates the character combobox with new items and attempts to restore selection.
        :param items_to_add: A list of (translated_name, internal_name) tuples to add to the combobox.
        :param current_internal_name: The internal name of the character to try and select after updating.
        """
        if self.character_combo is None:
            return
        
        # Check if the underlying C++ object is still alive
        if not self.character_combo.parent():
            return

        self.character_combo.blockSignals(True)
        try:
            self._all_char_items = items_to_add # Store the master list for filtering
            self.character_combo.clear()

            self.character_combo.addItem("", userData="")

            for translated_name, char_name in items_to_add:
                self.character_combo.addItem(translated_name, userData=char_name)
            
            target_index = 0
            if current_internal_name:
                index = self.character_combo.findData(current_internal_name)
                if index != -1:
                    target_index = index
            
            self.character_combo.setCurrentIndex(target_index)
            
            # Re-connect search signal (ensure it's only connected once)
            try:
                self.character_combo.lineEdit().textEdited.disconnect()
            except:
                pass
            self.character_combo.lineEdit().textEdited.connect(self._filter_character_combo)
            
        finally:
            self.character_combo.blockSignals(False)

    def filter_characters_by_config(self) -> None:
        try:
            current_key = self.app.current_config_key
            config_map = self.app.character_manager.get_character_config_map()
            lang = self.app.language
            
            allowed_chars = [name for name, cfg in config_map.items() if cfg == current_key]
            
            items_to_add = []
            if allowed_chars:
                items_to_add = sorted(
                    [(self.app.character_manager.get_display_name(name, lang), name) for name in allowed_chars],
                    key=lambda x: x[0]
                )
            else:
                # If no characters match, show all characters
                items_to_add = self.app.character_manager.get_all_characters(lang)
            
            current_internal_name = self.app.character_var
            # Filter items to add based on current combobox content if it's supposed to be filtered
            if allowed_chars:
                self.update_character_combo(items_to_add, current_internal_name)
            else: # If we are showing all, just update with all
                self.update_character_combo(self.app.character_manager.get_all_characters(lang), current_internal_name)
        except Exception as e:
            self.app.logger.exception(f"Failed to filter characters by config: {e}")