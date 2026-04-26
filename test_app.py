"""
Plain-asserts test suite. Run: uv run python test_app.py [--ollama]
- Without --ollama: covers strip_chatter, signature, dedup, cache, opus path.
- With --ollama: also exercises a real Ollama call if reachable.
"""
from __future__ import annotations

import argparse
import io
import sys
import time

from PIL import Image

from app import qimage_to_pil, quick_signature, AppWindow
from ocr_translator import (
    OcrTranslator,
    _LRUCache,
    _is_safe_ollama_url,
    default_ollama_base,
    ollama_chat_translate,
    ollama_list_model_names,
    ollama_model_in_list,
    strip_translation_chatter,
)


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def test_strip_chatter() -> None:
    cases = [
        ("Here is the translation: Hello world", "Hello world"),
        ("Here's the translation:\nHello world", "Hello world"),
        ("**Translation:**\nGood day", "Good day"),
        ("**Translation**: Good day", "Good day"),
        ("Translation: Good day", "Good day"),
        ("English Translation:\nGood day", "Good day"),
        ("```\nGood day\n```", "Good day"),
        ("# Translation\nHello", "Hello"),
        ("The translation is: Hello", "Hello"),
        ("Plain English already", "Plain English already"),
    ]
    for raw, want in cases:
        got = strip_translation_chatter(raw)
        assert got == want, f"strip mismatch for {raw!r}: got {got!r}, want {want!r}"
    _ok("strip_translation_chatter handles 10 prefaces")


def test_signature_stable_and_distinct() -> None:
    a = Image.new("RGB", (200, 60), (10, 10, 10))
    b = Image.new("RGB", (200, 60), (10, 10, 10))
    c = Image.new("RGB", (200, 60), (200, 30, 30))
    sa, sb, sc = quick_signature(a), quick_signature(b), quick_signature(c)
    assert sa and sb and sc
    assert sa == sb, "identical frames must produce identical signatures"
    assert sa != sc, "different frames must produce different signatures"
    _ok("quick_signature: stable and discriminating")


def test_dedup_normalize() -> None:
    n = AppWindow._normalize
    assert n("Hello  world\n") == n("hello world")
    assert n("Hi.") != n("Hi")
    _ok("_normalize: case + whitespace insensitive")


def test_lru_cache() -> None:
    c = _LRUCache(maxsize=8)
    assert c.get(("k",)) is None
    c.set(("k",), "v")
    assert c.get(("k",)) == "v"
    for i in range(20):
        c.set((f"k{i}",), str(i))
    assert len(c._d) <= 8
    _ok("_LRUCache: capped + retrieval")


def test_translator_caches() -> None:
    t = OcrTranslator(backend="opus")
    if not t.opus_translator.available:
        print("  SKIP Opus-MT not available; cache test reduced")
        return
    de = "Guten Tag, wie geht es Ihnen?"
    en1 = t.translate_text(de)
    assert en1, "first translation must produce English"
    t0 = time.monotonic()
    en2 = t.translate_text(de)
    elapsed_ms = (time.monotonic() - t0) * 1000
    assert en1 == en2, "cached translation must be identical"
    assert elapsed_ms < 50, f"cache hit too slow: {elapsed_ms:.1f}ms"
    _ok(f"OcrTranslator cache hit: {elapsed_ms:.1f}ms")


def test_qimage_to_pil_roundtrip() -> None:
    from PySide6.QtGui import QImage

    qimg = QImage(128, 64, QImage.Format_RGB888)
    qimg.fill(0x336699)  # type: ignore[arg-type]
    pil = qimage_to_pil(qimg)
    assert pil is not None and pil.size == (128, 64)
    px = pil.getpixel((10, 10))
    assert isinstance(px, tuple) and len(px) == 3
    _ok("qimage_to_pil roundtrip works")


def test_ollama_happy_path() -> None:
    base = default_ollama_base()
    names = ollama_list_model_names(base)
    if not names:
        print(f"  SKIP Ollama not reachable at {base}")
        return
    model = next((n for n in names if "gemma" in n.lower()), names[0])
    en = ollama_chat_translate("Guten Tag, wie geht es Ihnen?", model, base)
    assert en, "Ollama returned empty"
    low = en.lower()
    for phrase in ("here is the translation", "translation:", "the translation is"):
        assert phrase not in low, f"chatter slipped through: {en!r}"
    _ok(f"Ollama chat ({model}) → {en[:60]!r}")


def test_translation_engine_ready_caches() -> None:
    t = OcrTranslator(backend="ollama", ollama_model="this-model-does-not-exist:latest")
    t.translation_engine_ready()
    t1 = time.monotonic()
    for _ in range(10):
        t.translation_engine_ready()
    elapsed = (time.monotonic() - t1) * 1000
    assert elapsed < 100, f"engine readiness should be cached, got {elapsed:.0f}ms"
    _ok(f"translation_engine_ready cached: 10 calls in {elapsed:.1f}ms")


def test_url_safety() -> None:
    import os as _os
    _os.environ.pop("LIVETRANSLATE_ALLOW_REMOTE_OLLAMA", None)
    ok, _ = _is_safe_ollama_url("http://127.0.0.1:11434")
    assert ok
    ok, _ = _is_safe_ollama_url("http://localhost:11434")
    assert ok
    ok, _ = _is_safe_ollama_url("http://[::1]:11434")
    assert ok
    bad_cases = [
        "file:///etc/passwd",
        "ftp://example.com/",
        "http://attacker.example.com/",
        "https://example.com/",
        "javascript:alert(1)",
        "not a url at all",
    ]
    for u in bad_cases:
        ok, _ = _is_safe_ollama_url(u)
        assert not ok, f"should reject {u!r}"
    _os.environ["LIVETRANSLATE_ALLOW_REMOTE_OLLAMA"] = "1"
    try:
        ok, _ = _is_safe_ollama_url("https://example.com/")
        assert ok, "explicit opt-in should allow remote http(s)"
        ok, _ = _is_safe_ollama_url("file:///etc/passwd")
        assert not ok, "scheme guard must still reject file://"
    finally:
        _os.environ.pop("LIVETRANSLATE_ALLOW_REMOTE_OLLAMA", None)
    _ok("Ollama URL safety: scheme + non-localhost guards")


def test_default_base_falls_back_safely(monkey_env=None) -> None:
    import os as _os
    saved = _os.environ.get("OLLAMA_BASE_URL")
    try:
        _os.environ["OLLAMA_BASE_URL"] = "file:///etc/passwd"
        assert default_ollama_base() == "http://127.0.0.1:11434"
        _os.environ["OLLAMA_BASE_URL"] = "http://attacker.example.com"
        assert default_ollama_base() == "http://127.0.0.1:11434"
    finally:
        if saved is None:
            _os.environ.pop("OLLAMA_BASE_URL", None)
        else:
            _os.environ["OLLAMA_BASE_URL"] = saved
    _ok("default_ollama_base: rejects unsafe OLLAMA_BASE_URL")


def test_unsafe_url_blocks_chat() -> None:
    try:
        ollama_chat_translate("Hallo", "gemma2:2b", "file:///etc/passwd")
    except PermissionError:
        _ok("ollama_chat_translate raises on unsafe scheme")
        return
    raise AssertionError("ollama_chat_translate must reject unsafe URLs")


def test_log_redaction_default() -> None:
    import os as _os
    import ocr_translator as _ot
    saved = _ot.DEBUG_LOG_CONTENT
    try:
        _ot.DEBUG_LOG_CONTENT = False
        cap = io.StringIO()
        old = sys.stdout
        sys.stdout = cap
        try:
            t = OcrTranslator(backend="opus")
            if t.opus_translator.available:
                t.translate_text("Geheime Information XYZ")
        finally:
            sys.stdout = old
        out = cap.getvalue()
        assert "Geheime Information XYZ" not in out, "OCR/translation content must not leak with redaction on"
        _ok("log redaction default: no captured text in stdout")
    finally:
        _ot.DEBUG_LOG_CONTENT = saved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama", action="store_true", help="also run Ollama call")
    args = ap.parse_args()

    print("Running tests…")
    test_strip_chatter()
    test_signature_stable_and_distinct()
    test_dedup_normalize()
    test_lru_cache()
    test_qimage_to_pil_roundtrip()
    test_translation_engine_ready_caches()
    test_translator_caches()
    test_url_safety()
    test_default_base_falls_back_safely()
    test_unsafe_url_blocks_chat()
    test_log_redaction_default()
    if args.ollama:
        test_ollama_happy_path()
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
