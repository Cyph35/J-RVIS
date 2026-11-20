"""AI model connection. Only this file knows about Ollama."""
import ollama

import config


class Brain:
    def __init__(self, model: str = config.OLLAMA_MODEL, host: str = config.OLLAMA_HOST) -> None:
        self.model = model
        self.client = ollama.Client(host=host)

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """Return the assistant message (may contain tool_calls)."""
        response = self.client.chat(
            model=self.model,
            messages=messages,
            tools=tools or None,
            think=False,
            keep_alive="30m",
        )
        return response.message
