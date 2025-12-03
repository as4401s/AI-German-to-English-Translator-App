#!/usr/bin/env python3
"""Download Helsinki-NLP/opus-mt-de-en model for bundling."""

import sys
from pathlib import Path

try:
    from transformers import MarianMTModel, MarianTokenizer
    import torch
except ImportError:
    print("❌ transformers not installed!")
    print("   Run: uv sync")
    print("   Or use: uv run python download_opus_model.py")
    sys.exit(1)

MODEL_NAME = "Helsinki-NLP/opus-mt-de-en"
MODEL_DIR = Path(__file__).parent / "models" / "opus-mt-de-en"

def download_model():
    """Download and save the model locally."""
    print("=" * 70)
    print("Downloading Helsinki-NLP/opus-mt-de-en Model")
    print("=" * 70)
    print()
    print(f"Model: {MODEL_NAME}")
    print(f"Target: {MODEL_DIR}")
    print()
    
    # Create model directory
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        print("Downloading tokenizer...")
        tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
        tokenizer.save_pretrained(MODEL_DIR)
        print("✓ Tokenizer saved")
        print()
        
        print("Downloading model (this may take a few minutes)...")
        model = MarianMTModel.from_pretrained(MODEL_NAME)
        model.save_pretrained(MODEL_DIR)
        print("✓ Model saved")
        print()
        
        # Check size
        total_size = sum(f.stat().st_size for f in MODEL_DIR.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        
        print("=" * 70)
        print("✅ Model downloaded successfully!")
        print("=" * 70)
        print()
        print(f"Location: {MODEL_DIR}")
        print(f"Size: {size_mb:.1f}MB")
        print()
        print("Model files:")
        for f in sorted(MODEL_DIR.rglob('*')):
            if f.is_file():
                print(f"  - {f.relative_to(MODEL_DIR.parent.parent)} ({f.stat().st_size / (1024*1024):.1f}MB)")
        print()
        print("You can now build the app with:")
        print("  ./build_app.sh")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Download failed: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    download_model()

