"""Thin client for the clef-flash model served by LM Studio's OpenAI-compatible API."""

from collections.abc import Iterator

from openai import OpenAI

BASE_URL = "http://localhost:1234/v1"
MODEL = "clef-flash"


class ClefFlash:
    def __init__(self, base_url: str = BASE_URL, model: str = MODEL) -> None:
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key="lm-studio")

    def chat(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """Return the answer text; clef-flash often puts it in `reasoning_content`."""
        resp = self.client.chat.completions.create(
            model=self.model, messages=self._messages(prompt, system), **kwargs
        )
        msg = resp.choices[0].message
        reasoning = getattr(msg, "reasoning_content", None) or ""
        return f"{reasoning}\n{msg.content or ''}".strip()

    def stream(self, prompt: str, system: str | None = None, **kwargs) -> Iterator[str]:
        for chunk in self.client.chat.completions.create(
            model=self.model, messages=self._messages(prompt, system), stream=True, **kwargs
        ):
            if chunk.choices and (delta := chunk.choices[0].delta.content):
                yield delta

    @staticmethod
    def _messages(prompt: str, system: str | None) -> list[dict]:
        msgs = [{"role": "system", "content": system}] if system else []
        msgs.append({"role": "user", "content": prompt})
        return msgs
