"""
Smoke-test Ollama DE→EN: output must be plain English (no "here is the translation" style).
Run: uv run python test_ollama_translate.py
Requires Ollama; uses OLLAMA_BASE_URL and picks first gemma* tag or --model.
"""
from __future__ import annotations

import argparse
import sys

from ocr_translator import (
    ollama_chat_translate,
    ollama_list_model_names,
    strip_translation_chatter,
    default_ollama_base,
)

BAD = (
    "here is the translation",
    "the translation is",
    "translation:",
    "here's the translation",
)


def _pick_model(explicit: str | None) -> str:
    if explicit:
        return explicit
    base = default_ollama_base()
    for n in ollama_list_model_names(base):
        if "gemma" in n.lower():
            return n
    raise SystemExit("No gemma* model in Ollama. Pull one: ollama pull gemma2:2b")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", help="Ollama model name (e.g. gemma3:12b)")
    args = p.parse_args()
    model = _pick_model(args.model)
    base = default_ollama_base()
    print(f"Using {model} @ {base}", file=sys.stderr)

    cases = [
        "Guten Tag, wie geht es Ihnen?",
        "Können Sie mir bitte helfen? Ich verstehe das nicht ganz.",
    ]
    for de in cases:
        en = ollama_chat_translate(de, model, base)
        low = en.lower()
        for phrase in BAD:
            assert phrase not in low, f"chatter in output: {en!r} (matched {phrase!r})"
        assert en.strip() == en
        print(f"DE: {de}\nEN: {en}\n---")

    # strip_chatter
    s = strip_translation_chatter("Here is the translation:\n\nHello, world")
    assert s.lower().strip().startswith("hello")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
