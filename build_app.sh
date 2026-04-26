#!/bin/bash
set -e

echo "======================================"
echo "Building Standalone LiveTranslate.app"
echo "======================================"
echo ""

# Check for bundled model
echo "1. Checking for model..."
MODEL_DIR="models/opus-mt-de-en"
if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/model.safetensors" ]; then
    MODEL_SIZE=$(du -sh "$MODEL_DIR" | cut -f1)
    echo "   ✓ Found bundled model: $MODEL_DIR ($MODEL_SIZE)"
else
    echo "   ✗ Model not found!"
    echo ""
    echo "Please download the model first:"
    echo "  uv run python download_opus_model.py"
    echo ""
    exit 1
fi
echo ""

# Check dependencies
echo "2. Checking dependencies..."
if ! command -v tesseract &> /dev/null; then
    echo "   ⚠️  Tesseract not found!"
    echo "   Install: brew install tesseract tesseract-lang"
    exit 1
fi
echo "   ✓ Tesseract installed"

if ! uv run python -c "import transformers" 2>/dev/null; then
    echo "   ⚠️  transformers not found!"
    echo "   Run: uv sync"
    exit 1
fi
echo "   ✓ transformers installed"
echo ""

# Clean previous builds
echo "3. Cleaning previous builds..."
rm -rf build dist
echo "   ✓ Cleaned"
echo ""

# Build
echo "4. Building app (this may take 5-10 minutes)..."
echo ""
uv run pyinstaller app.spec --noconfirm
echo ""

# Sign the app
echo "5. Signing app..."
if [ -d "dist/LiveTranslate.app" ]; then
    xattr -cr dist/LiveTranslate.app 2>/dev/null || true
    codesign --force --deep --sign - dist/LiveTranslate.app 2>/dev/null || true
    echo "   ✓ Signed"
fi
echo ""

# Check result
if [ -d "dist/LiveTranslate.app" ]; then
    APP_SIZE=$(du -sh dist/LiveTranslate.app | cut -f1)
    echo "======================================"
    echo "✅ Build successful!"
    echo "======================================"
    echo ""
    echo "App: dist/LiveTranslate.app"
    echo "Size: $APP_SIZE"
    echo ""
    echo "What's included:"
    echo "  ✓ Opus-MT model (~285MB, bundled) — offline \"Opus-MT\" in the app"
    echo "  ✓ Python runtime"
    echo "  ✓ All libraries (transformers, torch)"
    echo "  ✓ Custom icon"
    echo ""
    echo "Optional: Gemma via Ollama (not bundled — install ollama.ai and ollama pull <model>)"
    echo ""
    echo "To test:"
    echo "  open dist/LiveTranslate.app"
    echo ""
    echo "To install:"
    echo "  cp -r dist/LiveTranslate.app /Applications/"
    echo ""
    echo "Note: Opus path works fully offline. Ollama path uses the Mac's Ollama daemon (localhost)."
    echo "      Users need Tesseract: brew install tesseract tesseract-lang"
    echo ""
else
    echo "======================================"
    echo "❌ Build failed!"
    echo "======================================"
    exit 1
fi
