from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QRubberBand, QMessageBox)
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QPixmap, QImage
from constants import DIALOG_CROP_WIDTH, DIALOG_CROP_HEIGHT

try:
    from PIL import Image, ImageQt
    is_pil_installed = True
except ImportError:
    is_pil_installed = False

class CropLabel(QLabel):
    """QLabel with rubber band selection."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.current_rect = QRect()
        self.is_selecting = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
            self.is_selecting = True

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
            self.current_rect = self.rubberBand.geometry()

    def get_selection(self):
        return self.current_rect

class CropDialog(QDialog):
    """Dialog for selecting and inputting image crop method (interactive)."""

    def __init__(self, parent, pil_image):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(self.app.tr("crop_title"))
        self.resize(DIALOG_CROP_WIDTH, DIALOG_CROP_HEIGHT)
        self.crop_result = None
        self.pil_image = pil_image
        self.scale_ratio = 1.0

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(self.app.tr("crop_instruction")))

        self.image_label = CropLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Load and display
        self._load_and_display_image()

        layout.addWidget(self.image_label) # Wrap in ScrollArea for better UX? Original didn't.

        # Buttons
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton(self.app.tr("reset"))
        btn_reset.clicked.connect(self._reset_selection)

        btn_ok = QPushButton(self.app.tr("ok"))
        btn_ok.clicked.connect(self._ok)

        btn_cancel = QPushButton(self.app.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _load_and_display_image(self):
        if not self.pil_image or not is_pil_installed:
            return

        max_w, max_h = 850, 550
        w, h = self.pil_image.size

        scale_w = max_w / w
        scale_h = max_h / h
        self.scale_ratio = min(scale_w, scale_h, 1.0)

        new_w = int(w * self.scale_ratio)
        new_h = int(h * self.scale_ratio)

        # Ensure image is in a display-friendly mode and loaded
        if self.pil_image.mode != "RGBA" and self.pil_image.mode != "RGB":
            display_img = self.pil_image.convert("RGBA")
        else:
            display_img = self.pil_image

        resized = display_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.qim = ImageQt.ImageQt(resized)
        pixmap = QPixmap.fromImage(self.qim)

        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(new_w, new_h) 

    def _reset_selection(self):
        self.image_label.rubberBand.hide()
        self.image_label.current_rect = QRect()

    def _ok(self):
        rect = self.image_label.get_selection()
        if rect.isEmpty():
            # Entire image
            self.crop_result = ('coords', 0, 0, self.pil_image.size[0], self.pil_image.size[1])
            self.accept()
            return

        # Convert coords
        x1 = rect.x()
        y1 = rect.y()
        x2 = rect.right()
        y2 = rect.bottom()

        orig_left = int(x1 / self.scale_ratio)
        orig_top = int(y1 / self.scale_ratio)
        orig_right = int(x2 / self.scale_ratio)
        orig_bottom = int(y2 / self.scale_ratio)

        # Limit
        orig_left = max(0, orig_left)
        orig_top = max(0, orig_top)
        orig_right = min(self.pil_image.size[0], orig_right)
        orig_bottom = min(self.pil_image.size[1], orig_bottom)

        if (orig_right - orig_left) < 5 or (orig_bottom - orig_top) < 5:
            QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("crop_too_small"))
            return

        self.crop_result = ('coords', orig_left, orig_top, orig_right, orig_bottom)
        self.accept()
