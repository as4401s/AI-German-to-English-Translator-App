from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QTextEdit, QCheckBox, QWidget, QComboBox,
)

class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setStyleSheet("""
            #GlassCard {
                background: rgba(15, 15, 20, 0.7);
                border-radius: 16px;
                border: 1px solid rgba(74, 144, 226, 0.2);
            }
        """)

class TranslatorPanel(GlassCard):
    start_clicked = Signal()
    stop_clicked = Signal()
    pick_region_clicked = Signal()
    always_on_top_toggled = Signal(bool)
    copy_clicked = Signal()
    clear_clicked = Signal()
    show_german_toggled = Signal(bool)
    font_size_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        # Header - compact and modern with glassy look
        header = QLabel("Live Translate")
        header_font = QFont("SF Pro Display", 22)  # Modern font
        header_font.setBold(True)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        header.setStyleSheet("""
            background: transparent;
            color: #f0f0f0; 
            margin-bottom: 2px; 
            letter-spacing: 0.5px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        """)
        
        sub = QLabel("Real-time screen translation • German → English • Opus (offline) or Ollama (Gemma, etc.)")
        sub_font = QFont("SF Pro Text", 11)
        sub.setFont(sub_font)
        sub.setStyleSheet("""
            background: transparent;
            color: rgba(160, 160, 170, 0.8); 
            font-size: 11px; 
            margin-bottom: 4px; 
            letter-spacing: 0.3px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        """)

        # Control buttons row - compact
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.pick_btn = QPushButton("🎯 Select")
        self.start_btn = QPushButton("▶️ Start")
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)

        self.model_label = QLabel("Model")
        self.model_label.setStyleSheet("background: transparent; color: rgba(180, 180, 195, 0.95); font-size: 11px;")
        self.model_combo = QComboBox()
        self._populate_default_models()
        combo_font = QFont("SF Pro Text", 12)
        self.model_combo.setFont(combo_font)
        self.model_combo.setMinimumWidth(280)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(13, 27, 42, 0.6);
                color: #c5d4f0;
                border: 1px solid rgba(74, 144, 226, 0.3);
                border-radius: 8px;
                padding: 6px 12px;
                min-height: 28px;
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow { image: none; width:0; height:0; border: none; }
            QComboBox QAbstractItemView {
                background: rgba(20, 24, 32, 0.95);
                color: #e8e8f0;
                selection-background-color: rgba(74, 144, 226, 0.5);
            }
        """)
        
        # Modern glassy buttons with dark blue accents
        button_font = QFont("SF Pro Text", 13)
        button_font.setWeight(QFont.Weight.Medium)
        
        button_style = """
            QPushButton {
                background: rgba(13, 27, 42, 0.6);
                color: #6ba3f0;
                border: 1px solid rgba(74, 144, 226, 0.3);
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                min-height: 32px;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton:hover {
                background: rgba(26, 47, 74, 0.8);
                color: #8bb5ff;
                border-color: rgba(74, 144, 226, 0.5);
            }
            QPushButton:pressed {
                background: rgba(10, 21, 32, 0.9);
                color: #4a90e2;
                border-color: rgba(74, 144, 226, 0.4);
            }
            QPushButton:disabled {
                background: rgba(10, 10, 10, 0.4);
                color: rgba(100, 100, 100, 0.5);
                border-color: rgba(26, 26, 26, 0.3);
            }
        """
        
        stop_button_style = """
            QPushButton {
                background: rgba(42, 13, 13, 0.6);
                color: #f06b6b;
                border: 1px solid rgba(212, 74, 74, 0.3);
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                min-height: 32px;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton:hover {
                background: rgba(74, 26, 26, 0.8);
                color: #ff8b8b;
                border-color: rgba(212, 74, 74, 0.5);
            }
            QPushButton:pressed {
                background: rgba(26, 10, 10, 0.9);
                color: #d44a4a;
                border-color: rgba(212, 74, 74, 0.4);
            }
            QPushButton:disabled {
                background: rgba(10, 10, 10, 0.4);
                color: rgba(100, 100, 100, 0.5);
                border-color: rgba(26, 26, 26, 0.3);
            }
        """
        
        self.pick_btn.setStyleSheet(button_style)
        self.pick_btn.setFont(button_font)
        self.start_btn.setStyleSheet(button_style)
        self.start_btn.setFont(button_font)
        self.stop_btn.setStyleSheet(stop_button_style)
        self.stop_btn.setFont(button_font)
        
        row1.addWidget(self.pick_btn)
        row1.addWidget(self.start_btn)
        row1.addWidget(self.stop_btn)

        # Options - compact
        model_row = QHBoxLayout()
        model_row.setSpacing(10)
        model_row.addWidget(self.model_label)
        model_row.addWidget(self.model_combo, stretch=1)
        self.aot_check = QCheckBox("Always on top")
        self.aot_check.setChecked(True)
        checkbox_font = QFont("SF Pro Text", 11)
        checkbox_style = """
            QCheckBox {
                color: rgba(200, 200, 210, 0.9);
                font-size: 11px;
                spacing: 6px;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid rgba(74, 144, 226, 0.4);
                border-radius: 4px;
                background: rgba(10, 10, 10, 0.5);
            }
            QCheckBox::indicator:checked {
                background: rgba(74, 144, 226, 0.8);
                border-color: rgba(74, 144, 226, 0.6);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(107, 163, 240, 0.6);
                background: rgba(26, 47, 74, 0.4);
            }
        """
        self.aot_check.setFont(checkbox_font)
        self.aot_check.setStyleSheet(checkbox_style)

        self.show_german_check = QCheckBox("Show German")
        self.show_german_check.setChecked(False)
        self.show_german_check.setFont(checkbox_font)
        self.show_german_check.setStyleSheet(checkbox_style)

        options_model_aot = QVBoxLayout()
        options_model_aot.setSpacing(8)
        options_model_aot.addLayout(model_row)
        aot_row = QHBoxLayout()
        aot_row.addWidget(self.aot_check)
        aot_row.addSpacing(16)
        aot_row.addWidget(self.show_german_check)
        aot_row.addStretch()
        options_model_aot.addLayout(aot_row)
        options_layout = QHBoxLayout()
        options_layout.addLayout(options_model_aot, stretch=1)

        # Preview section - smaller and modern with glassy look
        preview_label = QLabel("📸 Preview")
        preview_label_font = QFont("SF Pro Text", 11)
        preview_label_font.setWeight(QFont.Weight.Medium)
        preview_label.setFont(preview_label_font)
        preview_label.setStyleSheet("""
            background: transparent;
            color: rgba(160, 160, 170, 0.9); 
            font-size: 11px; 
            font-weight: 500; 
            margin-top: 4px; 
            letter-spacing: 0.3px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        """)

        self.preview = QLabel("Select a region to begin")
        self.preview.setFixedHeight(120)  # Reduced height
        self.preview.setAlignment(Qt.AlignCenter)
        preview_font = QFont("SF Pro Text", 11)
        self.preview.setFont(preview_font)
        self.preview.setStyleSheet("""
            QLabel {
                background: rgba(15, 15, 20, 0.5);
                border: 1px solid rgba(74, 144, 226, 0.15);
                border-radius: 10px;
                color: rgba(120, 120, 130, 0.8);
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
        """)

        translation_header_row = QHBoxLayout()
        translation_header_row.setContentsMargins(0, 0, 0, 0)
        translation_label = QLabel("🌍 Translation")
        translation_label_font = QFont("SF Pro Text", 11)
        translation_label_font.setWeight(QFont.Weight.Medium)
        translation_label.setFont(translation_label_font)
        translation_label.setStyleSheet("""
            background: transparent;
            color: rgba(160, 160, 170, 0.9); 
            font-size: 11px; 
            font-weight: 500; 
            margin-top: 4px; 
            letter-spacing: 0.3px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        """)

        self.busy_label = QLabel("")
        self.busy_label.setFont(translation_label_font)
        self.busy_label.setStyleSheet("background: transparent; color: rgba(120, 200, 255, 0.95); font-size: 11px;")

        small_btn_style = """
            QPushButton {
                background: rgba(13, 27, 42, 0.6);
                color: #c5d4f0;
                border: 1px solid rgba(74, 144, 226, 0.25);
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                min-height: 22px;
            }
            QPushButton:hover { background: rgba(26, 47, 74, 0.8); color: #e6efff; }
            QPushButton:disabled { color: rgba(140,140,140,0.5); border-color: rgba(40,40,40,0.3); }
        """
        self.copy_btn = QPushButton("Copy")
        self.clear_btn = QPushButton("Clear")
        self.font_minus_btn = QPushButton("A−")
        self.font_plus_btn = QPushButton("A+")
        for b in (self.copy_btn, self.clear_btn, self.font_minus_btn, self.font_plus_btn):
            b.setStyleSheet(small_btn_style)
            b.setCursor(Qt.PointingHandCursor)

        translation_header_row.addWidget(translation_label)
        translation_header_row.addSpacing(8)
        translation_header_row.addWidget(self.busy_label)
        translation_header_row.addStretch()
        translation_header_row.addWidget(self.font_minus_btn)
        translation_header_row.addWidget(self.font_plus_btn)
        translation_header_row.addSpacing(6)
        translation_header_row.addWidget(self.copy_btn)
        translation_header_row.addWidget(self.clear_btn)
        
        self.translation_view = QTextEdit()
        self.translation_view.setReadOnly(True)
        self.translation_view.setMinimumHeight(300)  # Larger minimum height
        self.translation_view.setPlaceholderText("English translations will appear here...")
        translation_font = QFont("SF Pro Text", 14)
        self.translation_view.setFont(translation_font)
        self.translation_view.setStyleSheet("""
            QTextEdit {
                background: rgba(15, 15, 20, 0.5);
                color: #f0f0f0;
                border: 1px solid rgba(74, 144, 226, 0.2);
                border-radius: 12px;
                padding: 16px;
                font-size: 14px;
                line-height: 1.7;
                selection-background-color: rgba(74, 144, 226, 0.4);
                selection-color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QScrollBar:vertical {
                background: rgba(10, 10, 15, 0.5);
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(42, 74, 110, 0.6);
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(74, 144, 226, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        # Status section - compact and modern with glassy look
        status_label = QLabel("Status")
        status_label_font = QFont("SF Pro Text", 11)
        status_label_font.setWeight(QFont.Weight.Medium)
        status_label.setFont(status_label_font)
        status_label.setStyleSheet("""
            background: transparent;
            color: rgba(160, 160, 170, 0.9); 
            font-size: 11px; 
            font-weight: 500; 
            margin-top: 4px; 
            letter-spacing: 0.3px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        """)

        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setMaximumHeight(80)  # Much smaller
        self.status_output.setPlaceholderText("Status messages...")
        status_font = QFont("SF Pro Text", 11)
        self.status_output.setFont(status_font)
        self.status_output.setStyleSheet("""
            QTextEdit {
                background: rgba(15, 15, 20, 0.4);
                color: rgba(180, 180, 190, 0.8);
                border: 1px solid rgba(74, 144, 226, 0.15);
                border-radius: 10px;
                padding: 10px;
                font-size: 11px;
                line-height: 1.4;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QScrollBar:vertical {
                background: rgba(10, 10, 15, 0.5);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(42, 74, 110, 0.6);
                border-radius: 4px;
                min-height: 15px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(74, 144, 226, 0.8);
            }
        """)

        # Add all widgets with stretch priorities
        layout.addWidget(header)
        layout.addWidget(sub)
        layout.addLayout(row1)
        layout.addLayout(options_layout)
        layout.addWidget(preview_label)
        layout.addWidget(self.preview)
        layout.addLayout(translation_header_row)
        layout.addWidget(self.translation_view, stretch=3)  # Translation area gets most space
        layout.addWidget(status_label)
        layout.addWidget(self.status_output, stretch=0)  # Status area stays small

        self._translation_font_pt: int = 14
        self._show_german: bool = False

        self.pick_btn.clicked.connect(self.pick_region_clicked.emit)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.aot_check.toggled.connect(self.always_on_top_toggled.emit)
        self.copy_btn.clicked.connect(self.copy_clicked.emit)
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        self.show_german_check.toggled.connect(self._on_show_german_toggled)
        self.font_plus_btn.clicked.connect(lambda: self._adjust_font(+1))
        self.font_minus_btn.clicked.connect(lambda: self._adjust_font(-1))

    def _populate_default_models(self) -> None:
        """Opus (offline) and common Ollama Gemma tags (add more in add_ollama_model_if_absent)."""
        self.model_combo.clear()
        entries = [
            ("Opus-MT (local, offline)", ("opus", None)),
            ("Ollama: gemma2:2b", ("ollama", "gemma2:2b")),
            ("Ollama: gemma2:4b", ("ollama", "gemma2:4b")),
            ("Ollama: gemma2:9b", ("ollama", "gemma2:9b")),
            ("Ollama: gemma3:4b", ("ollama", "gemma3:4b")),
            ("Ollama: gemma3:12b", ("ollama", "gemma3:12b")),
            ("Ollama: gemma3:27b", ("ollama", "gemma3:27b")),
        ]
        for text, data in entries:
            self.model_combo.addItem(text, data)

    def add_ollama_model_if_absent(self, model_name: str) -> None:
        """Add a Gemma (or any) Ollama tag found locally so users can pick it."""
        for i in range(self.model_combo.count()):
            d = self.model_combo.itemData(i)
            if d and d[0] == "ollama" and d[1] == model_name:
                return
        self.model_combo.addItem(f"Ollama: {model_name}", ("ollama", model_name))

    def merge_ollama_tag_models(self) -> None:
        """Call after the window is up; app supplies tag list from Ollama."""
        try:
            from ocr_translator import default_ollama_base, ollama_list_model_names
        except ImportError:
            return
        self.model_combo.blockSignals(True)
        try:
            for name in ollama_list_model_names(default_ollama_base()):
                if "gemma" in name.lower():
                    self.add_ollama_model_if_absent(name)
        finally:
            self.model_combo.blockSignals(False)

    def schedule_merge_ollama_tags(self) -> None:
        QTimer.singleShot(0, self.merge_ollama_tag_models)

    def translation_backend_selection(self) -> tuple[str, str | None]:
        d = self.model_combo.currentData()
        if not d or not isinstance(d, (tuple, list)) or len(d) < 2:
            return "opus", None
        b, m = d[0], d[1]
        return b, m if b == "ollama" else None

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.pick_btn.setEnabled(not running)
        self.model_combo.setEnabled(not running)

    def append_translation(self, text: str):
        if not text or not text.strip():
            return
        if self.translation_view.toPlainText():
            self.translation_view.append("")
        self.translation_view.append(text)
        self._scroll_to_bottom()

    def append_translation_pair(self, de_text: str, en_text: str):
        en = (en_text or "").strip()
        if not en:
            return
        if self.translation_view.toPlainText():
            self.translation_view.append("")
        if self._show_german and de_text and de_text.strip():
            self.translation_view.append(
                f'<div style="color: rgba(180,200,230,0.55); font-size: {max(11, self._translation_font_pt - 2)}pt;">'
                f'{self._html_escape(de_text.strip())}</div>'
            )
        self.translation_view.append(en)
        self._scroll_to_bottom()

    @staticmethod
    def _html_escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    def _scroll_to_bottom(self) -> None:
        sb = self.translation_view.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def set_busy(self, busy: bool) -> None:
        self.busy_label.setText("● translating…" if busy else "")

    def set_show_german(self, enabled: bool) -> None:
        self._show_german = bool(enabled)
        if self.show_german_check.isChecked() != enabled:
            self.show_german_check.blockSignals(True)
            self.show_german_check.setChecked(enabled)
            self.show_german_check.blockSignals(False)

    def _on_show_german_toggled(self, on: bool) -> None:
        self._show_german = bool(on)
        self.show_german_toggled.emit(self._show_german)

    def _adjust_font(self, delta: int) -> None:
        new_size = max(9, min(28, self._translation_font_pt + delta))
        if new_size == self._translation_font_pt:
            return
        self._translation_font_pt = new_size
        self.font_size_changed.emit(new_size)
        self.set_translation_font_size(new_size)

    def set_translation_font_size(self, pt: int) -> None:
        pt = max(9, min(28, int(pt)))
        self._translation_font_pt = pt
        f = self.translation_view.font()
        f.setPointSize(pt)
        self.translation_view.setFont(f)

    def clear_translation(self):
        self.translation_view.clear()

    def append_status(self, text: str):
        if text:
            self.status_output.append(text)

    def set_preview_image(self, qimg: QImage):
        if qimg is None or qimg.isNull():
            return
        try:
            if qimg.width() <= 0 or qimg.height() <= 0:
                return
            pix = QPixmap.fromImage(qimg)
            if pix.isNull():
                return
            preview_width = self.preview.width()
            preview_height = self.preview.height()
            if preview_width > 0 and preview_height > 0:
                scaled = pix.scaled(
                    preview_width,
                    preview_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
                if not scaled.isNull():
                    self.preview.setPixmap(scaled)
        except Exception:
            pass
