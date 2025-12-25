import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QMessageBox, 
                             QColorDialog, QFileDialog, QSlider)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase
from utils.utils import get_app_path

class DisplaySettingsDialog(QDialog):
    """Dialog for display settings, including text color."""
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(self.app.tr("display_settings"))
        self.setMinimumSize(300, 150)

        # Store initial color
        self.initial_text_color = self.app.app_config.text_color if hasattr(self.app.app_config, 'text_color') else "#ffffff"
        self.selected_text_color = self.initial_text_color

        self.initial_background_image = self.app.app_config.background_image
        self.selected_background_image = self.initial_background_image

        self.initial_opacity = self.app.app_config.background_opacity
        self.selected_opacity = self.initial_opacity

        self.initial_theme = self.app._current_app_theme
        self.selected_theme = self.initial_theme

        self.initial_input_bg = self.app.app_config.custom_input_bg_color
        self.selected_input_bg = self.initial_input_bg

        self.initial_font = self.app.app_config.app_font
        self.selected_font = self.initial_font

        self.initial_transparent_frames = self.app.app_config.transparent_frames
        self.selected_transparent_frames = self.initial_transparent_frames

        self.initial_text_shadow = getattr(self.app.app_config, 'show_text_shadow', True)
        self.selected_text_shadow = self.initial_text_shadow

        self.initial_shadow_color = getattr(self.app.app_config, 'text_shadow_color', "#000000")
        self.selected_shadow_color = self.initial_shadow_color

        self.initial_shadow_ox = getattr(self.app.app_config, 'shadow_offset_x', 2.0)
        self.selected_shadow_ox = self.initial_shadow_ox
        self.initial_shadow_oy = getattr(self.app.app_config, 'shadow_offset_y', 2.0)
        self.selected_shadow_oy = self.initial_shadow_oy
        self.initial_shadow_blur = getattr(self.app.app_config, 'shadow_blur', 5.0)
        self.selected_shadow_blur = self.initial_shadow_blur
        self.initial_shadow_spread = getattr(self.app.app_config, 'shadow_spread', 0.0)
        self.selected_shadow_spread = self.initial_shadow_spread

        self.init_ui()

    def init_ui(self):
        # Force fixed colors for this dialog to ensure usability
        # Use specific selectors to avoid overriding preview boxes
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: #ffffff;
            }
            QLabel:not([objectName^="preview"]), QCheckBox, QGroupBox {
                background-color: #000000;
                color: #ffffff;
            }
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QComboBox {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QComboBox QAbstractItemView {
                background-color: #222222;
                color: #ffffff;
                selection-background-color: #444444;
            }
            QLineEdit {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)

        layout = QVBoxLayout(self)

        # Text Color setting
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel(self.app.tr("text_color")))

        self.text_color_button = QPushButton(self.app.tr("select_color"))
        self.text_color_button.clicked.connect(self._pick_text_color)
        color_layout.addWidget(self.text_color_button)

        self.color_preview_label = QLabel()
        self.color_preview_label.setObjectName("previewText")
        self.color_preview_label.setFixedSize(50, 20)
        self.color_preview_label.setStyleSheet(f"background-color: {self.selected_text_color} !important; border: 1px solid white;")
        color_layout.addWidget(self.color_preview_label)

        layout.addLayout(color_layout)

        # Input Background Color setting
        input_bg_layout = QHBoxLayout()
        input_bg_layout.addWidget(QLabel(self.app.tr("input_bg_color")))

        self.btn_input_bg = QPushButton(self.app.tr("select_color"))
        self.btn_input_bg.clicked.connect(self._pick_input_bg_color)
        input_bg_layout.addWidget(self.btn_input_bg)

        self.input_bg_preview = QLabel()
        self.input_bg_preview.setObjectName("previewInput")
        self.input_bg_preview.setFixedSize(50, 20)
        bg_style = f"background-color: {self.selected_input_bg} !important;" if self.selected_input_bg else "background-color: transparent !important;"
        self.input_bg_preview.setStyleSheet(f"{bg_style} border: 1px solid white;")
        input_bg_layout.addWidget(self.input_bg_preview)

        self.btn_reset_input_bg = QPushButton(self.app.tr("reset"))
        self.btn_reset_input_bg.clicked.connect(self._reset_input_bg_color)
        input_bg_layout.addWidget(self.btn_reset_input_bg)

        layout.addLayout(input_bg_layout)

        # Font Setting
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(self.app.tr("font_settings")))

        self.combo_font = QComboBox()
        self.combo_font.addItem(self.app.tr("default_font"))

        fonts = self._get_compatible_fonts()
        self.combo_font.addItems(fonts)

        if self.initial_font and self.initial_font in fonts:
            self.combo_font.setCurrentText(self.initial_font)
        else:
            self.combo_font.setCurrentIndex(0) 

        self.combo_font.currentTextChanged.connect(self._update_selected_font)
        font_layout.addWidget(self.combo_font)

        layout.addLayout(font_layout)

        # Text Shadow Setting
        shadow_layout = QHBoxLayout()
        self.cb_text_shadow = QCheckBox(self.app.tr("text_shadow"))
        self.cb_text_shadow.setChecked(self.initial_text_shadow)
        self.cb_text_shadow.toggled.connect(self._update_text_shadow)
        shadow_layout.addWidget(self.cb_text_shadow)
        
        # Shadow Color picker
        self.btn_shadow_color = QPushButton(self.app.tr("shadow_color"))
        self.btn_shadow_color.clicked.connect(self._pick_shadow_color)
        self.btn_shadow_color.setEnabled(self.initial_text_shadow)
        shadow_layout.addWidget(self.btn_shadow_color)
        
        self.shadow_color_preview = QLabel()
        self.shadow_color_preview.setObjectName("previewShadow")
        self.shadow_color_preview.setFixedSize(50, 20)
        self.shadow_color_preview.setStyleSheet(f"background-color: {self.selected_shadow_color} !important; border: 1px solid white;")
        shadow_layout.addWidget(self.shadow_color_preview)
        shadow_layout.addStretch()
        layout.addLayout(shadow_layout)

        # Advanced Shadow Controls
        self.shadow_ctrl_group = QHBoxLayout()
        
        self.slider_ox = self._create_shadow_slider("OX", -5, 5, self.initial_shadow_ox)
        self.slider_oy = self._create_shadow_slider("OY", -5, 5, self.initial_shadow_oy)
        self.slider_blur = self._create_shadow_slider("Blur", 0, 15, self.initial_shadow_blur)
        self.slider_spread = self._create_shadow_slider("Spread", 0, 5, self.initial_shadow_spread)
        
        self.shadow_ctrl_group.addStretch()
        layout.addLayout(self.shadow_ctrl_group)
        self._update_shadow_controls_visibility(self.initial_text_shadow)

        # Transparent Frames Setting
        transparent_frames_layout = QHBoxLayout()
        self.cb_transparent_frames = QCheckBox(self.app.tr("transparent_frames") if self.app.tr("transparent_frames") != "transparent_frames" else "フレーム透過")
        self.cb_transparent_frames.setChecked(self.initial_transparent_frames)
        self.cb_transparent_frames.toggled.connect(self._update_transparent_frames)
        transparent_frames_layout.addWidget(self.cb_transparent_frames)
        transparent_frames_layout.addStretch()
        layout.addLayout(transparent_frames_layout)

        # Theme Setting
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel(self.app.tr("theme_settings")))

        self.combo_theme = QComboBox()
        self.theme_map = {
            self.app.tr("dark_theme"): "dark",
            self.app.tr("light_theme"): "light",
            self.app.tr("clear_theme"): "clear",
            self.app.tr("custom_theme"): "custom"
        }
        self.theme_map_inv = {v: k for k, v in self.theme_map.items()}

        self.combo_theme.addItems(list(self.theme_map.keys()))
        if self.initial_theme in self.theme_map_inv:
            self.combo_theme.setCurrentText(self.theme_map_inv[self.initial_theme])

        self.combo_theme.currentTextChanged.connect(self._update_selected_theme)
        theme_layout.addWidget(self.combo_theme)

        layout.addLayout(theme_layout)

        # Background Image Setting
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel(self.app.tr("background_image")))

        self.lbl_bg_path = QLabel(os.path.basename(self.selected_background_image) if self.selected_background_image else "None")
        bg_layout.addWidget(self.lbl_bg_path)

        btn_select_bg = QPushButton(self.app.tr("select_image"))
        btn_select_bg.clicked.connect(self._select_background_image)
        bg_layout.addWidget(btn_select_bg)

        btn_clear_bg = QPushButton(self.app.tr("clear_image"))
        btn_clear_bg.clicked.connect(self._clear_background_image)
        bg_layout.addWidget(btn_clear_bg)

        btn_cleanup = QPushButton(self.app.tr("cleanup_button"))
        btn_cleanup.clicked.connect(self._cleanup_images)
        bg_layout.addWidget(btn_cleanup)

        layout.addLayout(bg_layout)

        # Opacity Slider
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel(self.app.tr("bg_opacity")))

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(int(self.selected_opacity * 100))
        self.slider_opacity.valueChanged.connect(self._update_opacity_label)

        self.lbl_opacity_val = QLabel(f"{int(self.selected_opacity * 100)}%")
        self.lbl_opacity_val.setFixedWidth(40)

        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity_val)

        layout.addLayout(opacity_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton(self.app.tr("apply"))
        btn_apply.clicked.connect(self._apply_settings)

        btn_cancel = QPushButton(self.app.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()

        btn_help = QPushButton(self.app.tr("help_customization"))
        btn_help.clicked.connect(self._open_help)
        btn_layout.addWidget(btn_help)

        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)

        btn_full_reset = QPushButton(self.app.tr("full_reset"))
        btn_full_reset.clicked.connect(self._full_reset)
        btn_layout.addWidget(btn_full_reset)

        layout.addLayout(btn_layout)

        # Apply initial shadows to widgets in this dialog
        self.app.theme_manager.refresh_global_shadows()

    def _auto_switch_to_custom(self):
        """Automatically switch theme combo to 'Custom' if an individual setting is changed."""
        if self.selected_theme != "custom":
            custom_label = self.app.tr("custom_theme")
            if custom_label in self.theme_map:
                self.combo_theme.setCurrentText(custom_label)
                self.selected_theme = "custom"

    def _create_shadow_slider(self, label, min_val, max_val, current):
        vbox = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(40)
        vbox.addWidget(lbl)
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_val, max_val)
        s.setValue(int(current))
        s.setFixedWidth(80)
        s.valueChanged.connect(self._on_shadow_slider_changed)
        vbox.addWidget(s)
        self.shadow_ctrl_group.addLayout(vbox)
        return s

    def _on_shadow_slider_changed(self):
        self.selected_shadow_ox = self.slider_ox.value()
        self.selected_shadow_oy = self.slider_oy.value()
        self.selected_shadow_blur = self.slider_blur.value()
        self.selected_shadow_spread = self.slider_spread.value()
        self._auto_switch_to_custom()

    def _update_shadow_controls_visibility(self, enabled):
        self.slider_ox.setEnabled(enabled)
        self.slider_oy.setEnabled(enabled)
        self.slider_blur.setEnabled(enabled)
        self.slider_spread.setEnabled(enabled)

    def _pick_text_color(self):
        current_color = QColor(self.selected_text_color)
        color = QColorDialog.getColor(current_color, self, self.app.tr("select_text_color"))

        if color.isValid():
            self.selected_text_color = color.name() 
            self.color_preview_label.setStyleSheet(f"background-color: {self.selected_text_color} !important; border: 1px solid white;")
            self._auto_switch_to_custom()

    def _select_background_image(self):
        image_filter = "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.app.tr("select_image"),
            "",
            image_filter
        )
        if file_path:
            self.selected_background_image = file_path
            self.lbl_bg_path.setText(os.path.basename(file_path))
            self._auto_switch_to_custom()

    def _cleanup_images(self):
        self.app.cleanup_unused_images()

    def _clear_background_image(self):
        self.selected_background_image = ""
        self.lbl_bg_path.setText("None")
        self._auto_switch_to_custom()

    def _update_selected_theme(self, text):
        if text in self.theme_map:
            theme_id = self.theme_map[text]
            self.selected_theme = theme_id
            
            # Auto-apply preset colors if switching TO a preset (not Custom)
            from utils.constants import THEME_COLORS
            if theme_id in THEME_COLORS and theme_id != "custom":
                colors = THEME_COLORS[theme_id]
                self.selected_text_color = colors.get("text", self.selected_text_color)
                self.selected_shadow_color = colors.get("shadow", self.selected_shadow_color)
                self.selected_input_bg = colors.get("input_bg", self.selected_input_bg)
                
                # Reset shadow sliders to defaults for presets
                self.selected_shadow_ox = 2.0; self.selected_shadow_oy = 2.0
                self.selected_shadow_blur = 5.0; self.selected_shadow_spread = 0.0
                self.slider_ox.setValue(2); self.slider_oy.setValue(2)
                self.slider_blur.setValue(5); self.slider_spread.setValue(0)
                
                self._update_all_previews()

    def _update_all_previews(self):
        """Update all color preview squares with currently selected values."""
        self.color_preview_label.setStyleSheet(f"background-color: {self.selected_text_color} !important; border: 1px solid white;")
        self.shadow_color_preview.setStyleSheet(f"background-color: {self.selected_shadow_color} !important; border: 1px solid white;")
        bg_style = f"background-color: {self.selected_input_bg} !important;" if self.selected_input_bg else "background-color: transparent !important;"
        self.input_bg_preview.setStyleSheet(f"{bg_style} border: 1px solid white;")

    def _update_opacity_label(self, value):
        self.selected_opacity = value / 100.0
        self.lbl_opacity_val.setText(f"{value}%")
        self._auto_switch_to_custom()

    def _update_transparent_frames(self, checked):
        self.selected_transparent_frames = checked
        self._auto_switch_to_custom()

    def _update_text_shadow(self, checked):
        self.selected_text_shadow = checked
        self.btn_shadow_color.setEnabled(checked)
        self._update_shadow_controls_visibility(checked)
        self._auto_switch_to_custom()

    def _pick_shadow_color(self):
        current = QColor(self.selected_shadow_color)
        color = QColorDialog.getColor(current, self, self.app.tr("shadow_color"))
        if color.isValid():
            self.selected_shadow_color = color.name()
            self.shadow_color_preview.setStyleSheet(f"background-color: {self.selected_shadow_color} !important; border: 1px solid white;")
            self._auto_switch_to_custom()

    def _apply_settings(self):
        if self.selected_text_color != self.initial_text_color:
            self.app.update_text_color(self.selected_text_color)

        if self.selected_background_image != self.initial_background_image:
            self.app.update_background_image(self.selected_background_image)

        if self.selected_opacity != self.initial_opacity:
            self.app.update_background_opacity(self.selected_opacity)

        if self.selected_theme != self.initial_theme:
            self.app.apply_theme(self.selected_theme)

        if self.selected_input_bg != self.initial_input_bg:
            self.app.update_input_bg_color(self.selected_input_bg)

        if self.selected_font != self.initial_font:
            self.app.update_app_font(self.selected_font)

        if self.selected_transparent_frames != self.initial_transparent_frames:
            self.app.app_config.transparent_frames = self.selected_transparent_frames
            self.app.update_frame_transparency(self.selected_transparent_frames)
            
        if self.selected_text_shadow != self.initial_text_shadow:
            self.app.app_config.show_text_shadow = self.selected_text_shadow
            self.app.html_renderer.set_show_shadow(self.selected_text_shadow)
            self.app.refresh_results_display()
            
        if self.selected_shadow_color != self.initial_shadow_color:
            self.app.update_shadow_color(self.selected_shadow_color)

        # Update Shadow Params
        if (self.selected_shadow_ox != self.initial_shadow_ox or 
            self.selected_shadow_oy != self.initial_shadow_oy or 
            self.selected_shadow_blur != self.initial_shadow_blur or 
            self.selected_shadow_spread != self.initial_shadow_spread):
            self.app.update_shadow_params(
                self.selected_shadow_ox, 
                self.selected_shadow_oy, 
                self.selected_shadow_blur, 
                self.selected_shadow_spread
            )

        self.app.config_manager.save()
        self.accept()

    def _pick_input_bg_color(self):
        current = QColor(self.selected_input_bg) if self.selected_input_bg else Qt.GlobalColor.white
        color = QColorDialog.getColor(current, self, self.app.tr("input_bg_color"))

        if color.isValid():
            self.selected_input_bg = color.name()
            self.input_bg_preview.setStyleSheet(f"background-color: {self.selected_input_bg} !important; border: 1px solid white;")
            self._auto_switch_to_custom()

    def _reset_input_bg_color(self):
        self.selected_input_bg = ""
        self.input_bg_preview.setStyleSheet("background-color: transparent; border: 1px solid black;")
        self._auto_switch_to_custom()

    def _full_reset(self):
        reply = QMessageBox.question(
            self,
            self.app.tr("full_reset"),
            self.app.tr("confirm_full_reset"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.selected_text_color = "#ffffff"
            self.selected_background_image = ""
            self.selected_opacity = 1.0
            self.selected_theme = "dark"
            self.selected_input_bg = "#3c3c3c"
            self.selected_font = ""
            self.selected_text_shadow = True
            self.selected_shadow_color = "#000000"
            self.selected_shadow_ox = 2.0
            self.selected_shadow_oy = 2.0
            self.selected_shadow_blur = 5.0
            self.selected_shadow_spread = 0.0

            self.lbl_bg_path.setText("None")
            self.slider_opacity.setValue(100)
            self.cb_text_shadow.setChecked(True)
            self.btn_shadow_color.setEnabled(True)
            self.slider_ox.setValue(2); self.slider_oy.setValue(2)
            self.slider_blur.setValue(5); self.slider_spread.setValue(0)
            self._update_shadow_controls_visibility(True)
            self._update_all_previews()

            if "dark" in self.theme_map_inv:
                self.combo_theme.setCurrentText(self.theme_map_inv["dark"])

            self.input_bg_preview.setStyleSheet(f"background-color: {self.selected_input_bg}; border: 1px solid black;")
            self.combo_font.setCurrentIndex(0)

            self._apply_settings()
            self.app.config_manager.save() 

    def _get_compatible_fonts(self) -> list[str]:
        """Get list of fonts supporting Japanese."""
        families = QFontDatabase.families()
        compatible = []
        for family in families:
            if QFontDatabase.writingSystems(family) and QFontDatabase.WritingSystem.Japanese in QFontDatabase.writingSystems(family):
                compatible.append(family)
        return sorted(compatible)

    def _update_selected_font(self, font_name):
        if font_name == self.app.tr("default_font"):
            self.selected_font = ""
        else:
            self.selected_font = font_name
        self._auto_switch_to_custom()

    def _open_help(self):
        """Open the HTML help file in default browser."""
        help_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "appearance_help.html")
        if os.path.exists(help_path):
            try:
                os.startfile(help_path)
            except AttributeError:
                import webbrowser
                webbrowser.open(f"file:///{help_path}")
        else:
            QMessageBox.warning(self, "Help Error", f"Help file not found at:{help_path}")
