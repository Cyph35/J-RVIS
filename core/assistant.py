"""Main conversation flow: model -> validated tool call -> result -> reply."""
from typing import Callable

import config
from core.brain import Brain
from core.command_router import ToolRegistry, default_registry


class Assistant:
    def __init__(self, brain: Brain | None = None, registry: ToolRegistry | None = None,
                 confirm: Callable[[str], bool] | None = None) -> None:
        self.confirm = confirm
        self.brain = brain or Brain()
        self.registry = registry or default_registry()
        self.messages: list[dict] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.last_tool_calls: list[tuple[str, dict, dict]] = []  # (name, args, outcome)

    def handle(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        self.last_tool_calls = []
        reply = None
        for _ in range(config.MAX_TOOL_ROUNDS):
            try:
                msg = self.brain.chat(self.messages, self.registry.schemas())
            except Exception as exc:
                self.messages.pop() if self.messages[-1]["role"] == "user" else None
                return f"I can't reach my local AI model right now ({type(exc).__name__}). Is Ollama running? Try: ollama serve"
            self.messages.append(msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else msg)
            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                break
            for call in msg.tool_calls:
                name, args = call.function.name, dict(call.function.arguments or {})
                outcome = self.registry.execute(name, args, self.confirm)
                self.last_tool_calls.append((name, args, outcome))
                content = outcome.get("result") if outcome["ok"] else "ERROR: " + outcome["error"]
                self.messages.append({"role": "tool", "tool_name": name, "content": content})
        if reply is None:
            reply = "Sorry, I couldn't complete that request."
        return reply
