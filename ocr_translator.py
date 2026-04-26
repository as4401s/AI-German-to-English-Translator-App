from __future__ import annotations
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

from PIL import Image, ImageOps, ImageFilter

# Security: do not log captured screen text by default. The app captures
# arbitrary on-screen content (passwords, chats, emails, etc.) which could
# otherwise persist verbatim in ~/Library/Logs/LiveTranslate/app.log.
DEBUG_LOG_CONTENT = os.environ.get("LIVETRANSLATE_DEBUG") == "1"

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
            
            # Check for bundled model first (PyInstaller sets sys._MEIPASS to the onedir root)
            if getattr(sys, "frozen", False):
                if hasattr(sys, "_MEIPASS"):
                    meip = Path(sys._MEIPASS)
                    for sub in (
                        meip / "models" / "opus-mt-de-en",
                        meip / "opus-mt-de-en",
                    ):
                        if sub.is_dir() and (sub / "config.json").exists():
                            model_dir = str(sub)
                            print(f"✓ Found bundled model at: {model_dir}")
                            break
                if not model_dir and hasattr(sys, "executable"):
                    exe_path = Path(sys.executable)
                    if exe_path.parent.name == "MacOS":
                        for bundled_path in (
                            exe_path.parent.parent / "Resources" / "models" / "opus-mt-de-en",
                            exe_path.parent.parent / "Resources" / "opus-mt-de-en",
                        ):
                            if bundled_path.is_dir() and (bundled_path / "config.json").exists():
                                model_dir = str(bundled_path)
                                print(f"✓ Found bundled model at: {model_dir}")
                                break
            
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

            # Security: only load weights from .safetensors. .bin files use
            # Python pickle, which can execute arbitrary code on load.
            safetensors_path = Path(model_dir) / "model.safetensors"
            if not safetensors_path.exists():
                print(
                    f"❌ Refusing to load model: {safetensors_path} not found. "
                    "Only safetensors are accepted (pickle .bin is unsafe)."
                )
                return

            print("   Loading tokenizer...")
            self.tokenizer = MarianTokenizer.from_pretrained(
                model_dir,
                local_files_only=True,
            )
            print("   ✓ Tokenizer loaded")

            print("   Loading model...")
            self.model = MarianMTModel.from_pretrained(
                model_dir,
                local_files_only=True,
                use_safetensors=True,
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
                if DEBUG_LOG_CONTENT:
                    print(f"✓ Translation: {result[:80]}")
                else:
                    print(f"✓ Translation: <{len(result)} chars>")
            else:
                print("⚠️  Empty translation result")
            
            return result.strip()
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            import traceback
            traceback.print_exc()
            return ""


_LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost", ""}


def _is_safe_ollama_url(url: str) -> tuple[bool, str]:
    """Allow only http(s); allow non-localhost only with explicit opt-in.

    Security: prevents (a) `file://` and similar schemes from being passed to
    urlopen, and (b) accidental data exfiltration of captured screen text to
    a remote host via OLLAMA_BASE_URL.
    """
    try:
        u = urlparse(url)
    except Exception:
        return False, "could not parse URL"
    if u.scheme not in ("http", "https"):
        return False, f"scheme {u.scheme!r} not allowed (only http/https)"
    host = (u.hostname or "").lower()
    if host in _LOCALHOST_HOSTS:
        return True, ""
    if os.environ.get("LIVETRANSLATE_ALLOW_REMOTE_OLLAMA") == "1":
        return True, ""
    return (
        False,
        f"non-localhost host {host!r} blocked. Set LIVETRANSLATE_ALLOW_REMOTE_OLLAMA=1 to opt in.",
    )


def default_ollama_base() -> str:
    """Return a vetted Ollama base URL; falls back to localhost on bad input."""
    raw = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ok, reason = _is_safe_ollama_url(raw)
    if ok:
        return raw
    print(f"⚠️  Ignoring OLLAMA_BASE_URL={raw!r}: {reason}")
    return "http://127.0.0.1:11434"


OLLAMA_SYSTEM_PROMPT = (
    "You translate German to English. "
    "Output only the English translation. "
    "Do not add a title, label, preface, explanation, or phrasing like "
    '"Here is the translation". '
    "Do not wrap the answer in markdown or quotes unless the source text is quoted."
)

_MAX_OLLAMA_CHARS = 12000


_CHATTER_LINE_RES = (
    re.compile(r"^#+\s*translation\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^\**\s*translation\s*:?\s*\**\s*$", re.IGNORECASE),
    re.compile(r"^here\s*(?:'s| is)\s*(?:the\s+)?translation\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^the\s+translation\s+(?:is|in\s+english)\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^english\s+translation\s*:?\s*$", re.IGNORECASE),
    re.compile(r"^translated\s+text\s*:?\s*$", re.IGNORECASE),
)
_CHATTER_INLINE_RES = (
    re.compile(r"^#+\s*translation\s*:?\s*", re.IGNORECASE),
    re.compile(r"^\**\s*translation\s*\**\s*:\s*\**\s*", re.IGNORECASE),
    re.compile(r"^here\s*(?:'s| is)\s*(?:the\s+)?translation\s*:\s*", re.IGNORECASE),
    re.compile(r"^the\s+translation\s+(?:is|in\s+english)\s*:\s*", re.IGNORECASE),
    re.compile(r"^english\s+translation\s*:\s*", re.IGNORECASE),
    re.compile(r"^translated\s+text\s*:\s*", re.IGNORECASE),
)


def strip_translation_chatter(text: str) -> str:
    """Remove common assistant prefaces so the UI shows only English text."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    lines = s.splitlines()
    while lines and any(p.match(lines[0].strip()) for p in _CHATTER_LINE_RES):
        lines.pop(0)
    s = "\n".join(lines).lstrip()

    for _ in range(3):
        before = s
        for p in _CHATTER_INLINE_RES:
            s = p.sub("", s, count=1)
        s = s.lstrip(" *#`:\t")
        if s == before:
            break
    return s.strip()


def ollama_list_model_names(base: str) -> list[str]:
    ok, reason = _is_safe_ollama_url(base)
    if not ok:
        print(f"⚠️  Refusing Ollama tags fetch: {reason}")
        return []
    try:
        url = urljoin(base.rstrip("/") + "/", "api/tags")
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=4) as r:  # noqa: S310 - vetted above
            data = json.load(r)
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        print(f"⚠️  Ollama tags fetch failed: {e}")
        return []


def ollama_model_in_list(model: str, names: list[str]) -> bool:
    if not model or not names:
        return False
    if model in names:
        return True
    for n in names:
        if n.split("/")[-1] == model:
            return True
    return False


def ollama_chat_translate(
    text: str,
    model: str,
    base: str,
    timeout_s: float = 300.0,
) -> str:
    """Call Ollama /api/chat; returns English only (with chatter stripped)."""
    if not text.strip():
        return ""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Translate the following German text to English. "
                    "Output only the English, nothing else:\n\n"
                    + text
                ),
            },
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    ok, reason = _is_safe_ollama_url(base)
    if not ok:
        raise PermissionError(f"Ollama base URL rejected: {reason}")
    body = json.dumps(payload).encode("utf-8")
    url = urljoin(base.rstrip("/") + "/", "api/chat")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:  # noqa: S310 - vetted above
        data = json.load(r)
    content = (data.get("message") or {}).get("content") or ""
    return strip_translation_chatter(content)


def ollama_translate_long_text(
    text: str,
    model: str,
    base: str,
) -> str:
    """One request if short; else chunk by line length (or raw slices for very long lines)."""
    t = text.strip()
    if not t:
        return ""
    if len(t) <= _MAX_OLLAMA_CHARS:
        return ollama_chat_translate(t, model, base)
    out: list[str] = []
    buf: list[str] = []
    n = 0
    for line in t.splitlines():
        if len(line) > _MAX_OLLAMA_CHARS:
            if buf:
                out.append(ollama_chat_translate("\n".join(buf), model, base))
                buf = []
                n = 0
            for i in range(0, len(line), _MAX_OLLAMA_CHARS):
                out.append(ollama_chat_translate(line[i : i + _MAX_OLLAMA_CHARS], model, base))
            continue
        add = len(line) + (1 if buf else 0)
        if buf and n + add > _MAX_OLLAMA_CHARS:
            out.append(ollama_chat_translate("\n".join(buf), model, base))
            buf = [line]
            n = len(line)
        else:
            buf.append(line)
            n += add
    if buf:
        out.append(ollama_chat_translate("\n".join(buf), model, base))
    return "\n".join(s for s in out if s.strip())


class _LRUCache:
    def __init__(self, maxsize: int = 256):
        self._d: "OrderedDict[tuple, str]" = OrderedDict()
        self._max = max(8, maxsize)

    def get(self, key: tuple) -> Optional[str]:
        v = self._d.get(key)
        if v is None:
            return None
        self._d.move_to_end(key)
        return v

    def set(self, key: tuple, value: str) -> None:
        self._d[key] = value
        self._d.move_to_end(key)
        while len(self._d) > self._max:
            self._d.popitem(last=False)

    def clear(self) -> None:
        self._d.clear()


class OcrTranslator:
    def __init__(
        self,
        lang_hint: str = "deu",
        backend: str = "opus",
        ollama_model: Optional[str] = None,
        ollama_base: Optional[str] = None,
        cache_size: int = 256,
    ):
        self.tess_lang = lang_hint
        self.pytesseract_ok = PYTESSERACT_AVAILABLE

        self.opus_translator = OpusTranslator()
        self._backend: str = "opus" if backend not in ("opus", "ollama") else backend
        self._ollama_model: str = ollama_model or "gemma2:2b"
        self._ollama_base: str = (ollama_base or default_ollama_base()).rstrip("/")
        self._cache = _LRUCache(cache_size)
        self._engine_ready_ts: float = 0.0
        self._engine_ready_cached: bool = False

    def set_translation_config(
        self,
        backend: str,
        ollama_model: Optional[str] = None,
        ollama_base: Optional[str] = None,
    ) -> None:
        new_backend = "opus" if backend not in ("opus", "ollama") else backend
        new_model = ollama_model or self._ollama_model
        new_base = (ollama_base or self._ollama_base).rstrip("/")
        if (new_backend, new_model, new_base) != (
            self._backend, self._ollama_model, self._ollama_base
        ):
            self._cache.clear()
        self._backend = new_backend
        self._ollama_model = new_model
        self._ollama_base = new_base
        self._engine_ready_ts = 0.0

    def is_available(self) -> bool:
        """OCR and the currently selected translation engine are ready."""
        return self.pytesseract_ok and self.translation_engine_ready()

    def translation_engine_ready(self) -> bool:
        import time as _time

        now = _time.monotonic()
        if self._engine_ready_ts and now - self._engine_ready_ts < 5.0:
            return self._engine_ready_cached
        if self._backend == "ollama":
            names = ollama_list_model_names(self._ollama_base)
            ready = ollama_model_in_list(self._ollama_model, names)
        else:
            ready = self.opus_translator.available
        self._engine_ready_cached = ready
        self._engine_ready_ts = now
        return ready

    def current_backend(self) -> tuple[str, Optional[str], str]:
        return self._backend, (self._ollama_model if self._backend == "ollama" else None), self._ollama_base

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
        """Resolve a working Tesseract binary; needed for bundled .app and GUI launches with stripped PATH."""
        if getattr(self, "_tesseract_resolved", False):
            return
        try:
            import shutil
            cmd = shutil.which("tesseract")
            if not cmd:
                for path in (
                    "/opt/homebrew/bin/tesseract",
                    "/usr/local/bin/tesseract",
                    "/usr/bin/tesseract",
                ):
                    if os.path.exists(path):
                        cmd = path
                        break
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
        finally:
            self._tesseract_resolved = True

    @staticmethod
    def _cache_key(backend: str, model: Optional[str], text: str) -> tuple:
        norm = " ".join(text.split())
        return (backend, model or "", norm)

    def translate_text(self, de_text: str) -> str:
        """Translate already-OCR'd German text → English (cached)."""
        de_text = (de_text or "").strip()
        if not de_text:
            return ""
        if not self.translation_engine_ready():
            return ""
        key = self._cache_key(
            self._backend,
            self._ollama_model if self._backend == "ollama" else None,
            de_text,
        )
        hit = self._cache.get(key)
        if hit is not None:
            return hit

        try:
            if self._backend == "ollama":
                en = ollama_translate_long_text(de_text, self._ollama_model, self._ollama_base) or ""
            else:
                lines = de_text.split("\n")
                out: list[str] = []
                for ln in lines:
                    ln = ln.strip()
                    if ln:
                        t = self.opus_translator.translate(ln)
                        out.append(t or ln)
                    else:
                        out.append("")
                en = "\n".join(out)
            en = en.strip()
            if en:
                self._cache.set(key, en)
            return en
        except Exception as e:
            print(f"❌ Translation error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def ocr_and_translate(self, img: Image.Image) -> tuple[str, str]:
        de = self.ocr(img)
        if not de or not de.strip():
            return "", ""
        de_original = de
        if DEBUG_LOG_CONTENT:
            print(f"📝 OCR: {de[:120]}")
        else:
            print(f"📝 OCR: <{len(de)} chars, {len(de.splitlines())} lines>")
        en = self.translate_text(de_original)
        return de_original, en
