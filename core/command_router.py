"""Tool registry: the ONLY actions the model can trigger. Validates every call."""
from dataclasses import dataclass, field
from typing import Any, Callable

_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., str]
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)  # name -> {type, description}
    sensitive: bool = False  # requires user confirmation before running

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters),
                },
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict | None,
                confirm: Callable[[str], bool] | None = None) -> dict:
        """Return {"ok": bool, "result"|"error": str}. Never raises.

        Sensitive tools run only if `confirm(description)` returns True;
        with no confirm callback they are always refused.
        """
        arguments = arguments or {}
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "error": f"Unknown tool {name!r}. Available: {sorted(self._tools)}"}
        extra = set(arguments) - set(tool.parameters)
        if extra:
            return {"ok": False, "error": f"Unexpected arguments: {sorted(extra)}"}
        for pname, spec in tool.parameters.items():
            if pname not in arguments:
                return {"ok": False, "error": f"Missing argument {pname!r}"}
            if not isinstance(arguments[pname], _TYPES[spec["type"]]):
                return {"ok": False, "error": f"Argument {pname!r} must be {spec['type']}"}
        if tool.sensitive:
            summary = f"{tool.name}({', '.join(f'{k}={v!r}' for k, v in arguments.items())})"
            if confirm is None or not confirm(summary):
                return {"ok": False, "error": "The user did not approve this action, so it was not performed."}
        for pname, spec in tool.parameters.items():
            if "enum" in spec and arguments[pname] not in spec["enum"]:
                return {"ok": False, "error": f"Argument {pname!r} must be one of {spec['enum']}"}
        try:
            return {"ok": True, "result": str(tool.func(**arguments))}
        except Exception as exc:  # report honestly, never claim success
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def default_registry(memory=None, brain=None) -> ToolRegistry:
    from actions.applications import close_application, open_application
    from actions.browser import open_website, search_web
    from actions.system import get_current_time, get_system_info

    reg = ToolRegistry()
    reg.register(Tool("get_current_time", "Get the current local date and time.", get_current_time))
    reg.register(Tool("open_website", "Open a website in the browser.", open_website,
                      {"url": {"type": "string", "description": "Web address, e.g. https://google.com"}}))
    reg.register(Tool("search_web", "Search the web for a query in the browser.", search_web,
                      {"query": {"type": "string", "description": "Search text"}}))
    reg.register(Tool("open_application", "Open an approved Mac application (Calculator, Safari, Chrome, Spotify, Notes, Finder, Terminal, VS Code).",
                      open_application, {"name": {"type": "string", "description": "Application name"}}))
    reg.register(Tool("close_application", "Quit an approved Mac application.", close_application,
                      {"name": {"type": "string", "description": "Application name"}}, sensitive=True))
    reg.register(Tool("get_system_info", "Get basic info about this Mac: macOS version, chip, RAM, free disk space, battery.",
                      get_system_info))
    from actions.files import search_files
    from actions.music import ACTIONS, music_control
    from actions.workflows import WORKFLOWS

    reg.register(Tool("search_files", "Find files by name in Documents, Downloads and Desktop (read-only).", search_files,
                      {"query": {"type": "string", "description": "Part of the file name"}}))
    reg.register(Tool("music_control", "Control the music app: play, pause, next, previous, or now_playing.", music_control,
                      {"action": {"type": "string", "enum": ACTIONS, "description": "Music action"}}))

    def run_workflow(name: str) -> str:
        """Run a fixed, predefined list of tool calls. Stops at the first failure."""
        report = []
        for tool_name, args in WORKFLOWS[name]:
            outcome = reg.execute(tool_name, args)
            report.append(f"{tool_name}: {'ok' if outcome['ok'] else 'FAILED - ' + outcome['error']}")
            if not outcome["ok"]:
                raise RuntimeError(f"Workflow {name!r} stopped. " + "; ".join(report))
        return f"Workflow {name!r} done. " + "; ".join(report)

    reg.register(Tool("run_workflow", "Run a predefined multi-step routine: " + ", ".join(WORKFLOWS), run_workflow,
                      {"name": {"type": "string", "enum": list(WORKFLOWS), "description": "Workflow name"}}))
    if memory is not None:
        def remember_preference(key: str, value: str) -> str:
            memory.set_pref(key.strip().lower(), value.strip())
            return f"Remembered {key}: {value}"
        reg.register(Tool("remember_preference", "Save a lasting fact or preference about the user (e.g. favorite_music, name).",
                          remember_preference, {"key": {"type": "string", "description": "Short label"},
                                                "value": {"type": "string", "description": "The value to remember"}}))
    if brain is not None:
        from actions.screen import analyze_screen
        reg.register(Tool("analyze_screen", "Take a screenshot and answer a question about what is on the screen.",
                          lambda question: analyze_screen(question, brain),
                          {"question": {"type": "string", "description": "What to look for on screen"}}, sensitive=True))
    return reg
