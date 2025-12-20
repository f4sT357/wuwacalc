"""
Score Calculation Module (PyQt6)

Provides the logic for calculating Echo scores.
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QMessageBox
from echo_data import EchoData
from languages import TRANSLATIONS
from data_contracts import EchoEntry

class ScoreCalculator:
    """Class responsible for score calculation."""
    
    def __init__(self, app: 'ScoreCalculatorApp', renderer: 'HtmlRenderer'):
        """
        Initialization
        
        Args:
            app: The main application instance.
            renderer: The HtmlRenderer instance.
        """
        self.app = app
        self.renderer = renderer
    
    def calculate_all_scores(self) -> None:
        """Calculate all scores (supports mode selection)."""
        try:
            character = self.app.character_var
            weights = self.app.character_manager.get_stat_weights(character)
            score_mode = self.app.score_mode_var
            
            if score_mode == "single":
                self.app.logger.info(f"Calculating scores for character '{character}' using weights: {weights}")
                self.calculate_single_score(weights, character)
            else:
                self.app.logger.info(f"Batch calculating scores for character '{character}' using weights: {weights}")
                self.calculate_batch_scores(weights, character)
                
        except Exception as e:
            self.app.logger.exception(f"An error occurred during score calculation: {e}")
            self.app.gui_log(f"An error occurred during score calculation:\n{e}")
            QMessageBox.critical(self.app, "Error", f"An error occurred during score calculation:\n{e}")
    
    def extract_substats_from_entry(self, entry: EchoEntry) -> Dict[str, float]:
        """Extract substats from EchoEntry."""
        substats = {}
        for sub in entry.substats:
            if sub.stat and sub.value:
                try:
                    clean_val = sub.value.replace('%', '').strip()
                    val = float(clean_val)
                    substats[sub.stat] = val
                except ValueError:
                    continue
        return substats
    
    def _get_config_bundle(self) -> Dict[str, Any]:
        """Helper to create the configuration bundle for EchoData."""
        dm = self.app.data_manager
        return {
            "substat_max_values": dm.substat_max_values,
            "main_stat_multiplier": dm.main_stat_multiplier,
            "roll_quality": dm.roll_quality_config,
            "effective_stats": dm.effective_stats_config,
            "cv_weights": dm.cv_weights
        }

    def calculate_single_score(self, weights: Dict[str, float], character: str) -> None:
        """Calculate a single score."""
        try:
            tab_name = self.app.tab_mgr.get_selected_tab_name()
            if not tab_name:
                QMessageBox.warning(self.app, "Warning", "No tab selected.")
                return

            entry = self.app.tab_mgr.extract_tab_data(tab_name)
            if not entry:
                 QMessageBox.critical(self.app, "Error", f"Failed to extract data for tab '{tab_name}'")
                 return
            
            enabled_methods = self.app.app_config.enabled_calc_methods
            if not any(enabled_methods.values()):
                QMessageBox.warning(self.app, self.app.tr("warning"), 
                                  self.app.tr("no_methods_selected"))
                return
            
            main_stat = entry.main_stat
            self.app.result_text.clear()
            
            if not main_stat:
                self.app.result_text.append(f"The main stat for {tab_name} is not entered.")
                return
            
            substats = self.extract_substats_from_entry(entry)
            echo = EchoData(entry.cost, main_stat, substats)
            config_bundle = self._get_config_bundle()
            evaluation = echo.evaluate_comprehensive(weights, config_bundle, enabled_methods)
            
            # Use renderer for HTML
            html = self.renderer.render_single_score(
                character, tab_name, entry, main_stat, echo, evaluation
            )
            
            self.app.result_text.setHtml(html)
            self.app.tab_mgr.save_tab_result(tab_name)
            self.app.gui_log(f"Individual evaluation for {tab_name} complete.")
            
        except Exception as e:
            self.app.logger.exception(f"Individual score calculation error: {e}")
            self.app.gui_log(f"Individual score calculation error: {e}")
            QMessageBox.critical(self.app, "Error", f"Individual score calculation error:\n{e}")
    
    def calculate_batch_scores(self, weights: Dict[str, float], character: str) -> None:
        """Calculate scores in batch."""
        try:
            enabled_methods = self.app.app_config.enabled_calc_methods
            if not any(enabled_methods.values()):
                QMessageBox.warning(self.app, self.app.tr("warning"), 
                                  self.app.tr("no_methods_selected"))
                return
            
            all_evaluations = []
            total_scores = {"total": 0.0}
            for method in ["normalized", "ratio", "roll", "effective", "cv"]:
                if enabled_methods.get(method, False):
                    total_scores[method] = 0.0
            
            calculated_count = 0
            config_bundle = self._get_config_bundle()

            for tab_name in self.app.tab_mgr.tabs_content.keys():
                try:
                    entry = self.app.tab_mgr.extract_tab_data(tab_name)
                    if not entry:
                        continue

                    main_stat = entry.main_stat
                    if not main_stat:
                        continue
                    
                    substats = self.extract_substats_from_entry(entry)
                    echo = EchoData(entry.cost, main_stat, substats)
                    evaluation = echo.evaluate_comprehensive(weights, config_bundle, enabled_methods)
                    
                    eval_data = {
                        "tab_name": tab_name,
                        "effective_count": evaluation['effective_count'],
                        "total": evaluation['total_score'],
                        "recommendation": TRANSLATIONS.get(self.app.language, TRANSLATIONS["en"])[evaluation['recommendation']]
                    }
                    
                    for method, score in evaluation['individual_scores'].items():
                        eval_data[method] = score
                        total_scores[method] += score
                    
                    all_evaluations.append(eval_data)
                    total_scores["total"] += evaluation['total_score']
                    calculated_count += 1
                    
                except Exception as e:
                    self.app.logger.exception(f"Calculation error for {tab_name}: {e}")
            
            self.app.result_text.clear()
            
            if calculated_count == 0:
                self.app.result_text.setText("No data available.\n")
            else:
                html = self.renderer.render_batch_score(
                    character, calculated_count, len(self.app.tab_mgr.tabs_content), 
                    all_evaluations, total_scores, enabled_methods
                )
                self.app.result_text.setHtml(html)
                self.app.gui_log(f"Batch calculation for {character} complete ({calculated_count} echoes).")
                
        except Exception as e:
            self.app.logger.exception(f"Batch calculation error: {e}")
            self.app.gui_log(f"Batch calculation error: {e}")
            QMessageBox.critical(self.app, "Error", f"Batch calculation error:\n{e}")