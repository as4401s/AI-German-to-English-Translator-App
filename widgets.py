from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QTextEdit, QCheckBox, QWidget
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
        
        sub = QLabel("Real-time screen translation • German → English • Fully Offline")
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
        options_layout = QHBoxLayout()
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
        options_layout.addWidget(self.aot_check)
        options_layout.addStretch()

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

        # Output section - largest area with glassy modern styling
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
        layout.addWidget(translation_label)
        layout.addWidget(self.translation_view, stretch=3)  # Translation area gets most space
        layout.addWidget(status_label)
        layout.addWidget(self.status_output, stretch=0)  # Status area stays small

        # Connect signals
        self.pick_btn.clicked.connect(self.pick_region_clicked.emit)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.aot_check.toggled.connect(self.always_on_top_toggled.emit)

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.pick_btn.setEnabled(not running)

    def append_translation(self, text: str):
        print(f"[append_translation] Called with text: {text[:100] if text else '(empty)'}")
        print(f"[append_translation] Text length: {len(text) if text else 0}")
        has_newlines = '\n' in text if text else False
        print(f"[append_translation] Has newlines: {has_newlines}")
        print(f"[append_translation] Current view text length: {len(self.translation_view.toPlainText())}")
        
        if text and text.strip():
            current_text = self.translation_view.toPlainText()
            if current_text:
                self.translation_view.append("")  # Add spacing between translations
            
            # Preserve formatting - don't strip, just append as-is
            # QTextEdit.append() preserves newlines and formatting
            self.translation_view.append(text)
            
            # Force update/repaint
            self.translation_view.repaint()
            self.translation_view.update()
            
            # Auto-scroll to bottom
            scrollbar = self.translation_view.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

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
