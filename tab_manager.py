"""
Tab Management Module (PyQt6)

Provides functions for managing, saving, restoring, clearing, and exporting tab data.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple, TYPE_CHECKING

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QGroupBox, QComboBox, QLineEdit, QLabel, 
                             QMessageBox, QFileDialog)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from constants import DEFAULT_COST_CONFIG
from data_contracts import EchoEntry, SubStat, TabImageData, TabResultData

if TYPE_CHECKING:
    from wuwacalc17 import ScoreCalculatorApp

class TabManager:
    """Class responsible for managing tab data."""
    
    def __init__(self, app: 'ScoreCalculatorApp'):
        """
        Initialization
        
        Args:
            app: The main application instance.
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        # UI Elements
        self.tabs_content: Dict[str, Dict[str, Any]] = {}
        
        # Data storage for each tab using data classes
        self._tab_images: Dict[str, TabImageData] = {}
        self._tab_results: Dict[str, TabResultData] = {}
    
    def get_selected_tab_name(self) -> Optional[str]:
        """Get the internal key of the currently selected tab."""
        if self.app.notebook is None:
            return None
        index = self.app.notebook.currentIndex()
        if index == -1:
            return None
            
        # Return internal key from config instead of localized label
        config_key = self.app.current_config_key
        # We need direct access to TAB_CONFIGS constants
        # It's better to import it inside method or use app attribute if stored
        # from constants import TAB_CONFIGS # Removed
        tab_configs = self.app.data_manager.tab_configs
        if config_key in tab_configs:
             keys = tab_configs[config_key]
             if index < len(keys):
                 return keys[index]
        
        # Fallback to tabText if something fails (though this shouldn't happen)
        return self.app.notebook.tabText(index)
    
    def show_tab_image(self, tab_name: str) -> None:
        """Display the image saved in the tab."""
        if self.app.image_label is None:
            return
        data = self._tab_images.get(tab_name)
        if data:
            self.app.loaded_image = data.cropped.copy()
            self.app.original_image = data.original.copy()
            self.app.update_image_preview(self.app.loaded_image)
        else:
            # If there's no saved image for this tab, do not clear the currently
            # displayed preview. Leaving the existing preview prevents the image
            # from disappearing immediately after it was loaded by the user.
            # Only reset the internal references; UI preview remains until
            # explicitly cleared by the user (e.g., Clear Tab / Clear All).
            self.app.loaded_image = None
            self.app.original_image = None
            self.app.logger.debug(f"No saved image for tab '{tab_name}'; keeping current preview.")
    
    def save_tab_result(self, tab_name: str) -> None:
        """Save the current calculation result for each tab."""
        if self.app.result_text is None:
            return
        try:
            result_content = self.app.result_text.toHtml()
            self._tab_results[tab_name] = TabResultData(content=result_content)
        except Exception as e:
            self.logger.warning(f"Failed to save tab result: {e}", exc_info=True)
    
    def show_tab_result(self, tab_name: str) -> None:
        """Restore the saved calculation result."""
        if self.app.result_text is None:
            return
        
        result_data = self._tab_results.get(tab_name)
        if result_data:
            try:
                self.app.result_text.setHtml(result_data.content)
            except Exception as e:
                self.logger.warning(f"Failed to restore tab result: {e}", exc_info=True)
        else:
            self.app.result_text.clear()
    
    def _reset_tab_content(self, content: Dict[str, Any]) -> None:
        """Resets the widgets of a single tab content."""
        content["main_widget"].setCurrentIndex(-1)
        for stat_widget, val_widget in content["sub_entries"]:
            stat_widget.setCurrentIndex(-1)
            val_widget.clear()

    def clear_current_tab(self) -> None:
        """Clear the contents of the current tab only."""
        try:
            tab_name = self.get_selected_tab_name()
            if not tab_name or tab_name not in self.tabs_content:
                return
            
            content = self.tabs_content[tab_name]
            self._reset_tab_content(content)
            
            # Also clear the image
            if tab_name in self._tab_images:
                del self._tab_images[tab_name]
            # Also clear the calculation result
            if tab_name in self._tab_results:
                del self._tab_results[tab_name]
            
            self.show_tab_image(tab_name)
            self.show_tab_result(tab_name)
            
            self.app.gui_log(f"Cleared the contents of tab '{tab_name}'.")
        except Exception as e:
            error_msg = f"Failed to clear tab: {e}"
            QMessageBox.critical(self.app, "Error", error_msg)
            self.logger.exception(f"Tab clear error: {e}")
    

    
    def clear_all(self) -> None:
        """Reset all tabs, text, logs, input values, etc."""
        try:
            # Reset all tab contents
            for content in self.tabs_content.values():
                self._reset_tab_content(content)
            
            if self.app.result_text:
                self.app.result_text.clear()
            if self.app.log_text:
                self.app.log_text.clear()
                
            self.app.loaded_image = None
            self.app.original_image = None
            self.app._image_preview = None
            self._tab_images.clear()
            self._tab_results.clear()
            
            if self.app.image_label:
                self.app.image_label.setText("No image loaded")
                self.app.image_label.setPixmap(QPixmap())
                
            self.app.gui_log("All items have been cleared.")
        except Exception as e:
            error_msg = f"Failed to reset items: {e}"
            QMessageBox.critical(self.app, "Clear Error", error_msg)
            self.logger.exception(f"Clear all error: {e}")
    
    def export_result_to_txt(self) -> None:
        """Export the score calculation result to a text file."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self.app, "Save Result", "", "Text Files (*.txt);;All Files (*.*)"
            )
            if not file_path:
                return
            text = self.app.result_text.toPlainText()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self.app, "Success", "Calculation result exported to text file.")
            self.app.gui_log(f"Exported calculation result to TXT file: {file_path}")
        except Exception as e:
            QMessageBox.critical(self.app, "Error", f"Export failed:\n{e}")
            self.logger.exception(f"Error during export: {e}")
            self.app.gui_log(f"Error during export: {e}")
    
    def save_tab_image(self, tab_name: str, original_image: 'Image.Image', cropped_image: 'Image.Image') -> None:
        """Save image data to the tab."""
        self._tab_images[tab_name] = TabImageData(
            original=original_image,
            cropped=cropped_image
        )
    
    def get_tab_image(self, tab_name: str) -> Optional[TabImageData]:
        """Get the image data for the tab."""
        return self._tab_images.get(tab_name)

    def update_tabs(self) -> None:
        """Update tabs based on configuration."""
        if self.app.notebook is None:
            return
            
        self.app._updating_tabs = True
        try:
            config_key = self._validate_config_key()
            config_tab_names = self.app.data_manager.tab_configs[config_key]
            
            old_data = self._save_current_tab_state()
            
            self.app.notebook.clear()
            self.tabs_content = {}
            
            cost_counts = self._calculate_cost_counts(config_tab_names)
            
            current_cost_indices = {} # Track occurrence index for each cost
            
            for tab_name in config_tab_names:
                cost_num = next((ch for ch in tab_name if ch.isdigit()), "1")
                
                # Calculate cost key (e.g. "4_1", "4_2" or just "4" if only one)
                total_for_cost = cost_counts[cost_num]
                current_idx = current_cost_indices.get(cost_num, 0) + 1
                current_cost_indices[cost_num] = current_idx
                
                cost_key = cost_num if total_for_cost == 1 else f"{cost_num}_{current_idx}"
                
                # Create and Add Page
                self._create_and_add_tab_page(tab_name, cost_num, cost_key)
                
                # Restore data using (cost, index) key if available
                state_key = (cost_num, current_idx)
                if state_key in old_data:
                    self._restore_tab_data(tab_name, old_data[state_key])

        except Exception as e:
            self.app.gui_log(f"Tab update error: {e}")
            self.logger.exception("Tab update failed")
        finally:
            self.app._updating_tabs = False
            
    def retranslate_tabs(self) -> None:
        """Update all tab titles and internal labels based on the current language."""
        if self.app.notebook is None:
            return
            
        self.app._updating_tabs = True
        try:
            # Update Tab Titles
            for i in range(self.app.notebook.count()):
                # We need to find the tab_name for this index
                # Since we don't store index to tab_name mapping directly, 
                # we can use the order in config_tab_names
                config_key = self.app.current_config_key
                config_tab_names = self.app.data_manager.tab_configs.get(config_key, [])
                if i < len(config_tab_names):
                    tab_name = config_tab_names[i]
                    new_label = self._generate_tab_label(tab_name)
                    self.app.notebook.setTabText(i, new_label)
            
            # Update Content in each tab
            for tab_name, content in self.tabs_content.items():
                # Update Group Titles
                content["main_group"].setTitle(self.app.tr("main_stat"))
                content["sub_group"].setTitle(self.app.tr("substats"))
                
                # Update Main Stat ComboBox
                main_combo = content["main_widget"]
                current_main_key = main_combo.currentData()
                main_combo.blockSignals(True)
                main_combo.clear()
                cost_num = content["cost"]
                fallback_main_stats = ["HP", "ATK", "DEF"]
                main_opts = self.app.data_manager.main_stat_options.get(cost_num, fallback_main_stats)
                for s in main_opts:
                    main_combo.addItem(self.app.tr(s), userData=s)
                if current_main_key:
                    idx = main_combo.findData(current_main_key)
                    if idx != -1:
                        main_combo.setCurrentIndex(idx)
                main_combo.blockSignals(False)
                
                # Update Substat ComboBoxes
                sub_max_vals = self.app.data_manager.substat_max_values
                for stat_combo, _ in content["sub_entries"]:
                    current_sub_key = stat_combo.currentData()
                    stat_combo.blockSignals(True)
                    stat_combo.clear()
                    stat_combo.addItem("", userData="")
                    for s in sub_max_vals.keys():
                        stat_combo.addItem(self.app.tr(s), userData=s)
                    if current_sub_key:
                        idx = stat_combo.findData(current_sub_key)
                        if idx != -1:
                            stat_combo.setCurrentIndex(idx)
                    stat_combo.blockSignals(False)
                    
        finally:
            self.app._updating_tabs = False

    def _validate_config_key(self) -> str:
        """Validates and returns the current configuration key."""
        config_key = self.app.current_config_key
        tab_configs = self.app.data_manager.tab_configs
        if config_key not in tab_configs:
            self.app.gui_log(f"Invalid cost key '{config_key}' detected, falling back to {DEFAULT_COST_CONFIG}")
            config_key = DEFAULT_COST_CONFIG
            self.app.current_config_key = config_key
            if self.app.config_combo:
                self.app.config_combo.setCurrentText(config_key)
        return config_key

    def _save_current_tab_state(self) -> Dict[str, Any]:
        """Saves the current state of all tabs using (cost, index) as key."""
        state = {}
        cost_indices = {}
        for tab_name, content in self.tabs_content.items():
            cost_num = content.get("cost", "1")
            idx = cost_indices.get(cost_num, 0) + 1
            cost_indices[cost_num] = idx
            
            # Key is (cost, index), e.g., ("4", 1) for the first cost-4 tab
            state_key = (cost_num, idx)
            
            main_val = content["main_widget"].currentText()
            sub_vals = []
            for stat_widget, val_widget in content["sub_entries"]:
                sub_vals.append((stat_widget.currentText(), val_widget.text()))
            state[state_key] = {
                "main_stat": main_val,
                "substats": sub_vals
            }
        return state

    def _calculate_cost_counts(self, tab_names: List[str]) -> Dict[str, int]:
        """Calculates the total count of each cost in the configuration."""
        totals = {}
        for name in tab_names:
            first_digit = next((ch for ch in name if ch.isdigit()), None)
            if first_digit:
                totals[first_digit] = totals.get(first_digit, 0) + 1
        return totals

    def _create_and_add_tab_page(self, tab_name: str, cost_num: str, cost_key: str) -> None:
        """Creates a single tab page and adds it to the notebook."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        
        # Main Stat Section
        main_group, main_combo = self._create_main_stat_section(page_layout, cost_num)
        
        # Substats Section
        sub_group, sub_entries = self._create_substat_section(page_layout)
        
        page_layout.addStretch()
        
        # Generate Label
        tab_label = self._generate_tab_label(tab_name)
        
        self.app.notebook.addTab(page, tab_label)
        
        # Store references
        self.tabs_content[tab_name] = {
            "cost": cost_num,
            "cost_key": cost_key,
            "main_group": main_group,
            "main_widget": main_combo,
            "sub_group": sub_group,
            "sub_entries": sub_entries
        }

    def _create_main_stat_section(self, layout: QVBoxLayout, cost_num: str) -> Tuple[QGroupBox, QComboBox]:
        """Creates the main stat selection group."""
        group = QGroupBox(self.app.tr("main_stat"))
        group_layout = QVBoxLayout(group)
        layout.addWidget(group)
        
        fallback_main_stats = ["HP", "ATK", "DEF"]
        main_opts = self.app.data_manager.main_stat_options.get(cost_num, fallback_main_stats)
        
        combo = QComboBox()
        for s in main_opts:
            combo.addItem(self.app.tr(s), userData=s)
        group_layout.addWidget(combo)
        return group, combo

    def _create_substat_section(self, layout: QVBoxLayout) -> Tuple[QGroupBox, List[Tuple[QComboBox, QLineEdit]]]:
        """Creates the substat entry group."""
        group = QGroupBox(self.app.tr("substats"))
        group_layout = QGridLayout(group)
        layout.addWidget(group)
        
        sub_entries = []
        sub_max_vals = self.app.data_manager.substat_max_values
        
        for i in range(5):
            row = i // 2
            col = i % 2
            
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            
            stat_combo = QComboBox()
            stat_combo.addItem("", userData="")
            for s in sub_max_vals.keys():
                stat_combo.addItem(self.app.tr(s), userData=s)
            
            val_entry = QLineEdit()
            val_entry.setFixedWidth(60)
            
            cell_layout.addWidget(stat_combo)
            cell_layout.addWidget(val_entry)
            
            group_layout.addWidget(cell_widget, row, col)
            sub_entries.append((stat_combo, val_entry))
            
        return group, sub_entries

    def _generate_tab_label(self, tab_name: str) -> str:
        """Generates a localized label for the tab."""
        if "cost" in tab_name:
            try:
                parts = tab_name.split('_')
                # parts[0] is like "cost4"
                c_num = parts[0].replace("cost", "")
                base_label = self.app.tr("cost_echo", c_num)
                
                suffix = ""
                # If there's a numbered suffix like _1, _2
                if len(parts) >= 3 and parts[2].isdigit():
                    suffix = f" {parts[2]}"
                
                return f"{base_label}{suffix}"
            except Exception as e:
                self.logger.warning(f"Failed to generate custom tab label for '{tab_name}': {e}")
        return tab_name

    def _restore_tab_data(self, tab_name: str, data: Dict[str, Any]) -> None:
        """Restores the state of a single tab."""
        if tab_name not in self.tabs_content:
            return
            
        content = self.tabs_content[tab_name]
        main_combo = content["main_widget"]
        sub_entries = content["sub_entries"]
        
        main_combo.setCurrentText(data.get("main_stat", ""))
        
        saved_substats = data.get("substats", [])
        for i, (s_val, v_val) in enumerate(saved_substats):
            if i < len(sub_entries):
                sub_entries[i][0].setCurrentText(s_val)
                sub_entries[i][1].setText(v_val)

    def extract_tab_data(self, tab_name: str) -> Optional[EchoEntry]:
        """
        Extracts data from the specified tab into a structured EchoEntry.
        Returns None if tab does not exist.
        """
        if tab_name not in self.tabs_content:
            return None
        
        content = self.tabs_content[tab_name]
        main_stat = content["main_widget"].currentData() # Use currentData for internal key
        cost = content.get("cost")
        
        substats = []
        for stat_widget, val_widget in content["sub_entries"]:
            s_key = stat_widget.currentData() # Use currentData for internal key
            v_text = val_widget.text()
            if s_key and v_text:
                substats.append(SubStat(stat=s_key, value=v_text))
                
        return EchoEntry(
            tab_index=0, # Placeholder or lookup real index if needed
            cost=cost,
            main_stat=main_stat,
            substats=substats
        )

    def get_all_echo_entries(self) -> List[EchoEntry]:
        """
        全タブのEchoEntryデータをリストで返す（重複検出用）
        """
        entries = []
        for tab_name in self.tabs_content:
            entry = self.extract_tab_data(tab_name)
            if entry:
                entries.append(entry)
        return entries

    @staticmethod
    def find_duplicate_entries(entries: List[EchoEntry]) -> List[int]:
        """
        完全一致するEchoEntryのインデックスリストを返す（重複IDリスト）
        各列（cost, main_stat, substats）全て一致で重複とみなす
        """
        seen = {}
        duplicates = []
        for idx, entry in enumerate(entries):
            # サブステータスをタプル化して順序も含めて比較
            substats_tuple = tuple((s.stat, s.value) for s in entry.substats)
            key = (entry.cost, entry.main_stat, substats_tuple)
            if key in seen:
                duplicates.append(idx)
            else:
                seen[key] = idx
        return duplicates

    def apply_character_main_stats(self, force: bool = False) -> None:
        """Automatically enters main stats."""
        if not force and not self.app.auto_apply_main_stats:
            return
            
        mainstats = self.app.character_manager.get_main_stats(self.app.character_var)
        
        if self.app.ui.character_combo:
            self.app.ui.character_combo.blockSignals(True)

        for tab_name, content in self.tabs_content.items():
            combo = content["main_widget"]
            # If no char is selected (mainstats is empty), this helper will default to "---"
            self.update_main_stat_combobox(combo, content, mainstats or {}, tab_name)
        
        if self.app.ui.character_combo:
            self.app.ui.character_combo.blockSignals(False)

    def update_main_stat_combobox(self, combo: 'QComboBox', content: Dict[str, Any], mainstats: Dict[str, Any], tab_name: str) -> None:
        """Helper to update a single main stat combobox."""
        try:
            combo.blockSignals(True)
            combo.clear()
            
            # 1. Collect candidate keys (internal Japanese names)
            keys = []
            
            # Try lookup by exact tab name (e.g. "cost4_echo") - Used in JSON profiles
            preferred = mainstats.get(tab_name)
            if preferred:
                if isinstance(preferred, list):
                    keys.extend(preferred)
                else:
                    keys.append(preferred)
            else:
                # 2. Fallback to cost-based lookup (Legacy/General support)
                cost_str = str(content.get("cost", ""))
                keys.extend(mainstats.get(cost_str, []))
            
            # If no character-specific options, use default options for this cost
            if not keys:
                cost_num = str(content.get("cost", "1"))
                keys = self.app.data_manager.main_stat_options.get(cost_num, ["HP", "ATK", "DEF"])

            # 2. Populate ComboBox with translation and internal key
            combo.addItem("---", userData="")
            for k in keys:
                combo.addItem(self.app.tr(k), userData=k)
            
            # Select preferred stat if we found one
            if preferred:
                target_stat = preferred[0] if isinstance(preferred, list) else preferred
                idx = combo.findData(target_stat)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            
            combo.blockSignals(False)
        except Exception as e:
            self.app.logger.exception(f"Error updating main stat combobox for '{tab_name}': {e}")
            combo.blockSignals(False)

    def apply_ocr_result(self, result: 'OCRResult') -> None:
        """
        Applies comprehensive OCR results to the currently selected tab.
        Includes substats and main stat.
        """
        for msg in result.log_messages:
            self.app.gui_log(msg)
        
        if not result.substats and not result.main_stat:
            self.app.gui_log("OCR completed but no usable data was parsed.")
            return
        
        tab_name = self.get_selected_tab_name()
        if not tab_name or tab_name not in self.tabs_content:
            self.app.gui_log(f"OCR auto-fill failed: Tab '{tab_name}' not found or not selected")
            return
        
        content = self.tabs_content[tab_name]
        
        # 1. Update Main Stat if detected
        if result.main_stat:
            main_combo = content.get("main_widget")
            if main_combo:
                idx = main_combo.findData(result.main_stat) # Use findData for internal key
                if idx >= 0:
                    main_combo.setCurrentIndex(idx)
                    translated_main = self.app.tr(result.main_stat)
                    self.app.gui_log(f"Auto-selected main stat: {translated_main}")

        # 2. Update Substats
        sub_entries = content["sub_entries"]
        # Clear substats first for clarity
        for stat_widget, val_widget in sub_entries:
            stat_widget.setCurrentIndex(0)
            val_widget.clear()

        for i, substat_data in enumerate(result.substats):
            if i < len(sub_entries):
                stat_key = getattr(substat_data, 'stat', "")
                num_found = getattr(substat_data, 'value', "")
                
                stat_widget = sub_entries[i][0]
                idx = stat_widget.findData(stat_key) # Use findData for internal key
                if idx >= 0:
                    stat_widget.setCurrentIndex(idx)
                
                sub_entries[i][1].setText(str(num_found))

        self.app.gui_log(f"Successfully applied OCR results to tab '{tab_name}'.")

    def fill_selected_tab_with_ocr_results(self, substats: List['SubStat'], log_messages: List[str]) -> None:
        """Legacy compatibility wrapper."""
        from data_contracts import OCRResult
        fake_result = OCRResult(substats=substats, log_messages=log_messages, cost=None, main_stat=None, raw_text="")
        self.apply_ocr_result(fake_result)
