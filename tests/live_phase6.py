"""Manual live check: real model, 11 tools, side-effecting tools stubbed, in-memory DB."""
import time
from core.assistant import Assistant
from core.brain import Brain
from core.command_router import Tool, default_registry
from memory.conversation import Memory
from memory.database import connect

mem, brain = Memory(connect(":memory:")), Brain()
reg = default_registry(memory=mem, brain=brain)
KEEP = {"get_current_time", "remember_preference", "run_workflow"}
for name, t in list(reg._tools.items()):
    if name not in KEEP:
        reg.register(Tool(name, t.description, lambda _n=name, **kw: f"(stub {_n}) {kw}", t.parameters, sensitive=False))
reg.register(Tool("open_application", reg._tools["open_application"].description, lambda **kw: "(stub open)", reg._tools["open_application"].parameters))
import actions.workflows as wf
for steps in wf.WORKFLOWS.values(): pass

CASES = [("What time is it?", "get_current_time"), ("Open Calculator.", "open_application"),
         ("Find my resume file.", "search_files"), ("Pause the music.", "music_control"),
         ("What song is playing right now?", "music_control"), ("Start my work setup.", "run_workflow"),
         ("Remember that my favorite music is lofi.", "remember_preference"),
         ("What is on my screen?", "analyze_screen"), ("Search for Python tutorials.", "search_web"),
         ("Hi, who are you?", None)]
hits = 0
for prompt, expected in CASES:
    a = Assistant(brain=brain, registry=reg, memory=mem)
    t = time.time(); r = a.handle(prompt)
    called = a.last_tool_calls[0] if a.last_tool_calls else None
    ok = (called[0] if called else None) == expected; hits += ok
    print(f"{'PASS' if ok else 'FAIL'} {time.time()-t:4.1f}s {prompt!r} -> {called[0] if called else None} {called[1] if called else ''}")
print(f"{hits}/{len(CASES)}  prefs={mem.prefs()}")
a = Assistant(brain=brain, registry=reg, memory=mem)
print("recall:", a.handle("What is my favorite music?"))
