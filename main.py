import sys

from core.assistant import Assistant


def ask_confirm(summary: str) -> bool:
    return input(f"  JARVIS wants to run {summary}. Allow? [y/N] ").strip().lower() in {"y", "yes"}


def show(assistant: Assistant, reply: str) -> None:
    print("jarvis>", reply)
    for name, args, outcome in assistant.last_tool_calls:
        print(f"  [tool] {name}({args}) -> {'ok' if outcome['ok'] else 'FAILED'}")


def text_loop(assistant: Assistant) -> None:
    print("JARVIS v0.2 - text mode. Type 'quit' to exit.")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit"}:
            break
        if text:
            show(assistant, assistant.handle(text))


def voice_loop(assistant: Assistant) -> None:
    from voice.listener import record_utterance
    from voice.transcriber import Transcriber

    print("Loading speech model...")
    transcriber = Transcriber()
    print("JARVIS v0.2 - voice mode. Press Enter to speak, or type 'quit'. Ctrl+C stops.")
    while True:
        try:
            if input("[Enter = speak] ").strip().lower() in {"quit", "exit"}:
                break
            audio = record_utterance()
            if audio is None:
                print("(didn't hear anything)")
                continue
            text = transcriber.transcribe(audio)
            if not text:
                print("(couldn't make out any words)")
                continue
            print("you said>", text)
            show(assistant, assistant.handle(text))
        except (EOFError, KeyboardInterrupt):
            print()
            break


def main() -> None:
    assistant = Assistant(confirm=ask_confirm)
    (voice_loop if "--voice" in sys.argv else text_loop)(assistant)


if __name__ == "__main__":
    main()
