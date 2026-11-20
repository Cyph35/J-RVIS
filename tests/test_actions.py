import pytest

from actions.applications import open_application
from actions.browser import open_website
from core.command_router import Tool, ToolRegistry


def test_unapproved_app_rejected():
    with pytest.raises(ValueError):
        open_application("rm -rf /")


@pytest.fixture(autouse=True)
def no_browser(monkeypatch):
    monkeypatch.setattr("webbrowser.open", lambda url: True)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "https://a b.com"])
def test_bad_urls_rejected(url):
    with pytest.raises(ValueError):
        open_website(url)


def make_reg():
    reg = ToolRegistry()
    reg.register(Tool("echo", "echo", lambda text: text, {"text": {"type": "string", "description": "t"}}))
    reg.register(Tool("boom", "fails", lambda: 1 / 0))
    return reg


def test_registry_validation():
    reg = make_reg()
    assert reg.execute("echo", {"text": "hi"}) == {"ok": True, "result": "hi"}
    assert not reg.execute("nope", {})["ok"]
    assert not reg.execute("echo", {})["ok"]
    assert not reg.execute("echo", {"text": 5})["ok"]
    assert not reg.execute("echo", {"text": "a", "x": 1})["ok"]


def test_tool_failure_reported_not_raised():
    out = make_reg().execute("boom", {})
    assert out["ok"] is False and "ZeroDivisionError" in out["error"]
