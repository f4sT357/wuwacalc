import unittest
from unittest.mock import MagicMock, patch, ANY
from score_calculator import ScoreCalculator
from data_contracts import EchoEntry, SubStat, EvaluationResult
from constants import ACTION_SINGLE, ACTION_BATCH

class TestScoreCalculator(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_renderer = MagicMock()
        self.calculator = ScoreCalculator(self.mock_app, self.mock_renderer)
        
        # Setup mocks for dependencies
        self.mock_app.data_manager.substat_max_values = {}
        self.mock_app.data_manager.main_stat_multiplier = {}
        self.mock_app.data_manager.roll_quality_config = {}
        self.mock_app.data_manager.effective_stats_config = {}
        self.mock_app.data_manager.cv_weights = {}
        self.mock_app.tr.side_effect = lambda x: f"tr_{x}"
        self.mock_app.app_config.history_duplicate_mode = "latest"

    @patch('score_calculator.EchoData')
    def test_process_echo_evaluation(self, MockEchoData):
        # Setup input
        entry = EchoEntry(0, "4", "ATK%", [SubStat("Crit Rate", "10.0")])
        weights = {"Crit Rate": 1.0}
        config = {}
        methods = {"normalized": True}
        
        # Mock EchoData behavior
        mock_echo_instance = MockEchoData.return_value
        mock_echo_instance.get_fingerprint.return_value = "hash123"
        mock_eval_result = EvaluationResult(100.0, 1, "S", "S", {})
        mock_echo_instance.evaluate_comprehensive.return_value = mock_eval_result
        
        # Run
        result = self.calculator._process_echo_evaluation(
            entry, weights, config, methods, "Char1", ACTION_SINGLE, "Tab1"
        )
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.total_score, 100.0)
        
        # Verify History Add
        self.mock_app.history_mgr.add_entry.assert_called_once_with(
            character="Char1",
            cost="4",
            action=ACTION_SINGLE,
            result=ANY,
            fingerprint="hash123",
            details={"score": 100.0},
            duplicate_mode="latest"
        )

    def test_calculate_single_score_calls_process(self):
        # Test that calculate_single_score correctly calls _process_echo_evaluation
        self.mock_app.tab_mgr.get_selected_tab_name.return_value = "Tab1"
        self.mock_app.tab_mgr.extract_tab_data.return_value = EchoEntry(0, "4", "Main", [])
        self.mock_app.app_config.enabled_calc_methods = {"method": True}
        
        with patch.object(self.calculator, '_process_echo_evaluation') as mock_process:
            mock_process.return_value = EvaluationResult(100.0, 1, "S", "S", {})
            
            self.calculator.calculate_single_score({}, "Char1")
            
            mock_process.assert_called_once()
            self.mock_renderer.render_single_score.assert_called_once()

    def test_evaluate_tab_for_batch_calls_process(self):
        # Test that _evaluate_tab_for_batch correctly calls _process_echo_evaluation
        self.mock_app.language = "en"
        self.mock_app.tab_mgr.extract_tab_data.return_value = EchoEntry(0, "4", "Main", [])
        
        with patch('score_calculator.TRANSLATIONS', {"en": {"S": "S_Rank"}}):
            with patch.object(self.calculator, '_process_echo_evaluation') as mock_process:
                mock_process.return_value = EvaluationResult(100.0, 1, "S", "S", {})
                
                result = self.calculator._evaluate_tab_for_batch("Tab1", {}, {}, {}, "Char1")
                
                mock_process.assert_called_once()
                self.assertIsNotNone(result)
                self.assertEqual(result["total"], 100.0)

if __name__ == '__main__':
    unittest.main()
