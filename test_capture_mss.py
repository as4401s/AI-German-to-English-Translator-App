from capture import CaptureBox, RegionGrabber
from PySide6.QtGui import QImage
import time

def test_capture():
    print("Testing MSS Capture...")
    
    # Create a dummy box (top-left corner of primary screen)
    box = CaptureBox(x=100, y=100, w=500, h=300, screen_name="dummy")
    
    grabber = RegionGrabber(box)
    
    start = time.time()
    img = grabber.grab_qimage()
    end = time.time()
    
    print(f"Capture time: {(end - start)*1000:.2f} ms")
    
    if img.isNull():
        print("❌ Capture failed: Image is null")
    else:
        print(f"✓ Capture successful: {img.width()}x{img.height()}")
        print(f"  Format: {img.format()}")
        
        # Save for inspection
        img.save("test_capture_mss.png")
        print("  Saved to test_capture_mss.png")

if __name__ == "__main__":
    test_capture()
