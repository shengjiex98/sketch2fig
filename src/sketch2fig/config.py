"""Application settings and shared Claude API helper."""

import base64
import logging
import re
from pathlib import Path

import anthropic
from anthropic.types import ImageBlockParam, TextBlock, TextBlockParam
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_MAGIC_MEDIA_TYPES: dict[bytes, str] = {
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF8": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP
}

_EXT_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _detect_media_type(path: Path, raw: bytes) -> str:
    """Detect image media type from magic bytes, falling back to extension."""
    for magic, media_type in _MAGIC_MEDIA_TYPES.items():
        if raw.startswith(magic):
            return media_type
    return _EXT_MEDIA_TYPES.get(path.suffix.lower(), "image/png")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SKETCH2FIG_",
        env_file=".env",
        extra="ignore",
    )

    model: str = "claude-sonnet-4-6"
    # Read ANTHROPIC_API_KEY (standard name, no prefix) or SKETCH2FIG_ANTHROPIC_API_KEY
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "SKETCH2FIG_ANTHROPIC_API_KEY"),
    )


settings = Settings()


def call_claude(
    system: str,
    user_text: str,
    image_paths: list[Path] | None = None,
    response_format: str = "json",
) -> str:
    """Call Claude with optional images and return the text response.

    Args:
        system: System prompt.
        user_text: User message text.
        image_paths: Optional list of image files to include before the text.
        response_format: "json" appends a reminder to return raw JSON; "text" leaves as-is.

    Returns:
        Raw text from Claude's first content block.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)

    content: list[ImageBlockParam | TextBlockParam] = []
    for path in image_paths or []:
        raw = path.read_bytes()
        data = base64.standard_b64encode(raw).decode("utf-8")
        media_type = _detect_media_type(path, raw)
        content.append(
            ImageBlockParam(
                type="image",
                source={"type": "base64", "media_type": media_type, "data": data},  # type: ignore[arg-type]
            )
        )

    if response_format == "json":
        user_text = (
            user_text + "\n\nRespond with valid JSON only — no markdown code fences."
        )

    content.append(TextBlockParam(type="text", text=user_text))

    message = client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": content}],
    )

    usage = message.usage
    logger.info(
        "Claude usage: input_tokens=%d output_tokens=%d",
        usage.input_tokens,
        usage.output_tokens,
    )

    block = message.content[0]
    if not isinstance(block, TextBlock):
        raise ValueError(f"Expected TextBlock, got {type(block).__name__}")
    return block.text


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from a JSON response, if present."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def extract_tikz_block(text: str) -> str:
    """Extract the tikzpicture environment from a fenced code block response."""
    # Try to find content inside ```latex ... ``` or ``` ... ```
    m = re.search(r"```(?:latex|tex)?\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # If no fence, return as-is (might already be a raw block)
    return text.strip()
