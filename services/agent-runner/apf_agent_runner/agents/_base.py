"""Shared helpers for all APF agents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Resolve the prompt templates that live in apf_agent_core.
_PROMPT_DIR = (
    Path(__file__).resolve().parents[4]  # repo root
    / "packages"
    / "agent-core"
    / "apf_agent_core"
    / "prompts"
)

_jinja_env: Environment | None = None


def _get_jinja_env() -> Environment:
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(_PROMPT_DIR)),
            autoescape=select_autoescape([]),  # no HTML escaping for LLM prompts
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


def render_prompt(template_name: str, ctx: Any) -> tuple[str, str]:
    """Render a Jinja2 template and return ``(system_prompt, user_prompt)``.

    The templates use ``{% block system %}`` / ``{% block user %}`` blocks.
    We render the full template once, then split on the block boundaries so
    that agents can pass system and user messages separately to the LLM.
    """
    env = _get_jinja_env()
    tmpl = env.get_template(template_name)

    # Render system block
    system_src = "{% extends '" + template_name + "' %}{% block user %}{% endblock %}"
    system_tmpl = env.from_string(system_src)
    system = system_tmpl.render(ctx=ctx).strip()

    # Render user block
    user_src = "{% extends '" + template_name + "' %}{% block system %}{% endblock %}"
    user_tmpl = env.from_string(user_src)
    user = user_tmpl.render(ctx=ctx).strip()

    return system, user


def extract_json(text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from an LLM response.

    Handles:
    - Raw JSON
    - JSON wrapped in ```json ... ``` fences
    - Leading/trailing prose before/after the JSON object
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening fence (e.g. ```json)
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt to extract the outermost JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:500]}")
