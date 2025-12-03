# Live Translate

Real-time on-screen German to English translation - fully standalone macOS app.

## Features

- 🎯 **Real-time Translation**: Captures and translates German text from your screen
- 🔒 **Privacy First**: 100% offline - all processing on your Mac
- 🖼️ **Screen Capture**: Select any region to translate
- ⚡ **Fast**: ~5 seconds per translation
- 💻 **Standalone**: No internet or external servers needed
- 🎨 **Custom Icon**: Professional macOS app

## Running from Source (CLI)

### Quick Start
```bash
# Install dependencies
uv sync

# Download translation model (if not already downloaded)
uv run python download_opus_model.py

# Run the app
uv run python app.py
```

Or use the convenience script:
```bash
./run.sh
```

### Prerequisites
- **Tesseract OCR**: `brew install tesseract tesseract-lang`
- **Python 3.11+**: Managed by `uv`
- **Translation Model**: Run `download_opus_model.py` first (downloads ~285MB)

## Build Standalone App

### 1. Install Tesseract
```bash
brew install tesseract tesseract-lang
```

### 2. Install Python Dependencies
```bash
uv sync
```

### 3. Download Translation Model (~285MB)
```bash
uv run python download_opus_model.py
```

This downloads the Helsinki-NLP/opus-mt-de-en model (~285MB).

### 4. Build the App
```bash
./build_app.sh
```

This creates `dist/LiveTranslate.app` (~800MB total with model bundled).

### 5. Install
```bash
cp -r dist/LiveTranslate.app /Applications/
```

## Using the App

1. **Launch**: Open `LiveTranslate.app`
2. **First time**: 
   - Wait ~10 seconds (loads 1.6GB AI model)
   - Grant Screen Recording permission
3. **Translate**:
   - Click "Select Region"
   - Draw rectangle over German text
   - Click "Start Translation"
   - English appears in real-time!

## Permissions

**Screen Recording permission required.**

System Settings → Privacy & Security → Screen Recording → Enable LiveTranslate

**Note**: Permission prompt appears each time you select a region. This is normal macOS behavior for unsigned apps.

## What's Included

- **285MB AI Model**: Helsinki-NLP/opus-mt-de-en - fast and accurate German→English translation
- **Python Runtime**: Complete Python environment
- **All Libraries**: Qt6, Pillow, transformers, torch, pytesseract
- **Custom Icon**: Professional app icon
- **Fully Standalone**: No internet or external dependencies needed

## Distribution

**Your app is ready!** → `dist/LiveTranslate.app` (800MB)

### Works On Any Mac
- ✅ Apple Silicon (M1/M2/M3/M4)
- ✅ Intel Macs  
- ✅ macOS 10.13+

### To Share the App

**Option 1: Create ZIP**
```bash
zip -r LiveTranslate.zip dist/LiveTranslate.app
```

**Option 2: Create DMG** (recommended)
```bash
hdiutil create -volname "LiveTranslate" -srcfolder dist/LiveTranslate.app -ov -format UDZO LiveTranslate.dmg
```

**Option 3: Direct copy**
- AirDrop to other Macs
- Copy to USB drive
- Share via cloud storage

### User Setup (One-time)
Users only need Tesseract OCR:
```bash
brew install tesseract tesseract-lang
```

Then:
1. Drag `LiveTranslate.app` to `/Applications/`
2. Launch and grant Screen Recording permission
3. Done! No configuration needed.

## How It Works

1. Captures selected screen region every second
2. Extracts German text using Tesseract OCR
3. Translates to English using embedded Opus-MT model (offline!)
4. Displays English translation in real-time

## Tips

- Use clear, readable text for best results
- Larger text works better
- Keep "Always on top" checked to see translations over other windows
- Translation takes ~2-3 seconds per frame (3x FASTER!)

## Troubleshooting

### "Translation model not available"
**Fix**: Model should be bundled. If you see this, rebuild:
```bash
./build_app.sh
```

### "Permission denied" for screen capture
**Fix**: Grant Screen Recording permission in System Settings → Privacy

### Slow translations
**Normal**: 3-5 seconds per translation is expected for local AI

## Tech Stack

- **PySide6**: UI framework
- **Tesseract**: OCR engine  
- **transformers**: Hugging Face transformers library
- **Helsinki-NLP/opus-mt-de-en**: MarianMT translation model
- **Pillow**: Image processing
