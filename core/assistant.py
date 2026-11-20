"""Main conversation flow: model -> validated tool call -> result -> reply."""
import config
from core.brain import Brain
from core.command_router import ToolRegistry, default_registry


class Assistant:
    def __init__(self, brain: Brain | None = None, registry: ToolRegistry | None = None) -> None:
        self.brain = brain or Brain()
        self.registry = registry or default_registry()
        self.messages: list[dict] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.last_tool_calls: list[tuple[str, dict, dict]] = []  # (name, args, outcome)

    def handle(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        self.last_tool_calls = []
        reply = None
        for _ in range(config.MAX_TOOL_ROUNDS):
            msg = self.brain.chat(self.messages, self.registry.schemas())
            self.messages.append(msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else msg)
            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                break
            for call in msg.tool_calls:
                name, args = call.function.name, dict(call.function.arguments or {})
                outcome = self.registry.execute(name, args)
                self.last_tool_calls.append((name, args, outcome))
                content = outcome.get("result") if outcome["ok"] else "ERROR: " + outcome["error"]
                self.messages.append({"role": "tool", "tool_name": name, "content": content})
        if reply is None:
            reply = "Sorry, I couldn't complete that request."
        return reply
