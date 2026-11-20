"""Manual end-to-end check: real model + real Calculator launch/quit + confirmation."""
import time
from core.assistant import Assistant

asked = []
def approve(s): asked.append(s); return True
def deny(s): asked.append(s); return False

for label, confirm, prompt in [
    ("open", approve, "Open Calculator."),
    ("sysinfo", approve, "How much free disk space and battery do I have?"),
    ("close-approved", approve, "Close Calculator."),
    ("open", approve, "Open Calculator."),
    ("close-denied", deny, "Quit Calculator."),
]:
    a = Assistant(confirm=confirm)
    t = time.time(); r = a.handle(prompt)
    print(f"[{label}] {time.time()-t:.1f}s tools={[(n, o['ok']) for n,_,o in a.last_tool_calls]}\n   {r}")
print("confirmations asked:", asked)
