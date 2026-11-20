"""Main conversation flow: model -> validated tool call -> result -> reply."""
import threading
from typing import Callable

import config
from core.brain import Brain
from core.command_router import ToolRegistry, default_registry


class Assistant:
    def __init__(self, brain: Brain | None = None, registry: ToolRegistry | None = None,
                 confirm: Callable[[str], bool] | None = None, memory=None) -> None:
        self.confirm = confirm
        self._lock = threading.Lock()  # voice and typed requests share one conversation
        self.memory = memory
        self.brain = brain or Brain()
        self.registry = registry or default_registry(memory=memory, brain=self.brain)
        self.messages: list[dict] = [{"role": "system", "content": self._system_prompt()}]
        if memory is not None:
            self.messages += memory.recent_messages(config.HISTORY_MESSAGES)
        self.last_tool_calls: list[tuple[str, dict, dict]] = []  # (name, args, outcome)

    def _system_prompt(self) -> str:
        prompt = config.SYSTEM_PROMPT
        prefs = self.memory.prefs() if self.memory is not None else {}
        if prefs:
            prompt += " Known facts about the user: " + "; ".join(f"{k} = {v}" for k, v in prefs.items()) + "."
        return prompt

    def handle(self, user_text: str, confirm: Callable[[str], bool] | None = None) -> str:
        with self._lock:
            return self._handle(user_text, confirm or self.confirm)

    def _handle(self, user_text: str, confirm: Callable[[str], bool] | None) -> str:
        self.messages[0]["content"] = self._system_prompt()  # pick up newly remembered facts
        self.messages.append({"role": "user", "content": user_text})
        self.last_tool_calls = []
        reply = None
        for _ in range(config.MAX_TOOL_ROUNDS):
            try:
                msg = self.brain.chat(self.messages, self.registry.schemas())
            except Exception as exc:
                if self.messages[-1]["role"] == "user":
                    self.messages.pop()
                return f"I can't reach my local AI model right now ({type(exc).__name__}). Is Ollama running? Try: ollama serve"
            self.messages.append(msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else msg)
            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                break
            for call in msg.tool_calls:
                name, args = call.function.name, dict(call.function.arguments or {})
                if len(self.last_tool_calls) >= config.MAX_TOOL_CALLS_PER_REQUEST:
                    outcome = {"ok": False, "error": "Tool call limit reached for this request."}
                else:
                    outcome = self.registry.execute(name, args, confirm)
                self.last_tool_calls.append((name, args, outcome))
                if self.memory is not None:
                    self.memory.log_task(name, args, outcome["ok"])
                content = outcome.get("result") if outcome["ok"] else "ERROR: " + outcome["error"]
                self.messages.append({"role": "tool", "tool_name": name, "content": content})
        if reply is None:
            reply = "Sorry, I couldn't complete that request."
        if self.memory is not None:
            self.memory.add_message("user", user_text)
            self.memory.add_message("assistant", reply)
        return reply
