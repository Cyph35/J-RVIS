import pytest

from actions.files import search_files
from core.command_router import Tool, ToolRegistry, default_registry
from memory.conversation import Memory
from memory.database import connect


@pytest.fixture
def mem():
    return Memory(connect(":memory:"))


def test_history_prefs_and_log(mem):
    mem.add_message("user", "hi"); mem.add_message("assistant", "hello")
    mem.add_message("user", "bye")
    assert mem.recent_messages(2) == [{"role": "assistant", "content": "hello"}, {"role": "user", "content": "bye"}]
    mem.set_pref("name", "Klint"); mem.set_pref("name", "K")
    assert mem.prefs() == {"name": "K"}
    mem.log_task("open_application", {"name": "x" * 500}, True)
    assert len(mem.conn.execute("SELECT args FROM task_log").fetchone()[0]) <= 200
    mem.forget_all()
    assert mem.recent_messages() == [] and mem.prefs() == {}


def test_file_search_scoped_and_limited(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "Resume-2026.pdf").write_text("x")
    (tmp_path / ".hidden-resume").write_text("x")
    out = search_files("resume", roots=[tmp_path])
    assert "Resume-2026.pdf" in out and ".hidden" not in out
    assert "No files" in search_files("nonexistent", roots=[tmp_path])
    with pytest.raises(ValueError):
        search_files("a")


def test_enum_validation():
    reg = default_registry()
    assert not reg.execute("music_control", {"action": "format_disk"})["ok"]
    assert not reg.execute("run_workflow", {"name": "rm_rf"})["ok"]


def test_workflow_stops_at_first_failure(monkeypatch):
    import actions.workflows as wf
    monkeypatch.setitem(wf.WORKFLOWS, "t", [("a", {}), ("b", {}), ("c", {})])
    reg = default_registry()
    ran = []
    reg.register(Tool("a", "a", lambda: ran.append("a") or "ok"))
    reg.register(Tool("b", "b", lambda: 1 / 0))
    reg.register(Tool("c", "c", lambda: ran.append("c") or "ok"))
    out = reg.execute("run_workflow", {"name": "t"})
    assert not out["ok"] and ran == ["a"] and "stopped" in out["error"]


def test_screen_tool_is_sensitive_and_needs_confirm():
    reg = default_registry(brain=object())
    assert not reg.execute("analyze_screen", {"question": "x"})["ok"]  # no confirm -> refused


def test_remember_preference_tool(mem):
    reg = default_registry(memory=mem)
    assert reg.execute("remember_preference", {"key": "Favorite Music", "value": "lofi"})["ok"]
    assert mem.prefs() == {"favorite music": "lofi"}
