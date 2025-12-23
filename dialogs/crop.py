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
        self.percent_label = None
        self.confirm_checkbox = None
        self.last_percent = None
        self.init_ui()

    def init_ui(self):
        import json
        import os
        from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.app.tr("crop_instruction")))

        self.image_label = CropLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # パーセント表示用ラベル
        self.percent_label = QLabel("")
        layout.addWidget(self.percent_label)

        # 適用確認用チェックボックス
        self.confirm_checkbox = QCheckBox(self.app.tr("crop_confirm_apply"))
        self.confirm_checkbox.setChecked(True)
        layout.addWidget(self.confirm_checkbox)

        # --- プリセットUI ---
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(False)
        self.preset_combo.setMinimumWidth(120)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText(self.app.tr("preset_name_placeholder") if hasattr(self.app, 'tr') else "名前")
        self.preset_input = QLineEdit()
        self.preset_input.setPlaceholderText("例: 50x50")
        btn_save = QPushButton(self.app.tr("save"))
        btn_load = QPushButton(self.app.tr("load"))
        btn_delete = QPushButton(self.app.tr("delete"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.preset_name_input)
        preset_layout.addWidget(self.preset_input)
        preset_layout.addWidget(btn_save)
        preset_layout.addWidget(btn_load)
        preset_layout.addWidget(btn_delete)
        layout.addLayout(preset_layout)

        self._preset_file = os.path.join(os.path.dirname(__file__), "..", "crop_presets.json")
        self._load_presets()
        btn_save.clicked.connect(self._save_preset)
        btn_load.clicked.connect(self._apply_preset)
        btn_delete.clicked.connect(self._delete_preset)
        self.preset_combo.currentIndexChanged.connect(self._preset_combo_changed)

        # Load and display
        self._load_and_display_image()
        layout.addWidget(self.image_label)

        # CropLabelのマウスリリースでパーセント更新
        self.image_label.mouseReleaseEvent = self._wrap_mouse_release(self.image_label.mouseReleaseEvent)

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

    def _load_presets(self):
        import json, os
        self.presets = []
        try:
            preset_path = os.path.abspath(self._preset_file)
            if os.path.exists(preset_path):
                with open(preset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.presets = data.get("crop_presets", [])
        except Exception:
            self.presets = []
        self.preset_combo.clear()
        for p in self.presets:
            self.preset_combo.addItem(p.get("name", f"{p['w']}x{p['h']}"))

    def _save_presets_to_file(self):
        import json, os
        try:
            preset_path = os.path.abspath(self._preset_file)
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump({"crop_presets": self.presets}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_preset(self):
        text = self.preset_input.text().strip()
        name = self.preset_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("preset_name_required") if hasattr(self.app, 'tr') else "プリセット名を入力してください")
            return
        # 入力が空ならlast_percentを使う
        if not text and self.last_percent:
            w, h = self.last_percent
        else:
            if "x" not in text:
                QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("preset_format"))
                return
            try:
                # 入力値がピクセル数ならパーセントに変換
                if self.pil_image:
                    img_w, img_h = self.pil_image.size
                    vals = text.split("x")
                    if len(vals) == 2:
                        v1, v2 = vals
                        if v1.strip().endswith("%") or v2.strip().endswith("%"):
                            w = float(v1.strip().replace("%", ""))
                            h = float(v2.strip().replace("%", ""))
                        else:
                            # ピクセル数→パーセント
                            w = float(v1) / img_w * 100
                            h = float(v2) / img_h * 100
                    else:
                        raise ValueError()
                else:
                    raise ValueError()
            except Exception:
                QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("preset_format"))
                return
        self.presets.append({"name": name, "w": w, "h": h})
        self._save_presets_to_file()
        self._load_presets()

    def _apply_preset(self):
        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(self.presets):
            return
        preset = self.presets[idx]
        w, h = preset["w"], preset["h"]
        img_w, img_h = self.pil_image.size
        crop_w = int(img_w * w / 100)
        crop_h = int(img_h * h / 100)
        # センタリング
        left = (img_w - crop_w) // 2
        top = (img_h - crop_h) // 2
        right = left + crop_w
        bottom = top + crop_h
        # スケール変換
        left_s = int(left * self.scale_ratio)
        top_s = int(top * self.scale_ratio)
        right_s = int(right * self.scale_ratio)
        bottom_s = int(bottom * self.scale_ratio)
        self.image_label.rubberBand.setGeometry(QRect(left_s, top_s, right_s-left_s, bottom_s-top_s))
        self.image_label.rubberBand.show()
        self.image_label.current_rect = QRect(left_s, top_s, right_s-left_s, bottom_s-top_s)
        self._update_percent_label()

    def _delete_preset(self):
        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(self.presets):
            return
        del self.presets[idx]
        self._save_presets_to_file()
        self._load_presets()

    def _preset_combo_changed(self, idx):
        if idx < 0 or idx >= len(self.presets):
            return
        preset = self.presets[idx]
        self.preset_name_input.setText(preset['name'])
        self.preset_input.setText(f"{preset['w']:.1f}x{preset['h']:.1f}")

    def _wrap_mouse_release(self, orig_func):
        def wrapped(event):
            orig_func(event)
            self._update_percent_label()
        return wrapped

    def _update_percent_label(self):
        rect = self.image_label.get_selection()
        if rect.isEmpty():
            self.percent_label.setText("")
            self.last_percent = None
            return
        x1, y1, x2, y2 = rect.x(), rect.y(), rect.right(), rect.bottom()
        w, h = self.pil_image.size
        crop_w = int((x2 - x1) / self.scale_ratio)
        crop_h = int((y2 - y1) / self.scale_ratio)
        percent_w = crop_w / w * 100
        percent_h = crop_h / h * 100
        self.last_percent = (percent_w, percent_h)
        self.percent_label.setText(f"{percent_w:.1f}% x {percent_h:.1f}%")
        # 入力欄に自動反映
        if self.preset_input is not None:
            self.preset_input.setText(f"{percent_w:.1f}x{percent_h:.1f}")

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
        self._update_percent_label()

    def _ok(self):
        if self.confirm_checkbox and not self.confirm_checkbox.isChecked():
            QMessageBox.information(self, self.app.tr("info"), self.app.tr("crop_confirm_needed"))
            return
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
