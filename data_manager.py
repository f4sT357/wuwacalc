import json
import os
import logging
from typing import Dict, Any, List

from constants import (
    KEY_SUBSTATS, KEY_STAT, KEY_VALUE, KEY_CHARACTER, KEY_CHARACTER_JP
)
from data_contracts import DataLoadError

class DataManager:
    """
    Manages loading and accessing external data configuration.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.game_data_path = os.path.join(data_dir, "game_data.json")
        self.calc_config_path = os.path.join(data_dir, "calculation_config.json")
        
        self.game_data: Dict[str, Any] = {}
        self.calc_config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    def load_all(self) -> None:
        """
        Loads both game data and calculation config.
        Raises DataLoadError if critical data cannot be loaded.
        """
        self.load_game_data()
        self.load_calc_config()

    def load_game_data(self) -> None:
        """
        Loads game data from JSON.
        Raises:
            DataLoadError: If file is missing or invalid JSON.
        """
        if not os.path.exists(self.game_data_path):
            self.logger.critical(f"Game data file not found: {self.game_data_path}")
            raise DataLoadError(f"Game data file missing: {self.game_data_path}")

        try:
            with open(self.game_data_path, 'r', encoding='utf-8') as f:
                self.game_data = json.load(f)
            self.logger.info(f"Loaded game data from {self.game_data_path}")
        except json.JSONDecodeError as e:
            self.logger.critical(f"Invalid JSON in game data: {e}")
            raise DataLoadError(f"Game data corrupted: {e}")
        except Exception as e:
            self.logger.critical(f"Failed to load game data: {e}")
            raise DataLoadError(f"Failed to load game data: {e}")

    def load_calc_config(self) -> None:
        """
        Loads calculation config from JSON.
        Raises:
            DataLoadError: If file is missing or invalid JSON.
        """
        if not os.path.exists(self.calc_config_path):
            self.logger.critical(f"Calculation config file not found: {self.calc_config_path}")
            raise DataLoadError(f"Config file missing: {self.calc_config_path}")

        try:
            with open(self.calc_config_path, 'r', encoding='utf-8') as f:
                self.calc_config = json.load(f)
            self.logger.info(f"Loaded calculation config from {self.calc_config_path}")
        except json.JSONDecodeError as e:
            self.logger.critical(f"Invalid JSON in calculation config: {e}")
            raise DataLoadError(f"Calculation config corrupted: {e}")
        except Exception as e:
            self.logger.critical(f"Failed to load calculation config: {e}")
            raise DataLoadError(f"Failed to load calculation config: {e}")

    # --- Property Accessors for Convenience ---

    @property
    def substat_max_values(self) -> Dict[str, float]:
        return self.game_data.get("substat_max_values", {})

    @property
    def main_stat_options(self) -> Dict[str, List[str]]:
        return self.game_data.get("main_stat_options", {})

    @property
    def substat_types(self) -> Dict[str, str]:
        return self.game_data.get("substat_types", {})

    @property
    def character_stat_weights(self) -> Dict[str, Dict[str, float]]:
        return self.game_data.get("character_stat_weights", {})
    
    @property
    def character_main_stats(self) -> Dict[str, Dict[str, str]]:
        return self.game_data.get("character_main_stats", {})

    @property
    def stat_aliases(self) -> Dict[str, List[str]]:
        return self.game_data.get("stat_aliases", {})
    
    @property
    def tab_configs(self) -> Dict[str, List[str]]:
        return self.game_data.get("tab_configs", {})

    @property
    def char_name_map_jp_to_en(self) -> Dict[str, str]:
        return self.game_data.get("char_name_map_jp_to_en", {})

    @property
    def main_stat_multiplier(self) -> float:
        return self.calc_config.get("main_stat_multiplier", 15.0)

    @property
    def roll_quality_config(self) -> Dict[str, Any]:
        return self.calc_config.get("roll_quality", {})

    @property
    def effective_stats_config(self) -> Dict[str, Any]:
        return self.calc_config.get("effective_stats", {})

    @property
    def cv_weights(self) -> Dict[str, float]:
        return self.calc_config.get("cv_weights", {})
    
    @property
    def character_config_map(self) -> Dict[str, str]:
        return self.game_data.get("character_config_map", {})
