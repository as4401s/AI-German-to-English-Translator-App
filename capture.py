# capture.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPixmap, QImage, QGuiApplication
)
from PySide6.QtWidgets import QWidget

@dataclass
class CaptureBox:
    # Logical/global coords + screen name where the selection lives
    x: int
    y: int
    w: int
    h: int
    screen_name: str

class RegionSelectorOverlay(QWidget):
    """Full-screen overlay to pick a rectangle; draws a stitched background snapshot."""
    region_selected = Signal(int, int, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        vg = QGuiApplication.primaryScreen().virtualGeometry()
        self._virt_left, self._virt_top = vg.x(), vg.y()
        self._virt_w, self._virt_h = vg.width(), vg.height()

        # Stitch screenshots from all screens (logical space)
        try:
            canvas = QImage(self._virt_w, self._virt_h, QImage.Format_RGBA8888)
            if canvas.isNull():
                # Fallback to blank canvas if allocation fails
                canvas = QImage(self._virt_w, self._virt_h, QImage.Format_RGBA8888)
                canvas.fill(QColor(0, 0, 0, 255))
            else:
                canvas.fill(QColor(0, 0, 0, 255))
            
            painter = QPainter(canvas)
            if painter.isActive():
                for s in QGuiApplication.screens():
                    try:
                        shot = s.grabWindow(0)  # respects Screen Recording permission
                        if not shot.isNull():
                            sg = s.geometry()       # logical coords
                            painter.drawPixmap(sg.x() - self._virt_left, sg.y() - self._virt_top, shot)
                    except Exception:
                        # Skip screens that fail to capture
                        continue
            painter.end()
            self._bg_qpix = QPixmap.fromImage(canvas)
            if self._bg_qpix.isNull():
                # Fallback to blank pixmap
                self._bg_qpix = QPixmap(self._virt_w, self._virt_h)
                self._bg_qpix.fill(QColor(0, 0, 0))
        except Exception:
            # Fallback to blank background on any error
            self._bg_qpix = QPixmap(self._virt_w, self._virt_h)
            self._bg_qpix.fill(QColor(0, 0, 0))

        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._rect: Optional[QRect] = None

        self.setGeometry(self._virt_left, self._virt_top, self._virt_w, self._virt_h)
        self.showFullScreen()
        self.raise_()

    def mousePressEvent(self, e):
        self._origin = e.position().toPoint()
        self._current = self._origin
        self._rect = QRect(self._origin, self._current)
        self.update()

    def mouseMoveEvent(self, e):
        if self._origin:
            self._current = e.position().toPoint()
            self._rect = QRect(self._origin, self._current).normalized()
            self.update()

    def mouseReleaseEvent(self, e):
        if self._rect:
            r = self._rect.normalized()
            gx = self.geometry().x() + r.x()
            gy = self.geometry().y() + r.y()
            self.region_selected.emit(gx, gy, r.width(), r.height())
        self.close()

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(0, 0, self._bg_qpix)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        if self._rect:
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(self._rect, QColor(0, 0, 0, 0))
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.setPen(QPen(QColor(255, 255, 255, 230), 2))
            p.drawRect(self._rect)

import mss
import numpy as np

class RegionGrabber:
    """
    Fast region capture using mss.
    """
    def __init__(self, box: CaptureBox):
        self.box = box
        self.sct = mss.mss()
        
        # Verify monitor bounds to handle negative coordinates (secondary screens)
        # mss handles virtual geometry automatically, but we need to be careful with bounds
        print(f"✓ Initialized mss for capture region: {box.x},{box.y} {box.w}x{box.h}")

    def grab_qimage(self, max_width: int = 1100) -> QImage:
        try:
            # mss requires a dict for the monitor/region
            monitor = {
                "top": self.box.y,
                "left": self.box.x,
                "width": self.box.w,
                "height": self.box.h
            }
            
            # Grab the screen shot
            sct_img = self.sct.grab(monitor)
            
            # Convert to QImage
            # mss returns BGRA, we need to convert to Format_RGB32 or Format_ARGB32
            # QImage(bytes, width, height, bytes_per_line, format)
            img = QImage(sct_img.raw, sct_img.width, sct_img.height, QImage.Format_RGB32)
            
            # mss returns BGRA, QImage.Format_RGB32 expects ARGB (in little endian) or something similar
            # Actually mss raw is BGRA. 
            # QImage.Format_RGB32 is 0xffRRGGBB.
            # We might need to swap channels if colors look wrong.
            # Let's try Format_ARGB32 or Format_RGBA8888
            
            # Create QImage from the raw data
            # sct_img.raw is BGRA
            img = QImage(sct_img.raw, sct_img.width, sct_img.height, QImage.Format_ARGB32)
            
            if img.isNull():
                return QImage()
                
            # Scale if needed
            if img.width() > max_width and max_width > 0:
                new_height = int(max_width * img.height() / img.width())
                if new_height > 0:
                    img = img.scaled(max_width, new_height,
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            return img
        except Exception as e:
            print(f"Capture error: {e}")
            import traceback
            traceback.print_exc()
            return QImage()