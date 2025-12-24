"""
Tab Management Module (PyQt6)

Provides functions for managing, saving, restoring, clearing, and exporting tab data.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QComboBox, QLineEdit, QGridLayout, QTabWidget, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from data_contracts import EchoEntry, SubStat, OCRResult
from constants import DEFAULT_COST_CONFIG
import logging
import os

# Placeholder classes for data storage
class TabImageData:
    def __init__(self, original, cropped):
        self.original = original
        self.cropped = cropped

class TabResultData:
    def __init__(self, content):
        self.content = content

class TabManager(QObject):
    """
    Manages the echo tabs and their data.
    Decoupled from the main application class.
    """
    
    # Signals for UI notifications
    log_requested = pyqtSignal(str)
    tabs_updated = pyqtSignal()
    image_preview_requested = pyqtSignal(object) # Image.Image
    calculation_requested = pyqtSignal()

    def __init__(self, 
                 notebook: QTabWidget, 
                 data_manager: Any, 
                 config_manager: Any, 
                 tr_func: Callable):
        """
        Initialization with explicit dependencies.
        
        Args:
            notebook: The QTabWidget to manage.
            data_manager: DataManager instance.
            config_manager: ConfigManager instance.
            tr_func: Translation function.
        """
        super().__init__()
        self.notebook = notebook
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.tr = tr_func
        
        self.logger = logging.getLogger(__name__)
        self.tabs_content = {}
        self._updating_tabs = False
        
        # State storage (previously implicit or attached to app)
        self._tab_images: Dict[str, TabImageData] = {}
        self._tab_results: Dict[str, TabResultData] = {}
        self._last_character = None

    def get_selected_tab_name(self) -> Optional[str]:
        """Get the internal key of the currently selected tab."""
        if self.notebook is None:
            return None
        index = self.notebook.currentIndex()
        if index == -1:
            return None
            
        config_key = self.config_manager.get_app_config().current_config_key
        tab_configs = self.data_manager.tab_configs
        if config_key in tab_configs:
             keys = tab_configs[config_key]
             if index < len(keys):
                 return keys[index]
        
        return None

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
            
            self.log_requested.emit(f"Cleared the contents of tab '{tab_name}'.")
        except Exception as e:
            error_msg = f"Failed to clear tab: {e}"
            self.log_requested.emit(error_msg)
            self.logger.exception(f"Tab clear error: {e}")

    def clear_all(self) -> None:
        """Reset all tabs, text, logs, input values, etc."""
        try:
            # Reset all tab contents
            for content in self.tabs_content.values():
                self._reset_tab_content(content)
            
            self._tab_images.clear()
            self._tab_results.clear()
            self.log_requested.emit("All items have been cleared.")
        except Exception as e:
            self.log_requested.emit(f"Failed to reset items: {e}")
            self.logger.exception(f"Clear all error: {e}")

    def _reset_tab_content(self, content: Dict[str, Any]) -> None:
        """Resets the widgets of a single tab content."""
        content["main_widget"].setCurrentIndex(-1)
        for stat_widget, val_widget in content["sub_entries"]:
            stat_widget.setCurrentIndex(0) # Index 0 is usually empty
            val_widget.clear()

    def update_tabs(self) -> None:
        """Rebuilds the notebook tabs based on the current cost configuration."""
        if self.notebook is None:
            return
            
        self._updating_tabs = True
        try:
            config_key = self._validate_config_key()
            config_tab_names = self.data_manager.tab_configs[config_key]
            
            old_data = self._save_current_tab_state()
            
            self.notebook.clear()
            self.tabs_content = {}
            
            cost_counts = self._calculate_cost_counts(config_tab_names)
            current_cost_indices = {}
            
            for tab_name in config_tab_names:
                cost_num = next((ch for ch in tab_name if ch.isdigit()), "1")
                total_for_cost = cost_counts[cost_num]
                current_idx = current_cost_indices.get(cost_num, 0) + 1
                current_cost_indices[cost_num] = current_idx
                
                cost_key = cost_num if total_for_cost == 1 else f"{cost_num}_{current_idx}"
                
                self._create_and_add_tab_page(tab_name, cost_num, cost_key)
                
                state_key = (cost_num, current_idx)
                if state_key in old_data:
                    self._restore_tab_data(tab_name, old_data[state_key])
            
            self.tabs_updated.emit()
        except Exception as e:
            self.log_requested.emit(f"Tab update error: {e}")
            self.logger.exception("Tab update failed")
        finally:
            self._updating_tabs = False

    def retranslate_tabs(self, language: str) -> None:
        """Update all tab titles and internal labels based on the current language."""
        if self.notebook is None:
            return
            
        self._updating_tabs = True
        try:
            # Update Tab Titles
            config_key = self._validate_config_key()
            config_tab_names = self.data_manager.tab_configs.get(config_key, [])
            for i in range(min(self.notebook.count(), len(config_tab_names))):
                tab_name = config_tab_names[i]
                new_label = self._generate_tab_label(tab_name)
                self.notebook.setTabText(i, new_label)
            
            # Update Content in each tab
            for tab_name, content in self.tabs_content.items():
                content["main_group"].setTitle(self.tr("main_stat"))
                content["sub_group"].setTitle(self.tr("substats"))
                
                main_combo = content["main_widget"]
                current_main_key = main_combo.currentData()
                main_combo.blockSignals(True)
                main_combo.clear()
                cost_num = content["cost"]
                main_opts = self.data_manager.main_stat_options.get(cost_num, ["HP", "ATK", "DEF"])
                for s in main_opts:
                    main_combo.addItem(self.tr(s), userData=s)
                if current_main_key:
                    idx = main_combo.findData(current_main_key)
                    if idx != -1:
                        main_combo.setCurrentIndex(idx)
                main_combo.blockSignals(False)
                
                sub_max_vals = self.data_manager.substat_max_values
                for stat_combo, _ in content["sub_entries"]:
                    current_sub_key = stat_combo.currentData()
                    stat_combo.blockSignals(True)
                    stat_combo.clear()
                    stat_combo.addItem("", userData="")
                    for s in sub_max_vals.keys():
                        stat_combo.addItem(self.tr(s), userData=s)
                    if current_sub_key:
                        idx = stat_combo.findData(current_sub_key)
                        if idx != -1:
                            stat_combo.setCurrentIndex(idx)
                    stat_combo.blockSignals(False)
        finally:
            self._updating_tabs = False

    def _validate_config_key(self) -> str:
        config_key = self.config_manager.get_app_config().current_config_key
        if config_key not in self.data_manager.tab_configs:
            config_key = DEFAULT_COST_CONFIG
        return config_key

    def _save_current_tab_state(self) -> Dict[tuple, Any]:
        state = {}
        cost_indices = {}
        for tab_name, content in self.tabs_content.items():
            cost_num = content.get("cost", "1")
            idx = cost_indices.get(cost_num, 0) + 1
            cost_indices[cost_num] = idx
            state_key = (cost_num, idx)
            
            main_val = content["main_widget"].currentData()
            sub_vals = []
            for stat_widget, val_widget in content["sub_entries"]:
                sub_vals.append((stat_widget.currentData(), val_widget.text()))
            state[state_key] = {
                "main_stat": main_val,
                "substats": sub_vals
            }
        return state

    def _calculate_cost_counts(self, tab_names: List[str]) -> Dict[str, int]:
        totals = {}
        for name in tab_names:
            first_digit = next((ch for ch in name if ch.isdigit()), None)
            if first_digit:
                totals[first_digit] = totals.get(first_digit, 0) + 1
        return totals

    def _create_and_add_tab_page(self, tab_name: str, cost_num: str, cost_key: str) -> None:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        main_group, main_combo = self._create_main_stat_section(page_layout, cost_num)
        sub_group, sub_entries = self._create_substat_section(page_layout)
        page_layout.addStretch()
        tab_label = self._generate_tab_label(tab_name)
        self.notebook.addTab(page, tab_label)
        self.tabs_content[tab_name] = {
            "cost": cost_num,
            "cost_key": cost_key,
            "main_group": main_group,
            "main_widget": main_combo,
            "sub_group": sub_group,
            "sub_entries": sub_entries
        }

    def _create_main_stat_section(self, layout: QVBoxLayout, cost_num: str) -> Tuple[QGroupBox, QComboBox]:
        group = QGroupBox(self.tr("main_stat"))
        group_layout = QVBoxLayout(group)
        layout.addWidget(group)
        main_opts = self.data_manager.main_stat_options.get(cost_num, ["HP", "ATK", "DEF"])
        combo = QComboBox()
        for s in main_opts:
            combo.addItem(self.tr(s), userData=s)
        group_layout.addWidget(combo)
        return group, combo

    def _create_substat_section(self, layout: QVBoxLayout) -> Tuple[QGroupBox, List[Tuple[QComboBox, QLineEdit]]]:
        group = QGroupBox(self.tr("substats"))
        group_layout = QGridLayout(group)
        layout.addWidget(group)
        sub_entries = []
        sub_max_vals = self.data_manager.substat_max_values
        for i in range(5):
            row = i // 2
            col = i % 2
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            stat_combo = QComboBox()
            stat_combo.addItem("", userData="")
            for s in sub_max_vals.keys():
                stat_combo.addItem(self.tr(s), userData=s)
            val_entry = QLineEdit()
            val_entry.setFixedWidth(60)
            cell_layout.addWidget(stat_combo)
            cell_layout.addWidget(val_entry)
            group_layout.addWidget(cell_widget, row, col)
            sub_entries.append((stat_combo, val_entry))
        return group, sub_entries

    def _generate_tab_label(self, tab_name: str) -> str:
        if "cost" in tab_name:
            try:
                parts = tab_name.split('_')
                c_num = parts[0].replace("cost", "")
                base_label = self.tr("cost_echo", c_num)
                suffix = f" {parts[2]}" if len(parts) >= 3 and parts[2].isdigit() else ""
                return f"{base_label}{suffix}"
            except Exception as e:
                self.logger.warning(f"Failed to generate custom tab label for '{tab_name}': {e}")
        return tab_name

    def _restore_tab_data(self, tab_name: str, data: Dict[str, Any]) -> None:
        if tab_name not in self.tabs_content:
            return
        content = self.tabs_content[tab_name]
        main_combo = content["main_widget"]
        sub_entries = content["sub_entries"]
        
        main_val = data.get("main_stat", "")
        idx = main_combo.findData(main_val)
        if idx >= 0:
            main_combo.setCurrentIndex(idx)
        
        saved_substats = data.get("substats", [])
        for i, (s_key, v_val) in enumerate(saved_substats):
            if i < len(sub_entries):
                s_idx = sub_entries[i][0].findData(s_key)
                if s_idx >= 0:
                    sub_entries[i][0].setCurrentIndex(s_idx)
                sub_entries[i][1].setText(str(v_val))

    def extract_tab_data(self, tab_name: str) -> Optional[EchoEntry]:
        if tab_name not in self.tabs_content:
            return None
        content = self.tabs_content[tab_name]
        main_stat = content["main_widget"].currentData()
        cost = content.get("cost")
        substats = []
        for stat_widget, val_widget in content["sub_entries"]:
            s_key = stat_widget.currentData()
            v_text = val_widget.text()
            if s_key and v_text:
                substats.append(SubStat(stat=s_key, value=v_text))
        return EchoEntry(tab_index=0, cost=cost, main_stat=main_stat, substats=substats)

    def get_all_echo_entries(self) -> List[EchoEntry]:
        entries = []
        for tab_name in self.tabs_content:
            entry = self.extract_tab_data(tab_name)
            if entry:
                entries.append(entry)
        return entries

    def find_duplicate_entries(self, entries: List[EchoEntry]) -> List[int]:
        seen = {}
        duplicates = []
        for idx, entry in enumerate(entries):
            substats_tuple = tuple((s.stat, s.value) for s in entry.substats)
            key = (entry.cost, entry.main_stat, substats_tuple)
            if key in seen:
                duplicates.append(idx)
            else:
                seen[key] = idx
        return duplicates

    def apply_character_main_stats(self, force: bool = False, character: str = None) -> None:
        if not character:
            character = self.config_manager.get_app_config().character_var
        if not character:
            return
        if not force and not self.config_manager.get_app_config().auto_apply_main_stats:
            return
        mainstats = self.data_manager.character_main_stats.get(character, {})
        for tab_name, content in self.tabs_content.items():
            self._update_main_stat_combobox(content["main_widget"], content, mainstats, tab_name)

    def _update_main_stat_combobox(self, combo: QComboBox, content: Dict[str, Any], mainstats: Dict[str, Any], tab_name: str) -> None:
        try:
            combo.blockSignals(True)
            current_data = combo.currentData()
            combo.clear()
            keys = []
            preferred = mainstats.get(tab_name)
            if preferred:
                keys.extend(preferred if isinstance(preferred, list) else [preferred])
            else:
                cost_str = str(content.get("cost", ""))
                keys.extend(mainstats.get(cost_str, []))
            
            if not keys:
                cost_num = str(content.get("cost", "1"))
                keys = self.data_manager.main_stat_options.get(cost_num, ["HP", "ATK", "DEF"])

            combo.addItem("---", userData="")
            for k in keys:
                combo.addItem(self.tr(k), userData=k)
            
            if preferred:
                target_stat = preferred[0] if isinstance(preferred, list) else preferred
                idx = combo.findData(target_stat)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            elif current_data:
                idx = combo.findData(current_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        except Exception as e:
            self.logger.exception(f"Error updating main stat combobox for '{tab_name}': {e}")
            combo.blockSignals(False)

    def apply_ocr_result(self, result: OCRResult) -> None:
        """Applies OCR results to the currently selected tab."""
        tab_name = self.get_selected_tab_name()
        if tab_name:
            self.apply_ocr_result_to_tab(tab_name, result)

    def apply_ocr_result_to_tab(self, tab_name: str, result: OCRResult) -> None:
        """Applies OCR results to a specific tab."""
        if tab_name not in self.tabs_content:
            return
        
        content = self.tabs_content[tab_name]
        
        # Apply Main Stat
        if result.main_stat:
            idx = content["main_widget"].findData(result.main_stat)
            if idx >= 0:
                content["main_widget"].setCurrentIndex(idx)
                self.log_requested.emit(f"[{tab_name}] Auto-selected main stat: {self.tr(result.main_stat)}")

        # Apply Substats
        sub_entries = content["sub_entries"]
        for stat_widget, val_widget in sub_entries:
            stat_widget.setCurrentIndex(0)
            val_widget.clear()

        for i, substat_data in enumerate(result.substats):
            if i < len(sub_entries):
                idx = sub_entries[i][0].findData(substat_data.stat)
                if idx >= 0:
                    sub_entries[i][0].setCurrentIndex(idx)
                sub_entries[i][1].setText(str(substat_data.value))

    def save_tab_image(self, tab_name: str, original: Any, cropped: Any) -> None:
        self._tab_images[tab_name] = TabImageData(original=original, cropped=cropped)

    def get_tab_image(self, tab_name: str) -> Optional[TabImageData]:
        return self._tab_images.get(tab_name)

    def save_tab_result(self, tab_name: str, html_content: str) -> None:
        self._tab_results[tab_name] = TabResultData(content=html_content)

    def get_tab_result(self, tab_name: str) -> Optional[str]:
        data = self._tab_results.get(tab_name)
        return data.content if data else None

    def export_to_txt(self, parent_window: QWidget, text: str) -> None:
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                parent_window, "Save Result", "", "Text Files (*.txt);;All Files (*.*)"
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.log_requested.emit(f"Exported result to: {file_path}")
        except Exception as e:
            self.logger.exception(f"Export failed: {e}")
            self.log_requested.emit(f"Export failed: {e}")