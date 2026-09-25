"""Loads and renders prompt templates from prompts/*.md.

Templates use {{token}} placeholders (not str.format's {}) so prompt text can safely
contain literal braces, e.g. JSON examples describing the expected structured output.
"""

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache
def _load_template(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text()


def render_prompt(name: str, **values: str) -> str:
    text = _load_template(name)
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text
