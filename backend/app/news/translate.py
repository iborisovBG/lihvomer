"""Офлайн превод EN→BG чрез Argos Translate.

Моделът е с отворен код и се изпълнява локално — няма API ключ, няма такса и
няма изпращане на съдържание към трета страна. Ако пакетът не е инсталиран,
преводът се пропуска и оригиналният текст се запазва, вместо да се показва
подвеждащ резултат.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_ready: bool | None = None


def _ensure_model() -> bool:
    global _ready
    if _ready is not None:
        return _ready

    with _lock:
        if _ready is not None:
            return _ready
        try:
            import argostranslate.translate as translate

            languages = {lang.code for lang in translate.get_installed_languages()}
            _ready = {"en", "bg"} <= languages
            if not _ready:
                logger.warning(
                    "Езиковият пакет en→bg не е инсталиран. "
                    "Пуснете `python -m scripts.install_translator`."
                )
        except ImportError:
            logger.warning("argostranslate не е инсталиран; преводът е изключен.")
            _ready = False
    return _ready


def translate_to_bg(text: str, source_language: str) -> tuple[str, bool]:
    """Връща (текст, дали е преведен)."""
    if not text or source_language == "bg":
        return text, False
    if not _ensure_model():
        return text, False

    try:
        import argostranslate.translate as translate

        return translate.translate(text, source_language, "bg"), True
    except Exception as exc:
        logger.warning("Преводът се провали: %s", exc)
        return text, False


def translator_available() -> bool:
    return _ensure_model()
