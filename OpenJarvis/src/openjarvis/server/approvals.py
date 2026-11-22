"""Voice/screen approvals for risky tool calls.

The agent asks ``confirm(prompt)`` before a tool that changes things (run a command, write a file, commit). The call blocks until the
user answers through the app (``POST /v1/approvals/{id}``) or the request times out, and silence always means NO."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

TIMEOUT_SECONDS = 120
_generation = 0          # bumps whenever the user interrupts; running agent loops compare it and stop


def generation() -> int:
    return _generation


class ApprovalBroker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: Dict[str, Dict[str, Any]] = {}

    def confirm(self, prompt: str) -> bool:
        item = {"id": uuid.uuid4().hex[:10], "prompt": prompt, "created": time.time(), "event": threading.Event(), "approved": False}
        with self._lock:
            self._pending[item["id"]] = item
        try:
            item["event"].wait(TIMEOUT_SECONDS)
            return bool(item["approved"]) and item["event"].is_set()
        finally:
            with self._lock:
                self._pending.pop(item["id"], None)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"id": i["id"], "prompt": i["prompt"], "age": round(time.time() - i["created"], 1)} for i in self._pending.values() if not i["event"].is_set()]

    def deny_all(self) -> int:
        with self._lock:
            items = [i for i in self._pending.values() if not i["event"].is_set()]
        for i in items:
            i["approved"] = False
            i["event"].set()
        return len(items)

    def resolve(self, approval_id: str, approve: bool) -> bool:
        with self._lock:
            item = self._pending.get(approval_id)
        if not item or item["event"].is_set():
            return False
        item["approved"] = bool(approve)
        item["event"].set()
        return True


broker = ApprovalBroker()


try:  # module level: with postponed annotations FastAPI cannot resolve a class defined inside the function
    from pydantic import BaseModel

    class Decision(BaseModel):
        approve: bool
except ImportError:  # pragma: no cover
    Decision = None  # type: ignore[assignment,misc]


def create_approvals_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/v1/approvals", tags=["approvals"])

    @router.get("")
    def pending():
        return {"pending": broker.list()}

    @router.post("/interrupt")
    def interrupt():
        """The user spoke or pressed stop: running agent loops stop after their current model call, and open questions count as no."""
        global _generation
        _generation += 1
        return {"ok": True, "denied": broker.deny_all()}

    @router.post("/{approval_id}")
    def decide(approval_id: str, body: Decision):
        return {"ok": broker.resolve(approval_id, body.approve)}

    return router
