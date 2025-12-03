#!/bin/bash
set -e

echo "======================================"
echo "Building DMG for LiveTranslate.app"
echo "======================================"
echo ""

# Check if app exists
if [ ! -d "dist/LiveTranslate.app" ]; then
    echo "❌ LiveTranslate.app not found!"
    echo "   Run: ./build_app.sh first"
    exit 1
fi

APP_NAME="LiveTranslate"
DMG_NAME="${APP_NAME}.dmg"
DMG_PATH="dist/${DMG_NAME}"

# Remove old DMG if exists
if [ -f "$DMG_PATH" ]; then
    echo "Removing old DMG..."
    rm -f "$DMG_PATH"
fi

echo "Creating DMG..."
echo ""

# Create a temporary directory for DMG contents
TEMP_DMG_DIR="dist/dmg_contents"
rm -rf "$TEMP_DMG_DIR"
mkdir -p "$TEMP_DMG_DIR"

# Copy app to temp directory
cp -R "dist/LiveTranslate.app" "$TEMP_DMG_DIR/"

# Create Applications symlink (standard macOS DMG convention)
ln -s /Applications "$TEMP_DMG_DIR/Applications"

# Create a background image directory (optional, for better DMG appearance)
# For now, we'll create a simple DMG without custom background

# Calculate size needed (app size + 100MB overhead)
APP_SIZE=$(du -sm "dist/LiveTranslate.app" | cut -f1)
DMG_SIZE=$((APP_SIZE + 100))

echo "Creating disk image..."
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$TEMP_DMG_DIR" \
    -ov \
    -format UDZO \
    -size ${DMG_SIZE}m \
    "$DMG_PATH"

# Clean up temp directory
rm -rf "$TEMP_DMG_DIR"

# Get final DMG size
DMG_SIZE_MB=$(du -sh "$DMG_PATH" | cut -f1)

echo ""
echo "======================================"
echo "✅ DMG created successfully!"
echo "======================================"
echo ""
echo "DMG: $DMG_PATH"
echo "Size: $DMG_SIZE_MB"
echo ""
echo "To test:"
echo "  open $DMG_PATH"
echo ""
echo "To distribute:"
echo "  Share the DMG file - users can drag the app to Applications"
echo ""

