import os
import shutil
from PyQt6.QtWidgets import QApplication, QStyleFactory, QMessageBox
from constants import THEME_COLORS
from utils import get_app_path

class ThemeManager:
    def __init__(self, app_instance):
        self.app = app_instance

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba string."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        return hex_color

    def _apply_theme_stylesheet(self, theme_name: str) -> None:
        """Sets the stylesheet based on the theme name."""
        colors = THEME_COLORS.get(theme_name, THEME_COLORS["light"])
        bg_image = self.app.app_config.background_image
        alpha = self.app.app_config.background_opacity
        is_transparent = self.app.app_config.transparent_frames
        
        main_window_bg_style = ""
        
        c_bg = colors['background']
        c_input = self.app.app_config.custom_input_bg_color or colors['input_bg']
        c_btn = colors['button_bg']
        c_btn_hover = colors['button_hover']
        c_tab = colors['tab_bg']
        c_tab_sel = colors['tab_selected']

        if bg_image:
            if not os.path.isabs(bg_image):
                bg_image = os.path.join(get_app_path(), bg_image)

            if os.path.exists(bg_image):
                img_path = bg_image.replace('\\', '/')
                main_window_bg_style = f"border-image: url('{img_path}') 0 0 0 0 stretch stretch;"
                
                c_bg = self._hex_to_rgba(c_bg, alpha)
                c_input = self._hex_to_rgba(c_input, alpha)
                c_btn = self._hex_to_rgba(c_btn, alpha)
                c_btn_hover = self._hex_to_rgba(c_btn_hover, alpha)
                c_tab = self._hex_to_rgba(c_tab, alpha)
                c_tab_sel = self._hex_to_rgba(c_tab_sel, alpha)
        
        font_style = f"font-family: '{self.app.app_config.app_font}';" if self.app.app_config.app_font else ""

        # Adjust GroupBox, Frame and TextEdit based on transparency setting
        if is_transparent:
            group_bg = "transparent"
            group_border = "none"
            text_edit_bg = "rgba(0, 0, 0, 0.2)"
            # Keep tabs slightly more visible for structure
            tab_pane_bg = "rgba(0, 0, 0, 0.1)"
            tab_pane_border = f"1px solid rgba(128, 128, 128, 0.3)"
        else:
            group_bg = c_bg
            group_border = f"1px solid {colors['group_border']}"
            text_edit_bg = c_input
            tab_pane_bg = c_bg
            tab_pane_border = f"1px solid {colors['border']}"

        stylesheet = f"""
            QMainWindow {{ 
                {main_window_bg_style if main_window_bg_style else f"background-color: {colors['background']};"}
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QWidget {{ 
                background-color: {c_bg}; 
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {colors['border']}; 
                {font_style} 
            }}
            QTextEdit {{
                background-color: {text_edit_bg}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {colors['border']}; 
                {font_style}
            }}
            QPushButton {{ 
                background-color: {c_btn}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {colors['border']}; 
                padding: 5px; 
                {font_style} 
            }}
            QPushButton:hover {{ 
                background-color: {c_btn_hover}; 
            }}
            QTabWidget::pane {{ 
                border: {tab_pane_border}; 
                background-color: {tab_pane_bg}; 
            }}
            QTabBar::tab {{ 
                background: {c_tab}; 
                color: {self.app.app_config.text_color}; 
                padding: 5px; 
                min-width: 80px;
                {font_style} 
            }}
            QTabBar::tab:selected {{ 
                background: {c_tab_sel}; 
                font-weight: bold;
            }}
            QGroupBox {{ 
                border: {group_border}; 
                margin-top: 15px; 
                background-color: {group_bg}; 
                {font_style} 
                font-weight: bold;
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 5px; 
                background-color: transparent; 
            }}
            QComboBox {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {colors['border']}; 
                {font_style} 
            }}
            QComboBox QAbstractItemView {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                selection-background-color: {colors['button_hover']}; 
                {font_style} 
            }}
        """
        q_app = QApplication.instance()
        if q_app:
            q_app.setStyleSheet(stylesheet)

    def update_app_font(self, font_family: str):
        self.app.config_manager.update_app_setting("app_font", font_family)
        self.apply_theme(self.app._current_app_theme)

    def apply_theme(self, theme_name: str) -> None:
        try:
            self.app._current_app_theme = theme_name
            self.app.config_manager.update_app_setting("theme", theme_name)
            if QApplication.instance():
                QApplication.setStyle(QStyleFactory.create("Fusion"))
                self._apply_theme_stylesheet(theme_name)
        except Exception as e:
            self.app.logger.exception(f"Error applying theme: {e}")

    def update_background_image(self, new_path: str) -> None:
        try:
            if not new_path:
                self.app.app_config.background_image = ""
                self.app.config_manager.update_app_setting("background_image", "")
            else:
                app_path = get_app_path()
                images_dir = os.path.join(app_path, 'images')
                final_dest_path = self._copy_image_safely(new_path, images_dir)
                saved_path = os.path.relpath(final_dest_path, app_path).replace('\\', '/')
                self.app.app_config.background_image = saved_path
                self.app.config_manager.update_app_setting("background_image", saved_path)
            self.apply_theme(self.app._current_app_theme)
        except Exception as e:
            self.app.logger.exception(f"Error background image: {e}")

    def update_background_opacity(self, opacity: float) -> None:
        self.app.app_config.background_opacity = opacity
        self.app.config_manager.update_app_setting("background_opacity", opacity)
        self.apply_theme(self.app._current_app_theme)

    def update_text_color(self, new_color: str) -> None:
        self.app.app_config.text_color = new_color
        self.app.config_manager.update_app_setting("text_color", new_color)
        self.apply_theme(self.app._current_app_theme)

    def update_input_bg_color(self, new_color: str) -> None:
        self.app.app_config.custom_input_bg_color = new_color
        self.app.config_manager.update_app_setting("custom_input_bg_color", new_color)
        self.apply_theme(self.app._current_app_theme)

    def update_frame_transparency(self, transparent: bool):
        """Update transparency and re-apply theme to ensure global stylesheet wins."""
        self.app.app_config.transparent_frames = transparent
        self.app.config_manager.update_app_setting("transparent_frames", transparent)
        self.apply_theme(self.app._current_app_theme)

    def refresh_global_shadows(self) -> None:
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QCheckBox, QRadioButton, QPushButton
        from PyQt6.QtGui import QColor
        config = self.app.app_config
        show = config.show_text_shadow
        color = QColor(config.text_shadow_color)
        widgets = self.app.findChildren((QLabel, QCheckBox, QRadioButton, QPushButton))
        for w in widgets:
            try:
                w.setGraphicsEffect(None)
                if show:
                    effect = QGraphicsDropShadowEffect(w)
                    effect.setBlurRadius(config.shadow_blur)
                    effect.setOffset(config.shadow_offset_x, config.shadow_offset_y)
                    effect.setColor(color)
                    w.setGraphicsEffect(effect)
            except Exception: continue

    def _copy_image_safely(self, source_path: str, dest_dir: str) -> str:
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, filename)
        if os.path.exists(dest_path):
            try:
                if os.path.samefile(source_path, dest_path): return dest_path
            except Exception: pass
            name, ext = os.path.splitext(filename)
            i = 1
            while True:
                new_filename = f"{name}_{i}{ext}"
                new_dest_path = os.path.join(dest_dir, new_filename)
                if not os.path.exists(new_dest_path): 
                    dest_path = new_dest_path
                    break
                i += 1
        shutil.copy(source_path, dest_path)
        return dest_path

    def cleanup_unused_images(self):
        images_dir = os.path.join(get_app_path(), 'images')
        if not os.path.isdir(images_dir): return
        current = os.path.basename(self.app.app_config.background_image) if self.app.app_config.background_image else None
        try:
            unused = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f)) and f != current]
            if not unused: return
            if QMessageBox.question(self.app, "Cleanup", f"Delete {len(unused)} unused images?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                for f in unused:
                    try: os.remove(os.path.join(images_dir, f))
                    except: pass
        except Exception: pass
