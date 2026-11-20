from core.assistant import Assistant


def ask_confirm(summary: str) -> bool:
    return input(f"  JARVIS wants to run {summary}. Allow? [y/N] ").strip().lower() in {"y", "yes"}


def main() -> None:
    print("JARVIS v0.1 - text mode. Type 'quit' to exit.")
    assistant = Assistant(confirm=ask_confirm)
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit"}:
            break
        if text:
            print("jarvis>", assistant.handle(text))
            for name, args, outcome in assistant.last_tool_calls:
                print(f"  [tool] {name}({args}) -> {'ok' if outcome['ok'] else 'FAILED'}")


if __name__ == "__main__":
    main()
