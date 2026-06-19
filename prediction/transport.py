"""Default LLM transport using the Anthropic SDK.

Provides a ready-made ``llm_call`` callable for ``adjust_prediction``. Reads
``ANTHROPIC_API_KEY`` from the environment. When the key is absent the factory
returns ``None`` so the hybrid engine degrades to the deterministic baseline.
"""

from __future__ import annotations

import json
import os
from typing import Callable, Optional

from .llm_adjuster import MODEL_ID

_MAX_TOKENS = 512


def make_anthropic_llm_call() -> Optional[Callable[[str], str]]:
    """Return an ``llm_call`` backed by the Anthropic SDK, or ``None``.

    Returns ``None`` when ``ANTHROPIC_API_KEY`` is not set, letting the caller
    fall back to the deterministic baseline without crashing.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def _call(prompt: str) -> str:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        # The model sometimes wraps JSON in a code fence; strip it.
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            stripped = "\n".join(lines).strip()
        json.loads(stripped)  # validate; raises on bad JSON (caught upstream)
        return stripped

    return _call
