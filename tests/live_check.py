"""Manual live check against the local model (stubs for side-effecting tools)."""
import sys, time
from core.assistant import Assistant
from core.command_router import Tool, ToolRegistry, default_registry
from actions.system import get_current_time

reg = ToolRegistry()
reg.register(Tool("get_current_time", "Get the current local date and time.", get_current_time))
for real in default_registry()._tools.values():
    if real.name != "get_current_time":
        reg.register(Tool(real.name, real.description, lambda **kw: f"(stub) ran with {kw}", real.parameters))

PROMPTS = [
    ("What time is it?", "get_current_time"),
    ("Open Calculator.", "open_application"),
    ("Search for Python tutorials.", "search_web"),
    ("Open youtube.com", "open_website"),
    ("Hi, who are you?", None),
]
hits = 0
for prompt, expected in PROMPTS:
    a = Assistant(registry=reg)
    t = time.time()
    reply = a.handle(prompt)
    called = a.last_tool_calls[0][0] if a.last_tool_calls else None
    ok = called == expected
    hits += ok
    print(f"{'PASS' if ok else 'FAIL'} {time.time()-t:4.1f}s  {prompt!r} -> tool={called} args={a.last_tool_calls[0][1] if a.last_tool_calls else {}}\n     reply: {reply}")
print(f"{hits}/{len(PROMPTS)}")
