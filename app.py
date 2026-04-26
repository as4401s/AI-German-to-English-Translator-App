# app.py
from __future__ import annotations
import os
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

POLL_INTERVAL_MS = 200  # 5 fps capture; OCR/translation pace is the bottleneck
SIG_SIZE = (64, 28)


_MAX_LOG_BYTES = 1_000_000  # 1 MB; security: cap log so OCR/debug content doesn't accumulate forever


def _setup_logging() -> None:
    """When packaged as a .app, mirror stdout/stderr into ~/Library/Logs/LiveTranslate/app.log."""
    if not getattr(sys, "frozen", False):
        return
    try:
        log_dir = Path.home() / "Library" / "Logs" / "LiveTranslate"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "app.log"
        try:
            if log_path.exists() and log_path.stat().st_size > _MAX_LOG_BYTES:
                old = log_dir / "app.log.old"
                if old.exists():
                    old.unlink()
                log_path.rename(old)
        except Exception:
            pass
        f = open(log_path, "a", buffering=1, encoding="utf-8")  # noqa: SIM115
        sys.stdout = f
        sys.stderr = f
        print(f"\n--- LiveTranslate started {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    except Exception:
        pass

def apply_dark_palette(app: QApplication):
    pal = QPalette()
    bg = QColor(18,20,25); base = QColor(30,34,43); text = QColor(255,255,255)
    pal.setColor(QPalette.Window, bg); pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base); pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, QColor(58,63,75)); pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.Highlight, QColor(78,84,100)); pal.setColor(QPalette.HighlightedText, text)
    app.setPalette(pal); app.setStyleSheet("QWidget { color: #FFFFFF; }")

def qimage_to_pil(qimg: QImage) -> Optional[Image.Image]:
    """Convert QImage to PIL Image, fast path with safe fallback."""
    if qimg is None or qimg.isNull() or qimg.width() <= 0 or qimg.height() <= 0:
        return None
    try:
        rgb = qimg.convertToFormat(QImage.Format_RGB888)
        if rgb.isNull():
            return None
        w, h = rgb.width(), rgb.height()
        bpl = rgb.bytesPerLine()
        ptr = rgb.constBits()
        if ptr is None:
            return None
        try:
            buf = bytes(ptr)  # PySide6 fast path: memoryview-like → bytes
        except Exception:
            mv = memoryview(ptr)  # type: ignore[arg-type]
            buf = bytes(mv)
        return Image.frombytes("RGB", (w, h), buf, "raw", "RGB", bpl)
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
    translated = Signal(str, str)  # de, en
    status = Signal(str)
    busy = Signal(bool)
    error = Signal(str)


class FrameWorker(QThread):
    def __init__(self, translator: OcrTranslator, parent=None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._translator = translator
        self._queue: "deque[Image.Image]" = deque(maxlen=2)
        self._running = True
        self._processing = False

    def push_frame(self, pil_img: Image.Image):
        if pil_img is not None:
            self._queue.append(pil_img)

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            img: Optional[Image.Image] = None
            if self._queue:
                img = self._queue.pop()
                self._queue.clear()
            if img is None:
                self.msleep(15)
                continue
            try:
                self._processing = True
                self.signals.busy.emit(True)
                de, en = self._translator.ocr_and_translate(img)
                if de or en:
                    self.signals.translated.emit(de or "", en or "")
            except Exception:
                err = traceback.format_exc()
                print(f"ERROR: {err}")
                self.signals.error.emit(err)
            finally:
                self._processing = False
                self.signals.busy.emit(False)

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

        b, om = self.panel.translation_backend_selection()
        self.translator = OcrTranslator(
            lang_hint="deu",
            backend=b,
            ollama_model=om,
        )
        self.panel.schedule_merge_ollama_tags()
        self.panel.model_combo.currentIndexChanged.connect(self._sync_translator_from_ui)
        self.worker: Optional[FrameWorker] = None

        self._running = False
        self._last_pushed_sig: Optional[str] = None
        self._last_pushed_ts: float = 0.0
        self._last_text: Optional[str] = None
        self._last_de: Optional[str] = None
        self._last_error_time = 0.0
        self._busy_since: float = 0.0

        self.panel.pick_region_clicked.connect(self.pick_region)
        self.panel.start_clicked.connect(self.start_translate)
        self.panel.stop_clicked.connect(self.stop_translate)
        self.panel.always_on_top_toggled.connect(self._toggle_on_top)
        self.panel.copy_clicked.connect(self._on_copy)
        self.panel.clear_clicked.connect(self.panel.clear_translation)
        self.panel.show_german_toggled.connect(self._on_show_german_toggled)
        self.panel.font_size_changed.connect(self.panel.set_translation_font_size)

        self._refresh_translation_status_line()

        if not self.translator.pytesseract_ok:
            self.panel.append_status("⚠️  pytesseract / Tesseract not available. Install tesseract-ocr (e.g. brew).")

        self._toggle_on_top(True)

    def _sync_translator_from_ui(self) -> None:
        b, om = self.panel.translation_backend_selection()
        self.translator.set_translation_config(b, ollama_model=om)
        if self._running:
            return
        self._refresh_translation_status_line()

    def _refresh_translation_status_line(self) -> None:
        """Update status to reflect the selected translation engine and readiness."""
        if not self.translator.pytesseract_ok:
            return
        if not self.translator.translation_engine_ready():
            b, om = self.panel.translation_backend_selection()
            if b == "ollama":
                from ocr_translator import default_ollama_base, ollama_list_model_names, ollama_model_in_list
                base = default_ollama_base()
                names = ollama_list_model_names(base)
                if not names:
                    self.panel.append_status(
                        f"⚠️  Ollama not reachable at {base}. Start Ollama or set OLLAMA_BASE_URL."
                    )
                elif not ollama_model_in_list(om or "", names):
                    self.panel.append_status(
                        f"⚠️  Ollama model {om!r} not found. Run: ollama pull {om}"
                    )
                else:
                    self.panel.append_status("⚠️  Translation engine not ready. Check Ollama.")
            else:
                if not self.translator.opus_translator.available:
                    self.panel.append_status(
                        "⚠️  Opus-MT not loaded. Run: python download_opus_model.py"
                    )
        else:
            b, om = self.panel.translation_backend_selection()
            if b == "ollama":
                from ocr_translator import default_ollama_base
                self.panel.append_status(
                    f"🟢 Ollama • {om} @ {default_ollama_base()}"
                )
            else:
                mn = getattr(self.translator.opus_translator, "model_name", "Opus-MT")
                self.panel.append_status(f"🟢 Opus-MT: {mn}")

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
            b, om = self.panel.translation_backend_selection()
            self.translator.set_translation_config(b, ollama_model=om)
            if not self.translator.translation_engine_ready():
                self._running = False
                self.panel.set_running(False)
                self._refresh_translation_status_line()
                self.panel.append_status("⚠️  Fix the translation model above, then start again.")
                return

            self.panel.set_running(True)
            self._last_pushed_sig = None
            self._last_pushed_ts = 0.0
            self._last_text = None
            self._last_de = None
            self.panel.clear_translation()
            self.panel.set_busy(False)

            self.worker = FrameWorker(self.translator, parent=self)
            self.worker.signals.translated.connect(self._on_translated)
            self.worker.signals.status.connect(self._on_status)
            self.worker.signals.busy.connect(self.panel.set_busy)
            self.worker.signals.error.connect(self._on_error)
            self.worker.start()

            self.timer.start()
            backend_label, model_label, _ = self.translator.current_backend()
            engine = f"Ollama • {model_label}" if backend_label == "ollama" else "Opus-MT"
            self.panel.append_status(f"▶️ Started ({engine})")
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
            qimg = self.grabber.grab_qimage(max_width=1000)
            if qimg.isNull() or qimg.width() <= 0 or qimg.height() <= 0:
                return
            try:
                self.panel.set_preview_image(qimg)
            except Exception:
                pass

            pil = qimage_to_pil(qimg)
            if pil is None or pil.width <= 0 or pil.height <= 0:
                return

            sig = quick_signature(pil)
            now = time.monotonic()
            # Skip if frame looks identical to the last one we pushed (re-push every 2s as a heartbeat)
            if sig and sig == self._last_pushed_sig and (now - self._last_pushed_ts) < 2.0:
                return
            if self.worker and self.worker.isRunning():
                self.worker.push_frame(pil)
                self._last_pushed_sig = sig
                self._last_pushed_ts = now
        except Exception:
            now = time.time()
            if now - self._last_error_time > 5.0:
                self.panel.append_status(f"[Capture Error]\n{traceback.format_exc()}")
                self._last_error_time = now

    def _on_translated(self, de_text: str, en_text: str):
        de = (de_text or "").strip()
        en = (en_text or "").strip()
        if not en:
            return
        if self._last_text and self._normalize(en) == self._normalize(self._last_text):
            return
        self.panel.append_translation_pair(de, en)
        self._last_text = en
        self._last_de = de

    def _on_copy(self):
        text = self.panel.translation_view.toPlainText().strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        self.panel.append_status("📋 Copied translations to clipboard")

    def _on_show_german_toggled(self, enabled: bool):
        self.panel.set_show_german(enabled)

    def _on_error(self, msg: str):
        first = msg.split("Traceback")[0].strip() or msg.splitlines()[0]
        self.panel.append_status(f"⚠️ Error: {first}")

    def _on_status(self, msg: str):
        self.panel.append_status(msg)

    @staticmethod
    def _normalize(s: str) -> str:
        return " ".join(s.split()).lower()

    def closeEvent(self, event):
        """Clean up when window is closed."""
        self.stop_translate()
        event.accept()

def main():
    _setup_logging()
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
