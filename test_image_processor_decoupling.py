import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
import sys

# Ensure QApplication exists
app_instance = QApplication.instance()
if not app_instance:
    app_instance = QApplication(sys.argv)

from image_processor import ImageProcessor

class TestImageProcessorDecoupling(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.crop_mode_var = "percent"
        self.mock_app.crop_left_percent_var = 0.0
        self.mock_app.crop_top_percent_var = 0.0
        self.mock_app.crop_width_percent_var = 100.0
        self.mock_app.crop_height_percent_var = 100.0
        
        self.mock_logic = MagicMock()
        self.processor = ImageProcessor(self.mock_app, self.mock_logic)

    @patch('image_processor.is_pil_installed', True)
    @patch('image_processor.QFileDialog.getOpenFileNames')
    def test_import_image_cancel_emits_log(self, mock_get_open):
        # Setup mock to return empty list (cancelled)
        mock_get_open.return_value = ([], "filter")
        
        # Connect signal
        mock_slot = MagicMock()
        self.processor.logMessage.connect(mock_slot)
        
        # Run
        self.processor.import_image()
        
        # Verify signal emitted: "Image selection was cancelled."
        mock_slot.assert_called_with("Image selection was cancelled.")

    @patch('image_processor.is_pil_installed', True)
    def test_perform_crop_preview_emits_image(self):
        # Setup mocks
        self.mock_app.original_image = MagicMock()
        # Mock utils.crop_image_by_percent to return a dummy image
        with patch('image_processor.crop_image_by_percent') as mock_crop:
            mock_cropped_image = MagicMock()
            mock_crop.return_value = mock_cropped_image
            
            mock_slot = MagicMock()
            self.processor.imageUpdated.connect(mock_slot)
            
            self.processor.perform_crop_preview()
            
            # Should emit imageUpdated with the cropped image
            mock_slot.assert_called_with(mock_cropped_image)

if __name__ == '__main__':
    unittest.main()
