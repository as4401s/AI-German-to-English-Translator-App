# app.py
from __future__ import annotations
import sys, hashlib, traceback, time
from typing import Optional
from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QPalette, QColor, QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

from PIL import Image, ImageOps

from capture import RegionSelectorOverlay, CaptureBox, RegionGrabber
from widgets import TranslatorPanel
from ocr_translator import OcrTranslator

POLL_INTERVAL_MS = 100  # Faster polling for real-time translation
SIG_SIZE = (64, 28)
MIN_DELTA_CHARS = 3  # Lower threshold for more responsive updates
SIGNATURE_THRESHOLD = 0.85  # Only process if signature similarity is below this

def apply_dark_palette(app: QApplication):
    pal = QPalette()
    bg = QColor(18,20,25); base = QColor(30,34,43); text = QColor(255,255,255)
    pal.setColor(QPalette.Window, bg); pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base); pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, QColor(58,63,75)); pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.Highlight, QColor(78,84,100)); pal.setColor(QPalette.HighlightedText, text)
    app.setPalette(pal); app.setStyleSheet("QWidget { color: #FFFFFF; }")

def qimage_to_pil(qimg: QImage) -> Optional[Image.Image]:
    """Convert QImage to PIL Image, returns None on failure."""
    if qimg is None or qimg.isNull() or qimg.width() <= 0 or qimg.height() <= 0:
        return None
    
    try:
        # Convert QImage to QPixmap and back to ensure it's in a good format
        width, height = qimg.width(), qimg.height()
        
        # Convert to RGB888 format for consistent handling
        qimg_rgb = qimg.convertToFormat(QImage.Format_RGB888)
        if qimg_rgb.isNull():
            return None
        
        # Get the raw bytes
        ptr = qimg_rgb.constBits()
        if ptr is None:
            return None
        
        # Create PIL Image from raw RGB data
        # Format_RGB888 is RGB in memory (3 bytes per pixel)
        bytes_per_line = qimg_rgb.bytesPerLine()
        
        # Copy the data to ensure it's safe
        img_bytes = bytearray(height * bytes_per_line)
        for i in range(len(img_bytes)):
            img_bytes[i] = ptr[i]
        
        # Create PIL Image
        pil_img = Image.frombytes("RGB", (width, height), bytes(img_bytes), "raw", "RGB", bytes_per_line)
        return pil_img
    except Exception as e:
        print(f"Error converting QImage to PIL: {e}")
        return None

def quick_signature(pil_img: Image.Image) -> str:
    """Generate a quick hash signature of an image."""
    try:
        if pil_img is None or pil_img.width <= 0 or pil_img.height <= 0:
            return ""
        g = ImageOps.grayscale(pil_img).resize(SIG_SIZE, Image.Resampling.LANCZOS)
        return hashlib.blake2b(g.tobytes(), digest_size=16).hexdigest()
    except Exception:
        return ""

class WorkerSignals(QObject):
    translated = Signal(str)
    status = Signal(str)
    ocrtext = Signal(str)
    error = Signal(str)

class FrameWorker(QThread):
    def __init__(self, translator: OcrTranslator, parent=None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._translator = translator
        self._queue = deque(maxlen=3)  # Keep last 3 frames for smoother processing
        self._running = True
        self._emit_ocr = False
        self._processing = False  # Prevent concurrent processing

    def set_emit_ocr(self, enabled: bool):
        self._emit_ocr = enabled

    def push_frame(self, pil_img: Image.Image):
        if pil_img is not None:
            # Always add the latest frame, replacing oldest if queue is full
            self._queue.append(pil_img)

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            if self._processing:
                self.msleep(5)  # Reduced sleep for faster response
                continue
            
            # Get the most recent frame (if available)
            img = None
            if self._queue:
                img = self._queue.pop()  # Get and remove the latest frame
                # Clear any remaining old frames to always process the newest
                self._queue.clear()
            
            if img is None:
                self.msleep(10)  # Reduced wait time for faster processing
                continue
            
            try:
                self._processing = True
                de, en = self._translator.ocr_and_translate(img)
                self._processing = False
                
                if self._emit_ocr and de:
                    self.signals.ocrtext.emit(de)
                    
                # Emit translation if we have it
                if en and en.strip():
                    self.signals.translated.emit(en)
                elif de:
                    # If we got German text but no translation, don't show status to reduce noise
                    pass
                # Don't log "No OCR text found" to reduce noise
                    
            except Exception as e:
                self._processing = False
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
                self.signals.error.emit(traceback.format_exc())

class AppWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Translate")
        self.setMinimumSize(600, 500)  # Allow smaller window
        self.resize(950, 750)
        # Glassy background with gradient
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0a0a0f, stop:1 #000005);
        """)

        self.panel = TranslatorPanel()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26,26,26,26)
        lay.addWidget(self.panel)

        self.selector: Optional[RegionSelectorOverlay] = None
        self.capture_box: Optional[CaptureBox] = None
        self.grabber: Optional[RegionGrabber] = None

        self.timer = QTimer(self)
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self._tick)

        self.translator = OcrTranslator(lang_hint="deu")
        self.worker: Optional[FrameWorker] = None

        self._running = False
        self._last_sig: Optional[str] = None
        self._last_text: Optional[str] = None
        self._last_error_time = 0.0
        self._skip_count = 0

        self.panel.pick_region_clicked.connect(self.pick_region)
        self.panel.start_clicked.connect(self.start_translate)
        self.panel.stop_clicked.connect(self.stop_translate)
        self.panel.always_on_top_toggled.connect(self._toggle_on_top)

        # Check translator availability
        if not self.translator.is_available():
            self.panel.append_status("⚠️  Translation model not available!")
            if hasattr(self.translator, 'opus_translator'):
                if not self.translator.opus_translator.available:
                    self.panel.append_status("   Model failed to load. Check console for errors.")
                else:
                    self.panel.append_status("   OCR may not be available.")
            else:
                self.panel.append_status("   Check console for initialization errors.")
            self.panel.append_status("   OCR will still work, but no translation.")
        else:
            model_name = getattr(self.translator.opus_translator, "model_name", "Opus-MT model") if hasattr(self.translator, 'opus_translator') else "Translation model"
            self.panel.append_status(f"🟢 Translation model ready: {model_name}")

        self._toggle_on_top(True)

    def _toggle_on_top(self, enabled: bool):
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def pick_region(self):
        try:
            self.selector = RegionSelectorOverlay()
            self.selector.region_selected.connect(self._on_region_selected)
            self.selector.show()
        except Exception:
            self.panel.append_status(f"[Error]\n{traceback.format_exc()}")

    def _on_region_selected(self, x: int, y: int, w: int, h: int):
        try:
            # Find which screen contains the center point
            from PySide6.QtCore import QPoint
            center = QPoint(x + w // 2, y + h // 2)
            screen = None
            
            # Try to find the screen that contains the center point
            for s in QGuiApplication.screens():
                sg = s.geometry()
                if sg.contains(center):
                    screen = s
                    break
            
            # If not found, try to find the screen that contains any part of the selection
            if screen is None:
                for s in QGuiApplication.screens():
                    sg = s.geometry()
                    # Check if selection overlaps with screen
                    if not (x + w < sg.x() or x > sg.x() + sg.width() or
                            y + h < sg.y() or y > sg.y() + sg.height()):
                        screen = s
                        break
            
            # Fallback to primary screen
            if screen is None:
                screen = QGuiApplication.primaryScreen()
                print(f"⚠️ Could not find screen for region, using primary: {screen.name()}")

            print(f"✓ Selected region on screen: {screen.name()} (geometry: {screen.geometry()})")
            self.capture_box = CaptureBox(x, y, w, h, screen_name=screen.name())
            self.grabber = RegionGrabber(self.capture_box)

            self.panel.append_status(f"✅ Region selected: {w}×{h}px at ({x},{y})")

            # Test capture
            qimg = self.grabber.grab_qimage(max_width=1000)
            if qimg.isNull() or qimg.width() <= 0 or qimg.height() <= 0:
                self.panel.append_status("⚠️ Preview failed (check Screen Recording permission)")
                return
            
            self.panel.set_preview_image(qimg)
            self.panel.append_status(f"✅ Preview loaded: {qimg.width()}×{qimg.height()}px")
        except Exception:
            self.panel.append_status(f"[Error]\n{traceback.format_exc()}")

    def start_translate(self):
        if not self.grabber:
            self.panel.append_status("⚠️ Please select a region first.")
            return
        
        if self._running:
            return
        
        try:
            # Stop any existing worker
            if self.worker is not None:
                self.worker.stop()
                self.worker.wait(500)
                self.worker = None

            self._running = True
            self.panel.set_running(True)
            self._last_sig = None
            self._last_text = None
            self.panel.clear_translation()

            # Create and start worker thread
            self.worker = FrameWorker(self.translator, parent=self)
            self.worker.signals.translated.connect(self._on_translated)
            self.worker.signals.status.connect(self._on_status)
            self.worker.signals.error.connect(self._on_error)
            self.worker.start()

            # Start polling timer
            self.timer.start()
            self.panel.append_status("▶️ Translation started (AI-powered)")
        except Exception:
            self._running = False
            self.panel.set_running(False)
            self.panel.append_status(f"[Error]\n{traceback.format_exc()}")

    def stop_translate(self):
        self.timer.stop()
        self._running = False
        
        if self.worker:
            self.worker.stop()
            self.worker.wait(800)
            self.worker = None
        
        self.panel.set_running(False)
        self.panel.append_status("⏹ Stopped")

    def _tick(self):
        if not self._running or not self.worker or not self.grabber:
            return
        
        if not self.worker.isRunning():
            return
        
        try:
            # Grab frame continuously for smooth flow
            qimg = self.grabber.grab_qimage(max_width=1000)
            if qimg.isNull() or qimg.width() <= 0 or qimg.height() <= 0:
                return
            
            # Update preview smoothly
            try:
                self.panel.set_preview_image(qimg)
            except Exception:
                pass
            
            # Convert to PIL
            pil = qimage_to_pil(qimg)
            if pil is None or pil.width <= 0 or pil.height <= 0:
                return
            
            # Use signature to avoid processing identical frames
            # But be lenient - process every frame, signature is just for optimization
            sig = quick_signature(pil)
            
            # Always push frames for continuous translation
            # The worker will handle processing efficiently
            if self.worker and self.worker.isRunning():
                self.worker.push_frame(pil)
            
            # Update signature for next comparison
            self._last_sig = sig
        except Exception:
            # Rate limit error messages
            now = time.time()
            if now - self._last_error_time > 5.0:
                self.panel.append_status(f"[Capture Error]\n{traceback.format_exc()}")
                self._last_error_time = now

    def _on_translated(self, en_text: str):
        if not en_text or not en_text.strip():
            return
        
        # Clean the text
        en_text = en_text.strip()
        
        if not self._last_text or self._meaningfully_different(self._last_text, en_text):
            # Only show English translation - clean output only
            self.panel.append_translation(en_text)
            self._last_text = en_text

    def _on_error(self, msg: str):
        self.panel.append_status(f"⚠️ Error: {msg.split('Traceback')[0].strip()}")

    def _on_status(self, msg: str):
        self.panel.append_status(msg)

    @staticmethod
    def _meaningfully_different(a: str, b: str) -> bool:
        a = a.strip()
        b = b.strip()
        if a == b:
            return False
        # Allow updates if text is different (even slightly) for real-time feel
        # But avoid updating if it's just whitespace differences
        a_clean = ' '.join(a.split())
        b_clean = ' '.join(b.split())
        if a_clean == b_clean:
            return False
        # Update if there's a meaningful difference
        return abs(len(a_clean) - len(b_clean)) >= MIN_DELTA_CHARS or a_clean != b_clean

    def closeEvent(self, event):
        """Clean up when window is closed."""
        self.stop_translate()
        event.accept()

def main():
    try:
        app = QApplication(sys.argv)
        apply_dark_palette(app)
        win = AppWindow()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print("=" * 70)
        print("FATAL ERROR:")
        print("=" * 70)
        print(error_msg)
        print("=" * 70)
        
        # Show error dialog if possible
        try:
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Live Translate - Error")
            msg.setText("Application Error")
            msg.setDetailedText(error_msg)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
