from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QGroupBox)
from utils.constants import OCR_ENGINE_PILLOW, OCR_ENGINE_OPENCV
from utils.utils import is_opencv_installed

class ImagePreprocessingSettingsDialog(QDialog):
    """Dialog for OCR (Image Preprocessing) settings."""
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(self.app.tr("image_preprocessing_settings") if self.app.tr("image_preprocessing_settings") != "image_preprocessing_settings" else "Image Preprocessing Settings")
        self.setMinimumSize(300, 100)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        ocr_group = QGroupBox(self.app.tr("ocr_settings") if self.app.tr("ocr_settings") != "ocr_settings" else "OCR Settings")
        ocr_layout = QVBoxLayout(ocr_group)

        ocr_row = QHBoxLayout()
        ocr_row.addWidget(QLabel(self.app.tr("ocr_engine") if self.app.tr("ocr_engine") != "ocr_engine" else "OCR Engine"))

        self.combo_ocr_engine = QComboBox()
        self.combo_ocr_engine.addItem("Standard (Pillow)", OCR_ENGINE_PILLOW)
        self.combo_ocr_engine.addItem("Advanced (OpenCV)", OCR_ENGINE_OPENCV)

        # Initial selection
        current_engine = self.app.app_config.ocr_engine
        if current_engine == OCR_ENGINE_OPENCV:
            self.combo_ocr_engine.setCurrentIndex(1)
        else:
            self.combo_ocr_engine.setCurrentIndex(0)

        ocr_row.addWidget(self.combo_ocr_engine)
        ocr_layout.addLayout(ocr_row)

        # Warning label if OpenCV is missing
        self.lbl_opencv_warning = QLabel("OpenCV is not installed. Using Standard mode.Run: pip install opencv-python")
        self.lbl_opencv_warning.setStyleSheet("color: red; font-size: 10px;")
        self.lbl_opencv_warning.setVisible(False)
        ocr_layout.addWidget(self.lbl_opencv_warning)

        # Logic to handle missing OpenCV
        if not is_opencv_installed:
            from PySide6.QtGui import QStandardItemModel
            model = self.combo_ocr_engine.model()
            if isinstance(model, QStandardItemModel):
                item = model.item(1)
                if item:
                    item.setEnabled(False) # Disable OpenCV item

            self.combo_ocr_engine.setCurrentIndex(0) # Force Pillow
            self.lbl_opencv_warning.setVisible(True)

        layout.addWidget(ocr_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton(self.app.tr("apply"))
        btn_apply.clicked.connect(self._apply_settings)

        btn_cancel = QPushButton(self.app.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _apply_settings(self):
        selected_engine = self.combo_ocr_engine.currentData()
        if selected_engine:
            self.app.app_config.ocr_engine = selected_engine
            self.app.config_manager.save()
            self.accept()
