from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps, ImageFilter

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("⚠️  pytesseract not available")

try:
    from transformers import MarianMTModel, MarianTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  transformers not available")


def enhance_for_ocr(img: Image.Image) -> Image.Image:
    """Enhance image for better OCR results."""
    try:
        if img is None or img.width <= 0 or img.height <= 0:
            return img
        
        g = ImageOps.grayscale(img)
        g = ImageOps.autocontrast(g, cutoff=2)
        
        if g.width < 600:
            ratio = 600 / float(g.width)
            new_height = max(1, int(g.height * ratio))
            g = g.resize((600, new_height), Image.Resampling.LANCZOS)
        
        g = g.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=3))
        
        return g
    except Exception:
        return img


class OpusTranslator:
    """Translator using Helsinki-NLP/opus-mt-de-en (MarianMT)."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.available = False
        self.model_name = "Helsinki-NLP/opus-mt-de-en"
        self.model_path = None
        
        if not TRANSFORMERS_AVAILABLE:
            print("⚠️  transformers not installed")
            print("   Install with: uv sync")
            return
        
        try:
            # Find model directory
            model_dir = None
            
            # Check for bundled model first
            if getattr(sys, 'frozen', False):
                # In bundled app, check Resources directory
                if hasattr(sys, 'executable'):
                    exe_path = Path(sys.executable)
                    if exe_path.parent.name == "MacOS":
                        # Check Resources/models/opus-mt-de-en (correct path)
                        bundled_path = exe_path.parent.parent / "Resources" / "models" / "opus-mt-de-en"
                        if bundled_path.exists():
                            model_dir = str(bundled_path)
                            print(f"✓ Found bundled model at: {model_dir}")
                        else:
                            # Fallback: check Resources/opus-mt-de-en (old path)
                            old_path = exe_path.parent.parent / "Resources" / "opus-mt-de-en"
                            if old_path.exists():
                                model_dir = str(old_path)
                                print(f"✓ Found bundled model at: {model_dir}")
            
            # Fallback to development model directory
            if not model_dir:
                dev_model_dir = Path(__file__).parent / "models" / "opus-mt-de-en"
                if dev_model_dir.exists():
                    model_dir = str(dev_model_dir)
                    print(f"✓ Found model at: {model_dir}")
            
            if not model_dir:
                print("⚠️  Model directory not found!")
                print("   Run: python download_opus_model.py")
                return
            
            self.model_path = model_dir
            print(f"Loading translation model from: {model_dir}")
            
            # Load tokenizer
            print("   Loading tokenizer...")
            self.tokenizer = MarianTokenizer.from_pretrained(
                model_dir,
                local_files_only=True
            )
            print("   ✓ Tokenizer loaded")
            
            # Load model
            print("   Loading model...")
            self.model = MarianMTModel.from_pretrained(
                model_dir,
                local_files_only=True
            )
            print("   ✓ Model loaded")
            
            # Use CPU for compatibility
            self.model.eval()
            print(f"   Using CPU")
            
            self.available = True
            print(f"✓ Translation model ready: {self.model_name}")
            
        except Exception as e:
            print(f"❌ Failed to load translation model: {e}")
            import traceback
            print("=" * 70)
            traceback.print_exc()
            print("=" * 70)
            self.available = False
            self.model = None
            self.tokenizer = None
    
    def translate(self, text: str) -> str:
        """Translate German text to English using Opus-MT."""
        if not self.available or not self.model or not self.tokenizer or not text or not text.strip():
            return ""
        
        try:
            clean_text = text.strip()
            if not clean_text:
                return ""
            
            # Tokenize input
            inputs = self.tokenizer(clean_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            
            # Translate
            with torch.no_grad():
                translated = self.model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
            
            # Decode output
            result = self.tokenizer.decode(translated[0], skip_special_tokens=True)
            
            if result:
                print(f"✓ Translation: {result[:80]}")
            else:
                print("⚠️  Empty translation result")
            
            return result.strip()
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            import traceback
            traceback.print_exc()
            return ""


class OcrTranslator:
    def __init__(self, lang_hint: str = "deu"):
        self.tess_lang = lang_hint
        self.pytesseract_ok = PYTESSERACT_AVAILABLE
        
        # Initialize translation
        self.opus_translator = OpusTranslator()
        self.translation_available = self.opus_translator.available

    def is_available(self) -> bool:
        return self.pytesseract_ok and self.translation_available

    def ocr(self, img: Image.Image) -> str:
        if not self.pytesseract_ok:
            return ""
        if img is None or img.width <= 0 or img.height <= 0:
            return ""
        
        try:
            # Fix Tesseract path for bundled app
            self._fix_tesseract_path()
            
            enhanced = enhance_for_ocr(img)
            if enhanced is None or enhanced.width <= 0 or enhanced.height <= 0:
                return ""
            
            # Use Tesseract config to preserve line breaks and layout
            config = '--psm 6 -c preserve_interword_spaces=1'
            txt = pytesseract.image_to_string(enhanced, lang=self.tess_lang, config=config)
            
            txt = txt.rstrip()
            return txt
        except Exception as e:
            print(f"OCR error: {e}")
            return ""
    
    def _fix_tesseract_path(self):
        """Fix Tesseract path for bundled app."""
        if getattr(sys, 'frozen', False):
            import shutil
            tesseract_cmd = shutil.which('tesseract')
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            else:
                common_paths = [
                    '/usr/local/bin/tesseract',
                    '/opt/homebrew/bin/tesseract',
                    '/usr/bin/tesseract',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        return

    def ocr_and_translate(self, img: Image.Image) -> tuple[str, str]:
        de = self.ocr(img)
        
        if not de or not de.strip():
            return "", ""
        
        de_original = de
        print(f"📝 OCR: {de[:120]}")
        
        if not self.translation_available:
            return de_original, ""
        
        try:
            # Translate line by line to preserve formatting
            lines = de_original.split('\n')
            translated_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    en_line = self.opus_translator.translate(line)
                    if en_line:
                        translated_lines.append(en_line)
                    else:
                        translated_lines.append(line)  # Keep original if translation fails
                else:
                    translated_lines.append('')  # Preserve empty lines
            
            en = '\n'.join(translated_lines)
            
            if en and en.strip():
                return de_original, en
            else:
                return de_original, ""
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return de_original, ""
