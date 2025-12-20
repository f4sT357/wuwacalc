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

        button_text_color = self.app.app_config.text_color
        tab_text_color = self.app.app_config.text_color

        # When a background image is set, it overrides the background-color,
        # so we can define the base style first.
        main_window_style = f"background-color: {colors['background']};"
        if main_window_bg_style:
            main_window_style = main_window_bg_style

        stylesheet = f"""
            QMainWindow {{ 
                {main_window_style}
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QWidget {{ 
                background-color: {c_bg}; 
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {colors['border']}; 
                {font_style} 
            }}
            QPushButton {{ 
                background-color: {c_btn}; 
                color: {button_text_color}; 
                border: 1px solid {colors['border']}; 
                padding: 5px; 
                {font_style} 
            }}
            QPushButton:hover {{ 
                background-color: {c_btn_hover}; 
            }}
            QTabWidget::pane {{ 
                border: 1px solid {colors['border']}; 
                background-color: {c_bg}; 
            }}
            QTabBar::tab {{ 
                background: {c_tab}; 
                color: {tab_text_color}; 
                padding: 5px; 
                {font_style} 
            }}
            QTabBar::tab:selected {{ 
                background: {c_tab_sel}; 
            }}
            QGroupBox {{ 
                border: 1px solid {colors['group_border']}; 
                margin-top: 10px; 
                background-color: {c_bg}; 
                {font_style} 
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 3px; 
                background-color: transparent; 
            }}
            QComboBox QAbstractItemView {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                selection-background-color: {colors['button_hover']}; 
                {font_style} 
            }}
            QRubberBand {{ 
                background-color: rgba(255, 215, 0, 0.3);
                border: 1px solid #FFD700;
            }}
        """
        q_app = QApplication.instance()
        if q_app and isinstance(q_app, QApplication):
            q_app.setStyleSheet(stylesheet)

    def update_app_font(self, font_family: str):
        """Update the application font."""
        self.app.config_manager.update_app_setting("app_font", font_family)
        # Re-apply theme to incorporate font change into stylesheet
        self.apply_theme(self.app._current_app_theme)

    def apply_theme(self, theme_name: str) -> None:
        """Apply the specified theme."""
        try:
            self.app._current_app_theme = theme_name
            self.app.config_manager.update_app_setting("theme", theme_name)
            
            q_app = QApplication.instance()
            if q_app:
                QApplication.setStyle(QStyleFactory.create("Fusion"))
                self._apply_theme_stylesheet(theme_name)
        except Exception as e:
            self.app.logger.exception(f"Error applying theme '{theme_name}': {e}")
            QMessageBox.critical(self.app, "Theme Error", f"Failed to apply theme '{theme_name}':\n{e}")

    def get_current_theme(self) -> str:
        """Returns the current theme name."""
        return self.app._current_app_theme

    def update_background_image(self, new_path: str) -> None:
        """
        Update the background image. If a new image is selected, copy it to the 'images'
        directory and update the config with the new path.
        """
        try:
            if not new_path:
                self.app.app_config.background_image = ""
                self.app.config_manager.update_app_setting("background_image", "")
                self.apply_theme(self.app._current_app_theme)
                self.app.gui_log("Background image cleared.")
                return

            if not os.path.exists(new_path):
                self.app.gui_log(f"Error: Background image file not found at {new_path}")
                return

            app_path = get_app_path()
            images_dir = os.path.join(app_path, 'images')

            final_dest_path = self._copy_image_safely(new_path, images_dir)
            saved_path = os.path.relpath(final_dest_path, app_path).replace('\\', '/')

            self.app.app_config.background_image = saved_path
            self.app.config_manager.update_app_setting("background_image", saved_path)
            self.apply_theme(self.app._current_app_theme)
            self.app.gui_log(f"Background image updated: {saved_path}")

        except Exception as e:
            self.app.logger.exception(f"Error updating background image: {e}")
            QMessageBox.critical(self.app, "Settings Error", f"Failed to update background image:\n{e}")

    def update_background_opacity(self, opacity: float) -> None:
        """Update the background opacity and re-apply theme."""
        try:
            self.app.app_config.background_opacity = opacity
            self.app.config_manager.update_app_setting("background_opacity", opacity)
            self.apply_theme(self.app._current_app_theme)
        except Exception as e:
            self.app.logger.exception(f"Error updating background opacity: {e}")
            QMessageBox.critical(self.app, "Settings Error", f"Failed to update background opacity:\n{e}")

    def update_text_color(self, new_color: str) -> None:
        """Update the text color and re-apply theme."""
        try:
            self.app.app_config.text_color = new_color
            self.app.config_manager.update_app_setting("text_color", new_color)
            self.apply_theme(self.app._current_app_theme)
            self.app.gui_log(f"Text color updated to {new_color}")
        except Exception as e:
            self.app.logger.exception(f"Error updating text color to {new_color}: {e}")
            QMessageBox.critical(self.app, "Settings Error", f"Failed to update text color:\n{e}")

    def update_input_bg_color(self, new_color: str) -> None:
        """Update the custom background color for input fields."""
        try:
            self.app.app_config.custom_input_bg_color = new_color
            self.app.config_manager.update_app_setting("custom_input_bg_color", new_color)
            self.apply_theme(self.app._current_app_theme)
            self.app.gui_log(f"Input background color updated to {new_color}")
        except Exception as e:
            self.app.logger.exception(f"Error updating input background color: {e}")
            QMessageBox.critical(self.app, "Settings Error", f"Failed to update input background color:\n{e}")

    def cleanup_unused_images(self):
        """Scans the 'images' directory and deletes any images not currently in use."""
        app_path = get_app_path()
        images_dir = os.path.join(app_path, 'images')

        if not os.path.isdir(images_dir):
            QMessageBox.information(self.app, self.app.tr("cleanup_title"), self.app.tr("cleanup_no_folder"))
            return

        current_image_path = self.app.app_config.background_image
        current_image_filename = os.path.basename(current_image_path) if current_image_path else None

        try:
            all_images = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
            unused_images = [f for f in all_images if f != current_image_filename]

            if not unused_images:
                QMessageBox.information(self.app, self.app.tr("cleanup_title"), self.app.tr("cleanup_no_unused"))
                return

            confirm_reply = QMessageBox.question(
                self.app,
                self.app.tr("cleanup_title"),
                self.app.tr("cleanup_confirm", len(unused_images), "\n".join(unused_images)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if confirm_reply == QMessageBox.StandardButton.Yes:
                deleted_count = 0
                error_files = []
                for filename in unused_images:
                    try:
                        os.remove(os.path.join(images_dir, filename))
                        deleted_count += 1
                    except Exception:
                        error_files.append(filename)
                
                if error_files:
                    QMessageBox.warning(self.app, self.app.tr("cleanup_title"), self.app.tr("cleanup_error", deleted_count, "\n".join(error_files)))
                else:
                    QMessageBox.information(self.app, self.app.tr("cleanup_title"), self.app.tr("cleanup_success", deleted_count))
        except Exception as e:
            self.app.logger.error(f"Error during image cleanup: {e}", exc_info=True)
            QMessageBox.critical(self.app, self.app.tr("cleanup_title"), self.app.tr("cleanup_unexpected_error", str(e)))

    def _copy_image_safely(self, source_path: str, dest_dir: str) -> str:
        """
        Copies a file to a destination directory, avoiding filename collisions.
        """
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, filename)

        if os.path.exists(dest_path):
            try:
                if os.path.samefile(source_path, dest_path):
                    return dest_path
            except FileNotFoundError:
                pass

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
        self.app.gui_log(f"Copied image to {dest_path}")
        return dest_path

    def _migrate_background_image_path(self) -> None:
        """
        Checks and migrates the background image path to the 'images' folder.
        """
        try:
            bg_path = self.app.app_config.background_image
            
            if not bg_path or bg_path.startswith('images/'):
                return

            app_path = get_app_path()
            
            if os.path.isabs(bg_path):
                old_full_path = bg_path
            else:
                old_full_path = os.path.join(app_path, bg_path)

            if not os.path.exists(old_full_path):
                title = self.app.tr("title_warning")
                message = self.app.tr("warn_legacy_bg_not_found", old_full_path)
                self.app._startup_messages.append((title, message))
                
                self.app.app_config.background_image = ""
                self.app.config_manager.update_app_setting("background_image", "")
                self.app.config_manager.save()
                return

            images_dir = os.path.join(app_path, 'images')
            final_dest_path = self._copy_image_safely(old_full_path, images_dir)
            new_relative_path = os.path.relpath(final_dest_path, app_path).replace('\\', '/')
            
            if new_relative_path != bg_path:
                self.app.app_config.background_image = new_relative_path
                self.app.config_manager.update_app_setting("background_image", new_relative_path)
                self.app.config_manager.save()
                self.app.gui_log(f"Migrated background image to {new_relative_path}")

        except Exception as e:
            self.app.logger.error(f"Failed to migrate background image setting: {e}", exc_info=True)

    def update_frame_transparency(self, transparent: bool):
        """Update QFrame transparency throughout the application."""
        try:
            from PyQt6.QtWidgets import QFrame
            frames = self.app.findChildren(QFrame)
            self.app.logger.info(f"Updating frame transparency: {transparent}, found {len(frames)} frames")
            
            for i, frame in enumerate(frames):
                try:
                    frame_id = id(frame)
                    if transparent:
                        # Store original frame style and stylesheet
                        if frame_id not in self.app._frame_original_properties:
                            self.app._frame_original_properties[frame_id] = {
                                'shape': frame.frameShape(),
                                'shadow': frame.frameShadow(),
                                'stylesheet': frame.styleSheet()
                            }
                        
                        # Remove frame border completely
                        frame.setFrameShape(QFrame.Shape.NoFrame)
                        frame.setFrameShadow(QFrame.Shadow.Plain)
                        
                        # Set transparent background
                        frame.setAutoFillBackground(False)
                        current_style = frame.styleSheet()
                        # Add transparent background and remove all borders
                        frame.setStyleSheet(current_style + " QFrame { background: transparent; border: none; }")
                    else:
                        # Restore original frame style
                        if frame_id in self.app._frame_original_properties:
                            props = self.app._frame_original_properties[frame_id]
                            frame.setFrameShape(props['shape'])
                            frame.setFrameShadow(props['shadow'])
                            frame.setStyleSheet(props['stylesheet'])
                            # Clean up stored properties
                            del self.app._frame_original_properties[frame_id]
                        frame.setAutoFillBackground(True)
                except Exception as e:
                    self.app.logger.warning(f"Failed to update transparency for frame {i}: {e}")
                    continue
            
            self.app.logger.info("Frame transparency update completed")
        except Exception as e:
            self.app.logger.error(f"Error in update_frame_transparency: {e}", exc_info=True)
