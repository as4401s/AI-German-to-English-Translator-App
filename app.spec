# -*- mode: python ; coding: utf-8 -*-

import glob
import os
from pathlib import Path

block_cipher = None

# Include bundled model files
datas = []
model_dir = Path('models/opus-mt-de-en')
if model_dir.exists():
    # Include all model files into Resources/models/opus-mt-de-en
    for model_file in model_dir.rglob('*'):
        if model_file.is_file():
            # Bundle into Resources/models/opus-mt-de-en/
            rel_path = model_file.relative_to(model_dir)
            datas.append((str(model_file), f'models/opus-mt-de-en/{rel_path.parent}' if rel_path.parent != Path('.') else 'models/opus-mt-de-en'))
    model_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file()) / (1024**2)
    print(f"✓ Including bundled model: {model_dir} ({model_size:.1f}MB)")
else:
    print("⚠️  WARNING: Model directory not found!")
    print("   Run: uv run python download_opus_model.py")

binaries = []

a = Analysis(
    ['app.py'],  # Main script - PyInstaller will auto-detect imports
    pathex=[],  # Current directory is already in path
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # Local modules
        'widgets',
        'capture',
        'ocr_translator',
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # PIL
        'PIL',
        'PIL._imaging',
        # OCR
        'pytesseract',
        # Transformers
        'transformers',
        'torch',
        'sentencepiece',
        'sacremoses',
        'safetensors',
        'huggingface_hub',
        'transformers.models.marian.*',
        # Other dependencies
        'mss',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LiveTranslate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Enable console to see errors when double-clicking
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LiveTranslate',
)

app = BUNDLE(
    coll,
    name='LiveTranslate.app',
    icon='my_app_icon.icns',
    bundle_identifier='com.livetranslate.app',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'Live Translate',
        'CFBundleDisplayName': 'Live Translate',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
    },
)
