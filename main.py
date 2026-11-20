from core.assistant import Assistant


def main() -> None:
    print("JARVIS v0.1 - text mode. Type 'quit' to exit.")
    assistant = Assistant()
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
