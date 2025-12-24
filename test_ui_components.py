import sys
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QMainWindow

# Ensure QApplication exists only once
app_instance = QApplication.instance()
if not app_instance:
    app_instance = QApplication(sys.argv)

from ui_components import UIComponents, SettingsPanel

class TestUIComponents(unittest.TestCase):
    def setUp(self):
        # Use QMainWindow to satisfy QObject type checks
        self.mock_app = QMainWindow()
        
        # Mock tr method
        self.mock_app.tr = MagicMock(side_effect=lambda x: f"tr_{x}")
        
        # Mock data manager
        self.mock_app.data_manager = MagicMock()
        self.mock_app.data_manager.tab_configs = {"default": []}
        
        # Mock app properties
        self.mock_app.current_config_key = "default"
        self.mock_app.language = "en"
        self.mock_app.mode_var = "manual"
        self.mock_app.score_mode_var = "batch"
        self.mock_app.auto_apply_main_stats = True
        
        # Mock app_config
        self.mock_app.app_config = MagicMock()
        self.mock_app.app_config.enabled_calc_methods = {}
        self.mock_app.app_config.crop_left_percent = 0.0
        self.mock_app.app_config.crop_top_percent = 0.0
        self.mock_app.app_config.crop_width_percent = 0.0
        self.mock_app.app_config.crop_height_percent = 0.0
        self.mock_app.crop_mode_var = "percent"
        
        # Mock events handler
        self.mock_app.events = MagicMock()
        
        # Mock other dependencies accessed in create_main_layout
        self.mock_app.score_calc = MagicMock()
        self.mock_app.tab_mgr = MagicMock()
        self.mock_app.image_proc = MagicMock()
        self.mock_app._open_readme = MagicMock()
        self.mock_app.open_display_settings = MagicMock()
        self.mock_app.open_image_preprocessing_settings = MagicMock()
        self.mock_app.open_history = MagicMock()
        self.mock_app.open_char_settings_new = MagicMock()
        self.mock_app.open_char_settings_edit = MagicMock()
        
        # Mock image related attributes
        self.mock_app.loaded_image = None
        self.mock_app.image_label = None

        self.ui = UIComponents(self.mock_app)

    def test_settings_panel_initialization(self):
        """Test that SettingsPanel is correctly initialized and linked."""
        self.assertIsInstance(self.ui.settings_panel, SettingsPanel)
        self.assertEqual(self.ui.settings_panel.app, self.mock_app)
        self.assertEqual(self.ui.settings_panel.ui, self.ui)

    def test_property_delegation(self):
        """Test that UIComponents properties delegate to SettingsPanel widgets."""
        # Check a few critical properties
        self.assertIs(self.ui.character_combo, self.ui.settings_panel.character_combo)
        self.assertIs(self.ui.mode_button_group, self.ui.settings_panel.mode_button_group)
        
        # Note: Some properties return None before setup_ui is called, 
        # so we verify they access the correct attribute on settings_panel
        # by checking the initial None state
        self.assertIsNone(self.ui.lbl_cost_config)
        self.assertIsNone(self.ui.settings_panel.lbl_cost_config)

    def test_layout_creation(self):
        """Test that create_main_layout correctly constructs the UI hierarchy."""
        # We need to ensure QWidget creation works (requires QApplication, handled at top)
        try:
            self.ui.create_main_layout()
        except Exception as e:
            self.fail(f"create_main_layout raised exception: {e}")
            
        self.assertIsNotNone(self.ui.main_widget)
        self.assertIsNotNone(self.ui.settings_panel.settings_group)
        
        # Verify settings widgets are populated
        self.assertIsNotNone(self.ui.settings_panel.lbl_cost_config)
        self.assertIsNotNone(self.ui.settings_panel.app.config_combo)

    def test_retranslate_ui(self):
        """Test that retranslate_ui calls the settings panel's retranslate."""
        # First create layout to populate widgets
        self.ui.create_main_layout()
        
        # Mock the settings_panel.retranslate_ui method to verify it's called
        with patch.object(self.ui.settings_panel, 'retranslate_ui') as mock_retranslate:
            self.ui.retranslate_ui()
            mock_retranslate.assert_called_once()

if __name__ == '__main__':
    unittest.main()
