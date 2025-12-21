from typing import Union, Tuple, Optional, TYPE_CHECKING
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QTabWidget, QScrollArea, QTextEdit, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QRadioButton, QButtonGroup, 
                             QGroupBox, QSplitter, QFrame, QSizePolicy, QLineEdit, QSlider, QMenu)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from ui_constants import (
    RIGHT_TOP_HEIGHT, LOG_MIN_HEIGHT, LOG_DEFAULT_HEIGHT,
    VALUE_ENTRY_WIDTH, CROP_ENTRY_WIDTH, NUM_SUBSTATS
)

if TYPE_CHECKING:
    from wuwacalc17 import ScoreCalculatorApp


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

        self.character_combo = QComboBox()
        self.character_combo.setEditable(True)
        self.character_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.character_combo.lineEdit().setPlaceholderText(self.app.tr("search_character_placeholder"))
        self._all_char_items: list[tuple[str, str]] = [] # Store (display, internal)
        self._is_filtering = False

        self.mode_button_group = QButtonGroup(self.app)  # For Input Mode radio buttons
        self.calc_mode_button_group = QButtonGroup(self.app) # For Calc Mode radio buttons
        self.character_combo.setObjectName("CharComboBox")
    
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
        self.create_settings_frame(parent_layout)
        self.create_buttons_frame(parent_layout)
        
        # Tabs
        self.app.notebook = QTabWidget()
        self.app.notebook.blockSignals(True) # Block signals during initial setup
        self.app.notebook.currentChanged.connect(self.app.events.on_tab_changed)
        self.app.notebook.blockSignals(False) # Unblock signals after setup
        parent_layout.addWidget(self.app.notebook)
        
        self.create_result_frame(parent_layout)
    
    def create_settings_frame(self, parent_layout: QVBoxLayout) -> None:
        """Create the UI for the basic settings area."""
        settings_group = QGroupBox(self.app.tr("basic_settings"))
        settings_layout = QGridLayout(settings_group)
        parent_layout.addWidget(settings_group)
        
        # Decompose into individual row setups
        self._setup_basic_settings_row(settings_layout)
        self._setup_input_mode_row(settings_layout)
        self._setup_calc_mode_row(settings_layout)
        self._setup_calc_methods_row(settings_layout)

    def _setup_basic_settings_row(self, layout: QGridLayout) -> None:
        """Row 0: Cost Config, Character, and Language."""
        layout.addWidget(QLabel(self.app.tr("cost_config")), 0, 0)
        self.app.config_combo = QComboBox()
        self.app.config_combo.addItems(list(self.app.data_manager.tab_configs.keys()))
        self.app.config_combo.blockSignals(True)
        self.app.config_combo.setCurrentText(self.app.current_config_key)
        self.app.config_combo.blockSignals(False)
        self.app.config_combo.currentTextChanged.connect(self.app.events.on_config_change)
        layout.addWidget(self.app.config_combo, 0, 1)
        
        layout.addWidget(QLabel(self.app.tr("character")), 0, 2)
        self.character_combo.activated.connect(self.app.events.on_character_change)
        layout.addWidget(self.character_combo, 0, 3)
        
        layout.addWidget(QLabel(self.app.tr("language")), 0, 4)
        lang_combo = QComboBox()
        lang_combo.addItems(["ja", "en"])
        lang_combo.setCurrentText(self.app.language)
        lang_combo.currentTextChanged.connect(self.app.events.on_language_change)
        layout.addWidget(lang_combo, 0, 5)

    def _setup_input_mode_row(self, layout: QGridLayout) -> None:
        """Row 1: Input Mode (Manual/OCR) and Auto Main Stats."""
        layout.addWidget(QLabel(self.app.tr("input_mode")), 1, 0)
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
        
        # Auto Main
        self.cb_auto_main = QCheckBox(self.app.tr("auto_main"))
        self.cb_auto_main.setChecked(self.app.auto_apply_main_stats)
        self.cb_auto_main.toggled.connect(self.app.events.on_auto_main_change)
        layout.addWidget(self.cb_auto_main, 1, 4, 1, 2)

    def _setup_calc_mode_row(self, layout: QGridLayout) -> None:
        """Row 2: Calculation mode (Batch/Single)."""
        layout.addWidget(QLabel(self.app.tr("calc_mode")), 2, 0)
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
        """Row 3: Calculation methods checkboxes."""
        layout.addWidget(QLabel(self.app.tr("calc_methods")), 3, 0)
        
        methods_layout = QHBoxLayout()
        
        self.app.cb_method_normalized = QCheckBox(self.app.tr("method_normalized"))
        self.app.cb_method_ratio = QCheckBox(self.app.tr("method_ratio"))
        self.app.cb_method_roll = QCheckBox(self.app.tr("method_roll"))
        self.app.cb_method_effective = QCheckBox(self.app.tr("method_effective"))
        self.app.cb_method_cv = QCheckBox(self.app.tr("method_cv"))

        # Add tooltips for accessibility
        self.app.cb_method_normalized.setToolTip(self.app.tr("normalized_score_desc"))
        self.app.cb_method_ratio.setToolTip(self.app.tr("ratio_score_desc"))
        self.app.cb_method_roll.setToolTip(self.app.tr("roll_quality_desc"))
        self.app.cb_method_effective.setToolTip(self.app.tr("effective_stat_desc"))
        self.app.cb_method_cv.setToolTip(self.app.tr("cv_score_desc"))
        
        enabled_methods = self.app.app_config.enabled_calc_methods
        self.app.cb_method_normalized.setChecked(enabled_methods.get("normalized", True))
        self.app.cb_method_ratio.setChecked(enabled_methods.get("ratio", True))
        self.app.cb_method_roll.setChecked(enabled_methods.get("roll", True))
        self.app.cb_method_effective.setChecked(enabled_methods.get("effective", True))
        self.app.cb_method_cv.setChecked(enabled_methods.get("cv", True))
        
        self.app.cb_method_normalized.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.app.cb_method_ratio.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.app.cb_method_roll.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.app.cb_method_effective.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        self.app.cb_method_cv.toggled.connect(lambda: self.app.events.on_calc_method_changed())
        
        methods_layout.addWidget(self.app.cb_method_normalized)
        methods_layout.addWidget(self.app.cb_method_ratio)
        methods_layout.addWidget(self.app.cb_method_roll)
        methods_layout.addWidget(self.app.cb_method_effective)
        methods_layout.addWidget(self.app.cb_method_cv)
        methods_layout.addStretch()
        
        layout.addLayout(methods_layout, 3, 1, 1, 5)

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

    def _add_char_setting_button(self, layout: QHBoxLayout) -> None:
        """Add Character Setting button with its dropdown menu."""
        btn_char = QPushButton(self.app.tr("char_setting"))
        char_menu = QMenu(btn_char)
        
        # New Action
        action_new = char_menu.addAction(self.app.tr("new"))
        if action_new.text() == "new": # Fallback
             action_new.setText(self.app.tr("char_setting") + " (New)")
        action_new.triggered.connect(self.app.open_char_settings_new)

        # Edit Action
        action_edit = char_menu.addAction(self.app.tr("edit"))
        if action_edit.text() == "edit": # Fallback
             action_edit.setText(self.app.tr("char_setting") + " (Edit)")
        action_edit.triggered.connect(self.app.open_char_settings_edit)
        
        btn_char.setMenu(char_menu)
        layout.addWidget(btn_char)

    def _add_app_utility_buttons(self, layout: QHBoxLayout) -> None:
        """Add utility buttons: Help, Settings, Test Mode, History."""
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
        log_group = QGroupBox(self.app.tr("log"))
        log_layout = QVBoxLayout(log_group)
        self.app.log_text = QTextEdit()
        self.app.log_text.setReadOnly(True)
        log_layout.addWidget(self.app.log_text)
        right_splitter.addWidget(log_group)
        
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
        self.app.image_label = QLabel(self.app.tr("no_image"))
        self.app.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.app.image_label)
        layout.addWidget(scroll)

    def _setup_image_action_buttons(self, layout: QVBoxLayout) -> None:
        """Add image action buttons: Load, Paste, Crop."""
        btn_layout = QHBoxLayout()
        btn_load = QPushButton(self.app.tr("load_image"))
        btn_load.clicked.connect(self.app.image_proc.import_image)
        btn_paste = QPushButton(self.app.tr("paste_clipboard"))
        btn_paste.clicked.connect(self.app.image_proc.paste_from_clipboard)
        btn_paste.setToolTip(self.app.tr("paste_clipboard") + " (Ctrl+V)")
        btn_crop = QPushButton(self.app.tr("perform_crop"))
        btn_crop.clicked.connect(self.app.image_proc.perform_crop)
        
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_paste)
        btn_layout.addWidget(btn_crop)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _setup_crop_settings_row(self, layout: QVBoxLayout) -> None:
        """Add crop mode selection and 4-value percent crop sliders/entries."""
        crop_layout = QHBoxLayout()
        crop_layout.addWidget(QLabel(self.app.tr("crop_mode")))
        
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
        group = QGroupBox(self.app.tr("calc_result"))
        layout = QVBoxLayout(group)
        parent_layout.addWidget(group)
        
        self.app.result_text = QTextEdit()
        self.app.result_text.setReadOnly(True)
        layout.addWidget(self.app.result_text)

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
            
            allowed_chars = [name for name, cfg in config_map.items() if cfg == current_key]
            
            items_to_add = []
            if allowed_chars:
                items_to_add = sorted(
                    [(self.app.character_manager.get_display_name(name), name) for name in allowed_chars],
                    key=lambda x: x[0]
                )
            else:
                # If no characters match, show all characters
                items_to_add = self.app.character_manager.get_all_characters()
            
            current_internal_name = self.app.character_var
            # Filter items to add based on current combobox content if it's supposed to be filtered
            if allowed_chars:
                 self.update_character_combo(items_to_add, current_internal_name)
            else: # If we are showing all, just update with all
                 self.update_character_combo(self.app.character_manager.get_all_characters(), current_internal_name)
        except Exception as e:
            self.app.logger.exception(f"Failed to filter characters by config: {e}")